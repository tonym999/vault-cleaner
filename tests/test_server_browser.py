"""Real-browser acceptance for the packaged local review server (#90)."""

from __future__ import annotations

import os
import tempfile
import threading
from collections.abc import Callable, Iterator
from csv import DictReader, DictWriter
from dataclasses import dataclass
from pathlib import Path

import pytest
from playwright.sync_api import (
    Browser,
    BrowserType,
    Dialog,
    Locator,
    Page,
    expect,
)
from playwright.sync_api import (
    Error as PlaywrightError,
)

from vault_cleaner.server import app as server_app
from vault_cleaner.server.app import DEFAULT_ASSETS, build_server
from vault_cleaner.server.session import Session

FIXTURES = Path(__file__).parent / "fixtures"
HOSTILE_EXPORT = FIXTURES / "weapons_hostile.csv"
CLASS_ARMOR_EXPORT = FIXTURES / "armor_classes.csv"
ARMOR_CLOSE_EXPORT = FIXTURES / "armor_close.csv"
ARMOR_DUPLICATES_UI_EXPORT = FIXTURES / "armor_duplicates_ui.csv"
ARMOR_SAME_STAT_UI_EXPORT = FIXTURES / "armor_same_stat_ui.csv"
ARMOR_SAME_STAT_FOUR_UI_EXPORT = FIXTURES / "armor_same_stat_four_ui.csv"
HOSTILE_NAME = "</script><img src=x onerror=alert(1)>"
HOSTILE_NOTE = "</script><script>alert(1)</script>"
BOLD_NOTE = '"quoted" & <b>bold</b>'


@dataclass(frozen=True)
class LiveServer:
    session: Session
    origin: str
    bootstrap_url: str


class _TempfileProxy:
    """Keep server-owned upload directories under this test's ``tmp_path``."""

    def __init__(self, delegate: object, staging_root: Path) -> None:
        self._delegate = delegate
        self._staging_root = staging_root

    def mkdtemp(
        self,
        suffix: str | None = None,
        prefix: str | None = None,
        dir: str | os.PathLike[str] | None = None,
    ) -> str:
        if prefix is not None and prefix.startswith("vault-cleaner-uploads-"):
            dir = self._staging_root
        return self._delegate.mkdtemp(suffix=suffix, prefix=prefix, dir=dir)

    def __getattr__(self, name: str) -> object:
        return getattr(self._delegate, name)


@pytest.fixture(scope="session")
def browser(
    browser_type: BrowserType,
    launch_browser: Callable[[], Browser],
) -> Iterator[Browser]:
    """Launch the managed browser, with an opt-in missing-browser guard."""
    try:
        managed_browser = launch_browser()
    except PlaywrightError as error:
        # Playwright 1.62 may launch Chromium through its separate headless
        # shell.  Checking BrowserType.executable_path before launch therefore
        # checks a different binary than the one this fixture needs.  Keep the
        # guard limited to Playwright's own missing-executable diagnostic so
        # launch/library/runtime failures remain visible as real test errors.
        if not str(error).startswith("BrowserType.launch: Executable doesn't exist at "):
            raise
        message = f"managed Playwright {browser_type.name} executable is absent: {error}"
        if os.environ.get("VAULT_CLEANER_BROWSER_REQUIRED") == "1":
            pytest.fail(message)
        pytest.skip(message)
    yield managed_browser
    managed_browser.close()


@pytest.fixture
def live_server(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> Iterator[LiveServer]:
    staging_root = tmp_path / "server-staging"
    staging_root.mkdir()
    monkeypatch.setattr(
        server_app,
        "tempfile",
        _TempfileProxy(tempfile, staging_root),
    )
    config = tmp_path / "config.toml"
    config.write_text("", encoding="utf-8")
    session = Session(
        overrides_path=str(tmp_path / "overrides.json"),
        config_path=str(config),
        no_wishlists=True,
        bootstrap_token="browser-bootstrap",
        session_token="browser-session",
    )
    server = build_server(session, 0, assets=DEFAULT_ASSETS)
    thread = threading.Thread(
        target=server.serve_forever,
        name="vault-cleaner-browser-test-server",
    )
    thread.start()
    origin = session.expected_origin
    try:
        yield LiveServer(
            session=session,
            origin=origin,
            bootstrap_url=f"{origin}/bootstrap?token={session.bootstrap_token}",
        )
    finally:
        if thread.is_alive():
            server.shutdown()
        thread.join(timeout=5)
        server.server_close()
        session.close()
        assert not thread.is_alive(), "browser-test server thread did not stop"


def authenticate(page: Page, live_server: LiveServer) -> None:
    page.goto(live_server.bootstrap_url, wait_until="domcontentloaded")
    expect(page).to_have_url(f"{live_server.origin}/")
    expect(page.locator("#vc-status")).to_contain_text("Connected")


def badge_width_and_heading_budget(badge: Locator) -> tuple[float, float]:
    """Return (badge offsetWidth, its ``.armor-member-heading``'s fixed min-width).

    ``el.scrollWidth <= el.clientWidth`` on the badge itself is true by
    construction here: the badge sits in an auto-width ``<th>`` inside
    ``.scroller { overflow-x: auto }``, so a non-wrapping (``white-space:
    nowrap``) badge never overflows *itself* -- it just grows the ``<th>``
    to fit. That makes the naive scrollWidth/clientWidth check pass in both
    the wrapping and non-wrapping states, so it cannot detect a regression.

    Compare the badge's rendered width against the *fixed* min-width of its
    ``.armor-member-heading`` container instead. That budget comes from a
    separate selector (``.armor-member-heading { min-width: 11rem }``) that
    this ticket does not touch, and it does not grow with the badge's
    content the way the heading's own offsetWidth does -- so it is a real,
    independent layout budget: a wrapped badge stays within it, a
    non-wrapping badge blows through it (measured: 160px vs a 176px budget
    with the CSS rule in place; 252px vs the same 176px budget without it).
    """
    width, budget = badge.evaluate(
        "el => { var h = el.closest('.armor-member-heading');"
        " return [el.offsetWidth, h ? parseFloat(getComputedStyle(h).minWidth) : NaN]; }"
    )
    return float(width), float(budget)


def same_stat_members_export(
    tmp_path: Path, member_count: int, *, long_member_id: bool = False
) -> Path:
    """Build a test-owned same-stat input with the requested member count."""
    with ARMOR_SAME_STAT_FOUR_UI_EXPORT.open(encoding="utf-8", newline="") as source:
        reader = DictReader(source)
        rows = list(reader)
        assert reader.fieldnames is not None
        fieldnames = reader.fieldnames
    if member_count == 5:
        extra = rows[-1].copy()
        extra["Id"] = "8405"
        rows.append(extra)
    if long_member_id:
        rows[0]["Id"] = "9" * 200
    target = tmp_path / f"same-stat-{member_count}.csv"
    with target.open("w", encoding="utf-8", newline="") as destination:
        writer = DictWriter(destination, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows[:member_count])
    return target


@pytest.mark.browser
def test_hostile_export_remains_inert_in_live_dom(
    page: Page, live_server: LiveServer
) -> None:
    dialogs: list[str] = []

    def reject_dialog(dialog: Dialog) -> None:
        dialogs.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", reject_dialog)
    authenticate(page, live_server)
    page.locator("#vc-upload-weapons").set_input_files(HOSTILE_EXPORT)

    expect(page.locator("#vc-upload-status-weapons")).to_have_text("Accepted")
    expect(page.locator("#vc-report")).to_be_visible()
    hostile_row = page.locator('tr[data-id="18446744073709551615"]')
    expect(hostile_row.locator("td.namecell button")).to_contain_text(HOSTILE_NAME)
    hostile_row.locator("td.namecell button").click()
    expect(page.locator("#vc-detail-18446744073709551615")).to_contain_text(
        HOSTILE_NOTE
    )

    bold_row = page.locator('tr[data-id="7004"]')
    bold_row.locator("td.namecell button").click()
    expect(page.locator("#vc-detail-7004")).to_contain_text(BOLD_NOTE)

    dynamic_report = page.locator("#vc-list")
    expect(dynamic_report.locator("img")).to_have_count(0)
    expect(dynamic_report.locator("script")).to_have_count(0)
    expect(dynamic_report.locator("b")).to_have_count(0)
    expect(hostile_row.locator("button.approve")).to_be_enabled()
    assert dialogs == []


@pytest.mark.browser
def test_review_smoke_downloads_server_finalized_bytes(
    page: Page, live_server: LiveServer
) -> None:
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(CLASS_ARMOR_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-report")).to_be_visible()
    expect(page.locator("#vc-f-kind")).to_be_visible()
    class_filter = page.locator("#vc-f-classFacet")
    expect(class_filter).to_be_visible()
    expect(class_filter.locator('option[value="Hunter"]')).to_have_text("Hunter (1)")
    expect(class_filter.locator('option[value="Warlock"]')).to_have_text("Warlock (1)")
    expect(page.locator("#vc-f-owner")).to_have_count(0)
    headers = page.locator("#vc-list thead th")
    expect(headers).to_have_count(10)
    expect(page.locator("#vc-list thead")).to_contain_text("Class")
    expect(page.locator("#vc-list thead")).to_contain_text("Location")
    expect(page.locator("#vc-list tr[data-id]")).to_have_count(2)
    class_location_row = page.locator('#vc-list tr[data-id="9002"]')
    expect(class_location_row).to_be_visible()
    cells = class_location_row.locator("td")
    expect(cells.nth(3)).to_have_text("Hunter")
    expect(cells.nth(4)).to_have_text("Vault")
    warlock_location_row = page.locator('#vc-list tr[data-id="9012"]')
    expect(warlock_location_row).to_be_visible()
    warlock_cells = warlock_location_row.locator("td")
    expect(warlock_cells.nth(3)).to_have_text("Warlock")
    expect(warlock_cells.nth(4)).to_have_text("Hunter(550)")
    class_filter.select_option("Hunter")
    expect(page.locator("#vc-list tr[data-id]")).to_have_count(1)
    expect(page.locator('#vc-list tr[data-id="9002"]')).to_be_visible()
    expect(page.locator('#vc-list tr[data-id="9012"]')).to_have_count(0)
    page.get_by_role("button", name="Reset filters").click()
    expect(class_filter).to_have_value("")
    row = page.locator("#vc-list tr[data-id]").first
    expect(row).to_be_visible()

    approve = row.locator("button.approve")
    approve.click()
    expect(approve).to_have_attribute("aria-pressed", "true")

    unset = row.locator("button.clear-verdict")
    unset.click()
    expect(unset).to_have_attribute("aria-pressed", "true")

    veto = row.locator("button.veto")
    veto.click()
    expect(veto).to_have_attribute("aria-pressed", "true")

    page.once("dialog", lambda dialog: dialog.accept())
    with page.expect_download() as download_info:
        page.locator("#vc-finalize").click()
    download = download_info.value
    expect(page.locator("#vc-download-again")).to_be_visible()

    assert download.suggested_filename == "dim-import.csv"
    finalized = live_server.session.finalized_csv_bytes
    assert finalized is not None
    assert Path(download.path()).read_bytes() == finalized


@pytest.mark.browser
def test_armor_tuning_slots_are_visible_in_unexpanded_proposals(
    page: Page, live_server: LiveServer
) -> None:
    """Pairwise tuning is ordinary text in the existing Proposals table."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_CLOSE_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-report")).to_be_visible()
    page.locator("#vc-f-group").select_option("flat")
    expect(page.locator("#vc-list thead")).to_contain_text("Tuning Mod Slot")

    different = page.locator('#vc-list tr[data-id="6081"]')
    equal_unknown = page.locator('#vc-list tr[data-id="6101"]')
    expect(different).to_be_visible()
    expect(equal_unknown).to_be_visible()

    # Name, id, kind, class, location, action, reason, tuning, protection,
    # verdict. The pair is visible before any row expansion or hover.
    different_tuning = different.locator("td").nth(7)
    unknown_tuning = equal_unknown.locator("td").nth(7)
    expect(different_tuning).to_have_text("Candidate: Melee · Selected: Grenade")
    expect(unknown_tuning).to_have_text(
        "Candidate: none/unknown · Selected: none/unknown"
    )
    assert different.locator("td").nth(7).locator("span").count() == 0
    assert page.locator('#vc-detail-6081').count() == 0
    assert page.locator('#vc-detail-6101').count() == 0


@pytest.mark.browser
def test_armor_duplicates_view_uses_authoritative_group_and_verdicts(
    page: Page, live_server: LiveServer
) -> None:
    """The complete exact group and its proposal verdict share one server map."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_DUPLICATES_UI_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_visible()
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    expect(page.locator("#vc-duplicates")).to_be_visible()
    group = page.locator("article.armor-group")
    expect(group).to_have_count(1)
    expect(group.locator("p.armor-group-pieces")).to_have_text("3 pieces")
    expect(group.locator("p.sub")).to_have_text("Exact")
    expect(page.locator("#vc-duplicate-scope")).to_have_text("1 group · 3 pieces")
    expect(page.locator("#vc-duplicate-scope")).to_have_attribute("role", "status")
    expect(page.locator("#vc-duplicate-scope")).to_have_attribute("aria-live", "polite")
    expect(group).to_contain_text("Archetype Plate")
    expect(group).to_contain_text("Chest Armor")
    expect(group).to_contain_text("Hunter")
    expect(group).to_contain_text("Gunner")
    expect(group).to_contain_text("Tuning Mod Slot")
    expect(group).to_contain_text("Weapons")
    expect(group).to_contain_text("Primary")
    expect(group).to_contain_text("Secondary")
    expect(group).to_contain_text("Tertiary")
    expect(group).to_contain_text("The other three base stats are 0")

    for member_id in ("8201", "8202", "8203"):
        expect(group.locator(
            f'.armor-matrix-columns [data-member-id="exact_duplicate:{member_id}"]'
        )).to_be_visible()
        expect(group).to_contain_text(member_id)
    expect(group).to_contain_text("Preferred survivor")
    expect(group).to_contain_text("Retained protected")
    expect(group).to_contain_text("Proposed junk")
    assert group.locator('.armor-matrix-columns [data-member-id="exact_duplicate:8201"] button.approve').count() == 0
    assert group.locator('.armor-matrix-columns [data-member-id="exact_duplicate:8202"] button.veto').count() == 0
    proposal = group.locator('.armor-matrix-columns [data-member-id="exact_duplicate:8203"]')
    expect(proposal.locator("button.approve")).to_be_enabled()

    proposal.locator("button.approve").click()
    expect(proposal.locator("button.approve")).to_have_attribute(
        "aria-pressed", "true"
    )

    page.locator("#vc-view-proposals").click()
    proposal_row = page.locator('#vc-list tr[data-id="8203"]')
    expect(proposal_row).to_be_visible()
    expect(proposal_row.locator("button.approve")).to_have_attribute(
        "aria-pressed", "true"
    )


@pytest.mark.browser
def test_armor_same_stat_group_renders_member_tuning_variation(
    page: Page, live_server: LiveServer
) -> None:
    """Same-stat groups are complete, review-only comparisons."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_SAME_STAT_UI_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    expect(group).to_have_count(1)
    expect(group.locator("p.armor-group-pieces")).to_have_text("2 pieces")
    expect(group.locator("p.sub")).to_have_text("Same stats · review only")
    expect(page.locator("#vc-duplicate-scope")).to_have_text("1 group · 2 pieces")
    expect(group.locator("p.hint").first).to_contain_text(
        "Base stats match but tuning differs, so this pass selects no survivor."
    )
    expect(group).to_contain_text("8301")
    expect(group).to_contain_text("8302")
    expect(group).to_contain_text("Tuning Mod Slot")
    expect(group).to_contain_text("Weapons")
    expect(group).to_contain_text("Health")
    matrix = group.locator(".armor-matrix")
    rows = group.locator(".armor-matrix-rows")
    columns = group.locator(".armor-matrix-columns")
    expect(matrix).to_have_attribute("data-member-count", "2")
    page.set_viewport_size({"width": 390, "height": 844})
    expect(rows).to_be_visible()
    expect(columns).to_be_hidden()
    visible_approve = rows.locator("button.approve").first
    expect(visible_approve).to_be_visible()
    visible_approve.click()
    expect(visible_approve).to_have_attribute("aria-pressed", "true")

    page.set_viewport_size({"width": 1440, "height": 900})
    matrix.evaluate("el => { el.style.width = '527px'; }")
    expect(rows).to_be_visible()
    expect(columns).to_be_hidden()
    matrix.evaluate("el => { el.style.width = '528px'; }")
    expect(columns).to_be_visible()
    expect(rows).to_be_hidden()
    expect(group.locator(
        ".armor-matrix-columns th[scope='row']"
    ).filter(has_text="Tuning Mod Slot")).to_be_visible()
    expect(group.locator(".armor-matrix-columns button.approve")).to_have_count(2)
    expect(group).not_to_contain_text("Preferred survivor")
    expect(group).not_to_contain_text("Proposed junk")


@pytest.mark.browser
def test_armor_same_stat_three_member_matrix_switches_at_45rem(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """A real three-member input switches only at the measured 45rem floor."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(same_stat_members_export(tmp_path, 3))
    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    matrix = group.locator(".armor-matrix")
    rows = group.locator(".armor-matrix-rows")
    columns = group.locator(".armor-matrix-columns")
    expect(matrix).to_have_attribute("data-member-count", "3")
    matrix.evaluate("el => { el.style.width = '719px'; }")
    expect(rows).to_be_visible()
    expect(columns).to_be_hidden()
    matrix.evaluate("el => { el.style.width = '720px'; }")
    expect(columns).to_be_visible()
    expect(rows).to_be_hidden()


@pytest.mark.browser
def test_armor_two_member_column_matrix_wraps_a_long_opaque_id(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """A long opaque id cannot widen the active matrix past its 33rem budget."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(
        same_stat_members_export(tmp_path, 2, long_member_id=True)
    )
    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    page.locator("#vc-view-duplicates").click()

    matrix = page.locator('.armor-matrix[data-member-count="2"]')
    matrix.evaluate("el => { el.style.width = '528px'; }")
    columns = matrix.locator(".armor-matrix-columns")
    expect(columns).to_be_visible()
    scroll_width, client_width = columns.evaluate(
        "el => [el.scrollWidth, el.clientWidth]"
    )
    assert scroll_width <= client_width


@pytest.mark.browser
def test_armor_matrix_tab_order_uses_only_the_active_orientation(
    page: Page, live_server: LiveServer
) -> None:
    """Tab traversal never reaches controls in the display:none matrix."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_SAME_STAT_UI_EXPORT)
    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    page.locator("#vc-view-duplicates").click()

    matrix = page.locator(".armor-matrix")

    def assert_tab_order(active_class: str) -> Locator:
        controls = matrix.locator(f".{active_class} button")
        assert controls.count() == 6
        controls.first.focus()
        for index in range(controls.count()):
            assert page.evaluate(
                "(className) => document.activeElement.closest('.' + className) !== null",
                active_class,
            )
            if index < controls.count() - 1:
                page.keyboard.press("Tab")
        return controls

    page.set_viewport_size({"width": 390, "height": 844})
    expect(matrix.locator(".armor-matrix-rows")).to_be_visible()
    expect(matrix.locator(".armor-matrix-columns")).to_be_hidden()
    assert_tab_order("armor-matrix-rows")
    page.keyboard.press("Tab")
    assert page.evaluate(
        "() => document.activeElement.closest('.armor-matrix-columns') === null"
    )

    page.set_viewport_size({"width": 1440, "height": 900})
    matrix.evaluate("el => { el.style.width = '528px'; }")
    expect(matrix.locator(".armor-matrix-columns")).to_be_visible()
    expect(matrix.locator(".armor-matrix-rows")).to_be_hidden()
    column_controls = assert_tab_order("armor-matrix-columns")
    column_controls.first.focus()
    page.keyboard.press("Shift+Tab")
    assert page.evaluate(
        "() => document.activeElement.closest('.armor-matrix-rows') === null"
    )


@pytest.mark.browser
def test_armor_same_stat_five_member_matrix_stays_in_row_fallback(
    page: Page, live_server: LiveServer, tmp_path: Path
) -> None:
    """An unbounded five-member group never borrows a four-member threshold."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(same_stat_members_export(tmp_path, 5))
    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    page.locator("#vc-view-duplicates").click()

    page.set_viewport_size({"width": 1440, "height": 900})
    matrix = page.locator('.armor-matrix[data-member-count="5"]')
    expect(matrix).to_have_attribute("data-member-count", "5")
    expect(matrix.locator(".armor-matrix-rows")).to_be_visible()
    expect(matrix.locator(".armor-matrix-columns")).to_be_hidden()


@pytest.mark.browser
def test_armor_same_stat_four_member_responsive_member_matrix(
    page: Page, live_server: LiveServer
) -> None:
    """Four-member comparisons switch by container size, not viewport size."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_SAME_STAT_FOUR_UI_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    expect(group).to_have_count(1)
    expect(group.locator("p.armor-group-pieces")).to_have_text("4 pieces")
    expect(page.locator("#vc-duplicate-scope")).to_have_text("1 group · 4 pieces")

    rows = group.locator(".armor-matrix-rows")
    columns = group.locator(".armor-matrix-columns")
    matrix = group.locator(".armor-matrix")
    expect(matrix).to_have_attribute("data-member-count", "4")
    expect(columns).to_be_visible()
    expect(rows).to_be_hidden()
    expect(columns.locator("thead th").first).to_have_text("Comparison")
    expect(columns.locator("th[scope='row']").filter(has_text="Tuning Mod Slot")).to_be_visible()
    expect(columns.locator("th[scope='row']").filter(has_text="Protection")).to_be_visible()
    expect(columns.locator("th[scope='row']").filter(has_text="Verdict")).to_be_visible()

    page.set_viewport_size({"width": 390, "height": 844})
    expect(rows).to_be_visible()
    expect(columns).to_be_hidden()
    expect(rows.locator("tbody tr")).to_have_count(4)
    assert page.evaluate("document.documentElement.scrollWidth") <= 390
    assert rows.locator("button:visible").count() == rows.locator("button").count()
    assert columns.locator("button:visible").count() == 0

    page.set_viewport_size({"width": 1440, "height": 900})
    matrix.evaluate("el => { el.style.width = '911px'; }")
    expect(rows).to_be_visible()
    expect(columns).to_be_hidden()
    matrix.evaluate("el => { el.style.width = '912px'; }")
    expect(columns).to_be_visible()
    expect(rows).to_be_hidden()
    assert page.evaluate("document.documentElement.scrollWidth") <= 1440

    # Badges wrap within their heading's fixed width budget instead of
    # forcing the cell wider (see badge_width_and_heading_budget for why a
    # bare scrollWidth <= clientWidth check on the badge cannot catch this).
    badges = columns.locator(".armor-member-heading .badge")
    assert badges.count() == 4
    for i in range(badges.count()):
        badge = badges.nth(i)
        width, budget = badge_width_and_heading_budget(badge)
        assert width <= budget, (
            f"badge {i} exceeded its heading's {budget}px width budget: {width}px"
        )

    # Light and dark color schemes: assert theme-sensitive computed values
    # actually change, not just that emulate_media was called.
    scope_summary = page.locator(".scope-summary").first
    group_pieces = page.locator(".armor-group-pieces").first
    transparent_values = {"rgba(0, 0, 0, 0)", "transparent"}

    def theme_snapshot() -> dict[str, str]:
        return {
            "scope-summary backgroundColor": scope_summary.evaluate(
                "el => getComputedStyle(el).backgroundColor"
            ),
            "scope-summary borderLeftColor": scope_summary.evaluate(
                "el => getComputedStyle(el).borderLeftColor"
            ),
            "armor-group-pieces color": group_pieces.evaluate(
                "el => getComputedStyle(el).color"
            ),
            "armor-group-pieces borderColor": group_pieces.evaluate(
                "el => getComputedStyle(el).borderColor"
            ),
        }

    page.emulate_media(color_scheme="dark")
    dark_theme = theme_snapshot()
    dark_scroll_width = page.evaluate("document.documentElement.scrollWidth")
    assert dark_scroll_width <= page.viewport_size["width"]
    for i in range(badges.count()):
        badge = badges.nth(i)
        width, budget = badge_width_and_heading_budget(badge)
        assert width <= budget, (
            f"badge {i} exceeded its heading's {budget}px width budget in dark mode: {width}px"
        )

    page.emulate_media(color_scheme="light")
    light_theme = theme_snapshot()
    light_scroll_width = page.evaluate("document.documentElement.scrollWidth")
    assert light_scroll_width <= page.viewport_size["width"]
    for i in range(badges.count()):
        badge = badges.nth(i)
        width, budget = badge_width_and_heading_budget(badge)
        assert width <= budget, (
            f"badge {i} exceeded its heading's {budget}px width budget in light mode: {width}px"
        )

    for label, value in dark_theme.items():
        assert value not in transparent_values, f"dark {label} was transparent: {value}"
    for label, value in light_theme.items():
        assert value not in transparent_values, f"light {label} was transparent: {value}"
    for label in dark_theme:
        assert dark_theme[label] != light_theme[label], (
            f"{label} did not change between dark and light color schemes: "
            f"{dark_theme[label]!r}"
        )


@pytest.mark.browser
def test_armor_duplicates_mixed_report_scope_summary_and_filtering(
    page: Page, live_server: LiveServer
) -> None:
    """Mixed report displays scope summary, and kind/facet filters update it accurately."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_CLOSE_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()

    # Proposals surface keeps the "shown" tile -- pin its presence here first
    # so the later absence check on the duplicates surface proves a surface
    # distinction, not just that the string never renders anywhere.
    shown_tile = page.locator("#vc-summary .tile .k:text-is('shown')")
    expect(shown_tile).to_have_count(1)

    page.locator("#vc-view-duplicates").click()

    scope = page.locator("#vc-duplicate-scope")
    expect(scope).to_be_visible()
    expect(scope).to_have_attribute("role", "status")
    expect(scope).to_have_attribute("aria-live", "polite")

    # The duplicates surface has no per-item filter to "show", so #vc-summary
    # must not carry the "shown" tile here (#119 review Check 4).
    expect(shown_tile).to_have_count(0)

    # The scope region lives outside the list host that renderList clears on
    # every keystroke -- pin that here so a future change that instead builds
    # this element inside #vc-duplicate-list (destroy-and-recreate on every
    # render, never reliably announced) is caught rather than merely passing
    # a same-id text check.
    assert scope.evaluate("el => el.parentElement && el.parentElement.id") == "vc-duplicates"
    scope_node_before_filter = scope.element_handle()
    assert scope_node_before_filter is not None

    # Unfiltered mixed report: 2 groups, 4 pieces
    expect(scope).to_have_text("2 groups · 4 pieces")

    # Filter to exact duplicates: group count and piece count differ (1 group vs 2 pieces)
    page.locator("#vc-dup-kind-exact").click()
    expect(scope).to_have_text(
        "1 of 2 groups · 2 of 4 pieces — filtered to exact duplicates"
    )
    assert scope.evaluate("el => el.parentElement && el.parentElement.id") == "vc-duplicates"
    scope_node_after_filter = page.locator("#vc-duplicate-scope").element_handle()
    assert scope_node_after_filter is not None
    same_node = scope_node_before_filter.evaluate(
        "(el, other) => el === other", scope_node_after_filter
    )
    assert same_node, (
        "#vc-duplicate-scope was destroyed and recreated by the kind filter "
        "change instead of being updated in place"
    )

    # Filter to same-stat groups: group count and piece count differ (1 group vs 2 pieces)
    page.locator("#vc-dup-kind-same_stat").click()
    expect(scope).to_have_text(
        "1 of 2 groups · 2 of 4 pieces — filtered to same-stat groups"
    )

    # Reset kind to all
    page.locator("#vc-dup-kind-all").click()
    expect(scope).to_have_text("2 groups · 4 pieces")


@pytest.mark.browser
def test_duplicates_surface_does_not_scroll_horizontally(
    page: Page, live_server: LiveServer
) -> None:
    """Wrapping guards, not scroller removal, keep the document from
    overflowing sideways at narrow and desktop widths (#118)."""
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_SAME_STAT_UI_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    expect(group).to_have_count(1)

    fingerprint = page.locator("#vc-fingerprint")
    digest = fingerprint.inner_text()
    assert digest

    for width, height in ((390, 844), (1440, 1000)):
        page.set_viewport_size({"width": width, "height": height})
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        assert scroll_width <= width, (
            f"document scrolled horizontally at {width}px viewport: "
            f"scrollWidth={scroll_width}"
        )

    # The fingerprint still renders its digest -- overflow was fixed by
    # wrapping, not by hiding or emptying the element.
    expect(fingerprint).to_have_text(digest)

    heading_overflow_wrap = group.locator("h3").evaluate(
        "el => getComputedStyle(el).overflowWrap"
    )
    assert heading_overflow_wrap == "anywhere"

    # The comparison table keeps its own contained horizontal scroll --
    # overflow was not "fixed" by removing it.
    scroller_overflow_x = group.locator(".scroller").first.evaluate(
        "el => getComputedStyle(el).overflowX"
    )
    assert scroller_overflow_x == "auto"

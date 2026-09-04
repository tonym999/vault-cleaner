"""Real-browser acceptance for the packaged local review server (#90)."""

from __future__ import annotations

import os
import tempfile
import threading
from collections.abc import Callable, Iterator
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
    # Role labels are lowercase in the stat spike (settled #131 copy, matching
    # the agreed artifact's "primary/secondary/tertiary" text).
    expect(group).to_contain_text("primary")
    expect(group).to_contain_text("secondary")
    expect(group).to_contain_text("tertiary")
    expect(group).to_contain_text("0 base")

    # Two matrix orientations register every member id twice (row + column
    # table); only one is ever visible at a time, so structural/interaction
    # assertions below scope to the :visible occurrence (#131).
    for member_id in ("8201", "8202", "8203"):
        expect(group.locator(f'[data-member-id="exact_duplicate:{member_id}"]:visible')).to_be_visible()
        expect(group).to_contain_text(member_id)
    expect(group).to_contain_text("Preferred survivor")
    expect(group).to_contain_text("Retained protected")
    expect(group).to_contain_text("Proposed junk")
    assert group.locator('[data-member-id="exact_duplicate:8201"]:visible button.approve').count() == 0
    assert group.locator('[data-member-id="exact_duplicate:8202"]:visible button.veto').count() == 0
    proposal = group.locator('[data-member-id="exact_duplicate:8203"]:visible')
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
def test_armor_stat_spike_bars_render_proportional_widths(
    page: Page, live_server: LiveServer
) -> None:
    """The 30/25/20 stat-spike bars must render at different widths (#131).

    An inline `style="width:...%"` attribute is blocked outright by the
    server's `style-src 'self'` CSP (no `unsafe-inline`), so Chromium drops
    it and every bar previously rendered at the same width regardless of
    value -- measured on the pre-fix head as an identical 86.39px for the
    30/25/20 stats. Assert rendered geometry
    (`getBoundingClientRect().width`), not the CSS declarations, so a fix
    that only changes the stylesheet without the attribute actually being
    dropped would still be caught.
    """
    authenticate(page, live_server)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.locator("#vc-upload-armor").set_input_files(ARMOR_DUPLICATES_UI_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    expect(group).to_have_count(1)
    primary_bar = group.locator(".sv.p .bar")
    secondary_bar = group.locator(".sv.s .bar")
    tertiary_bar = group.locator(".sv.t .bar")
    expect(primary_bar).to_be_visible()
    expect(secondary_bar).to_be_visible()
    expect(tertiary_bar).to_be_visible()

    primary_width = primary_bar.evaluate("el => el.getBoundingClientRect().width")
    secondary_width = secondary_bar.evaluate("el => el.getBoundingClientRect().width")
    tertiary_width = tertiary_bar.evaluate("el => el.getBoundingClientRect().width")

    assert primary_width > secondary_width > tertiary_width > 0, (
        primary_width, secondary_width, tertiary_width
    )


@pytest.mark.browser
def test_armor_duplicates_surface_has_no_csp_violations(
    page: Page, live_server: LiveServer
) -> None:
    """Loading and rendering Armor duplicates must trip no CSP violation.

    The server's `SERVER_CSP` sends `style-src 'self'` with no
    `unsafe-inline`; an inline `style` attribute anywhere in the rendered
    Armor duplicates DOM would be silently dropped by Chromium and logged
    as a console CSP violation without raising in Python. Attach the
    console listener before navigation so it also catches a violation
    during the initial page load, not only after the upload.
    """
    csp_violations: list[str] = []

    def record_console_message(message: object) -> None:
        text = message.text  # type: ignore[attr-defined]
        if "Content Security Policy" in text:
            csp_violations.append(text)

    page.on("console", record_console_message)
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_DUPLICATES_UI_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    expect(page.locator("article.armor-group")).to_have_count(1)
    assert csp_violations == []


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
    # The same-stat banner is the artifact's always-visible .tuneline.warn
    # treatment, not the generic .hint class (#131).
    expect(group.locator(".tuneline.warn")).to_contain_text(
        "Base stats match but tuning differs, so this pass selects no survivor."
    )
    expect(group).to_contain_text("8301")
    expect(group).to_contain_text("8302")
    expect(group).to_contain_text("Tuning Mod Slot")
    expect(group).to_contain_text("Weapons")
    expect(group).to_contain_text("Health")
    # Whichever matrix orientation is active at this viewport, the Tuning Mod
    # Slot axis is always present and visible (#131 acceptance: same-stat's
    # defining axis is never suppressed).
    expect(group.locator("th:visible").filter(has_text="Tuning Mod Slot")).to_be_visible()
    expect(group.locator("button.approve:visible")).to_have_count(2)
    expect(group).not_to_contain_text("Preferred survivor")
    expect(group).not_to_contain_text("Proposed junk")


@pytest.mark.browser
def test_armor_same_stat_four_member_badge_wrapping_and_transposition(
    page: Page, live_server: LiveServer
) -> None:
    """Four-member same-stat groups render both matrix orientations correctly.

    Member columns are the artifact orientation and are used only where a
    four-member matrix actually fits (#131 measured evidence:
    docs/evidence/issue-131/orientation-measurements.md); the row fallback is
    used everywhere else, including 390px. Exactly one orientation is ever
    visible, absent-from-accessibility-tree is proven by the hidden table
    failing `to_be_visible`, and both use the same field list.
    """
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_SAME_STAT_FOUR_UI_EXPORT)

    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    expect(group).to_have_count(1)
    expect(group.locator("p.armor-group-pieces")).to_have_text("4 pieces")
    expect(page.locator("#vc-duplicate-scope")).to_have_text("1 group · 4 pieces")

    columns_table = group.locator("table.armor-matrix-columns")
    rows_table = group.locator("table.armor-matrix-rows")

    # Fitting desktop panel (1440px): the 4-member budget (63.5rem/1016px)
    # fits inside the ~1156px comparison content box, so member columns are
    # the active orientation and the row fallback is hidden.
    page.set_viewport_size({"width": 1440, "height": 900})
    expect(columns_table).to_be_visible()
    expect(rows_table).to_be_hidden()
    expect(columns_table.locator("th.armor-matrix-corner")).to_have_text("Differs on")
    expect(columns_table.locator("th.armor-matrix-col-heading")).to_have_count(4)
    expect(columns_table.locator("th").filter(has_text="Tuning Mod Slot")).to_be_visible()
    expect(columns_table.locator("th").filter(has_text="Protection")).to_be_visible()
    expect(columns_table.locator("th").filter(has_text="Verdict")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth") <= 1440

    # Non-fitting desktop panel (1000px, below the 1016px budget): the row
    # fallback becomes active -- the orientation flip is width-driven, not a
    # fixed desktop/mobile split.
    page.set_viewport_size({"width": 1000, "height": 900})
    expect(rows_table).to_be_visible()
    expect(columns_table).to_be_hidden()
    assert page.evaluate("document.documentElement.scrollWidth") <= 1000

    # Narrow panel (390px): row fallback stays active. Transposed layout: 4
    # rows in tbody, one per member.
    page.set_viewport_size({"width": 390, "height": 844})
    expect(rows_table).to_be_visible()
    expect(columns_table).to_be_hidden()
    expect(rows_table.locator("tbody tr")).to_have_count(4)
    expect(rows_table.locator("th[scope='col']").filter(has_text="Member")).to_be_visible()
    expect(rows_table.locator("th[scope='col']").filter(has_text="Tuning Mod Slot")).to_be_visible()
    expect(rows_table.locator("th[scope='col']").filter(has_text="Protection")).to_be_visible()
    expect(rows_table.locator("th[scope='col']").filter(has_text="Verdict")).to_be_visible()

    # Viewport checks at desktop and mobile widths
    for width, height in ((1440, 900), (390, 844)):
        page.set_viewport_size({"width": width, "height": height})
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        assert scroll_width <= width, (
            f"document scrolled horizontally at {width}px: scrollWidth={scroll_width}"
        )

    # Badges wrap within their heading's fixed width budget instead of
    # forcing the cell wider (see badge_width_and_heading_budget for why a
    # bare scrollWidth <= clientWidth check on the badge cannot catch this).
    # Scoped to :visible -- the current viewport (390px, from the loop above)
    # has the row orientation active, and a display:none heading has no
    # usable geometry to budget against.
    badges = page.locator("article.armor-group .armor-member-heading:visible .badge")
    assert badges.count() == 4
    for i in range(badges.count()):
        badge = badges.nth(i)
        width, budget = badge_width_and_heading_budget(badge)
        assert width <= budget, (
            f"badge {i} exceeded its heading's {budget}px width budget: {width}px"
        )

    # Light and dark color schemes: assert theme-sensitive computed values
    # actually change, not just that emulate_media was called. Coverage
    # extended (#131 P3-2) beyond the scope summary and piece-count chip to
    # the archetype badge, a tuning banner, the stat spike and a section
    # heading, since #131's new CSS for those elements uses only
    # --accent/--muted/--line/--review/--warn-bg with no hardcoded colors.
    # This fixture is same-stat only, so only the `.tuneline.warn` variant
    # is exercised here; the plain `.tuneline` variant shares the same
    # `--accent`/`--line` tokens already covered by the archetype badge and
    # scope summary assertions below.
    scope_summary = page.locator(".scope-summary").first
    group_pieces = page.locator(".armor-group-pieces").first
    archetype_badge = page.locator(".badge.arch").first
    tuning_banner = page.locator(".tuneline.warn").first
    stat_spike_bar = page.locator(".armor-stat-summary.spike .sv.p .bar").first
    section_heading = page.locator(".armor-section-head h3").first
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
            "archetype-badge color": archetype_badge.evaluate(
                "el => getComputedStyle(el).color"
            ),
            "tuning-banner backgroundColor": tuning_banner.evaluate(
                "el => getComputedStyle(el).backgroundColor"
            ),
            "tuning-banner borderLeftColor": tuning_banner.evaluate(
                "el => getComputedStyle(el).borderLeftColor"
            ),
            "stat-spike-bar backgroundColor": stat_spike_bar.evaluate(
                "el => getComputedStyle(el).backgroundColor"
            ),
            "section-heading color": section_heading.evaluate(
                "el => getComputedStyle(el).color"
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

    heading_overflow_wrap = group.locator("h4").evaluate(
        "el => getComputedStyle(el).overflowWrap"
    )
    assert heading_overflow_wrap == "anywhere"

    # The comparison table keeps its own contained horizontal scroll --
    # overflow was not "fixed" by removing it.
    scroller_overflow_x = group.locator(".scroller").first.evaluate(
        "el => getComputedStyle(el).overflowX"
    )
    assert scroller_overflow_x == "auto"


@pytest.mark.browser
def test_armor_matrix_inactive_orientation_is_unreachable_by_keyboard(
    page: Page, live_server: LiveServer
) -> None:
    """The hidden matrix orientation is out of layout, not merely invisible.

    `display: none` (never `aria-hidden` or `tabindex="-1"`) is what keeps the
    inactive orientation out of both the accessibility tree and the keyboard
    tab order (#131). Proven here by attempting to focus a control inside the
    hidden table directly and confirming focus never lands there.
    """
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_SAME_STAT_UI_EXPORT)
    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    columns_table = group.locator("table.armor-matrix-columns")
    rows_table = group.locator("table.armor-matrix-rows")

    # Fitting desktop panel: columns active, row fallback out of layout.
    page.set_viewport_size({"width": 1440, "height": 900})
    expect(columns_table).to_be_visible()
    expect(rows_table).to_be_hidden()
    assert rows_table.evaluate("el => el.offsetParent") is None
    hidden_focus_result = rows_table.locator("button.approve").first.evaluate(
        "el => { el.focus(); return document.activeElement === el; }"
    )
    assert hidden_focus_result is False, (
        "a button inside the display:none row table accepted focus"
    )

    # Narrow panel: row fallback active, columns out of layout.
    page.set_viewport_size({"width": 390, "height": 844})
    expect(rows_table).to_be_visible()
    expect(columns_table).to_be_hidden()
    assert columns_table.evaluate("el => el.offsetParent") is None
    hidden_focus_result_columns = columns_table.locator("button.approve").first.evaluate(
        "el => { el.focus(); return document.activeElement === el; }"
    )
    assert hidden_focus_result_columns is False, (
        "a button inside the display:none column table accepted focus"
    )
    # The now-active row table's own button remains focusable.
    visible_focus_result = rows_table.locator("button.approve").first.evaluate(
        "el => { el.focus(); return document.activeElement === el; }"
    )
    assert visible_focus_result is True


@pytest.mark.browser
def test_armor_matrix_orientation_flips_at_its_measured_threshold(
    page: Page, live_server: LiveServer
) -> None:
    """The orientation switch is driven by the panel's own width (zoom/reflow).

    A two-member group's measured column budget is 38.5rem (616px). A panel
    just below that must show the row fallback; just above, member columns
    -- proving the flip is a real, width-driven container query rather than
    a fixed desktop/mobile breakpoint (#131).
    """
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_SAME_STAT_UI_EXPORT)
    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    columns_table = group.locator("table.armor-matrix-columns")
    rows_table = group.locator("table.armor-matrix-rows")

    # Comfortably below the 616px budget (measured comparison content box at
    # this viewport: 588px): row fallback.
    page.set_viewport_size({"width": 680, "height": 900})
    expect(rows_table).to_be_visible()
    expect(columns_table).to_be_hidden()
    assert page.evaluate("document.documentElement.scrollWidth") <= 680

    # Comfortably above it (measured comparison content box: 668px): member
    # columns.
    page.set_viewport_size({"width": 760, "height": 900})
    expect(columns_table).to_be_visible()
    expect(rows_table).to_be_hidden()
    assert page.evaluate("document.documentElement.scrollWidth") <= 760

    # And back down again -- the flip is reversible, not a one-way transition.
    page.set_viewport_size({"width": 680, "height": 900})
    expect(rows_table).to_be_visible()
    expect(columns_table).to_be_hidden()


@pytest.mark.browser
def test_armor_verdict_acknowledgement_reflected_after_orientation_flip(
    page: Page, live_server: LiveServer
) -> None:
    """An acknowledged verdict must not go stale in a hidden-then-shown orientation.

    #131's own "likely findings" #1 warned that doubling `state.duplicateRows`
    entries makes a repaint/disable path that only updates the first
    occurrence the likeliest defect, with tests that still index `[0]`
    passing anyway because `[0]` happens to be the visible one at the test's
    width. This test proves the fix by flipping the width *between* the
    acknowledgement and the assertion: approve a proposal member while the
    row fallback is active, then resize so the member-column orientation
    becomes active, and confirm the pressed/enabled state is correctly
    reflected in the now-visible occurrence -- not just the one that was on
    screen at click time. It also checks the now-hidden occurrence directly
    via its DOM attribute (not visibility, since `display: none` is
    legitimate there), proving the repaint is registry-wide.
    """
    authenticate(page, live_server)
    page.locator("#vc-upload-armor").set_input_files(ARMOR_SAME_STAT_UI_EXPORT)
    expect(page.locator("#vc-upload-status-armor")).to_have_text("Accepted")
    expect(page.locator("#vc-view-duplicates")).to_be_enabled()
    page.locator("#vc-view-duplicates").click()

    group = page.locator("article.armor-group")
    columns_table = group.locator("table.armor-matrix-columns")
    rows_table = group.locator("table.armor-matrix-rows")

    # Row fallback active (measured comparison content box 588px, below the
    # two-member 616px column budget).
    page.set_viewport_size({"width": 680, "height": 900})
    expect(rows_table).to_be_visible()
    expect(columns_table).to_be_hidden()

    approve_row = rows_table.locator('[data-member-id="same_stat:8301"] button.approve')
    veto_row = rows_table.locator('[data-member-id="same_stat:8301"] button.veto')
    expect(approve_row).to_be_enabled()
    approve_row.click()
    expect(approve_row).to_have_attribute("aria-pressed", "true")
    expect(veto_row).to_have_attribute("aria-pressed", "false")

    # Flip to the member-column orientation (measured content box 668px,
    # above the budget) *after* the acknowledgement, not before it.
    page.set_viewport_size({"width": 760, "height": 900})
    expect(columns_table).to_be_visible()
    expect(rows_table).to_be_hidden()

    approve_column = columns_table.locator('[data-member-id="same_stat:8301"] button.approve')
    veto_column = columns_table.locator('[data-member-id="same_stat:8301"] button.veto')
    expect(approve_column).to_have_attribute("aria-pressed", "true")
    expect(approve_column).to_be_enabled()
    expect(veto_column).to_have_attribute("aria-pressed", "false")

    # The now-hidden row occurrence stays correctly in sync too -- a
    # registry-wide repaint, not one scoped only to the occurrence that was
    # visible at click time.
    assert approve_row.get_attribute("aria-pressed") == "true"

    # The other member, never acted on, is unaffected in the newly active
    # orientation.
    other_column = columns_table.locator('[data-member-id="same_stat:8302"] button.approve')
    expect(other_column).to_have_attribute("aria-pressed", "false")

    # Flipping back down again still reflects the acknowledged verdict.
    page.set_viewport_size({"width": 680, "height": 900})
    expect(rows_table).to_be_visible()
    expect(columns_table).to_be_hidden()
    expect(approve_row).to_have_attribute("aria-pressed", "true")

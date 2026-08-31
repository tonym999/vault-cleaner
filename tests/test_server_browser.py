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
    expect(headers).to_have_count(9)
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

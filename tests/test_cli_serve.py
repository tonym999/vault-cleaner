from io import StringIO

import pytest

from vault_cleaner import cli
from vault_cleaner.review import OverridesError
from vault_cleaner.server import app as server_app
from vault_cleaner.wishlist import WishlistError


def test_serve_cli_passes_options_and_defaults(monkeypatch):
    calls = []
    monkeypatch.setattr(
        server_app, "run_server", lambda **kwargs: calls.append(kwargs) or 0
    )

    assert cli.main(["serve", "--no-wishlists"]) == 0
    assert calls == [
        {
            "config_path": "config.toml",
            "overrides_path": "data/overrides.json",
            "no_wishlists": True,
            "port": 0,
        }
    ]


def test_serve_cli_passes_explicit_options(monkeypatch):
    calls = []
    monkeypatch.setattr(
        server_app, "run_server", lambda **kwargs: calls.append(kwargs) or 0
    )

    assert cli.main([
        "serve",
        "--config", "elsewhere.toml",
        "--overrides", "custom.json",
        "--no-wishlists",
        "--port", "8123",
    ]) == 0
    assert calls[0] == {
        "config_path": "elsewhere.toml",
        "overrides_path": "custom.json",
        "no_wishlists": True,
        "port": 8123,
    }


@pytest.mark.parametrize("port", ["-1", "65536", "nope"])
def test_serve_cli_rejects_invalid_ports(port):
    with pytest.raises(SystemExit) as raised:
        cli.main(["serve", "--port", port])
    assert raised.value.code == 2


def test_prewarm_loads_wishlists_then_manifest(monkeypatch):
    events = []
    cfg = {
        "wishlists": {"sources": {"one": "https://example.test/one"}},
        "paths": {"manifest_cache_dir": "manifest-cache"},
        "manifest": {"max_age_days": 30},
    }
    monkeypatch.setattr(server_app, "load_config", lambda path: events.append(("config", path)) or cfg)
    monkeypatch.setattr(
        server_app,
        "load_all_with_sources",
        lambda value: events.append(("wishlists", value)),
    )
    monkeypatch.setattr(
        server_app,
        "load_perk_map_data",
        lambda path, age: events.append(("manifest", path, age)),
    )

    assert server_app.prewarm("chosen.toml") is cfg
    assert events == [
        ("config", "chosen.toml"),
        ("wishlists", cfg),
        ("manifest", "manifest-cache", 30),
    ]


def test_prewarm_skips_external_loaders_when_sources_are_empty(monkeypatch):
    cfg = {"wishlists": {"sources": {}}}
    monkeypatch.setattr(server_app, "load_config", lambda _path: cfg)
    monkeypatch.setattr(
        server_app,
        "load_all_with_sources",
        lambda _cfg: pytest.fail("empty wishlist sources were loaded"),
    )
    monkeypatch.setattr(
        server_app,
        "load_perk_map_data",
        lambda *_args: pytest.fail("manifest was loaded for empty wishlist sources"),
    )

    assert server_app.prewarm("chosen.toml") is cfg


def test_prewarm_failure_happens_before_binding(monkeypatch):
    monkeypatch.setattr(
        server_app,
        "prewarm",
        lambda _path: (_ for _ in ()).throw(WishlistError("offline")),
    )
    monkeypatch.setattr(
        server_app,
        "build_server",
        lambda *_args, **_kwargs: pytest.fail("socket was bound after pre-warm failed"),
    )

    with pytest.raises(WishlistError, match="offline"):
        server_app.run_server(
            config_path="config.toml",
            no_wishlists=False,
            port=0,
        )


def test_serve_cli_turns_prewarm_failure_into_clean_exit(monkeypatch, capsys):
    monkeypatch.setattr(
        server_app,
        "run_server",
        lambda **_kwargs: (_ for _ in ()).throw(WishlistError("offline")),
    )

    assert cli.main(["serve"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: offline\n")
    assert "--no-wishlists" in captured.err


@pytest.mark.parametrize("message", ["not valid JSON", "invalid UTF-8"])
def test_serve_cli_turns_overrides_startup_failure_into_clean_exit(
    monkeypatch, capsys, message
):
    monkeypatch.setattr(
        server_app,
        "run_server",
        lambda **_kwargs: (_ for _ in ()).throw(OverridesError(message)),
    )

    assert cli.main(["serve", "--no-wishlists"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"error: {message}\n"


def test_run_server_prints_working_bootstrap_shape_and_closes(monkeypatch, tmp_path):
    events = []
    output = StringIO()

    class FakeServer:
        def serve_forever(self):
            events.append("served")

        def server_close(self):
            events.append("server-closed")

    def fake_build(session, port):
        assert port == 0
        assert session.config_path == "config.toml"
        assert session.overrides_path == str(tmp_path / "overrides.json")
        assert session.no_wishlists is True
        session.configure_bound_port(54321)
        events.append("bound")
        return FakeServer()

    monkeypatch.setattr(server_app, "load_config", lambda _path: {})
    monkeypatch.setattr(server_app, "build_server", fake_build)
    monkeypatch.setattr(
        server_app.Session,
        "close",
        lambda _self: events.append("session-closed"),
    )

    assert server_app.run_server(
        config_path="config.toml",
        overrides_path=str(tmp_path / "overrides.json"),
        no_wishlists=True,
        port=0,
        stdout=output,
    ) == 0

    url = output.getvalue().strip()
    assert url.startswith("http://127.0.0.1:54321/bootstrap?token=")
    assert len(url.rsplit("=", 1)[1]) >= 32
    assert events == ["bound", "served", "session-closed", "server-closed"]


def test_run_server_closes_session_when_binding_fails(monkeypatch, tmp_path):
    events = []
    monkeypatch.setattr(server_app, "load_config", lambda _path: {})
    monkeypatch.setattr(
        server_app,
        "build_server",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("bind failed")),
    )
    monkeypatch.setattr(
        server_app.Session,
        "close",
        lambda _self: events.append("session-closed"),
    )

    with pytest.raises(RuntimeError, match="bind failed"):
        server_app.run_server(
            config_path="config.toml",
            overrides_path=str(tmp_path / "overrides.json"),
            no_wishlists=True,
            port=0,
        )

    assert events == ["session-closed"]


def test_run_server_closes_server_when_session_close_fails(monkeypatch, tmp_path):
    events = []

    class FakeServer:
        def serve_forever(self):
            events.append("served")

        def server_close(self):
            events.append("server-closed")

    def fake_build(session, port):
        session.configure_bound_port(54321)
        return FakeServer()

    def fail_close(_self):
        events.append("session-close-failed")
        raise RuntimeError("session cleanup failed")

    monkeypatch.setattr(server_app, "load_config", lambda _path: {})
    monkeypatch.setattr(server_app, "build_server", fake_build)
    monkeypatch.setattr(server_app.Session, "close", fail_close)

    with pytest.raises(RuntimeError, match="session cleanup failed"):
        server_app.run_server(
            config_path="config.toml",
            overrides_path=str(tmp_path / "overrides.json"),
            no_wishlists=True,
            port=0,
        )

    assert events == ["served", "session-close-failed", "server-closed"]


def test_run_server_rejects_invalid_overrides_before_binding(monkeypatch, tmp_path):
    overrides = tmp_path / "overrides.json"
    overrides.write_bytes(b"\xff")
    monkeypatch.setattr(server_app, "load_config", lambda _path: {})
    monkeypatch.setattr(
        server_app,
        "build_server",
        lambda *_args, **_kwargs: pytest.fail("socket was bound before overrides validation"),
    )

    with pytest.raises(OverridesError, match="invalid UTF-8"):
        server_app.run_server(
            config_path="config.toml",
            overrides_path=str(overrides),
            no_wishlists=True,
            port=0,
        )


def test_run_server_cleans_up_after_ctrl_c(monkeypatch, tmp_path):
    events = []
    output = StringIO()

    class KeyboardInterruptServer:
        def serve_forever(self):
            events.append("served")
            raise KeyboardInterrupt

        def server_close(self):
            events.append("server-closed")

    def fake_build(session, port):
        session.configure_bound_port(54321)
        return KeyboardInterruptServer()

    monkeypatch.setattr(server_app, "load_config", lambda _path: {})
    monkeypatch.setattr(server_app, "build_server", fake_build)
    monkeypatch.setattr(
        server_app.Session,
        "close",
        lambda _self: events.append("session-closed"),
    )

    assert server_app.run_server(
        config_path="config.toml",
        overrides_path=str(tmp_path / "overrides.json"),
        no_wishlists=True,
        port=0,
        stdout=output,
    ) == 0
    assert events == ["served", "session-closed", "server-closed"]

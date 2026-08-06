from types import SimpleNamespace

import pytest

from unmanic.libs import plugins as plugins_module


class DummyLogger:
    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def make_handler():
    handler = plugins_module.PluginsHandler.__new__(plugins_module.PluginsHandler)
    handler.logger = DummyLogger()
    return handler


def valid_repo_data():
    return {
        "repo": {"name": "Official Plugins", "repo_data_directory": "https://example.test/plugins"},
        "plugins": [],
    }


@pytest.mark.unittest
def test_default_repo_falls_back_to_direct_fetch_when_relay_returns_failure(monkeypatch):
    class FailedRelaySession:
        def get_installation_uuid(self):
            return "installation"

        def get_supporter_level(self):
            return 0

        def api_get(self, *args):
            return {"messages": [], "success": False}, 200

    response = SimpleNamespace(
        raise_for_status=lambda: None,
        json=valid_repo_data,
    )
    monkeypatch.setattr(plugins_module, "Session", FailedRelaySession)
    monkeypatch.setattr(plugins_module.requests, "get", lambda *args, **kwargs: response)

    result = make_handler().fetch_remote_repo_data("default")

    assert result == valid_repo_data()


@pytest.mark.unittest
def test_failed_refresh_does_not_replace_existing_cache(monkeypatch, tmp_path):
    handler = make_handler()
    handler.settings = SimpleNamespace(get_plugins_path=lambda: str(tmp_path))
    handler.get_plugin_repos = lambda: [{"path": "default"}]
    handler.fetch_remote_repo_data = lambda repo_path: False

    repo_cache = handler.get_repo_cache_file(handler.get_plugin_repo_id("default"))
    with open(repo_cache, "w") as cache_file:
        cache_file.write('{"repo": {"name": "cached"}, "plugins": []}')

    assert handler.update_plugin_repos() is False
    with open(repo_cache) as cache_file:
        assert '"cached"' in cache_file.read()

import threading

from unmanic.libs import libraryscanner


def _run_scan(monkeypatch, *, web_scanner, file_scanner, file_monitor):
    calls = {'web': [], 'files': []}

    class FakeLibrary:
        def __init__(self, library_id):
            self.library_id = library_id

        @staticmethod
        def get_all_libraries():
            return [{'id': 1}]

        def get_enable_remote_only(self):
            return False

        def get_enable_web_scanner(self):
            return web_scanner

        def get_enable_scanner(self):
            return file_scanner

        def get_enable_inotify(self):
            return file_monitor

        def get_id(self):
            return self.library_id

        def get_name(self):
            return 'Source'

        def get_path(self):
            return '/library/source'

    monkeypatch.setattr(libraryscanner, 'Library', FakeLibrary)
    manager = object.__new__(libraryscanner.LibraryScannerManager)
    manager.logger = type('FakeLogger', (), {'info': lambda *_args: None})()
    manager.abort_flag = threading.Event()
    manager.scan_cancel_flag = threading.Event()
    manager.system_configuration_is_valid = lambda: True
    manager.wait_if_paused_or_cancelled = lambda: True
    manager.set_current_library = lambda *_args, **_kwargs: None
    manager.scan_web_library = lambda library: calls['web'].append(library.library_id)
    manager.scan_library_path = lambda name, path, library_id: calls['files'].append(
        (name, path, library_id)
    )

    manager.run_scheduled_scan()
    return calls


def test_enabled_web_scanner_downloads_then_scans_the_local_library(monkeypatch):
    calls = _run_scan(
        monkeypatch,
        web_scanner=True,
        file_scanner=False,
        file_monitor=True,
    )

    assert calls == {'web': [1], 'files': [('Source', '/library/source', 1)]}


def test_disabled_scanners_do_not_start_a_library_scan(monkeypatch):
    calls = _run_scan(
        monkeypatch,
        web_scanner=False,
        file_scanner=False,
        file_monitor=False,
    )

    assert calls == {'web': [], 'files': []}


def test_existing_local_scanner_runs_without_enabling_web_scanner(monkeypatch):
    calls = _run_scan(
        monkeypatch,
        web_scanner=False,
        file_scanner=True,
        file_monitor=False,
    )

    assert calls == {'web': [], 'files': [('Source', '/library/source', 1)]}

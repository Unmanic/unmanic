import json

from unmanic.libs import library as library_module
from unmanic.libs import plugins as plugins_module
from unmanic.webserver.helpers import settings


class FakeLibrary:
    def __init__(self, **values):
        self.values = values

    def __getattr__(self, name):
        if name == 'save':
            return lambda: True
        if name.startswith('get_'):
            key = name[4:]
            return lambda: self.values.get(key)
        if name.startswith('set_'):
            key = name[4:]
            return lambda value: self.values.__setitem__(key, value)
        raise AttributeError(name)


def test_library_settings_response_hides_password_and_keeps_scanner_flags():
    library = FakeLibrary(
        id=4,
        name='Source',
        path='/library/source',
        locked=False,
        enable_remote_only=False,
        enable_scanner=False,
        enable_inotify=True,
        enable_web_scanner=True,
        web_url='https://media.example/library/',
        web_username='scanner',
        web_password='secret',
        priority_score=0,
        tags=[],
    )

    serialized = settings.serialize_library_settings(library)

    assert serialized['enable_inotify'] is True
    assert serialized['enable_web_scanner'] is True
    assert serialized['web_password_set'] is True
    assert 'web_password' not in serialized
    assert 'secret' not in json.dumps(serialized)


def test_library_settings_save_preserves_or_clears_password_explicitly(monkeypatch):
    library = FakeLibrary(
        name='Source', path='/library/source', locked=False,
        enable_remote_only=False, enable_scanner=False, enable_inotify=True,
        enable_web_scanner=False, web_url='', web_username='', web_password='saved',
        priority_score=0, tags=[],
    )
    monkeypatch.setattr(settings, 'Library', lambda _library_id: library)

    settings.save_library_config(4, {'enable_web_scanner': True}, {})
    assert library.values['web_password'] == 'saved'
    assert library.values['enable_inotify'] is True

    settings.save_library_config(4, {'clear_web_password': True}, {})
    assert library.values['web_password'] == ''


def test_library_export_does_not_include_web_password(monkeypatch):
    library = FakeLibrary(
        name='Source', path='/library/source', locked=False,
        enable_remote_only=False, enable_scanner=False, enable_inotify=True,
        enable_web_scanner=True, web_url='https://media.example/library/',
        web_username='scanner', web_password='secret', tags=[],
    )
    library.get_enabled_plugins = lambda include_settings=False: []

    class FakePluginHandler:
        def get_plugin_types_with_flows(self):
            return []

    export = library_module.Library.export
    monkeypatch.setattr(library_module, 'Library', lambda _library_id: library)
    monkeypatch.setattr(plugins_module, 'PluginsHandler', FakePluginHandler)

    result = export(4)

    assert 'web_password' not in result['library_config']
    assert 'secret' not in json.dumps(result)

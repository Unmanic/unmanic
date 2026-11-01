#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import asyncio
import queue
from pathlib import Path
import threading
from types import SimpleNamespace

from peewee import SqliteDatabase
import pytest

from unmanic.libs import library_workload, libraryscanner, plugins, postprocessor
from unmanic.libs.unmodels.libraries import Libraries, LibraryTags
from unmanic.libs.unmodels.tags import Tags
from unmanic.libs.unmodels.tasks import Tasks
from unmanic.libs.unplugins import plugin_types
from unmanic.webserver.api_v2.pending_api import ApiPendingHandler
from unmanic.webserver.api_v2.schema.schemas import RequestLibraryWorkloadSchema


@pytest.fixture
def database():
    database = SqliteDatabase(':memory:')
    with database.bind_ctx([Libraries, Tasks, Tags, LibraryTags]):
        database.create_tables([Libraries, Tasks, Tags, LibraryTags])
        Libraries.create(id=1, name='Source', path='/source')
        Libraries.create(id=2, name='Processing', path='/processing')
        yield database
    database.close()


def scanner(state='idle'):
    return SimpleNamespace(get_scan_status=lambda: {'state': state})


def test_query_counts_every_outstanding_stage_and_filters_libraries(database):
    for state in (*library_workload.ACTIVE_STATES, 'complete'):
        Tasks.create(abspath='/file-' + state, library_id=1, status=state)
    Tasks.create(abspath='/other', library_id=2, status='pending')
    workload = library_workload.get_library_workload([1], scanner())
    assert not workload['idle']
    assert workload['libraries'] == [{'library_id': 1, 'outstanding_tasks': 4, 'idle': False,
                                     'tasks': {state: 1 for state in library_workload.ACTIVE_STATES}}]
    assert len(library_workload.get_library_workload([], scanner())['libraries']) == 2


@pytest.mark.parametrize('state', ['scheduled', 'scanning', 'paused', 'cancelling'])
def test_a_scan_blocks_idle_even_when_selected_libraries_have_no_tasks(database, state):
    assert not library_workload.get_library_workload([1], scanner(state))['idle']
    assert library_workload.get_library_workload([1], scanner())['idle']


@pytest.mark.parametrize('ids', [[True], [-1], ['1'], '1', [999]])
def test_invalid_or_unknown_libraries_do_not_look_idle(database, ids):
    with pytest.raises(ValueError):
        library_workload.get_library_workload(ids, scanner())


def test_processed_task_is_outstanding_until_cleanup(database):
    task = Tasks.create(abspath='/output', library_id=2, status='processed', success=True)
    assert not library_workload.get_library_workload([2], scanner())['idle']
    task.delete_instance()
    assert library_workload.get_library_workload([2], scanner())['idle']


def test_missing_scanner_does_not_report_idle(database, monkeypatch):
    from unmanic.libs.uiserver import UnmanicRunningTreads
    monkeypatch.setattr(UnmanicRunningTreads, 'get_unmanic_running_thread', lambda *args: None)
    assert library_workload.get_library_workload([1])['scan_state'] == 'unavailable'
    assert not library_workload.get_library_workload([1])['idle']


def test_notification_reports_only_idle_libraries(database, monkeypatch):
    events = []
    monkeypatch.setattr(plugins, 'PluginsHandler', lambda: SimpleNamespace(
        run_event_plugins_for_plugin_type=lambda name, data: events.append((name, data))))
    Tasks.create(abspath='/busy', library_id=2, status='processed')
    library_workload.notify_library_workload_idle(scanner=scanner('scanning'))
    assert events == []
    library_workload.notify_library_workload_idle(scanner=scanner())
    assert events[0][0] == 'events.library_workload_idle'
    assert events[0][1]['library_ids'] == [1]
    assert not events[0][1]['workload']['idle']


def test_full_scan_notifies_after_idle_even_without_any_tasks(database, monkeypatch):
    events = []
    monkeypatch.setattr(plugins, 'PluginsHandler', lambda: SimpleNamespace(
        run_event_plugins_for_plugin_type=lambda name, data: events.append((name, data))))
    manager = object.__new__(libraryscanner.LibraryScannerManager)
    manager.scan_state_lock = threading.RLock()
    manager.abort_flag = threading.Event()
    manager.scan_requested = True
    manager.scan_state = 'scheduled'
    manager.scan_pause_flag = threading.Event()
    manager.scan_cancel_flag = threading.Event()
    manager.files_to_test = queue.Queue()
    manager.files_to_process = queue.Queue()
    manager.current_library_id = manager.current_library_name = manager.current_library_path = None
    manager.run_scheduled_scan = lambda: None
    manager.logger = SimpleNamespace(exception=lambda *args: pytest.fail('Notification failed'))
    manager.execute_scan_request()
    assert manager.get_scan_status()['state'] == 'idle'
    assert events[0][1]['reason'] == 'scan_complete'
    assert events[0][1]['library_ids'] == [1, 2]


@pytest.mark.parametrize('task_type', ['local', 'remote'])
def test_postprocessor_notifies_only_after_task_cleanup(database, monkeypatch, task_type):
    row = Tasks.create(abspath='/output', library_id=2, status='processed', success=True)
    events = []
    abort = threading.Event()
    def remove():
        row.delete_instance()
        abort.set()
    def complete(status):
        row.status = status
        row.save()
        abort.set()
    task = SimpleNamespace(get_task_library_id=lambda: 2, get_task_id=lambda: row.id,
                           get_task_type=lambda: task_type, get_cache_path=lambda: '/cache',
                           get_source_data=lambda: {}, get_source_abspath=lambda: '/output', delete=remove, set_status=complete)
    class Handler:
        def run_event_plugins_for_plugin_type(self, name, data):
            if name == 'events.library_workload_idle':
                assert not Tasks.select().where(Tasks.id == row.id, Tasks.status != 'complete').exists()
            events.append((name, data))
    monkeypatch.setattr(plugins, 'PluginsHandler', Handler)
    monkeypatch.setattr(postprocessor, 'PluginsHandler', Handler)
    from unmanic.libs.uiserver import UnmanicRunningTreads
    monkeypatch.setattr(UnmanicRunningTreads, 'get_unmanic_running_thread', lambda *args: scanner())
    processor = object.__new__(postprocessor.PostProcessor)
    processor.abort_flag = abort
    processor.event = SimpleNamespace(wait=lambda *args: None)
    processor.logger = SimpleNamespace(info=lambda *args: None,
                                      exception=lambda *args: pytest.fail('Post-processing failed'))
    processor.system_configuration_is_valid = lambda: True
    processor.task_queue = SimpleNamespace(task_list_processed_is_empty=lambda: False,
                                          get_next_processed_tasks=lambda: task)
    processor.post_process_file = processor.write_history_log = processor.commit_task_metadata = lambda: None
    processor.post_process_remote_file = processor.dump_history_log = lambda: None
    processor.run()
    assert events[-1][0] == 'events.library_workload_idle'
    assert events[-1][1]['library_ids'] == [2]


def test_query_api_and_registered_plugin_event(database):
    written = []
    handler = SimpleNamespace(read_json_request=lambda schema: schema.load({'library_ids': [2]}),
                              library_scanner=scanner(), write=written.append)
    asyncio.run(ApiPendingHandler.get_library_workload(handler))
    assert written[0]['idle']
    assert written[0]['libraries'][0]['library_id'] == 2
    assert plugin_types.grab_module('events.library_workload_idle').plugin_runner() == 'emit_library_workload_idle'
    with pytest.raises(Exception):
        RequestLibraryWorkloadSchema().load({'library_ids': [True]})


def test_scan_finishing_during_query_does_not_hide_work_created_after_count(database):
    states = iter(['scanning', 'idle'])
    manager = SimpleNamespace(get_scan_status=lambda: {'state': next(states)})
    assert not library_workload.get_library_workload([1], manager)['idle']


@pytest.mark.parametrize('selection', [[], [2], [2, 2]])
def test_library_dependency_selection_persists_and_survives_reload(database, selection):
    from unmanic.libs.library import Library
    library = Library(1)
    assert library.get_wait_for_library_ids() == []
    library.set_wait_for_library_ids(selection)
    library.model.save()
    assert Library(1).get_wait_for_library_ids() == sorted(set(selection))


@pytest.mark.parametrize('selection', [[1], [999], [True], ['2'], [-1], None])
def test_library_dependency_selection_rejects_self_missing_or_invalid_ids(database, selection):
    from unmanic.libs.library import Library, LibraryDependencyError
    with pytest.raises(LibraryDependencyError):
        Library(1).set_wait_for_library_ids(selection)
    assert Library(1).get_wait_for_library_ids() == []


def test_library_config_partial_update_preserves_dependency_selection(database, monkeypatch):
    from unmanic.libs.library import Library
    from unmanic.webserver.helpers import settings
    library = Library(2)
    library.set_wait_for_library_ids([1])
    library.model.save()
    assert settings.save_library_config(2, {'name': 'Renamed'})
    assert Library(2).get_wait_for_library_ids() == [1]
    assert settings.save_library_config(2, {'wait_for_library_ids': []})
    assert Library(2).get_wait_for_library_ids() == []



def test_invalid_dependency_selection_does_not_create_a_library(database):
    from unmanic.libs.library import LibraryDependencyError
    from unmanic.webserver.helpers import settings
    with pytest.raises(LibraryDependencyError):
        settings.save_library_config(0, {'name': 'Invalid', 'path': '/invalid', 'wait_for_library_ids': [999]})
    assert Libraries.select().count() == 2


def test_library_config_read_and_write_exposes_selected_ids(database, monkeypatch):
    from unmanic.libs.library import Library
    from unmanic.webserver.api_v2.settings_api import ApiSettingsHandler
    written = []
    monkeypatch.setattr(Library, 'get_enabled_plugins', lambda *args: [])
    library = Library(2)
    library.set_wait_for_library_ids([1])
    library.model.save()
    handler = SimpleNamespace(read_json_request=lambda schema: {'id': 2},
                              build_response=lambda schema, data: data,
                              write_success=written.append)
    asyncio.run(ApiSettingsHandler.read_library_config(handler))
    assert written[0]['library_config']['wait_for_library_ids'] == [1]


@pytest.fixture
def scan_manager():
    manager = object.__new__(libraryscanner.LibraryScannerManager)
    manager.scan_state_lock = threading.RLock()
    manager.scan_state = 'idle'
    manager.current_library_id = manager.current_library_name = manager.current_library_path = None
    manager.scan_requested = manager.scan_active = False
    manager.scan_pause_flag = threading.Event()
    manager.scan_cancel_flag = threading.Event()
    manager.abort_flag = threading.Event()
    manager.pending_scan_library_ids = set()
    manager.scan_library_ids = None
    manager.scanned_library_ids = []
    manager.files_to_test = queue.Queue()
    manager.files_to_process = queue.Queue()
    manager.logger = SimpleNamespace(info=lambda *args: None, warning=lambda *args: None,
                                     exception=lambda *args: pytest.fail('Scanner failed'))
    return manager


def test_targeted_scans_merge_queued_requests_and_keep_requests_while_active(database, scan_manager, monkeypatch):
    from unmanic.libs.library import Library
    from unmanic.libs import library_workload
    monkeypatch.setattr(library_workload, 'notify_library_workload_idle', lambda **kwargs: None)
    monkeypatch.setattr(Library, 'get_all_libraries', lambda: [{'id': 1}, {'id': 2}])
    Libraries.update(enable_scanner=True).execute()
    manager = scan_manager
    manager.system_configuration_is_valid = lambda: True
    manager.wait_if_paused_or_cancelled = lambda: True
    scanned = []
    events = []
    monkeypatch.setattr(library_workload, 'notify_library_workload_idle', lambda **kwargs: events.append(kwargs))
    def scan(name, path, library_id):
        scanned.append(library_id)
        if len(scanned) == 1:
            assert manager.request_scan([2])
            assert manager.request_scan([2])
            assert not manager.request_scan()
    manager.scan_library_path = scan
    assert manager.request_scan([1])
    assert manager.request_scan([1])
    manager.execute_scan_request()
    assert scanned == [1]
    assert manager.get_scan_status()['state'] == 'scheduled'
    assert manager.scan_library_ids == {2}
    manager.execute_scan_request()
    assert scanned == [1, 2]
    assert events[-1]['scanned_library_ids'] == [1, 2]
    assert manager.get_scan_status()['state'] == 'idle'


@pytest.mark.parametrize('selection', [[], [True], ['1'], [999], [-1]])
def test_invalid_targeted_scans_are_rejected_without_scheduling(database, scan_manager, selection):
    with pytest.raises(ValueError):
        scan_manager.request_scan(selection)
    assert scan_manager.get_scan_status()['state'] == 'idle'


def test_targeted_scan_cancel_clears_followup_requests(database, scan_manager, monkeypatch):
    monkeypatch.setattr(library_workload, 'notify_library_workload_idle', lambda **kwargs: None)
    assert scan_manager.request_scan([1])
    def scan():
        assert scan_manager.request_scan([2])
        assert scan_manager.cancel_scan()
        assert not scan_manager.request_scan([2])
    scan_manager.run_scheduled_scan = scan
    scan_manager.execute_scan_request()
    assert scan_manager.get_scan_status()['state'] == 'idle'
    assert not scan_manager.should_start_scan()


def test_targeted_scan_keeps_scanner_enablement_and_remote_only_constraints(database, scan_manager, monkeypatch):
    from unmanic.libs.library import Library
    monkeypatch.setattr(library_workload, 'notify_library_workload_idle', lambda **kwargs: None)
    monkeypatch.setattr(Library, 'get_all_libraries', lambda: [{'id': 1}, {'id': 2}])
    Libraries.update(enable_scanner=True, enable_remote_only=True).where(Libraries.id == 1).execute()
    scan_manager.system_configuration_is_valid = lambda: True
    scan_manager.wait_if_paused_or_cancelled = lambda: True
    scan_manager.scan_library_path = lambda *args: pytest.fail('Disabled/API-only Library was scanned')
    assert scan_manager.request_scan([1, 2])
    scan_manager.execute_scan_request()


def test_legacy_empty_body_scan_api_preserves_full_scan_request(database, scan_manager):
    handler = SimpleNamespace(library_scanner=scan_manager, request=SimpleNamespace(body=b''),
                              write_success=lambda: None)
    asyncio.run(ApiPendingHandler.trigger_library_rescan(handler))
    assert scan_manager.scan_library_ids is None
    assert scan_manager.should_start_scan()



def test_targeted_requests_merge_while_paused_without_resuming_the_scan(database, scan_manager):
    assert scan_manager.request_scan([1])
    assert scan_manager.pause_scan()
    assert scan_manager.request_scan([2])
    assert scan_manager.scan_library_ids == {1, 2}
    assert scan_manager.get_scan_status()['state'] == 'paused'
    assert not scan_manager.should_start_scan()
    assert scan_manager.resume_scan()
    assert scan_manager.should_start_scan()


def test_scan_api_accepts_target_ids_and_rejects_unknown_ids(database, scan_manager):
    from unmanic.webserver.api_v2.schema.schemas import RequestLibraryScanSchema
    written, errors = [], []
    handler = SimpleNamespace(library_scanner=scan_manager, request=SimpleNamespace(body=b'{"library_ids":[2]}'),
                              read_json_request=lambda schema: schema.load({'library_ids': [2]}),
                              write_success=lambda: written.append(True),
                              STATUS_ERROR_EXTERNAL=400, set_status=lambda *args, **kw: errors.append(args[0]),
                              write_error=lambda: None)
    asyncio.run(ApiPendingHandler.trigger_library_rescan(handler))
    assert written == [True]
    assert scan_manager.scan_library_ids == {2}
    handler.read_json_request = lambda schema: schema.load({'library_ids': [999]})
    asyncio.run(ApiPendingHandler.trigger_library_rescan(handler))
    assert errors == [400]
    assert RequestLibraryScanSchema().load({}) == {'library_ids': None}



def test_cancelled_scan_notification_is_distinct_and_followup_ids_are_discarded(database, scan_manager, monkeypatch):
    notifications = []
    monkeypatch.setattr(library_workload, 'notify_library_workload_idle', lambda **kwargs: notifications.append(kwargs))
    assert scan_manager.request_scan([1])
    def scan():
        scan_manager.scanned_library_ids.append(1)
        assert scan_manager.request_scan([2])
        assert scan_manager.cancel_scan()
    scan_manager.run_scheduled_scan = scan
    scan_manager.execute_scan_request()
    assert notifications[-1]['reason'] == 'scan_cancelled'
    assert not scan_manager.pending_scan_library_ids
    assert not scan_manager.should_start_scan()



def test_existing_library_database_receives_empty_dependency_default(tmp_path):
    import sqlite3
    from unmanic.libs.db_migrate import Migrations
    path = tmp_path / 'unmanic.db'
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE libraries (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, path TEXT NOT NULL)')
        connection.execute("INSERT INTO libraries VALUES (1, 'Existing', '/existing')")
    migrations = Migrations({'TYPE': 'SQLITE', 'FILE': str(path),
                             'MIGRATIONS_DIR': str(Path(__file__).parents[1] / 'unmanic/migrations_v1'),
                             'MIGRATIONS_HISTORY_VERSION': 'v1'})
    from unmanic.libs.unmodels.lib import db
    previous = db.obj
    db.initialize(migrations.database)
    try:
        migrations.update_schema()
    finally:
        migrations.database.close()
        db.initialize(previous)
    with sqlite3.connect(path) as connection:
        assert connection.execute('SELECT name, path FROM libraries').fetchall() == [
            ('Existing', '/existing')]
        # An older backend writes its known fields and ignores the new column.
        fields = [field for field in Libraries._meta.sorted_fields if field.name != 'wait_for_library_ids']
        values = {'id': 2, 'name': 'Older client', 'path': '/older'}
        for field in fields:
            if field.name not in values:
                values[field.name] = field.default() if callable(field.default) else field.default
        columns = ','.join(field.column_name for field in fields)
        parameters = ','.join('?' for field in fields)
        connection.execute('INSERT INTO libraries (' + columns + ') VALUES (' + parameters + ')',
                           [values[field.name] for field in fields])
        connection.commit()
    from unmanic.libs.library import Library
    with Libraries.bind_ctx(migrations.database):
        assert Library(1).get_wait_for_library_ids() == []
        assert Library(2).get_wait_for_library_ids() == []
    migrations.database.close()


def test_plugin_library_selector_preserves_id_list_in_config_form(monkeypatch):
    from unmanic.libs.session import Session
    from unmanic.webserver.helpers import plugins as plugin_settings
    monkeypatch.setattr(Session, 'register_unmanic', lambda self: None)
    monkeypatch.setattr(plugin_settings, 'PluginExecutor', lambda: SimpleNamespace(
        get_plugin_settings=lambda *args, **kwargs: ({'targets': [2]}, {
            'targets': {'input_type': 'library_select', 'label': 'Libraries to scan'}})))
    form = plugin_settings.get_plugin_settings('completion', library_id=1)
    assert form[0]['input_type'] == 'library_select'
    assert form[0]['value'] == [2]

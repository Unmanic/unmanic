#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.metadata.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     03 Feb 2026

    Copyright:
           Copyright (C) Josh Sunnex - All Rights Reserved

           Permission is hereby granted, free of charge, to any person obtaining a copy
           of this software and associated documentation files (the "Software"), to deal
           in the Software without restriction, including without limitation the rights
           to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
           copies of the Software, and to permit persons to whom the Software is
           furnished to do so, subject to the following conditions:

           The above copyright notice and this permission notice shall be included in all
           copies or substantial portions of the Software.

           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""

import json
import os
import threading
import time
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime

from unmanic.libs import common
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.unmodels import FileMetadata, FileMetadataPaths, TaskMetadata, Tasks
from peewee import fn


class UnmanicFileMetadata:
    """
    Thread-safe metadata access for plugins.
    """

    MAX_PLUGIN_JSON_BYTES = 32 * 1024
    CACHE_MAX_ENTRIES = 2000
    CACHE_TTL_SECONDS = 300
    CACHE_PRUNE_INTERVAL_SECONDS = 60

    _lock = threading.RLock()
    _ctx = threading.local()
    _logger = UnmanicLogging.get_logger(name="UnmanicFileMetadata")
    _main_pid = os.getpid()

    _task_cache = {}
    _path_cache = OrderedDict()
    _last_prune = 0

    @classmethod
    def _ensure_main_process(cls):
        if os.getpid() != cls._main_pid:
            raise RuntimeError("UnmanicFileMetadata is only available in the main process")

    @classmethod
    def bind_runner_context(cls, plugin_id, task_id=None, path=None):
        cls._ensure_main_process()
        cls._ctx.plugin_id = plugin_id
        cls._ctx.task_id = task_id
        cls._ctx.path = path

    @classmethod
    def clear_context(cls):
        cls._ctx.plugin_id = None
        cls._ctx.task_id = None
        cls._ctx.path = None

    @classmethod
    def _get_context(cls):
        plugin_id = getattr(cls._ctx, 'plugin_id', None)
        if not plugin_id:
            raise RuntimeError("Metadata context not bound to a plugin_id")
        task_id = getattr(cls._ctx, 'task_id', None)
        path = getattr(cls._ctx, 'path', None)
        return plugin_id, task_id, path

    @classmethod
    def _load_json_dict(cls, raw_json):
        if not raw_json:
            return {}
        try:
            data = json.loads(raw_json)
        except Exception:
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    @classmethod
    def _dump_json_dict(cls, data):
        if not isinstance(data, dict):
            raise ValueError("Metadata JSON must be a dict")
        return json.dumps(data)

    @classmethod
    def _enforce_plugin_size_limit(cls, plugin_data):
        encoded = json.dumps(plugin_data).encode('utf-8')
        if len(encoded) > cls.MAX_PLUGIN_JSON_BYTES:
            raise ValueError("Plugin metadata exceeds size limit ({} bytes)".format(cls.MAX_PLUGIN_JSON_BYTES))

    @classmethod
    def _ensure_task_cache_entry(cls, task_id):
        entry = cls._task_cache.get(task_id)
        if entry is None:
            entry = {
                'staged': {},
                'staged_loaded': False,
                'file': {},
                'file_loaded': False,
                'source_path': None,
                'fingerprint': None,
                'fingerprint_algo': None,
                'source_plugins': set(),
                'source_fingerprint': None,
                'source_fingerprint_algo': None,
                'source_path_at_set': None,
            }
            cls._task_cache[task_id] = entry
        return entry

    @classmethod
    def _load_task_metadata(cls, task_id):
        entry = cls._ensure_task_cache_entry(task_id)
        if entry['staged_loaded']:
            return entry['staged']

        try:
            row = TaskMetadata.get(TaskMetadata.task == task_id)
            entry['staged'] = cls._load_json_dict(row.json_blob)
        except TaskMetadata.DoesNotExist:
            entry['staged'] = {}
        entry['staged_loaded'] = True
        return entry['staged']

    @classmethod
    def _normalize_scoped_staged(cls, staged):
        if not isinstance(staged, dict):
            return {'source': {}, 'destination': {}, '__meta__': {}}
        if 'source' in staged or 'destination' in staged or '__meta__' in staged:
            source = staged.get('source') or {}
            destination = staged.get('destination') or {}
            meta = staged.get('__meta__') or {}
            if not isinstance(source, dict):
                source = {}
            if not isinstance(destination, dict):
                destination = {}
            if not isinstance(meta, dict):
                meta = {}
            return {'source': source, 'destination': destination, '__meta__': meta}

        # Legacy format: plugin_id -> dict. Treat as source scope.
        return {'source': staged, 'destination': {}, '__meta__': {}}

    @classmethod
    def _load_task_source_path(cls, task_id):
        entry = cls._ensure_task_cache_entry(task_id)
        if entry['source_path']:
            return entry['source_path']
        try:
            task = Tasks.get_by_id(task_id)
            entry['source_path'] = task.abspath
        except Exception:
            entry['source_path'] = None
        return entry['source_path']

    @classmethod
    def _load_file_metadata_for_task(cls, task_id):
        entry = cls._ensure_task_cache_entry(task_id)
        if entry['file_loaded']:
            return entry['file']

        source_path = cls._load_task_source_path(task_id)
        if not source_path or not os.path.exists(source_path):
            entry['file'] = {}
            entry['file_loaded'] = True
            return entry['file']

        fingerprint, algo = common.get_file_fingerprint(source_path)
        entry['fingerprint'] = fingerprint
        entry['fingerprint_algo'] = algo

        try:
            row = FileMetadata.get(FileMetadata.fingerprint == fingerprint)
            entry['file'] = cls._load_json_dict(row.metadata_json)
        except FileMetadata.DoesNotExist:
            entry['file'] = {}
        entry['file_loaded'] = True
        return entry['file']

    @classmethod
    def _prune_path_cache(cls, now):
        if now - cls._last_prune < cls.CACHE_PRUNE_INTERVAL_SECONDS:
            return
        cls._last_prune = now

        expired = []
        for key, entry in cls._path_cache.items():
            if now - entry.get('last_accessed', now) > cls.CACHE_TTL_SECONDS:
                expired.append(key)
        for key in expired:
            cls._path_cache.pop(key, None)

        while len(cls._path_cache) > cls.CACHE_MAX_ENTRIES:
            cls._path_cache.popitem(last=False)

    @classmethod
    def _get_cached_path_entry(cls, path):
        now = time.time()
        with cls._lock:
            cls._prune_path_cache(now)
            entry = cls._path_cache.get(path)
            if not entry:
                return None
            entry['last_accessed'] = now
            cls._path_cache.move_to_end(path)
            return entry

    @classmethod
    def _set_cached_path_entry(cls, path, entry):
        now = time.time()
        entry['created_at'] = now
        entry['last_accessed'] = now
        with cls._lock:
            cls._path_cache[path] = entry
            cls._path_cache.move_to_end(path)
            cls._prune_path_cache(now)

    @classmethod
    def get(cls, plugin_id_override=None):
        cls._ensure_main_process()
        plugin_id, task_id, path = cls._get_context()
        if plugin_id_override:
            plugin_id = plugin_id_override

        if task_id is not None:
            staged = cls._load_task_metadata(task_id)
            staged_scoped = cls._normalize_scoped_staged(staged)
            file_data = cls._load_file_metadata_for_task(task_id)
            merged = dict(file_data)
            merged.update(staged_scoped.get('source', {}))
            merged.update(staged_scoped.get('destination', {}))
            return deepcopy(merged.get(plugin_id, {}))

        if not path:
            raise RuntimeError("Metadata context requires a task_id or path")

        cached = cls._get_cached_path_entry(path)
        if cached:
            return deepcopy(cached.get('metadata', {}).get(plugin_id, {}))

        if not os.path.exists(path):
            return {}

        fingerprint, algo = common.get_file_fingerprint(path)
        try:
            row = FileMetadata.get(FileMetadata.fingerprint == fingerprint)
            metadata = cls._load_json_dict(row.metadata_json)
        except FileMetadata.DoesNotExist:
            metadata = {}

        entry = {
            'fingerprint': fingerprint,
            'fingerprint_algo': algo,
            'metadata': metadata,
        }
        cls._set_cached_path_entry(path, entry)
        return deepcopy(metadata.get(plugin_id, {}))

    @classmethod
    def set(cls, data, use_source_scope=False):
        cls._ensure_main_process()
        plugin_id, task_id, _ = cls._get_context()
        if task_id is None:
            raise RuntimeError("Metadata set() requires a task_id context")
        if not isinstance(data, dict):
            raise ValueError("Metadata set() requires a dict")

        with cls._lock:
            entry = cls._ensure_task_cache_entry(task_id)
            staged = cls._load_task_metadata(task_id)
            staged_scoped = cls._normalize_scoped_staged(staged)
            scope_key = 'source' if use_source_scope else 'destination'
            scope_blob = staged_scoped[scope_key]
            plugin_data = scope_blob.get(plugin_id, {})
            if not isinstance(plugin_data, dict):
                plugin_data = {}
            for key, value in data.items():
                if value is None:
                    plugin_data.pop(key, None)
                else:
                    plugin_data[key] = deepcopy(value)
            cls._enforce_plugin_size_limit(plugin_data)
            scope_blob[plugin_id] = plugin_data

            if scope_key == 'source':
                meta = staged_scoped.get('__meta__', {})
                if not meta.get('source_fingerprint'):
                    source_path = cls._load_task_source_path(task_id)
                    meta['source_path_at_set'] = source_path
                    if source_path and os.path.exists(source_path):
                        fingerprint, algo = common.get_file_fingerprint(source_path)
                        meta['source_fingerprint'] = fingerprint
                        meta['source_fingerprint_algo'] = algo
                    else:
                        cls._logger.info("Unable to fingerprint source path for metadata set: %s", source_path)
                staged_scoped['__meta__'] = meta

            entry['staged'] = staged_scoped
            entry['staged_loaded'] = True

            row, created = TaskMetadata.get_or_create(task=task_id, defaults={
                'json_blob': cls._dump_json_dict(staged_scoped),
                'updated_at': datetime.now(),
            })
            if not created:
                row.json_blob = cls._dump_json_dict(staged_scoped)
                row.updated_at = datetime.now()
                row.save()

    @classmethod
    def _upsert_path(cls, file_metadata_id, path, path_type):
        if not path:
            return
        now = datetime.now()
        FileMetadataPaths.update(
            file_metadata=file_metadata_id,
            path_type=path_type,
            updated_at=now,
        ).where(FileMetadataPaths.path == path).execute()

        row = FileMetadataPaths.get_or_none(
            (FileMetadataPaths.file_metadata == file_metadata_id) &
            (FileMetadataPaths.path == path)
        )
        if not row:
            FileMetadataPaths.create(
                file_metadata=file_metadata_id,
                path=path,
                path_type=path_type,
                created_at=now,
                updated_at=now,
            )

    @classmethod
    def commit_task(cls, task_id, task_success, source_path, destination_paths=None):
        cls._ensure_main_process()
        with cls._lock:
            staged = cls._load_task_metadata(task_id)
            if not staged:
                try:
                    TaskMetadata.delete().where(TaskMetadata.task == task_id).execute()
                except Exception:
                    pass
                cls._task_cache.pop(task_id, None)
                return 0

            task_entry = cls._ensure_task_cache_entry(task_id)
            staged_scoped = cls._normalize_scoped_staged(staged)
            source_staged = staged_scoped.get('source', {})
            destination_staged = staged_scoped.get('destination', {})
            meta = staged_scoped.get('__meta__', {})

        destination_paths = destination_paths or []
        destination_paths = [p for p in destination_paths if p]

        fingerprint_groups = {}
        if task_success and destination_paths and destination_staged:
            for path in destination_paths:
                if not os.path.exists(path):
                    continue
                fingerprint, algo = common.get_file_fingerprint(path)
                group = fingerprint_groups.setdefault(fingerprint, {'algo': algo, 'paths': [], 'scope': 'destination'})
                if path not in group['paths']:
                    group['paths'].append(path)
        if source_staged:
            source_path_at_set = meta.get('source_path_at_set') or source_path
            if not source_path_at_set or not os.path.exists(source_path_at_set):
                cls._logger.info(
                    "Source file missing at metadata commit; dropping source-scoped metadata for task %s",
                    task_id,
                )
            else:
                source_fingerprint = meta.get('source_fingerprint')
                source_algo = meta.get('source_fingerprint_algo')
                if not source_fingerprint:
                    source_fingerprint, source_algo = common.get_file_fingerprint(source_path_at_set)
                group = fingerprint_groups.setdefault(
                    source_fingerprint,
                    {'algo': source_algo, 'paths': [], 'scope': 'source'},
                )
                if source_path_at_set not in group['paths']:
                    group['paths'].append(source_path_at_set)

        with cls._lock:
            for fingerprint, data in fingerprint_groups.items():
                algo = data['algo']
                paths = data['paths']
                staged_payload = source_staged if data.get('scope') == 'source' else destination_staged

                if not staged_payload:
                    continue
                try:
                    row = FileMetadata.get(FileMetadata.fingerprint == fingerprint)
                    existing = cls._load_json_dict(row.metadata_json)
                    existing.update(deepcopy(staged_payload))
                    row.metadata_json = cls._dump_json_dict(existing)
                    row.fingerprint_algo = algo
                    row.updated_at = datetime.now()
                    row.last_task_id = task_id
                    row.save()
                except FileMetadata.DoesNotExist:
                    row = FileMetadata.create(
                        fingerprint=fingerprint,
                        fingerprint_algo=algo,
                        metadata_json=cls._dump_json_dict(staged_payload),
                        created_at=datetime.now(),
                        updated_at=datetime.now(),
                        last_task_id=task_id,
                    )

                if data.get('scope') == 'source':
                    source_path_at_set = meta.get('source_path_at_set') or source_path
                    if source_path_at_set:
                        cls._upsert_path(row.id, source_path_at_set, 'source')
                else:
                    for path in paths:
                        cls._upsert_path(row.id, path, 'destination')
                    if paths:
                        cls._upsert_path(row.id, paths[-1], 'last_seen')

            TaskMetadata.delete().where(TaskMetadata.task == task_id).execute()
            cls._task_cache.pop(task_id, None)
        return len(fingerprint_groups)

    @classmethod
    def find_by_path(cls, path):
        cls._ensure_main_process()
        if not path:
            return []
        search_value = path.strip()
        if not search_value:
            return []
        path_rows = FileMetadataPaths.select(FileMetadataPaths.file_metadata).where(
            fn.LOWER(FileMetadataPaths.path).contains(search_value.lower())
        )
        metadata_ids = list({row.file_metadata.id for row in path_rows})
        if not metadata_ids:
            return []

        path_map = {}
        for row in FileMetadataPaths.select().where(FileMetadataPaths.file_metadata.in_(metadata_ids)):
            path_map.setdefault(row.file_metadata.id, []).append({
                'path': row.path,
                'path_type': row.path_type,
            })

        results = []
        for row in FileMetadata.select().where(FileMetadata.id.in_(metadata_ids)):
            results.append({
                'fingerprint': row.fingerprint,
                'fingerprint_algo': row.fingerprint_algo,
                'metadata_json': cls._load_json_dict(row.metadata_json),
                'last_task_id': row.last_task_id,
                'paths': path_map.get(row.id, []),
            })
        return results

    @classmethod
    def find_all(cls):
        cls._ensure_main_process()
        path_map = {}
        for row in FileMetadataPaths.select():
            path_map.setdefault(row.file_metadata.id, []).append({
                'path': row.path,
                'path_type': row.path_type,
            })

        results = []
        for row in FileMetadata.select():
            results.append({
                'fingerprint': row.fingerprint,
                'fingerprint_algo': row.fingerprint_algo,
                'metadata_json': cls._load_json_dict(row.metadata_json),
                'last_task_id': row.last_task_id,
                'paths': path_map.get(row.id, []),
            })
        return results

    @classmethod
    def delete_for_plugin(cls, fingerprint, plugin_id=None):
        cls._ensure_main_process()
        if not fingerprint:
            return False
        try:
            row = FileMetadata.get(FileMetadata.fingerprint == fingerprint)
        except FileMetadata.DoesNotExist:
            return False

        if not plugin_id:
            row.delete_instance()
            return True

        data = cls._load_json_dict(row.metadata_json)
        data.pop(plugin_id, None)
        row.metadata_json = cls._dump_json_dict(data)
        row.updated_at = datetime.now()
        row.save()
        return True

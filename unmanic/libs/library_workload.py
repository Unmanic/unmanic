#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

"""Observe native Library workload without introducing another task ledger."""

from peewee import fn

from unmanic.libs.unmodels.libraries import Libraries
from unmanic.libs.unmodels.tasks import Tasks

ACTIVE_STATES = ('creating', 'pending', 'in_progress', 'processed')


def get_library_workload(library_ids=None, scanner=None):
    """Return an observation of scan state and outstanding tasks by Library.

    None or an empty list selects all configured Libraries. ``processed`` tasks
    remain outstanding until post-processing cleanup. Idle does not imply that
    completed tasks succeeded, and this query does not prevent new submissions.
    """
    known = {library.id for library in Libraries.select(Libraries.id)}
    if library_ids is not None and (not isinstance(library_ids, (list, tuple)) or any(
            type(value) is not int or value <= 0 for value in library_ids)):
        raise ValueError('library_ids must contain positive integer Library IDs')
    selected = sorted(set(library_ids or known))
    if set(selected) - known:
        raise ValueError('Unknown Library ID')
    if scanner is None:
        from unmanic.libs.uiserver import UnmanicRunningTreads
        scanner = UnmanicRunningTreads().get_unmanic_running_thread('library_scanner_manager')
    scan_state = scanner.get_scan_status()['state'] if scanner is not None else 'unavailable'
    counts = {library_id: {state: 0 for state in ACTIVE_STATES} for library_id in selected}
    query = (Tasks.select(Tasks.library_id, Tasks.status, fn.COUNT(Tasks.id).alias('count'))
             .where(Tasks.library_id.in_(selected), Tasks.status.in_(ACTIVE_STATES))
             .group_by(Tasks.library_id, Tasks.status))
    for row in query.dicts():
        counts[row['library_id']][row['status']] = row['count']
    if scan_state == 'idle':
        scan_state = scanner.get_scan_status()['state']
    libraries = []
    for library_id, states in counts.items():
        total = sum(states.values())
        libraries.append({'library_id': library_id, 'tasks': states,
                          'outstanding_tasks': total, 'idle': scan_state == 'idle' and total == 0})
    return {'scan_state': scan_state, 'libraries': libraries,
            'idle': scan_state == 'idle' and all(item['idle'] for item in libraries)}


def notify_library_workload_idle(library_ids=None, scanner=None, reason='task_complete', scanned_library_ids=None):
    """Notify plugins after cleanup or a full scan pass, when Libraries are idle.

    Notifications are observations and may repeat. Consumers can query a wider
    dependency set and coalesce their own actions. No success guarantee is implied.
    """
    workload = get_library_workload(library_ids, scanner)
    idle = [item['library_id'] for item in workload['libraries'] if item['idle']]
    if not idle:
        return
    from unmanic.libs.plugins import PluginsHandler
    data = {'library_ids': idle, 'reason': reason, 'workload': workload}
    if scanned_library_ids is not None:
        data['scanned_library_ids'] = scanned_library_ids
    PluginsHandler().run_event_plugins_for_plugin_type('events.library_workload_idle', data)

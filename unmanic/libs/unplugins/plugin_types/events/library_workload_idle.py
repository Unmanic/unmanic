#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

"""Plugin notification after native workload cleanup."""

from ..plugin_type_base import PluginType


class LibraryWorkloadIdle(PluginType):
    name = 'Events - Library workload idle'
    runner = 'emit_library_workload_idle'
    runner_docstring = """
    Observe idle Libraries after a complete scan pass or task cleanup.

    library_ids contains the observed idle Library IDs. reason identifies
    scan_complete, scan_cancelled or task_complete. workload contains scan_state and per-Library
    counts of creating, pending, in_progress and processed tasks. Notifications
    can repeat and are not a guarantee of successful processing or future idleness.
    For scan_complete, scanned_library_ids identifies Libraries attempted in the
    scan pass. Query the required Library set again before starting dependent work.
    """
    data_schema = {
        'library_ids': {'required': True, 'type': list},
        'reason': {'required': True, 'type': str},
        'workload': {'required': True, 'type': dict},
        'scanned_library_ids': {'required': False, 'type': list},
    }
    test_data = {
        'library_ids': [1], 'reason': 'scan_complete',
        'workload': {'scan_state': 'idle', 'idle': True, 'libraries': [
            {'library_id': 1, 'tasks': {'creating': 0, 'pending': 0, 'in_progress': 0, 'processed': 0},
             'outstanding_tasks': 0, 'idle': True}]},
    }

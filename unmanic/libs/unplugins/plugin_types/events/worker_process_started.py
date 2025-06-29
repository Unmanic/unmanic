#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
    unmanic.worker_process_started.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     29 June 2025, (9:37 PM)

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

from ..plugin_type_base import PluginType


class WorkerProcessStarted(PluginType):
    name = "Events - Worker process started"
    runner = "emit_worker_process_started"
    runner_docstring = """
    Runner function - emit data at the very start of a worker processing a task.

    The 'data' object argument includes:
        library_id            - Integer, the ID of the library.
        task_type             - String, "local" or "remote" indicating how this task is being processed.
        original_file_path    - String, absolute path to the original source file.
        task_cache_path       - String, the target cache path for this task.
        worker_runners_info   - Dict, per-runner metadata with initial status ("pending") and success (False).

    :param data:
    :return:
    """
    data_schema = {
        "library_id":          {"required": False, "type": int},
        "task_type":           {"required": False, "type": str},
        "original_file_path":  {"required": False, "type": str},
        "task_cache_path":     {"required": False, "type": str},
        "worker_runners_info": {"required": False, "type": dict},
    }
    test_data = {
        "library_id":          1,
        "task_type":           "local",
        "original_file_path":  "/path/to/media/file.mp4",
        "cache_directory":     "/path/to/cache/",
        "worker_runners_info": {
            "video_transcoder": {
                "plugin_id":   "video_transcoder",
                "name":        "Transcode Video Files",
                "author":      "Josh.5",
                "version":     "0.1.7",
                "icon":        "https://raw.githubusercontent.com/Unmanic/plugin.video_transcoder/master/icon.png",
                "description": "Transcode the video streams of a video file",
                "status":      "pending",
            }
        }
    }

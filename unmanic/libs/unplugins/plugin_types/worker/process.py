#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.process.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     05 Mar 2021, (8:05 PM)

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


class ProcessItem(PluginType):
    name = "Worker - Processing file"
    runner = "on_worker_process"
    runner_docstring = """
    Runner function - enables additional configured processing jobs during the worker stages of a task.

    The 'data' object argument includes:
        task_id                 - Integer, unique identifier of the task.
        worker_log              - Array, the log lines that are being tailed by the frontend. Can be left empty.
        library_id              - Number, the library that the current task is associated with.
        exec_command            - Array, a subprocess command that Unmanic should execute. Can be empty.
        command_progress_parser - Function, a function that Unmanic can use to parse the STDOUT of the command to collect progress stats. Can be empty.
        file_in                 - String, the source file to be processed by the command.
        file_out                - String, the destination that the command should output (may be the same as the file_in if necessary).
        original_file_path      - String, the absolute path to the original file.
        repeat                  - Boolean, should this runner be executed again once completed with the same variables.

    **Shared task & runner state**  
    Plugins can store shared, cross‐plugin and even cross‐process state via `TaskDataStore`:
    
        from unmanic.libs.task import TaskDataStore

        # Store mutable per‐task values:
        TaskDataStore.set_task_state("source_file_size", source_file_size)
        # read it back later (same or other plugin):
        p = TaskDataStore.get_task_state("source_file_size")

        # Store immutable runner‐scoped values:
        TaskDataStore.set_runner_value("probe_info", {...})
        val = TaskDataStore.get_runner_value("probe_info")

    **Spawning your own child process**  
    Instead of setting `exec_command`, you can perform complex or Python‐only work in a separate process while still reporting logs & progress:

        from unmanic.libs.unplugins.child_process import PluginChildProcess

        proc = PluginChildProcess(plugin_id="<your_plugin_id>", data=data)

        def child_work(log_queue, prog_queue):
            # any Python code here
            for i in range(10):
                # emit a UI log line:
                log_queue.put(f"step {i}/10 completed")
                # emit progress 0–100:
                prog_queue.put((i + 1) * 10)
                time.sleep(1)

        # Runs child_work in its own process, returns True if exit code==0
        success = proc.run(child_work)

    In this mode the `PluginChildProcess` helper:
      1. Spawns the child via `multiprocessing.Process`.  
      2. Registers its PID & start‐time with the worker’s `default_progress_parser`.  
      3. Drains `log_queue` → `data["worker_log"]` for UI tail.  
      4. Drains `prog_queue` → `command_progress_parser(line_text)` to update the progress bar.  
      5. Will unset the child process PID on exit to reset all tracked subprocess metrics in the Unmanic Worker (CPU, memory, progress, etc.).

    :param data:
    :return:
    """
    data_schema = {
        "library_id":              {
            "required": True,
            "type":     int,
        },
        "task_id":                 {
            "required": False,
            "type":     int
        },
        "worker_log":              {
            "required": True,
            "type":     list,
        },
        "exec_command":            {
            "required": True,
            "type":     [list, str],
        },
        "command_progress_parser": {
            "required": True,
            "type":     ['callable', None],
        },
        "file_in":                 {
            "required": True,
            "type":     str,
        },
        "file_out":                {
            "required": True,
            "type":     str,
        },
        "original_file_path":      {
            "required": False,
            "type":     str,
        },
        "repeat":                  {
            "required": False,
            "type":     bool,
        },
    }
    test_data = {
        'library_id':              1,
        "task_id":                 4321,
        'worker_log':              [],
        'exec_command':            [],
        'command_progress_parser': None,
        'file_in':                 '{library_path}/{test_file_in}',
        'file_out':                '{cache_path}/{test_file_out}',
        'original_file_path':      '{library_path}/{test_file_in}',
        'repeat':                  False,
    }

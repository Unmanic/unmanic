#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.child_process.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     09 jULY 2025, (11:34 PM)

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
import time
import queue
import threading
from multiprocessing import Process, Manager

from unmanic.libs.logs import UnmanicLogging


class PluginChildProcess:
    def __init__(self, plugin_id, data):
        """
        data must include:
          - data['worker_log']              : list to which your child functions logs go
          - data['command_progress_parser'] : callable(line_text, pid=None, proc_start_time=None, unset=False)
        """
        self.logger = UnmanicLogging.get_logger(
            name=f'Plugin.{plugin_id}.{__class__.__name__}'
        )
        self.data = data
        self.manager = Manager()
        self._log_q = self.manager.Queue()
        self._prog_q = self.manager.Queue()
        self._proc = None
        self._term_lock = threading.Lock()

    def run(self, target, *args, **kwargs):
        """
        Launch `target(*args, **kwargs, log_queue, prog_queue)` in its own process.
        Your `target` should accept two extra keyword args:
          log_queue  –> use log_queue.put(str) to emit log lines
          prog_queue –> use prog_queue.put(percentage:float) to emit progress
        """
        # Start child as before
        self._proc = Process(
            target=self._child_entry,
            args=(target, args, kwargs),
            daemon=True
        )
        self._proc.start()
        self.logger.info("Started child PID %s", self._proc.pid)

        # Register PID & start time with WorkerSubprocessMonitor
        parser = self.data.get('command_progress_parser')
        if callable(parser):
            try:
                parser(None, pid=self._proc.pid, proc_start_time=time.time())
            except Exception:
                self.logger.exception("Failed to register progress parser")

        # Drain logs, progress, watch exit
        return self._monitor()

    def _child_entry(self, target, args, kwargs):
        """
        Runs inside the child process.
        Injects our two required queues into the call.
        """
        try:
            kwargs['log_queue'] = self._log_q
            kwargs['prog_queue'] = self._prog_q
            target(*args, **kwargs)
        except Exception:
            self.logger.exception("Exception in child target")

    def _monitor(self):
        """
        Parent loop: pull from log_q -> data['worker_log'],
                     pull from prog_q -> call parser(...)
        """
        exit_ok = False
        parser = self.data.get('command_progress_parser')

        while True:
            # 1) drain logs
            try:
                while True:
                    msg = self._log_q.get_nowait()
                    self.data['worker_log'].append(f"{msg}\n")
            except queue.Empty:
                pass

            # 2) drain progress updates
            try:
                while True:
                    pct = self._prog_q.get_nowait()
                    if callable(parser):
                        parser(str(pct))
            except queue.Empty:
                pass

            # 3) if the child exited, we’re done. Unset parser PID
            if not self._proc.is_alive():
                exit_ok = (self._proc.exitcode == 0)
                if callable(parser):
                    # tell parser to unset its internal proc state
                    parser(None, unset=True)
                break

            # Add a short wait here to prevent CPU pinning
            time.sleep(0.1)

        return exit_ok

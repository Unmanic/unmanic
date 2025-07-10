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
import signal
import time
import queue
import threading

import psutil

from unmanic.libs.logs import UnmanicLogging

# Configure a global shared manager
_shared_manager = None

_active_plugin_pids = set()
_active_lock = threading.Lock()


def _register_pid(pid: int):
    with _active_lock:
        _active_plugin_pids.add(pid)


def _unregister_pid(pid: int):
    with _active_lock:
        _active_plugin_pids.discard(pid)


def kill_all_plugin_processes():
    """
    Terminate every plugin-spawned process (and its children)
    that’s still registered. Intended for use in atexit
    and tornado.autoreload hooks.
    """
    with _active_lock:
        pids = list(_active_plugin_pids)
        _active_plugin_pids.clear()

    for pid in pids:
        try:
            root = psutil.Process(pid)
        except psutil.NoSuchProcess:
            continue

        procs = root.children(recursive=True) + [root]

        # Ensure no processes are left in SIGSTOP
        for p in procs:
            try:
                # on Unix, unblock with SIGCONT
                p.send_signal(signal.SIGCONT)
            except Exception:
                pass
            try:
                # on all platforms psutil.resume() works if supported
                p.resume()
            except Exception:
                pass

        # Attempt graceful shutdown
        for p in procs:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass

        gone, alive = psutil.wait_procs(procs, timeout=3)

        # Finally, force kill any stragglers
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(alive, timeout=3)


def set_shared_manager(mgr):
    """Called once at service startup to inject the shared Manager."""
    global _shared_manager
    _shared_manager = mgr


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
        if _shared_manager is None:
            raise RuntimeError("PluginChildProcess must be initialized after shared Manager is set")
        self.manager = _shared_manager
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
        from multiprocessing import Process
        self._proc = Process(
            target=self._child_entry,
            args=(target, args, kwargs),
            daemon=True
        )
        self._proc.start()
        _register_pid(self._proc.pid)
        self.logger.info("Started child PID %s", self._proc.pid)

        # Register PID & start time with WorkerSubprocessMonitor
        parser = self.data.get('command_progress_parser')
        if callable(parser):
            try:
                parser(None, pid=self._proc.pid, proc_start_time=time.time())
            except Exception:
                self.logger.exception("Failed to register progress parser")

        # Drain logs, progress, watch exit
        success = self._monitor()

        # When the child process is done, unregister
        _unregister_pid(self._proc.pid)

        # Return success status
        return success

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

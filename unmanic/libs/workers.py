#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.workers.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     11 Aug 2021, (12:06 PM)

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
import os
import queue
import shlex
import shutil
import subprocess
import threading
import time

import psutil

from unmanic.libs import common
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.plugins import PluginsHandler


class WorkerCommandError(Exception):
    def __init___(self, command):
        Exception.__init__(self, "Worker command returned non 0 status. Command: {}".format(command))
        self.command = command


class WorkerSubprocessMonitor(threading.Thread):
    def __init__(self, parent_worker):
        super().__init__(daemon=True)
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)
        self._stop_event = threading.Event()
        self._terminate_lock = threading.Lock()

        self.parent_worker = parent_worker
        self.event = parent_worker.event
        self.redundant_flag = parent_worker.redundant_flag
        self.paused_flag = parent_worker.paused_flag
        self.paused = False

        # Set current subprocess to None
        self.subprocess_pid = None
        self.subprocess = None
        self.subprocess_start_time = 0
        self.subprocess_pause_time = 0

        # Subprocess stats
        self.subprocess_percent = 0
        self.subprocess_elapsed = 0
        self.subprocess_cpu_percent = 0
        self.subprocess_mem_percent = 0
        self.subprocess_rss_bytes = 0
        self.subprocess_vms_bytes = 0

    def set_proc(self, pid):
        try:
            if pid != self.subprocess_pid:
                self.subprocess_pid = pid
                self.subprocess = psutil.Process(pid=pid)
                # Reset pause time
                self.subprocess_start_time = time.time()
                self.subprocess_pause_time = 0
                # Reset subprocess progress
                self.subprocess_percent = 0
                self.subprocess_elapsed = 0
            if self.redundant_flag.is_set():
                # If the redundant flag is set then we should terminate any set procs straight away as the worker needs to stop
                self.logger.debug("A new subprocess was spawned, but the worker is trying to terminate. Subprocess PID %s",
                                  self.subprocess_pid)
                self.terminate_proc()

        except Exception:
            self.logger.exception("Exception in set_proc()")

    def unset_proc(self):
        try:
            self.subprocess_pid = None
            self.subprocess = None
            # Reset subprocess progress
            self.subprocess_percent = 0
            self.subprocess_elapsed = 0
            # Reset resource values
            self.set_proc_resources_in_parent_worker(0, 0, 0, 0)
        except Exception:
            self.logger.exception("Exception in unset_proc()")

    def set_proc_resources_in_parent_worker(self, normalised_cpu_percent, rss_bytes, vms_bytes, mem_percent):
        self.subprocess_cpu_percent = normalised_cpu_percent
        self.subprocess_rss_bytes = rss_bytes
        self.subprocess_vms_bytes = vms_bytes
        self.subprocess_mem_percent = mem_percent

    def suspend_proc(self):
        # Stop the process if the worker is paused
        # Then resume it when the worker is resumed
        try:
            if not self.subprocess or not self.subprocess.is_running():
                return

            # Create list of all subprocesses - parent + all children
            procs = [self.subprocess] + self.subprocess.children(recursive=True)

            # Suspend them all
            for p in procs:
                try:
                    self.logger.debug("Pausing PID %s", p.pid)
                    p.suspend()
                except psutil.NoSuchProcess:
                    continue

            self.paused = True
            self.subprocess_pause_time = int(time.time())
            while not self.redundant_flag.is_set():
                self.event.wait(1)
                if not self.paused_flag.is_set():
                    # Resume in reverse order
                    for p in reversed(procs):
                        try:
                            self.logger.debug("Resuming PID %s", p.pid)
                            p.resume()
                            # Force anything to shut down straight away if we are exiting the thread
                            if self.redundant_flag.is_set() or self._stop_event.is_set():
                                p.terminate()
                        except psutil.NoSuchProcess:
                            continue
                    self.paused = False
                    break

        except Exception:
            self.logger.exception("Exception in suspend_proc()")

    def terminate_proc(self):
        with self._terminate_lock:
            try:
                # If the process is still running, kill it
                if self.subprocess is not None:
                    self.logger.info("Terminating subprocess PID: %s", self.subprocess_pid)
                    self.__terminate_proc_tree(self.subprocess)
                    self.logger.info("Subprocess terminated")
                    self.unset_proc()
            except Exception:
                self.logger.exception("Exception in terminate_proc()")

    def __log_proc_terminated(self, proc: psutil.Process):
        try:
            self.logger.info("Process %s terminated with exit code %s", proc, proc.returncode)
        except Exception:
            self.logger.exception("Exception in __log_proc_terminated()")

    def __terminate_proc_tree(self, proc: psutil.Process):
        """
        Terminate the process tree (including grandchildren).
        Ensures any suspended processes are first resumed so that
        terminate() will actually take effect.  Processes that
        fail to stop with terminate() within 3s will be killed.

        :param proc:
        :return:
        """
        try:
            # Build the full tree
            all_procs = proc.children(recursive=True) + [proc]

            # Resume all suspended processes so they can handle signals
            for p in all_procs:
                try:
                    p.resume()
                except (psutil.NoSuchProcess, NotImplementedError):
                    pass

            # Attempt graceful shutdown
            for p in all_procs:
                try:
                    p.terminate()
                except psutil.NoSuchProcess:
                    pass

            # Wait up to 3s for them to exit
            gone, alive = psutil.wait_procs(all_procs, timeout=3, callback=self.__log_proc_terminated)

            # Force-kill any remaining processes
            for p in alive:
                try:
                    p.kill()
                except psutil.NoSuchProcess:
                    pass

            # Final wait to reap
            psutil.wait_procs(alive, timeout=3, callback=self.__log_proc_terminated)

        except Exception:
            self.logger.exception("Exception in __terminate_proc_tree()")

    def get_subprocess_elapsed(self):
        try:
            subprocess_elapsed = 0
            if self.subprocess is not None:
                # Get the time now
                now = int(time.time())
                # Get the total running time (including time being paused)
                total_run_time = int(now - self.subprocess_start_time)
                # Get the time when we started being paused
                pause_duration = int(now - self.subprocess_pause_time)
                # Calculate elapsed time of the subprocess subtracting the pause duration
                subprocess_elapsed = int(total_run_time - pause_duration)
            return subprocess_elapsed
        except Exception:
            self.logger.exception("Exception in get_subprocess_elapsed()")
            return 0

    def get_subprocess_stats(self):
        try:
            return {
                'pid':         str(self.subprocess_pid),
                'percent':     str(self.subprocess_percent),
                'elapsed':     self.get_subprocess_elapsed(),
                'cpu_percent': str(self.subprocess_cpu_percent),
                'mem_percent': str(self.subprocess_mem_percent),
                'rss_bytes':   str(self.subprocess_rss_bytes),
                'vms_bytes':   str(self.subprocess_vms_bytes),
            }
        except Exception:
            self.logger.exception("Exception in get_subprocess_stats()")
            # Return something minimal so UI won't break
            return {
                'pid':         '0', 'percent': '0', 'elapsed': '0',
                'cpu_percent': '0', 'mem_percent': '0',
                'rss_bytes':   '0', 'vms_bytes': '0',
            }

    def set_subprocess_start_time(self, proc_start_time):
        try:
            self.subprocess_start_time = proc_start_time
        except Exception:
            self.logger.exception("Exception in set_subprocess_start_time()")

    def set_subprocess_percent(self, percent):
        try:
            self.subprocess_percent = percent
        except Exception:
            self.logger.exception("Exception in set_subprocess_percent()")

    def default_progress_parser(self, line_text, pid=None, proc_start_time=None, unset=False):
        if unset:
            # Here we provide a plugin with the ability to unset a subprocess (indicating that it completed)
            self.unset_proc()
            return {
                'killed':  self.redundant_flag.is_set(),
                'paused':  self.paused,
                'percent': str(self.subprocess_percent),
            }
        try:
            if pid is not None:
                self.set_proc(pid)
            if proc_start_time is not None:
                self.set_subprocess_start_time(proc_start_time)
            try:
                stripped_text = str(line_text).strip()
                text_float = float(stripped_text)
                self.subprocess_percent = int(text_float)
            except (TypeError, ValueError):
                pass
            return {
                'killed':  self.redundant_flag.is_set(),
                'paused':  self.paused,
                'percent': str(self.subprocess_percent),
            }
        except Exception:
            self.logger.exception("Exception in default_progress_parser()")
            return {
                'killed':  self.redundant_flag.is_set(),
                'paused':  self.paused,
                'percent': str(self.subprocess_percent),
            }

    def run(self):
        # First fetch the number of CPUs for normalising the CPU percent
        cpu_count = psutil.cpu_count(logical=True)
        # Loop while thread is expected to be running
        self.logger.warning("Starting WorkerMonitor loop")
        while True:
            try:
                if self._stop_event.is_set():
                    self.event.wait(1)
                    break

                if self.redundant_flag.is_set():
                    # If the worker needs to exit, then terminate the subprocess
                    self.terminate_proc()
                    self.event.wait(1)
                    continue

                if self.subprocess is None:
                    self.event.wait(1)
                    continue

                if not self.subprocess.is_running():
                    self.event.wait(1)
                    continue

                # Fetch CPU info
                cpu_percent = self.subprocess.cpu_percent(interval=None)
                normalised_cpu_percent = cpu_percent / cpu_count

                # Fetch Memory info
                mem_info = self.subprocess.memory_info()
                total_rss = mem_info.rss
                total_vms = mem_info.vms
                for child in self.subprocess.children(recursive=True):
                    try:
                        mem = child.memory_info()
                        total_rss += mem.rss
                        total_vms += mem.vms
                    except psutil.NoSuchProcess:
                        continue

                # Calculate percentage of memory used relative to total system RAM
                total_system_ram = psutil.virtual_memory().total
                mem_percent = (total_rss / total_system_ram) * 100

                # Set values in parent worker thread
                self.set_proc_resources_in_parent_worker(normalised_cpu_percent, total_rss, total_vms, mem_percent)

                # Pause subprocesses if the worker is paused
                if self.paused_flag.is_set():
                    self.suspend_proc()

            except psutil.NoSuchProcess:
                self.logger.debug("No such process: %s", self.subprocess_pid)
            except Exception:
                self.logger.exception("Unhandled exception in WorkerMonitor.run()")

            # Poll interval
            try:
                self.event.wait(1)
            except Exception:
                # In case event.wait itself misbehaves
                self.logger.exception("Exception while waiting in WorkerMonitor.run()")
                time.sleep(1)

        self.logger.info("Exiting WorkerMonitor loop")

    def stop(self):
        self.terminate_proc()
        self._stop_event.set()


class Worker(threading.Thread):
    idle = True
    paused = False

    current_task = None
    worker_log = None
    start_time = None
    finish_time = None

    worker_runners_info = {}

    def __init__(self, thread_id, name, worker_group_id, pending_queue, complete_queue, event):
        super(Worker, self).__init__(name=name)
        self.thread_id = thread_id
        self.name = name
        self.worker_group_id = worker_group_id
        self.event = event

        self.current_task = None
        self.pending_queue = pending_queue
        self.complete_queue = complete_queue
        self.worker_subprocess_monitor = None

        # Create 'redundancy' flag. When this is set, the worker should die
        self.redundant_flag = threading.Event()
        self.redundant_flag.clear()

        # Create 'paused' flag. When this is set, the worker should be paused
        self.paused_flag = threading.Event()
        self.paused_flag.clear()

        # Create logger for this worker
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def run(self):
        self.logger.info("Starting worker")

        # Create proc monitor
        self.worker_subprocess_monitor = WorkerSubprocessMonitor(self)
        self.worker_subprocess_monitor.start()

        while not self.redundant_flag.is_set():
            self.event.wait(1)  # Add delay for preventing loop maxing compute resources

            # If the Foreman has paused this worker, then don't do anything
            if self.paused_flag.is_set():
                self.paused = True
                # If the worker is paused, wait for 5 seconds before continuing the loop
                self.event.wait(5)
                continue
            self.paused = False

            # Set the worker as Idle - This will announce to the Foreman that it's ready for a task
            self.idle = True

            # Wait for task
            while not self.redundant_flag.is_set() and self.current_task:
                self.event.wait(.5)  # Add delay for preventing loop maxing compute resources

                try:
                    # Process the set task
                    self.__process_task_queue_item()
                except queue.Empty:
                    continue
                except Exception as e:
                    self._log("Exception in processing job with {}:".format(self.name), message2=str(e),
                              level="exception")

        self.logger.info("Stopping worker")
        self.worker_subprocess_monitor.stop()
        self.worker_subprocess_monitor.join()
        self.worker_subprocess_monitor = None

    def set_task(self, new_task):
        """Sets the given task to the worker class"""
        # Ensure only one task can be set for a worker
        if self.current_task:
            return
        # Set the task
        self.current_task = new_task
        self.worker_log = []
        self.idle = False

    def get_status(self):
        """
        Fetch the status of this worker.

        :return:
        """
        subprocess_stats = None
        if self.worker_subprocess_monitor:
            subprocess_stats = self.worker_subprocess_monitor.get_subprocess_stats()
        status = {
            'id':              str(self.thread_id),
            'name':            self.name,
            'idle':            self.idle,
            'paused':          self.paused_flag.is_set(),
            'start_time':      None if not self.start_time else str(self.start_time),
            'current_task':    None,
            'current_file':    "",
            'worker_log_tail': [],
            'runners_info':    {},
            'subprocess':      subprocess_stats,
        }
        if self.current_task:
            # Fetch the current file
            try:
                status['current_task'] = self.current_task.get_task_id()
            except Exception as e:
                self._log("Exception in fetching the current task ID for worker {}:".format(self.name), message2=str(e),
                          level="exception")

            # Fetch the current file
            try:
                status['current_file'] = self.current_task.get_source_basename()
            except Exception as e:
                self._log("Exception in fetching the current file of worker {}:".format(self.name), message2=str(e),
                          level="exception")

            # Append the worker log tail
            try:
                if self.worker_log and len(self.worker_log) > 20:
                    status['worker_log_tail'] = self.worker_log[-19:]
                else:
                    status['worker_log_tail'] = self.worker_log
            except Exception as e:
                self._log("Exception in fetching log tail of worker: ", message2=str(e),
                          level="exception")

            # Append the runners info
            try:
                status['runners_info'] = self.worker_runners_info
            except Exception as e:
                self._log("Exception in runners info of worker {}:".format(self.name), message2=str(e),
                          level="exception")
        return status

    def __unset_current_task(self):
        self.current_task = None
        self.worker_runners_info = {}
        self.worker_log = []

    def __process_task_queue_item(self):
        """
        Processes the set task.

        :return:
        """
        # Mark worker as not idle now that it is processing a task
        self.idle = False

        # Log the start of the job
        self.logger.info("Picked up job - %s", self.current_task.get_source_abspath())

        # Mark as being "in progress"
        self.current_task.set_status('in_progress')

        # Start current task stats
        self.__set_start_task_stats()

        # Process the file. Will return true if success, otherwise false
        success = self.__exec_worker_runners_on_set_task()
        # Mark the task as either success or not
        self.current_task.set_success(success)

        # Mark task completion statistics
        self.__set_finish_task_stats()

        # Log completion of job
        self.logger.info("Finished job - %s", self.current_task.get_source_abspath())

        # Place the task into the completed queue
        self.complete_queue.put(self.current_task)

        # Reset the current file info for the next task
        self.__unset_current_task()

    def __set_start_task_stats(self):
        """Sets the initial stats for the start of a task"""
        # Set the start time to now
        self.start_time = time.time()

        # Clear the finish time
        self.finish_time = None

        # Format our starting statistics data
        self.current_task.task.processed_by_worker = self.name
        self.current_task.task.start_time = self.start_time
        self.current_task.task.finish_time = self.finish_time

    def __set_finish_task_stats(self):
        """Sets the final stats for the end of a task"""
        # Set the finish time to now
        self.finish_time = time.time()

        # Set the finish time in the statistics data
        self.current_task.task.finish_time = self.finish_time

    def __exec_worker_runners_on_set_task(self):
        """
        Executes the configured plugin runners against the set task.

        :return:
        """
        # Init plugins
        library_id = self.current_task.get_task_library_id()
        plugin_handler = PluginsHandler()
        plugin_modules = plugin_handler.get_enabled_plugin_modules_by_type('worker.process', library_id=library_id)

        # Create dictionary of runners info for the frontend
        self.worker_runners_info = {}
        for plugin_module in plugin_modules:
            self.worker_runners_info[plugin_module.get('plugin_id')] = {
                'plugin_id':   plugin_module.get('plugin_id'),
                'status':      'pending',
                "name":        plugin_module.get('name'),
                "author":      plugin_module.get('author'),
                "version":     plugin_module.get('version'),
                "icon":        plugin_module.get('icon'),
                "description": plugin_module.get('description'),
            }

        # Set the absolute path to the original file
        original_abspath = self.current_task.get_source_abspath()

        # Process item in loop.
        # First process the item for each plugin that configures it, then run the default Unmanic configuration
        task_cache_path = self.current_task.get_cache_path()
        cache_directory = os.path.dirname(os.path.abspath(task_cache_path))
        # Set the current input file to the original file path
        file_in = original_abspath
        # Mark the overall success of all runners. This will be set to False if any of the runners fails.
        overall_success = True
        # Set the current file out to nothing.
        # This will be configured by each runner.
        # If no runners are configured, then nothing needs to be done.
        current_file_out = original_abspath
        # The number of runners that have been run
        runner_count = 0
        # Flag if a task has run a command
        no_exec_command_run = True

        # Execute event plugin runners
        plugin_handler.run_event_plugins_for_plugin_type('events.worker_process_started', {
            "library_id":          library_id,
            "task_type":           self.current_task.get_task_type(),
            "original_file_path":  original_abspath,
            "cache_directory":     cache_directory,
            "worker_runners_info": self.worker_runners_info,
        })

        # Generate default data object for the runner functions
        task_id = self.current_task.get_task_id()
        data = {
            "worker_log":              self.worker_log,
            "library_id":              library_id,
            "exec_command":            [],
            "command_progress_parser": None,
            "file_in":                 file_in,
            "file_out":                None,
            "original_file_path":      original_abspath,
            "repeat":                  False,
        }

        for plugin_module in plugin_modules:
            # Increment the runners count (first runner will be set as #1)
            runner_count += 1
            runner_id = plugin_module.get('plugin_id')

            if not overall_success:
                # If one of the Plugins fails, don't continue.
                # The Plugins could be co-dependant and the final file will not go anywhere if 'overall_success' is False
                break

            # Mark the status of the worker for the frontend
            self.worker_runners_info[runner_id]['status'] = 'in_progress'
            self.worker_runners_info[runner_id]['success'] = False

            # Loop over runner. This way we can repeat the function with the same data if requested by the repeat flag
            runner_pass_count = 0
            while not self.redundant_flag.is_set():
                runner_pass_count += 1

                # Fetch file out details
                # This creates a temp file labeled "WORKING" that will be moved to the cache_path on completion
                split_file_out = os.path.splitext(task_cache_path)
                split_file_in = os.path.splitext(file_in)
                file_out = "{}-{}-{}-{}{}".format(split_file_out[0], "WORKING", runner_count, runner_pass_count,
                                                  split_file_in[1])

                # Reset data object for this runner functions
                data['library_id'] = library_id
                data['exec_command'] = []
                data['command_progress_parser'] = self.worker_subprocess_monitor.default_progress_parser
                data['file_in'] = file_in
                data['file_out'] = file_out
                data['original_file_path'] = original_abspath
                data['repeat'] = False
                data['task_id'] = task_id

                self.event.wait(.2)  # Add delay for preventing loop maxing compute resources
                self.worker_log.append("\n\nRUNNER: \n{} [Pass #{}]\n\n".format(plugin_module.get('name'), runner_pass_count))
                self.worker_log.append("\nExecuting plugin runner... Please wait\n")

                # Run plugin (in its own thread) to update data
                result = {"success": None}

                def _run_plugin():
                    result["success"] = plugin_handler.exec_plugin_runner(
                        data, runner_id, 'worker.process'
                    )

                runner_thread = threading.Thread(target=_run_plugin, daemon=True)
                runner_thread.start()

                # monitor the thread, bail if redundancy requested
                while runner_thread.is_alive():
                    if self.redundant_flag.is_set():
                        self.logger.warning("Worker stop flag set, aborting plugin runner '%s'", runner_id)
                        break
                    self.event.wait(0.2)

                # if we were told to shut down, mark failure and exit loop
                if self.redundant_flag.is_set():
                    self.worker_runners_info[runner_id]['status'] = 'complete'
                    self.worker_runners_info[runner_id]['success'] = False
                    overall_success = False
                    self.worker_log.append("\n\nWORKER TERMINATED!")
                    break

                # now check the plugin result
                if not result["success"]:
                    # Skip this plugin module's loop
                    self.worker_runners_info[runner_id]['status'] = 'complete'
                    self.worker_runners_info[runner_id]['success'] = False
                    # Set overall success status to failed
                    overall_success = False
                    # Append long entry to say the worker was terminated
                    self.worker_log.append("\n\nPLUGIN FAILED!")
                    self.worker_log.append("\nFailed to execute Plugin '{}'".format(plugin_module.get('name')))
                    self.worker_log.append("\nCheck Unmanic logs for more information")
                    break

                # Log the in and out files returned by the plugin runner for debugging
                self._log("Worker process '{}' (in)".format(runner_id), data.get("file_in"),
                          level='debug')
                self._log("Worker process '{}' (out)".format(runner_id), data.get("file_out"),
                          level='debug')

                # Only run the conversion process if "exec_command" is not empty
                if data.get("exec_command"):
                    self.worker_log.append("\nPlugin runner requested for a command to be executed by Unmanic")

                    # Exec command as subprocess
                    success = self.__exec_command_subprocess(data)
                    no_exec_command_run = False

                    if self.redundant_flag.is_set():
                        # This worker has been marked as redundant. It is being terminated.
                        self._log("Worker has been terminated before a command was completed", level="warning")
                        # Mark runner as failed
                        self.worker_runners_info[runner_id]['success'] = False
                        # Set overall success status to failed
                        overall_success = False
                        # Append long entry to say the worker was terminated
                        self.worker_log.append("\n\nWORKER TERMINATED!")
                        # Don't continue
                        break

                    # Check if command exited successfully.
                    if success:
                        # If file conversion was successful
                        self.logger.info("Successfully ran worker process '%s' on file '%s'",
                                         runner_id,
                                         data.get("file_in"))
                        # Check if 'file_out' was nulled by the plugin. If it is, then we will assume that the plugin modified the file_in in-place
                        if not data.get('file_out'):
                            # The 'file_out' is None. Ensure the new 'file_in' is set to whatever the plugin returned for 'file_in' for the next loop
                            file_in = data.get("file_in")
                        # Ensure the 'file_out' that was specified by the plugin to be created was actually created.
                        elif os.path.exists(data.get('file_out')):
                            # The outfile exists...
                            # In order to clean up as we go and avoid unnecessary RAM/disk use in the cache directory,
                            #   we want to remove the 'file_in' file.
                            # We want to ensure that we do not accidentally remove any original files here.
                            # We also want to ensure that the 'file_out' is not removed if the plugin set it to the same path as the 'file_in'.
                            # To avoid this, run x3 tests.
                            # First, check current 'file_in' is not the original file.
                            if os.path.abspath(data.get("file_in")) != os.path.abspath(original_abspath):
                                # Second, check that the 'file_in' is actually in cache directory. If it is not, we did not create it.
                                if "unmanic_file_conversion" in os.path.abspath(data.get("file_in")):
                                    # Finally, check that the file_out is not the same file as the file_in
                                    if os.path.abspath(data.get("file_out")) != os.path.abspath(data.get("file_in")):
                                        # Remove the old file_in file
                                        os.remove(os.path.abspath(data.get("file_in")))

                            # Set the new 'file_in' as the previous runner's 'file_out' for the next loop
                            file_in = data.get("file_out")
                    else:
                        # If file conversion was not successful
                        self._log(
                            "Error while running worker process '{}' on file '{}'".format(
                                runner_id,
                                original_abspath
                            ),
                            level="error")
                        self.worker_runners_info[runner_id]['success'] = False
                        overall_success = False
                else:
                    # Ensure the new 'file_in' is set to the previous runner's 'file_in' for the next loop
                    file_in = data.get("file_in")
                    # Log that this plugin did not request to execute anything
                    self.worker_log.append("\nRunner did not request for Unmanic to execute a command")
                    self._log(
                        "Worker process '{}' did not request to execute a command.".format(runner_id),
                        level='debug')

                if data.get('file_out') and os.path.exists(data.get('file_out')):
                    # Set the current file out to the most recently completed cache file
                    # If the file out does not exist, it is likely never used by the plugin.
                    current_file_out = data.get('file_out')
                else:
                    # Ensure the current_file_out is set the currently set 'file_in'
                    current_file_out = data.get('file_in')

                if data.get("repeat"):
                    # The returned data contained the 'repeat'' flag.
                    # Run another pass against this same plugin
                    continue
                break

            self.worker_runners_info[runner_id]['success'] = True
            self.worker_runners_info[runner_id]['status'] = 'complete'

        # Log if no command was run by any Plugins
        if no_exec_command_run:
            # If no jobs were carried out on this task
            self._log("No Plugin requested for Unmanic to run commands for this file '{}'".format(original_abspath),
                      level='warning')
            self.worker_log.append(
                "\n\nNo Plugin requested for Unmanic to run commands for this file '{}'".format(original_abspath))

        # Save the completed command log
        self.current_task.save_command_log(self.worker_log)

        # If all plugins that were executed completed successfully, then this was overall a successful task.
        # At this point we need to move the final out file to the original task cache path so the postprocessor can collect it.
        if overall_success:
            # If jobs carried out on this task were all successful, we will get here
            self.logger.info("Successfully completed Worker processing on file '%s'", original_abspath)

            # Attempt to move the final output file to the final cache file path for the postprocessor
            try:
                # Set the new file out as the extension may have changed
                split_file_name = os.path.splitext(current_file_out)
                file_extension = split_file_name[1].lstrip('.')
                self.current_task.set_cache_path(cache_directory, file_extension)
                # Read the updated cache path
                task_cache_path = self.current_task.get_cache_path()

                # Move file to original cache path
                self._log("Moving final cache file from '{}' to '{}'".format(current_file_out, task_cache_path))
                current_file_out = os.path.abspath(current_file_out)

                # There is a really odd intermittent bug with the shutil module that is causing it to
                #   sometimes report that the file does not exist.
                # This section adds a small pause and logs the error if that is the case.
                # I have not yet figured out a solution as this is difficult to reproduce.
                if not os.path.exists(current_file_out):
                    self._log("Error - current_file_out path does not exist! '{}'".format(file_in), level="error")
                    self.event.wait(1)

                # Ensure the cache directory exists
                if not os.path.exists(cache_directory):
                    os.makedirs(cache_directory)

                # Check that the current file out is not the original source file
                if os.path.abspath(current_file_out) == os.path.abspath(original_abspath):
                    # The current file out is not a cache file, the file must have never been modified.
                    # This can happen if all Plugins failed to run, or a Plugin specifically reset the out
                    #   file to the original source in order to preserve it.
                    # In this circumstance, we want to create a cache copy and let the process continue.
                    self._log("Final cache file is the same path as the original source. Creating cache copy.", level='debug')
                    shutil.copyfile(current_file_out, task_cache_path)
                else:
                    # Use shutil module to move the file to the final task cache location
                    shutil.move(current_file_out, task_cache_path)
            except Exception as e:
                self._log("Exception in final move operation of file {} to {}:".format(current_file_out, task_cache_path),
                          message2=str(e), level="exception")
                overall_success = False

        # Execute event plugin runners (only when added to queue)
        plugin_handler.run_event_plugins_for_plugin_type('events.worker_process_complete', {
            "library_id":          library_id,
            "task_type":           self.current_task.get_task_type(),
            "original_file_path":  original_abspath,
            "final_cache_path":    task_cache_path,
            "overall_success":     overall_success,
            "worker_runners_info": self.worker_runners_info,
            "worker_log":          self.worker_log,
        })

        # If the overall result of the jobs carried out on this task were not successful, log the failure and return False
        if not overall_success:
            self._log("Failed to process task for file '{}'".format(original_abspath), level='warning')
        return overall_success

    def __exec_command_subprocess(self, data):
        """
        Executes a command as a shell subprocess.
        Uses the given parser to record progress data from the shell STDOUT.

        :param data:
        :return:
        """
        # Fetch command to execute.
        exec_command = data.get("exec_command", [])

        # Fetch the command progress parser function
        command_progress_parser = data.get("command_progress_parser", self.worker_subprocess_monitor.default_progress_parser)

        # Log the command for debugging
        command_string = exec_command
        if isinstance(exec_command, list):
            command_string = shlex.join(exec_command)
        self._log("Executing: {}".format(command_string), level='debug')

        # Append start of command to worker subprocess stdout
        self.worker_log += [
            '\n\n',
            'COMMAND:\n',
            command_string,
            '\n\n',
            'LOG:\n',
        ]

        # Create output path if file_out is present and the path does not exists
        if data.get("file_out"):
            common.ensure_dir(data.get("file_out"))

        # Convert file
        try:
            # Execute command
            if isinstance(exec_command, list):
                sub_proc = subprocess.Popen(exec_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            universal_newlines=True, errors='replace')
            elif isinstance(exec_command, str):
                sub_proc = subprocess.Popen(exec_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            universal_newlines=True, errors='replace', shell=True)
            else:
                raise Exception(
                    "Plugin's returned 'exec_command' object must be either a list or a string. Received type {}.".format(
                        type(exec_command)))

            # Fetch process using psutil for control (sending SIGSTOP on windows will not work)
            proc = psutil.Process(pid=sub_proc.pid)

            # Create proc monitor
            self.worker_subprocess_monitor.set_proc(sub_proc.pid)

            # Set process priority on posix systems
            # TODO: Test how this will work on Windows
            if os.name == "posix":
                try:
                    parent_proc = psutil.Process(os.getpid())
                    parent_proc_nice = parent_proc.nice()
                    proc.nice(parent_proc_nice + 1)
                except Exception as e:
                    self._log("Unable to lower priority of subprocess. Subprocess should continue to run at normal priority",
                              str(e), level='warning')

            # Poll process for new output until finished
            while not self.redundant_flag.is_set():

                # Stop parsing the sub process if the worker is paused
                # Then resume it when the worker is resumed
                if self.paused_flag.is_set():
                    self.logger.debug("Pausing worker exec command subprocess loop")
                    while not self.redundant_flag.is_set():
                        self.event.wait(1)
                        if not self.paused_flag.is_set():
                            self.logger.debug("Resuming worker exec command subprocess loop")
                            break
                        continue

                # Fetch command stdout and append it to the current task object (to be saved during post process)
                line_text = sub_proc.stdout.readline()
                self.worker_log.append(line_text)

                # Check if the command has completed. If it has, exit the loop
                if line_text == '' and sub_proc.poll() is not None:
                    self._log("Subprocess task completed!", level='debug')
                    break

                # Parse the progress
                try:
                    progress_dict = command_progress_parser(line_text)
                    progress_percent = progress_dict.get('percent', 0)
                    self.worker_subprocess_monitor.set_subprocess_percent(progress_percent)
                except Exception as e:
                    # Only need to show any sort of exception if we have debugging enabled.
                    # So we should log it as a debug rather than an exception.
                    self._log("Exception while parsing command progress", str(e), level='debug')

            # Get the final output and the exit status
            if not self.redundant_flag.is_set():
                communicate = sub_proc.communicate()[0]

            # If the process is still running, kill it
            self.worker_subprocess_monitor.terminate_proc()

            # Stop proc monitor
            self.worker_subprocess_monitor.unset_proc()

            if sub_proc.returncode == 0:
                return True
            else:
                self._log("Command run against '{}' exited with non-zero status. "
                          "Download command dump from history for more information.".format(data.get("file_in")),
                          message2=str(exec_command), level="error")
                return False

        except Exception as e:
            self._log("Error while executing the command against file{}.".format(data.get("file_in")), message2=str(e),
                      level="error")

        return False

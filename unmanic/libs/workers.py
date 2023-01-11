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
import hashlib
import os
import queue
import shutil
import subprocess
import threading
import time

import psutil

from unmanic.libs import common, unlogger
from unmanic.libs.plugins import PluginsHandler


def default_progress_parser(line_text):
    return {
        'percent': ''
    }


class WorkerCommandError(Exception):
    def __init___(self, command):
        Exception.__init__(self, "Worker command returned non 0 status. Command: {}".format(command))
        self.command = command


class Worker(threading.Thread):
    idle = True
    paused = False

    current_task = None
    worker_log = None
    start_time = None
    finish_time = None

    worker_subprocess = None
    worker_subprocess_pid = None
    worker_subprocess_percent = None
    worker_subprocess_elapsed = None

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

        # Create 'redundancy' flag. When this is set, the worker should die
        self.redundant_flag = threading.Event()
        self.redundant_flag.clear()

        # Create 'paused' flag. When this is set, the worker should be paused
        self.paused_flag = threading.Event()
        self.paused_flag.clear()

        # Create logger for this worker
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(self.name)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def run(self):
        self._log("Starting worker")
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

        self._log("Stopping worker")

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

        TODO: Fetch subprocess pid

        :return:
        """
        status = {
            'id':              str(self.thread_id),
            'name':            self.name,
            'idle':            self.idle,
            'paused':          self.paused,
            'start_time':      None if not self.start_time else str(self.start_time),
            'current_task':    None,
            'current_file':    "",
            'worker_log_tail': [],
            'runners_info':    {},
            'subprocess':      {
                'pid':     self.ident,
                'percent': str(self.worker_subprocess_percent),
                'elapsed': str(self.worker_subprocess_elapsed),
            },
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

        # Set the progress to an empty string
        self.worker_subprocess_percent = ''
        self.worker_subprocess_elapsed = '0'

        # Log the start of the job
        self._log("Picked up job - {}".format(self.current_task.get_source_abspath()))

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
        self._log("Finished job - {}".format(self.current_task.get_source_abspath()))

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
        plugin_modules = plugin_handler.get_enabled_plugin_modules_by_type('worker.process_item', library_id=library_id)

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
        # First process the item for for each plugin that configures it, then run the default Unmanic configuration
        task_cache_path = self.current_task.get_cache_path()
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

        # Generate default data object for the runner functions
        data = {
            "worker_log":              self.worker_log,
            "library_id":              library_id,
            "exec_command":            [],
            "command_progress_parser": default_progress_parser,
            "file_in":                 file_in,
            "file_out":                None,
            "original_file_path":      original_abspath,
            "repeat":                  False,
        }

        for plugin_module in plugin_modules:
            # Increment the runners count (first runner will be set as #1)
            runner_count += 1

            if not overall_success:
                # If one of the Plugins fails, don't continue.
                # The Plugins could be co-dependant and the final file will not go anywhere if 'overall_success' is False
                break

            # Mark the status of the worker for the frontend
            self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'in_progress'
            self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = False

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
                data['command_progress_parser'] = default_progress_parser
                data['file_in'] = file_in
                data['file_out'] = file_out
                data['original_file_path'] = original_abspath
                data['repeat'] = False

                self.event.wait(.2)  # Add delay for preventing loop maxing compute resources
                self.worker_log.append("\n\nRUNNER: \n{} [Pass #{}]\n\n".format(plugin_module.get('name'), runner_pass_count))
                self.worker_log.append("\nExecuting plugin runner... Please wait\n")

                # Run plugin to update data
                if not plugin_handler.exec_plugin_runner(data, plugin_module.get('plugin_id'), 'worker.process_item'):
                    # Skip this plugin module's loop
                    self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'complete'
                    self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = False
                    # Set overall success status to failed
                    overall_success = False
                    # Append long entry to say the worker was terminated
                    self.worker_log.append("\n\nPLUGIN FAILED!")
                    self.worker_log.append("\nFailed to execute Plugin '{}'".format(plugin_module.get('name')))
                    self.worker_log.append("\nCheck Unmanic logs for more information")
                    break

                # Log the in and out files returned by the plugin runner for debugging
                self._log("Worker process '{}' (in)".format(plugin_module.get('plugin_id')), data.get("file_in"),
                          level='debug')
                self._log("Worker process '{}' (out)".format(plugin_module.get('plugin_id')), data.get("file_out"),
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
                        self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = False
                        # Set overall success status to failed
                        overall_success = False
                        # Append long entry to say the worker was terminated
                        self.worker_log.append("\n\nWORKER TERMINATED!")
                        # Don't continue
                        break

                    # Run command. Check if command exited successfully.
                    if success:
                        # If file conversion was successful
                        self._log("Successfully ran worker process '{}' on file '{}'".format(plugin_module.get('plugin_id'),
                                                                                             data.get("file_in")))
                        # Ensure the 'file_out' that was specified by the plugin to be created was actually created.
                        if os.path.exists(data.get('file_out')):
                            # The outfile exists...
                            # In order to clean up as we go and avoid unnecessary RAM/disk use in the cache directory,
                            #   we want to removed the 'file_in' file.
                            # We want to ensure that we do not accidentally remove any original files here.
                            # To avoid this, run x2 tests.
                            # First, check current 'file_in' is not the original file.
                            if os.path.abspath(data.get("file_in")) != os.path.abspath(original_abspath):
                                # Second, check that the 'file_in' is in cache directory.
                                if "unmanic_file_conversion" in os.path.abspath(data.get("file_in")):
                                    # Remove this file
                                    os.remove(os.path.abspath(data.get("file_in")))

                            # Set the new 'file_in' as the previous runner's 'file_out' for the next loop
                            file_in = data.get("file_out")
                    else:
                        # If file conversion was successful
                        self._log(
                            "Error while running worker process '{}' on file '{}'".format(
                                plugin_module.get('plugin_id'),
                                original_abspath
                            ),
                            level="error")
                        self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = False
                        overall_success = False

                        # Ensure the new 'file_in' is set to the previous runner's 'file_in' for the next loop
                        file_in = data.get("file_in")
                else:
                    # Ensure the new 'file_in' is set to the previous runner's 'file_in' for the next loop
                    file_in = data.get("file_in")
                    # Log that this plugin did not request to execute anything
                    self.worker_log.append("\nRunner did not request for Unmanic to execute a command")
                    self._log(
                        "Worker process '{}' did not request to execute a command.".format(plugin_module.get('plugin_id')),
                        level='debug')

                if os.path.exists(data.get('file_out')):
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

            self.worker_runners_info[plugin_module.get('plugin_id')]['success'] = True
            self.worker_runners_info[plugin_module.get('plugin_id')]['status'] = 'complete'

        # Log if no command was run by any Plugins
        if no_exec_command_run:
            # If no jobs were carried out on this task
            self._log("No Plugin requested for Unmanic to run commands for this file '{}'".format(original_abspath), level='warning')
            self.worker_log.append("\n\nNo Plugin requested for Unmanic to run commands for this file '{}'".format(original_abspath))

        # Save the completed command log
        self.current_task.save_command_log(self.worker_log)

        # If all plugins that were executed completed successfully, then this was overall a successful task.
        # At this point we need to move the final out file to the original task cache path so the postprocessor can collect it.
        if overall_success:
            # If jobs carried out on this task were all successful, we will get here
            self._log("Successfully completed Worker processing on file '{}'".format(original_abspath))

            # Attempt to move the final output file to the final cache file path for the postprocessor
            try:
                # Set the new file out as the extension may have changed
                split_file_name = os.path.splitext(current_file_out)
                file_extension = split_file_name[1].lstrip('.')
                cache_directory = os.path.dirname(os.path.abspath(task_cache_path))
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
                return False

            # Return True
            return True

        # If the overall result of the jobs carried out on this task were not successful, we will get here.
        # Log the failure and return False
        self._log("Failed to process task for file '{}'".format(original_abspath), level='warning')
        return False

    def __log_proc_terminated(self, proc):
        self._log("Process {} terminated with exit code {}".format(proc, proc.returncode))

    def __terminate_proc_tree(self, proc: psutil.Process):
        """
        Terminate the process tree (including grandchildren).
        Processes that fail to stop with SIGTERM will be sent a SIGKILL.

        :param proc:
        :return:
        """

        children = proc.children(recursive=True)
        children.append(proc)
        for p in children:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass
        gone, alive = psutil.wait_procs(children, timeout=3, callback=self.__log_proc_terminated)
        for p in alive:
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
        psutil.wait_procs(alive, timeout=3, callback=self.__log_proc_terminated)

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
        command_progress_parser = data.get("command_progress_parser", default_progress_parser)

        # Log the command for debugging
        command_string = exec_command
        if isinstance(exec_command, list):
            command_string = ' '.join(exec_command)
        self._log("Executing: {}".format(command_string), level='debug')

        # Append start of command to worker subprocess stdout
        self.worker_log += [
            '\n\n',
            'COMMAND:\n',
            command_string,
            '\n\n',
            'LOG:\n',
        ]

        # Create output path if not exists
        common.ensure_dir(data.get("file_out"))

        # Convert file
        try:
            proc_pause_time = 0
            proc_start_time = time.time()
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

            # Record PID and PROC
            self.worker_subprocess = sub_proc
            self.worker_subprocess_pid = sub_proc.pid

            # Poll process for new output until finished
            while not self.redundant_flag.is_set():
                line_text = sub_proc.stdout.readline()

                # Fetch command stdout and append it to the current task object (to be saved during post process)
                self.worker_log.append(line_text)

                # Check if the command has completed. If it has, exit the loop
                if line_text == '' and sub_proc.poll() is not None:
                    self._log("Subprocess task completed!", level='debug')
                    break

                # Parse the progress
                try:
                    progress_dict = command_progress_parser(line_text)
                    self.worker_subprocess_percent = progress_dict.get('percent', '0')
                    self.worker_subprocess_elapsed = str(time.time() - proc_start_time - proc_pause_time)
                except Exception as e:
                    # Only need to show any sort of exception if we have debugging enabled.
                    # So we should log it as a debug rather than an exception.
                    self._log("Exception while parsing command progress", str(e), level='debug')

                # Stop the process if the worker is paused
                # Then resume it when the worker is resumed
                if self.paused_flag.is_set():
                    self._log("Pausing PID {}".format(sub_proc.pid), level='debug')
                    proc.suspend()
                    self.paused = True
                    start_pause = time.time()
                    while not self.redundant_flag.is_set():
                        self.event.wait(1)
                        if not self.paused_flag.is_set():
                            self._log("Resuming PID {}".format(sub_proc.pid), level='debug')
                            proc.resume()
                            self.paused = False
                            # Elapsed time is used for calculating etc.
                            # We account for this by counting the time we are paused also.
                            # This is then subtracted from the elapsed time in the calculation above.
                            proc_pause_time = int(proc_pause_time + time.time() - start_pause)
                            break
                        continue

            # Get the final output and the exit status
            if not self.redundant_flag.is_set():
                communicate = sub_proc.communicate()[0]

            # If the process is still running, kill it
            if proc.is_running():
                self._log("Found worker subprocess is still running. Killing it.", level='warning')
                self.__terminate_proc_tree(proc)

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

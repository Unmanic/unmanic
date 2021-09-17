#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.foreman.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     02 Jan 2019, (7:21 AM)

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
import json
import threading
import queue
import time

from unmanic.libs import common
from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.workers import Worker


class Foreman(threading.Thread):
    def __init__(self, data_queues, settings, task_queue):
        super(Foreman, self).__init__(name='Foreman')
        self.settings = settings
        self.task_queue = task_queue
        self.data_queues = data_queues
        self.logger = data_queues["logging"].get_logger(self.name)
        self.workers_pending_task_queue = queue.Queue(maxsize=1)
        self.complete_queue = queue.Queue()
        self.worker_threads = {}
        self.remove_list = []
        self.abort_flag = threading.Event()
        self.abort_flag.clear()

        # Set the current plugin config
        self.plugin_config = {
            'settings':      {},
            'settings_hash': ''
        }
        self.plugin_configuration_changed()

    def _log(self, message, message2=None, level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()
        # Stop all workers
        # To avoid having the dictionary change size during iteration,
        #   we need to first get the thread_keys, then iterate through that
        thread_keys = [t for t in self.worker_threads]
        for thread in thread_keys:
            self.mark_worker_thread_as_redundant(thread)

    def get_worker_count(self):
        """Returns the worker count as an integer"""
        return int(self.settings.get_number_of_workers())

    def save_plugin_config(self, settings=None, settings_hash=None):
        if settings:
            self.plugin_config['settings'] = settings
        if settings_hash:
            self.plugin_config['settings_hash'] = settings_hash
        self._log('Updated plugin config', message2=self.plugin_config, level='debug')

    def get_current_plugin_configuration(self):
        plugin_handler = PluginsHandler()
        all_plugin_settings = plugin_handler.get_settings_of_all_enabled_plugins()
        return all_plugin_settings

    def plugin_configuration_changed(self):
        current_plugin_settings = self.get_current_plugin_configuration()
        # Compare current settings with foreman recorded settings.
        json_encoded_settings = json.dumps(current_plugin_settings, sort_keys=True).encode()
        current_settings_hash = hashlib.md5(json_encoded_settings).hexdigest()
        if current_settings_hash == self.plugin_config.get('settings_hash', ''):
            return False
        # Record current settings
        self.save_plugin_config(settings=current_plugin_settings, settings_hash=current_settings_hash)
        # Settings have changed
        return True

    def validate_worker_config(self):
        valid = True
        frontend_messages = self.data_queues.get('frontend_messages')

        # Ensure that the enabled plugins are compatible with the PluginHandler version
        plugin_handler = PluginsHandler()
        if plugin_handler.get_incompatible_enabled_plugins(frontend_messages):
            valid = False
        if not plugin_handler.within_enabled_plugin_limits(frontend_messages):
            valid = False

        # Check if plugin configuration has been modified. If it has, stop the workers.
        # What we want to avoid here is someone partially modifying the plugin configuration
        #   and having the workers pickup a job mid configuration.
        if self.plugin_configuration_changed():
            # Generate a frontend message and falsify validation
            frontend_messages.put(
                {
                    'id':      'pluginSettingsChangeWorkersStopped',
                    'type':    'warning',
                    'code':    'pluginSettingsChangeWorkersStopped',
                    'message': '',
                    'timeout': 0
                }
            )
            valid = False

        return valid

    def init_worker_threads(self):
        # Remove any redundant idle workers from our list
        # To avoid having the dictionary change size during iteration,
        #   we need to first get the thread_keys, then iterate through that
        thread_keys = [t for t in self.worker_threads]
        for thread in thread_keys:
            if thread in self.worker_threads:
                if not self.worker_threads[thread].is_alive():
                    del self.worker_threads[thread]

        # Check that we have enough workers running. Spawn new ones as required.
        if len(self.worker_threads) < self.get_worker_count():
            self._log("Foreman Threads under the configured limit. Spawning more...")
            # Not enough workers, create some
            for i in range(self.get_worker_count()):
                worker_id = "W{}".format(i)
                if worker_id not in self.worker_threads:
                    # This worker does not yet exists, create it
                    self.start_worker_thread(worker_id)

        # Check if we have to many workers running and stop the ones that are idle
        if len(self.worker_threads) > self.get_worker_count():
            self._log("Foreman Threads exceed the configured limit. Marking some for removal...", level='debug')
            # Too many workers, stop any idle ones
            for thread in self.worker_threads:
                if self.worker_threads[thread].idle:
                    # This thread id is greater than the max number available. We should set it as redundant
                    self.mark_worker_thread_as_redundant(thread)

    def pause_all_worker_threads(self):
        """Pause all threads"""
        result = True
        for thread in self.worker_threads:
            if not self.pause_worker_thread(thread):
                result = False
        return result

    def resume_all_worker_threads(self):
        """Resume all threads"""
        result = True
        for thread in self.worker_threads:
            if not self.resume_worker_thread(thread):
                result = False
        return result

    def start_worker_thread(self, worker_id):
        thread = Worker(worker_id, "Worker-{}".format(worker_id), self.workers_pending_task_queue, self.complete_queue)
        thread.daemon = True
        thread.start()
        self.worker_threads[worker_id] = thread

    def check_for_idle_workers(self):
        for thread in self.worker_threads:
            if self.worker_threads[thread].idle and self.worker_threads[thread].is_alive():
                if not self.worker_threads[thread].paused:
                    return True
        return False

    def postprocessor_queue_full(self):
        """
        Check if Post-processor queue is greater than the number of workers enabled.pluginEnabledLimits
        If it is, return True. Else False.

        :return:
        """
        frontend_messages = self.data_queues.get('frontend_messages')
        limit = self.get_worker_count()
        if len(self.task_queue.list_processed_tasks()) > limit:
            self._log("Postprocessor queue is over {}. Halting feeding workers until it drops.".format(limit), level='warning')
            frontend_messages.update(
                {
                    'id':      'pendingTaskHaltedPostProcessorQueueFull',
                    'type':    'status',
                    'code':    'pendingTaskHaltedPostProcessorQueueFull',
                    'message': '',
                    'timeout': 0
                }
            )
            return True

        # Remove the status notification
        frontend_messages.remove_item('pendingTaskHaltedPostProcessorQueueFull')
        return False

    def pause_worker_thread(self, worker_id):
        """
        Pauses a single worker thread

        :param worker_id:
        :type worker_id:
        :return:
        :rtype:
        """
        self._log("Asked to pause Worker ID '{}'".format(worker_id), level='debug')
        if worker_id not in self.worker_threads:
            self._log("Asked to pause Worker ID '{}', but this was not found.".format(worker_id), level='warning')
            return False

        self.worker_threads[worker_id].paused_flag.set()
        return True

    def resume_worker_thread(self, worker_id):
        """
        Resume a single worker thread

        :param worker_id:
        :type worker_id:
        :return:
        :rtype:
        """
        self._log("Asked to resume Worker ID '{}'".format(worker_id), level='debug')
        if worker_id not in self.worker_threads:
            self._log("Asked to resume Worker ID '{}', but this was not found.".format(worker_id), level='warning')
            return False

        self.worker_threads[worker_id].paused_flag.clear()
        return True

    def terminate_worker_thread(self, worker_id):
        """
        Terminate a single worker thread

        :param worker_id:
        :type worker_id:
        :return:
        :rtype:
        """
        self._log("Asked to terminate Worker ID '{}'".format(worker_id), level='debug')
        if worker_id not in self.worker_threads:
            self._log("Asked to terminate Worker ID '{}', but this was not found.".format(worker_id), level='warning')
            return False

        self.mark_worker_thread_as_redundant(worker_id)
        return True

    def mark_worker_thread_as_redundant(self, worker_id):
        self.worker_threads[worker_id].redundant_flag.set()
        self.remove_list.append(worker_id)

    def add_to_task_queue(self, item):
        self.workers_pending_task_queue.put(item)

    def run(self):
        self._log("Starting Foreman Monitor loop")
        try:
            while not self.abort_flag.is_set():
                time.sleep(1)

                # Fetch all completed tasks from workers
                while not self.abort_flag.is_set() and not self.complete_queue.empty():
                    time.sleep(.2)
                    try:
                        task_item = self.complete_queue.get_nowait()
                        task_item.set_status('processed')
                    except queue.Empty:
                        continue
                    except Exception as e:
                        self._log("Exception when fetching completed task report from worker", message2=str(e),
                                  level="exception")

                # Setup the correct number of workers
                if not self.abort_flag.is_set():
                    self.init_worker_threads()

                # If the worker config is not valid, then pause all workers until it is
                if not self.validate_worker_config():
                    # Pause all workers
                    self.pause_all_worker_threads()
                    continue

                if not self.abort_flag.is_set() and not self.task_queue.task_list_pending_is_empty():

                    # Check if there are any free workers
                    if not self.check_for_idle_workers():
                        # All workers are currently busy
                        time.sleep(1)
                        continue

                    # Check if we are able to start up a worker for another encoding job
                    if self.workers_pending_task_queue.full():
                        continue

                    # Check if postprocessor task queue is full
                    if self.postprocessor_queue_full():
                        time.sleep(3)
                        continue

                    next_item_to_process = self.task_queue.get_next_pending_tasks()
                    if next_item_to_process:
                        try:
                            self._log("Processing item - {}".format(next_item_to_process.get_source_abspath()))
                        except Exception as e:
                            self._log("Exception in fetching task absolute path", message2=str(e), level="exception")
                        self.add_to_task_queue(next_item_to_process)
        except Exception as e:
            self.stop()
            raise Exception(e)

        self._log("Leaving Foreman Monitor loop...")

    def get_all_worker_status(self):
        all_status = []
        for thread in self.worker_threads:
            all_status.append(self.worker_threads[thread].get_status())
        return all_status

    def get_worker_status(self, worker_id):
        result = {}
        for thread in self.worker_threads:
            if int(worker_id) == int(thread):
                result = self.worker_threads[thread].get_status()
        return result

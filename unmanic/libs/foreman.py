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
from datetime import datetime, timedelta

from unmanic.libs import common, installation_link
from unmanic.libs.library import Library
from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.worker_group import WorkerGroup
from unmanic.libs.workers import Worker


class Foreman(threading.Thread):
    def __init__(self, data_queues, settings, task_queue, event):
        super(Foreman, self).__init__(name='Foreman')
        self.settings = settings
        self.event = event
        self.task_queue = task_queue
        self.data_queues = data_queues
        self.logger = data_queues["logging"].get_logger(self.name)
        self.workers_pending_task_queue = queue.Queue(maxsize=1)
        self.remote_workers_pending_task_queue = queue.Queue(maxsize=1)
        self.complete_queue = queue.Queue()
        self.worker_threads = {}
        self.remote_task_manager_threads = {}
        self.abort_flag = threading.Event()
        self.abort_flag.clear()

        # Set the current plugin config
        self.current_config = {
            'settings':      {},
            'settings_hash': ''
        }
        self.configuration_changed()

        # Set the current time for scheduler
        self.last_schedule_run = datetime.today().strftime('%H:%M')

        self.links = installation_link.Links()
        self.link_heartbeat_last_run = 0
        self.available_remote_managers = {}

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
        # Stop all remote link manager threads
        thread_keys = [t for t in self.remote_task_manager_threads]
        for thread in thread_keys:
            self.mark_remote_task_manager_thread_as_redundant(thread)

    def get_total_worker_count(self):
        """Returns the worker count as an integer"""
        worker_count = 0
        for worker_group in WorkerGroup.get_all_worker_groups():
            worker_count += worker_group.get('number_of_workers', 0)
        return int(worker_count)

    def save_current_config(self, settings=None, settings_hash=None):
        if settings:
            self.current_config['settings'] = settings
        if settings_hash:
            self.current_config['settings_hash'] = settings_hash
        self._log('Updated config. If this is modified, all workers will be paused', level='debug')

    def get_current_library_configuration(self):
        # Fetch all libraries
        all_plugin_settings = {}
        for library in Library.get_all_libraries():
            try:
                library_config = Library(library.get('id'))
            except Exception as e:
                self._log("Unable to fetch library config for ID {}".format(library.get('id')), level='exception')
                continue
            # Get list of enabled plugins with their settings
            enabled_plugins = []
            for enabled_plugin in library_config.get_enabled_plugins(include_settings=True):
                enabled_plugins.append({
                    'plugin_id': enabled_plugin.get('plugin_id'),
                    'settings':  enabled_plugin.get('settings'),
                })

            # Get the plugin flow
            plugin_flow = library_config.get_plugin_flow()

            # Append this library's plugin config and flow the the dictionary
            all_plugin_settings[library.get('id')] = {
                'enabled_plugins': enabled_plugins,
                'plugin_flow':     plugin_flow,
            }
        return all_plugin_settings

    def configuration_changed(self):
        current_settings = self.get_current_library_configuration()
        # Compare current settings with foreman recorded settings.
        json_encoded_settings = json.dumps(current_settings, sort_keys=True).encode()
        current_settings_hash = hashlib.md5(json_encoded_settings).hexdigest()
        if current_settings_hash == self.current_config.get('settings_hash', ''):
            return False
        # Record current settings
        self.save_current_config(settings=current_settings, settings_hash=current_settings_hash)
        # Settings have changed
        return True

    def validate_worker_config(self):
        valid = True
        frontend_messages = self.data_queues.get('frontend_messages')

        # Ensure that the enabled plugins are compatible with the PluginHandler version
        plugin_handler = PluginsHandler()
        if plugin_handler.get_incompatible_enabled_plugins(frontend_messages):
            valid = False
        if not self.links.within_enabled_link_limits(frontend_messages):
            valid = False

        # Check if plugin configuration has been modified. If it has, stop the workers.
        # What we want to avoid here is someone partially modifying the plugin configuration
        #   and having the workers pickup a job mid configuration.
        if self.configuration_changed():
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

        # Ensure library config is within limits
        if not Library.within_library_count_limits(frontend_messages):
            valid = False

        return valid

    def run_task(self, time_now, task, worker_count, worker_group):
        worker_group_id = worker_group.get_id()
        self.last_schedule_run = time_now
        if task == 'pause':
            # Pause all workers now
            self._log("Running scheduled event - Pause all worker threads", level='debug')
            self.pause_all_worker_threads(worker_group_id=worker_group_id)
        elif task == 'resume':
            # Resume all workers now
            self._log("Running scheduled event - Resume all worker threads", level='debug')
            self.resume_all_worker_threads(worker_group_id=worker_group_id)
        elif task == 'count':
            # Set the worker count value
            # Save the settings so this scheduled event will persist an application restart
            self._log("Running scheduled event - Setting worker count to '{}'".format(worker_count), level='debug')
            worker_group.set_number_of_workers(worker_count)
            worker_group.save()

    def manage_event_schedules(self):
        """
        Manage all scheduled worker events
        This function limits itself to run only once every 60 seconds

        :return:
        """
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_of_week = datetime.today().today().weekday()
        time_now = datetime.today().strftime('%H:%M')

        # Only run once a minute
        if time_now == self.last_schedule_run:
            return

        for wg in WorkerGroup.get_all_worker_groups():
            try:
                worker_group = WorkerGroup(group_id=wg.get('id'))
                event_schedules = worker_group.get_worker_event_schedules()
            except Exception as e:
                self._log("While iterating through the worker groups, the worker group disappeared", str(e), level='debug')
                continue

            for event_schedule in event_schedules:
                schedule_time = event_schedule.get('schedule_time')
                # Ensure we have a schedule time
                if not schedule_time:
                    continue
                # Ensure the schedule time is now
                if time_now != schedule_time:
                    continue

                repetition = event_schedule.get('repetition')
                # Ensure we have a repetition
                if not repetition:
                    continue

                # Check if it should run
                if repetition == 'daily':
                    self.run_task(time_now, event_schedule.get('schedule_task'), event_schedule.get('schedule_worker_count'),
                                  worker_group)
                elif repetition == 'weekday' and days[day_of_week] not in ['saturday', 'sunday']:
                    self.run_task(time_now, event_schedule.get('schedule_task'), event_schedule.get('schedule_worker_count'),
                                  worker_group)
                elif repetition == 'weekend' and days[day_of_week] in ['saturday', 'sunday']:
                    self.run_task(time_now, event_schedule.get('schedule_task'), event_schedule.get('schedule_worker_count'),
                                  worker_group)
                elif repetition == days[day_of_week]:
                    self.run_task(time_now, event_schedule.get('schedule_task'), event_schedule.get('schedule_worker_count'),
                                  worker_group)

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
        worker_group_ids = []
        worker_group_names = []
        for worker_group in WorkerGroup.get_all_worker_groups():
            worker_group_ids.append(worker_group.get('id'))

            # Create threads as required
            for i in range(worker_group.get('number_of_workers')):
                worker_id = "{}-{}".format(worker_group.get('name'), i)
                worker_name = "{}-Worker-{}".format(worker_group.get('name'), (i + 1))
                # Add this name to a list. If the name changes, we can remove old incorrectly named workers
                worker_group_names.append(worker_name)
                if worker_id not in self.worker_threads:
                    # This worker does not yet exist, create it
                    self.start_worker_thread(worker_id, worker_name, worker_group.get('id'))

            # Remove any workers that do not belong. The max number of supported workers is 12
            for i in range(worker_group.get('number_of_workers'), 12):
                worker_id = "{}-{}".format(worker_group.get('name'), i)
                if worker_id in self.worker_threads:
                    # Only remove threads that are idle (never terminate a task just to reduce worker count)
                    if self.worker_threads[worker_id].idle:
                        self.mark_worker_thread_as_redundant(worker_id)

        # Remove workers for groups that no longer exist
        for thread in self.worker_threads:
            worker_group_id = self.worker_threads[thread].worker_group_id
            worker_name = self.worker_threads[thread].name
            if worker_group_id not in worker_group_ids or worker_name not in worker_group_names:
                # Only remove threads that are idle (never terminate a task just to reduce worker count)
                if self.worker_threads[thread].idle:
                    self.mark_worker_thread_as_redundant(thread)

    def fetch_available_remote_installation(self, library_name=None):
        # Fetch the first matching remote worker from the list
        assigned_installation_id = None
        assigned_installation_info = {}
        installation_ids = [t for t in self.available_remote_managers]
        for installation_id in installation_ids:
            if installation_id not in self.remote_task_manager_threads:
                # Check that a remote worker is on an installation with a matching library name
                installation_library_names = self.available_remote_managers[installation_id].get('library_names', [])
                if library_name is not None and library_name not in installation_library_names:
                    continue
                assigned_installation_info = self.available_remote_managers[installation_id]
                assigned_installation_id = installation_id
                break
        return assigned_installation_id, assigned_installation_info

    def init_remote_task_manager_thread(self, library_name=None):
        # Fetch the installation ID and info
        installation_id, installation_info = self.fetch_available_remote_installation(library_name=library_name)
        del self.available_remote_managers[installation_id]

        # Ensure a worker was assigned
        if not installation_info:
            return False

        # Startup a thread
        thread = installation_link.RemoteTaskManager(installation_id,
                                                     "RemoteTaskManager-{}".format(installation_id),
                                                     installation_info,
                                                     self.remote_workers_pending_task_queue,
                                                     self.complete_queue,
                                                     self.event)
        thread.daemon = True
        thread.start()
        self.remote_task_manager_threads[installation_id] = thread
        return True

    def remove_stale_available_remote_managers(self):
        """
        Loop over the current list of available remote managers and remove any that were marked available over X seconds ago
        This ensures that the data on these manager info lists are up-to-date if the remote installation config changes.

        :return:
        """
        installation_ids = [t for t in self.available_remote_managers]
        for installation_id in installation_ids:
            if installation_id not in self.remote_task_manager_threads:
                # Check that a remote worker is on an installation with a matching library name
                installation_info = self.available_remote_managers[installation_id]
                if installation_info.get('created') < datetime.now() - timedelta(seconds=30):
                    del self.available_remote_managers[installation_id]

    def remove_stopped_remote_task_manager_threads(self):
        """
        Remove any redundant link managers from our list
        Remove any worker IDs from the remote_task_manager_threads list so they are freed up for another link manager thread

        :return:
        """
        # Remove any redundant link managers from our list
        thread_keys = [t for t in self.remote_task_manager_threads]
        for thread in thread_keys:
            if thread in self.remote_task_manager_threads:
                if not self.remote_task_manager_threads[thread].is_alive():
                    self._log("Removing thread '{}'".format(thread), level='debug')
                    del self.remote_task_manager_threads[thread]
                    continue

    def terminate_unlinked_remote_task_manager_threads(self):
        """
        Mark a manager as redundant if the remote installation configuration has been removed

        :return:
        """
        # Get a list of configured UUIDS
        configured_uuids = {}
        for configured_remote_installation in self.settings.get_remote_installations():
            if configured_remote_installation.get('uuid'):
                configured_uuids[configured_remote_installation.get('uuid')] = configured_remote_installation.get('address')
        # Find and remove any redundant link managers from our list
        term_log_msg = "Remote installation link with {} '{}' has been removed from settings. Marking tread for termination"
        for thread in self.remote_task_manager_threads:
            thread_info = self.remote_task_manager_threads[thread].get_info()
            thread_assigned_uuid = thread_info.get('installation_info', {}).get('uuid')
            thread_assigned_address = thread_info.get('installation_info', {}).get('address')
            # Ensure the UUID is still in our config
            if thread_assigned_uuid not in configured_uuids:
                self.mark_remote_task_manager_thread_as_redundant(thread)
                self._log(term_log_msg.format('UUID', thread_assigned_uuid))
                continue
            # Ensure the configured address has not changed
            configured_address = configured_uuids.get(thread_assigned_uuid)
            if thread_assigned_address not in configured_address:
                self.mark_remote_task_manager_thread_as_redundant(thread)
                self._log(term_log_msg.format('address', thread_assigned_address))
                continue

    def update_remote_worker_availability_status(self):
        """
        Updates the list of available remote managers that can be started

        :return:
        """
        available_installations = self.links.check_remote_installation_for_available_workers()
        for installation_uuid in available_installations:
            remote_address = available_installations[installation_uuid].get('address', '')
            remote_auth = available_installations[installation_uuid].get('auth', 'None')
            remote_username = available_installations[installation_uuid].get('username', '')
            remote_password = available_installations[installation_uuid].get('password', '')
            remote_library_names = available_installations[installation_uuid].get('library_names', [])
            available_slots = available_installations[installation_uuid].get('available_slots', 0)
            for slot_number in range(available_slots):
                remote_manager_id = "{}|M{}".format(installation_uuid, slot_number)
                if remote_manager_id in self.available_remote_managers or remote_manager_id in self.remote_task_manager_threads:
                    # This worker is already managed by a link manager thread or is already in the list of available workers
                    continue
                # Add this remote worker ID to the list of available remote managers
                self.available_remote_managers[remote_manager_id] = {
                    'uuid':          installation_uuid,
                    'address':       remote_address,
                    'auth':          remote_auth,
                    'username':      remote_username,
                    'password':      remote_password,
                    'library_names': remote_library_names,
                    'created':       datetime.now(),
                }

    def start_worker_thread(self, worker_id, worker_name, worker_group):
        thread = Worker(worker_id, worker_name, worker_group, self.workers_pending_task_queue,
                        self.complete_queue, self.event)
        thread.daemon = True
        thread.start()
        self.worker_threads[worker_id] = thread

    def fetch_available_worker_ids(self):
        tread_ids = []
        for thread in self.worker_threads:
            if self.worker_threads[thread].idle and self.worker_threads[thread].is_alive():
                if not self.worker_threads[thread].paused:
                    tread_ids.append(self.worker_threads[thread].thread_id)
        return tread_ids

    def check_for_idle_workers(self):
        for thread in self.worker_threads:
            if self.worker_threads[thread].idle and self.worker_threads[thread].is_alive():
                if not self.worker_threads[thread].paused:
                    return True
        return False

    def check_for_idle_remote_workers(self):
        if self.available_remote_managers:
            return True
        return False

    def get_available_remote_library_names(self):
        library_names = []
        for installation_id in self.available_remote_managers:
            for library_name in self.available_remote_managers[installation_id].get('library_names', []):
                if library_name not in library_names:
                    library_names.append(library_name)
        return library_names

    def get_tags_configured_for_worker(self, worker_id):
        """Fetch the tags for a given worker ID"""
        assigned_worker_group_id = self.worker_threads[worker_id].worker_group_id
        worker_group = WorkerGroup(group_id=assigned_worker_group_id)
        return worker_group.get_tags()

    def postprocessor_queue_full(self):
        """
        Check if Post-processor queue is greater than the number of workers enabled.
        If it is, return True. Else False.

        :return:
        """
        frontend_messages = self.data_queues.get('frontend_messages')
        # Use the configured worker count + 1 as the post-processor queue limit
        limit = (int(self.get_total_worker_count()) + 1)
        # Include a count of all available and busy remote workers for the postprocessor queue limit
        limit += len(self.available_remote_managers)
        limit += len(self.remote_task_manager_threads)
        current_count = len(self.task_queue.list_processed_tasks())
        if current_count > limit:
            msg = "There are currently {} items in the post-processor queue. Halting feeding workers until it drops below {}."
            self._log(msg.format(current_count, limit), level='warning')
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
        if worker_id not in self.worker_threads:
            self._log("Asked to pause Worker ID '{}', but this was not found.".format(worker_id), level='warning')
            return False

        if not self.worker_threads[worker_id].paused_flag.is_set():
            self._log("Asked to pause Worker ID '{}'".format(worker_id), level='debug')
            self.worker_threads[worker_id].paused_flag.set()
        return True

    def pause_all_worker_threads(self, worker_group_id=None):
        """Pause all threads"""
        result = True
        for thread in self.worker_threads:
            # Limit by worker group if requested
            if worker_group_id and self.worker_threads[thread].worker_group_id != worker_group_id:
                continue
            if not self.pause_worker_thread(thread):
                result = False
        return result

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

    def resume_all_worker_threads(self, worker_group_id=None):
        """Resume all threads"""
        result = True
        for thread in self.worker_threads:
            # Limit by worker group if requested
            if worker_group_id and self.worker_threads[thread].worker_group_id != worker_group_id:
                continue
            if not self.resume_worker_thread(thread):
                result = False
        return result

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

    def terminate_all_worker_threads(self):
        """Terminate all threads"""
        result = True
        for thread in self.worker_threads:
            if not self.terminate_worker_thread(thread):
                result = False
        return result

    def mark_worker_thread_as_redundant(self, worker_id):
        self.worker_threads[worker_id].redundant_flag.set()

    def mark_remote_task_manager_thread_as_redundant(self, link_manager_id):
        self.remote_task_manager_threads[link_manager_id].redundant_flag.set()

    def hand_task_to_workers(self, item, local=True, library_name=None, worker_id=None):
        if local:
            # Assign the task to the worker id provided
            if worker_id in self.worker_threads and self.worker_threads[worker_id].is_alive():
                self.worker_threads[worker_id].set_task(item)
            # If the worker thread specified was not available to collect this task, it will be fetched again in the next loop
        else:
            # Place into queue for a remote link manager thread to collect
            self.remote_workers_pending_task_queue.put(item)
            # Spawn link manager thread to pickup task
            if not self.init_remote_task_manager_thread(library_name=library_name):
                # Remove item from queue
                self.remote_workers_pending_task_queue.get_nowait()
                # Return failure. This will cause the item to be re-queued at the bottom of the list
                return False
        return True

    def link_manager_tread_heartbeat(self):
        """
        Run a list of tasks to test the status of our Link Management threads.
        Unlike worker threads, Link Management threads live and die for a single task.
        If a Link Management thread is alive for more than 10 seconds without picking up a task, it will die.
        This function will reap all dead or completed threads and clean up issues where a thread may have died
            before running a task that was added to the pending task queue (in which case a new thread should be started)

        :return:
        """
        # Only run heartbeat every 10 seconds
        time_now = time.time()
        if self.link_heartbeat_last_run > (time_now - 10):
            return
        # self._log("Running remote link manager heartbeat", level='debug')
        # Terminate remote manager threads for unlinked installations
        self.terminate_unlinked_remote_task_manager_threads()
        # Clear out dead threads
        self.remove_stopped_remote_task_manager_threads()
        # Clear out old available workers (should last only a minute before being refreshed)
        self.remove_stale_available_remote_managers()
        # Check for updates to the worker availability status of linked remote installations
        self.update_remote_worker_availability_status()
        # Mark this as the last time run
        self.link_heartbeat_last_run = time_now

    def run(self):
        self._log("Starting Foreman Monitor loop")

        # Flag to force checking for idle remote workers when set to False.
        # This will prevent always looping on idle local workers when the local worker's
        # tags prevent them from taking up tasks
        allow_local_idle_worker_check = True

        while not self.abort_flag.is_set():
            self.event.wait(2)

            try:
                # Fetch all completed tasks from workers
                while not self.abort_flag.is_set() and not self.complete_queue.empty():
                    self.event.wait(.5)
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

                # Manage worker event schedules
                self.manage_event_schedules()

                if not self.abort_flag.is_set() and not self.task_queue.task_list_pending_is_empty():

                    # Check the status of all link manager threads (close dead ones)
                    self.link_manager_tread_heartbeat()

                    # Check if we are able to start up a worker for another encoding job
                    # These queues holds only one task at a time and is used to hand tasks to the workers
                    if self.workers_pending_task_queue.full() or self.remote_workers_pending_task_queue.full():
                        # In order to simplify the process and run the foreman management in a single thread, if either of
                        # these are full, it means the thread that is assigned to pick up the item has not done so.
                        # In order to prevent a second thread starting and taking the first thread's task, we should not
                        # process any more pending tasks until that first thread is ready and has taken its task out of the
                        # queue.
                        continue

                    # Check if there are any free workers
                    worker_ids = []
                    if allow_local_idle_worker_check and self.check_for_idle_workers():
                        # Local workers are available
                        process_local = True
                        # For local workers, process either local tasks or tasks provided from a remote installation
                        get_local_pending_tasks_only = False
                        # Specify the worker ID that will handle the next task
                        worker_ids = self.fetch_available_worker_ids()
                        # If not workers were available (possibly due to being recycled), just continue loop
                        if not worker_ids:
                            continue
                    elif self.check_for_idle_remote_workers():
                        allow_local_idle_worker_check = True
                        # Remote workers are available
                        process_local = False
                        # For remote workers, only process local tasks. Don't hand remote tasks to another remote installation
                        get_local_pending_tasks_only = True
                    else:
                        allow_local_idle_worker_check = True
                        # All workers are currently busy
                        self.event.wait(1)
                        continue

                    # Check if postprocessor task queue is full
                    if self.postprocessor_queue_full():
                        self.event.wait(5)
                        continue

                    # Fetch the next item in the queue
                    available_worker_id = None
                    next_item_to_process = None
                    if process_local:
                        # For local processing, ensure tags match the available library and worker
                        for worker_id in worker_ids:
                            try:
                                library_tags = self.get_tags_configured_for_worker(worker_id)
                            except Exception as e:
                                # This will happen if the worker group is deleted
                                self._log("Error while fetching the tags for the configured worker", str(e), level='debug')
                                # Break this fore loop. The main while loop wil clean up these workers on the next pass
                                break
                            next_item_to_process = self.task_queue.get_next_pending_tasks(
                                local_only=get_local_pending_tasks_only,
                                library_tags=library_tags)
                            if next_item_to_process:
                                available_worker_id = worker_id
                                break
                        # If no local worker ID was assigned to the given item, then try again in 2 seconds
                        if not available_worker_id:
                            allow_local_idle_worker_check = False
                            self.event.wait(1)
                            continue
                    else:
                        # For remote items, run a search matching an available remote installation library
                        remote_library_names = self.get_available_remote_library_names()
                        next_item_to_process = self.task_queue.get_next_pending_tasks(local_only=get_local_pending_tasks_only,
                                                                                      library_names=remote_library_names)

                    if next_item_to_process:
                        try:
                            source_abspath = next_item_to_process.get_source_abspath()
                            task_library_name = next_item_to_process.get_task_library_name()
                        except Exception as e:
                            self._log("Exception in fetching task details", message2=str(e), level="exception")
                            self.event.wait(3)
                            continue

                        self._log("Processing item - {}".format(source_abspath))
                        success = self.hand_task_to_workers(next_item_to_process, local=process_local,
                                                            library_name=task_library_name,
                                                            worker_id=available_worker_id)
                        if not success:
                            self._log("Re-queueing tasks. Unable to find worker capable of processing task '{}'".format(
                                next_item_to_process.get_source_abspath()), level="warning")
                            # Re-queue item at the bottom
                            self.task_queue.requeue_tasks_at_bottom(next_item_to_process.get_task_id())
            except Exception as e:
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

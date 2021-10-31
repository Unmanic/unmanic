#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.installation_link.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     28 Oct 2021, (7:24 PM)

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
import json
import os.path
import queue
import threading
import time

import requests
from requests_toolbelt import MultipartEncoder

from unmanic import config
from unmanic.libs import common, session, unlogger
from unmanic.libs.singleton import SingletonType


class Links(object, metaclass=SingletonType):

    def __init__(self, *args, **kwargs):
        self.settings = config.Config()
        self.session = session.Session()
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def __format_address(self, address: str):
        address = address.strip()
        if not address.lower().startswith('http'):
            address = "http://{}".format(address)
        return address

    def __merge_config_dicts(self, config_dict, compare_dict):
        for key in config_dict.keys():
            if config_dict.get(key) != compare_dict.get(key) and compare_dict.get(key) is not None:
                # Apply the new value
                config_dict[key] = compare_dict.get(key)
                # Also flag the dict as updated
                config_dict['last_updated'] = time.time()

    def __generate_default_config(self, config_dict: dict):
        return {
            "address":                config_dict.get('address', '???'),
            "enable_receiving_tasks": config_dict.get('enable_receiving_tasks', False),
            "enable_sending_tasks":   config_dict.get('enable_sending_tasks', False),
            "name":                   config_dict.get('name', '???'),
            "version":                config_dict.get('version', '???'),
            "uuid":                   config_dict.get('uuid', '???'),
            "available":              config_dict.get('available', False),
            "last_updated":           config_dict.get('last_updated', time.time()),
        }

    def remote_api_get(self, remote_url: str, endpoint: str):
        """
        GET to remote installation API

        :param remote_url:
        :param endpoint:
        :return:
        """
        address = self.__format_address(remote_url)
        url = "{}{}".format(address, endpoint)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        return res.json()

    def remote_api_post(self, remote_url: str, endpoint: str, data: dict):
        """
        POST to remote installation API

        :param remote_url:
        :param endpoint:
        :param data:
        :return:
        """
        address = self.__format_address(remote_url)
        url = "{}{}".format(address, endpoint)
        res = requests.post(url, json=data, timeout=2)
        if res.status_code == 200:
            return res.json()
        return {}

    def remote_api_post_file(self, remote_url: str, endpoint: str, path: str):
        """
        Send a file to the remote installation
        No timeout is set so the request will continue until closed

        :param remote_url:
        :param endpoint:
        :param path:
        :return:
        """
        address = self.__format_address(remote_url)
        url = "{}{}".format(address, endpoint)
        # NOTE: If you remove a content type from the upload (text/plain) the file upload fails
        # NOTE2: This method reads the file into memory before uploading. This is slow and
        #   not ideal for devices with small amounts of ram.
        # with open(path, "rb") as f:
        #     # Note: If you remove a content type from this (text/plain) the file upload fails
        #     files = {"fileName": (os.path.basename(path), f, 'text/plain')}
        #     res = requests.post(url, files=files)
        m = MultipartEncoder(fields={'fileName': (os.path.basename(path), open(path, 'rb'), 'text/plain')})
        res = requests.post(url, data=m, headers={'Content-Type': m.content_type})
        if res.status_code == 200:
            return res.json()
        return {}

    def remote_api_delete(self, remote_url: str, endpoint: str, data: dict):
        """
        DELETE to remote installation API

        :param remote_url:
        :param endpoint:
        :param data:
        :return:
        """
        address = self.__format_address(remote_url)
        url = "{}{}".format(address, endpoint)
        res = requests.delete(url, json=data, timeout=2)
        if res.status_code == 200:
            return res.json()
        return {}

    def remote_api_get_download(self, remote_url: str, endpoint: str, path: str):
        address = self.__format_address(remote_url)
        url = "{}{}".format(address, endpoint)
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=None):
                    if chunk:
                        f.write(chunk)
        return True

    def validate_remote_installation(self, address: str):
        """
        Validate a remote Unmanic installation by requesting
        its system info and version

        :param address:
        :return:
        """
        address = self.__format_address(address)

        # Fetch config
        url = "{}/unmanic/api/v2/settings/configuration".format(address)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        system_configuration_data = res.json()

        # Fetch settings
        url = "{}/unmanic/api/v2/settings/read".format(address)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        settings_data = res.json()

        # Fetch version
        url = "{}/unmanic/api/v2/version/read".format(address)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        version_data = res.json()

        # Fetch version
        url = "{}/unmanic/api/v2/session/state".format(address)
        res = requests.get(url, timeout=2)
        if res.status_code != 200:
            return {}
        session_data = res.json()

        return {
            'system_configuration': system_configuration_data.get('configuration'),
            'settings':             settings_data.get('settings'),
            'version':              version_data.get('version'),
            'session':              {
                "level":       session_data.get('level'),
                "picture_uri": session_data.get('picture_uri'),
                "name":        session_data.get('name'),
                "email":       session_data.get('email'),
                "uuid":        session_data.get('uuid'),
            },
        }

    def update_all_remote_installation_links(self):
        """
        Updates the link status and configuration of linked remote installations

        :return:
        """
        save_settings = False
        installation_id_list = []
        remote_installations = []
        for local_config in self.settings.get_remote_installations():
            # Ensure address is not added twice by comparing installation IDs
            if local_config.get('uuid') in installation_id_list and local_config.get('uuid', '???') != '???':
                # Do not update this installation. By doing this it will be removed from the list
                save_settings = True
                continue

            # Ensure the address is something valid
            if not local_config.get('address'):
                save_settings = True
                continue

            # Remove any entries that have an unknown address and uuid
            if local_config.get('address') == '???' and local_config.get('uuid') == '???':
                save_settings = True
                continue

            # Fetch updated data
            installation_data = None
            try:
                installation_data = self.validate_remote_installation(local_config.get('address'))
            except Exception:
                pass

            # Generate updated configured values
            updated_config = self.__generate_default_config(local_config)
            updated_config["available"] = False
            if installation_data:
                # Mark the installation as available
                updated_config["available"] = True

                merge_dict = {
                    "name":    installation_data.get('settings', {}).get('installation_name'),
                    "version": installation_data.get('version'),
                    "uuid":    installation_data.get('session', {}).get('uuid'),
                }
                self.__merge_config_dicts(updated_config, merge_dict)

                # Fetch the corresponding remote configuration for this local installation
                remote_config = self.fetch_remote_installation_link_config_for_this(local_config.get('address'))

                # If the remote configuration is newer than this one, use those values
                # The remote installation will do the same and this will synchronise
                if local_config.get('last_updated', 1) < remote_config.get('last_updated', 1):
                    # Note that the configuration options are reversed when reading from the remote installation config
                    updated_config["enable_receiving_tasks"] = remote_config.get('enable_sending_tasks')
                    updated_config["enable_sending_tasks"] = remote_config.get('enable_receiving_tasks')
                    # Also sync the last_updated flag
                    updated_config['last_updated'] = remote_config.get('last_updated')

                # If the remote config is unable to contact this installation (or it does not have a corresponding config yet)
                #   then also push the configuration
                if not remote_config.get('available'):
                    self.push_remote_installation_link_config(updated_config)

            # Only save to file if the settings have been updated
            if updated_config.get('last_updated') == local_config.get('last_updated'):
                save_settings = True
            remote_installations.append(updated_config)

            # Add UUID to list for next loop
            installation_id_list.append(updated_config.get('uuid', '???'))

        # Update installation data. Only save the config to disk if it was modified
        self.settings.set_config_item('remote_installations', remote_installations, save_settings=save_settings)

        return remote_installations

    def read_remote_installation_link_config(self, uuid):
        """
        Returns the configuration of the remote installation

        :return:
        """
        for remote_installation in self.settings.get_remote_installations():
            if remote_installation.get('uuid') == uuid:
                return remote_installation

        # Ensure we have settings data from the remote installation
        raise Exception("Unable to read installation link configuration.")

    def update_single_remote_installation_link_config(self, configuration: dict):
        """
        Returns the configuration of the remote installation

        :param configuration:
        :return:
        """
        uuid = configuration.get('uuid')
        if not uuid:
            raise Exception("Updating a single installation link configuration requires a UUID.")

        config_exists = False
        remote_installations = []
        for local_config in self.settings.get_remote_installations():
            updated_config = self.__generate_default_config(local_config)

            # If this is the uuid in the config provided, then update our config with the provided values
            if local_config.get('uuid') == uuid:
                config_exists = True
                self.__merge_config_dicts(updated_config, configuration)

            remote_installations.append(updated_config)

        # If the config does not yet exist, the add it now
        if not config_exists:
            remote_installations.append(self.__generate_default_config(configuration))

        # Update installation data and save the config to disk
        self.settings.set_config_item('remote_installations', remote_installations, save_settings=True)

    def fetch_remote_installation_link_config_for_this(self, address: str):
        """
        Fetches and returns the corresponding link configuration from a remote installation

        :param address:
        :return:
        """
        address = self.__format_address(address)
        url = "{}/unmanic/api/v2/settings/link/read".format(address)
        data = {
            "uuid": self.session.uuid
        }
        res = requests.post(url, json=data, timeout=2)
        if res.status_code == 200:
            data = res.json()
            return data.get('link_config')
        return {}

    def push_remote_installation_link_config(self, configuration: dict):
        """
        Pushes the given link config to the remote installation returns the corresponding link configuration from a remote installation

        :param configuration:
        :return:
        """
        address = self.__format_address(configuration.get('address'))
        url = "{}/unmanic/api/v2/settings/link/write".format(address)

        # First generate an updated config
        updated_config = self.__generate_default_config(configuration)

        # Update the bits for the remote instance
        updated_config['uuid'] = self.session.uuid
        updated_config['name'] = self.settings.get_installation_name()
        updated_config['version'] = self.settings.read_version()

        # Configure settings
        updated_config["enable_receiving_tasks"] = configuration.get('enable_sending_tasks')
        updated_config["enable_sending_tasks"] = configuration.get('enable_receiving_tasks')

        # Remove some of the other fields. These will need to be adjusted on the remote instance manually
        del updated_config['address']
        del updated_config['available']

        data = {'link_config': updated_config}
        res = requests.post(url, json=data, timeout=2)
        if res.status_code == 200:
            return True
        return False

    def check_remote_installation_for_available_workers(self):
        """
        Return a list of installations with workers available for a remote task.
        This list is filtered by:
            - Only installations that are available
            - Only installations that are configured for sending tasks to
            - Only installations that have not pending tasks
            - Only installations that have at least one idle worker that is not paused

        :return:
        """
        available_workers = []
        for local_config in self.settings.get_remote_installations():

            # Only installations that are available
            if not local_config.get('available'):
                continue

            # Only installations that are configured for sending tasks to
            if not local_config.get('enable_sending_tasks'):
                continue

            # No valid UUID, no valid connection. This link may still be syncing
            if len(local_config.get('uuid', '')) < 20:
                continue

            try:

                # Only installations that have not pending tasks
                results = self.remote_api_post(local_config.get('address'), '/unmanic/api/v2/pending/tasks', {
                    "start":  0,
                    "length": 1
                })
                if int(results.get('recordsTotal', 0)) > 0:
                    continue

                # Only installations that have at least one idle worker that is not paused
                results = self.remote_api_get(local_config.get('address'), '/unmanic/api/v2/workers/status')
                for worker in results.get('workers_status', []):
                    if worker.get('idle') and not worker.get('paused'):
                        worker['address'] = local_config.get('address')
                        worker['uuid'] = local_config.get('uuid')
                        available_workers.append(worker)
            except Exception as e:
                self._log("Failed to contact remote installation '{}'".format(local_config.get('address')), level='warning')
                continue

        return available_workers

    def send_file_to_remote_installation(self, address: str, path: str):
        """
        Send a file to a remote installation.
        The remote installation will return the ID of a generated task.

        :return:
        """
        return self.remote_api_post_file(address, '/unmanic/api/v2/upload/pending/file', path)

    def remove_task_from_remote_installation(self, address: str, remote_task_id: int):
        """
        Remove a task from the pending queue

        :return:
        """
        data = {
            "id_list": [remote_task_id]
        }
        return self.remote_api_delete(address, '/unmanic/api/v2/pending/tasks', data)

    def get_remote_pending_task_status(self, address: str, remote_task_id: int):
        """
        Get the remote pending task status

        :return:
        """
        data = {
            "id_list": [remote_task_id]
        }
        return self.remote_api_post(address, '/unmanic/api/v2/pending/status/get', data)

    def start_the_remote_task_by_id(self, address: str, remote_task_id: int):
        """
        Start the remote pending task

        :return:
        """
        data = {
            "id_list": [remote_task_id]
        }
        return self.remote_api_post(address, '/unmanic/api/v2/pending/status/set/ready', data)

    def get_single_worker_status(self, address: str, worker_id: str):
        """
        Start the remote pending task

        :return:
        """
        results = self.remote_api_get(address, '/unmanic/api/v2/workers/status')
        for worker in results.get('workers_status', []):
            if worker.get('id') == worker_id:
                return worker
        return {}

    def terminate_remote_worker(self, address: str, worker_id: str):
        """
        Start the remote pending task

        :return:
        """
        data = {
            "worker_id": [worker_id]
        }
        return self.remote_api_delete(address, '/unmanic/api/v2/workers/worker/terminate', data)

    def fetch_remote_task_data(self, address: str, remote_task_id: int, path: str):
        """
        Fetch the completed remote task data

        :param address:
        :param remote_task_id:
        :param path:
        :return:
        """
        task_data = {}
        # Request API generate a DL link
        link_info = self.remote_api_get(address, '/unmanic/api/v2/pending/download/data/id/{}'.format(remote_task_id))
        if link_info.get('link_id'):
            # Download the data file
            res = self.remote_api_get_download(address, '/unmanic/downloads/{}'.format(link_info.get('link_id')), path)
            if res and os.path.exists(path):
                with open(path) as f:
                    task_data = json.load(f)
        return task_data

    def fetch_remote_task_completed_file(self, address: str, remote_task_id: int, path: str):
        """
        Fetch the completed remote task file

        :param address:
        :param remote_task_id:
        :param path:
        :return:
        """
        # Request API generate a DL link
        link_info = self.remote_api_get(address, '/unmanic/api/v2/pending/download/file/id/{}'.format(remote_task_id))
        if link_info.get('link_id'):
            # Download the file
            res = self.remote_api_get_download(address, '/unmanic/downloads/{}'.format(link_info.get('link_id')), path)
            if res and os.path.exists(path):
                return True
        return False


class RemoteTaskManager(threading.Thread):
    paused = False

    current_task = None
    worker_log = None
    start_time = None
    finish_time = None

    worker_subprocess_percent = None
    worker_subprocess_elapsed = None

    worker_runners_info = {}

    def __init__(self, thread_id, name, assigned_worker_info, pending_queue, complete_queue):
        super(RemoteTaskManager, self).__init__(name=name)
        self.thread_id = thread_id
        self.name = name
        self.assigned_worker_info = assigned_worker_info
        self.pending_queue = pending_queue
        self.complete_queue = complete_queue

        self.links = Links()

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
        self._log("Starting remote task manager {} - {}".format(self.thread_id, self.assigned_worker_info.get('address')))
        # A manager should only run for a single task and connection to a single worker.
        # If either of these become unavailable, then the manager should exit

        # Check that the assigned worker is still available
        available_workers = self.links.check_remote_installation_for_available_workers()
        for worker in available_workers:
            remote_worker_id = "{}|{}".format(worker.get('uuid'), worker.get('id'))
            if remote_worker_id != self.thread_id:
                # The worker this manager was assigned is no longer available
                self.redundant_flag.set()
                return

        # Pull task
        try:
            # Pending task queue has an item available. Fetch it.
            next_task = self.pending_queue.get_nowait()

            # Configure worker for this task
            self.__set_current_task(next_task)

            # Process the set task
            self.__process_task_queue_item()

        except queue.Empty:
            self._log("Remote task manager started by the pending queue was empty", level="warning")
        except Exception as e:
            self._log("Exception in processing job with {}:".format(self.name), message2=str(e),
                      level="exception")

        self._log("Stopping remote task manager {} - {}".format(self.thread_id, self.assigned_worker_info.get('address')))

    def __set_current_task(self, current_task):
        """Sets the given task to the worker class"""
        self.current_task = current_task
        self.worker_log = []

    def __unset_current_task(self):
        self.current_task = None
        self.worker_runners_info = {}
        self.worker_log = []

    def __process_task_queue_item(self):
        """
        Processes the set task.

        :return:
        """
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
        success = self.__send_task_to_remote_worker_and_monitor()
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

    def __send_task_to_remote_worker_and_monitor(self):
        """
        Sends the task file to the remote installation to process.
        Monitors progress and then fetches the results

        :return:
        """
        # Set the absolute path to the original file
        original_abspath = self.current_task.get_source_abspath()

        # Set the remote worker address and worker ID
        address = self.assigned_worker_info.get('address')
        worker_id = self.assigned_worker_info.get('id')

        # Get source file checksum
        initial_checksum = common.get_file_checksum(original_abspath)

        # Send a file to a remote installation.
        self._log("Uploading file to remote installation '{}'".format(original_abspath), level='debug')
        info = self.links.send_file_to_remote_installation(address, original_abspath)
        if not info:
            self._log("Failed to upload the file '{}'".format(original_abspath), level='error')
            return False

        remote_task_id = info.get('id')

        # Compare uploaded file md5checksum
        if info.get('checksum') != initial_checksum:
            self._log("The uploaded file did not return a correct checksum '{}'".format(original_abspath), level='error')
            # Send request to terminate the remote worker then return
            self.links.remove_task_from_remote_installation(address, remote_task_id)
            return False

        # Start the remote task
        result = self.links.start_the_remote_task_by_id(address, remote_task_id)
        if not result.get('success'):
            self._log("Failed to set initial remote pending task to status '{}'".format(original_abspath), level='error')
            # Send request to terminate the remote worker then return
            self.links.remove_task_from_remote_installation(address, remote_task_id)
            return False

        # Loop while redundant_flag not set (while true because of below)
        task_complete = False
        last_status_fetch = 0
        failed_status_count = 0
        while not task_complete:
            time.sleep(1)
            if self.redundant_flag.is_set():
                # Send request to terminate the remote worker then exit
                self.links.terminate_remote_worker(address, worker_id)
                break

            # Only fetch the status every 5 seconds
            time_now = time.time()
            if last_status_fetch > (time_now - 5):
                continue

            # Fetch task status
            task_status = self.links.get_remote_pending_task_status(address, remote_task_id)
            task_complete = False
            for ts in task_status.get('results', []):
                if str(ts.get('id')) == str(remote_task_id) and ts.get('status') == 'complete':
                    # Task is complete. Exit loop but do not set redundant flag on link manager
                    task_complete = True
                    break
            if task_complete:
                break

            # Fetch worker progress
            worker_status = self.links.get_single_worker_status(address, worker_id)
            if not worker_status:
                failed_status_count += 1
                # If this count gets above 20, kill the task - we have lost contact
                if failed_status_count > 20:
                    self.redundant_flag.set()
                    # Dont wait for the next loop to terminate the process - cant reach it anyway!
                    break

            # Update status
            self.paused = worker_status.get('paused')
            self.worker_log = worker_status.get('worker_log_tail')
            self.worker_runners_info = worker_status.get('runners_info')
            self.worker_subprocess_percent = worker_status.get('subprocess', {}).get('percent')
            self.worker_subprocess_elapsed = worker_status.get('subprocess', {}).get('elapsed')

            # Mark this as the last time run
            last_status_fetch = time_now

        self._log("Remote task completed '{}'".format(original_abspath), level='info')

        # Create local cache path to download results
        task_cache_path = self.current_task.get_cache_path()
        # Ensure the cache directory exists
        cache_directory = os.path.dirname(os.path.abspath(task_cache_path))
        if not os.path.exists(cache_directory):
            os.makedirs(cache_directory)

        # Fetch remote task result data
        data = self.links.fetch_remote_task_data(address, remote_task_id, os.path.join(cache_directory, 'remote_data.json'))

        if not data:
            self._log(
                "Failed to retrieve remote task data for '{}'. NOTE: The cached files have not been removed from the remote host.".format(
                    original_abspath), level='error')
            return False
        self.worker_log = data.get('log')

        # Save the completed command log
        self.current_task.save_command_log(self.worker_log)

        # Fetch remote task file
        if data.get('task_success'):
            self._log(
                "Remote task was successful, proceeding to download the completed file '{}'".format(data.get('task_label')),
                level='debug')
            # Set the new file out as the extension may have changed
            split_file_name = os.path.splitext(data.get('abspath'))
            file_extension = split_file_name[1].lstrip('.')
            self.current_task.set_cache_path(cache_directory, file_extension)
            # Read the updated cache path
            task_cache_path = self.current_task.get_cache_path()

            # Download the file
            success = self.links.fetch_remote_task_completed_file(address, remote_task_id, task_cache_path)
            if not success:
                self._log("Failed to download file '{}'".format(os.path.basename(data.get('abspath'))), level='error')
                # Send request to terminate the remote worker then return
                self.links.remove_task_from_remote_installation(address, remote_task_id)
                return False

            # Match checksum from task result data with downloaded file
            downloaded_checksum = common.get_file_checksum(task_cache_path)
            if downloaded_checksum != data.get('checksum'):
                self._log("The downloaded file did not produce a correct checksum '{}'".format(task_cache_path),
                          level='error')
                # Send request to terminate the remote worker then return
                self.links.remove_task_from_remote_installation(address, remote_task_id)
                return False

            # Send request to terminate the remote worker then return
            self.links.remove_task_from_remote_installation(address, remote_task_id)

            return True

        return False

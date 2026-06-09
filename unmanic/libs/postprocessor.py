#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.postprocessor.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Apr 2019, (7:33 PM)
 
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
import shutil
import threading
import time

from unmanic import config
from unmanic.libs import common, history
from unmanic.libs.frontend_push_messages import FrontendPushMessages
from unmanic.libs.library import Library
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.metadata import UnmanicFileMetadata
from unmanic.libs.notifications import Notifications
from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.task import TaskDataStore

"""

The post-processor handles all tasks carried out on completion of a workers task.
This may be on either success or failure of the task.

The post-processor runs as a single thread, processing completed jobs one at a time.
This prevents conflicting copy operations or deleting a file that is also being post processed.

"""


class PostProcessError(Exception):
    def __init__(self, expected_var, result_var):
        Exception.__init__(self, "Errors found during post process checks. Expected {}, but instead found {}".format(
            expected_var, result_var))
        self.expected_var = expected_var
        self.result_var = result_var


class PostProcessor(threading.Thread):
    """
    PostProcessor

    """

    def __init__(self, data_queues, task_queue, event):
        super(PostProcessor, self).__init__(name='PostProcessor')
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)
        self.event = event
        self.data_queues = data_queues
        self.settings = config.Config()
        self.task_queue = task_queue
        self.abort_flag = threading.Event()
        self.current_task = None
        self._last_destination_files = []
        self._last_file_move_processes_success = False
        self.ffmpeg = None
        self.abort_flag.clear()

    @staticmethod
    def __path_is_within_directory(path, directory):
        path_real = os.path.realpath(path)
        directory_real = os.path.realpath(directory)
        return path_real == directory_real or path_real.startswith(directory_real + os.sep)

    def __deliver_remote_file(self, cache_path, source_path, destination_path, cache_root):
        """
        Deliver the processed remote-task output from this linked installation.

        This runs on the linked/remote installation after worker processing has
        completed and the final processed file already exists at ``cache_path``.

        There are two delivery modes:
        1. Cache-internal/direct delivery:
           If the destination path is inside this installation's cache root, the
           processed file is moved directly to that destination.
        2. Library/network-share staging:
           If the destination is outside the cache root, the processed file is
           staged into a ``unmanic_remote_pending_library-*`` directory. The OG
           installation can then retrieve it from there, or the staging path can
           be used as a handoff location on a shared library/network path.

        Returns a tuple of ``(move_success, final_destination)`` where
        ``final_destination`` is the actual delivered/staged path on success.
        """
        if not os.path.exists(cache_path):
            self.logger.warning("Final cache file '%s' does not exist!", cache_path)
            return False, None

        if self.__path_is_within_directory(destination_path, cache_root):
            move_success = self.__copy_file(cache_path, destination_path, [], 'DEFAULT', move=True)
            if not move_success:
                self.logger.error(
                    "Failed to deliver processed remote file '%s' to '%s'.", cache_path, destination_path
                )
            return move_success, destination_path if move_success else None

        random_string = '{}-{}'.format(common.random_string(), int(time.time()))
        staging_attempts = [
            (
                "library",
                os.path.join(os.path.dirname(source_path), "unmanic_remote_pending_library-" + random_string)
            ),
            (
                "cache",
                os.path.join(cache_root, "unmanic_remote_pending_library-" + random_string)
            ),
        ]

        for staging_name, staging_dir in staging_attempts:
            staging_target = os.path.join(staging_dir, os.path.basename(cache_path))
            if self.__stage_remote_file(cache_path, staging_name, staging_dir, staging_target):
                return True, staging_target

        return False, None

    def __stage_remote_file(self, cache_path, staging_name, staging_dir, staging_target):
        """
        Stage a processed remote-task file into a temporary handoff directory.

        This helper creates the ``unmanic_remote_pending_library-*`` directory
        and then moves the processed cache file into that directory using the
        standard ``__copy_file(..., move=True)`` logic, which still uses the
        ``.unmanic.part`` temporary-file pattern before final rename.

        ``staging_name`` is used only for logging to indicate whether this is a
        library-adjacent handoff directory or a cache-side fallback handoff
        directory.
        """
        self.logger.debug("Attempting remote staging in %s directory '%s'", staging_name, staging_dir)
        try:
            os.makedirs(staging_dir, exist_ok=False)
        except Exception as e:
            self.logger.warning("Failed to create %s staging directory '%s': %s", staging_name, staging_dir, e)
            return False

        move_success = self.__copy_file(cache_path, staging_target, [], 'DEFAULT', move=True)
        if move_success:
            self.logger.debug("Remote file staged to %s directory '%s'", staging_name, staging_target)
            return True

        self.logger.warning(
            "Failed to deliver processed remote file '%s' to %s staging path '%s'.",
            cache_path,
            staging_name,
            staging_target,
        )
        return False

    def stop(self):
        self.abort_flag.set()

    def run(self):
        self.logger.info("Starting PostProcessor Monitor loop...")
        while not self.abort_flag.is_set():
            self.event.wait(1)

            if not self.system_configuration_is_valid():
                self.event.wait(2)
                continue

            while not self.abort_flag.is_set() and not self.task_queue.task_list_processed_is_empty():
                self.event.wait(.2)
                self.current_task = self.task_queue.get_next_processed_tasks()
                if self.current_task:

                    # Execute event plugin runners
                    plugin_handler = PluginsHandler()
                    plugin_handler.run_event_plugins_for_plugin_type('events.postprocessor_started', {
                        'library_id':  self.current_task.get_task_library_id(),
                        'task_id':     self.current_task.get_task_id(),
                        'task_type':   self.current_task.get_task_type(),
                        'cache_path':  self.current_task.get_cache_path(),
                        'source_data': self.current_task.get_source_data(),
                    })

                    try:
                        self.logger.info("Post-processing task - %s", self.current_task.get_source_abspath())
                    except Exception as e:
                        self.logger.exception("Exception in fetching task absolute path: %s", e)
                    if self.current_task.get_task_type() == 'local':
                        try:
                            # Post processes the converted file (return it to original directory etc.)
                            self.post_process_file()
                        except Exception as e:
                            self.logger.exception("Exception in post-processing local task file: %s", e)
                        try:
                            # Write source and destination data to historic log
                            self.write_history_log()
                        except Exception as e:
                            self.logger.exception("Exception in writing history log: %s", e)
                        try:
                            # Commit task metadata to database after all plugin runners
                            self.commit_task_metadata()
                        except Exception as e:
                            self.logger.exception("Exception in committing task metadata: %s", e)
                        try:
                            # Remove file from task queue
                            self.current_task.delete()
                        except Exception as e:
                            self.logger.exception("Exception in removing task from task list: %s", e)
                    else:
                        try:
                            # Post processes the remote converted file (return it to original directory etc.)
                            self.post_process_remote_file()
                        except Exception as e:
                            self.logger.exception("Exception in post-processing remote task file: %s", e)
                        try:
                            # Write source and destination data to historic log
                            self.dump_history_log()
                        except Exception as e:
                            self.logger.exception("Exception in dumping history log for remote task: %s", e)
                        try:
                            # Update the task status to 'complete'
                            self.current_task.set_status('complete')
                        except Exception as e:
                            self.logger.exception("Exception in marking remote task as complete: %s", e)

        self.logger.info("Leaving PostProcessor Monitor loop...")

    def system_configuration_is_valid(self):
        """
        Check and ensure the system configuration is correct for running

        :return:
        """
        valid = True
        plugin_handler = PluginsHandler()
        if plugin_handler.get_incompatible_enabled_plugins():
            valid = False
        if not Library.within_library_count_limits():
            valid = False
        return valid

    def post_process_file(self):
        # Init plugins handler
        plugin_handler = PluginsHandler()

        # Read current task data
        # task_data = self.current_task.get_task_data()
        library_id = self.current_task.get_task_library_id()
        cache_path = self.current_task.get_cache_path()
        source_data = self.current_task.get_source_data()
        destination_data = self.current_task.get_destination_data()
        # Move file back to original folder and remove source
        file_move_processes_success = True
        # Create a list for filling with destination paths
        destination_files = []
        if self.current_task.task.success:
            # Run a postprocess file movement on the cache file for each plugin that configures it

            # Fetch all 'postprocessor.file_move' plugin modules
            plugin_modules = plugin_handler.get_enabled_plugin_modules_by_type('postprocessor.file_move',
                                                                               library_id=library_id)

            # Check if the source file needs to be removed by default (only if it does not match the destination file)
            remove_source_file = False
            if source_data['abspath'] != destination_data['abspath']:
                remove_source_file = True

            # Set initial data (some fields will be overwritten further down)
            # - 'library_id'                - The library ID for this task
            # - 'source_data'               - Dictionary of data pertaining to the source file
            # - 'remove_source_file'        - True to remove the original file (default is True if file name has changed)
            # - 'copy_file'                 - True to run a plugin initiated file copy (default is False unless the plugin says otherwise)
            # - 'file_in'                   - Source path to copy from (if 'copy_file' is True)
            # - 'file_out'                  - Destination path to copy to (if 'copy_file' is True)
            # - 'run_default_file_copy'     - Prevent the final Unmanic post-process file movement (if different from the original file name)
            data = {
                'library_id':            library_id,
                'task_id':               self.current_task.get_task_id(),
                'source_data':           None,
                'remove_source_file':    remove_source_file,
                'copy_file':             None,
                'file_in':               None,
                'file_out':              None,
                'run_default_file_copy': True,
            }

            for plugin_module in plugin_modules:
                # Always set source_data to the original file's source_data
                data["source_data"] = source_data
                # Always set copy_file to False
                data["copy_file"] = False
                # Always set file in to cache path
                data["file_in"] = cache_path
                # Always set file out to destination data absolute path
                data["file_out"] = destination_data.get('abspath')

                # Run plugin to update data
                if not plugin_handler.exec_plugin_runner(data, plugin_module.get('plugin_id'), 'postprocessor.file_move'):
                    # Do not continue with this plugin module's loop
                    continue

                if data.get('copy_file'):
                    # Copy the file
                    file_in = os.path.abspath(data.get('file_in'))
                    file_out = os.path.abspath(data.get('file_out'))
                    if not self.__copy_file(file_in, file_out, destination_files, plugin_module.get('plugin_id')):
                        file_move_processes_success = False
                else:
                    self.logger.debug(
                        "Plugin did not request a file copy (%s)", plugin_module.get('plugin_id')
                    )

            # Unmanic's default file movement process
            # Only carry out final post-processor file moments if all others were successful
            if file_move_processes_success and data.get('run_default_file_copy'):
                # Run the default post-process file movement.
                # This will always move the file back to the original location.
                # If that original location is the same file name, it will overwrite the original file.
                if destination_data.get('abspath') == source_data.get('abspath'):
                    # Only run the final file copy to overwrite the source file if the remove_source_file flag was never set
                    # The remove_source_file flag will remove the source file in later lines after this copy operation,
                    #   so if we did copy the file here, it would be a waste of time
                    if not data.get('remove_source_file'):
                        if not self.__copy_file(cache_path, destination_data.get('abspath'), destination_files, 'DEFAULT',
                                                move=True):
                            file_move_processes_success = False
                elif not self.__copy_file(cache_path, destination_data.get('abspath'), destination_files, 'DEFAULT',
                                          move=True):
                    file_move_processes_success = False

            # Source file removal process
            # Only run if all final post-processor file moments were successful
            if file_move_processes_success:
                # Check if the remove source flag is still True after all plugins have run. If so, we will remove the source file
                if data.get('remove_source_file'):
                    # Only carry out a source removal if the file exists and the final copy was also successful
                    if file_move_processes_success and os.path.exists(source_data.get('abspath')):
                        self.logger.info("Removing source: %s", source_data.get('abspath'))
                        os.remove(source_data.get('abspath'))
                    else:
                        self.logger.warning(
                            "Keeping source file '%s'. Not all postprocessor file movement functions completed.",
                            source_data.get('abspath'),
                        )

            # Log a final error if not all file moments were successful
            if not file_move_processes_success:
                self.logger.error(
                    "Error while running postprocessor file movement on file '%s'. "
                    "Not all postprocessor file movement functions completed.",
                    cache_path,
                )

        else:
            self.logger.warning(
                "Skipping file movement post-processor as the task was not successful '%s'", cache_path
            )

        # Fetch all 'postprocessor.task_result' plugin modules
        plugin_modules = plugin_handler.get_enabled_plugin_modules_by_type(
            'postprocessor.task_result', library_id=library_id)

        for plugin_module in plugin_modules:
            data = {
                'library_id':                  library_id,
                "task_id":                     self.current_task.get_task_id(),
                "task_type":                   self.current_task.get_task_type(),
                'final_cache_path':            cache_path,
                'task_processing_success':     self.current_task.get_task_success(),
                'file_move_processes_success': file_move_processes_success,
                'destination_files':           destination_files,
                'source_data':                 source_data,
                'start_time':                  self.current_task.get_start_time(),
                'finish_time':                 self.current_task.get_finish_time(),
            }

            # Run plugin to update data
            if not plugin_handler.exec_plugin_runner(data, plugin_module.get('plugin_id'), 'postprocessor.task_result'):
                # Do not continue with this plugin module's loop
                continue

        # Cleanup cache files
        self.__cleanup_cache_files(cache_path)
        self._last_destination_files = destination_files
        self._last_file_move_processes_success = file_move_processes_success

    def post_process_remote_file(self):
        """
        Post-process a task that was executed on a linked/remote installation.

        This function runs on the linked/remote installation after the worker
        has completed processing for a task that originated on the OG installation.

        Its job is not to run postprocessor plugins. Instead, it is responsible
        for safely handing the processed file back toward the OG installation:

        The destination path is derived from the remote task's ``abspath`` plus
        the processed output extension. In practice this reflects how the OG
        installation created the remote task in the first place:

        - If the task file was uploaded to this linked installation, the task
          ``abspath`` lives under this installation's cache area, so the
          derived destination is also inside the cache root. In that case the
          processed file is moved directly to that cache-based destination.
        - If the task was created against a shared library/network path on this
          linked installation, the task ``abspath`` lives on that library/share
          path, so the derived destination is outside the cache root. In that case
          the processed file is staged into a ``unmanic_remote_pending_library-*``
          handoff directory so the OG installation can retrieve it from the
          shared path or fall back to an HTTP download if that fails.

        The remote source file is only removed after a successful cache-internal
        delivery. If delivery fails, the source is retained to avoid data loss.

        :return:
        """
        # Read current task data
        cache_path = self.current_task.get_cache_path()
        source_data = self.current_task.get_source_data()
        destination_data = self.current_task.get_destination_data()
        def_cache_path = self.settings.get_cache_path()

        destination_path = destination_data.get('abspath')
        source_path = source_data.get('abspath')
        remove_source_file = self.__path_is_within_directory(destination_path, def_cache_path)

        self.logger.debug("Cache path: %s", def_cache_path)
        self.logger.debug("Remote source: %s, destination file: %s.", source_path, destination_path)
        self.logger.debug("Task cache path: %s", cache_path)

        move_success, final_destination = self.__deliver_remote_file(
            cache_path, source_path, destination_path, def_cache_path)

        if not os.path.exists(source_path):
            self.logger.warning("Remote source file '%s' does not exist!", source_path)
        elif not remove_source_file:
            self.logger.info("Keep remote source: %s, remote file source is in library and not cache.", source_path)
        elif move_success:
            self.logger.info("Removing remote source: %s", source_path)
            try:
                os.remove(source_path)
            except OSError as e:
                self.logger.error("Failed to remove remote source '%s': %s", source_path, e)
        else:
            self.logger.warning(
                "Retaining remote source '%s' because processed file delivery did not succeed.", source_path
            )

        self.__cleanup_cache_files(cache_path)
        self._last_destination_files = [final_destination] if final_destination else []
        self._last_file_move_processes_success = move_success

        if final_destination:
            self.current_task.modify_path(final_destination)

    def __cleanup_cache_files(self, cache_path):
        """
        Remove cache files and the cache directory
        This ensures we are not simply blindly removing a whole directory.
        It ensures were are in-fact only deleting this task's cache files.

        :param cache_path:
        :return:
        """
        task_cache_directory = os.path.dirname(cache_path)
        if os.path.exists(task_cache_directory) and "unmanic_file_conversion" in task_cache_directory:
            self.logger.info("Removing task cache directory '%s'", task_cache_directory)
            try:
                shutil.rmtree(task_cache_directory)
            except Exception as e:
                self.logger.error("Exception while clearing cache path: %s", e)

    def __copy_file(self, file_in, file_out, destination_files, plugin_id, move=False):
        if move:
            self.logger.info("Move file triggered by (%s) %s --> %s", plugin_id, file_in, file_out)
        else:
            self.logger.info("Copy file triggered by (%s) %s --> %s", plugin_id, file_in, file_out)

        try:
            # Ensure the src and dst are not the same file
            if os.path.exists(file_out) and os.path.samefile(file_in, file_out):
                self.logger.warning(
                    "The file_in and file_out path are the same file. Nothing will be done! '%s'", file_in
                )
                return False

            # Get a checksum prior to copy
            if not os.path.exists(file_in):
                self.logger.warning("The file_in path does not exist! '%s'", file_in)
                self.event.wait(1)
            self.logger.debug("Fetching checksum of source file '%s'.", file_in)

            # Use a '.part' suffix for the file movement, then rename it after
            part_file_out = os.path.join("{}.unmanic.part".format(file_out))

            # Carry out the file movement
            if move:
                self.logger.debug("Moving file '%s' --> '%s'.", file_in, part_file_out)
                if os.path.exists(part_file_out):
                    os.remove(part_file_out)
                shutil.move(file_in, part_file_out, copy_function=shutil.copyfile)
            else:
                self.logger.debug("Copying file '%s' --> '%s'.", file_in, part_file_out)
                shutil.copyfile(file_in, part_file_out)

            # Remove dest file if it already exists (required only for moves)
            if os.path.exists(file_out):
                self.logger.debug("The file_out path already exists. Removing file '%s'", file_out)
                os.remove(file_out)

            # Move file from part to final destination
            self.logger.debug("Renaming file '%s' --> '%s'.", part_file_out, file_out)
            shutil.move(part_file_out, file_out, copy_function=shutil.copyfile)
            # Write final path to destination_files list
            destination_files.append(file_out)
            # Mark move process a success
            return True
        except Exception as e:
            self.logger.exception("Exception while copying file %s to %s: %s", file_in, file_out, e)
            file_move_processes_success = False

        return file_move_processes_success

    def write_history_log(self):
        """
        Record task history

        :return:
        """
        self.logger.debug("Writing task history log.")
        history_logging = history.History()
        task_dump = self.current_task.task_dump()
        destination_data = self.current_task.get_destination_data()
        source_data = self.current_task.get_source_data()

        # If task fails, the add a notification that a task has failed
        if not self.current_task.task.success:
            notifications = Notifications()
            notifications.add(
                {
                    'uuid':       'newFailedTask',
                    'type':       'error',
                    'icon':       'report',
                    'label':      'failedTaskLabel',
                    'message':    'You have a new failed task in your completed tasks list',
                    'navigation': {
                        'push':   '/ui/dashboard',
                        'events': [
                            'completedTasksShowFailed',
                        ],
                    },
                })

        self._log_completed_task_data(task_dump, source_data, destination_data)

        history_logging.save_task_history(
            {
                'task_label':          task_dump.get('task_label', ''),
                'abspath':             task_dump.get('abspath', ''),
                'task_success':        task_dump.get('task_success', False),
                'start_time':          task_dump.get('start_time', ''),
                'finish_time':         task_dump.get('finish_time', ''),
                'processed_by_worker': task_dump.get('processed_by_worker', ''),
                'log':                 task_dump.get('log', ''),
            }
        )

        # Execute event plugin runners
        plugin_handler = PluginsHandler()
        plugin_handler.run_event_plugins_for_plugin_type('events.postprocessor_complete', {
            'library_id':                  self.current_task.get_task_library_id(),
            'task_id':                     self.current_task.get_task_id(),
            'task_type':                   self.current_task.get_task_type(),
            'source_data':                 self.current_task.get_source_data(),
            'destination_data':            self.current_task.get_destination_data(),
            'destination_files':           list(self._last_destination_files or []),
            'task_success':                task_dump.get('task_success', False),
            'file_move_processes_success': self._last_file_move_processes_success,
            'start_time':                  task_dump.get('start_time', ''),
            'finish_time':                 task_dump.get('finish_time', ''),
            'processed_by_worker':         task_dump.get('processed_by_worker', ''),
            'log':                         task_dump.get('log', ''),
        })

    def commit_task_metadata(self):
        """
        Commit task metadata after all postprocessor runners have finished.
        """
        source_data = self.current_task.get_source_data()
        destination_data = self.current_task.get_destination_data()
        task_success = self.current_task.get_task_success()
        destination_files = list(self._last_destination_files or [])
        if not destination_files and destination_data:
            destination_files = [destination_data.get('abspath')]
        committed = UnmanicFileMetadata.commit_task(
            task_id=self.current_task.get_task_id(),
            task_success=task_success,
            source_path=source_data.get('abspath'),
            destination_paths=destination_files,
        )
        if committed:
            self.logger.debug("Committed file metadata entries: %s", committed)
        return committed

    def dump_history_log(self):
        self.logger.debug("Dumping remote task history log.")
        task_dump = self.current_task.task_dump()
        destination_data = self.current_task.get_destination_data()

        # Dump history log & task state as metadata in the file's path
        tasks_data_file = os.path.join(os.path.dirname(destination_data.get('abspath')), 'data.json')
        task_state = TaskDataStore.export_task_state(self.current_task.get_task_id())
        result = common.json_dump_to_file(
            {
                'task_label':          task_dump.get('task_label', ''),
                'abspath':             task_dump.get('abspath', ''),
                'task_success':        task_dump.get('task_success', False),
                'start_time':          task_dump.get('start_time', ''),
                'finish_time':         task_dump.get('finish_time', ''),
                'processed_by_worker': task_dump.get('processed_by_worker', ''),
                'log':                 task_dump.get('log', ''),
                'checksum':            'UNKNOWN',
                'task_state':          task_state,
            }, tasks_data_file)
        if not result['success']:
            for message in result['errors']:
                self.logger.error("Exception: %s", message)
            raise Exception("Exception in dumping completed task data to file")

    def _log_completed_task_data(self, task_dump, source_data, destination_data):
        status = "success" if task_dump.get('task_success', False) else "failed"
        start_time = task_dump.get('start_time', '')
        finish_time = task_dump.get('finish_time', '')
        command_error_log_tail = ""
        if status != "success":
            task_log = task_dump.get('log', '')
            if task_log:
                command_error_log_tail = "\n".join(task_log.splitlines()[-20:])
        try:
            library_id = self.current_task.get_task_library_id()
            library_name = self.current_task.get_task_library_name()
        except Exception:
            library_id = None
            library_name = None

        UnmanicLogging.data(
            "completed_task",
            data_search_key=f"{library_id} | {finish_time} | {source_data.get('abspath', '')}",
            task_id=self.current_task.get_task_id(),
            task_type=self.current_task.get_task_type(),
            library_id=library_id,
            library_name=library_name,
            status=status,
            start_time=start_time,
            finish_time=finish_time,
            source_file=source_data.get('basename', ''),
            source_path=source_data.get('abspath', ''),
            dest_file=destination_data.get('basename', ''),
            dest_path=destination_data.get('abspath', ''),
            command_error_log_tail=command_error_log_tail,
        )

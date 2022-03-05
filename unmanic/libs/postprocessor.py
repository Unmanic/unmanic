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
from unmanic.libs.library import Library
from unmanic.libs.plugins import PluginsHandler

"""

The post-processor handles all tasks carried out on completion of a workers task.
This may be on either success or failure of the task.

The post-processor runs as a single thread, processing completed jobs one at a time.
This prevents conflicting copy operations or deleting a file that is also being post processed.

"""


class PostProcessError(Exception):
    def __init___(self, expected_var, result_var):
        Exception.__init__(self, "Errors found during post process checks. Expected {}, but instead found {}".format(
            expected_var, result_var))
        self.expected_var = expected_var
        self.result_var = result_var


class PostProcessor(threading.Thread):
    """
    PostProcessor

    """

    def __init__(self, data_queues, task_queue):
        super(PostProcessor, self).__init__(name='PostProcessor')
        self.logger = data_queues["logging"].get_logger(self.name)
        self.data_queues = data_queues
        self.settings = config.Config()
        self.task_queue = task_queue
        self.abort_flag = threading.Event()
        self.current_task = None
        self.ffmpeg = None
        self.abort_flag.clear()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        self._log("Starting PostProcessor Monitor loop...")
        while not self.abort_flag.is_set():
            time.sleep(1)

            if not self.system_configuration_is_valid():
                time.sleep(2)
                continue

            while not self.abort_flag.is_set() and not self.task_queue.task_list_processed_is_empty():
                time.sleep(.2)
                self.current_task = self.task_queue.get_next_processed_tasks()
                if self.current_task:
                    try:
                        self._log("Post-processing task - {}".format(self.current_task.get_source_abspath()))
                    except Exception as e:
                        self._log("Exception in fetching task absolute path", message2=str(e), level="exception")
                    if self.current_task.get_task_type() == 'local':
                        # Post process the converted file (return it to original directory etc.)
                        self.post_process_file()
                        # Write source and destination data to historic log
                        self.write_history_log()
                        # Remove file from task queue
                        self.current_task.delete()
                    else:
                        # Post process the remote converted file (return it to original directory etc.)
                        self.post_process_remote_file()
                        # Write source and destination data to historic log
                        self.dump_history_log()
                        # Update the task status to 'complete'
                        self.current_task.set_status('complete')

        self._log("Leaving PostProcessor Monitor loop...")

    def system_configuration_is_valid(self):
        """
        Check and ensure the system configuration is correct for running

        :return:
        """
        valid = True
        plugin_handler = PluginsHandler()
        if plugin_handler.get_incompatible_enabled_plugins(self.data_queues.get('frontend_messages')):
            valid = False
        if not Library.within_library_count_limits(self.data_queues.get('frontend_messages')):
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
            # Run a postprocess file movement on the cache file for for each plugin that configures it

            # Fetch all 'postprocessor.file_move' plugin modules
            plugin_modules = plugin_handler.get_enabled_plugin_modules_by_type('postprocessor.file_move',
                                                                               library_id=library_id)

            # Check if the source file needs to be remove by default (only if it does not match the destination file)
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
                    self._log("Plugin did not request a file copy ({})".format(plugin_module.get('plugin_id')), level='debug')

            # Unmanic's default file movement process
            # Only carry out final post-processor file moments if all others were successful
            if file_move_processes_success and data.get('run_default_file_copy'):
                # Run the default post-process file movement.
                # This will always move the file back to the original location.
                # If that original location is the same file name, it will overwrite the original file.
                if destination_data.get('abspath') == source_data.get('abspath'):
                    # Only run the final file copy to overwrite the source file if the remove_source_file flag was never set
                    if not data.get('remove_source_file'):
                        if not self.__copy_file(cache_path, destination_data.get('abspath'), destination_files, 'DEFAULT'):
                            file_move_processes_success = False
                elif not self.__copy_file(cache_path, destination_data.get('abspath'), destination_files, 'DEFAULT'):
                    file_move_processes_success = False

            # Source file removal process
            # Only run if all final post-processor file moments were successful
            if file_move_processes_success:
                # Check if the remove source flag is still True after all plugins have run. If so, we will remove the source file
                if data.get('remove_source_file'):
                    # Only carry out a source removal if the file exists and the final copy was also successful
                    if file_move_processes_success and os.path.exists(source_data.get('abspath')):
                        self._log("Removing source: {}".format(source_data.get('abspath')))
                        os.remove(source_data.get('abspath'))
                    else:
                        self._log("Keeping source file '{}'. Not all postprocessor file movement functions completed.".format(
                            source_data.get('abspath')), level="warning")

            # Log a final error if not all file moments were successful
            if not file_move_processes_success:
                self._log(
                    "Error while running postprocessor file movement on file '{}'. Not all postprocessor file movement functions completed.".format(
                        cache_path), level="error")

        else:
            self._log("Skipping file movement post-processor as the task was not successful '{}'".format(cache_path),
                      level='warning')

        # Fetch all 'postprocessor.task_result' plugin modules
        plugin_modules = plugin_handler.get_enabled_plugin_modules_by_type('postprocessor.task_result', library_id=library_id)

        for plugin_module in plugin_modules:
            data = {
                'library_id':                  library_id,
                'source_data':                 source_data,
                'task_processing_success':     self.current_task.task.success,
                'file_move_processes_success': file_move_processes_success,
                'destination_files':           destination_files,
            }

            # Run plugin to update data
            if not plugin_handler.exec_plugin_runner(data, plugin_module.get('plugin_id'), 'postprocessor.task_result'):
                # Do not continue with this plugin module's loop
                continue

        # Cleanup cache files
        self.__cleanup_cache_files(cache_path)

    def post_process_remote_file(self):
        """
        Process remote files.
        Remote files are not processed by plugins.

        TODO: Should we move remote tasks to a permanent download location within the cache path? Possibly not...

        :return:
        """
        # Read current task data
        cache_path = self.current_task.get_cache_path()
        source_data = self.current_task.get_source_data()
        destination_data = self.current_task.get_destination_data()

        # Remove the source
        if os.path.exists(source_data.get('abspath')):
            self._log("Removing remote source: {}".format(source_data.get('abspath')))
            os.remove(source_data.get('abspath'))
        else:
            self._log("Remote source file '{}' does not exist!".format(source_data.get('abspath')), level="warning")

        # Copy final cache file to original directory
        self.__copy_file(cache_path, destination_data.get('abspath'), [], 'DEFAULT')

        # Cleanup cache files
        self.__cleanup_cache_files(cache_path)

        # Modify the task abspath - this may be different now
        self.current_task.modify_path(destination_data.get('abspath'))

    def __cleanup_cache_files(self, cache_path):
        """
        Remove cache files and the cache directory
        This ensure we are not simply blindly removing a whole directory.
        It ensures were are in-fact only deleting this task's cache files.

        :param cache_path:
        :return:
        """
        task_cache_directory = os.path.dirname(cache_path)
        if os.path.exists(task_cache_directory) and "unmanic_file_conversion" in task_cache_directory:
            self._log("Removing task cache directory '{}'".format(task_cache_directory))
            try:
                shutil.rmtree(task_cache_directory)
            except Exception as e:
                self._log("Exception while clearing cache path '{}'".format(str(e)), level='error')

    def __copy_file(self, file_in, file_out, destination_files, plugin_id):
        self._log("Copy file triggered by ({}) {} --> {}".format(plugin_id, file_in, file_out))
        try:
            before_checksum = common.get_file_checksum(file_in)
            if not os.path.exists(file_in):
                self._log("Error - file_in path does not exist! '{}'".format(file_in), level="error")
                time.sleep(1)
            shutil.copyfile(file_in, file_out)
            after_checksum = common.get_file_checksum(file_out)
            # Compare the checksums on the copied file to ensure it is still correct
            if before_checksum != after_checksum:
                # Something went wrong during that file copy
                self._log("Copy function failed during postprocessor file movement '{}' on file '{}'".format(
                    plugin_id, file_in), level='warning')
                file_move_processes_success = False
            else:
                destination_files.append(file_out)
                file_move_processes_success = True
        except Exception as e:
            self._log("Exception while copying file {} to {}:".format(file_in, file_out),
                      message2=str(e), level="exception")
            file_move_processes_success = False

        return file_move_processes_success

    def write_history_log(self):
        """
        Record task history

        :return:
        """
        self._log("Writing task history log.", level='debug')
        history_logging = history.History()
        task_dump = self.current_task.task_dump()

        history_logging.save_task_history(
            {
                'task_label':          task_dump.get('task_label', ''),
                'abspath':             task_dump.get('abspath', ''),
                'task_success':        task_dump.get('task_success', ''),
                'start_time':          task_dump.get('start_time', ''),
                'finish_time':         task_dump.get('finish_time', ''),
                'processed_by_worker': task_dump.get('processed_by_worker', ''),
                'log':                 task_dump.get('log', ''),
            }
        )

    def dump_history_log(self):
        self._log("Dumping remote task history log.", level='debug')
        task_dump = self.current_task.task_dump()
        destination_data = self.current_task.get_destination_data()

        # Generate checksum
        checksum = 'UNKNOWN'
        if os.path.exists(task_dump.get('abspath')):
            checksum = common.get_file_checksum(task_dump.get('abspath'))

        # Dump history log as metadata in the file's path
        tasks_data_file = os.path.join(os.path.dirname(destination_data.get('abspath')), 'data.json')
        result = common.json_dump_to_file(
            {
                'task_label':          task_dump.get('task_label', ''),
                'abspath':             task_dump.get('abspath', ''),
                'task_success':        task_dump.get('task_success', ''),
                'start_time':          task_dump.get('start_time', ''),
                'finish_time':         task_dump.get('finish_time', ''),
                'processed_by_worker': task_dump.get('processed_by_worker', ''),
                'log':                 task_dump.get('log', ''),
                'checksum':            checksum,
            }
            , tasks_data_file)
        if not result['success']:
            for message in result['errors']:
                self._log("Exception:", message2=str(message), level="exception")
            raise Exception("Exception in dumping completed task data to file")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.history.py
 
    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Jun 2019, (10:42 AM)
 
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
import json
import time
from operator import attrgetter

from unmanic.libs import common, unlogger
from unmanic.libs.unmodels import db, HistoricTasks, \
    HistoricTaskSettings, \
    HistoricTaskProbe, \
    HistoricTaskProbeStreams, \
    HistoricTaskFfmpegLog

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError


class History(object):
    """
    History

    Record statistical data for historical jobs
    """

    def __init__(self, settings=None):
        self.name = 'History'
        self.settings = settings

    def _log(self, message, message2='', level="info"):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        logger = unmanic_logging.get_logger(self.name)
        if logger:
            message = common.format_message(message, message2)
            getattr(logger, level)(message)
        else:
            print("Unmanic.{} - ERROR!!! Failed to find logger".format(self.name))

    def read_history_log(self):
        """
        Note: Depreciated
        TODO: Remove this function

        :return:
        """
        self._log("read_history_log function is depreciated", level="warning")
        self._log("Reading history from file:", level="debug")
        data = []
        if not os.path.exists(self.settings.get_config_path()):
            os.makedirs(self.settings.get_config_path())
        history_file = os.path.join(self.settings.get_config_path(), 'history.json')
        if os.path.exists(history_file):
            try:
                with open(history_file) as infile:
                    data = json.load(infile)
            except JSONDecodeError:
                self._log("ValueError in reading history from file:", level="exception")
            except Exception as e:
                self._log("Exception in reading history from file:", message2=str(e), level="exception")

        return sorted(data, key=lambda i: i['time_complete'])

    def read_completed_job_data(self, job_id):
        """
        Note: Depreciated
        TODO: Remove this function

        :return:
        """
        self._log("read_completed_job_data function is depreciated", level="warning")
        self._log("Reading completed job data from file:", level="debug")
        data = []
        # Create completed job details path in not exists
        completed_job_details_dir = os.path.join(self.settings.get_config_path(), 'completed_job_details')
        if not os.path.exists(completed_job_details_dir):
            os.makedirs(completed_job_details_dir)
        # Set path of conversion details file
        job_details_file = os.path.join(completed_job_details_dir, '{}.json'.format(job_id))
        if os.path.exists(job_details_file):
            try:
                with open(job_details_file) as infile:
                    data = json.load(infile)
            except JSONDecodeError:
                self._log("ValueError in reading completed job data from file:", level="exception")
            except Exception as e:
                self._log("Exception in reading completed job data from file:", message2=str(e), level="exception")
        return data

    def migrate_old_beta_data(self):
        """
        Temporary function to migrate old JSON data to database
        TODO: Remove this function post release. It will not be required.

        :return:
        """
        self._log("migrate_old_beta_data function is temporary. To be removed post release.", level="warning")

        # Get paths to old historical json files. These are needed for the cleanup
        if not os.path.exists(self.settings.get_config_path()):
            os.makedirs(self.settings.get_config_path())
        history_file = os.path.join(self.settings.get_config_path(), 'history.json')
        completed_job_details_dir = os.path.join(self.settings.get_config_path(), 'completed_job_details')

        # Check if we need to execute this migration
        if not os.path.exists(history_file):
            # Migration has already run. no need to continue
            self._log("No job history migration required. No history.json file exists.", level="debug")
            return

        # Read current history log and migrate each entry
        history_log = self.read_history_log()
        for historical_job in history_log:

            # Fetch completed job data (if it exists)
            try:
                completed_job_data = self.read_completed_job_data(historical_job['job_id'])
            except Exception as e:
                self._log("Missing critical data in completed_job_data JSON dump. Ignore this record.", str(e),
                          level="debug")
                continue

            # No completed job data exists for this job
            if not completed_job_data:
                continue

            # Append ffmpeg_log to completed_job_data
            completed_job_data['ffmpeg_log'] = []

            # Set path of job details file (to be deleted post migration)
            job_details_file = os.path.join(completed_job_details_dir, '{}.json'.format(historical_job['job_id']))

            # Create new format dictionary from job data
            task_data = {
                'task_label':          historical_job['description'],
                'task_success':        historical_job['success'],
                'start_time':          completed_job_data['statistics']['start_time'],
                'finish_time':         completed_job_data['statistics']['finish_time'],
                'processed_by_worker': completed_job_data['statistics']['processed_by_worker'],
                'task_dump':           completed_job_data,
            }

            try:
                result = self.save_task_history(task_data)
                if not result:
                    raise Exception('Failed to migrate historical file data to database')

                # Remove json file
                os.remove(job_details_file)

            except Exception as error:
                self._log("Failed to save historic task entry to database.", error, level="error")
                continue

            # Success
            self._log("Migrated historical task to DB:", historical_job['abspath'], level="info")

        # If completed_job_details_dir is empty, delete it
        files = os.listdir(completed_job_details_dir)
        if len(files) == 0:
            os.rmdir(completed_job_details_dir)
            os.remove(history_file)

    def get_historic_task_list(self, limit=None):
        """
        Read all historic tasks entries

        :return:
        """
        try:
            # Fetch a single row (get() will raise DoesNotExist exception if no results are found)
            if limit:
                historic_tasks = HistoricTasks.select().order_by(HistoricTasks.id.desc()).limit(limit)
            else:
                historic_tasks = HistoricTasks.select().order_by(HistoricTasks.id.desc())
        except HistoricTasks.DoesNotExist:
            # No historic entries exist yet
            self._log("No historic tasks exist yet.", level="warning")
            historic_tasks = []

        return historic_tasks.dicts()

    def get_total_historic_task_list_count(self):
        query = HistoricTasks.select().order_by(HistoricTasks.id.desc())
        return query.count()

    def get_historic_task_list_filtered_and_sorted(self, order=None, start=0, length=None, search_value=None, id_list=None,
                                                   task_success=None):
        try:
            query = (HistoricTasks.select())

            if id_list:
                query = query.where(HistoricTasks.id.in_(id_list))

            if search_value:
                query = query.where(HistoricTasks.task_label.contains(search_value))

            if task_success:
                query = query.where(HistoricTasks.task_success.in_([task_success]))

            # Get order by
            if order:
                if order.get("dir") == "asc":
                    order_by = attrgetter(order.get("column"))(HistoricTasks).asc()
                else:
                    order_by = attrgetter(order.get("column"))(HistoricTasks).desc()

            if length:
                query = query.order_by(order_by).limit(length).offset(start)

        except HistoricTasks.DoesNotExist:
            # No historic entries exist yet
            self._log("No historic tasks exist yet.", level="warning")
            query = []

        return query.dicts()

    def get_current_path_of_historic_tasks_by_id(self, id_list=None):
        """
        Returns a list of HistoricTasks filtered by id_list and joined with the current absolute path of that file.
        For failures this will be the the source path
        For success, this will be the destination path

        :param id_list:
        :return:
        """
        """
            SELECT
                t1.*,
                t2.type,
                t2.abspath
            FROM historictasks AS "t1"
            INNER JOIN "historictaskprobe" AS "t2"
                ON (
                    ("t2"."historictask_id" = "t1"."id" AND t1.task_success AND t2.type = "source")
                    OR
                    ("t2"."historictask_id" = "t1"."id" AND NOT t1.task_success AND t2.type = "destination")
                )
            WHERE t1.id IN ( %s)
        """
        query = (
            HistoricTasks.select(HistoricTasks.id, HistoricTasks.task_label, HistoricTasks.task_success,
                                 HistoricTaskProbe.type,
                                 HistoricTaskProbe.abspath))

        if id_list:
            query = query.where(HistoricTasks.id.in_(id_list))

        predicate = (
            (HistoricTaskProbe.historictask_id == HistoricTasks.id) &
            (
                ((HistoricTasks.task_success == True) & (HistoricTaskProbe.type == "destination"))
                |
                ((HistoricTasks.task_success != True) & (HistoricTaskProbe.type == "source"))
            )
        )

        query = query.join(HistoricTaskProbe, on=predicate)

        return query.dicts()

    def get_historic_tasks_list_with_source_probe(self, order=None, start=0, length=None, search_value=None, id_list=None,
                                                  task_success=None, abspath=None):
        """
        Return a list of matching historic tasks with their source file's ffmpeg probe.

        :param order:
        :param start:
        :param length:
        :param search_value:
        :param id_list:
        :param task_success:
        :param abspath:
        :return:
        """
        query = (
            HistoricTasks.select(HistoricTasks.id, HistoricTasks.task_label, HistoricTasks.task_success,
                                 HistoricTaskProbe.type,
                                 HistoricTaskProbe.abspath))

        if id_list:
            query = query.where(HistoricTasks.id.in_(id_list))

        if search_value:
            query = query.where(HistoricTasks.task_label.contains(search_value))

        if task_success is not None:
            query = query.where(HistoricTasks.task_success.in_([task_success]))

        if abspath:
            query = query.where(HistoricTaskProbe.abspath.in_([abspath]))

        predicate = (
            (HistoricTaskProbe.historictask_id == HistoricTasks.id) &
            (HistoricTaskProbe.type == "source")
        )

        query = query.join(HistoricTaskProbe, on=predicate)

        return query.dicts()

    def get_historic_task_data_dictionary(self, task_id):
        """
        Read all data for a task and return a dictionary of that data

        :return:
        """
        # Get historic task matching the id
        try:
            # Fetch the historic task (get() will raise DoesNotExist exception if no results are found)
            historic_tasks = HistoricTasks.get_by_id(task_id)
        except HistoricTasks.DoesNotExist:
            self._log("Failed to retrieve historic task from database for id {}.".format(task_id), level="exception")
            return False
        # Get all saved data for this task and create dictionary of task data
        historic_task = historic_tasks.model_to_dict()
        # Return task data dictionary
        return historic_task

    def delete_historic_tasks_recursively(self, id_list=None):
        """
        Deletes a given list of historic tasks based on their IDs

        :param id_list:
        :return:
        """
        # Prevent running if no list of IDs was given
        if not id_list:
            return False

        try:
            query = (HistoricTasks.select())

            if id_list:
                query = query.where(HistoricTasks.id.in_(id_list))

            for historic_task_id in query:
                try:
                    historic_task_id.delete_instance(recursive=True)
                except Exception as e:
                    # Catch delete exceptions
                    self._log("An error occurred while deleting historic task ID: {}.".format(historic_task_id), str(e),
                              level="exception")
                    return False

            return True

        except HistoricTasks.DoesNotExist:
            # No historic entries exist yet
            self._log("No historic tasks exist yet.", level="warning")

    def save_task_history(self, task_data):
        """
        Record a task's data and state to the database.

        :param task_data:
        :return:
        """
        try:
            # Create the new historical task entry
            new_historic_task = self.create_historic_task_entry(task_data)

            # TODO: Create a snapshot of the current configuration of the application into HistoricTaskSettings

            # Ensure a dump of the task was passed through with the task data param
            # This dump is a snapshot of all information pertaining to the task
            task_dump = task_data.get('task_dump', {})
            if not task_dump:
                self._log('Passed param dict', json.dumps(task_data), level="debug")
                raise Exception('Function param missing task data dump')

            # Create an entry of the data from the source ffprobe
            self.create_historic_task_probe_entry('source', new_historic_task, task_dump)

            # Create an entry of the data from the destination ffprobe
            self.create_historic_task_probe_entry('destination', new_historic_task, task_dump)

            # Create an entry of the data from the source ffprobe
            self.create_historic_task_ffmpeg_log_entry(new_historic_task, task_dump)

            return True

        except Exception as error:
            self._log("Failed to save historic task entry to database.", error, level="exception")
            return False

    def create_historic_task_ffmpeg_log_entry(self, historic_task, task_dump):
        """
        Create an entry of the stdout log from the ffmpeg command

        Required task_dump params:
            - ffmpeg_log

        :param historic_task:
        :param task_dump:
        :return:
        """
        if 'ffmpeg_log' not in task_dump:
            self._log('Task dump dict missing ffmpeg_log', json.dumps(task_dump), level="debug")
            raise Exception('Function param missing ffmpeg_log')

        ffmpeg_log = task_dump.get('ffmpeg_log')

        HistoricTaskFfmpegLog.create(
            historictask_id=historic_task,
            dump=ffmpeg_log
        )

    def create_historic_task_entry(self, task_data):
        """
        Create a historic task entry

        Required task_data params:
            - task_label
            - task_success
            - start_time
            - finish_time
            - processed_by_worker

        :param task_data:
        :return:
        """
        if not task_data:
            self._log('Task data param empty', json.dumps(task_data), level="debug")
            raise Exception('Task data param empty. This should not happen - Something has gone really wrong.')

        new_historic_task = HistoricTasks.create(task_label=task_data['task_label'],
                                                 task_success=task_data['task_success'],
                                                 start_time=task_data['start_time'],
                                                 finish_time=task_data['finish_time'],
                                                 processed_by_worker=task_data['processed_by_worker'])
        return new_historic_task

    def create_historic_task_probe_entry(self, probe_type, historic_task, task_dump):
        """
        Create an entry of the data from the source or destination ffprobe
        Create an entry for each stream in the file probe with create_historic_task_probe_streams_entries()

        Required task_dump params:
            - type
            - abspath
            - basename
            - bit_rate
            - format_long_name
            - format_name
            - size

        :param probe_type:
        :param historic_task:
        :param task_dump:
        :return:
        """
        probe_data = task_dump.get('file_probe_data', None)

        if not probe_data:
            self._log('Task dump dict missing ffprobe data', json.dumps(task_dump), level="debug")
            raise Exception('Function param missing {} data'.format(probe_type))

        file_probe = probe_data.get(probe_type, None)

        if not file_probe:
            if historic_task.task_success:
                raise Exception('Exception: Successful task data missing {} probe data. Something is wrong'.format(probe_type))
            message = 'Task dump probe data for {} file does not exist possibly due to task failure'.format(probe_type)
            self._log(message, level="debug")
            return

        abspath = file_probe.get('abspath', None)
        basename = file_probe.get('basename', None)

        historic_task_probe = HistoricTaskProbe.create(
            historictask_id=historic_task,
            type=probe_type,
            abspath=abspath,
            basename=basename,
            bit_rate=file_probe.get('bit_rate', ''),
            format_long_name=file_probe.get('format_long_name', ''),
            format_name=file_probe.get('format_name', ''),
            size=file_probe.get('size', '')
        )

        self.create_historic_task_probe_streams_entries(probe_type, historic_task_probe, file_probe)

    def create_historic_task_probe_streams_entries(self, probe_type, historic_task_probe, file_probe):
        """
        Create an entry for each stream in the file's ffprobe

        Required file_probe params:
            - codec_type

        Other file_probe params:
            - codec_long_name
            - avg_frame_rate
            - bit_rate
            - coded_height
            - coded_width
            - height
            - width
            - duration
            - channels
            - channel_layout

        :param probe_type:
        :param historic_task_probe:
        :param file_probe:
        :return:
        """
        # Loop over streams and add them
        for stream in file_probe.get('streams', []):

            if not stream.get('codec_type', None):
                self._log('Stream data for {} missing codec_type'.format(probe_type), json.dumps(stream), level="debug")
                raise Exception('Stream data for {} missing required "codec_type" data'.format(probe_type))

            HistoricTaskProbeStreams.create(
                historictaskprobe_id=historic_task_probe,
                codec_type=stream.get('codec_type', None),
                codec_long_name=stream.get('codec_long_name', ''),
                avg_frame_rate=stream.get('avg_frame_rate', ''),
                bit_rate=stream.get('bit_rate', ''),
                coded_height=stream.get('coded_height', ''),
                coded_width=stream.get('coded_width', ''),
                height=stream.get('height', ''),
                width=stream.get('width', ''),
                duration=stream.get('duration', ''),
                channels=stream.get('channels', ''),
                channel_layout=stream.get('channel_layout', '')
            )

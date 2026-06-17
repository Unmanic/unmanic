#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.taskqueue.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     23 Apr 2019, (19:17 PM)

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

           THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""

import time

from unmanic.libs import task
from unmanic.libs import common
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.unmodels import Libraries, LibraryTags, Tags
from unmanic.libs.unmodels.tasks import Tasks

"""

An object to contain all details of the job queue in such a way that it is presented in a synchronous list
while being able to be accessed by a number of threads simultaneously

"""


def build_tasks_count_query(status):
    """
    Return a 0 if no tasks exist for the given status.
    Return a count >= 1 if any tasks exist for the given status.

    # TODO: look into peewee dynamic query building (surly this exists)

    :param status:
    :return:
    """
    # Fetch only on result in order to know that there are any at all
    # Filter by status
    query = Tasks.select().where((Tasks.status == status)).limit(1)
    return query.count()


def build_tasks_query(status, sort_by='id', sort_order='asc', local_only=False, library_names=None, library_tags=None):
    """
    Return the first task item in the task list filtered by status
    and sorted by the self.sort_by and self.sort_order variables.

    :param status:
    :param sort_order:
    :param sort_by:
    :param local_only:
    :param library_names:
    :param library_tags:
    :return:
    """
    from peewee import OperationalError
    logger = UnmanicLogging.get_logger(name='TaskQueue')

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # pick query based on sort params
            query = Tasks.select().where((Tasks.status == status))

            # Limit to one result
            if local_only:
                query = query.where((Tasks.type == 'local'))

            query = query.join(Libraries, on=(Libraries.id == Tasks.library_id))
            if library_names is not None:
                query = query.where(Libraries.name.in_(library_names))
            if library_tags is not None:
                query = query.join(LibraryTags, join_type='LEFT OUTER JOIN')
                query = query.join(Tags, join_type='LEFT OUTER JOIN')
                if library_tags:
                    query = query.where(Tags.name.in_(library_tags))
                else:
                    # Handle a query where the list is empty. In this case we want to match for only libraries that have no tags
                    query = query.where(Tags.name.is_null())

            # Limit to one result
            query = query.limit(1)
            if sort_order == 'asc':
                query = query.order_by(sort_by.asc())
            else:
                query = query.order_by(sort_by.desc())
            return query.first()
        except OperationalError as e:
            if 'database is locked' in str(e).lower():
                if attempt < max_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)
                    logger.warning(f"Database locked while querying tasks, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Database locked after {max_retries} attempts querying tasks, giving up")
            raise


def build_tasks_query_full_task_list(status, sort_by='id', sort_order='asc', limit=None):
    """
    Return all task items in the task list filtered by status.
    The query is sorted by the self.sort_by and self.sort_order variables
    and may be limited by the limit variable.

    :param sort_order:
    :param sort_by:
    :param status:
    :param limit:
    :return:
    """
    query = Tasks.select(Tasks).where((Tasks.status == status))

    # Set the sort order
    if sort_order == 'asc':
        query = query.order_by(sort_by.asc())
    else:
        query = query.order_by(sort_by.desc())

    # Set query limit if one was given
    if limit:
        query = query.limit(limit)

    # Return results as dictionary
    return query.dicts()


def fetch_next_task_filtered(status, sort_by='id', sort_order='asc', local_only=False, library_names=None, library_tags=None):
    """
    Returns the next task in the task list for a given status.

    Uses atomic UPDATE...WHERE to prevent race conditions in multi-machine setups.
    If another machine claims the task first, returns False and caller retries.

    :param status:
    :param sort_order:
    :param sort_by:
    :param local_only:
    :param library_names:
    :param library_tags:
    :return: Task object if successfully claimed, False if no tasks or race lost
    """
    logger = UnmanicLogging.get_logger(name='TaskQueue')
    logger.debug(f"Fetching next task with status='{status}', local_only={local_only}, library_names={library_names}, library_tags={library_tags}")

    # Step 1: Find the first task matching all filters
    task_item = build_tasks_query(status, sort_by=sort_by, sort_order=sort_order, local_only=local_only,
                                  library_names=library_names, library_tags=library_tags)
    if not task_item:
        logger.debug(f"No tasks found with status='{status}'")
        return False

    task_id = task_item.id
    logger.debug(f"Found candidate task {task_id}: {task_item.abspath} (status={task_item.status})")

    # Step 2: Atomically claim this task by updating status from 'pending' to 'in_progress'
    # This UPDATE will only succeed if status is still 'pending' (another machine hasn't claimed it)
    try:
        updated_count = Tasks.update({
            Tasks.status: 'in_progress'
        }).where(
            (Tasks.id == task_id) &
            (Tasks.status == status)  # Only update if status hasn't changed
        ).execute()

        if updated_count == 0:
            logger.info(f"Lost race for task {task_id}: Another machine claimed it first")
            return False

        logger.info(f"Successfully claimed task {task_id}: {task_item.abspath} (status={task_item.status}, type={task_item.type})")

        # Step 3: Load the full Task object and return
        next_task = task.Task()
        next_task.read_and_set_task_by_absolute_path(task_item.abspath)
        return next_task

    except Exception as e:
        logger.exception(f"Exception while claiming task {task_id}: {str(e)}")
        return False


class TaskQueue(object):
    """
    TaskQueue

    Creates an job item per file.
    This job item is passed through stages by the Foreman and PostProcessor

    Attributes:
        data_queues (list): A list of Queue objects. Contains the logger

    """

    def __init__(self, data_queues):
        self.name = 'TaskQueue'
        self.data_queues = data_queues
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)

        # Sort fields
        self.sort_by = Tasks.priority
        self.sort_order = 'desc'

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    """
    Last task based on status pending, in_progress or processed
    """

    def list_pending_tasks(self, limit=None):
        """
        Returns a list of 'pending' tasks
        Can limit to <limit> results

        :param limit:
        :return:
        """
        results = build_tasks_query_full_task_list('pending', self.sort_by, self.sort_order, limit)
        if results:
            return list(results)
        return []

    def list_in_progress_tasks(self, limit=None):
        """
        Returns a list of 'in_progress' tasks
        Can limit to <limit> results

        :param limit:
        :return:
        """
        results = build_tasks_query_full_task_list('in_progress', self.sort_by, self.sort_order, limit)
        if results:
            return list(results)
        return []

    def list_processed_tasks(self, limit=None):
        """
        Returns a list of 'processed' tasks
        Can limit to <limit> results

        :param limit:
        :return:
        """
        results = build_tasks_query_full_task_list('processed', self.sort_by, self.sort_order, limit)
        if results:
            return list(results)
        return []

    """
    Get first task in task list based on status pending, in_progress or processed
    """

    def get_next_pending_tasks(self, local_only=False, library_names=None, library_tags=None):
        """
        Fetch the next pending task and atomically mark it as 'in_progress'.

        Uses atomic UPDATE...WHERE to prevent race conditions where multiple Unmanic instances
        (local and remote) could pick up the same task simultaneously.

        Retries on database lock errors (transient concurrency issues).

        :param local_only:
        :param library_names:
        :param library_tags:
        :return: Task object if successfully claimed, False if no pending tasks
        """
        import time
        from peewee import OperationalError

        self._log("Attempting to fetch next pending task", f"local_only={local_only}, library_names={library_names}, library_tags={library_tags}")

        # Retry logic for transient database lock errors
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Fetch Task item and atomically claim it as 'in_progress'
                # Note: fetch_next_task_filtered now does atomic UPDATE...WHERE internally
                task_item = fetch_next_task_filtered('pending', sort_by=self.sort_by, sort_order=self.sort_order,
                                                     local_only=local_only, library_names=library_names, library_tags=library_tags)
                if task_item:
                    self._log(f"Task {task_item.get_task_id()} successfully claimed and marked in_progress", task_item.get_source_abspath(), level='info')
                else:
                    self._log("No pending tasks found to process (or lost race to another machine)", level='debug')

                return task_item
            except OperationalError as e:
                if 'database is locked' in str(e).lower():
                    if attempt < max_retries - 1:
                        wait_time = 0.1 * (2 ** attempt)  # Exponential backoff: 0.1s, 0.2s, 0.4s
                        self._log(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})", level='warning')
                        time.sleep(wait_time)
                        continue
                    else:
                        self._log(f"Database locked after {max_retries} attempts, giving up", level='error')
                # Re-raise if not a lock error or we've exhausted retries
                raise

    def get_next_processed_tasks(self):
        # Fetch Task item matching the filters specified
        task_item = fetch_next_task_filtered('processed', sort_by=self.sort_by, sort_order=self.sort_order)
        return task_item

    def requeue_tasks_at_bottom(self, task_id):
        task_handler = task.Task()
        return task_handler.reorder_tasks([task_id], 'bottom')

    """
    Check if a particular task list is empty
    """

    @staticmethod
    def task_list_pending_is_empty():
        # Fetch only on result in order to know that there are any at all
        pending_query_count = build_tasks_count_query('pending')
        if pending_query_count > 0:
            return False
        return True

    @staticmethod
    def task_list_in_progress_is_empty():
        # Fetch only on result in order to know that there are any at all
        pending_query_count = build_tasks_count_query('in_progress')
        if pending_query_count > 0:
            return False
        return True

    @staticmethod
    def task_list_processed_is_empty():
        # Fetch only on result in order to know that there are any at all
        pending_query_count = build_tasks_count_query('processed')
        if pending_query_count > 0:
            return False
        return True

    """
    Set the status of a task item
    """

    @staticmethod
    def mark_item_in_progress(task_item):
        """
        DEPRECATED: This method is no longer used.

        Task status is now marked as 'in_progress' atomically in fetch_next_task_filtered()
        to prevent race conditions in multi-machine setups where both local and remote
        Unmanic instances could pick up the same task simultaneously.

        Keeping this method for backward compatibility only.

        :param task_item:
        :return:
        """
        task_item.set_status('in_progress')
        return task_item

    @staticmethod
    def mark_item_as_processed(task_item):
        """
        Set the given task status as 'processed' and then return it.

        :param task_item:
        :return:
        """
        # Set item as status = 'processed'
        task_item.set_status('processed')
        return task_item

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.scheduler.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     11 Sep 2021, (11:15 AM)

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
import random
import threading
import time
from datetime import datetime, timedelta

import schedule

from unmanic import config
from unmanic.libs import common, task, unlogger
from unmanic.libs.installation_link import Links
from unmanic.libs.plugins import PluginsHandler
from unmanic.libs.session import Session


class ScheduledTasksManager(threading.Thread):
    """
    Manage any tasks that Unmanic needs to execute at regular intervals
    """

    def __init__(self, event):
        super(ScheduledTasksManager, self).__init__(name='ScheduledTasksManager')
        self.logger = None
        self.event = event
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        self.scheduler = schedule.Scheduler()
        self.force_local_worker_timer = 0

    def _log(self, message, message2='', level="info"):
        if not self.logger:
            unmanic_logging = unlogger.UnmanicLogger.__call__()
            self.logger = unmanic_logging.get_logger(self.name)
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        self._log("Starting ScheduledTasks Monitor loop")

        # Create scheduled tasks
        # Check the session every 60 minutes
        self.scheduler.every(60).minutes.do(self.register_unmanic)
        # Run the plugin repo update every 3 hours
        self.scheduler.every(3).hours.do(self.plugin_repo_update)
        # Run the remote installation link update every 10 seconds
        self.scheduler.every(10).seconds.do(self.update_remote_installation_links)
        # Run the remote installation distributed worker counter sync every minute
        self.scheduler.every(1).minutes.do(self.set_worker_count_based_on_remote_installation_links)
        # Run a completed task cleanup every 60 minutes and on startup
        self.scheduler.every(12).hours.do(self.manage_completed_tasks)
        self.manage_completed_tasks()

        # Loop every 2 seconds to check if a task is due to be run
        while not self.abort_flag.is_set():
            self.event.wait(2)
            # Check if scheduled task is due
            self.scheduler.run_pending()

        # Clear any tasks and exit
        self.scheduler.clear()
        self._log("Leaving ScheduledTasks Monitor loop...")

    def register_unmanic(self):
        self._log("Updating session data")
        s = Session()
        s.register_unmanic(force=True)

    def plugin_repo_update(self):
        self._log("Checking for updates to plugin repos")
        plugin_handler = PluginsHandler()
        plugin_handler.update_plugin_repos()

    def update_remote_installation_links(self):
        # Don't log this as it will happen often
        links = Links()
        links.update_all_remote_installation_links()

    def set_worker_count_based_on_remote_installation_links(self):
        settings = config.Config()

        # Get local task count as int
        task_handler = task.Task()
        local_task_count = int(task_handler.get_total_task_list_count())

        # Get target count
        target_count = int(settings.get_distributed_worker_count_target())
        # # TODO: Check if we should be aiming for one less than the target
        # if target_count > 1:
        #     target_count -= 1

        linked_configs = []
        for local_config in settings.get_remote_installations():
            if local_config.get('enable_distributed_worker_count'):
                linked_configs.append(local_config)

        # If no remote links are configured, then return here
        if not linked_configs:
            return

        # There is a link config with distributed worker counts enabled
        self._log("Syncing distributed worker count for this installation")

        # Get total tasks count of pending tasks across all linked_configs
        total_tasks = local_task_count
        for linked_config in linked_configs:
            total_tasks += int(linked_config.get('task_count', 0))

        # From the counts fetched from all linked_configs, balance out the target count (including this installation)
        allocated_worker_count = 0
        for linked_config in linked_configs:
            if linked_config.get('task_count', 0) == 0:
                continue
            allocated_worker_count += round((int(linked_config.get('task_count', 0)) / total_tasks) * target_count)

        # Calculate worker count for local
        target_workers_for_this_installation = 0
        if local_task_count > 0:
            target_workers_for_this_installation = round((local_task_count / total_tasks) * target_count)

        # If the total allocated worker count is now above our target, set this installation back to 0
        if allocated_worker_count > target_count:
            target_workers_for_this_installation = 0

        # Every 10-12 minutes (make it random), give this installation at least 1 worker if it has pending tasks.
        #       This should cause the pending task queue to sit idle if there is only one task in the queue and it will provide
        #           rotation of workers when the pending task queue is close to the same.
        #       EG. If time now (seconds) > time last checked (seconds) + 10mins (600 seconds) + random seconds within 2mins
        time_now = time.time()
        time_to_next_force_local_worker = int(self.force_local_worker_timer + 600 + random.randrange(120))
        if time_now > time_to_next_force_local_worker:
            if (local_task_count > 1) and (target_workers_for_this_installation < 1):
                target_workers_for_this_installation = 1
                self.force_local_worker_timer = time_now

        self._log("Configuring worker count as {} for this installation".format(target_workers_for_this_installation))
        settings.set_config_item('number_of_workers', target_workers_for_this_installation, save_settings=True)

    def manage_completed_tasks(self):
        settings = config.Config()
        # Only run if configured to auto manage completed tasks
        if not settings.get_auto_manage_completed_tasks():
            return

        self._log("Running completed task cleanup for this installation")
        max_age_in_days = settings.get_max_age_of_completed_tasks()
        date_x_days_ago = datetime.now() - timedelta(days=int(max_age_in_days))
        before_time = date_x_days_ago.timestamp()

        task_success = True
        inc_status = 'successfully'
        if not settings.get_always_keep_failed_tasks():
            inc_status = 'successfully or failed'
            task_success = None

        # Fetch completed tasks
        from unmanic.libs import history
        history_logging = history.History()
        count = history_logging.get_historic_task_list_filtered_and_sorted(task_success=task_success,
                                                                           before_time=before_time).count()
        results = history_logging.get_historic_task_list_filtered_and_sorted(task_success=task_success,
                                                                             before_time=before_time)

        if count == 0:
            self._log("Found no {} completed tasks older than {} days".format(inc_status, max_age_in_days))
            return

        self._log(
            "Found {} {} completed tasks older than {} days that should be removed".format(count, inc_status, max_age_in_days))
        if not history_logging.delete_historic_tasks_recursively(results):
            self._log("Failed to delete {} {} completed tasks".format(count, inc_status), level='error')
            return

        self._log("Deleted {} {} completed tasks".format(count, inc_status))

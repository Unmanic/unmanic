#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.service.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Dec 2018, (7:21 AM)

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
import argparse
import os
import json
import time
import threading
import queue
import schedule
import signal

from unmanic import config, metadata
from unmanic.libs import unlogger, common, eventmonitor, ffmpeg, history, unmodels
from unmanic.libs.filetest import FileTest
from unmanic.libs.taskqueue import TaskQueue
from unmanic.libs.postprocessor import PostProcessor
from unmanic.libs.taskhandler import TaskHandler
from unmanic.libs.uiserver import UIServer
from unmanic.libs.foreman import Foreman
from unmanic.libs.unplugins.pluginscli import PluginsCLI

unmanic_logging = unlogger.UnmanicLogger.__call__()
main_logger = unmanic_logging.get_logger()


class LibraryScanner(threading.Thread):
    def __init__(self, data_queues, settings):
        super(LibraryScanner, self).__init__(name='LibraryScanner')
        self.interval = 0
        self.firstrun = True
        self.settings = settings
        self.logger = data_queues["logging"].get_logger(self.name)
        self.scheduledtasks = data_queues["scheduledtasks"]
        self.library_scanner_triggers = data_queues["library_scanner_triggers"]
        self.abort_flag = threading.Event()
        self.abort_flag.clear()
        self.ffmpeg = None

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def init_ffmpeg_handle_settings(self):
        return {
            'audio_codec':                          self.settings.get_config_item('audio_codec'),
            'audio_stream_encoder':                 self.settings.get_audio_stream_encoder(),
            'audio_codec_cloning':                  self.settings.get_audio_codec_cloning(),
            'audio_stereo_stream_bitrate':          self.settings.get_audio_stereo_stream_bitrate(),
            'cache_path':                           self.settings.get_cache_path(),
            'debugging':                            self.settings.get_debugging(),
            'enable_audio_encoding':                self.settings.get_enable_audio_encoding(),
            'enable_audio_stream_stereo_cloning':   self.settings.get_enable_audio_stream_stereo_cloning(),
            'enable_audio_stream_transcoding':      self.settings.get_enable_audio_stream_transcoding(),
            'enable_video_encoding':                self.settings.get_enable_video_encoding(),
            'out_container':                        self.settings.get_out_container(),
            'remove_subtitle_streams':              self.settings.get_remove_subtitle_streams(),
            'video_codec':                          self.settings.get_video_codec(),
            'video_stream_encoder':                 self.settings.get_video_stream_encoder(),
            'overwrite_additional_ffmpeg_options':  self.settings.get_overwrite_additional_ffmpeg_options(),
            'additional_ffmpeg_options':            self.settings.get_additional_ffmpeg_options(),
            'enable_hardware_accelerated_decoding': self.settings.get_enable_hardware_accelerated_decoding(),
        }

    def stop(self):
        self.abort_flag.set()

    def abort_is_set(self):
        # Check if the abort flag is set
        if self.abort_flag.is_set():
            # Return True straight away if it is
            return True

        # Sleep for a fraction of a second to prevent CPU pinning
        time.sleep(.1)

        # Return False
        return False

    def run(self):
        # If we have a config set to run a schedule, then start the process.
        # Otherwise close this thread now.
        self._log("Starting LibraryScanner Monitor loop")
        while not self.abort_is_set():
            # Main loop to configure the scheduler
            if int(self.settings.get_schedule_full_scan_minutes()) != self.interval:
                self.interval = int(self.settings.get_schedule_full_scan_minutes())
            if self.interval and self.interval != 0:
                self._log("Setting LibraryScanner schedule to scan every {} mins...".format(self.interval))
                # Configure schedule
                schedule.every(self.interval).minutes.do(self.scheduled_job)
                # Register application
                self.register_unmanic()

                # First run the task
                if self.settings.get_run_full_scan_on_start() and self.firstrun:
                    self._log("Running LibraryScanner on start")
                    self.scheduled_job()
                self.firstrun = False

                # Then loop and wait for the schedule
                while not self.abort_is_set():

                    # Check if a manual library scan was triggered
                    try:
                        if not self.library_scanner_triggers.empty():
                            trigger = self.library_scanner_triggers.get_nowait()
                            if trigger == "library_scan":
                                self.scheduled_job()
                                break
                    except queue.Empty:
                        continue
                    except Exception as e:
                        self._log("Exception in retrieving library scanner trigger {}:".format(self.name), message2=str(e),
                                  level="exception")

                    # Check if scheduled task is due
                    schedule.run_pending()
                    # Delay for 1 second before checking again.
                    time.sleep(1)
                    # If the settings have changed, then break this loop and clear
                    # the scheduled job resetting to the new interval
                    if int(self.settings.get_schedule_full_scan_minutes()) != self.interval:
                        self._log("Resetting LibraryScanner schedule")
                        break
                schedule.clear()

        self._log("Leaving LibraryScanner Monitor loop...")

    def scheduled_job(self):
        self._log("Running full library scan")
        self.scan_library_path(self.settings.get_library_path())

    def add_path_to_queue(self, pathname):
        self.scheduledtasks.put(pathname)

    def scan_library_path(self, search_folder):
        if not os.path.exists(search_folder):
            self._log("Path does not exist - '{}'".format(search_folder), level="warning")
            return
        if self.settings.get_debugging():
            self._log("Scanning directory - '{}'".format(search_folder), level="debug")
        for root, subFolders, files in os.walk(search_folder, followlinks=True):
            if self.abort_flag.is_set():
                break
            if self.settings.get_debugging():
                self._log(json.dumps(files, indent=2), level="debug")
            # Add all files in this path that match our container filter
            for file_path in files:
                if self.abort_flag.is_set():
                    break

                # Get full path to file
                pathname = os.path.join(root, file_path)

                # Test file to be added to task list. Add it if required
                file_test = FileTest(self.settings, pathname)
                result, issues = file_test.should_file_be_added_to_task_list()
                # Log any error messages
                for issue in issues:
                    if type(issue) is dict:
                        self._log(issue.get('message'))
                    else:
                        self._log(issue)
                # If file needs to be added, then add it
                if result:
                    self.add_path_to_queue(pathname)

    def register_unmanic(self):
        from unmanic.libs import session
        s = session.Session()
        s.register_unmanic(s.get_installation_uuid())


def init_db():
    # Set paths
    config_path = common.get_config_dir()
    app_dir = os.path.dirname(os.path.abspath(__file__))

    # Set database connection settings
    database_settings = {
        "TYPE":           "SQLITE",
        "FILE":           os.path.join(config_path, 'unmanic.db'),
        "MIGRATIONS_DIR": os.path.join(app_dir, 'migrations'),
    }

    # Ensure the config path exists
    if not os.path.exists(config_path):
        os.makedirs(config_path)

    # Create database connection
    db_connection = unmodels.Database.select_database(database_settings)

    # Run database migrations
    migrations = unmodels.Migrations(database_settings)
    migrations.run_all()

    # Return the database connection
    return db_connection


class Service:

    def __init__(self):
        self.threads = []
        self.run_threads = True
        self.db_connection = None

        self.developer = None

    def start_handler(self, data_queues, settings, task_queue):
        main_logger.info("Starting TaskHandler")
        handler = TaskHandler(data_queues, settings, task_queue)
        handler.daemon = True
        handler.start()
        self.threads.append({
            'name':   'TaskHandler',
            'thread': handler
        })
        return handler

    def start_post_processor(self, data_queues, settings, task_queue):
        main_logger.info("Starting PostProcessor")
        postprocessor = PostProcessor(data_queues, settings, task_queue)
        postprocessor.daemon = True
        postprocessor.start()
        self.threads.append({
            'name':   'PostProcessor',
            'thread': postprocessor
        })
        return postprocessor

    def start_foreman(self, data_queues, settings, task_queue):
        main_logger.info("Starting Foreman")
        foreman = Foreman(data_queues, settings, task_queue)
        foreman.daemon = True
        foreman.start()
        self.threads.append({
            'name':   'Foreman',
            'thread': foreman
        })
        return foreman

    def start_library_scanner_manager(self, data_queues, settings):
        main_logger.info("Starting LibraryScanner")
        scheduler = LibraryScanner(data_queues, settings)
        scheduler.daemon = True
        scheduler.start()
        self.threads.append({
            'name':   'LibraryScanner',
            'thread': scheduler
        })
        return scheduler

    def start_inotify_watch_manager(self, data_queues, settings):
        if eventmonitor.event_monitor_module:
            main_logger.info("Starting EventMonitorManager")
            event_monitor_manager = eventmonitor.EventMonitorManager(data_queues, settings)
            event_monitor_manager.daemon = True
            event_monitor_manager.start()
            self.threads.append({
                'name':   'EventMonitorManager',
                'thread': event_monitor_manager
            })
            return event_monitor_manager
        else:
            main_logger.warn("Unable to start EventMonitorManager as no event monitor module was found")

    def start_ui_server(self, data_queues, foreman):
        main_logger.info("Starting UIServer")
        uiserver = UIServer(data_queues, foreman, self.developer)
        uiserver.daemon = True
        uiserver.start()
        self.threads.append({
            'name':   'UIServer',
            'thread': uiserver
        })
        return uiserver

    def initial_register_unmanic(self, settings):
        from unmanic.libs import session
        s = session.Session()
        s.register_unmanic(s.get_installation_uuid())

    def sig_handle(self, a, b):
        main_logger.info("SIGTERM Received")
        self.run_threads = False

    def start_threads(self, settings):
        # Create our data queues
        data_queues = {
            "library_scanner_triggers": queue.Queue(maxsize=1),
            "scheduledtasks":           queue.Queue(),
            "inotifytasks":             queue.Queue(),
            "progress_reports":         queue.Queue(),
            "logging":                  unmanic_logging
        }

        # Clear cache directory
        main_logger.info("Clearing previous cache")
        common.clean_files_in_dir(settings.get_cache_path())

        main_logger.info("Starting all threads")

        # Register installation
        self.initial_register_unmanic(settings)

        # Setup job queue
        task_queue = TaskQueue(settings, data_queues)

        # Setup post-processor thread
        self.start_post_processor(data_queues, settings, task_queue)

        # Start the foreman thread
        foreman = self.start_foreman(data_queues, settings, task_queue)

        # Start new thread to handle messages from service
        self.start_handler(data_queues, settings, task_queue)

        # Start scheduled thread
        self.start_library_scanner_manager(data_queues, settings)

        # Start inotify watch manager
        self.start_inotify_watch_manager(data_queues, settings)

        # Start new thread to run the web UI
        self.start_ui_server(data_queues, foreman)

    def stop_threads(self):
        main_logger.info("Stopping all threads")
        for thread in self.threads:
            main_logger.info("Sending thread {} abort signal".format(thread['name']))
            thread['thread'].stop()
        for thread in self.threads:
            main_logger.info("Waiting for thread {} to stop".format(thread['name']))
            thread['thread'].join(10)
            main_logger.info("Thread {} has successfully stopped".format(thread['name']))
        self.threads = []

    def init_config(self):
        # Init DB
        if not self.db_connection:
            self.db_connection = init_db()

        # Read settings
        return config.CONFIG(db_connection=self.db_connection)

    def run(self):
        # Init the configuration
        settings = self.init_config()

        # Start all threads
        self.start_threads(settings)

        # Watch for the term signal
        signal.signal(signal.SIGINT, self.sig_handle)
        signal.signal(signal.SIGTERM, self.sig_handle)
        while self.run_threads:
            signal.pause()

        # Received term signal. Stop everything
        self.stop_threads()
        self.db_connection.stop()
        while not self.db_connection.is_stopped():
            time.sleep(0.1)
            continue
        main_logger.info("Exit Unmanic")


def main():
    parser = argparse.ArgumentParser(description='Unmanic')
    parser.add_argument('--version', action='version',
                        version='%(prog)s {version}'.format(version=metadata.read_version_string('long')))
    parser.add_argument('--manage_plugins', action='store_true',
                        help='manage installed plugins')
    parser.add_argument('--dev',
                        action='store_true',
                        help='Enable developer mode')
    args = parser.parse_args()

    if args.manage_plugins:
        # Init the DB connection
        db_connection = init_db()

        # Run the plugin manager CLI
        plugin_cli = PluginsCLI()
        plugin_cli.run()

        # Stop the DB connection
        db_connection.stop()
        while not db_connection.is_stopped():
            time.sleep(0.1)
            continue
    else:
        # Run the main Unmanic service
        service = Service()
        service.developer = args.dev
        service.run()


if __name__ == "__main__":
    main()

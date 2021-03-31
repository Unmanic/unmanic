#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.eventmonitor.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     25 Feb 2021, (10:06 AM)

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
import threading
import time
import pyinotify

from unmanic.libs import common, ffmpeg, history
from unmanic.libs.filetest import FileTest


class EventProcessor(pyinotify.ProcessEvent):
    def __init__(self, data_queues, settings):
        self.name = "EventProcessor"
        self.settings = settings
        self.logger = data_queues["logging"].get_logger(self.name)
        self.inotifytasks = data_queues["inotifytasks"]
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

    def inotify_enabled(self):
        if self.settings.get_enable_inotify():
            return True
        return False

    def add_path_to_queue(self, pathname):
        self.inotifytasks.put(pathname)

    def handle_event(self, event):
        # Get full path to file
        pathname = event.pathname

        # Test file to be added to task list. Add it if required
        file_test = FileTest(self.settings, pathname)
        result, issues = file_test.should_file_be_added_to_task_list()
        # Log any error messages
        for issue in issues:
            self._log(issue.get('message'))
        # If file needs to be added, then add it
        if result:
            self.add_path_to_queue(pathname)

    def process_IN_CLOSE_WRITE(self, event):
        if self.inotify_enabled():
            self._log("CLOSE_WRITE event detected:", event.pathname)
            self.handle_event(event)

    def process_IN_MOVED_TO(self, event):
        if self.inotify_enabled():
            self._log("MOVED_TO event detected:", event.pathname)
            self.handle_event(event)

    def process_IN_DELETE(self, event):
        if self.inotify_enabled():
            self._log("DELETE event detected:", event.pathname)
            self._log("Nothing to do for this event")

    def process_default(self, event):
        pass


class EventMonitorManager(threading.Thread):
    """
    EventMonitorManager

    Manage the EventProcessor thread.
    If the settings for enabling the EventProcessor changes, this manager
    class will stop or start the EventProcessor thread accordingly.

    """

    def __init__(self, data_queues, settings):
        super(EventMonitorManager, self).__init__(name='EventMonitorManager')
        self.name = "EventMonitorManager"
        self.settings = settings
        self.data_queues = data_queues

        self.logger = data_queues["logging"].get_logger(self.name)
        self.inotifytasks = data_queues["inotifytasks"]

        self.abort_flag = threading.Event()
        self.abort_flag.clear()

        self.event_processor_thread = None

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def stop(self):
        self.abort_flag.set()

    def run(self):
        # If we have a config set to run a schedule, then start the process.
        # Otherwise close this thread now.
        self._log("Starting EventMonitorManager loop")
        while not self.abort_flag.is_set():
            # Check settings to ensure the event monitor should be enabled...
            if self.settings.get_enable_inotify():
                # If enabled, ensure it is running and start it if it is not
                if not self.event_processor_thread:
                    self.start_event_processor()
            else:
                # If not enabled, ensure the EventProcessor is not running and stop it if it is
                if self.event_processor_thread:
                    self.stop_event_processor()
            # Add delay
            time.sleep(1)

        self.stop_event_processor()
        self._log("Leaving EventMonitorManager loop...")

    def start_event_processor(self):
        """
        Start the EventProcessor thread if it is not already running.

        :return:
        """
        if not self.event_processor_thread:
            self._log("EventMonitorManager spawning EventProcessor thread...")
            wm = pyinotify.WatchManager()
            wm.add_watch(self.settings.get_library_path(), pyinotify.ALL_EVENTS, rec=True)
            # event processor
            ep = EventProcessor(self.data_queues, self.settings)
            # notifier
            self.event_processor_thread = pyinotify.ThreadedNotifier(wm, ep)
            self.event_processor_thread.start()
        else:
            self._log("Given signal to start the EventProcessor thread, but it is already running....")

    def stop_event_processor(self):
        """
        Stop the EventProcessor thread if it is running.

        :return:
        """
        if self.event_processor_thread:
            self._log("EventMonitorManager stopping EventProcessor thread...")

            self._log("Sending thread EventProcessor abort signal")
            self.event_processor_thread.stop()

            self._log("Waiting for thread EventProcessor to stop")
            self.event_processor_thread.join()
            self._log("Thread EventProcessor has successfully stopped")
        else:
            self._log("Given signal to stop the EventProcessor thread, but it is not running...")

        self.event_processor_thread = None

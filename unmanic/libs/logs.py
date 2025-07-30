#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.unlogger.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     06 Jan 2019, (8:41 AM)

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
import logging
import threading
import json
import time
from logging.handlers import RotatingFileHandler
from queue import Queue, Empty
import requests
from datetime import datetime, timedelta
from json_log_formatter import JSONFormatter


class ForwardJSONFormatter(JSONFormatter):
    """
    JSON log formatter which adds log record attributes if debugging is enabled.
    """

    def json_record(self, message, extra, record):
        # Check the logger's effective level
        logger = logging.getLogger(record.name)
        # Always include levelname used for labels
        extra['levelname'] = record.levelname
        # If the logger's effective level is DEBUG, add more context
        if logger.getEffectiveLevel() == logging.DEBUG:
            extra['filename'] = record.filename
            extra['funcName'] = record.funcName
            extra['lineno'] = record.lineno
            extra['module'] = record.module
            extra['name'] = record.name
            extra['pathname'] = record.pathname
            extra['process'] = record.process
            extra['processName'] = record.processName
            if hasattr(record, 'stack_info'):
                extra['stack_info'] = record.stack_info
            else:
                extra['stack_info'] = None
            extra['thread'] = record.thread
            extra['threadName'] = record.threadName
        # Choose time from metric_timestamp or data_timestamp
        ts_str = extra.get('metric_timestamp') or extra.get('data_timestamp')
        if ts_str:
            try:
                ts_float = float(ts_str)
                extra['time'] = datetime.utcfromtimestamp(ts_float).isoformat()
            except Exception:
                pass  # Ignore this. The default formatter will add a "time" record
        return super(ForwardJSONFormatter, self).json_record(message, extra, record)


class ForwardLogHandler(logging.Handler):
    """
    A custom log handler that:
    - Writes incoming logs to disk in chunk files at intervals or size thresholds.
    - A separate thread reads these chunk files from disk and forwards them.
    - On success, chunk files are removed.
    - On failure, chunk files remain for later retry.
    """

    def __init__(self, buffer_path, installation_name, labels=None, flush_interval=5, max_chunk_size=5 * 1024 * 1024):
        # TODO: Set default flush interval to 10 seconds
        super().__init__()
        self.buffer_path = buffer_path
        self.endpoint = None
        self.app_id = None
        self.installation_name = installation_name
        self.labels = labels if labels is not None else {"job": "unmanic"}
        self.flush_interval = flush_interval
        self.max_chunk_size = max_chunk_size

        self.log_queue = Queue()
        self.stop_event = threading.Event()

        # Thread that processes logs from the queue and writes them to disk
        self.writer_thread = threading.Thread(target=self._process_logs, daemon=True)
        self.writer_thread.start()

        # Thread that periodically attempts to send logs from disk
        self.sender_thread = threading.Thread(target=self._send_from_disk, daemon=True)
        self.sender_thread.start()

        self.previous_connection_failed = False

    def configure_endpoint(self, endpoint, app_id):
        self.endpoint = endpoint
        self.app_id = app_id

    def emit(self, record):
        try:
            log_entry = self.format(record)

            # Set log timestamp in nanoseconds
            ts = str(int(time.time() * 1e9))
            if hasattr(record, 'created'):
                ts = str(int(record.created * 1e9))

            # Set default labels
            labels = {
                "service_name":      "unmanic",  # This is a required label
                "logger":            record.name,
                "level":             record.levelname,
                "installation_name": self.installation_name,
                "log_type":          "APPLICATION_LOG",
            }

            # If the record has a log_type attribute, override
            if hasattr(record, 'log_type') and record.log_type:
                labels['log_type'] = record.log_type

            # If the record has a metric_name attribute, add it as a label
            if hasattr(record, 'metric_name') and record.metric_name:
                labels['metric_name'] = record.metric_name

            # If the record has a data_primary_key attribute, add it as a label
            if hasattr(record, 'data_primary_key') and record.data_primary_key:
                labels['data_primary_key'] = record.data_primary_key

            self.log_queue.put({
                "labels": labels,
                "entry":  [ts, log_entry]
            })
        except Exception as e:
            logging.getLogger("Unmanic.ForwardLogHandler").error("Failed to enqueue log: %s", e)

    def _process_logs(self):
        """
        Reads logs from the queue and writes them to disk in chunks.
        Chunks are created either at flush_interval timeout or if max_chunk_size is reached.
        """
        buffer = []
        buffer_size = 0
        last_flush_time = int(time.time())

        while not self.stop_event.is_set():

            try:
                log_entry = self.log_queue.get(timeout=0.2)
                if log_entry is None:
                    # Sentinel received, means shutdown is requested
                    break
                # Process the log entry
                buffer.append(log_entry)
                buffer_size += len(log_entry)

                # If size exceeds max_chunk_size, flush now
                if buffer_size >= self.max_chunk_size:
                    self._flush_to_disk(buffer)
                    buffer = []
                    buffer_size = 0
                    last_flush_time = int(time.time())

            except Empty:
                # No logs available right now
                pass

            current_time = int(time.time())
            if current_time - last_flush_time >= 5:
                # Flush to disk if more than 5 seconds have passed
                if buffer:
                    self._flush_to_disk(buffer)
                    buffer = []
                    buffer_size = 0
                    last_flush_time = current_time

        # Outside the loop, if we are shutting down and have pending logs, flush them
        if buffer:
            self._flush_to_disk(buffer)

    def _flush_to_disk(self, buffer):
        """
        Write the given buffer of logs to a new chunk file on disk.
        The file name includes a timestamp to ensure ordering by time.
        """
        try:
            if not os.path.exists(self.buffer_path):
                os.makedirs(self.buffer_path)

            if not buffer:
                # Nothing in buffer
                return

            timestamp_str = datetime.utcnow().isoformat().replace(":", "-")
            buffer_file = os.path.join(self.buffer_path, f"log_buffer_{timestamp_str}.json.lock")

            with open(buffer_file, "w") as f:
                for log_entry in buffer:
                    f.write(json.dumps(log_entry) + "\n")

            # Rename the file to indicate it is ready for processing
            os.rename(buffer_file, buffer_file.rstrip(".lock"))
        except Exception as e:
            logging.getLogger("Unmanic.ForwardLogHandler").error("Failed to save logs to disk: %s", e)

    def _send_from_disk(self):
        """
        Periodically attempts to send logs from disk.
        Processes one file at a time, oldest first (important).
        If successful (204), deletes the file.
        If failed, leaves the file for later retry.
        """
        while not self.stop_event.is_set():
            # Just loop if no endpoint is set
            if not self.endpoint or not self.app_id:
                self.stop_event.wait(timeout=10)
                continue
            # Attempt to send the oldest file first
            buffer_files = self._get_buffer_files()
            if not buffer_files:
                # No files to send, sleep
                self.stop_event.wait(timeout=10)
                continue

            for buffer_file in buffer_files:
                # Ignore files that are too old
                if self._buffer_file_too_old(buffer_file):
                    os.remove(buffer_file)
                    self.stop_event.wait(timeout=0.2)
                    continue
                # Ignore if no endpoint is set
                if not self.endpoint or not self.app_id:
                    self.stop_event.wait(timeout=0.2)
                    continue
                if not self._attempt_send_file(buffer_file):
                    # Add a longer pause here and then retry after the delay
                    self.stop_event.wait(timeout=60)
                self.stop_event.wait(timeout=0.2)
                if self.stop_event.is_set():
                    break
            self.stop_event.wait(timeout=0.2)

    def _get_buffer_files(self):
        """
        Returns a sorted list of buffer files based on their timestamp in the filename.
        """
        if not os.path.exists(self.buffer_path):
            return []
        files = [f for f in os.listdir(self.buffer_path) if f.startswith("log_buffer_") and f.endswith(".json")]
        files.sort()
        return [os.path.join(self.buffer_path, f) for f in files]

    def _attempt_send_file(self, buffer_file):
        """
        Attempt to send the logs from buffer_file.
        On success, delete the file.
        On failure, leave it for next retry.
        """
        try:
            buffer = []
            with open(buffer_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        buffer.append(json.loads(line))

            if not buffer:
                # Empty file, just remove it
                os.remove(buffer_file)
                return True

            payload = self._create_payload(buffer)
            response = requests.post(f"{self.endpoint}/api/v1/push", json=payload,
                                     headers={"Content-Type": "application/json"})

            if response.status_code == 204:
                # Success, remove the file
                os.remove(buffer_file)
                if self.previous_connection_failed:
                    self.previous_connection_failed = False
                    logging.getLogger("Unmanic.ForwardLogHandler").info("Successfully flushed log buffer after retry.")
                return True
            else:
                # The buffer file will be left here for another retry later on
                self.previous_connection_failed = True
                logging.getLogger("Unmanic.ForwardLogHandler").error(
                    "Failed to forward logs from %s to remote host %s: %s %s",
                    os.path.basename(buffer_file),
                    self.endpoint,
                    response.status_code,
                    response.text)
        except requests.exceptions.ConnectionError as e:
            # Ignore this. We will try again later
            logging.getLogger("Unmanic.ForwardLogHandler").warning(
                "ConnectionError on remote endpoint %s. Ensure this URL is reachable by Unmanic.",
                self.endpoint)
            self.previous_connection_failed = True
        except Exception as e:
            # Ignore this. We will try again later
            logging.getLogger("Unmanic.ForwardLogHandler").exception(
                "Exception while trying to forward logs from %s: %s",
                buffer_file, e)
            self.previous_connection_failed = True
        return False

    @staticmethod
    def _buffer_file_too_old(buffer_file, max_days=14):
        """
        Check if the log buffer file is older than the specified number of days based on its timestamp in the filename.

        The expected filename format is:
          log_buffer_YYYY-MM-DDTHH-MM-SS.ffffff.json

        Returns True if the timestamp is older than max_days, otherwise False.
        """
        basename = os.path.basename(buffer_file)
        prefix = "log_buffer_"
        suffix = ".json"

        if not (basename.startswith(prefix) and basename.endswith(suffix)):
            return False  # Filename doesn't match expected pattern.

        # Extract the timestamp part from the filename.
        timestamp_str = basename[len(prefix):-len(suffix)]

        # Migrate from old format (log_buffer_YYYY-MM-DDTHH:MM:SS.ffffff.json)
        try:
            # Try new format first (with colons replaced by dashes)
            file_timestamp = datetime.strptime(timestamp_str, "%Y-%m-%dT%H-%M-%S.%f")
        except ValueError:
            try:
                # Fallback to old format with colons
                file_timestamp = datetime.fromisoformat(timestamp_str)
            except ValueError:
                # Unable to parse the timestamp.
                return False

        max_age_threshold = datetime.now() - timedelta(days=max_days)
        return file_timestamp < max_age_threshold

    def _create_payload(self, buffer):
        """
        Create the payload from the given buffer of logs.
        {
          "streams": [
            {
              "stream": { "label": "value", ... },
              "values": [
                [ "<ts in ns>", "<log line>" ],
                ...
              ]
            }
          ]
        }
        """
        combined_streams = {}
        for log_item in buffer:
            stream_key = frozenset(log_item["labels"].items())
            if stream_key not in combined_streams:
                combined_streams[stream_key] = {
                    "stream": dict(log_item["labels"]),
                    "values": []
                }
            combined_streams[stream_key]["values"].append(log_item["entry"])

        return {
            "app_id": self.app_id,
            "data":   {"streams": list(combined_streams.values())}
        }

    def close(self):
        """
        Stop the log handler gracefully.
        Ensures all logs in the queue are flushed to disk.
        """
        # Place Sentinel entry into queue to indicate that no more logs should be processed
        self.log_queue.put(None)

        # Signal the thread to stop
        self.stop_event.set()

        # Wait for the threads to finish processing
        self.writer_thread.join()
        self.sender_thread.join()

        # Explicitly flush any remaining logs in the queue
        remaining_logs = []
        while True:
            try:
                log_entry = self.log_queue.get(timeout=1)
                if log_entry is not None:
                    remaining_logs.append(log_entry)
            except Empty:
                # No logs available right now, break loop
                break

        if remaining_logs:
            self._flush_to_disk(remaining_logs)

        super().close()


class UnmanicLogging:
    METRIC = 9
    DATA = 8
    _instance = None
    _lock = threading.Lock()
    _configured = False
    _log_path = None
    stream_handler = None  # Stream handler
    file_handler = None  # File handler
    remote_handler = None  # Remote log handler

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UnmanicLogging, cls).__new__(cls)
                cls._instance._logger = logging.getLogger("Unmanic")
                logging.addLevelName(cls._instance.METRIC, "METRIC")
                logging.addLevelName(cls._instance.DATA, "DATA")
                cls._instance._logger.setLevel(logging.INFO)
                cls._instance._logger.propagate = False
            return cls._instance

    @staticmethod
    def get_logger(name=None, settings=None):
        """
        Get a child logger. Configure the root logger if 'settings' are provided.
        """
        logger_instance = UnmanicLogging()
        if settings and not logger_instance._configured:
            logger_instance.configure(settings)

        if name:
            return logging.getLogger(f"Unmanic.{name}")
        return logger_instance._logger

    def configure(self, settings):
        """
        Configure the logger using the provided Config settings instance.

        :param settings: Instance of Config class with application settings.
        """
        with self._lock:
            if self._configured:
                return
            # Get logger for this class
            init_logger = logging.getLogger(f"Unmanic.UnmanicLogging")

            # Default formatter
            formatter = logging.Formatter(
                '%(asctime)s:%(levelname)s:%(name)s - %(message)s',
                datefmt='%Y-%m-%dT%H:%M:%S'
            )

            # Set up stream handler
            if self.stream_handler is None:
                self.stream_handler = logging.StreamHandler()
                self.stream_handler.setFormatter(formatter)
                # Set the log level of the stream handle for this log line only
                self.stream_handler.setLevel(logging.INFO)
                self._logger.addHandler(self.stream_handler)
                # Add an info log to let users know where to look for their logs
                init_logger.info("Initialising file logger. All further logs should output to the 'unmanic.log' file")
                # Set the log level of the stream handle always to error
                self.stream_handler.setLevel(logging.CRITICAL)

            # Set up file handler if log path exists
            self._log_path = settings.get_log_path()
            if self._log_path:
                if not os.path.exists(self._log_path):
                    os.makedirs(self._log_path)

                self.file_handler = RotatingFileHandler(
                    os.path.join(self._log_path, "unmanic.log"), maxBytes=10 * 1024 * 1024, backupCount=5
                )
                self.file_handler.setFormatter(formatter)
                # Set file handler log level based on debugging setting
                self.file_handler.setLevel(logging.DEBUG if settings.get_debugging() else logging.INFO)
                self._logger.addHandler(self.file_handler)

            # Setup ForwardLogHandler
            json_formatter = ForwardJSONFormatter()
            buffer_path = os.path.join(self._log_path, "buffer")
            installation_name = settings.get_installation_name()
            self.remote_handler = ForwardLogHandler(buffer_path, installation_name)
            self.remote_handler.setFormatter(json_formatter)
            self.remote_handler.setLevel(self.DATA)
            self._logger.addHandler(self.remote_handler)

            # Set root logger level
            self._logger.setLevel(self.DATA)
            self._configured = True

    @staticmethod
    def metric(name: str, timestamp: datetime = None, **kwargs):
        """
        Custom log method for the METRIC level.
        Logs directly to the remote_handler, if enabled.
        """
        instance = UnmanicLogging()
        if not timestamp:
            timestamp = datetime.now()
        log_record = {
            'log_type':         'METRIC',
            'metric_name':      name,
            'metric_timestamp': f"{int(timestamp.timestamp())}.{timestamp.microsecond}",
            **kwargs
        }
        log_message = " ".join(
            f'{key}="{value}"' if " " in str(value) else f"{key}={value}"
            for key, value in log_record.items() if value
        )
        instance._logger.log(instance.METRIC, log_message, extra=log_record)

    @staticmethod
    def data(data_primary_key: str, data_search_key: str = None, timestamp: datetime = None, **kwargs):
        """
        Custom log method for the DATA level.
        Logs directly to the remote_handler, if enabled.
        """
        instance = UnmanicLogging()
        if not timestamp:
            timestamp = datetime.now()
        log_record = {
            'log_type':         'DATA',
            'data_primary_key': data_primary_key,
            'data_search_key':  data_search_key,
            'data_timestamp':   f"{int(timestamp.timestamp())}.{timestamp.microsecond}",
            **kwargs
        }
        log_message = "DATA STREAM"
        instance._logger.log(instance.DATA, log_message, extra=log_record)

    @staticmethod
    def enable_debugging():
        """
        Enable debugging globally across all threads.
        """
        instance = UnmanicLogging()
        instance._logger.setLevel(logging.DEBUG)
        instance._logger.info("Log level set to DEBUG")

    @staticmethod
    def disable_debugging():
        """
        Disable debugging globally across all threads.
        """
        instance = UnmanicLogging()
        instance._logger.setLevel(logging.INFO)
        instance._logger.info("Log level set to INFO")

    @staticmethod
    def disable_file_handler(debugging=False):
        """
        Disable logging to file and only log to stdout.

        :param debugging: If True, sets stream handler to DEBUG level; otherwise INFO level.
        """
        instance = UnmanicLogging()

        # Remove file handler if it exists
        if instance.file_handler:
            instance._logger.removeHandler(instance.file_handler)
            instance.file_handler = None
            instance._logger.info("File logging disabled. Logging only to stdout.")

        # Adjust stream handler level
        if instance.stream_handler:
            instance.stream_handler.setLevel(logging.DEBUG if debugging else logging.INFO)
            instance._logger.info(f"Stream logging set to {'DEBUG' if debugging else 'INFO'}")

    @staticmethod
    def update_stream_formatter(formatter):
        """
        Update the formatter of the stream handler.

        :param formatter: A logging.Formatter instance.
        """
        instance = UnmanicLogging()
        if instance.stream_handler:
            instance.stream_handler.setFormatter(formatter)
            instance._logger.info("Stream handler formatter updated.")
        else:
            instance._logger.warning("No stream handler found to update formatter.")

    @staticmethod
    def enable_remote_logging(endpoint, app_id):
        instance = UnmanicLogging()
        instance.remote_handler.configure_endpoint(endpoint, app_id)
        instance._logger.info("Remote logging enabled.")

    @staticmethod
    def disable_remote_logging():
        instance = UnmanicLogging()
        instance.remote_handler.configure_endpoint(None, None)
        instance._logger.info("Remote logging disabled.")

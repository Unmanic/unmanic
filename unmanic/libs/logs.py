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

from unmanic.libs.notifications import Notifications
from unmanic.libs.frontend_push_messages import FrontendPushMessages


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
    Forwards logs to a remote endpoint while maintaining an ordered on-disk buffer.
    """

    STATE_FILENAME = "buffer_state.json"
    _BATCH_MAX_ITEMS = 256
    _CLEANUP_INTERVAL_SECONDS = 600

    def __init__(self, buffer_path, installation_name, labels=None, flush_interval=5, max_chunk_size=5 * 1024 * 1024):
        """Initialise buffering paths, runtime state, and background threads."""
        super().__init__()
        self.buffer_path = buffer_path
        self.endpoint = None
        self.app_id = None
        self.installation_name = installation_name
        self.labels = labels if labels is not None else {"job": "unmanic"}
        self.flush_interval = flush_interval
        self.max_chunk_size = max_chunk_size

        self.buffer_retention_max_days = None
        self._retention_disabled = False

        self._state_lock = threading.Lock()
        self._buffer_state_path = os.path.join(self.buffer_path, self.STATE_FILENAME)
        self._buffer_state = self._load_buffer_state()

        self._in_memory_chunks = Queue()
        self.log_queue = Queue()
        self.stop_event = threading.Event()

        self._last_cleanup = time.monotonic()
        self.previous_connection_failed = False
        self._notified_failures = set()

        self._sync_state_with_disk()

        self.writer_thread = threading.Thread(target=self._writer_loop, daemon=True)
        self.writer_thread.start()

        self.sender_thread = threading.Thread(target=self._sender_loop, daemon=True)
        self.sender_thread.start()

    def configure_endpoint(self, endpoint, app_id):
        """Update the remote endpoint used for forwarding."""
        self.endpoint = endpoint
        self.app_id = app_id

    def configure_retention(self, max_days):
        """Toggle disk retention and track the configured horizon in days."""
        try:
            max_days_int = int(max_days)
        except (TypeError, ValueError):
            if max_days is not None:
                logging.getLogger("Unmanic.ForwardLogHandler").warning(
                    "Invalid log buffer retention value %r. Falling back to default.",
                    max_days
                )
            max_days_int = None

        if max_days_int is not None and max_days_int < 0:
            max_days_int = 0

        previously_disabled = self._retention_disabled
        self.buffer_retention_max_days = max_days_int
        self._retention_disabled = max_days_int == 0

        if previously_disabled and not self._retention_disabled:
            self._spill_memory_chunks_to_disk()

    def emit(self, record):
        """Format a record and enqueue it for asynchronous handling."""
        try:
            log_entry = self.format(record)

            # Set log timestamp in nanoseconds
            ts = str(int(time.time() * 1e9))
            if hasattr(record, "created"):
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
            if hasattr(record, "log_type") and record.log_type:
                labels["log_type"] = record.log_type

            # If the record has a metric_name attribute, add it as a label
            if hasattr(record, "metric_name") and record.metric_name:
                labels["metric_name"] = record.metric_name

            # If the record has a data_primary_key attribute, add it as a label
            if hasattr(record, "data_primary_key") and record.data_primary_key:
                labels["data_primary_key"] = record.data_primary_key

            self.log_queue.put({
                "labels": labels,
                "entry":  [ts, log_entry]
            })
        except Exception as e:
            logging.getLogger("Unmanic.ForwardLogHandler").error("Failed to enqueue log: %s", e)

    def _writer_loop(self):
        """Drain the queue into either the disk-backed buffer or the in-memory queue."""
        batch = []
        last_flush = time.monotonic()

        while not self.stop_event.is_set():

            try:
                log_entry = self.log_queue.get(timeout=0.2)
                if log_entry is None:
                    # Sentinel received, means shutdown is requested
                    break
                batch.append(log_entry)
                if len(batch) >= self._BATCH_MAX_ITEMS:
                    self._handle_batch(batch)
                    batch = []
                    last_flush = time.monotonic()
            except Empty:
                pass

            if batch and (time.monotonic() - last_flush) >= self.flush_interval:
                self._handle_batch(batch)
                batch = []
                last_flush = time.monotonic()

        if batch:
            self._handle_batch(batch)

    def _handle_batch(self, batch):
        """Send a batch to in-memory or disk storage depending on retention mode."""
        if not batch:
            return
        if self._retention_disabled:
            self._in_memory_chunks.put(list(batch))
            return
        self._append_to_disk(batch)

    def _append_to_disk(self, batch):
        """Append log entries to the current hour's JSONL buffer file."""
        if not batch:
            return
        try:
            os.makedirs(self.buffer_path, exist_ok=True)
            buffer_file = self._get_hourly_buffer_file()
            with open(buffer_file, "a", encoding="utf-8") as handle:
                for log_entry in batch:
                    handle.write(json.dumps(log_entry))
                    handle.write("\n")
            self._ensure_state_entry(os.path.basename(buffer_file))
        except Exception as exc:
            logging.getLogger("Unmanic.ForwardLogHandler").error("Failed to save logs to disk: %s", exc)

    def _ensure_state_entry(self, filename):
        """Register a new buffer file with an initial offset of zero."""
        with self._state_lock:
            if filename not in self._buffer_state:
                self._buffer_state[filename] = 0
                self._persist_state_locked()

    def _sender_loop(self):
        """Continuously attempt to forward buffered logs, oldest first."""
        while not self.stop_event.is_set():
            processed = False

            if self._send_next_disk_batch():
                processed = True
            else:
                if self._send_from_memory():
                    processed = True

            now = time.monotonic()
            if now - self._last_cleanup >= self._CLEANUP_INTERVAL_SECONDS:
                self._cleanup_retention()
                self._last_cleanup = now

            wait_time = 0.2 if processed else 2
            self.stop_event.wait(timeout=wait_time)

    def _send_next_disk_batch(self):
        """Send the next available chunk from disk, returning True on success."""
        if not (self.endpoint and self.app_id):
            return False

        chunk = self._read_next_disk_chunk()
        if not chunk:
            return False

        file_path, start_offset, end_offset, entries, payload = chunk
        filename = os.path.basename(file_path)

        if not self._transmit_buffer(entries, filename, payload):
            return False

        self._update_state_offset(filename, end_offset)
        self._maybe_remove_consumed_file(file_path)
        return True

    def _read_next_disk_chunk(self):
        """Determine the next readable slice of buffered logs on disk."""
        files = self._list_buffer_files()
        if not files:
            return None

        for file_path in files:
            filename = os.path.basename(file_path)

            with self._state_lock:
                offset = self._buffer_state.get(filename, 0)

            try:
                file_size = os.path.getsize(file_path)
            except FileNotFoundError:
                self._remove_state_entry(filename)
                continue

            if offset > file_size:
                offset = 0

            chunk = self._read_file_chunk(file_path, filename, offset)
            if chunk:
                return chunk

            if offset >= file_size:
                self._maybe_remove_consumed_file(file_path)

        return None

    def _read_file_chunk(self, file_path, filename, offset):
        """Read entries from a single file until the payload nears the 5 MB threshold."""
        entries = []
        payload = None
        payload_size = 0
        new_offset = offset

        try:
            with open(file_path, "rb") as handle:
                handle.seek(offset)
                while True:
                    line_start = handle.tell()
                    line_bytes = handle.readline()
                    if not line_bytes:
                        break
                    line_end = handle.tell()
                    stripped = line_bytes.strip()
                    if not stripped:
                        new_offset = line_end
                        continue
                    try:
                        entry = json.loads(stripped.decode("utf-8"))
                    except Exception:
                        logging.getLogger("Unmanic.ForwardLogHandler").warning(
                            "Skipping corrupt log entry in %s.",
                            filename,
                        )
                        new_offset = line_end
                        continue

                    entries.append(entry)
                    payload, payload_size = self._build_payload(entries)
                    if payload_size > self.max_chunk_size:
                        if len(entries) == 1:
                            logging.getLogger("Unmanic.ForwardLogHandler").warning(
                                "Single log entry in %s exceeds max chunk size (%s bytes). Sending anyway.",
                                filename,
                                payload_size,
                            )
                            new_offset = line_end
                            break
                        entries.pop()
                        payload, payload_size = self._build_payload(entries)
                        handle.seek(line_start)
                        new_offset = line_start
                        break

                    new_offset = line_end
                    if payload_size >= self.max_chunk_size * 0.9:
                        break
        except FileNotFoundError:
            self._remove_state_entry(filename)
            return None
        except Exception as exc:
            logging.getLogger("Unmanic.ForwardLogHandler").exception(
                "Failed reading log buffer %s: %s",
                filename,
                exc,
            )
            return None

        if not entries:
            return None

        if payload is None:
            payload, payload_size = self._build_payload(entries)

        return file_path, offset, new_offset, entries, payload

    def _build_payload(self, entries):
        """Return a payload dict and byte size for the given entries."""
        payload = self._create_payload(entries)
        payload_bytes = json.dumps(payload).encode("utf-8")
        return payload, len(payload_bytes)

    def _update_state_offset(self, filename, offset):
        """Persist the latest read offset for a buffer file."""
        with self._state_lock:
            self._buffer_state[filename] = offset
            self._persist_state_locked()

    def _maybe_remove_consumed_file(self, file_path):
        """Delete a buffer file once all bytes have been transmitted and it's past the hour."""
        filename = os.path.basename(file_path)
        try:
            file_size = os.path.getsize(file_path)
        except FileNotFoundError:
            self._remove_state_entry(filename)
            return

        with self._state_lock:
            offset = self._buffer_state.get(filename, 0)

        if offset < file_size:
            return

        timestamp = self._parse_buffer_filename_timestamp(filename)
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        if timestamp and timestamp >= current_hour:
            return

        try:
            os.remove(file_path)
        except FileNotFoundError:
            pass
        self._remove_state_entry(filename)

    def _cleanup_retention(self):
        """Remove buffer files that sit beyond the configured retention horizon."""
        if not self.buffer_retention_max_days or self.buffer_retention_max_days <= 0:
            return
        threshold = datetime.utcnow() - timedelta(days=self.buffer_retention_max_days)

        # TODO: remove legacy `.json` cleanup once all older buffer files are gone in the wild.
        if os.path.isdir(self.buffer_path):
            for legacy_name in os.listdir(self.buffer_path):
                if not legacy_name.endswith(".json"):
                    continue
                legacy_path = os.path.join(self.buffer_path, legacy_name)
                try:
                    os.remove(legacy_path)
                except FileNotFoundError:
                    pass

        for file_path in self._list_buffer_files():
            filename = os.path.basename(file_path)
            timestamp = self._parse_buffer_filename_timestamp(filename)
            if timestamp and timestamp < threshold:
                try:
                    os.remove(file_path)
                except FileNotFoundError:
                    pass
                self._remove_state_entry(filename)

    def _send_from_memory(self):
        """Drain in-memory batches while enforcing the 5 MB payload limit."""
        processed = False
        while True:
            try:
                chunk = self._in_memory_chunks.get_nowait()
            except Empty:
                break

            index = 0
            while index < len(chunk):
                sub_entries, consumed, payload = self._slice_entries_for_send(chunk[index:])
                if not sub_entries:
                    break

                if not (self.endpoint and self.app_id):
                    remaining = chunk[index:]
                    if remaining:
                        self._in_memory_chunks.put(list(remaining))
                    return processed

                if not self._transmit_buffer(sub_entries, "in-memory chunk", payload):
                    remaining = list(sub_entries) + chunk[index + consumed:]
                    if remaining:
                        self._in_memory_chunks.put(list(remaining))
                    return processed

                processed = True
                index += consumed

        return processed

    def _slice_entries_for_send(self, entries):
        """Return a sub-batch that fits inside the max payload size."""
        if not entries:
            return [], 0, None

        chunk = []
        payload = None
        payload_size = 0

        for entry in entries:
            chunk.append(entry)
            payload, payload_size = self._build_payload(chunk)
            if payload_size > self.max_chunk_size:
                if len(chunk) == 1:
                    logging.getLogger("Unmanic.ForwardLogHandler").warning(
                        "Single in-memory log entry exceeds max chunk size (%s bytes). Sending anyway.",
                        payload_size,
                    )
                    return chunk, 1, payload
                chunk.pop()
                payload, payload_size = self._build_payload(chunk)
                return chunk, len(chunk), payload
            if payload_size >= self.max_chunk_size * 0.9:
                return chunk, len(chunk), payload

        return chunk, len(chunk), payload

    def _get_hourly_buffer_file(self):
        """Return the JSONL filename for the current UTC hour."""
        current_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        timestamp = current_hour.strftime("%Y%m%dT%H")
        return os.path.join(self.buffer_path, f"log_buffer_{timestamp}.jsonl")

    def _list_buffer_files(self):
        """Return all buffer filenames sorted chronologically."""
        if not os.path.isdir(self.buffer_path):
            return []
        files = [
            os.path.join(self.buffer_path, name)
            for name in os.listdir(self.buffer_path)
            if name.startswith("log_buffer_") and (name.endswith(".jsonl") or name.endswith(".json"))
        ]
        files.sort()
        return files

    def _parse_buffer_filename_timestamp(self, filename):
        """Parse the UTC hour encoded in a JSONL buffer filename."""
        prefix = "log_buffer_"
        suffix = ".jsonl"
        if not filename.startswith(prefix) or not filename.endswith(suffix):
            return None
        timestamp_str = filename[len(prefix):-len(suffix)]
        try:
            return datetime.strptime(timestamp_str, "%Y%m%dT%H")
        except ValueError:
            return None

    def _spill_memory_chunks_to_disk(self):
        """Persist in-memory batches when retention becomes enabled again."""
        pending = []
        while True:
            try:
                pending.extend(self._in_memory_chunks.get_nowait())
            except Empty:
                break

        if not pending:
            return

        for start in range(0, len(pending), self._BATCH_MAX_ITEMS):
            self._append_to_disk(pending[start:start + self._BATCH_MAX_ITEMS])

    def _load_buffer_state(self):
        """Read the persisted offsets mapping from disk, if present."""
        if not os.path.exists(self._buffer_state_path):
            return {}
        try:
            with open(self._buffer_state_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception:
            logging.getLogger("Unmanic.ForwardLogHandler").warning(
                "Failed to load log buffer state. Starting fresh.")
            return {}

        files = data.get("files", {})
        state = {}
        for name, offset in files.items():
            try:
                state[name] = int(offset)
            except (TypeError, ValueError):
                continue
        return state

    def _persist_state_locked(self):
        """Write the state file atomically; caller must hold `_state_lock`."""
        try:
            os.makedirs(self.buffer_path, exist_ok=True)
            temp_path = f"{self._buffer_state_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as handle:
                json.dump({"files": self._buffer_state}, handle)
            os.replace(temp_path, self._buffer_state_path)
        except Exception as exc:
            logging.getLogger("Unmanic.ForwardLogHandler").warning(
                "Failed to persist log buffer state: %s",
                exc,
            )

    def _persist_state(self):
        """Public helper to persist state with locking."""
        with self._state_lock:
            self._persist_state_locked()

    def _remove_state_entry(self, filename):
        """Drop a single filename from the persisted offsets mapping."""
        with self._state_lock:
            if filename in self._buffer_state:
                del self._buffer_state[filename]
                self._persist_state_locked()

    def _sync_state_with_disk(self):
        """Ensure state entries only reference buffer files that still exist."""
        if not os.path.isdir(self.buffer_path):
            return
        existing = {
            name
            for name in os.listdir(self.buffer_path)
            if name.startswith("log_buffer_") and name.endswith(".jsonl")
        }
        with self._state_lock:
            changed = False
            for name in list(self._buffer_state.keys()):
                if name not in existing:
                    del self._buffer_state[name]
                    changed = True
            for name in existing:
                if name not in self._buffer_state:
                    self._buffer_state[name] = 0
                    changed = True
            if changed:
                self._persist_state_locked()

    def _transmit_buffer(self, entries, buffer_label, payload=None):
        """Send a payload to the remote endpoint, logging any retriable failures."""
        if not entries:
            return True
        if not (self.endpoint and self.app_id):
            return False

        if payload is None:
            payload = self._create_payload(entries)

        try:
            response = requests.post(
                f"{self.endpoint}/api/v1/push",
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 204:
                if self.previous_connection_failed:
                    self.previous_connection_failed = False
                    self._notified_failures.clear()
                    logging.getLogger("Unmanic.ForwardLogHandler").info("Successfully flushed log buffer after retry.")
                return True

            self.previous_connection_failed = True
            message_text = "Failed to forward logs to remote host {}: {} {}".format(
                self.endpoint,
                response.status_code,
                response.text,
            )

            status_key = str(response.status_code)

            if status_key not in self._notified_failures:
                notifications = Notifications()
                notifications.update({
                    'uuid':       f'forwardLogHandlerError_{response.status_code}',
                    'type':       'warning',
                    'icon':       'report_problem',
                    'label':      'forwardLogHandlerErrorLabel',
                    'message':    message_text,
                    'navigation': {
                        'push': '/ui/settings-support',
                    },
                })

                frontend_messages = FrontendPushMessages()
                frontend_messages.add(
                    {
                        'id':      f'forwardLogHandlerError_{response.status_code}',
                        'type':    'error',
                        'code':    'forwardLogHandlerError',
                        'message': message_text,
                        'timeout': 20000
                    }
                )
                logging.getLogger("Unmanic.ForwardLogHandler").error(message_text)
                self._notified_failures.add(status_key)
        except requests.exceptions.ConnectionError:
            logging.getLogger("Unmanic.ForwardLogHandler").warning(
                "ConnectionError on remote endpoint %s while sending %s. Ensure this URL is reachable by Unmanic.",
                self.endpoint,
                buffer_label,
            )
            self.previous_connection_failed = True
        except Exception as exc:
            logging.getLogger("Unmanic.ForwardLogHandler").exception(
                "Exception while trying to forward logs from %s: %s",
                buffer_label,
                exc,
            )
            self.previous_connection_failed = True
            self._notified_failures.add('EXCEPTION')
        return False

    def _create_payload(self, buffer):
        """Group entries by labels to produce the payload expected by the remote API."""
        combined_streams = {}
        for log_item in buffer:
            stream_key = frozenset(log_item["labels"].items())
            if stream_key not in combined_streams:
                combined_streams[stream_key] = {
                    "stream": dict(log_item["labels"]),
                    "values": [],
                }
            combined_streams[stream_key]["values"].append(log_item["entry"])

        return {
            "app_id": self.app_id,
            "data":   {"streams": list(combined_streams.values())},
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
                log_entry = self.log_queue.get_nowait()
            except Empty:
                # No logs available right now, break loop
                break
            if log_entry is not None:
                remaining_logs.append(log_entry)

        if remaining_logs:
            self._handle_batch(remaining_logs)

        self._persist_state()

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
    def enable_remote_logging(endpoint, app_id, log_buffer_retention):
        instance = UnmanicLogging()
        instance.remote_handler.configure_retention(log_buffer_retention)
        instance.remote_handler.configure_endpoint(endpoint, app_id)

        instance._logger.info("Remote logging enabled.")

    @staticmethod
    def disable_remote_logging(log_buffer_retention):
        instance = UnmanicLogging()
        instance.remote_handler.configure_retention(log_buffer_retention)
        instance.remote_handler.configure_endpoint(None, None)
        instance._logger.info("Remote logging disabled.")

    @staticmethod
    def set_remote_logging_retention(log_buffer_retention):
        """
        Enable debugging globally across all threads.
        """
        instance = UnmanicLogging()
        instance.remote_handler.configure_retention(log_buffer_retention)
        instance._logger.info("Remote logging buffer retention set to %s days.", log_buffer_retention)

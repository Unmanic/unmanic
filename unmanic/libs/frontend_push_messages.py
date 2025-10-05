#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.frontend_push_messages.py

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

           THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
           EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
           MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
           IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
           DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
           OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
           OR OTHER DEALINGS IN THE SOFTWARE.

"""
import threading
from queue import Queue, Empty

from unmanic.libs.singleton import SingletonType


class FrontendPushMessages(Queue, metaclass=SingletonType):
    """
    Handles messages passed to the frontend.

    Messages are sent as objects. These objects require the following fields:
        - 'id'          : A unique ID of the message. Prevent messages duplication
        - 'type'        : The type of message - 'error', 'warning', 'success', or 'info'
        - 'code'        : A code to represent an I18n string for the frontend to display
        - 'message'     : Additional message string that can be appended to the I18n string displayed on the frontend.
        - 'timeout'     : The timeout for this message. If set to 0, then the message will persist until manually dismissed.

    """

    def _init(self, maxsize):
        self._lock = threading.RLock()
        self.all_items = set()
        Queue._init(self, maxsize)

    def __add_to_queue_locked(self, item):
        # Add the item to the queue without blocking (lock already held)
        Queue.put_nowait(self, item)

    @staticmethod
    def __validate_item(item):
        # Ensure all required keys are present
        for key in ['id', 'type', 'code', 'message', 'timeout']:
            if key not in item:
                raise Exception("Frontend message item incorrectly formatted. Missing key: '{}'".format(key))

        # Ensure the given type is valid
        if item.get('type') not in ['error', 'warning', 'success', 'info', 'status']:
            raise Exception(
                "Frontend message item's code must be in ['error', 'warning', 'success', 'info', 'status']. Received '{}'".format(
                    item.get('type')
                )
            )
        return True

    def __get_all_items_locked(self):
        items = []
        while True:
            try:
                # Get all items out of queue
                items.append(self.get_nowait())
            except Empty:
                break
        return items

    def __requeue_items_locked(self, items):
        # Add all given items back into the queue
        for item in items:
            Queue.put_nowait(self, item)

    def add(self, item):
        # Ensure received item is valid
        self.__validate_item(item)
        with self._lock:
            item_id = item.get('id')
            if item_id in self.all_items:
                return
            self.all_items.add(item_id)
            self.__add_to_queue_locked(item)

    def get_all_items(self):
        items = []
        with self._lock:
            items = self.__get_all_items_locked()
            # Add all items back into the queue for continued processing
            self.__requeue_items_locked(items)
        return items

    def requeue_items(self, items):
        with self._lock:
            # Add all given items back into the queue
            self.__requeue_items_locked(items)

    def remove_item(self, item_id):
        with self._lock:
            current_items = self.__get_all_items_locked()
            requeue_items = []
            # Create list of items that will be queued again
            for current_item in current_items:
                if current_item.get('id') != item_id:
                    requeue_items.append(current_item)
            if item_id in self.all_items:
                self.all_items.remove(item_id)
            # Add all requeue_items items back into the queue
            self.__requeue_items_locked(requeue_items)

    def read_all_items(self):
        with self._lock:
            current_items = self.__get_all_items_locked()
            # Add all requeue_items items back into the queue
            self.__requeue_items_locked(current_items)
            return list(current_items)

    def update(self, item):
        # Ensure received item is valid
        self.__validate_item(item)
        item_id = item.get('id')
        with self._lock:
            current_items = self.__get_all_items_locked()

            requeue_items = []
            replaced = False
            # Create list of items that will be queued again, replacing matching IDs
            for current_item in current_items:
                if current_item.get('id') == item_id:
                    requeue_items.append(item)
                    replaced = True
                else:
                    requeue_items.append(current_item)
            if not replaced:
                self.all_items.add(item_id)
                # Restore original queue state before adding new item
                self.__requeue_items_locked(current_items)
                self.__add_to_queue_locked(item)
                return
            self.all_items.add(item_id)
            # Add all requeue_items items back into the queue
            self.__requeue_items_locked(requeue_items)

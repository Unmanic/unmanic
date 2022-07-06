#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.notifications.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     03 Jul 2022, (7:49 AM)

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
import uuid
from queue import Queue

from unmanic.libs.singleton import SingletonType


class Notifications(Queue, metaclass=SingletonType):
    """
    Handles messages passed to the frontend.

    Messages are sent as objects. These objects require the following fields:
        - 'uuid'            : A unique ID of the message. Prevent messages duplication
        - 'type'            : The type of message - 'error', 'warning', 'success', or 'info'
        - 'icon'            : The icon to display with the notification
        - 'label'           : A code to represent an I18n string for the frontend to display the notification label
        - 'message'         : The message string that is appended to the I18n string displayed on the frontend.
        - 'link'            : The link to be applied to the notification. Can be relative or a URL

    Examples:
        notifications = Notifications()

        # Place a notification
        notifications.add(
            {
                'uuid':       'failedTask',
                'type':       'error',
                'icon':       'report',
                'label':      'failedTaskLabel',
                'message':    'You have a new failed task in your completed tasks list',
                'navigation': {
                    'push': '/unmanic/ui/dashboard',
                    'events': [
                        'completedTasksShowMore',
                    ],
                },
            })

        # Remove an item
        notifications.remove('updateAvailable')

        # Read the current list of notifications
        notifications.read_all_items()

        # Update an item in place
        notifications.add(
            {
                'uuid':       'updateAvailable',
                'type':       'info',
                'icon':       'update',
                'label':      'updateAvailableLabel',
                'message':    'updateAvailableMessage',
                'navigation': {
                    'url': 'https://docs.unmanic.app',
                },
            })

    """

    def _init(self, maxsize):
        self.all_items = set()
        Queue._init(self, maxsize)

    def __add_to_queue(self, item, block=True, timeout=None):
        Queue.put(self, item, block, timeout)

    @staticmethod
    def __validate_item(item):
        # Ensure all required keys are present
        for key in ['type', 'icon', 'label', 'message', 'navigation']:
            if key not in item:
                raise Exception("Frontend message item incorrectly formatted. Missing key: '{}'".format(key))

        # Ensure the given type is valid
        if item.get('type') not in ['error', 'warning', 'success', 'info']:
            raise Exception(
                "Frontend message item's code must be in ['error', 'warning', 'success', 'info', 'status']. Received '{}'".format(
                    item.get('type')
                )
            )
        return True

    def __get_all_items(self):
        items = []
        while not self.empty():
            items.append(self.get())
        return items

    def __requeue_items(self, items):
        for item in items:
            self.__add_to_queue(item)

    def add(self, item):
        # Ensure received item is valid
        self.__validate_item(item)
        # Generate uuid if one is not provided
        if not item.get('uuid'):
            item['uuid'] = str(uuid.uuid4())
        # If it is not already in message list, add it to the list and the queue
        if item.get('uuid') not in self.all_items:
            self.all_items.add(item.get('uuid'))
            self.__add_to_queue(item)

    def remove(self, item_uuid):
        """
        Remove a single item from the notifications list given it's UUID

        :param item_uuid:
        :return:
        """
        success = False
        # Get all items out of queue
        current_items = self.__get_all_items()
        # Create list of items that will be queued again
        requeue_items = []
        for current_item in current_items:
            if current_item.get('uuid') != item_uuid:
                requeue_items.append(current_item)
        # Remove the requested item UUID from the all_items set
        lock = threading.RLock()
        lock.acquire()
        if item_uuid in self.all_items:
            self.all_items.remove(item_uuid)
            success = True
        lock.release()
        # Add all requeue_items items back into the queue
        self.__requeue_items(requeue_items)
        return success

    def read_all_items(self):
        # Get all items out of queue
        current_items = self.__get_all_items()
        # Add all requeue_items items back into the queue
        self.__requeue_items(current_items)
        # Return items list
        return current_items

    def update(self, item):
        # Ensure received item is valid
        self.__validate_item(item)
        # Generate uuid if one is not provided
        if not item.get('uuid'):
            item['uuid'] = str(uuid.uuid4())
        # If it is not already in message list, add it to the list and the queue
        if item.get('uuid') not in self.all_items:
            self.all_items.add(item.get('uuid'))
            self.__add_to_queue(item)
        else:
            # Get all items out of queue
            current_items = self.__get_all_items()
            # Create list of items that will be queued again
            # This will not include the item requested for update
            lock = threading.RLock()
            lock.acquire()
            requeue_items = []
            for current_item in current_items:
                if current_item.get('uuid') != item.get('uuid'):
                    requeue_items.append(current_item)
                    continue
                requeue_items.append(item)
            # Add all requeue_items items back into the queue
            self.__requeue_items(requeue_items)

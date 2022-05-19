#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.worker_group.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     18 Apr 2022, (4:08 PM)

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

from unmanic import config
from unmanic.libs.unmodels import Tags
from unmanic.libs.unmodels.workergroups import WorkerGroups
from unmanic.libs.unmodels.workerschedules import WorkerSchedules


def generate_random_worker_group_name():
    names = ['Altoa', 'Anje', 'Anji', 'Azibo', 'Azra', 'Bajin', 'Baliaja', 'Benni', 'Bie', 'Ditid', 'Ecia', 'Ejie', 'Ekon',
             'Equinus', 'Erasto', 'Fefeya', 'Gamjee', 'Gilta', 'Girisha', 'Haijen', 'Hakalai', 'Halasuwa', 'Hamedi', 'Hokajin',
             'Hokima', 'Hyptu', 'Ithra', 'Jaryaya', 'Javinda', 'Javyn', 'Jijel', 'Jinjin', 'Jiranty', 'Jumoke', 'Kaijin',
             'Kanjin', 'Khuwei', 'Kina', 'Lakjin', 'Makas', 'Malak', 'Meimei', 'Melkree', 'Napokue', 'Nelina', 'Nepita',
             'Nuenvan', 'Prerrahar', 'Pujati', 'Rakash', 'Reji', 'Renji', 'Rhazin', 'Ronjaty', 'Rujabu', 'Saonji', 'Shadrala',
             'Shengis', 'Suja', 'Suli', 'Suliya', 'Talisa', 'Tanjin', 'Tayo', 'Tazingo', 'Tedar', 'Teshi', 'Tirezi',
             'Trezzahn', 'Trolgar', 'Ttarmek', 'Ugoki', 'Valja', 'Vekuzz', 'Venjo', 'Venmara', 'Vinji', 'Voyambi', 'Vujii',
             'Vuzashi', 'Wanjin', 'Yaci', 'Yamike', 'Yavo', 'Yera', 'Yeree', 'Yetu', 'Yishi', 'Yuhai', 'Zaejin', 'Zalma',
             'Zea', 'Zelaji', 'Zelea', 'Ziataaman', 'Ziataima', 'Ziatakraa', 'Zola', 'Zoljin', 'Zoti', 'Zujia', 'Zulabar',
             'Zulja', 'Zuljah', 'Zulkis', 'Zulraja', 'Zulrajas', 'Zulwatha', 'Zulyafi', 'Zunabar', 'Zyra', ]
    return random.choice(names)


class WorkerGroup(object):
    """
    WorkerGroup

    Contains all data pertaining to a worker group

    """

    def __init__(self, group_id: int):
        # Ensure worker group ID is not 0
        if group_id < 1:
            raise Exception("Worker group ID cannot be less than 1")
        self.model = WorkerGroups.get_or_none(id=group_id)
        if not self.model:
            raise Exception("Unable to fetch Worker group  with ID {}".format(group_id))

    @staticmethod
    def random_name():
        return generate_random_worker_group_name()

    @staticmethod
    def get_all_worker_groups():
        """
        Return a list of all worker groups

        :return:
        """
        # Fetch all worker groups from DB
        configured_worker_groups = WorkerGroups.select()

        if not configured_worker_groups:
            default_worker_group = {
                'id':                     1,
                'locked':                 False,
                'name':                   generate_random_worker_group_name(),
                'number_of_workers':      0,
                'tags':                   [],
                'worker_event_schedules': [],
            }

            # Migrate default worker data from
            settings = config.Config()
            if settings.number_of_workers is not None:
                default_worker_group['number_of_workers'] = settings.number_of_workers
                if settings.worker_event_schedules is not None:
                    default_worker_group['worker_event_schedules'] = settings.worker_event_schedules

                # Disable the legacy settings
                settings.set_config_item('number_of_workers', None, save_settings=True)
                settings.set_config_item('worker_event_schedules', None, save_settings=True)

                WorkerGroup.create(default_worker_group)
                return [default_worker_group]

        # Loop over results
        worker_groups = []
        for group in configured_worker_groups:
            group_config = {
                'id':                     group.id,
                'locked':                 group.locked,
                'name':                   group.name,
                'number_of_workers':      group.number_of_workers,
                'worker_event_schedules': [],
                'tags':                   [],
            }
            # Append tags
            for tag in group.tags.order_by(Tags.name):
                group_config['tags'].append(tag.name)
            # Append worker_event_schedules
            for event_schedule in group.worker_schedules:
                group_config['worker_event_schedules'].append({
                    'repetition':            event_schedule.repetition,
                    'schedule_task':         event_schedule.schedule_task,
                    'schedule_time':         event_schedule.schedule_time,
                    'schedule_worker_count': event_schedule.schedule_worker_count,
                })

            worker_groups.append(group_config)

        # Return the list of worker groups
        return worker_groups

    @staticmethod
    def create(data: dict):
        """
        Create a new library

        :param data:
        :return:
        """
        # Ensure the name is not blank
        if not data.get('name'):
            data['name'] = generate_random_worker_group_name()

        worker_group_data = {
            'locked':            data.get('locked'),
            'name':              data.get('name'),
            'number_of_workers': data.get('number_of_workers'),
        }
        worker_group_id = WorkerGroups.create(**worker_group_data)

        # Fetch worker group
        worker_group = WorkerGroup(int(worker_group_id.id))

        # Set lists
        worker_group.set_tags(data.get('tags', []))
        worker_group.set_worker_event_schedules(data.get('worker_event_schedules', []))

    @staticmethod
    def create_schedules(worker_group_id: int, worker_event_schedules: list):
        for worker_event_schedule in worker_event_schedules:
            worker_event_schedule_data = {
                'worker_group_id':       worker_group_id,
                'repetition':            worker_event_schedule.get('repetition'),
                'schedule_task':         worker_event_schedule.get('schedule_task'),
                'schedule_time':         worker_event_schedule.get('schedule_time'),
                'schedule_worker_count': worker_event_schedule.get('schedule_worker_count'),
            }
            WorkerSchedules.create(**worker_event_schedule_data)

    def __remove_schedules(self):
        """
        Remove all schedules

        :return:
        """
        query = WorkerSchedules.delete()
        query = query.where(WorkerSchedules.worker_group_id == self.model.id)
        return query.execute()

    def get_id(self):
        return self.model.id

    def get_name(self):
        return self.model.name

    def set_name(self, value):
        self.model.name = value

    def get_locked(self):
        return self.model.locked

    def set_locked(self, value):
        self.model.locked = value

    def get_number_of_workers(self):
        return self.model.number_of_workers

    def set_number_of_workers(self, value):
        self.model.number_of_workers = value

    def get_tags(self):
        return_value = []
        for tag in self.model.tags.order_by(Tags.name):
            return_value.append(tag.name)
        return return_value

    def set_tags(self, value):
        # Create any missing tags
        for tag_name in value:
            # Do not update any current tags with on_conflict_replace() as this will also change their IDs
            # Instead, just ignore them
            Tags.insert(name=tag_name).on_conflict_ignore().execute()
        # Create a SELECT query for all tags with the listed names
        tags_select_query = Tags.select().where(Tags.name.in_(value))
        # Clear out the current linking table of tags linked to this library
        # Add new links for each tag that was fetched matching the provided names
        self.model.tags.add(tags_select_query, clear_existing=True)

    def get_worker_event_schedules(self):
        return_value = []
        for event_schedule in self.model.worker_schedules:
            return_value.append({
                'repetition':            event_schedule.repetition,
                'schedule_task':         event_schedule.schedule_task,
                'schedule_time':         event_schedule.schedule_time,
                'schedule_worker_count': event_schedule.schedule_worker_count,
            })
        return return_value

    def set_worker_event_schedules(self, value):
        # Remove all schedules
        self.__remove_schedules()
        # Save the event schedules
        if value:
            WorkerGroup.create_schedules(self.model.id, value)

    def save(self):
        """
        Save the data for this library

        :return:
        """
        # Ensure a name is actually set
        if not self.get_name():
            self.set_name(generate_random_worker_group_name())

        # Save changes made to model
        self.model.save()

    def delete(self):
        """
        Delete the current library

        :return:
        """
        # Ensure we are not trying to delete a locked library
        if self.get_locked():
            raise Exception("Unable to remove a locked library")

        # Remove all schedules
        self.__remove_schedules()

        # Remove the library entry
        return self.model.delete_instance(recursive=True)

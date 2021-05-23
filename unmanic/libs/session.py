#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    unmanic.session.py

    Written by:               Josh.5 <jsunnex@gmail.com>
    Date:                     10 Mar 2021, (5:20 PM)

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
import time
import requests

from unmanic import config
from unmanic.libs import common, unlogger
from unmanic.libs.singleton import SingletonType
from unmanic.libs.unmodels import db, Installation


class Session(object, metaclass=SingletonType):
    """
    Session

    Manages the Unbmanic applications session for unlocking
    features and fetching data from the Unmanic site API.

    """

    """
    level - The user auth level
    Set level to 0 by default
    """
    level = 0

    """
    picture_uri - The user avatar
    """
    picture_uri = ''

    """
    name - The user's name
    """
    name = ''

    """
    email - The user's email
    """
    email = ''

    """
    created - The timestamp when the session was last checked
    """
    created = None

    """
    uuid - This installation's UUID
    """
    uuid = None

    def __init__(self, *args, **kwargs):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def __check_session_valid(self):
        """
        Ensure that the session is valid.
        A session is only valid for a limited amount of time.
        After a session expires, it should be re-acquired.

        :return:
        """
        if not self.created:
            return False
        # Get session expiration time
        time_now = time.time()
        time_when_session_expires = self.created + 18000
        # Check that the time create is less than 5 hours old
        if time_now < time_when_session_expires:
            self._log("Session valid ", level="debug")
            return True
        self._log("Session no longer valid ", level="debug")
        return False

    def __update_created_timestamp(self):
        """
        Update the session "created" timestamp.

        :return:
        """
        self.created = time.time()
        from datetime import datetime
        created = datetime.fromtimestamp(self.created)
        self._log("Updated session at ", created, level="debug")

    def get_installation_uuid(self):
        """
        Returns the installation UUID as a string.
        If it does not yet exist, it will create one.

        :return:
        """
        if not self.uuid:
            # Fetch installation
            db_installation = Installation()
            try:
                # Fetch a single row (get() will raise DoesNotExist exception if no results are found)
                current_installation = db_installation.select().order_by(Installation.id.asc()).limit(1).get()
            except Exception as e:
                # Create settings (defaults will be applied)
                self._log("Unmanic session does not yet exist... Creating.", level="debug")
                db_installation.delete().execute()
                current_installation = db_installation.create()

            self.uuid = str(current_installation.uuid)
        return self.uuid

    def get_site_url(self):
        """
        Set the Unmanic application site URL
        :return:
        """
        api_proto = "https"
        api_domain = "unmanic.app"
        return "{0}://{1}".format(api_proto, api_domain)

    def set_full_api_url(self, api_version, api_path):
        """
        Set the API path URL

        :param api_version:
        :param api_path:
        :return:
        """
        api_versioned_path = "api/v{}".format(api_version)
        return "{0}/{1}/{2}".format(self.get_site_url(), api_versioned_path, api_path)

    def api_get(self, api_version, api_path):
        """
        Generate and execute a GET API call.

        :param api_version:
        :param api_path:
        :return:
        """
        u = self.set_full_api_url(api_version, api_path)
        r = requests.get(u)
        return r.json()

    def api_post(self, api_version, api_path, data):
        """
        Generate and execute a POST API call.

        :param api_version:
        :param api_path:
        :param data:
        :return:
        """
        u = self.set_full_api_url(api_version, api_path)
        r = requests.post(u, json=data)
        return r.json()

    def register_unmanic(self, uuid, force=False):
        """
        Register Unmanic with site.
        This sends information about the system that Unmanic is running on.
        It also sends a unique ID.

        Based on the return information, this will set the session level

        Return success status

        :return:
        """
        # First check if the current session is still valid
        if not force and self.__check_session_valid():
            return True

        settings = config.CONFIG()
        try:
            # Build post data
            from unmanic.libs.system import System
            system = System()
            system_info = system.info()
            platform_info = system_info.get("platform", None)
            if platform_info:
                platform_info = " * ".join(platform_info)
            post_data = {
                "uuid":           uuid,
                "version":        settings.read_version(),
                "python_version": system_info.get("python", ''),
                "system":         {
                    "platform": platform_info,
                    "devices":  system_info.get("devices", {}),
                }
            }

            # Register Unmanic
            registration_response = self.api_post(1, 'unmanic-register', post_data)

            # Save data
            if registration_response and registration_response.get("success"):
                registration_data = registration_response.get("data")

                # Set level from response data (default back to 0)
                self.level = registration_data.get("level", 0)

                # Get user data from response data
                user_data = registration_data.get('user')
                if user_data:
                    # Set name from user data
                    name = user_data.get("name")
                    self.name = name if name else 'Valued Supporter'

                    # Set avatar from user data
                    picture_uri = user_data.get("picture_uri")
                    self.picture_uri = picture_uri if picture_uri else '/assets/global/img/avatar/avatar_placeholder.png'

                    # Set email from user data
                    email = user_data.get("email")
                    self.email = email if email else ''

                self.__update_created_timestamp()

                return True
            return False
        except Exception as e:
            self._log("Exception while registering Unmanic.", str(e), level="debug")
            return False

    def get_sign_out_url(self):
        """
        Fetch the application sign out client ID

        :return:
        """
        return "{0}/unmanic-logout".format(self.get_site_url())

    def get_patreon_login_url(self):
        """
        Fetch the Patreon client ID

        :return:
        """
        return "{0}/patreon-login".format(self.get_site_url())

    def get_patreon_sponsor_page(self):
        """
        Fetch the Patreon sponsor page

        :return:
        """
        try:
            # Fetch Patreon client ID from Unmanic site API
            response = self.api_get(1, 'unmanic-patreon-sponsor-page')

            if response and response.get("success"):
                response_data = response.get("data")
                return response_data

        except Exception as e:
            self._log("Exception while fetching Patreon sponsor page.", str(e), level="debug")
        return False

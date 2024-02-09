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
import base64
import pickle
import random
import time
import requests

from unmanic import config
from unmanic.libs import common, unlogger
from unmanic.libs.singleton import SingletonType
from unmanic.libs.unmodels import Installation


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
    non supporter library count
    """
    library_count = 2

    """
    non supporter linked installations count
    """
    link_count = 5

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
    created - The timestamp when the session was created
    """
    created = None

    """
    last_check - The timestamp when the session was last checked
    """
    last_check = None

    """
    uuid - This installation's UUID
    """
    uuid = None

    """
    user_access_token - The access token to authenticate requests with the Unmanic API
    """
    user_access_token = None

    """
    session_cookies - A stored copy of the session cookies to persist between restarts
    """
    session_cookies = None

    def __init__(self, *args, **kwargs):
        unmanic_logging = unlogger.UnmanicLogger.__call__()
        self.logger = unmanic_logging.get_logger(__class__.__name__)
        self.timeout = 30
        self.dev_local_api = kwargs.get('dev_local_api', False)
        self.requests_session = requests.Session()

    def _log(self, message, message2='', level="info"):
        message = common.format_message(message, message2)
        getattr(self.logger, level)(message)

    def __created_older_than_x_days(self, days=1):
        # (86400 = 24 hours)
        seconds = (days * 86400)
        # Get session expiration time
        time_now = time.time()
        time_when_session_expires = self.created + seconds
        # Check that the time create is less than 24 hours old
        if time_now < time_when_session_expires:
            return False
        return True

    def __check_session_valid(self):
        """
        Ensure that the session is valid.
        A session is only valid for a limited amount of time.
        After a session expires, it should be re-acquired.

        :return:
        """
        # Last checked less than a min ago... just keep the current session.
        # This check is only to prevent spamming requests when the site API is unreachable
        # Only check in every 40 mins (2400s) minimum. Never ignore a checkin for more than 45 mins (2700s)
        ### if self.last_check and 2700 > (time.time() - self.last_check) < 2400:
        if self.last_check and 45 > (time.time() - self.last_check) < 40:
            return True
        # If the session has never been created, return false
        if not self.created:
            return False
        # Check if the time the session was created is less than 1 day old
        if not self.__created_older_than_x_days(days=2):
            # Only try to recreate the session once a day
            return True
        self._log("Session no longer valid ", level="debug")
        return False

    def __update_created_timestamp(self):
        """
        Update the session "created" timestamp.

        :return:
        """
        # Get the time now in seconds
        seconds = time.time()
        # Create a seconds offset of some random number between 300 (5 mins) and 900 (15 mins)
        seconds_offset = random.randint(300, 900 - 1)
        # Set the created flag with the seconds variable plus a random offset to avoid people joining
        #   together to register if the site goes down
        self.created = (seconds + seconds_offset)
        # Print only the accurate update time in debug log
        from datetime import datetime
        created = datetime.fromtimestamp(seconds)
        self._log("Updated session at ", str(created), level="debug")

    def __fetch_installation_data(self):
        """
        Fetch installation data from DB

        :return:
        """
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
        self.level = int(current_installation.level)
        self.picture_uri = str(current_installation.picture_uri)
        self.name = str(current_installation.name)
        self.email = str(current_installation.email)
        self.created = current_installation.created

        self.__update_session_auth(access_token=current_installation.user_access_token,
                                   session_cookies=current_installation.session_cookies)

    def __store_installation_data(self):
        """
        Store installation data in DB to persist reboot

        :return:
        """
        if self.uuid:
            db_installation = Installation.get_or_none(uuid=self.uuid)
            db_installation.level = self.level
            db_installation.picture_uri = self.picture_uri
            db_installation.name = self.name
            db_installation.email = self.email
            db_installation.created = self.created
            db_installation.user_access_token = self.user_access_token
            db_installation.session_cookies = self.session_cookies
            db_installation.save()

    def __reset_session_installation_data(self):
        """
        Reset stored session data

        :return:
        """
        self.level = 0
        self.picture_uri = ''
        self.name = ''
        self.email = ''
        self.created = time.time()
        self.user_access_token = None
        self.__store_installation_data()

    def __update_session_auth(self, access_token=None, session_cookies=None):
        # Update session headers
        if access_token:
            self.user_access_token = access_token
            self.requests_session.headers.update({'Authorization': self.user_access_token})
        # Update session cookies
        if session_cookies:
            self.session_cookies = session_cookies
            try:
                self.requests_session.cookies = pickle.loads(base64.b64decode(session_cookies))
            except Exception as e:
                self._log("Error trying to reload session cookies", level="error")
                self._log(str(e), level="error")

    def get_installation_uuid(self):
        """
        Returns the installation UUID as a string.
        If it does not yet exist, it will create one.

        :return:
        """
        if not self.uuid:
            self.__fetch_installation_data()
        return self.uuid

    def get_site_url(self):
        """
        Set the Unmanic application site URL
        :return:
        """
        api_proto = "https"
        api_domain = "api.unmanic.app"
        if self.dev_local_api:
            api_proto = "http"
            api_domain = "api.unmanic.localhost"
        return "{0}://{1}".format(api_proto, api_domain)

    def set_full_api_url(self, api_prefix, api_version, api_path):
        """
        Set the API path URL

        :param api_prefix:
        :param api_version:
        :param api_path:
        :return:
        """
        api_versioned_path = "{}/v{}".format(api_prefix, api_version)
        return "{0}/{1}/{2}".format(self.get_site_url(), api_versioned_path, api_path)

    def api_get(self, api_prefix, api_version, api_path):
        """
        Generate and execute a GET API call.

        :param api_prefix:
        :param api_version:
        :param api_path:
        :return:
        """
        u = self.set_full_api_url(api_prefix, api_version, api_path)
        r = self.requests_session.get(u, timeout=self.timeout)
        return r.json()

    def api_post(self, api_prefix, api_version, api_path, data):
        """
        Generate and execute a POST API call.

        :param api_prefix:
        :param api_version:
        :param api_path:
        :param data:
        :return:
        """
        u = self.set_full_api_url(api_prefix, api_version, api_path)
        r = self.requests_session.post(u, json=data, timeout=self.timeout)
        return r.json()

    def verify_token(self):
        if not self.user_access_token:
            # No valid tokens exist
            return False
        # Check if access token is valid
        response = self.api_get('support-auth-api', 1, 'user_auth/verify_token')
        if not response.get('success'):
            response = self.api_get('support-auth-api', 1, 'user_auth/refresh_token')
            if not response.get('success'):
                # Just blank the class attribute.
                # It is fine for requests to be sent with further requests.
                # User will appear to be logged out.
                self.user_access_token = None
                return False
        # Check if we received a new access token
        access_token = response.get('data', {}).get('accessToken')
        if access_token:
            self.__update_session_auth(access_token=access_token)
        self.session_cookies = base64.b64encode(pickle.dumps(self.requests_session.cookies)).decode('utf-8')
        self.__update_session_auth()
        return True

    def auth_user_account(self, force_checkin=False):
        # Don't bother if the user has never logged in
        if not self.user_access_token and not force_checkin:
            self._log("The user access token is not set add we are not being forced to refresh for one.", level="debug")
            return
        # Start by verifying the token
        token_verified = self.verify_token()
        if not token_verified:
            # Try to fetch token if this was the initial login
            post_data = {"uuid": self.get_installation_uuid()}
            response = self.api_post('support-auth-api', 1, 'app_auth/retrieve_app_token', post_data)
            if response.get('success'):
                access_token = response.get('data', {}).get('accessToken')
                self.__update_session_auth(access_token=access_token)
                token_verified = self.verify_token()
        # Set default level to 0
        updated_level = 0
        # Finally, fetch user info if the token was successfully verified
        if token_verified:
            response = self.api_get('support-auth-api', 1, 'user_auth/user_info')
            if response.get('success'):
                # Get user data from response data
                user_data = response.get('data', {}).get('user')
                if user_data:
                    # Set name from user data
                    self.name = user_data.get("name", "Valued Supporter")

                    # Set avatar from user data
                    self.picture_uri = user_data.get("picture_uri", "/assets/global/img/avatar/avatar_placeholder.png")

                    # Set email from user data
                    self.email = user_data.get("email", "")

                    # Update level from response data (default back to 0)
                    updated_level = int(user_data.get("supporter_level", 0))
        self.level = updated_level

    def register_unmanic(self, force=False):
        """
        Register Unmanic with site.
        This sends information about the system that Unmanic is running on.
        It also sends a unique ID.

        Based on the return information, this will set the session level.

        Return success status.

        :param force:
        :return:
        """
        # First check if the current session is still valid
        if not force and self.__check_session_valid():
            return True

        # Set now as the last time this was run (before it was actually run
        self.last_check = time.time()

        # Update the session
        settings = config.Config()
        try:
            # Fetch the installation data prior to running a session update
            self.__fetch_installation_data()

            # Build post data
            from unmanic.libs.system import System
            system = System()
            system_info = system.info()
            platform_info = system_info.get("platform", None)
            if platform_info:
                platform_info = " * ".join(platform_info)
            post_data = {
                "uuid":           self.get_installation_uuid(),
                "version":        settings.read_version(),
                "python_version": system_info.get("python", ''),
                "system":         {
                    "platform": platform_info,
                    "devices":  system_info.get("devices", {}),
                }
            }

            # Refresh user auth
            self.auth_user_account(force_checkin=force)

            # Register Unmanic
            registration_response = self.api_post('unmanic-api', 1, 'installation_auth/register', post_data)

            # Save data
            if registration_response and registration_response.get("success"):
                self.__update_created_timestamp()
                # Persist session in DB
                self.__store_installation_data()
                return True

            # Allow an extension for the session for 7 days without an internet connection
            if self.__created_older_than_x_days(days=7):
                # Reset the session - Unmanic should phone home once every 7 days
                self.__reset_session_installation_data()
            return False
        except Exception as e:
            self._log("Exception while registering Unmanic.", str(e), level="debug")
            if self.__check_session_valid():
                # If the session is still valid, just return true. Perhaps the internet is down and it timed out?
                return True
            return False

    def sign_out(self):
        """
        Remove any user auth

        :return:
        """
        post_data = {
            "uuid": self.get_installation_uuid(),
        }
        registration_response = self.api_post('unmanic-api', 1,
                                              'installation_auth/remove-installation-registration',
                                              post_data)
        # Save data
        if registration_response and registration_response.get("success"):
            self.__reset_session_installation_data()
            return True
        return False

    def get_sign_out_url(self):
        """
        Fetch the application sign out client ID

        :return:
        """
        return "{0}/unmanic-api/v1/installation_auth/logout".format(self.get_site_url())

    def get_patreon_login_url(self):
        """
        Fetch the Patreon client ID

        :return:
        """
        return "{0}/patreon-login".format(self.get_site_url())

    def get_github_login_url(self):
        """
        Fetch the GitHub client ID

        :return:
        """
        return "{0}/github-login".format(self.get_site_url())

    def get_discord_login_url(self):
        """
        Fetch the Discord client ID

        :return:
        """
        return "{0}/support-auth-api/v1/login_discord/login".format(self.get_site_url())

    def get_patreon_sponsor_page(self):
        """
        Fetch the Patreon sponsor page

        :return:
        """
        try:
            # Fetch Patreon client ID from Unmanic site API
            response = self.api_get('unmanic-api', 1, 'links/unmanic-patreon-sponsor-page')

            if response and response.get("success"):
                response_data = response.get("data")
                return response_data

        except Exception as e:
            self._log("Exception while fetching Patreon sponsor page.", str(e), level="debug")
        return False

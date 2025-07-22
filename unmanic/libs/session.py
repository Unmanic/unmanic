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
import datetime
import os
import pickle
import random
import time

import requests

from unmanic import config
from unmanic.libs.logs import UnmanicLogging
from unmanic.libs.singleton import SingletonType
from unmanic.libs.unmodels import Installation


class RemoteApiException(Exception):
    """
    RemoteApiException
    Custom exception for errors contacting the remote Unmanic API
    """

    def __init__(self, message, status_code):
        super().__init__(f"Session Error - Remote API [CODE: {status_code}]: {message}")


class Session(object, metaclass=SingletonType):
    """
    Session

    Manages the Unmanic applications session for unlocking
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
    link_count = 3

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
    application_token - The application token for acquiring an updated access token
    """
    application_token = None

    def __init__(self, *args, **kwargs):
        self.logger = UnmanicLogging.get_logger(name=__class__.__name__)
        self.timeout = 30
        self.dev_api = kwargs.get('dev_api', None)
        self.requests_session = requests.Session()
        self.token_poll_task = None
        self.logger.info('Initialising new session object')
        self.created = None
        self.last_check = None

    def __created_older_than_x_days(self, days=1):
        if not self.created:
            # There is no session created. How did we get here???
            return False
        # (86400 = 24 hours)
        seconds = (days * 86400)
        # Get session expiration time
        time_now = time.time()
        time_when_session_expires = self.created + seconds
        # Check that the time create is less than X days old
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
        if self.last_check and 2700 > (time.time() - self.last_check) < 2400:
            return True
        # If the session has never been created, return false
        if not self.created:
            return False
        # Check if the time the session was created is less than X days old
        if not self.__created_older_than_x_days(days=2):
            # Only try to recreate the session once a day
            return True
        self.logger.debug('Session no longer valid')
        return False

    def __update_created_timestamp(self):
        """
        Update the session "created" timestamp.

        :return:
        """
        # Get the time now in seconds
        seconds = time.time()
        # Create a seconds offset of some random number between 300 (5 mins) and 900 (15 mins)
        seconds_offset = random.randint(300, 900)
        # Set the created flag with the seconds variable plus a random offset to avoid people joining
        #   together to register if the site goes down
        self.created = (seconds + seconds_offset)
        # Print only the accurate update time in debug log
        created = datetime.datetime.fromtimestamp(seconds)
        self.logger.debug('Updated session at %s', str(created))

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
            self.logger.debug('Unmanic session does not yet exist... Creating.')
            db_installation.delete().execute()
            current_installation = db_installation.create()

        self.uuid = str(current_installation.uuid)
        self.level = int(current_installation.level)
        self.picture_uri = str(current_installation.picture_uri)
        self.name = str(current_installation.name)  # This is the user's name. Not the installation's name
        self.email = str(current_installation.email)
        self.created = current_installation.created if current_installation.created else None
        if isinstance(self.created, datetime.datetime):
            self.created = self.created.timestamp()

        self.application_token = str(current_installation.application_token)
        self.__update_session_auth(access_token=current_installation.user_access_token)

    def __store_installation_data(self, force_save_access_token=False):
        """
        Store installation data in DB to persist reboot

        :return:
        """
        if self.uuid:
            db_installation = Installation.get_or_none(uuid=self.uuid)
            db_installation.level = self.level
            db_installation.picture_uri = self.picture_uri
            db_installation.name = self.name  # This is the user's name. Not the installation's name
            db_installation.email = self.email
            db_installation.created = self.created
            if self.user_access_token or force_save_access_token:
                db_installation.user_access_token = self.user_access_token
            if self.application_token or force_save_access_token:
                db_installation.application_token = self.application_token
            db_installation.save()

    def __configure_log_forwarding(self, session_valid=False):
        if session_valid:
            # Import endpoint from env vars
            endpoint = os.environ.get('UNMANIC_REMOTE_LOGGING_ENDPOINT', '')
            # If not set in env vars, fetch endpoint from unmanic-api
            if not endpoint or not endpoint.startswith("http"):
                endpoint = None
                try:
                    # Fetch endpoint from Unmanic site API
                    response, status_code = self.api_get('unmanic-api', 1, 'central_config/get_datastore_endpoint')
                    if status_code in [200] and response.get("success"):
                        endpoint = response.get("data").get("endpoint")
                except Exception as e:
                    self.logger.debug('Exception while fetching Unmanic Central Datastore endpoint - %s', e)
            if endpoint:
                UnmanicLogging.enable_remote_logging(endpoint, self.uuid)
                return
        UnmanicLogging.disable_remote_logging()

    def __reset_session_installation_data(self):
        """
        Reset stored session data

        :return:
        """
        self.logger.debug('Resetting session installation data.')
        self.level = 0
        self.picture_uri = ''
        self.name = ''
        self.email = ''
        self.created = time.time()
        self.user_access_token = None
        self.application_token = None
        self.__store_installation_data(force_save_access_token=True)
        self.__configure_log_forwarding(session_valid=False)
        self.__clear_session_auth()

    def __update_session_auth(self, access_token=None):
        # Update session headers
        if access_token:
            self.user_access_token = access_token
            self.requests_session.headers.update({'Authorization': self.user_access_token})

    def __clear_session_auth(self):
        self.requests_session.cookies.clear()
        self.requests_session.headers.update({'Authorization': ''})

    def get_installation_uuid(self):
        """
        Returns the installation UUID as a string.
        If it does not yet exist, it will create one.

        :return:
        """
        if not self.uuid:
            self.__fetch_installation_data()
        return self.uuid

    def get_supporter_level(self):
        """
        Returns the supporter level

        :return:
        """
        if not self.level:
            self.__fetch_installation_data()
        return self.level

    def get_site_url(self):
        """
        Set the Unmanic application site URL
        :return:
        """
        api_proto = "https"
        api_domain = "api.unmanic.app"
        if self.dev_api:
            return self.dev_api
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
        if r.status_code > 403:
            # There is an issue with the remote API
            raise RemoteApiException(f"GET request failed for {u}", r.status_code)
        if r.status_code == 401:
            # Verify the token. Refresh as required
            self.logger.debug("Auto exec token verification (api_get)")
            token_verified = self.verify_token()
            # If successful, then retry request
            if token_verified:
                r = self.requests_session.get(u, timeout=self.timeout)
                if r.status_code > 403:
                    # There is an issue with the remote API
                    raise RemoteApiException(f"GET request still failed for {u}", r.status_code)
            else:
                self.logger.debug('Failed to verify auth (api_get)')
        return r.json(), r.status_code

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
        if r.status_code > 403:
            # There is an issue with the remote API
            raise RemoteApiException(f"POST request failed for {u}", r.status_code)
        if r.status_code == 401:
            # Verify the token. Refresh as required
            self.logger.debug("Auto exec token verification (api_post)")
            token_verified = self.verify_token()
            # If successful, then retry request
            if token_verified:
                r = self.requests_session.post(u, json=data, timeout=self.timeout)
                if r.status_code > 403:
                    # There is an issue with the remote API
                    raise RemoteApiException(f"POST request still failed for {u}", r.status_code)
            else:
                self.logger.debug('Failed to verify auth (api_post)')
        return r.json(), r.status_code

    def get_access_token(self):
        if not self.application_token:
            # No application token set
            return False
        d = {"applicationToken": self.application_token, "uuid": self.get_installation_uuid()}
        u = self.set_full_api_url('support-auth-api', 2, 'app_auth/get_token')
        r = self.requests_session.post(u, json=d, timeout=self.timeout)
        if r.status_code in [200, 201, 202]:
            # Token refreshed
            # Store the updated access token
            response = r.json()
            self.__update_session_auth(access_token=response.get('data', {}).get('accessToken'))
            self.__store_installation_data()
            self.__configure_log_forwarding(session_valid=True)
            return True
        elif r.status_code > 403:
            # Issue was with server... Just carry on with current access token can't fix that here.
            raise RemoteApiException(f"Token refresh request failed for {u}", r.status_code)
        elif r.status_code in [403]:
            # Log this failure in the debug logs
            self.logger.info('Failed to get access token.')
            response = r.json()
            for message in response.get('messages', []):
                self.logger.info('Remote Message: %s', message)
        return False

    def verify_token(self):
        if not self.user_access_token:
            if self.get_access_token():
                # Successfully refreshed access token
                return True
            # No valid tokens exist
            return False
        # Check if access token is valid
        u = self.set_full_api_url('support-auth-api', 1, 'user_auth/verify_token')
        r = self.requests_session.get(u, timeout=self.timeout)
        if r.status_code in [200, 201, 202]:
            # Token is valid
            return True
        elif r.status_code > 403:
            # Issue with server... Just carry on with current access token can't fix that here.
            raise RemoteApiException(f"Token verification request failed for {u}", r.status_code)

        # Access token is not valid. Refresh it.
        self.logger.debug('Unable to verify access token. Refreshing...')
        if self.get_access_token():
            # Successfully refreshed access token
            return True
        return False

    def fetch_user_data(self):
        response, status_code = self.api_get('support-auth-api', 2, 'user_info/get')
        if status_code == 401:
            # API return a 401. Set back to default level 0
            self.level = 0
            return
        if status_code > 403:
            # Failed to fetch data from server. Ignore this for now. Will try again later.
            raise RemoteApiException("Failed to fetch user info from user_info/get", status_code)
        if status_code in [200, 201, 202] and response.get('success'):
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
                self.level = int(user_data.get("supporter_level", 0))

    def auth_user_account(self, force_checkin=False):
        # Don't bother if the user has never logged in
        if not self.user_access_token and not force_checkin:
            self.logger.debug('The user access token is not set add we are not being forced to refresh for one.')
            return False

        # Start by verifying the token
        token_verified = self.verify_token()

        # If that token verification failed but we are not being forced to check in, then just ignore it.
        if not token_verified and not force_checkin:
            self.logger.debug('The user access token is not valid but we are not being forced to refresh for one.')
            return False

        # If the token was verified and is valid, fetch user info
        if token_verified:
            self.fetch_user_data()
            return True

        # Finally, if no valid session and no user account (and at this point force_checkin was True), run the sign-out process
        self.sign_out(remote=False)
        return False

    def auth_trial_account(self):
        # Check if access token is valid
        d = {"uuid": self.get_installation_uuid()}
        u = self.set_full_api_url('support-auth-api', 1, 'user_auth/trial_token')
        r = self.requests_session.post(u, json=d, timeout=self.timeout)
        if r.status_code in [200, 201, 202]:
            # Token refreshed
            # Store the updated access token
            response = r.json()
            self.logger.debug("Updating session with trial token")
            self.__update_session_auth(access_token=response.get('data', {}).get('accessToken'))
            # Fetch user data
            self.fetch_user_data()
            # Store the updated session cookies
            self.__store_installation_data()
            self.__configure_log_forwarding(session_valid=True)  # TODO: Remove from here. It wont work with trials.
            return True
        elif r.status_code > 403:
            # Issue with server... Just carry on with current access token can't fix that here.
            raise RemoteApiException(f"Trial token verification request failed for {u}", r.status_code)

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
        # Fetch the installation data prior to running a session update
        self.__fetch_installation_data()

        try:
            # Build post data
            from unmanic.libs.system import System
            system = System()
            system_info = system.info()
            platform_info = system_info.get("platform", None)
            if platform_info:
                platform_info = " * ".join(platform_info)
            post_data = {
                "uuid":              self.get_installation_uuid(),
                "installation_name": settings.get_installation_name(),
                "version":           settings.read_version(),
                "python_version":    system_info.get("python", ''),
                "system":            {
                    "platform": platform_info,
                    "devices":  system_info.get("devices", {}),
                }
            }

            # Refresh user auth
            result = self.auth_user_account(force_checkin=force)
            if not result and force:
                # Fetch trial token
                result = self.auth_trial_account()

            # Register Unmanic
            registration_response, status_code = self.api_post('unmanic-api', 1, 'installation_auth/register', post_data)

            # Save data
            if status_code in [200, 201, 202] and registration_response.get("success"):
                self.__update_created_timestamp()
                # Persist session in DB
                self.__store_installation_data()
                self.__configure_log_forwarding(session_valid=True)
                return True
            elif status_code > 403:
                raise RemoteApiException("Failed to register installation to installation_auth/register", status_code)

            # Allow an extension for the session for 7 days without an internet connection
            # We will get here if we received a 403 from the unmanic-api. We should just ignore that for a few days
            if self.__created_older_than_x_days(days=7):
                # Reset the session - Unmanic should phone home once every 7 days
                self.__reset_session_installation_data()
            else:
                self.logger.debug("Allowing session extension")
            return False
        except RemoteApiException as e:
            self.logger.error("Exception while registering Unmanic with remote API: %s", e)
            if self.level < 2:
                # Upgrade supporter level here to avoid stopping anything
                # (this function will return false below to indicate a failure in updating the session)
                self.level = 100
                self.logger.debug("Setting trial application level while remote servers are down", self.level)
        except Exception as e:
            self.logger.debug("Exception while registering Unmanic: %s", e, exc_info=True)
            if self.__check_session_valid():
                # If the session is still valid, just return true. Perhaps the internet is down and it timed out?
                return True
            return False
        return False

    def sign_out(self, remote=True):
        """
        Remove any user auth

        :return:
        """
        try:
            if remote:
                post_data = {
                    "uuid": self.get_installation_uuid(),
                }
                response, status_code = self.api_post('unmanic-api', 1,
                                                      'installation_auth/remove_installation_registration',
                                                      post_data)
                # The only way we can now log out is if the auth server response with true
                # Save data
                self.logger.debug("Remote registry logout response - Code: %s, Body: %s", status_code, response)
        except RemoteApiException as e:
            self.logger.warning(
                "Failed to reach remote server to request a logout. This is fine, we can continue to logout the app locally.")
        self.__reset_session_installation_data()
        return True

    def get_sign_out_url(self):
        """
        Fetch the application sign out URL

        :return:
        """
        return "{0}/unmanic-api/v1/installation_auth/logout".format(self.get_site_url())

    def init_device_auth_flow(self):
        """
        Starts the device authentication flow to obtain an application token.
        It sends a POST request for a device code and then polls until the app token is available.

        It then logs the verification URL and user code for the user to enter, and finally
        calls poll_for_app_token() to retrieve the app token.
        """
        # Try to fetch token if this was the initial login
        post_data = {"uuid": self.get_installation_uuid()}
        response, status_code = self.api_post('support-auth-api', 2, 'app_auth/request_pin', post_data)
        if status_code >= 400:
            self.logger.error(
                "The remote service returned an error (HTTP %s). We are unable to proceed at this time. Please try again later.",
                status_code)
            return False

        if status_code != 200:
            raise Exception(f"Unexpected response status: {status_code}")

        if not response.get("success"):
            raise Exception("Device auth request was unsuccessful: " + str(response.get("messages")))

        data = response.get("data", {})
        user_code = data.get("user_code")
        device_code = data.get("device_code")
        verification_uri = data.get("verification_uri")
        verification_uri_complete = data.get("verification_uri_complete")
        interval = data.get("interval")
        expires_in = data.get("expires_in")

        self.logger.info("Visit %s and enter the code: %s", verification_uri, user_code)

        # Begin polling for the application token using the device code, interval, and expiry
        return {
            "user_code":                 user_code,
            "device_code":               device_code,
            "interval":                  interval,
            "expires_in":                expires_in,
            "verification_uri":          verification_uri,
            "verification_uri_complete": verification_uri_complete
        }

    def poll_for_app_token(self, device_code, interval, expires_in):
        """
        Polls the remote API for the application token.
        This function is intended to run in a background thread.
        It runs for a maximum of "expires_in" seconds.
        """
        start_time = time.time()
        self.logger.info("Polling for app token")
        while time.time() - start_time < expires_in:
            time.sleep(interval)

            # Try to fetch token if this was the initial login
            post_data = {
                "uuid":        self.get_installation_uuid(),
                "device_code": device_code,
            }
            response, status_code = self.api_post('support-auth-api', 2, 'app_auth/retrieve_app_token', post_data)
            if status_code > 403:
                # Issue with server... Just carry on with current access token can't fix that here.
                raise RemoteApiException("App token retrieval request failed for %s", status_code)
            elif status_code in [200] and response.get('data', {}).get('applicationToken'):
                time.sleep(interval)  # Wait for {interval} before we use this new app token
                # Store the updated access token
                self.logger.info("Application linked to account")
                # Store the updated refresh token
                self.application_token = response.get('data', {}).get('applicationToken')
                self.get_access_token()
                token_verified = self.verify_token()
                self.logger.info("Application auth token verified: %s", token_verified)
                self.register_unmanic(force=True)
                return token_verified

        self.logger.info("Polling for app token timed out after %s seconds.", expires_in)
        return None

    def get_patreon_login_url(self):
        """
        Fetch the Patreon Login URL

        :return:
        """
        return "{0}/support-auth-api/v1/login_patreon/login".format(self.get_site_url())

    def get_github_login_url(self):
        """
        Fetch the GitHub Login URL

        :return:
        """
        return "{0}/support-auth-api/v1/login_github/login".format(self.get_site_url())

    def get_discord_login_url(self):
        """
        Fetch the Discord Login URL

        :return:
        """
        return "{0}/support-auth-api/v1/login_discord/login".format(self.get_site_url())

    def get_patreon_sponsor_page(self):
        """
        Fetch the Patreon sponsor page

        :return:
        """
        try:
            # Fetch Patreon sponsorship URL from Unmanic site API
            response, status_code = self.api_get('unmanic-api', 1, 'links/unmanic_patreon_sponsor_page')
            if status_code in [200, 201, 202] and response.get("success"):
                response_data = response.get("data")
                return response_data
        except Exception as e:
            self.logger.debug('Exception while fetching Patreon sponsor page - %s', e)
        return False

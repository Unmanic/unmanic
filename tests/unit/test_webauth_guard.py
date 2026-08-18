#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import pytest

from unmanic.libs.webauth import guard


@pytest.mark.unittest
class TestOriginCheck(object):
    def test_absent_origin_is_allowed_so_machine_clients_work(self):
        assert guard.origin_is_allowed(None, "10.0.0.1:8888", []) is True
        assert guard.origin_is_allowed("", "10.0.0.1:8888", []) is True

    def test_matching_origin_is_allowed(self):
        assert guard.origin_is_allowed("http://10.0.0.1:8888", "10.0.0.1:8888", []) is True
        assert guard.origin_is_allowed("https://10.0.0.1:8888", "10.0.0.1:8888", []) is True

    def test_mismatched_origin_is_rejected(self):
        assert guard.origin_is_allowed("http://evil.example.com", "10.0.0.1:8888", []) is False

    def test_a_different_port_is_a_different_origin(self):
        assert guard.origin_is_allowed("http://10.0.0.1:9999", "10.0.0.1:8888", []) is False

    def test_a_prefix_of_the_host_is_not_a_match(self):
        assert guard.origin_is_allowed("http://10.0.0.1:8888.evil.com", "10.0.0.1:8888", []) is False

    def test_trusted_origins_are_allowed(self):
        trusted = ["https://unmanic.example.com"]
        assert guard.origin_is_allowed("https://unmanic.example.com", "10.0.0.1:8888", trusted) is True
        assert guard.origin_is_allowed("https://other.example.com", "10.0.0.1:8888", trusted) is False

    def test_null_origin_is_rejected(self):
        assert guard.origin_is_allowed("null", "10.0.0.1:8888", []) is False


@pytest.mark.unittest
class TestSafeNextPath(object):
    def test_local_paths_are_preserved(self):
        assert guard.safe_next_path("/unmanic/ui/settings/") == "/unmanic/ui/settings/"

    def test_absolute_urls_are_rejected(self):
        assert guard.safe_next_path("https://evil.example.com") == guard.DEFAULT_LANDING_PATH
        assert guard.safe_next_path("http://evil.example.com") == guard.DEFAULT_LANDING_PATH

    def test_protocol_relative_urls_are_rejected(self):
        assert guard.safe_next_path("//evil.example.com") == guard.DEFAULT_LANDING_PATH
        assert guard.safe_next_path("/\\evil.example.com") == guard.DEFAULT_LANDING_PATH
        assert guard.safe_next_path("/\tevil") == guard.DEFAULT_LANDING_PATH

    def test_empty_and_relative_values_fall_back(self):
        assert guard.safe_next_path("") == guard.DEFAULT_LANDING_PATH
        assert guard.safe_next_path(None) == guard.DEFAULT_LANDING_PATH
        assert guard.safe_next_path("settings") == guard.DEFAULT_LANDING_PATH


class FakeRequest(object):
    def __init__(self, path="/unmanic/ui/dashboard/", method="GET", headers=None, cookies=None):
        self.path = path
        self.method = method
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.remote_ip = "10.0.0.9"
        self.host = "10.0.0.1:8888"


@pytest.mark.unittest
class TestSecFetchSite(object):
    def test_cross_site_is_blocked_on_guarded_prefixes(self):
        for prefix in guard.CSRF_GUARDED_PREFIXES:
            request = FakeRequest(path=prefix + "something", headers={"Sec-Fetch-Site": "cross-site"})
            assert guard.sec_fetch_is_allowed(request) is False

    def test_cross_site_is_permitted_on_ui_routes(self):
        request = FakeRequest(path="/unmanic/ui/trigger/", headers={"Sec-Fetch-Site": "cross-site"})
        assert guard.sec_fetch_is_allowed(request) is True

    def test_absent_header_is_allowed_because_websockets_omit_it(self):
        request = FakeRequest(path="/unmanic/api/v2/version/read")
        assert guard.sec_fetch_is_allowed(request) is True

    def test_same_origin_and_none_are_allowed(self):
        for value in ["same-origin", "same-site", "none"]:
            request = FakeRequest(path="/unmanic/api/v2/version/read", headers={"Sec-Fetch-Site": value})
            assert guard.sec_fetch_is_allowed(request) is True


@pytest.mark.unittest
class TestWantsHtml(object):
    def test_browser_navigation_wants_html(self):
        request = FakeRequest(headers={"Accept": "text/html,application/xhtml+xml"})
        assert guard.wants_html(request) is True

    def test_xhr_does_not_want_html(self):
        request = FakeRequest(headers={"Accept": "application/json"})
        assert guard.wants_html(request) is False

    def test_no_accept_header_does_not_want_html(self):
        assert guard.wants_html(FakeRequest()) is False

    def test_non_get_never_wants_html(self):
        request = FakeRequest(method="POST", headers={"Accept": "text/html"})
        assert guard.wants_html(request) is False

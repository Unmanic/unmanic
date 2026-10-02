#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import pytest

from unmanic.libs.webauth.throttle import LoginThrottle


class FakeClock(object):
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.mark.unittest
class TestLoginThrottle(object):
    def setup_method(self):
        self.clock = FakeClock()
        self.throttle = LoginThrottle(
            max_failures=3, window_seconds=900, lockout_steps=(60, 300, 900), time_func=self.clock
        )

    def test_allows_by_default(self):
        assert self.throttle.retry_after("10.0.0.1") == 0

    def test_locks_out_after_the_failure_threshold(self):
        for _ in range(3):
            self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 60

    def test_below_the_threshold_is_still_allowed(self):
        self.throttle.record_failure("10.0.0.1")
        self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 0

    def test_lockout_expires(self):
        for _ in range(3):
            self.throttle.record_failure("10.0.0.1")
        self.clock.advance(61)
        assert self.throttle.retry_after("10.0.0.1") == 0

    def test_lockout_escalates_on_repeat_offences(self):
        for _ in range(3):
            self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 60
        self.clock.advance(61)
        for _ in range(3):
            self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 300
        self.clock.advance(301)
        for _ in range(3):
            self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 900

    def test_escalation_is_capped_at_the_last_step(self):
        for _ in range(4):
            for _ in range(3):
                self.throttle.record_failure("10.0.0.1")
            self.clock.advance(901)
        for _ in range(3):
            self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 900

    def test_keys_are_isolated(self):
        for _ in range(3):
            self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 60
        assert self.throttle.retry_after("10.0.0.2") == 0

    def test_failures_outside_the_window_do_not_accumulate(self):
        self.throttle.record_failure("10.0.0.1")
        self.throttle.record_failure("10.0.0.1")
        self.clock.advance(901)
        self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 0

    def test_success_clears_the_failure_record(self):
        self.throttle.record_failure("10.0.0.1")
        self.throttle.record_failure("10.0.0.1")
        self.throttle.record_success("10.0.0.1")
        self.throttle.record_failure("10.0.0.1")
        assert self.throttle.retry_after("10.0.0.1") == 0

    def test_retry_after_counts_down(self):
        for _ in range(3):
            self.throttle.record_failure("10.0.0.1")
        self.clock.advance(20)
        assert self.throttle.retry_after("10.0.0.1") == 40

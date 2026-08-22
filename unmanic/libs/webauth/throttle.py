#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import math
import threading
import time
from typing import Callable, Dict, Sequence


class LoginThrottle(object):
    """
    LoginThrottle

    In-memory, escalating lockout for failed authentication attempts.

    No artificial delay is applied to a rejected request; a delay would itself be a
    resource exhaustion vector. Requests are refused outright instead.
    """

    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: int = 900,
        lockout_steps: Sequence[int] = (60, 300, 900),
        time_func: Callable[[], float] = time.monotonic,
    ):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.lockout_steps = tuple(lockout_steps)
        self.time_func = time_func
        self._lock = threading.Lock()
        self._state = {}  # type: Dict[str, Dict[str, float]]

    def _entry(self, key: str) -> Dict[str, float]:
        return self._state.setdefault(
            key, {"failures": 0, "first_failure": 0.0, "locked_until": 0.0, "offences": 0}
        )

    def retry_after(self, key: str) -> int:
        """
        Return the number of seconds until this key may try again. 0 means allowed.

        :param key:
        :return:
        """
        with self._lock:
            entry = self._state.get(key)
            if entry is None:
                return 0
            remaining = entry["locked_until"] - self.time_func()
            if remaining <= 0:
                return 0
            return int(math.ceil(remaining))

    def record_failure(self, key: str) -> None:
        """
        Record a failed attempt, locking the key out once the threshold is reached.

        :param key:
        :return:
        """
        with self._lock:
            now = self.time_func()
            entry = self._entry(key)
            if entry["failures"] == 0 or (now - entry["first_failure"]) > self.window_seconds:
                entry["failures"] = 0
                entry["first_failure"] = now
            entry["failures"] += 1
            if entry["failures"] >= self.max_failures:
                step_index = min(int(entry["offences"]), len(self.lockout_steps) - 1)
                entry["locked_until"] = now + self.lockout_steps[step_index]
                entry["offences"] = min(int(entry["offences"]) + 1, len(self.lockout_steps) - 1)
                entry["failures"] = 0
                entry["first_failure"] = 0.0

    def record_success(self, key: str) -> None:
        """
        Clear the failure record for a key.

        :param key:
        :return:
        """
        with self._lock:
            self._state.pop(key, None)


login_throttle = LoginThrottle()

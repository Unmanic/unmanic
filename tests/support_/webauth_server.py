#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import asyncio
import base64
import os
import threading

import tornado.httpserver
import tornado.ioloop
import tornado.netutil


class BackgroundServer(object):
    """
    BackgroundServer

    Runs a Tornado application on a random port in a background thread and exposes its
    base URL, so tests can drive it over real HTTP.

    tornado.testing.AsyncHTTPTestCase is deliberately not used. Its AsyncTestCase base
    takes a methodName argument that current pytest releases do not supply, so it fails
    at collection with "object has no attribute 'runTest'". requirements-dev.txt pins
    only 'pytest>=7.4.3', so that breakage applies to anyone running the suite today.
    Driving a real server over real HTTP avoids the coupling entirely and exercises the
    same path the application actually serves.
    """

    def __init__(self, app_factory):
        self.app_factory = app_factory
        self.port = None
        self.io_loop = None
        self._server = None
        self._thread = None
        self._ready = threading.Event()
        self._error = None

    def start(self) -> str:
        """
        Start the server and return its base URL.

        :return:
        """

        def run():
            try:
                asyncio.set_event_loop(asyncio.new_event_loop())
                self.io_loop = tornado.ioloop.IOLoop.current()
                sockets = tornado.netutil.bind_sockets(0, "127.0.0.1")
                self.port = sockets[0].getsockname()[1]
                self._server = tornado.httpserver.HTTPServer(self.app_factory())
                self._server.add_sockets(sockets)
            except Exception as e:  # pragma: no cover - surfaced through start()
                self._error = e
                self._ready.set()
                return
            self._ready.set()
            self.io_loop.start()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        if not self._ready.wait(15):
            raise RuntimeError("Test server did not start within 15 seconds")
        if self._error is not None:
            raise self._error
        return "http://127.0.0.1:{}".format(self.port)

    def stop(self) -> None:
        """
        Shut the server down.

        :return:
        """
        if self.io_loop is not None:
            self.io_loop.add_callback(self._server.stop)
            self.io_loop.add_callback(self.io_loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=10)


def basic_header(username: str, password: str) -> str:
    """
    Build an HTTP Basic Authorization header value.

    :param username:
    :param password:
    :return:
    """
    raw = "{}:{}".format(username, password).encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def websocket_handshake_headers() -> dict:
    """
    Build the headers a browser sends to open a WebSocket.

    Used to assert on the handshake status code without pulling in a WebSocket client
    library. An authorised handshake answers 101; a refused one answers 401 or 302.

    :return:
    """
    return {
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-WebSocket-Key": base64.b64encode(os.urandom(16)).decode("ascii"),
        "Sec-WebSocket-Version": "13",
    }

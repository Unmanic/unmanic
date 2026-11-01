#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

from types import SimpleNamespace

import requests

from unmanic.libs import session as session_module


def test_library_opens_independent_read_and_write_sessions(monkeypatch):
    connection_id = "5aaec515-53b1-4e7b-8448-12f2976e8c98"
    library_row = SimpleNamespace(
        web_url="https://media.example/library/",
        web_username="reader",
        web_password="read-secret",
        web_write_url="https://dav.example/output/",
        web_write_username="writer",
        web_write_password="write-secret",
        web_write_credentials_same_as_read=False,
    )

    class FakeLibraries:
        @staticmethod
        def get_or_none(**kwargs):
            assert kwargs == {"web_connection_id": connection_id}
            return library_row

    monkeypatch.setattr(session_module, "Libraries", FakeLibraries)
    manager = session_module.Session()
    manager.web_connections = {}
    library = SimpleNamespace(get_web_connection_id=lambda: connection_id)

    connections = manager.open_library_web_connections(library)

    assert connections["connection_id"] == connection_id
    assert connections["read"]["role"] == "read"
    assert connections["write"]["role"] == "write"
    assert connections["read"]["url"] == "https://media.example/library/"
    assert connections["write"]["url"] == "https://dav.example/output/"
    assert connections["read"]["session"] is not connections["write"]["session"]
    assert connections["read"]["session"].auth == ("reader", "read-secret")
    assert connections["write"]["session"].auth == ("writer", "write-secret")
    assert isinstance(connections["read"]["session"], requests.Session)
    assert manager.get_web_connection(connection_id, "write")["session"] is connections["write"]["session"]


def test_write_session_reuses_read_credentials_when_selected(monkeypatch):
    connection_id = "5aaec515-53b1-4e7b-8448-12f2976e8c98"
    library_row = SimpleNamespace(
        web_url="https://media.example/library/",
        web_username="reader",
        web_password="read-secret",
        web_write_url="",
        web_write_username="",
        web_write_password="",
        web_write_credentials_same_as_read=True,
    )

    class FakeLibraries:
        @staticmethod
        def get_or_none(**kwargs):
            return library_row

    monkeypatch.setattr(session_module, "Libraries", FakeLibraries)
    manager = session_module.Session()
    manager.web_connections = {}

    connection = manager.get_web_connection(connection_id, "write")

    assert connection["url"] == "https://media.example/library/"
    assert connection["session"].auth == ("reader", "read-secret")


def test_sessions_are_isolated_between_libraries(monkeypatch):
    rows = {
        "5aaec515-53b1-4e7b-8448-12f2976e8c98": SimpleNamespace(
            web_url="https://first.example/library/",
            web_username="first-reader",
            web_password="first-secret",
        ),
        "a0831ea5-8e25-4e50-9a2e-a2028d7a3770": SimpleNamespace(
            web_url="https://second.example/library/",
            web_username="second-reader",
            web_password="second-secret",
        ),
    }

    class FakeLibraries:
        @staticmethod
        def get_or_none(**kwargs):
            return rows.get(kwargs["web_connection_id"])

    monkeypatch.setattr(session_module, "Libraries", FakeLibraries)
    manager = session_module.Session()
    manager.web_connections = {}

    first = manager.get_web_connection("5aaec515-53b1-4e7b-8448-12f2976e8c98", "read")
    second = manager.get_web_connection("a0831ea5-8e25-4e50-9a2e-a2028d7a3770", "read")

    assert first["session"] is not second["session"]
    assert first["session"].auth == ("first-reader", "first-secret")
    assert second["session"].auth == ("second-reader", "second-secret")


def test_connection_id_is_stable_across_stale_library_instances():
    from peewee import SqliteDatabase
    from unmanic.libs.library import Library
    from unmanic.libs.unmodels.libraries import Libraries

    database = SqliteDatabase(":memory:")
    with database.bind_ctx([Libraries], bind_refs=False, bind_backrefs=False):
        database.create_tables([Libraries])
        row = Libraries.create(name="Source", path="/library/source")
        first = SimpleNamespace(model=Libraries.get_by_id(row.id))
        second = SimpleNamespace(model=Libraries.get_by_id(row.id))
        first_id = Library.get_web_connection_id(first)
        second_id = Library.get_web_connection_id(second)
        assert first_id == second_id
        assert Libraries.get_by_id(row.id).web_connection_id == first_id
    database.close()

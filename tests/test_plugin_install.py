#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import builtins
import json
from types import SimpleNamespace
from unittest.mock import Mock
import zipfile

import pytest

from unmanic.libs.plugins import PluginsHandler


def handler(directory):
    return SimpleNamespace(
        logger=Mock(), get_plugin_path=lambda plugin_id: str(directory),
        _assert_zip_members_safe=PluginsHandler._assert_zip_members_safe,
        get_plugin_info=lambda plugin_id: json.loads((directory / "info.json").read_text()),
    )


def test_plugin_metadata_remains_readable_throughout_update(tmp_path, monkeypatch):
    directory = tmp_path / "plugin"
    directory.mkdir()
    info = directory / "info.json"
    info.write_text(json.dumps({"id": "example", "compatibility": [2], "version": "1"}))
    archive = tmp_path / "plugin.zip"
    updated = {"id": "example", "compatibility": [2], "version": "2"}
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("info.json", json.dumps(updated))
        stream.writestr("plugin.py", "# updated plugin\n")
    original_open = builtins.open
    observations = []

    def observe_writes(path, mode="r", *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        if isinstance(path, (str, bytes)) and "w" in mode:
            with original_open(info) as current:
                observations.append(json.load(current)["version"])
        return stream

    monkeypatch.setattr(builtins, "open", observe_writes)
    assert PluginsHandler.install_plugin(handler(directory), archive) == updated
    assert observations and set(observations) == {"1"}
    assert json.loads(info.read_text()) == updated


def test_invalid_update_metadata_preserves_installed_plugin(tmp_path):
    directory = tmp_path / "plugin"
    directory.mkdir()
    info = directory / "info.json"
    info.write_text('{"id":"example","compatibility":[2]}')
    (directory / "plugin.py").write_text("# installed plugin\n")
    archive = tmp_path / "plugin.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("info.json", "")
        stream.writestr("plugin.py", "# broken update\n")
    with pytest.raises(json.JSONDecodeError):
        PluginsHandler.install_plugin(handler(directory), archive, plugin_id="example")
    assert json.loads(info.read_text())["compatibility"] == [2]
    assert (directory / "plugin.py").read_text() == "# installed plugin\n"

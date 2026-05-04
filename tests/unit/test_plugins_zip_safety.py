#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    test_plugins_zip_safety.py

    Tests for PluginsHandler._assert_zip_members_safe — ensures the plugin
    install pipeline rejects zip-slip / symlink / absolute-path entries
    before extraction.
"""
import os
import stat
import tempfile
import zipfile

import pytest

from unmanic.libs.plugins import PluginsHandler


def _make_zip(tmp_path, entries):
    """Build a zip in tmp_path. Each entry is (name, data, external_attr)."""
    zip_path = os.path.join(tmp_path, "plugin.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, data, external_attr in entries:
            info = zipfile.ZipInfo(name)
            if external_attr is not None:
                info.external_attr = external_attr
            zf.writestr(info, data)
    return zip_path


class TestAssertZipMembersSafe:

    def test_safe_zip_passes(self, tmp_path):
        dest = str(tmp_path / "dest")
        os.makedirs(dest)
        zip_path = _make_zip(str(tmp_path), [
            ("info.json", b"{}", None),
            ("plugin.py", b"# code", None),
            ("static/index.html", b"<html/>", None),
        ])
        with zipfile.ZipFile(zip_path) as zf:
            PluginsHandler._assert_zip_members_safe(zf, dest)

    def test_parent_traversal_rejected(self, tmp_path):
        dest = str(tmp_path / "dest")
        os.makedirs(dest)
        zip_path = _make_zip(str(tmp_path), [("../escape.txt", b"x", None)])
        with zipfile.ZipFile(zip_path) as zf, pytest.raises(Exception, match="outside plugin directory"):
            PluginsHandler._assert_zip_members_safe(zf, dest)

    def test_deep_parent_traversal_rejected(self, tmp_path):
        dest = str(tmp_path / "dest")
        os.makedirs(dest)
        zip_path = _make_zip(str(tmp_path), [("a/b/../../../etc/passwd", b"x", None)])
        with zipfile.ZipFile(zip_path) as zf, pytest.raises(Exception, match="outside plugin directory"):
            PluginsHandler._assert_zip_members_safe(zf, dest)

    def test_absolute_posix_path_rejected(self, tmp_path):
        dest = str(tmp_path / "dest")
        os.makedirs(dest)
        zip_path = _make_zip(str(tmp_path), [("/etc/passwd", b"x", None)])
        with zipfile.ZipFile(zip_path) as zf, pytest.raises(Exception, match="absolute path"):
            PluginsHandler._assert_zip_members_safe(zf, dest)

    def test_windows_drive_path_rejected(self, tmp_path):
        dest = str(tmp_path / "dest")
        os.makedirs(dest)
        zip_path = _make_zip(str(tmp_path), [("C:/Windows/evil.dll", b"x", None)])
        with zipfile.ZipFile(zip_path) as zf, pytest.raises(Exception, match="absolute path"):
            PluginsHandler._assert_zip_members_safe(zf, dest)

    def test_symlink_entry_rejected(self, tmp_path):
        dest = str(tmp_path / "dest")
        os.makedirs(dest)
        # external_attr encodes a symlink in the upper 16 bits as Unix file mode.
        symlink_attr = (stat.S_IFLNK | 0o777) << 16
        zip_path = _make_zip(str(tmp_path), [("link", b"../../etc", symlink_attr)])
        with zipfile.ZipFile(zip_path) as zf, pytest.raises(Exception, match="symlink"):
            PluginsHandler._assert_zip_members_safe(zf, dest)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import subprocess

import versioninfo


def test_build_version_ignores_non_release_tags(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.chdir(tmp_path)
    commit = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
              "commit", "--allow-empty", "-q", "-m", "Test version"]
    subprocess.run(commit, check=True)
    subprocess.run(["git", "tag", "0.4.1"], check=True)
    subprocess.run(commit, check=True)
    subprocess.run(["git", "tag", "tv-611.1"], check=True)

    version = versioninfo.get_git_version_info()

    assert version["short"] == "0.4.1.post1"
    assert version["long"].startswith("0.4.1+")
    assert "tv-611.1" not in version["long"]

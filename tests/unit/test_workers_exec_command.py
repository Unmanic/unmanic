#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    test_workers_exec_command.py

    Tests for Worker._coerce_exec_command_to_argv — ensures plugin-supplied
    exec_command values are normalised to an argv list and that strings are
    never handed to subprocess.Popen with shell=True.
"""
import logging

import pytest

from unmanic.libs.workers import Worker


class TestCoerceExecCommandToArgv:

    def test_list_returned_unchanged(self):
        cmd = ["ffmpeg", "-i", "in.mkv", "-c", "copy", "out.mkv"]
        assert Worker._coerce_exec_command_to_argv(cmd) is cmd

    def test_simple_string_split(self):
        result = Worker._coerce_exec_command_to_argv("ffmpeg -i in.mkv out.mkv")
        assert result == ["ffmpeg", "-i", "in.mkv", "out.mkv"]

    def test_string_with_filename_metacharacters_does_not_inject(self):
        # A filename containing shell metacharacters must not become extra
        # arguments or commands. shlex.split treats unquoted ; & | as
        # separators (which would split into bad argv but never spawn a
        # shell), so plugin authors who rely on such filenames will see a
        # loud failure rather than silent injection.
        evil = "movie; rm -rf /tmp/x"
        cmd = 'ffmpeg -i "{}" out.mkv'.format(evil)
        result = Worker._coerce_exec_command_to_argv(cmd)
        assert result == ["ffmpeg", "-i", evil, "out.mkv"]
        assert "rm" not in [a.strip() for a in result]

    def test_string_emits_deprecation_warning(self, caplog):
        logger = logging.getLogger("test")
        with caplog.at_level(logging.WARNING, logger="test"):
            Worker._coerce_exec_command_to_argv("ffmpeg -version", logger=logger)
        assert any("deprecated" in r.message for r in caplog.records)

    def test_list_does_not_warn(self, caplog):
        logger = logging.getLogger("test")
        with caplog.at_level(logging.WARNING, logger="test"):
            Worker._coerce_exec_command_to_argv(["ffmpeg", "-version"], logger=logger)
        assert not any("deprecated" in r.message for r in caplog.records)

    def test_invalid_type_raises(self):
        for bad in [None, 42, {"cmd": "ffmpeg"}, ("ffmpeg",)]:
            with pytest.raises(Exception, match="must be a list"):
                Worker._coerce_exec_command_to_argv(bad)

    def test_string_quoted_args_preserved(self):
        result = Worker._coerce_exec_command_to_argv(
            'ffmpeg -i "input file with spaces.mkv" -c copy "out file.mkv"')
        assert result == ["ffmpeg", "-i", "input file with spaces.mkv",
                          "-c", "copy", "out file.mkv"]

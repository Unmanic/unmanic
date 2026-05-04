#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    test_postprocessor_remote.py

    Tests for PostProcessor.post_process_remote_file — locks in the
    invariant that the remote-source file is never removed unless the
    processed file has been delivered to its destination.
"""
import logging
import os

import pytest

from unmanic.libs.postprocessor import PostProcessor


def _build_postprocessor(cache_root, dest_path, source_abspath, cache_path):
    """Build a PostProcessor with just enough state to drive the remote path."""
    pp = PostProcessor.__new__(PostProcessor)
    pp.logger = logging.getLogger("test.postprocessor")
    pp._last_destination_files = []
    pp._last_file_move_processes_success = False

    class _Settings:
        def get_cache_path(self):
            return str(cache_root)

    class _Task:
        def get_cache_path(self_inner):
            return cache_path

        def get_source_data(self_inner):
            return {"abspath": source_abspath}

        def get_destination_data(self_inner):
            return {"abspath": dest_path}

        def modify_path(self_inner, new_path):
            self_inner.modified_to = new_path

    pp.settings = _Settings()
    pp.current_task = _Task()
    return pp


def _disable_cleanup(pp):
    """Cache cleanup unlinks tmp dirs we want to inspect — neutralise it."""
    pp._PostProcessor__cleanup_cache_files = lambda _path: None


class TestPostProcessRemoteFile:

    def test_source_retained_when_copy_to_cache_destination_fails(self, tmp_path):
        """Headline case: cache-internal handoff that fails to copy must
        not delete the source. Previously the source was removed first."""
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        source = tmp_path / "source.mkv"
        source.write_bytes(b"original")
        cache_file = cache_root / "task-cache" / "processed.mkv"
        cache_file.parent.mkdir()
        cache_file.write_bytes(b"processed")
        # Destination is inside the cache root, so remove_source_file is True.
        destination = cache_root / "destination" / "out.mkv"

        pp = _build_postprocessor(cache_root, str(destination), str(source), str(cache_file))
        _disable_cleanup(pp)
        # Force the copy to fail.
        pp._PostProcessor__copy_file = lambda *args, **kwargs: False

        pp.post_process_remote_file()

        assert source.exists(), "source must be retained when delivery fails"
        assert pp._last_file_move_processes_success is False
        assert pp._last_destination_files == []

    def test_source_removed_only_after_successful_copy(self, tmp_path):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        source = tmp_path / "source.mkv"
        source.write_bytes(b"original")
        cache_file = cache_root / "task-cache" / "processed.mkv"
        cache_file.parent.mkdir()
        cache_file.write_bytes(b"processed")
        destination = cache_root / "destination" / "out.mkv"

        pp = _build_postprocessor(cache_root, str(destination), str(source), str(cache_file))
        _disable_cleanup(pp)
        pp._PostProcessor__copy_file = lambda *args, **kwargs: True

        pp.post_process_remote_file()

        assert not source.exists(), "source must be removed once delivery succeeds"
        assert pp._last_file_move_processes_success is True
        assert pp._last_destination_files == [str(destination)]

    def test_library_destination_keeps_source_regardless(self, tmp_path):
        """When the destination is in the library (not the cache), the source
        is always kept — copy success or failure does not change that."""
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        library = tmp_path / "library"
        library.mkdir()
        source = library / "source.mkv"
        source.write_bytes(b"original")
        cache_file = cache_root / "task-cache" / "processed.mkv"
        cache_file.parent.mkdir()
        cache_file.write_bytes(b"processed")
        destination = library / "out.mkv"  # outside cache_root

        pp = _build_postprocessor(cache_root, str(destination), str(source), str(cache_file))
        _disable_cleanup(pp)
        pp._PostProcessor__copy_file = lambda *args, **kwargs: True

        pp.post_process_remote_file()

        assert source.exists(), "library source must always be retained"
        assert pp._last_file_move_processes_success is True
        assert pp._last_destination_files and pp._last_destination_files[0].endswith(
            "processed.mkv")

    def test_library_path_falls_back_to_cache_on_library_failure(self, tmp_path):
        """If the library staging dir copy fails, the function falls back to
        a cache-side staging dir and reports success."""
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        library = tmp_path / "library"
        library.mkdir()
        source = library / "source.mkv"
        source.write_bytes(b"original")
        cache_file = cache_root / "task-cache" / "processed.mkv"
        cache_file.parent.mkdir()
        cache_file.write_bytes(b"processed")
        destination = library / "out.mkv"

        pp = _build_postprocessor(cache_root, str(destination), str(source), str(cache_file))
        _disable_cleanup(pp)

        # First call (library-side) fails, subsequent calls succeed.
        calls = {"n": 0}

        def fake_copy(*args, **kwargs):
            calls["n"] += 1
            return calls["n"] != 1

        pp._PostProcessor__copy_file = fake_copy

        pp.post_process_remote_file()

        assert source.exists()
        assert pp._last_file_move_processes_success is True
        assert pp._last_destination_files
        assert "cache" in pp._last_destination_files[0]

    def test_both_staging_dirs_failing_reports_failure(self, tmp_path):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        library = tmp_path / "library"
        library.mkdir()
        source = library / "source.mkv"
        source.write_bytes(b"original")
        cache_file = cache_root / "task-cache" / "processed.mkv"
        cache_file.parent.mkdir()
        cache_file.write_bytes(b"processed")
        destination = library / "out.mkv"

        pp = _build_postprocessor(cache_root, str(destination), str(source), str(cache_file))
        _disable_cleanup(pp)
        pp._PostProcessor__copy_file = lambda *args, **kwargs: False

        pp.post_process_remote_file()

        assert source.exists()
        assert pp._last_file_move_processes_success is False
        assert pp._last_destination_files == []

    def test_missing_cache_file_reports_failure(self, tmp_path):
        cache_root = tmp_path / "cache"
        cache_root.mkdir()
        source = tmp_path / "source.mkv"
        source.write_bytes(b"original")
        cache_file = cache_root / "task-cache" / "processed.mkv"  # never created
        destination = cache_root / "destination" / "out.mkv"

        pp = _build_postprocessor(cache_root, str(destination), str(source), str(cache_file))
        _disable_cleanup(pp)
        # Sentinel: __copy_file should never be invoked when cache is missing.
        pp._PostProcessor__copy_file = lambda *args, **kwargs: pytest.fail("__copy_file should not be called")

        pp.post_process_remote_file()

        assert source.exists()
        assert pp._last_file_move_processes_success is False
        assert pp._last_destination_files == []

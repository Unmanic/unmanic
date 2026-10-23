#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Discover and download files from an HTTP directory listing."""

import base64
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import tempfile
import urllib.error
import urllib.parse
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Remote redirects are not accepted")


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attributes):
        if tag == 'a':
            self.hrefs.extend(value for name, value in attributes if name == 'href' and value)


def _validate_url(value, directory=False):
    if not isinstance(value, str):
        raise ValueError("Expected an HTTP or HTTPS URL")
    parts = urllib.parse.urlsplit(value)
    if parts.scheme not in {'http', 'https'} or not parts.hostname:
        raise ValueError("Expected an HTTP or HTTPS URL")
    if parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError("URL must not contain credentials, query parameters or a fragment")
    path = urllib.parse.quote(urllib.parse.unquote(parts.path or '/'), safe='/')
    if directory and not path.endswith('/'):
        raise ValueError("Directory URL must end with /")
    return urllib.parse.urlunsplit(parts._replace(path=path))


def _same_origin(first, second):
    first_parts = urllib.parse.urlsplit(first)
    second_parts = urllib.parse.urlsplit(second)
    return (first_parts.scheme, first_parts.netloc) == (second_parts.scheme, second_parts.netloc)


def _relative_path(root_url, child_url):
    root_path = urllib.parse.unquote(urllib.parse.urlsplit(root_url).path)
    child_path = urllib.parse.unquote(urllib.parse.urlsplit(child_url).path)
    root_prefix = root_path if root_path.endswith('/') else root_path + '/'
    if not child_path.startswith(root_prefix):
        raise ValueError("Remote file escaped the web scanner root")
    relative = child_path[len(root_prefix):].strip('/')
    parts = relative.split('/')
    if not relative or any(not part or part in {'.', '..'} or '\\' in part for part in parts):
        raise ValueError("Remote file contains an invalid relative path")
    return Path(*parts)


def _safe_target(destination, relative):
    """Create a destination beneath the library without following symlinks."""
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    root = root.resolve(strict=True)
    relative = Path(relative)
    if relative.is_absolute() or not relative.parts or any(part in {'.', '..'} for part in relative.parts):
        raise ValueError("Remote file contains an invalid relative path")

    target = root
    for part in relative.parts[:-1]:
        target = target / part
        if target.is_symlink():
            raise ValueError("Remote file path crosses a symbolic link")
        if target.exists() and not target.is_dir():
            raise ValueError("Remote file path crosses a non-directory entry")
        target.mkdir(exist_ok=True)
        if target.is_symlink():
            raise ValueError("Remote file path crosses a symbolic link")

    target = target / relative.parts[-1]
    if target.is_symlink():
        raise ValueError("Remote file path targets a symbolic link")
    return target


class WebDirectory:
    def __init__(self, url, username='', password=''):
        self.url = _validate_url(url, directory=True)
        self.username = username or ''
        self.password = password or ''
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, url, method='GET', headers=None):
        url = _validate_url(url)
        if not _same_origin(self.url, url):
            raise ValueError("Remote URL does not match the web scanner origin")
        root_path = urllib.parse.unquote(urllib.parse.urlsplit(self.url).path)
        url_path = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
        root_prefix = root_path if root_path.endswith('/') else root_path + '/'
        if url_path != root_path and not url_path.startswith(root_prefix):
            raise ValueError("Remote URL escaped the web scanner root")
        request_headers = dict(headers or {})
        if self.username or self.password:
            token = base64.b64encode(
                '{}:{}'.format(self.username, self.password).encode('utf-8')
            ).decode('ascii')
            request_headers['Authorization'] = 'Basic {}'.format(token)
        request = urllib.request.Request(url, headers=request_headers, method=method)
        return self.opener.open(request, timeout=60)

    def listing(self, url):
        url = _validate_url(url, directory=True)
        with self.request(url) as response:
            parser = Links()
            encoding = response.headers.get_content_charset() or 'utf-8'
            parser.feed(response.read().decode(encoding, errors='replace'))

        children = set()
        for href in parser.hrefs:
            try:
                child = _validate_url(urllib.parse.urljoin(url, href))
            except ValueError:
                continue
            if not _same_origin(self.url, child) or child == url:
                continue
            directory_path = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
            child_path = urllib.parse.unquote(urllib.parse.urlsplit(child).path)
            directory_prefix = directory_path if directory_path.endswith('/') else directory_path + '/'
            if not child_path.startswith(directory_prefix):
                continue
            remainder = child_path[len(directory_prefix):].rstrip('/')
            if not remainder or '/' in remainder or remainder in {'.', '..'}:
                continue
            children.add(child + ('/' if href.endswith('/') and not child.endswith('/') else ''))
        return sorted(children)

    def files(self):
        result = []

        def walk(directory):
            for child in self.listing(directory):
                relative = _relative_path(self.url, child)
                if child.endswith('/'):
                    walk(child)
                else:
                    result.append((relative, child))

        walk(self.url)
        return sorted(result, key=lambda item: item[0].as_posix())

    def download(self, url, target, previous_metadata=None):
        target = Path(target)
        if target.is_symlink():
            raise ValueError("Web scanner cannot replace a symbolic link")
        headers = {}
        previous_metadata = previous_metadata or {}
        if target.is_file():
            if previous_metadata.get('etag'):
                headers['If-None-Match'] = previous_metadata['etag']
            if previous_metadata.get('last_modified'):
                headers['If-Modified-Since'] = previous_metadata['last_modified']

        try:
            response = self.request(url, headers=headers)
        except urllib.error.HTTPError as error:
            if error.code == 304:
                error.close()
                if target.is_file():
                    return False, previous_metadata
                raise RuntimeError("Remote server returned 304 for a missing local file")
            raise

        if response.getcode() == 304:
            response.close()
            if target.is_file():
                return False, previous_metadata
            raise RuntimeError("Remote server returned 304 for a missing local file")

        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        digest = hashlib.sha256()
        try:
            with tempfile.NamedTemporaryFile(dir=str(target.parent), prefix='.unmanic-web-', delete=False) as temporary:
                temporary_path = Path(temporary.name)
                for chunk in iter(lambda: response.read(1024 * 1024), b''):
                    temporary.write(chunk)
                    digest.update(chunk)
            metadata = {
                'etag': response.headers.get('ETag', ''),
                'last_modified': response.headers.get('Last-Modified', ''),
                'content_length': response.headers.get('Content-Length', ''),
            }
            changed = not target.is_file() or _file_hash(target) != digest.hexdigest()
            if changed:
                os.replace(temporary_path, target)
            return changed, metadata
        finally:
            response.close()
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()


def _file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _load_state(path, url):
    try:
        state = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(state, dict) or state.get('url') != url:
        return {}
    files = state.get('files', {})
    return files if isinstance(files, dict) else {}


def _save_state(path, url, files):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=str(path.parent),
            prefix='.unmanic-web-state-',
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump({'url': url, 'files': files}, temporary, indent=2, sort_keys=True)
            temporary.write('\n')
        os.replace(temporary_path, path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def acquire(url, destination, state_path, username='', password=''):
    """Download remote files into a local library and return the changed count."""
    remote = WebDirectory(url, username=username, password=password)
    previous_files = _load_state(state_path, remote.url)
    current_files = {}
    changed_count = 0
    for relative, remote_url in remote.files():
        key = relative.as_posix()
        target = _safe_target(destination, relative)
        changed, metadata = remote.download(
            remote_url,
            target,
            previous_metadata=previous_files.get(key),
        )
        current_files[key] = metadata
        if changed:
            changed_count += 1
    _save_state(state_path, remote.url, current_files)
    return changed_count

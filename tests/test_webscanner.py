from email.message import Message
from pathlib import Path

import pytest

from unmanic.libs import webscanner


def test_directory_url_requires_trailing_slash():
    with pytest.raises(ValueError, match='Directory URL must end with /'):
        webscanner.WebDirectory('https://media.example/library')


def test_relative_path_rejects_escape():
    with pytest.raises(ValueError, match='escaped'):
        webscanner._relative_path(
            'https://media.example/library/',
            'https://media.example/other/video.mkv',
        )


def test_relative_path_rejects_encoded_escape():
    with pytest.raises(ValueError, match='invalid relative path'):
        webscanner._relative_path(
            'https://media.example/library/',
            'https://media.example/library/%2e%2e/private.txt',
        )


def test_request_uses_basic_auth_for_the_configured_origin():
    remote = webscanner.WebDirectory(
        'https://media.example/library/',
        username='user',
        password='pass',
    )
    captured = {}

    class FakeOpener:
        def open(self, request, timeout):
            captured['request'] = request
            captured['timeout'] = timeout
            return object()

    remote.opener = FakeOpener()
    remote.request('https://media.example/library/video.mkv')

    assert captured['request'].get_header('Authorization') == 'Basic dXNlcjpwYXNz'
    assert captured['timeout'] == 60


def test_request_rejects_another_origin_before_sending_credentials():
    remote = webscanner.WebDirectory(
        'https://media.example/library/',
        username='user',
        password='pass',
    )
    opened = []

    class FakeOpener:
        def open(self, request, timeout):
            opened.append(request)
            return object()

    remote.opener = FakeOpener()
    with pytest.raises(ValueError, match='origin'):
        remote.request('https://other.example/library/video.mkv')
    assert opened == []


def test_listing_discovers_files_and_directories_and_ignores_escaped_links(monkeypatch):
    remote = webscanner.WebDirectory('https://media.example/library/')

    class Response:
        headers = Message()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return (
                b'<a href="video.mkv">video</a>'
                b'<a href="nested/">nested</a>'
                b'<a href="../private.txt">private</a>'
                b'<a href="https://other.example/video.mkv">external</a>'
            )

    monkeypatch.setattr(remote, 'request', lambda url: Response())

    assert remote.listing(remote.url) == [
        'https://media.example/library/nested/',
        'https://media.example/library/video.mkv',
    ]


def test_files_retain_remote_relative_paths(monkeypatch):
    remote = webscanner.WebDirectory('https://media.example/library/')
    listings = {
        'https://media.example/library/': [
            'https://media.example/library/root.mkv',
            'https://media.example/library/nested/',
        ],
        'https://media.example/library/nested/': [
            'https://media.example/library/nested/child.mp4',
        ],
    }
    monkeypatch.setattr(remote, 'listing', lambda url: listings[url])

    assert remote.files() == [
        (Path('nested/child.mp4'), 'https://media.example/library/nested/child.mp4'),
        (Path('root.mkv'), 'https://media.example/library/root.mkv'),
    ]


def test_acquire_downloads_files_and_saves_state(tmp_path, monkeypatch):
    destination = tmp_path / 'library'
    state_path = tmp_path / 'config' / 'web_scanner' / '1.json'

    class FakeWebDirectory:
        url = 'https://media.example/library/'

        def __init__(self, url, username='', password=''):
            assert url == self.url
            assert username == 'user'
            assert password == 'pass'

        def files(self):
            return [(Path('video.mkv'), 'https://media.example/library/video.mkv')]

        def download(self, url, target, previous_metadata=None):
            assert url.endswith('/video.mkv')
            assert previous_metadata is None
            Path(target).parent.mkdir(parents=True, exist_ok=True)
            Path(target).write_bytes(b'video')
            return True, {'etag': 'one'}

    monkeypatch.setattr(webscanner, 'WebDirectory', FakeWebDirectory)

    changed = webscanner.acquire(
        'https://media.example/library/',
        destination,
        state_path,
        username='user',
        password='pass',
    )

    assert changed == 1
    assert (destination / 'video.mkv').read_bytes() == b'video'
    state = state_path.read_text()
    assert '"etag": "one"' in state
    assert 'pass' not in state


def test_download_does_not_send_stale_validators_for_missing_local_file(tmp_path, monkeypatch):
    remote = webscanner.WebDirectory('https://media.example/library/')
    target = tmp_path / 'library' / 'video.mkv'
    captured = {}

    class Response:
        headers = {'ETag': 'new', 'Last-Modified': 'today', 'Content-Length': '5'}

        def __init__(self):
            self.data = b'video'

        def read(self, size=-1):
            result, self.data = self.data, b''
            return result

        def getcode(self):
            return 200

        def close(self):
            pass

    def request(url, headers=None):
        captured['headers'] = headers
        return Response()

    monkeypatch.setattr(remote, 'request', request)
    changed, metadata = remote.download(
        remote.url + 'video.mkv',
        target,
        previous_metadata={'etag': 'old', 'last_modified': 'yesterday'},
    )

    assert captured['headers'] == {}
    assert changed is True
    assert metadata['etag'] == 'new'
    assert target.read_bytes() == b'video'


def test_acquire_rejects_symlinked_destination_parent_without_writing_outside(tmp_path, monkeypatch):
    destination = tmp_path / 'library'
    outside = tmp_path / 'outside'
    destination.mkdir()
    outside.mkdir()
    (destination / 'linked').symlink_to(outside, target_is_directory=True)

    class FakeWebDirectory:
        url = 'https://media.example/library/'

        def __init__(self, url, username='', password=''):
            pass

        def files(self):
            return [(Path('linked/new/video.mkv'), self.url + 'linked/new/video.mkv')]

    monkeypatch.setattr(webscanner, 'WebDirectory', FakeWebDirectory)
    with pytest.raises(ValueError, match='symbolic link'):
        webscanner.acquire(
            'https://media.example/library/',
            destination,
            tmp_path / 'config' / 'state.json',
        )
    assert not (outside / 'new').exists()

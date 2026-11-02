"""Security tests for the self-update download path (CodeQL alert 12, py/full-ssrf).

`POST /api/download-update` used to pass a client-supplied URL straight to `urlopen`,
guarded only by a string prefix check, and followed any redirect. These tests pin the
properties that matter: only this project's own release assets on github.com are
fetchable, redirects may only stay on GitHub's download hosts over https, and the
response size is bounded.
"""

import http.client
import http.server
import json
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from line_vault.server import (
    MAX_UPDATE_DOWNLOAD_BYTES,
    UpdateRedirectHandler,
    build_update_opener,
    create_server,
    fetch_update_asset,
    resolve_update_download_url,
)

LATEST_EXE = "https://github.com/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe"
TAGGED_EXE = "https://github.com/SanHsien/line-vault/releases/download/v1.4.3/LINE-Vault-win64.exe"
TAGGED_ZIP = "https://github.com/SanHsien/line-vault/releases/download/v1.4.3/LINE-Vault-v1.4.3-win64.zip"


@pytest.mark.parametrize("url", [LATEST_EXE, TAGGED_EXE, TAGGED_ZIP])
def test_update_url_accepts_own_release_assets_unchanged(url):
    """The URLs the app itself advertises must keep working."""
    assert resolve_update_download_url(url, "LINE-Vault-win64.exe") == url


def test_update_url_empty_falls_back_to_latest_release_asset():
    assert resolve_update_download_url("", "LINE-Vault-win64.exe") == LATEST_EXE
    assert (
        resolve_update_download_url("", "LINE-Vault-win64.zip")
        == "https://github.com/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.zip"
    )


@pytest.mark.parametrize(
    "url",
    [
        # non-https schemes
        "http://github.com/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        "file:///C:/Windows/win.ini",
        "ftp://github.com/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        # internal / loopback / metadata targets
        "https://127.0.0.1/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        "https://localhost:8765/api/shutdown",
        "https://169.254.169.254/latest/meta-data/",
        "https://[::1]/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        # host spoofing
        "https://github.com.evil.example/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        "https://github.com@evil.example/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        "https://evil.example@github.com/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        "https://github.com:8443/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        "https://github.com\\@evil.example/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        # GitHub's CDN is only a legitimate redirect target, never a client-chosen start
        "https://objects.githubusercontent.com/github-production-release-asset/1/2",
        # somebody else's GitHub release, or not a release asset at all
        "https://github.com/attacker/line-vault/releases/download/v9/LINE-Vault-win64.exe",
        "https://github.com/SanHsien/other-repo/releases/download/v9/LINE-Vault-win64.exe",
        "https://github.com/SanHsien/line-vault/archive/refs/heads/main.zip",
        "https://github.com/SanHsien/line-vault/releases/latest",
        "https://github.com/SanHsien/line-vault/releases/download/v1.4.3/",
        # path tricks, query, fragment, control characters
        "https://github.com/SanHsien/line-vault/releases/download/../../../attacker/x/releases/download/v1/a.exe",
        "https://github.com/SanHsien/line-vault/releases/download/%2e%2e/a.exe",
        "https://github.com/SanHsien/line-vault/releases/download/v1/LINE-Vault-win64.exe?x=1",
        "https://github.com/SanHsien/line-vault/releases/download/v1/LINE-Vault-win64.exe#frag",
        "https://github.com/SanHsien/line-vault/releases/download/v1/LINE-Vault-win64.exe\r\nHost: evil",
        "https://github.com/SanHsien/line-vault/releases/download/v1/LINE Vault.exe",
        # not an installable asset
        "https://github.com/SanHsien/line-vault/releases/download/v1/install.sh",
        # not a URL at all
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "javascript:alert(1)",
    ],
)
def test_update_url_rejects_everything_but_own_release_assets(url):
    """Each rejected form is a way to point the server at a target the maintainer did not publish."""
    assert resolve_update_download_url(url, "LINE-Vault-win64.exe") is None


@pytest.mark.parametrize(
    "target",
    [
        "https://objects.githubusercontent.com/github-production-release-asset/1/2?sig=abc",
        "https://release-assets.githubusercontent.com/github-production-release-asset/1/2?sp=r",
        "https://github.com/SanHsien/line-vault/releases/download/v1.4.3/LINE-Vault-win64.exe",
    ],
)
def test_update_redirect_allows_github_download_hosts_over_https(target):
    handler = UpdateRedirectHandler()
    request = urllib.request.Request(LATEST_EXE)
    new_request = handler.redirect_request(request, None, 302, "Found", {}, target)
    assert new_request is not None
    assert new_request.full_url == target


@pytest.mark.parametrize(
    "target",
    [
        "http://objects.githubusercontent.com/x",
        "http://127.0.0.1:8765/api/shutdown",
        "https://127.0.0.1/x",
        "https://localhost/x",
        "https://169.254.169.254/latest/meta-data/",
        "file:///C:/Windows/win.ini",
        "https://evil.example/LINE-Vault-win64.exe",
        "https://github.com.evil.example/x",
        "https://objects.githubusercontent.com.evil.example/x",
        "https://evil.example@objects.githubusercontent.com/x",
        "https://objects.githubusercontent.com:8443/x",
    ],
)
def test_update_redirect_refuses_other_hosts_schemes_and_ports(target):
    """A 302 from github.com must not be able to bounce the server to an internal or foreign target."""
    handler = UpdateRedirectHandler()
    request = urllib.request.Request(LATEST_EXE)
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        handler.redirect_request(request, None, 302, "Found", {}, target)
    assert "blocked" in str(exc_info.value.msg).lower()


def test_update_opener_does_not_follow_redirect_to_loopback_service():
    """End to end: a real 302 to a loopback service is refused and the service is never contacted."""
    hits: list[str] = []

    class Secret(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"internal-secret")

        def log_message(self, *args):
            pass

    secret_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Secret)
    secret_port = secret_srv.server_port

    class Redirector(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{secret_port}/internal")
            self.end_headers()

        def log_message(self, *args):
            pass

    redirect_srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Redirector)
    threads = [
        threading.Thread(target=secret_srv.serve_forever, daemon=True),
        threading.Thread(target=redirect_srv.serve_forever, daemon=True),
    ]
    for th in threads:
        th.start()
    try:
        opener = build_update_opener()
        with pytest.raises(urllib.error.HTTPError):
            opener.open(f"http://127.0.0.1:{redirect_srv.server_port}/start", timeout=5)
        assert hits == []
    finally:
        for srv in (redirect_srv, secret_srv):
            srv.shutdown()
            srv.server_close()


class _FakeResponse:
    def __init__(self, payload: bytes, content_length: str | None = None):
        self._payload = payload
        self._pos = 0
        self.headers = {} if content_length is None else {"Content-Length": content_length}

    def read(self, n: int = -1) -> bytes:
        end = len(self._payload) if n < 0 else self._pos + n
        chunk = self._payload[self._pos:end]
        self._pos += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeOpener:
    def __init__(self, response: _FakeResponse):
        self.response = response
        self.requested: list[str] = []

    def open(self, request, timeout=None):
        self.requested.append(request.full_url)
        return self.response


def test_fetch_update_asset_returns_bytes_within_cap():
    opener = _FakeOpener(_FakeResponse(b"MZ" + b"\x00" * 100))
    assert fetch_update_asset(LATEST_EXE, opener=opener) == b"MZ" + b"\x00" * 100
    assert opener.requested == [LATEST_EXE]


def test_fetch_update_asset_refuses_oversized_body_without_content_length():
    opener = _FakeOpener(_FakeResponse(b"A" * 5000))
    with pytest.raises(ValueError):
        fetch_update_asset(LATEST_EXE, opener=opener, max_bytes=4096)


def test_fetch_update_asset_refuses_declared_oversized_body_up_front():
    opener = _FakeOpener(_FakeResponse(b"A" * 10, content_length=str(MAX_UPDATE_DOWNLOAD_BYTES + 1)))
    with pytest.raises(ValueError):
        fetch_update_asset(LATEST_EXE, opener=opener)


def test_fetch_update_asset_revalidates_url_before_any_request():
    """The fetch helper is a second line of defence: it never opens a URL the resolver would refuse."""
    opener = _FakeOpener(_FakeResponse(b"x"))
    with pytest.raises(ValueError):
        fetch_update_asset("https://127.0.0.1/LINE-Vault-win64.exe", opener=opener)
    assert opener.requested == []


def _post(base_url: str, payload: dict):
    req = urllib.request.Request(
        f"{base_url}/api/download-update",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    return urllib.request.urlopen(req, timeout=10)


@pytest.fixture
def running_server(tmp_path: Path, monkeypatch):
    home = tmp_path / "home"
    (home / "Downloads").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    server = create_server(vault_dir=tmp_path / "vault", host="127.0.0.1", port=0)
    th = threading.Thread(target=server.serve_forever, daemon=True)
    th.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", home
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize(
    "bad_url",
    [
        "http://127.0.0.1:8765/api/shutdown",
        "file:///C:/Windows/win.ini",
        "https://169.254.169.254/latest/meta-data/",
        "https://github.com.evil.example/SanHsien/line-vault/releases/latest/download/LINE-Vault-win64.exe",
        "https://github.com/attacker/line-vault/releases/download/v9/LINE-Vault-win64.exe",
    ],
)
def test_download_update_endpoint_rejects_foreign_url_without_any_request(running_server, monkeypatch, bad_url):
    base_url, home = running_server
    calls: list[str] = []
    monkeypatch.setattr(
        "line_vault.server.fetch_update_asset",
        lambda url, **kwargs: calls.append(url) or b"should-not-happen",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        _post(base_url, {"download_url": bad_url})
    assert exc_info.value.code == 400
    assert calls == []
    assert list((home / "Downloads").iterdir()) == []


def test_download_update_endpoint_saves_own_release_asset(running_server, monkeypatch):
    base_url, home = running_server
    calls: list[str] = []

    def fake_fetch(url, **kwargs):
        calls.append(url)
        return b"MZ-fake-exe"

    monkeypatch.setattr("line_vault.server.fetch_update_asset", fake_fetch)
    with _post(base_url, {"download_url": TAGGED_EXE}) as res:
        body = json.loads(res.read().decode("utf-8"))
    assert body["success"] is True
    assert calls == [TAGGED_EXE]
    saved = Path(body["saved_path"])
    assert saved.parent == home / "Downloads"
    assert saved.read_bytes() == b"MZ-fake-exe"


def test_download_update_endpoint_without_url_uses_latest_release_asset(running_server, monkeypatch):
    base_url, _home = running_server
    calls: list[str] = []
    monkeypatch.setattr(
        "line_vault.server.fetch_update_asset",
        lambda url, **kwargs: calls.append(url) or b"MZ",
    )
    with _post(base_url, {"asset_type": "exe"}) as res:
        assert json.loads(res.read().decode("utf-8"))["success"] is True
    assert calls == [LATEST_EXE]


@pytest.mark.parametrize(
    "error",
    [
        ValueError("update asset exceeds size limit"),
        http.client.InvalidURL("bad url"),
        urllib.error.URLError("unreachable"),
        TimeoutError("slow"),
    ],
)
def test_download_update_endpoint_reports_fetch_failures_as_structured_500(running_server, monkeypatch, error):
    base_url, home = running_server

    def failing_fetch(url, **kwargs):
        raise error

    monkeypatch.setattr("line_vault.server.fetch_update_asset", failing_fetch)
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        _post(base_url, {"download_url": LATEST_EXE})
    assert exc_info.value.code == 500
    assert "error" in json.loads(exc_info.value.read().decode("utf-8"))
    assert list((home / "Downloads").iterdir()) == []

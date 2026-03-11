#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update service tests."""

from __future__ import annotations

import hashlib
from pathlib import Path


def test_launcher_settings_persist_update_proxy_config(tmp_path: Path):
    from launcher.settings import LauncherSettings, LauncherSettingsStore
    from launcher.update_service import ProxyConfig

    settings_path = tmp_path / "ui_settings.json"
    store = LauncherSettingsStore(settings_path)
    store.save(
        LauncherSettings(
            update_repo="akane/ferrum-bot",
            update_proxy=ProxyConfig(
                enabled=True,
                scheme="socks5",
                host="127.0.0.1",
                port=7890,
                username="alice",
                password="secret",
            ),
        )
    )

    loaded = store.load()
    assert loaded.update_repo == "akane/ferrum-bot"
    assert loaded.update_proxy.enabled is True
    assert loaded.update_proxy.scheme == "socks5"
    assert loaded.update_proxy.host == "127.0.0.1"
    assert loaded.update_proxy.port == 7890
    assert loaded.update_proxy.username == "alice"
    assert loaded.update_proxy.password == "secret"


def test_build_requests_proxies_for_http_proxy():
    from launcher.update_service import ProxyConfig, build_requests_proxies

    proxies = build_requests_proxies(
        ProxyConfig(enabled=True, scheme="http", host="proxy.local", port=8080)
    )

    assert proxies == {
        "http": "http://proxy.local:8080",
        "https": "http://proxy.local:8080",
    }


def test_build_requests_proxies_for_socks5_with_credentials():
    from launcher.update_service import ProxyConfig, build_requests_proxies

    proxies = build_requests_proxies(
        ProxyConfig(
            enabled=True,
            scheme="socks5",
            host="127.0.0.1",
            port=1080,
            username="alice",
            password="secret",
        )
    )

    assert proxies == {
        "http": "socks5://alice:secret@127.0.0.1:1080",
        "https": "socks5://alice:secret@127.0.0.1:1080",
    }


def test_fetch_latest_release_parses_release_payload(monkeypatch):
    from launcher.update_service import GitHubUpdateService

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "tag_name": "v1.0.04",
                "html_url": "https://github.com/example/ferrum/releases/tag/v1.0.04",
                "body": "Bug fixes",
                "published_at": "2026-03-11T10:00:00Z",
                "assets": [
                    {
                        "name": "FerrumBot-v1.0.04-portable.zip",
                        "browser_download_url": "https://example.com/FerrumBot-v1.0.04-portable.zip",
                        "size": 2048,
                        "digest": "sha256:abcd",
                    }
                ],
            }

    class FakeSession:
        def get(self, url, headers=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["timeout"] = timeout
            return FakeResponse()

    service = GitHubUpdateService(
        repo="example/ferrum",
        current_version="1.0.03",
        session=FakeSession(),
    )

    release = service.fetch_latest_release()

    assert captured["url"].endswith("/repos/example/ferrum/releases/latest")
    assert captured["headers"]["Accept"] == "application/vnd.github+json"
    assert release.version == "1.0.04"
    assert release.tag_name == "v1.0.04"
    assert release.is_newer is True
    assert release.assets[0].name == "FerrumBot-v1.0.04-portable.zip"
    assert release.assets[0].download_url == "https://example.com/FerrumBot-v1.0.04-portable.zip"
    assert release.assets[0].sha256 == "abcd"


def test_fetch_latest_release_uses_proxies_from_config(monkeypatch):
    from launcher.update_service import GitHubUpdateService, ProxyConfig

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "tag_name": "v1.0.03",
                "html_url": "https://github.com/example/ferrum/releases/tag/v1.0.03",
                "body": "",
                "published_at": "2026-03-11T10:00:00Z",
                "assets": [],
            }

    class FakeSession:
        def __init__(self):
            self.proxies = {}

        def get(self, url, headers=None, timeout=None):
            return FakeResponse()

    session = FakeSession()
    service = GitHubUpdateService(
        repo="example/ferrum",
        current_version="1.0.03",
        proxy=ProxyConfig(enabled=True, scheme="http", host="proxy.local", port=8080),
        session=session,
    )

    service.fetch_latest_release()

    assert session.proxies == {
        "http": "http://proxy.local:8080",
        "https": "http://proxy.local:8080",
    }


def test_download_release_asset_streams_zip_to_target(tmp_path: Path):
    from launcher.update_service import GitHubUpdateService, ReleaseAsset

    class FakeResponse:
        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size=8192):
            yield b"abc"
            yield b"123"

    class FakeSession:
        def __init__(self):
            self.proxies = {}
            self.calls = []

        def get(self, url, headers=None, timeout=None, stream=False):
            self.calls.append((url, timeout, stream))
            return FakeResponse()

    session = FakeSession()
    service = GitHubUpdateService(
        repo="example/ferrum",
        current_version="1.0.03",
        session=session,
    )

    target = service.download_release_asset(
        ReleaseAsset(
            name="FerrumBot-v1.0.04-portable.zip",
            download_url="https://example.com/FerrumBot-v1.0.04-portable.zip",
        ),
        tmp_path,
    )

    assert target.read_bytes() == b"abc123"
    assert session.calls == [("https://example.com/FerrumBot-v1.0.04-portable.zip", 30, True)]


def test_fetch_latest_release_rejects_prerelease_payload():
    from launcher.update_service import GitHubUpdateService

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "tag_name": "v1.0.04-beta.1",
                "prerelease": True,
                "html_url": "https://github.com/example/ferrum/releases/tag/v1.0.04-beta.1",
                "body": "preview",
                "published_at": "2026-03-11T10:00:00Z",
                "assets": [],
            }

    class FakeSession:
        def __init__(self):
            self.proxies = {}

        def get(self, url, headers=None, timeout=None):
            return FakeResponse()

    service = GitHubUpdateService(repo="example/ferrum", current_version="1.0.03", session=FakeSession())

    release = service.fetch_latest_release()

    assert release.is_prerelease is True
    assert release.is_newer is False


def test_select_release_asset_prefers_exact_portable_name():
    from launcher.update_service import select_release_asset

    asset = select_release_asset(
        {
            "tag_name": "v1.0.04",
            "assets": [
                {"name": "FerrumBot-v1.0.04-debug.zip", "download_url": "https://example.com/debug.zip"},
                {"name": "FerrumBot-v1.0.04-portable.zip", "download_url": "https://example.com/portable.zip"},
            ],
        }
    )

    assert asset.name == "FerrumBot-v1.0.04-portable.zip"


def test_select_release_asset_rejects_ambiguous_zip_assets():
    from launcher.update_service import select_release_asset

    try:
        select_release_asset(
            {
                "tag_name": "v1.0.04",
                "assets": [
                    {"name": "client-a.zip", "download_url": "https://example.com/a.zip"},
                    {"name": "client-b.zip", "download_url": "https://example.com/b.zip"},
                ],
            }
        )
    except ValueError as exc:
        assert "ambiguous" in str(exc).lower()
    else:  # pragma: no cover - red path guard
        raise AssertionError("expected ambiguous asset selection to fail")


def test_parse_sha256sums_updates_matching_asset_hash():
    from launcher.update_service import ReleaseAsset, parse_sha256sums_asset

    portable = ReleaseAsset(name="FerrumBot-v1.0.04-portable.zip", download_url="https://example.com/portable.zip")
    checksum_asset = ReleaseAsset(name="SHA256SUMS.txt", download_url="https://example.com/SHA256SUMS.txt")

    updated = parse_sha256sums_asset(
        assets=[portable, checksum_asset],
        checksum_text="deadbeef  FerrumBot-v1.0.04-portable.zip\n",
    )

    assert updated[0].sha256 == "deadbeef"


def test_verify_file_sha256_accepts_matching_file(tmp_path: Path):
    from launcher.update_service import verify_file_sha256

    payload = b"portable-update"
    file_path = tmp_path / "FerrumBot-v1.0.04-portable.zip"
    file_path.write_bytes(payload)

    verify_file_sha256(file_path, hashlib.sha256(payload).hexdigest())


def test_verify_file_sha256_rejects_mismatched_file(tmp_path: Path):
    from launcher.update_service import verify_file_sha256

    file_path = tmp_path / "FerrumBot-v1.0.04-portable.zip"
    file_path.write_bytes(b"portable-update")

    try:
        verify_file_sha256(file_path, "deadbeef")
    except ValueError as exc:
        assert "sha256" in str(exc).lower()
    else:  # pragma: no cover - red path guard
        raise AssertionError("expected sha256 mismatch to fail")


def test_expected_release_asset_name_uses_version_tag():
    from launcher.update_service import expected_release_asset_name

    assert expected_release_asset_name("v1.0.04") == "FerrumBot-v1.0.04-portable.zip"


def test_validate_release_metadata_accepts_stable_release_with_verified_asset():
    from launcher.update_service import validate_release_metadata

    issues = validate_release_metadata(
        {
            "tag_name": "v1.0.04",
            "is_prerelease": False,
            "assets": [
                {
                    "name": "FerrumBot-v1.0.04-portable.zip",
                    "download_url": "https://example.com/FerrumBot-v1.0.04-portable.zip",
                    "sha256": "deadbeef",
                }
            ],
        }
    )

    assert issues == []


def test_validate_release_metadata_reports_missing_verified_asset():
    from launcher.update_service import validate_release_metadata

    issues = validate_release_metadata(
        {
            "tag_name": "v1.0.04",
            "is_prerelease": False,
            "assets": [
                {
                    "name": "client.zip",
                    "download_url": "https://example.com/client.zip",
                    "sha256": "",
                }
            ],
        }
    )

    assert any("FerrumBot-v1.0.04-portable.zip" in issue for issue in issues)
    assert any("SHA-256" in issue for issue in issues)

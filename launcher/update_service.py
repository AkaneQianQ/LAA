#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub release update helpers for the launcher."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote


DEFAULT_UPDATE_REPO = "AkaneQianQ/LAA"
LEGACY_UPDATE_REPOS = {"AkaneGod/FerrumBot"}
GITHUB_API_BASE = "https://api.github.com"
RELEASE_PRODUCT_NAME = "LAA"
PORTABLE_ASSET_TEMPLATE = RELEASE_PRODUCT_NAME + "-{tag_name}-portable.zip"
SHA256SUMS_NAME = "SHA256SUMS.txt"


@dataclass(frozen=True)
class ProxyConfig:
    enabled: bool = False
    scheme: str = "http"
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    size: int = 0
    sha256: str = ""


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag_name: str
    published_at: str
    html_url: str
    body: str = ""
    assets: list[ReleaseAsset] = field(default_factory=list)
    is_newer: bool = False
    is_prerelease: bool = False


def build_requests_proxies(proxy: ProxyConfig | None) -> dict[str, str]:
    if proxy is None or not proxy.enabled or not proxy.host or int(proxy.port) <= 0:
        return {}

    scheme = "socks5" if str(proxy.scheme).lower() == "socks5" else "http"
    auth = ""
    if proxy.username:
        auth = quote(proxy.username, safe="")
        if proxy.password:
            auth += f":{quote(proxy.password, safe='')}"
        auth += "@"
    endpoint = f"{scheme}://{auth}{proxy.host}:{int(proxy.port)}"
    return {"http": endpoint, "https": endpoint}


def normalize_version(value: str) -> str:
    return str(value).strip().lstrip("vV")


def expected_release_asset_name(tag_name: str) -> str:
    return PORTABLE_ASSET_TEMPLATE.format(tag_name=str(tag_name).strip())


def is_remote_version_newer(current_version: str, remote_version: str) -> bool:
    return _version_key(normalize_version(remote_version)) > _version_key(normalize_version(current_version))


def _version_key(value: str) -> tuple[int, ...]:
    parts = []
    for piece in str(value).split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            digits = "".join(ch for ch in piece if ch.isdigit())
            parts.append(int(digits) if digits else 0)
    return tuple(parts)


class GitHubUpdateService:
    """Query GitHub releases and prepare update metadata."""

    def __init__(
        self,
        repo: str,
        current_version: str,
        proxy: ProxyConfig | None = None,
        session=None,
        api_base: str = GITHUB_API_BASE,
    ) -> None:
        self.repo = str(repo).strip()
        self.current_version = normalize_version(current_version)
        self.proxy = proxy or ProxyConfig()
        self.api_base = api_base.rstrip("/")
        self.session = session or self._create_session()
        proxies = build_requests_proxies(self.proxy)
        if proxies:
            self.session.proxies.update(proxies)

    def fetch_latest_release(self) -> ReleaseInfo:
        try:
            response = self.session.get(
                f"{self.api_base}/repos/{self.repo}/releases/latest",
                headers={
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                timeout=15,
            )
            response.raise_for_status()
        except Exception as exc:
            if not self._is_github_rate_limit_error(exc):
                raise
            return self._fetch_latest_release_from_public_page()

        payload = response.json()
        return self._build_release_info_from_api_payload(payload)

    def download_release_asset(self, asset: ReleaseAsset, target_dir: str | Path) -> Path:
        target_path = Path(target_dir) / asset.name
        target_path.parent.mkdir(parents=True, exist_ok=True)
        response = self.session.get(asset.download_url, timeout=30, stream=True)
        response.raise_for_status()
        with target_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    handle.write(chunk)
        return target_path

    @staticmethod
    def _parse_asset(payload: dict) -> ReleaseAsset:
        digest = str(payload.get("digest", "")).strip()
        if digest.lower().startswith("sha256:"):
            digest = digest.split(":", 1)[1]
        return ReleaseAsset(
            name=str(payload.get("name", "")),
            download_url=str(payload.get("browser_download_url", "")),
            size=int(payload.get("size", 0) or 0),
            sha256=digest,
        )

    def _hydrate_asset_hashes(self, assets: list[ReleaseAsset]) -> list[ReleaseAsset]:
        if any(asset.sha256 for asset in assets):
            return assets
        checksum_asset = next((asset for asset in assets if asset.name == SHA256SUMS_NAME), None)
        if checksum_asset is None:
            return assets
        try:
            response = self.session.get(checksum_asset.download_url, timeout=15)
            response.raise_for_status()
            checksum_text = response.text
        except Exception:
            return assets
        return parse_sha256sums_asset(assets, checksum_text)

    def _build_release_info_from_api_payload(self, payload: dict) -> ReleaseInfo:
        tag_name = str(payload.get("tag_name", "")).strip()
        version = normalize_version(tag_name)
        assets = [self._parse_asset(item) for item in payload.get("assets", []) if isinstance(item, dict)]
        assets = self._hydrate_asset_hashes(assets)
        is_prerelease = bool(payload.get("prerelease", False))
        return ReleaseInfo(
            version=version,
            tag_name=tag_name,
            published_at=str(payload.get("published_at", "")),
            html_url=str(payload.get("html_url", "")),
            body=str(payload.get("body", "")),
            assets=assets,
            is_newer=(not is_prerelease) and is_remote_version_newer(self.current_version, version),
            is_prerelease=is_prerelease,
        )

    def _fetch_latest_release_from_public_page(self) -> ReleaseInfo:
        response = self.session.get(
            f"https://github.com/{self.repo}/releases/latest",
            timeout=15,
        )
        response.raise_for_status()
        html_url = str(getattr(response, "url", "") or "").strip()
        tag_name = self._extract_tag_name_from_release_url(html_url)
        version = normalize_version(tag_name)
        assets = self._hydrate_asset_hashes(
            [
                ReleaseAsset(
                    name=expected_release_asset_name(tag_name),
                    download_url=f"https://github.com/{self.repo}/releases/download/{tag_name}/{expected_release_asset_name(tag_name)}",
                ),
                ReleaseAsset(
                    name=SHA256SUMS_NAME,
                    download_url=f"https://github.com/{self.repo}/releases/download/{tag_name}/{SHA256SUMS_NAME}",
                ),
            ]
        )
        return ReleaseInfo(
            version=version,
            tag_name=tag_name,
            published_at="",
            html_url=html_url,
            body="",
            assets=assets,
            is_newer=is_remote_version_newer(self.current_version, version),
            is_prerelease=False,
        )

    @staticmethod
    def _extract_tag_name_from_release_url(url: str) -> str:
        match = re.search(r"/releases/tag/([^/?#]+)", str(url))
        if not match:
            raise ValueError(f"unable to determine release tag from url: {url}")
        return match.group(1).strip()

    @staticmethod
    def _is_github_rate_limit_error(exc: Exception) -> bool:
        response = getattr(exc, "response", None)
        if response is None:
            return False
        if int(getattr(response, "status_code", 0) or 0) != 403:
            return False
        message = f"{exc} {getattr(response, 'text', '')}".lower()
        return "rate limit" in message

    @staticmethod
    def _create_session():
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - runtime dependency path
            raise RuntimeError("requests is required for update checks") from exc
        return requests.Session()


def select_release_asset(release_info: dict) -> ReleaseAsset:
    assets = []
    for item in release_info.get("assets", []):
        if not isinstance(item, dict):
            continue
        assets.append(
            ReleaseAsset(
                name=str(item.get("name", "")),
                download_url=str(item.get("download_url", "")),
                size=int(item.get("size", 0) or 0),
                sha256=str(item.get("sha256", "")),
            )
        )
    tag_name = str(release_info.get("tag_name", "")).strip()
    if not assets:
        raise ValueError("release has no downloadable assets")
    exact_name = expected_release_asset_name(tag_name) if tag_name else ""
    exact_matches = [asset for asset in assets if asset.name == exact_name]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise ValueError("ambiguous exact portable assets in release")
    preferred = [
        asset
        for asset in assets
        if asset.name.lower().endswith(".zip") and RELEASE_PRODUCT_NAME.lower() in asset.name.lower()
    ]
    if len(preferred) == 1:
        return preferred[0]
    if len(preferred) > 1:
        raise ValueError(f"ambiguous {RELEASE_PRODUCT_NAME} zip assets in release")
    zip_assets = [asset for asset in assets if asset.name.lower().endswith(".zip")]
    if zip_assets:
        if len(zip_assets) > 1:
            raise ValueError("ambiguous zip assets in release")
        return zip_assets[0]
    return assets[0]


def validate_release_metadata(release_info: dict) -> list[str]:
    issues: list[str] = []
    tag_name = str(release_info.get("tag_name", "")).strip()
    expected_asset = expected_release_asset_name(tag_name) if tag_name else ""
    if bool(release_info.get("is_prerelease", False)):
        issues.append("Prerelease builds are not eligible for automatic updates.")
    assets = [asset for asset in release_info.get("assets", []) if isinstance(asset, dict)]
    matching = [asset for asset in assets if str(asset.get("name", "")).strip() == expected_asset]
    if not matching:
        issues.append(f"Missing required release asset: {expected_asset}")
        issues.append(f"Missing SHA-256 verification for asset: {expected_asset}")
    elif not str(matching[0].get("sha256", "")).strip():
        issues.append(f"Missing SHA-256 verification for asset: {expected_asset}")
    return issues


def download_and_apply_release(
    repo: str,
    current_version: str,
    proxy: ProxyConfig,
    release_info: dict,
    install_dir: str,
    restart_executable: str,
    restart_args: list[str] | None = None,
    session=None,
) -> dict:
    service = GitHubUpdateService(
        repo=repo,
        current_version=current_version,
        proxy=proxy,
        session=session,
    )
    asset = select_release_asset(release_info)
    download_dir = Path(tempfile.mkdtemp(prefix=f"{RELEASE_PRODUCT_NAME.lower()}-update-"))
    download_path = service.download_release_asset(asset, download_dir)
    if not asset.sha256:
        raise ValueError("release asset is missing sha256 verification data")
    verify_file_sha256(download_path, asset.sha256)
    script_path = write_windows_updater_script(download_dir)
    launch_windows_updater(
        script_path=script_path,
        zip_path=download_path,
        install_dir=install_dir,
        restart_executable=restart_executable,
        restart_args=restart_args or [],
    )
    return {
        "download_path": str(download_path),
        "script_path": str(script_path),
        "asset_name": asset.name,
        "sha256": asset.sha256,
    }


def parse_sha256sums_asset(assets: list[ReleaseAsset], checksum_text: str) -> list[ReleaseAsset]:
    checksum_map: dict[str, str] = {}
    for raw_line in checksum_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        checksum = parts[0].strip()
        filename = parts[-1].strip().lstrip("*")
        checksum_map[filename] = checksum
    return [
        ReleaseAsset(
            name=asset.name,
            download_url=asset.download_url,
            size=asset.size,
            sha256=asset.sha256 or checksum_map.get(asset.name, ""),
        )
        for asset in assets
    ]


def verify_file_sha256(file_path: str | Path, expected_sha256: str) -> None:
    expected = str(expected_sha256).strip().lower()
    if not expected:
        raise ValueError("missing sha256 for verification")
    digest = hashlib.sha256(Path(file_path).read_bytes()).hexdigest().lower()
    if digest != expected:
        raise ValueError(f"sha256 mismatch for {Path(file_path).name}")


def write_windows_updater_script(target_dir: str | Path) -> Path:
    script_path = Path(target_dir) / "apply_update.ps1"
    script_path.write_text(
        "\n".join(
            [
                "param(",
                "    [string]$ZipPath,",
                "    [string]$InstallDir,",
                "    [string]$RestartFile,",
                "    [string]$RestartArgsJson,",
                "    [int]$ProcessIdToWait = 0",
                ")",
                '$ErrorActionPreference = "Stop"',
                "if ($ProcessIdToWait -gt 0) {",
                "    Wait-Process -Id $ProcessIdToWait -ErrorAction SilentlyContinue",
                "}",
                f'$stageDir = Join-Path ([System.IO.Path]::GetTempPath()) ("{RELEASE_PRODUCT_NAME}-apply-" + [guid]::NewGuid().ToString())',
                "New-Item -ItemType Directory -Force -Path $stageDir | Out-Null",
                "Expand-Archive -LiteralPath $ZipPath -DestinationPath $stageDir -Force",
                "$items = Get-ChildItem -LiteralPath $stageDir",
                "if ($items.Count -eq 1 -and $items[0].PSIsContainer) {",
                "    $sourceDir = $items[0].FullName",
                "} else {",
                "    $sourceDir = $stageDir",
                "}",
                "robocopy $sourceDir $InstallDir /E /R:2 /W:1 /NFL /NDL /NJH /NJS /NP | Out-Null",
                "$restartArgs = @()",
                "if ($RestartArgsJson) {",
                "    $restartArgs = ConvertFrom-Json -InputObject $RestartArgsJson",
                "}",
                "Start-Process -FilePath $RestartFile -ArgumentList $restartArgs -WorkingDirectory $InstallDir",
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def launch_windows_updater(
    script_path: str | Path,
    zip_path: str | Path,
    install_dir: str,
    restart_executable: str,
    restart_args: list[str],
    process_id: int | None = None,
) -> subprocess.Popen:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-WindowStyle",
        "Hidden",
        "-File",
        str(script_path),
        "-ZipPath",
        str(zip_path),
        "-InstallDir",
        str(install_dir),
        "-RestartFile",
        str(restart_executable),
        "-RestartArgsJson",
        json.dumps(list(restart_args), ensure_ascii=False),
        "-ProcessIdToWait",
        str(int(process_id or 0)),
    ]
    return subprocess.Popen(command)

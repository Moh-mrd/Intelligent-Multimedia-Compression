"""Backend client and formatting helpers.

Talks to the existing FastAPI service (GET /health, POST /api/image, POST /api/video and the
file URLs returned in `files`). It has no Streamlit dependency and never invents values.
"""

from __future__ import annotations

import re

import requests

HEALTH_TIMEOUT_S = 15
UPLOAD_TIMEOUT_S = 900      # compression can take several minutes
DOWNLOAD_TIMEOUT_S = 600


class ApiError(Exception):
    """A problem talking to the backend, with a message that is safe to show to the user."""


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------
def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def format_size(n) -> str:
    if not _is_num(n):
        return "—"
    return f"{n / 1024:,.1f} KB" if n < 1024**2 else f"{n / 1024**2:,.2f} MB"


def fmt_num(value, spec: str, suffix: str = "") -> str:
    """Format an optional numeric value. Missing -> em dash; non-numeric -> shown as received."""
    if value is None or isinstance(value, bool):
        return "—"
    try:
        return f"{float(value):{spec}}{suffix}"
    except (TypeError, ValueError):
        return str(value)


def space_saved(res: dict):
    """Percentage saved, calculated from the API's byte counts (None if unavailable)."""
    orig, comp = res.get("original_bytes"), res.get("compressed_bytes")
    if not _is_num(orig) or not _is_num(comp) or orig <= 0:
        return None
    return (1 - comp / orig) * 100


def compression_ratio(res: dict):
    """original / compressed, calculated from the byte counts (None if unavailable)."""
    orig, comp = res.get("original_bytes"), res.get("compressed_bytes")
    if not _is_num(orig) or not _is_num(comp) or orig <= 0 or comp <= 0:
        return None
    return orig / comp


def normalize_api_url(raw: str) -> str:
    url = (raw or "").strip().rstrip("/")
    if url and not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


# ---------------------------------------------------------------------------
# HTTP calls
# ---------------------------------------------------------------------------
def _error_message(resp: requests.Response) -> str:
    try:
        body = resp.json()
        if isinstance(body, dict) and body.get("detail"):
            return str(body["detail"])
    except ValueError:
        pass
    text = (resp.text or "").strip()
    if text[:15].lower().startswith(("<!doctype", "<html")):
        return (
            f"The server returned an error page (HTTP {resp.status_code}). "
            "The backend notebook may have stopped, or the tunnel URL may have expired."
        )
    return text[:300] or f"The server returned HTTP {resp.status_code}."


def api_health(api_url: str) -> dict:
    """GET /health"""
    if not api_url:
        raise ApiError("Enter the API URL first.")
    try:
        r = requests.get(f"{api_url}/health", timeout=HEALTH_TIMEOUT_S)
    except requests.exceptions.Timeout as exc:
        raise ApiError("The connection test timed out. Check that the notebook is still running.") from exc
    except requests.exceptions.RequestException as exc:
        raise ApiError(
            "Could not reach the API. Check that the notebook is still running "
            "and that the URL is the latest one (it changes every session)."
        ) from exc
    if not r.ok:
        raise ApiError(_error_message(r))
    try:
        info = r.json()
    except ValueError as exc:
        raise ApiError("The server replied, but not with a valid health report. Check the URL.") from exc
    return info if isinstance(info, dict) else {}


def api_compress(api_url: str, path: str, uploaded, params: dict, max_mb: int) -> tuple[bytes, dict]:
    """POST an uploaded file to /api/image or /api/video. Returns (original bytes, response JSON)."""
    if not api_url:
        raise ApiError("Enter the API URL first.")
    raw = uploaded.getvalue()
    if len(raw) > max_mb * 1024**2:
        raise ApiError(f"The file is larger than {max_mb} MB. Use a smaller file.")
    try:
        r = requests.post(
            f"{api_url}{path}",
            data=params,
            timeout=UPLOAD_TIMEOUT_S,
            files={"file": (uploaded.name, raw, uploaded.type or "application/octet-stream")},
        )
    except requests.exceptions.Timeout as exc:
        raise ApiError("The request timed out. Try a shorter video or a smaller file.") from exc
    except requests.exceptions.RequestException as exc:
        raise ApiError(
            "Could not reach the API. Check that the notebook is still running and the URL is current."
        ) from exc
    if r.status_code in (404, 405, 501):
        raise ApiError(
            f"This backend does not provide {path}, so this feature is unavailable on the current server."
        )
    if not r.ok:
        raise ApiError(_error_message(r))
    try:
        res = r.json()
    except ValueError as exc:
        raise ApiError("The API returned an unexpected response (not JSON).") from exc
    if not isinstance(res, dict):
        raise ApiError("The API returned an unexpected response.")
    return raw, res


def result_url(res: dict, key: str) -> str:
    files = res.get("files")
    url = files.get(key) if isinstance(files, dict) else None
    if not url or not isinstance(url, str):
        raise ApiError(f"The API response did not include a download link (files.{key}).")
    return url


def fetch_file(api_url: str, rel: str) -> bytes:
    """GET a file URL returned by the API (relative to the API URL)."""
    try:
        r = requests.get(f"{api_url}/{rel.lstrip('/')}", timeout=DOWNLOAD_TIMEOUT_S)
    except requests.exceptions.RequestException as exc:
        raise ApiError("Compression finished, but the output file could not be downloaded.") from exc
    if not r.ok:
        raise ApiError(f"The output file could not be downloaded (HTTP {r.status_code}).")
    return r.content

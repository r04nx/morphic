"""
agents/github_source.py
-----------------------
Fetches actual Java source files from the HackathonPS chaos backend repo:
  https://github.com/Sparky17561/HackathonPS

Public API:
    fetch_java_source(class_name: str) -> dict | None
        Returns {"class_name", "file_path", "github_url", "line_count", "source"} or None.

Strategy:
    1. Try raw.githubusercontent.com  — works for public repos, no rate-limit.
    2. Fall back to GitHub REST API with GITHUB_TOKEN if raw returns non-200.

All results are cached in-process so repeated RCA calls for the same class
don't make duplicate network requests.
"""

import logging
import re
from typing import Optional

import requests

from config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Repo constants
# ---------------------------------------------------------------------------

_OWNER    = "Sparky17561"
_REPO     = "HackathonPS"
_BRANCH   = "main"
_RAW_BASE = f"https://raw.githubusercontent.com/{_OWNER}/{_REPO}/{_BRANCH}"
_API_BASE = f"https://api.github.com/repos/{_OWNER}/{_REPO}"

# ---------------------------------------------------------------------------
# File index — every Java class in the repo, keyed by simple class name.
# We know the full tree from the initial repo scan.
# ---------------------------------------------------------------------------

_CLASS_INDEX: dict[str, str] = {
    "BackendApplication":  "src/main/java/com/hacksys/backend/BackendApplication.java",
    "AppConfig":           "src/main/java/com/hacksys/backend/config/AppConfig.java",
    "AsyncConfig":         "src/main/java/com/hacksys/backend/config/AsyncConfig.java",
    "HealthController":    "src/main/java/com/hacksys/backend/controller/HealthController.java",
    "InventoryController": "src/main/java/com/hacksys/backend/controller/InventoryController.java",
    "LogController":       "src/main/java/com/hacksys/backend/controller/LogController.java",
    "OrderController":     "src/main/java/com/hacksys/backend/controller/OrderController.java",
    "PaymentController":   "src/main/java/com/hacksys/backend/controller/PaymentController.java",
    "InventoryItem":       "src/main/java/com/hacksys/backend/model/InventoryItem.java",
    "Order":               "src/main/java/com/hacksys/backend/model/Order.java",
    "Payment":             "src/main/java/com/hacksys/backend/model/Payment.java",
    "ChaosScheduler":      "src/main/java/com/hacksys/backend/scheduler/ChaosScheduler.java",
    "InventoryService":    "src/main/java/com/hacksys/backend/service/InventoryService.java",
    "OrderService":        "src/main/java/com/hacksys/backend/service/OrderService.java",
    "PaymentService":      "src/main/java/com/hacksys/backend/service/PaymentService.java",
    "LogStore":            "src/main/java/com/hacksys/backend/util/LogStore.java",
    "TraceContext":        "src/main/java/com/hacksys/backend/util/TraceContext.java",
}

# In-process cache: class_name -> result dict
_CACHE: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _api_headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    if Config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {Config.GITHUB_TOKEN}"
    return headers


def _resolve_path(class_name: str) -> Optional[str]:
    """
    Map a class name to a repo-relative file path.
    Accepts simple names  ("PaymentService")
    and fully-qualified names ("com.hacksys.backend.service.PaymentService").
    """
    simple = class_name.split(".")[-1].strip()
    return _CLASS_INDEX.get(simple)


def _download_raw(path: str) -> Optional[str]:
    """Download file via raw.githubusercontent.com (no auth needed for public repos)."""
    url = f"{_RAW_BASE}/{path}"
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            logger.debug("GitHub raw fetch OK: %s", path)
            return resp.text
        if resp.status_code == 404:
            logger.warning("GitHub raw 404: %s", path)
            return None
        logger.debug("GitHub raw returned %d for %s", resp.status_code, path)
    except requests.RequestException as exc:
        logger.debug("GitHub raw request failed for %s: %s", path, exc)
    return None


def _download_api(path: str) -> Optional[str]:
    """Download file via GitHub REST API (requires GITHUB_TOKEN for private repos)."""
    import base64
    if not Config.GITHUB_TOKEN:
        logger.debug("No GITHUB_TOKEN — skipping REST API fallback for %s", path)
        return None
    url = f"{_API_BASE}/contents/{path}"
    try:
        resp = requests.get(url, headers=_api_headers(), params={"ref": _BRANCH}, timeout=15)
        if resp.status_code == 404:
            logger.warning("GitHub API 404: %s", path)
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content", "")
    except Exception as exc:
        logger.warning("GitHub REST API fetch failed for %s: %s", path, exc)
    return None


def _add_line_numbers(source: str) -> str:
    """Add 1-based line numbers: '  42 | public void processPayment(...)'"""
    lines = source.splitlines()
    width = len(str(len(lines)))
    return "\n".join(
        f"{str(i + 1).rjust(width)} | {line}"
        for i, line in enumerate(lines)
    )

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_java_source(class_name: str) -> Optional[dict]:
    """
    Fetch the Java source for a given class name.

    Args:
        class_name: Simple ("PaymentService") or FQN ("com.hacksys.backend.service.PaymentService").

    Returns:
        {
            "class_name":   str,   # simple class name
            "file_path":    str,   # repo-relative path
            "github_url":   str,   # browser URL to file on GitHub
            "line_count":   int,
            "source":       str,   # raw source text
            "numbered_src": str,   # source with line numbers prefix
        }
        or None if the class is unknown or fetch fails.
    """
    simple = class_name.split(".")[-1].strip()

    # Cache hit
    if simple in _CACHE:
        logger.debug("GitHub source cache hit: %s", simple)
        return _CACHE[simple]

    path = _resolve_path(simple)
    if not path:
        logger.info("No known path for class '%s' — not in HackathonPS index", simple)
        return None

    # Try raw URL first, then REST API
    raw_source = _download_raw(path) or _download_api(path)
    if raw_source is None:
        logger.warning("Could not download source for %s", simple)
        return None

    result = {
        "class_name":   simple,
        "file_path":    path,
        "github_url":   f"https://github.com/{_OWNER}/{_REPO}/blob/{_BRANCH}/{path}",
        "line_count":   raw_source.count("\n") + 1,
        "source":       raw_source,
        "numbered_src": _add_line_numbers(raw_source),
    }
    _CACHE[simple] = result
    logger.info("Fetched GitHub source: %s (%d lines)", simple, result["line_count"])
    return result


def extract_class_name_from_logs(log_slice: list[dict]) -> Optional[str]:
    """
    Extract the most relevant Java class name from a list of log entries.

    Checks these fields in priority order:
      1. "class"           — direct class field in the log JSON
      2. "logger"          — logger name (usually the FQN of the class)
      3. "exception_class" — exception class name
      4. "message"         — free-text scan for known class names

    Returns the first match found, or None.
    """
    known = set(_CLASS_INDEX.keys())

    for entry in log_slice:
        # raw_log may be a nested dict
        raw = entry.get("raw") or {}
        if isinstance(raw, str):
            import json as _json
            try:
                raw = _json.loads(raw)
            except Exception:
                raw = {}

        # Priority 1: explicit "class" field
        for source_dict in (entry, raw):
            class_val = source_dict.get("class") or source_dict.get("className") or ""
            if class_val:
                simple = class_val.split(".")[-1].strip()
                if simple in known:
                    logger.debug("Class extracted from 'class' field: %s", simple)
                    return simple

        # Priority 2: logger name (usually FQN)
        for source_dict in (entry, raw):
            logger_val = source_dict.get("logger") or source_dict.get("loggerName") or ""
            if logger_val:
                simple = logger_val.split(".")[-1].strip()
                if simple in known:
                    logger.debug("Class extracted from logger field: %s", simple)
                    return simple

        # Priority 3: exception_class
        for source_dict in (entry, raw):
            exc_val = (
                source_dict.get("exception_class")
                or source_dict.get("exceptionClass")
                or source_dict.get("exception")
                or ""
            )
            if exc_val:
                simple = exc_val.split(".")[-1].strip().rstrip(":")
                if simple in known:
                    logger.debug("Class extracted from exception: %s", simple)
                    return simple

    # Priority 4: scan all string fields in all entries for known class names
    all_text = " ".join(
        str(v)
        for entry in log_slice
        for v in (list(entry.values()) + list((entry.get("raw") or {}).values() if isinstance(entry.get("raw"), dict) else []))
        if isinstance(v, str)
    )
    for name in ["PaymentService", "OrderService", "InventoryService",
                 "PaymentController", "OrderController", "InventoryController",
                 "ChaosScheduler", "AsyncConfig", "TraceContext", "LogStore"]:
        if name in all_text:
            logger.debug("Class extracted from free-text scan: %s", name)
            return name

    return None

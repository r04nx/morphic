"""
GitHub Source Fetcher
Fetches actual Java source files from the chaos backend repo
(https://github.com/Sparky17561/HackathonPS) to give Claude real code context.

Caches fetched files in-memory for the lifetime of the process so repeated
RCA calls on the same class don't burn GitHub API quota.
"""

import base64
import logging
import re
from typing import Optional

import requests

from config import Config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_OWNER = "Sparky17561"
_REPO_NAME  = "HackathonPS"
_REPO_REF   = "main"
_GITHUB_API = "https://api.github.com"

# Complete Java file index for this repo  (path → simple class name)
# Built once from the recursive tree we already know.
_KNOWN_FILES: dict[str, str] = {
    "src/main/java/com/hacksys/backend/BackendApplication.java":              "BackendApplication",
    "src/main/java/com/hacksys/backend/config/AppConfig.java":                "AppConfig",
    "src/main/java/com/hacksys/backend/config/AsyncConfig.java":              "AsyncConfig",
    "src/main/java/com/hacksys/backend/controller/HealthController.java":     "HealthController",
    "src/main/java/com/hacksys/backend/controller/InventoryController.java":  "InventoryController",
    "src/main/java/com/hacksys/backend/controller/LogController.java":        "LogController",
    "src/main/java/com/hacksys/backend/controller/OrderController.java":      "OrderController",
    "src/main/java/com/hacksys/backend/controller/PaymentController.java":    "PaymentController",
    "src/main/java/com/hacksys/backend/model/InventoryItem.java":             "InventoryItem",
    "src/main/java/com/hacksys/backend/model/Order.java":                     "Order",
    "src/main/java/com/hacksys/backend/model/Payment.java":                   "Payment",
    "src/main/java/com/hacksys/backend/scheduler/ChaosScheduler.java":        "ChaosScheduler",
    "src/main/java/com/hacksys/backend/service/InventoryService.java":        "InventoryService",
    "src/main/java/com/hacksys/backend/service/OrderService.java":            "OrderService",
    "src/main/java/com/hacksys/backend/service/PaymentService.java":          "PaymentService",
    "src/main/java/com/hacksys/backend/util/LogStore.java":                   "LogStore",
    "src/main/java/com/hacksys/backend/util/TraceContext.java":               "TraceContext",
}

# Reverse map: simple class name → file path
_CLASS_TO_PATH: dict[str, str] = {v: k for k, v in _KNOWN_FILES.items()}

# In-process cache: file path → (numbered source, raw source)
_CACHE: dict[str, tuple[str, str]] = {}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _auth_headers() -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if Config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {Config.GITHUB_TOKEN}"
    return headers


_RAW_BASE = "https://raw.githubusercontent.com"


def _fetch_file_raw(path: str) -> Optional[str]:
    """
    Fetch raw source for a repo-relative path.

    Strategy:
    1. Try raw.githubusercontent.com first — no auth needed, no rate limit for public repos.
    2. Fall back to GitHub REST API (uses GITHUB_TOKEN if set) for private repos.
    """
    # --- Primary: raw content URL ---
    raw_url = f"{_RAW_BASE}/{_REPO_OWNER}/{_REPO_NAME}/{_REPO_REF}/{path}"
    try:
        resp = requests.get(raw_url, timeout=15)
        if resp.status_code == 200:
            logger.debug("Fetched via raw URL: %s", path)
            return resp.text
        if resp.status_code == 404:
            logger.warning("GitHub source not found (raw): %s", path)
            return None
        # Non-200/404 — fall through to REST API
        logger.debug("Raw URL returned %d for %s — trying REST API", resp.status_code, path)
    except Exception as exc:
        logger.debug("Raw URL fetch failed for %s: %s — trying REST API", path, exc)

    # --- Fallback: REST API (authenticated) ---
    if not Config.GITHUB_TOKEN:
        logger.warning("No GITHUB_TOKEN set; cannot use REST API fallback for %s", path)
        return None

    api_url = f"{_GITHUB_API}/repos/{_REPO_OWNER}/{_REPO_NAME}/contents/{path}"
    try:
        resp = requests.get(
            api_url,
            headers=_auth_headers(),
            params={"ref": _REPO_REF},
            timeout=15,
        )
        if resp.status_code == 404:
            logger.warning("GitHub source not found (REST): %s", path)
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content", "")
    except Exception as exc:
        logger.warning("Failed to fetch GitHub source via REST %s: %s", path, exc)
        return None


def _add_line_numbers(source: str) -> str:
    """Prefix each line with its 1-based line number: '  42: public void ...'"""
    lines = source.splitlines()
    width = len(str(len(lines)))
    numbered = [f"{str(i + 1).rjust(width)}: {line}" for i, line in enumerate(lines)]
    return "\n".join(numbered)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_class_path(class_name: str) -> Optional[str]:
    """
    Given a simple class name (e.g. 'PaymentService') or a fully-qualified name
    (e.g. 'com.hacksys.backend.service.PaymentService'), return the repo-relative
    file path, or None if unknown.
    """
    # Try simple name first
    simple = class_name.split(".")[-1].replace(".java", "")
    if simple in _CLASS_TO_PATH:
        return _CLASS_TO_PATH[simple]

    # Try building a path from the FQN
    if "." in class_name:
        candidate = "src/main/java/" + class_name.replace(".", "/") + ".java"
        if candidate in _KNOWN_FILES:
            return candidate

    return None


def fetch_source(class_name: str) -> Optional[dict]:
    """
    Fetch the source of a Java class by name.

    Returns a dict:
    {
        "class_name":   str,
        "file_path":    str,
        "github_url":   str,
        "line_count":   int,
        "numbered_src": str,   ← ready for Claude prompt
        "raw_src":      str,
    }
    or None if the file cannot be fetched.
    """
    path = resolve_class_path(class_name)
    if not path:
        logger.info("No known source path for class '%s'", class_name)
        return None

    if path in _CACHE:
        numbered, raw = _CACHE[path]
        logger.debug("GitHub source cache hit: %s", path)
    else:
        raw = _fetch_file_raw(path)
        if raw is None:
            return None
        numbered = _add_line_numbers(raw)
        _CACHE[path] = (numbered, raw)
        logger.info("Fetched GitHub source: %s (%d lines)", path, raw.count("\n") + 1)

    github_url = (
        f"https://github.com/{_REPO_OWNER}/{_REPO_NAME}/blob/{_REPO_REF}/{path}"
    )
    return {
        "class_name":   class_name.split(".")[-1],
        "file_path":    path,
        "github_url":   github_url,
        "line_count":   raw.count("\n") + 1,
        "numbered_src": numbered,
        "raw_src":      raw,
    }


def extract_class_names_from_logs(log_slice: list[dict]) -> list[str]:
    """
    Scan log entries for Java class names and return unique matches ordered
    by relevance (most likely buggy class first).

    Looks in: message, exception, raw log fields.
    """
    text_parts: list[str] = []
    for entry in log_slice:
        for field in ("message", "exception", "error", "exception_class"):
            val = entry.get(field) or ""
            if val:
                text_parts.append(str(val))
        raw = entry.get("raw") or {}
        if isinstance(raw, dict):
            for field in ("logger", "class", "exception", "message", "error"):
                val = raw.get(field) or ""
                if val:
                    text_parts.append(str(val))

    combined = " ".join(text_parts)

    # Match known simple class names
    found: list[str] = []
    seen: set[str] = set()
    for simple_name in _CLASS_TO_PATH:
        if simple_name in combined and simple_name not in seen:
            seen.add(simple_name)
            found.append(simple_name)

    # Also try fully-qualified patterns: com.hacksys.backend.*.ClassName
    fqn_matches = re.findall(
        r"com\.hacksys\.backend(?:\.\w+)*\.([A-Z]\w+)", combined
    )
    for m in fqn_matches:
        if m not in seen and m in _CLASS_TO_PATH:
            seen.add(m)
            found.append(m)

    logger.debug("Class names extracted from logs: %s", found)
    return found


def fetch_sources_for_incident(
    log_slice: list[dict],
    triage_classification: str = "",
    max_files: int = 3,
) -> list[dict]:
    """
    Determine which Java source files are most relevant and fetch them.

    Priority:
    1. Classes explicitly mentioned in logs
    2. Heuristic based on triage classification (e.g. 'Payment' → PaymentService)

    Returns up to `max_files` source dicts.
    """
    candidates: list[str] = extract_class_names_from_logs(log_slice)

    # Heuristic fallback by classification keyword
    if not candidates:
        classification_lower = triage_classification.lower()
        if "payment" in classification_lower:
            candidates = ["PaymentService", "PaymentController"]
        elif "order" in classification_lower:
            candidates = ["OrderService", "OrderController"]
        elif "stock" in classification_lower or "inventory" in classification_lower:
            candidates = ["InventoryService", "InventoryController"]
        elif "async" in classification_lower or "mdc" in classification_lower or "trace" in classification_lower:
            candidates = ["AsyncConfig", "TraceContext", "ChaosScheduler"]
        else:
            candidates = ["OrderService", "PaymentService"]

    results: list[dict] = []
    for class_name in candidates[:max_files]:
        src = fetch_source(class_name)
        if src:
            results.append(src)

    logger.info(
        "Fetched %d source file(s) for RCA: %s",
        len(results),
        [r["class_name"] for r in results],
    )
    return results

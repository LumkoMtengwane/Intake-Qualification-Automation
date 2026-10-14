"""Shared helpers: env, config, logging, HTTP with retries. Standard library plus requests only."""
import json
import logging
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "state.json"


def load_env(path=ROOT / ".env"):
    """Load KEY=VALUE lines into os.environ without overriding real environment variables."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.split(" #")[0].strip())


def load_config():
    path = ROOT / "config.json"
    if not path.exists():
        raise SystemExit("config.json not found. Copy config.example.json to config.json and edit it.")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg["owner_email"] = os.environ.get("OWNER_EMAIL", cfg["owner_email"])
    return cfg


def require_env(*names):
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise SystemExit(f"Missing environment variables: {', '.join(missing)} (see .env.example)")


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def setup_logging():
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(ROOT / "logs" / "intake.log", encoding="utf-8"), logging.StreamHandler()],
    )
    return logging.getLogger("intake")


class ApiError(Exception):
    """Raised when an API call keeps failing. Message never includes secrets."""


def http(method, url, retries=3, backoff=2, **kwargs):
    """requests with retries and exponential backoff on 429, 5xx and network errors."""
    last = None
    for attempt in range(retries + 1):
        try:
            resp = requests.request(method, url, timeout=60, **kwargs)
            if resp.status_code < 400:
                return resp
            if resp.status_code not in (429, 500, 502, 503, 504, 529):
                raise ApiError(f"{method} {url.split('?')[0]} -> {resp.status_code}: {resp.text[:300]}")
            last = f"{resp.status_code}"
        except requests.RequestException as exc:
            last = type(exc).__name__
        if attempt < retries:
            time.sleep(backoff * (2 ** attempt))
    raise ApiError(f"{method} {url.split('?')[0]} failed after {retries + 1} attempts ({last})")

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class OpenClawSettings:
    enabled: bool
    endpoint: str
    endpoint_env: str
    provider: str
    model: str
    openai_api_key_env: str
    api_key_env: str
    timeout_seconds: int

    @classmethod
    def from_config(cls, cfg: dict[str, Any]) -> OpenClawSettings:
        oc = cfg.get("openclaw", {})
        return cls(
            enabled=bool(oc.get("enabled", False)),
            endpoint=str(oc.get("endpoint", "") or "").strip(),
            endpoint_env=str(oc.get("endpoint_env", "OPENCLAW_ENDPOINT")),
            provider=str(oc.get("provider", "openai")),
            model=str(oc.get("model", "gpt-5")),
            openai_api_key_env=str(oc.get("openai_api_key_env", "OPENAI_API_KEY")),
            api_key_env=str(oc.get("api_key_env", "OPENCLAW_API_KEY")),
            timeout_seconds=int(oc.get("timeout_seconds", 30)),
        )


def openclaw_available() -> tuple[bool, str]:
    try:
        openclaw = importlib.import_module("openclaw")

        version = getattr(openclaw, "__version__", "unknown")
        return True, str(version)
    except Exception as exc:
        # Compatibility shim for recent cmdop API rename.
        try:
            ce = importlib.import_module("cmdop.exceptions")
            if not hasattr(ce, "TimeoutError") and hasattr(ce, "ConnectionTimeoutError"):
                ce.TimeoutError = ce.ConnectionTimeoutError
                openclaw = importlib.import_module("openclaw")
                version = getattr(openclaw, "__version__", "unknown")
                return True, str(version)
        except Exception:
            pass
        return False, str(exc)


def healthcheck(settings: OpenClawSettings) -> dict[str, Any]:
    ok, version_or_error = openclaw_available()
    endpoint = settings.endpoint or str(os.getenv(settings.endpoint_env, "")).strip()
    openclaw_api_key_present = bool(os.getenv(settings.api_key_env))
    openai_api_key_present = bool(os.getenv(settings.openai_api_key_env))
    auth_ready = openclaw_api_key_present or openai_api_key_present
    report: dict[str, Any] = {
        "import_ok": ok,
        "openclaw_version": version_or_error if ok else None,
        "import_error": None if ok else version_or_error,
        "enabled": settings.enabled,
        "provider": settings.provider,
        "model": settings.model,
        "endpoint": endpoint,
        "endpoint_ok": None,
        "openclaw_api_key_present": openclaw_api_key_present,
        "openai_api_key_present": openai_api_key_present,
        "auth_ready": auth_ready,
    }

    if endpoint:
        url = endpoint.rstrip("/") + "/health"
        try:
            r = requests.get(url, timeout=settings.timeout_seconds)
            report["endpoint_ok"] = bool(r.ok)
            report["endpoint_status"] = r.status_code
        except Exception as exc:
            report["endpoint_ok"] = False
            report["endpoint_error"] = str(exc)

    return report

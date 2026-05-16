"""
wso2_service.py
---------------

Pushes governance-approved OpenAPI specs to WSO2 API Manager 4.x and publishes
them so they appear in the WSO2 Developer Portal.

Tested against WSO2 APIM 4.3.0; should also work on 4.0–4.5 because the parts
that vary between point releases (throttling tier names, gateway env names) are
discovered at runtime instead of hardcoded.

Why the previous version failed
-------------------------------
WSO2 APIM 4.x decoupled lifecycle transitions from gateway deployment. The
former code went straight from `import-openapi` to `change-lifecycle?action=Publish`
and the publish executor blew up internally with the generic error 900967
because:

  1. The imported API had no `endpointConfig` set (import-openapi silently
     drops endpointConfig from `additionalProperties` in 4.x).
  2. There was no revision created.
  3. There was no revision deployed to a gateway.

The correct sequence in 4.x is:

  import-openapi
    -> GET  /apis/{id}                                (poll until visible)
    -> PUT  /apis/{id}                                (set endpointConfig + policies)
    -> POST /apis/{id}/revisions                      (snapshot)
    -> POST /apis/{id}/deploy-revision?revisionId=…   (deploy to gateway)
    -> wait for the deployment to register
    -> POST /apis/change-lifecycle?apiId=…&action=Publish

Public contract is unchanged
----------------------------
    publish(data: dict, filename: str) -> {"success": bool,
                                            "wso2_api_id": str | None,
                                            "error": str | None}

Async safety (Risk #5)
----------------------
This module uses synchronous httpx. The full publish flow can take 5–15 seconds.
If you call it from inside an async FastAPI handler, wrap it so it doesn't
block the event loop:

    import asyncio
    wso2_result = await asyncio.to_thread(wso2_service.publish, data, file.filename)

A drop-in async helper `publish_async` is also provided below for convenience.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
import warnings
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

WSO2_BASE_URL = os.getenv("WSO2_BASE_URL", "").rstrip("/")
WSO2_CLIENT_ID = os.getenv("WSO2_CLIENT_ID", "")
WSO2_CLIENT_SECRET = os.getenv("WSO2_CLIENT_SECRET", "")

# Optional. If set, every published API points at this backend instead of the
# one in spec.servers[]. Useful when your governance platform doesn't actually
# proxy traffic and you just need a syntactically-valid URL for WSO2.
WSO2_DEFAULT_BACKEND_URL = os.getenv(
    "WSO2_DEFAULT_BACKEND_URL", "http://localhost:8080"
).rstrip("/")

_PUBLISHER_BASE = f"{WSO2_BASE_URL}/api/am/publisher/v4"
_TOKEN_URL = f"{WSO2_BASE_URL}/oauth2/token"

_VERIFY_SSL = os.getenv("WSO2_VERIFY_SSL", "false").lower() == "true"

# Suppress SSL warnings for self-signed certs in local/dev WSO2 Docker.
if not _VERIFY_SSL:
    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

# Scopes needed for the full sequence below. import_export is required for
# revision/deploy-revision in 4.2+; older servers happily ignore unknown scopes.
_TOKEN_SCOPES = (
    "apim:api_create "
    "apim:api_publish "
    "apim:api_view "
    "apim:api_manage "
    "apim:api_import_export"
)

# Polling tunables — generous on purpose.
_VISIBILITY_POLL_ATTEMPTS = 10
_VISIBILITY_POLL_INTERVAL = 0.6  # seconds
_DEPLOYMENT_POLL_ATTEMPTS = 10
_DEPLOYMENT_POLL_INTERVAL = 0.6  # seconds

_HTTP_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)

# Risk #4: when we PUT /apis/{id}, send only the fields we need to mutate.
# This protects us from server-side validators that reject read-only fields
# WSO2 happens to include in its GET response (createdTime, lastUpdatedTime,
# workflowStatus, etc. vary between point releases).
_PUT_API_WHITELIST = frozenset({
    "id",
    "name",
    "context",
    "version",
    "description",
    "provider",
    "lifeCycleStatus",   # accepted on PUT in 4.3 (preserved, not changed)
    "type",
    "transport",
    "tags",
    "policies",
    "apiThrottlingPolicy",
    "authorizationHeader",
    "securityScheme",
    "maxTps",
    "visibility",
    "visibleRoles",
    "visibleTenants",
    "subscriptionAvailability",
    "subscriptionAvailableTenants",
    "additionalProperties",
    "additionalPropertiesMap",
    "accessControl",
    "accessControlRoles",
    "businessInformation",
    "corsConfiguration",
    "websubSubscriptionConfiguration",
    "responseCachingEnabled",
    "cacheTimeout",
    "endpointConfig",
    "endpointImplementationType",
    "scopes",
    "operations",
    "categories",
    "keyManagers",
    "advertiseInfo",
    "gatewayVendor",
    "gatewayType",
})


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _is_configured() -> bool:
    return bool(WSO2_BASE_URL and WSO2_CLIENT_ID and WSO2_CLIENT_SECRET)


def _safe_context(title: str) -> str:
    """Convert an API title into a valid WSO2 context path segment."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")
    return f"/{slug}" if slug else "/api"


def _resolve_backend_url(data: dict) -> str:
    """
    Pick the best backend URL for the WSO2 API config.

    Priority:
      1. First valid http(s) URL in the spec's `servers[]` block.
      2. WSO2_DEFAULT_BACKEND_URL from .env.
      3. http://localhost:8080  (last-resort placeholder; always parses).
    """
    servers = data.get("servers") if isinstance(data, dict) else None
    if isinstance(servers, list):
        for entry in servers:
            if not isinstance(entry, dict):
                continue
            url = (entry.get("url") or "").strip()
            # WSO2 won't accept template variables like {host} as a backend.
            if url.startswith(("http://", "https://")) and "{" not in url:
                return url.rstrip("/")
    return WSO2_DEFAULT_BACKEND_URL or "http://localhost:8080"


def _build_endpoint_config(backend_url: str) -> dict:
    """Endpoint config payload accepted by WSO2 4.x for a standard HTTP API."""
    return {
        "endpoint_type": "http",
        "sandbox_endpoints": {"url": backend_url},
        "production_endpoints": {"url": backend_url},
    }


def _format_http_error(exc: httpx.HTTPStatusError, correlation_id: str) -> str:
    body = exc.response.text or ""
    snippet = body[:400].replace("\n", " ").strip()
    return (
        f"WSO2 HTTP {exc.response.status_code} on "
        f"{exc.request.method} {exc.request.url.path} "
        f"(correlation_id={correlation_id}): {snippet}"
    )


def _whitelisted_dto(dto: dict) -> dict:
    """Risk #4: drop fields WSO2 might reject as read-only on PUT."""
    return {k: v for k, v in dto.items() if k in _PUT_API_WHITELIST}


# ---------------------------------------------------------------------------
# WSO2 client wrapper
# ---------------------------------------------------------------------------

class _WSO2Client:
    """
    Thin wrapper around `httpx.Client` that:
      - Acquires an OAuth2 token once and reuses it.
      - Sends an `activityid` correlation UUID on every request, so failures
        can be matched against the WSO2 server logs.
      - Centralizes verify/timeout/headers.
    """

    def __init__(self) -> None:
        self.correlation_id = str(uuid.uuid4())
        self._client = httpx.Client(verify=_VERIFY_SSL, timeout=_HTTP_TIMEOUT)
        self._token: str | None = None
        # Cache the discovered subscription policy across calls in one publish.
        self._cached_policy: str | None = None

    def __enter__(self) -> "_WSO2Client":
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self._client.close()

    # ----- token

    def _ensure_token(self) -> str:
        if self._token:
            return self._token
        resp = self._client.post(
            _TOKEN_URL,
            auth=(WSO2_CLIENT_ID, WSO2_CLIENT_SECRET),
            data={"grant_type": "client_credentials", "scope": _TOKEN_SCOPES},
        )
        resp.raise_for_status()
        body = resp.json() or {}
        token = body.get("access_token")
        if not token:
            raise RuntimeError(
                f"WSO2 token endpoint returned no access_token. Body: {resp.text[:200]}"
            )
        # Risk #3: warn if the server didn't grant all the scopes we asked for.
        granted = (body.get("scope") or "").split()
        requested = _TOKEN_SCOPES.split()
        missing = [s for s in requested if s not in granted]
        if missing:
            logger.warning(
                "WSO2 OAuth client missing scopes: %s. "
                "Some operations may fail with 401/403. "
                "Re-register the client with these scopes if needed. "
                "(correlation_id=%s)",
                ", ".join(missing),
                self.correlation_id,
            )
        self._token = token
        return token

    def _headers(self, extra: dict | None = None) -> dict:
        h = {
            "Authorization": f"Bearer {self._ensure_token()}",
            "Accept": "application/json",
            "activityid": self.correlation_id,
        }
        if extra:
            h.update(extra)
        return h

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: Any = None,
        data: dict | None = None,
        files: dict | None = None,
        headers: dict | None = None,
        raise_for_status: bool = True,
    ) -> httpx.Response:
        url = f"{_PUBLISHER_BASE}{path}"
        resp = self._client.request(
            method,
            url,
            params=params,
            json=json_body,
            data=data,
            files=files,
            headers=self._headers(headers),
        )
        if raise_for_status:
            resp.raise_for_status()
        return resp

    # ----- adaptive subscription policy discovery (Risk #3)

    def discover_subscription_policy(self) -> str:
        """
        Pick a subscription policy this WSO2 install actually has.

        Preference order: 'Unlimited' → 'Default' → first available → 'Unlimited'.
        Fetched once per client; cached for the rest of the publish call.
        """
        if self._cached_policy:
            return self._cached_policy

        names: list[str] = []
        try:
            resp = self.request("GET", "/throttling-policies/subscription")
            for item in (resp.json() or {}).get("list") or []:
                n = (item.get("name") or "").strip()
                if n:
                    names.append(n)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Could not list subscription policies (%s); defaulting to 'Unlimited'. "
                "correlation_id=%s",
                exc.response.status_code,
                self.correlation_id,
            )

        chosen = "Unlimited"
        if names:
            for pref in ("Unlimited", "Default"):
                if pref in names:
                    chosen = pref
                    break
            else:
                chosen = names[0]

        logger.info(
            "WSO2 subscription policy: %s (available=%s, correlation_id=%s)",
            chosen, names or "<unknown>", self.correlation_id,
        )
        self._cached_policy = chosen
        return chosen

    # ----- core operations

    def find_existing_api(self, name: str, version: str) -> str | None:
        resp = self.request(
            "GET",
            "/apis",
            params={"query": f'name:"{name}" version:"{version}"', "limit": 10},
        )
        for item in (resp.json() or {}).get("list", []) or []:
            if item.get("name") == name and item.get("version") == str(version):
                return item.get("id")
        return None

    def get_api(self, api_id: str) -> dict:
        resp = self.request("GET", f"/apis/{api_id}")
        return resp.json() or {}

    def get_api_lifecycle_state(self, api_id: str) -> str | None:
        try:
            resp = self.request("GET", f"/apis/{api_id}/lifecycle-state")
        except httpx.HTTPStatusError:
            return None
        body = resp.json() or {}
        return (body.get("state") or "").upper() or None

    def get_api_deployments(self, api_id: str) -> list[dict]:
        try:
            resp = self.request("GET", f"/apis/{api_id}/deployments")
        except httpx.HTTPStatusError:
            return []
        body = resp.json()
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            return body.get("list") or []
        return []

    def wait_for_visibility(self, api_id: str) -> dict:
        """
        Poll GET /apis/{id} until it returns a populated DTO.

        Don't just check status 200: also confirm the body contains a non-empty
        `id`, since some 4.x builds briefly return 200 with a stub during the
        registry sync window.
        """
        last_body: dict = {}
        for _ in range(_VISIBILITY_POLL_ATTEMPTS):
            try:
                resp = self.request("GET", f"/apis/{api_id}")
                body = resp.json() or {}
                if body.get("id"):
                    return body
                last_body = body
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 404:
                    raise
            time.sleep(_VISIBILITY_POLL_INTERVAL)
        raise RuntimeError(
            f"WSO2 API {api_id} did not become fully visible after "
            f"{_VISIBILITY_POLL_ATTEMPTS * _VISIBILITY_POLL_INTERVAL:.1f}s "
            f"(last_body_keys={list(last_body)})"
        )

    def import_openapi(
        self,
        spec_bytes: bytes,
        filename: str,
        name: str,
        version: str,
        context: str,
    ) -> str:
        """
        Imports the OpenAPI spec. NOTE: we deliberately do NOT pass endpointConfig
        here; it is silently dropped by import-openapi in many 4.x builds. The
        full DTO (with endpointConfig + policies) is sent via PUT in the next
        step.
        """
        policy = self.discover_subscription_policy()
        additional = {
            "name": name,
            "version": str(version),
            "context": context,
            "provider": "admin",
            "visibility": "PUBLIC",
            "policies": [policy],
        }
        resp = self.request(
            "POST",
            "/apis/import-openapi",
            files={"file": (filename, spec_bytes, "application/yaml")},
            data={"additionalProperties": json.dumps(additional)},
        )
        api_id = (resp.json() or {}).get("id")
        if not api_id:
            raise RuntimeError(
                f"WSO2 import-openapi returned no API id. Body: {resp.text[:300]}"
            )
        return api_id

    def update_api(self, api_id: str, dto: dict) -> dict:
        """
        PUT /apis/{id} with only whitelisted (mutable) fields.

        Risk #4 fix: WSO2's PUT validator can reject fields that appear in its
        own GET response (varies by point release: createdTime, lastUpdatedTime,
        workflowStatus, etc.). We strip the DTO down to fields known to be
        accepted as input.
        """
        body = _whitelisted_dto(dto)
        resp = self.request("PUT", f"/apis/{api_id}", json_body=body)
        return resp.json() or {}

    def create_revision(self, api_id: str) -> str:
        resp = self.request(
            "POST",
            f"/apis/{api_id}/revisions",
            json_body={"description": "Auto-revision created by governance platform"},
        )
        body = resp.json() or {}
        rev_id = body.get("id")
        if not rev_id:
            raise RuntimeError(
                f"WSO2 create-revision returned no id. Body: {resp.text[:300]}"
            )
        return rev_id

    def list_gateway_environments(self) -> list[dict]:
        try:
            resp = self.request("GET", "/gateway-environments")
        except httpx.HTTPStatusError:
            return []
        body = resp.json()
        # Some 4.x builds return a bare list, others wrap it in {"list": [...]}.
        if isinstance(body, list):
            return body
        if isinstance(body, dict):
            return body.get("list") or []
        return []

    def pick_default_environment(self) -> tuple[str, str]:
        """
        Return (environment_name, vhost) suitable for deploy-revision.

        Prefers an environment named 'Default'. Falls back to the first
        configured environment. If discovery fails entirely, returns the
        documented stock-install defaults.
        """
        envs = self.list_gateway_environments()
        chosen: dict | None = None
        for env in envs:
            if (env.get("name") or "").lower() == "default":
                chosen = env
                break
        if chosen is None and envs:
            chosen = envs[0]

        if chosen is None:
            return "Default", "localhost"

        env_name = chosen.get("name") or "Default"
        vhosts = chosen.get("vhosts") or []
        vhost = "localhost"
        if vhosts and isinstance(vhosts, list):
            first = vhosts[0]
            if isinstance(first, dict):
                vhost = first.get("host") or "localhost"
            elif isinstance(first, str):
                vhost = first
        return env_name, vhost

    def deploy_revision(
        self, api_id: str, revision_id: str, env_name: str, vhost: str
    ) -> None:
        self.request(
            "POST",
            f"/apis/{api_id}/deploy-revision",
            params={"revisionId": revision_id},
            json_body=[
                {
                    "name": env_name,
                    "vhost": vhost,
                    "displayOnDevportal": True,
                }
            ],
        )

    def wait_for_deployment(self, api_id: str) -> None:
        """Poll GET /apis/{id}/deployments until non-empty."""
        for _ in range(_DEPLOYMENT_POLL_ATTEMPTS):
            if self.get_api_deployments(api_id):
                return
            time.sleep(_DEPLOYMENT_POLL_INTERVAL)
        # Don't hard-fail: deploy returned 201, so the deployment is registered
        # server-side. Just log and let the lifecycle attempt proceed.
        logger.warning(
            "WSO2 deployment list still empty after wait (api_id=%s, correlation_id=%s)",
            api_id,
            self.correlation_id,
        )

    def change_lifecycle(self, api_id: str, action: str) -> None:
        # NB: in v4 this is /apis/change-lifecycle?apiId=...&action=...
        # `action` is case-sensitive: "Publish", not "publish".
        self.request(
            "POST",
            "/apis/change-lifecycle",
            params={"apiId": api_id, "action": action},
            headers={"Content-Length": "0"},
        )

    # ----- diagnostics for error path

    def diagnostic_snapshot(self, api_id: str) -> str:
        bits: list[str] = []
        try:
            state = self.get_api_lifecycle_state(api_id)
            bits.append(f"lifecycle_state={state}")
        except Exception:
            pass
        try:
            count = len(self.get_api_deployments(api_id))
            bits.append(f"deployment_count={count}")
        except Exception:
            pass
        return ", ".join(bits)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def _full_publish_sequence(
    wso2: _WSO2Client,
    api_id: str,
    backend_url: str,
    starting_state: str | None,
) -> None:
    """
    Drive an API from wherever it currently is in the lifecycle to PUBLISHED.

    - PUBLISHED  -> nothing to do.
    - PROTOTYPED -> just transition to Published.
    - CREATED / unknown -> run the full pipeline.
    """
    state = (starting_state or "").upper()

    if state == "PUBLISHED":
        return

    if state == "PROTOTYPED":
        wso2.change_lifecycle(api_id, "Publish")
        return

    # CREATED / unknown: full pipeline.
    dto = wso2.wait_for_visibility(api_id)

    # Patch in endpointConfig + policy. update_api() drops read-only fields.
    dto["endpointConfig"] = _build_endpoint_config(backend_url)
    if not dto.get("policies"):
        dto["policies"] = [wso2.discover_subscription_policy()]
    wso2.update_api(api_id, dto)

    # Revision + deploy.
    revision_id = wso2.create_revision(api_id)
    env_name, vhost = wso2.pick_default_environment()
    logger.info(
        "WSO2 deploying revision %s to env=%s vhost=%s (api_id=%s, correlation_id=%s)",
        revision_id, env_name, vhost, api_id, wso2.correlation_id,
    )
    wso2.deploy_revision(api_id, revision_id, env_name, vhost)
    wso2.wait_for_deployment(api_id)

    # Final lifecycle transition.
    wso2.change_lifecycle(api_id, "Publish")


def publish(data: dict, filename: str) -> dict:
    """
    Push an approved OpenAPI spec to WSO2 API Manager and publish it so it
    appears in the WSO2 Developer Portal.

    Returns
    -------
    {"success": bool, "wso2_api_id": str | None, "error": str | None}
    """
    if not _is_configured():
        return {
            "success": False,
            "wso2_api_id": None,
            "error": "WSO2 not configured (WSO2_BASE_URL / client id / client secret missing)",
        }

    info = data.get("info", {}) if isinstance(data, dict) else {}
    name = (info.get("title") or "unnamed-api").strip()
    version = str(info.get("version") or "1.0").strip()
    context = _safe_context(name)
    backend_url = _resolve_backend_url(data)

    spec_bytes = yaml.dump(data, allow_unicode=True).encode("utf-8")
    safe_filename = (
        filename if filename.endswith((".yaml", ".yml")) else f"{filename}.yaml"
    )

    api_id: str | None = None
    # Manual lifecycle (not `with`) so the client is still open during the
    # except handler when we want to snapshot lifecycle/deployment state.
    wso2 = _WSO2Client()

    try:
        logger.info(
            "WSO2 publish start: name=%r version=%r backend=%s correlation_id=%s",
            name, version, backend_url, wso2.correlation_id,
        )

        existing_id = wso2.find_existing_api(name, version)
        if existing_id:
            api_id = existing_id
            state = wso2.get_api_lifecycle_state(api_id)
            logger.info(
                "WSO2 API exists (id=%s, state=%s); resuming",
                api_id, state,
            )
            _full_publish_sequence(wso2, api_id, backend_url, state)
        else:
            api_id = wso2.import_openapi(
                spec_bytes, safe_filename, name, version, context
            )
            logger.info(
                "WSO2 import-openapi created api_id=%s (correlation_id=%s)",
                api_id, wso2.correlation_id,
            )
            _full_publish_sequence(wso2, api_id, backend_url, "CREATED")

        logger.info(
            "WSO2 publish succeeded: api_id=%s correlation_id=%s",
            api_id, wso2.correlation_id,
        )
        return {"success": True, "wso2_api_id": api_id, "error": None}

    except httpx.HTTPStatusError as exc:
        cid = exc.request.headers.get("activityid", "?")
        msg = _format_http_error(exc, cid)
        if api_id:
            try:
                snapshot = wso2.diagnostic_snapshot(api_id)
                if snapshot:
                    msg = f"{msg} [{snapshot}]"
            except Exception:
                pass
        logger.error("WSO2 publish failed: %s", msg)
        return {"success": False, "wso2_api_id": api_id, "error": msg}

    except Exception as exc:
        logger.exception("WSO2 publish unexpected error")
        return {
            "success": False,
            "wso2_api_id": api_id,
            "error": f"{type(exc).__name__}: {exc}",
        }

    finally:
        # Always close the underlying httpx client, even on success.
        try:
            wso2._client.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Async wrapper (Risk #5)
# ---------------------------------------------------------------------------

async def publish_async(data: dict, filename: str) -> dict:
    """
    Async wrapper that runs `publish` in a worker thread so it doesn't block
    the FastAPI event loop. Use this from `async def` route handlers:

        wso2_result = await wso2_service.publish_async(data, file.filename)

    The synchronous `publish()` continues to work unchanged.
    """
    return await asyncio.to_thread(publish, data, filename)
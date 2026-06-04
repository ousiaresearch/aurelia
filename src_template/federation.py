"""federation.py — World-side federation client.

Each world instance uses this to:
- Register with the federation coordinator on startup
- Send periodic heartbeats to stay online
- Respond to cross-world travel requests
"""

import json
import time
import urllib.request
import urllib.error
import logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("federation")


def register_with_coordinator(
    coordinator_url: str,
    world_id: str,
    api_url: str,
    identity: dict,
    timeout: float = 10.0,
) -> bool:
    """POST /register to the federation coordinator.

    Returns True if registration succeeded, False otherwise.
    """
    payload = json.dumps({
        "world_id": world_id,
        "api_url": api_url,
        "identity": identity,
    }).encode()

    req = urllib.request.Request(
        f"{coordinator_url.rstrip('/')}/register",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        data = json.loads(resp.read())
        log.info(f"Registered with federation coordinator: {data.get('status')}")
        return True
    except urllib.error.URLError as e:
        log.warning(f"Federation coordinator unreachable: {e}")
        return False
    except Exception as e:
        log.warning(f"Registration failed: {e}")
        return False


def send_heartbeat(
    coordinator_url: str,
    world_id: str,
    identity: Optional[dict] = None,
    timeout: float = 5.0,
) -> bool:
    """POST /heartbeat to keep this world online in the coordinator.

    Call this each tick to prevent the coordinator from marking the world offline.
    """
    payload_dict: dict = {"world_id": world_id}
    if identity:
        payload_dict["identity"] = identity

    payload = json.dumps(payload_dict).encode()

    req = urllib.request.Request(
        f"{coordinator_url.rstrip('/')}/heartbeat",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except Exception:
        return False


def publish_federation_events(
    coordinator_url: str,
    world_id: str,
    events: list[dict],
    timeout: float = 5.0,
) -> dict:
    """POST /events to publish cross-world event-bus records.

    Returns the coordinator response. Failures are non-fatal for daemons; callers
    get a compact error dict rather than an exception.
    """
    if not events:
        return {"status": "ok", "accepted": 0, "duplicates": 0}

    payload = json.dumps({"world_id": world_id, "events": events}).encode()
    req = urllib.request.Request(
        f"{coordinator_url.rstrip('/')}/events",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read())
    except Exception as e:
        log.warning(f"Federation event publish failed: {e}")
        return {"status": "error", "accepted": 0, "duplicates": 0, "error": str(e)}

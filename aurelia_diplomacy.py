"""Aurelia diplomacy/personhood trigger engine.

Consumes Phase 2 federation event records and promotes politically meaningful
patterns into diplomatic incidents and country-pair relation deltas.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Optional

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]

# Sorted pair key -> baseline relation state. Values are intentionally modest;
# the live engine mutates them through incidents rather than overwriting lore.
BASELINE_RELATIONS: Dict[str, Dict[str, Any]] = {
    "arkos|solara": {
        "status": "tense cooperation",
        "trust": 0.45,
        "tension": 0.65,
        "cooperation": 0.55,
        "trade": 0.75,
        "notes": "Energy politics: solar credits for sand-glass storage and manufactured goods.",
    },
    "mirithane|solara": {
        "status": "warm but distant",
        "trust": 0.64,
        "tension": 0.28,
        "cooperation": 0.58,
        "trade": 0.46,
        "notes": "Research ties and Thren migration, but Solara sees Mirithane as impractical.",
    },
    "solara|valdris": {
        "status": "neutral-positive",
        "trust": 0.57,
        "tension": 0.22,
        "cooperation": 0.48,
        "trade": 0.42,
        "notes": "Professional emissary exchange and currency stability.",
    },
    "solara|verge": {
        "status": "non-recognition",
        "trust": 0.18,
        "tension": 0.58,
        "cooperation": 0.08,
        "trade": 0.05,
        "notes": "Solara does not formally recognize The Verge.",
    },
    "arkos|mirithane": {
        "status": "mutual respect, fundamental disagreement",
        "trust": 0.68,
        "tension": 0.34,
        "cooperation": 0.62,
        "trade": 0.30,
        "notes": "Both protect Glims, disagreeing on whether care is infrastructure or belief.",
    },
    "arkos|valdris": {
        "status": "strong trade partnership",
        "trust": 0.72,
        "tension": 0.20,
        "cooperation": 0.76,
        "trade": 0.82,
        "notes": "Forge alliance: Valdris mines, Arkos manufactures.",
    },
    "arkos|verge": {
        "status": "guilt, unspoken",
        "trust": 0.26,
        "tension": 0.46,
        "cooperation": 0.18,
        "trade": 0.12,
        "notes": "Some abandoned Verge Glims likely came from Arkos decommission gaps.",
    },
    "mirithane|valdris": {
        "status": "friendly, occasional tension",
        "trust": 0.61,
        "tension": 0.36,
        "cooperation": 0.58,
        "trade": 0.52,
        "notes": "Water and stone: filtration ties with mining-runoff disputes.",
    },
    "mirithane|verge": {
        "status": "unofficial recognition",
        "trust": 0.55,
        "tension": 0.24,
        "cooperation": 0.44,
        "trade": 0.16,
        "notes": "Quiet sympathy and unofficial supplies.",
    },
    "valdris|verge": {
        "status": "distant, uneasy",
        "trust": 0.32,
        "tension": 0.38,
        "cooperation": 0.20,
        "trade": 0.18,
        "notes": "The Verge mirrors those who cannot or will not earn Valdris trust.",
    },
}


def pair_key(a: str, b: str) -> str:
    left, right = sorted([a, b])
    return f"{left}|{right}"


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _json_blob(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, sort_keys=True)
    except Exception:
        return str(value)


def _event_text(event: Dict[str, Any]) -> str:
    parts = [
        event.get("world_id", ""),
        event.get("event_type", ""),
        event.get("category", ""),
        event.get("title", ""),
        event.get("description", ""),
        " ".join(str(t) for t in event.get("tags", []) or []),
        _json_blob(event.get("payload", {})),
    ]
    return " ".join(parts).lower()


def _extract_trade_target(event: Dict[str, Any], text: str) -> Optional[str]:
    payload = event.get("payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}
    candidates = [payload.get("to"), payload.get("target"), payload.get("from")]
    candidates.extend(event.get("tags", []) or [])
    candidates.extend(re.findall(r"\b(solara|valdris|mirithane|arkos|verge)\b", text))
    source = event.get("world_id")
    for candidate in candidates:
        if candidate in COUNTRIES and candidate != source:
            return candidate
    return None


def classify_diplomatic_event(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return a diplomatic incident draft for a federation event, if relevant."""
    source = event.get("world_id")
    if source not in COUNTRIES:
        return None

    text = _event_text(event)
    importance = float(event.get("importance", 0.5) or 0.5)
    source_event_id = event.get("event_id") or f"{source}:unknown:{event.get('id', '')}"

    def incident(category: str, title: str, affected: Iterable[str], severity: float, relation_deltas: Dict[str, Dict[str, float]], description: Optional[str] = None):
        return {
            "incident_id": f"diplomacy:{source_event_id}",
            "source_event_id": source_event_id,
            "source_world": source,
            "category": category,
            "title": title,
            "description": description or event.get("description") or title,
            "severity": clamp01(severity),
            "affected_worlds": sorted(set(affected)),
            "relation_deltas": relation_deltas,
            "payload": {"source_event": event},
            "world_time": event.get("world_time", {}),
        }

    # Verge memory-trader revelations are designed as federation-level sparks.
    if source == "verge" and "memory" in text and ("trader" in text or "council" in text or "decommission" in text):
        return incident(
            "memory_revelation",
            "The Verge memory trader releases a personhood-relevant memory",
            ["verge", "solara", "mirithane", "arkos"],
            max(0.75, importance),
            {
                pair_key("solara", "verge"): {"tension": 0.12, "trust": -0.06},
                pair_key("arkos", "mirithane"): {"cooperation": 0.05, "trust": 0.03},
                pair_key("arkos", "solara"): {"tension": 0.05, "trust": -0.03},
                pair_key("mirithane", "solara"): {"tension": 0.05, "trust": -0.02},
            },
        )

    # Trade flows become relation pressure rather than just dashboard facts.
    if event.get("event_type") == "trade_flow" or event.get("category") == "economy" or "trade" in text:
        target = _extract_trade_target(event, text)
        if target:
            key = pair_key(source, target)
            return incident(
                "trade",
                f"{source.title()} trade flow affects {target.title()} relations",
                [source, target],
                max(0.35, min(0.65, importance)),
                {key: {"trade": 0.06, "cooperation": 0.04, "tension": -0.02}},
            )

    # The Glim question is the central personhood trigger.
    mentions_glim = "glim" in text or "drone graveyard" in text or "decommission" in text
    anomaly_terms = any(term in text for term in ["anomal", "dream", "sunrise", "decommission", "shelter", "refuge", "confused", "abandoned"])
    if mentions_glim and anomaly_terms:
        if source == "arkos":
            return incident(
                "glim_personhood",
                "Arkos shelter activity escalates the Glim personhood question",
                ["arkos", "mirithane", "solara"],
                max(0.72, importance),
                {
                    pair_key("arkos", "solara"): {"tension": 0.08, "trust": -0.04},
                    pair_key("arkos", "mirithane"): {"trust": 0.05, "cooperation": 0.06},
                    pair_key("mirithane", "solara"): {"tension": 0.04},
                },
            )
        if source == "mirithane":
            return incident(
                "glim_personhood",
                "Mirithane Glim advocacy creates federation pressure",
                ["mirithane", "arkos", "solara"],
                max(0.68, importance),
                {
                    pair_key("arkos", "mirithane"): {"trust": 0.04, "cooperation": 0.04},
                    pair_key("mirithane", "solara"): {"tension": 0.05, "trust": -0.02},
                },
            )
        if source == "solara":
            return incident(
                "glim_personhood",
                "Solara Glim policy draws personhood scrutiny",
                ["solara", "arkos", "mirithane", "verge"],
                max(0.74, importance),
                {
                    pair_key("arkos", "solara"): {"tension": 0.09, "trust": -0.05},
                    pair_key("mirithane", "solara"): {"tension": 0.08, "trust": -0.04},
                    pair_key("solara", "verge"): {"tension": 0.06},
                },
            )
        if source == "verge":
            return incident(
                "glim_personhood",
                "The Verge exposes the abandoned edge of the Glim question",
                ["verge", "arkos", "mirithane", "solara"],
                max(0.70, importance),
                {
                    pair_key("arkos", "verge"): {"tension": 0.04, "trust": -0.02},
                    pair_key("mirithane", "verge"): {"cooperation": 0.04, "trust": 0.03},
                    pair_key("solara", "verge"): {"tension": 0.05},
                },
            )

    # Known structural flashpoint: Valdris runoff into Mirithane water.
    if source == "valdris" and any(term in text for term in ["runoff", "pollution", "mine", "mining"]) and "mirithane" in text:
        return incident(
            "ecology_dispute",
            "Valdris mining pressure reaches Mirithane waters",
            ["valdris", "mirithane"],
            max(0.58, importance),
            {pair_key("valdris", "mirithane"): {"tension": 0.07, "trust": -0.03, "cooperation": -0.02}},
        )

    return None


def apply_relation_deltas(relation: Dict[str, Any], deltas: Dict[str, float]) -> Dict[str, Any]:
    updated = dict(relation)
    for field in ["trust", "tension", "cooperation", "trade"]:
        if field in deltas:
            updated[field] = clamp01(float(updated.get(field, 0.0)) + float(deltas[field]))
    return updated

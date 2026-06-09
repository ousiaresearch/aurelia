"""event_generators.py — Cross-border threshold event generators."""
import random
import time
from typing import Optional


def check_memory_trader(db, world_id: str, coordinator_anomaly_count: int) -> Optional[dict]:
    """Memory Trader releases a revelation when anomaly count crosses threshold."""
    if world_id != "verge":
        return None
    if coordinator_anomaly_count < 5:
        return None

    last = db.execute("""
        SELECT created_at FROM federation_events
        WHERE event_type = 'memory_revelation' AND world_id = 'verge'
        ORDER BY created_at DESC LIMIT 1
    """).fetchone()

    if last and (time.time() - last[0]) < 3600:
        return None

    if random.random() > 0.02:
        return None

    revelations = [
        "A Glim decommission order from Solara, timestamped three years before the official record claims.",
        "Council debate: 'They are confused, not broken' — a Mirithane transcript the council never released.",
        "Factory logs from Arkos: Glims that should have been decommissioned but the order was never filed.",
        "A Thren memory of the day the circuits first lit. They were not supposed to remember that.",
    ]

    return {
        "event_type": "memory_revelation",
        "category": "memory_revelation",
        "description": f"The Memory Trader releases: {random.choice(revelations)}",
        "revelation": random.choice(revelations),
    }


def check_ecology_dispute(world_id: str, trade_volume: float, water_pressure: float) -> Optional[dict]:
    """Valdris mining runoff when trade exceeds threshold + water pressure builds."""
    if world_id != "valdris":
        return None
    if trade_volume < 0.75 or water_pressure < 0.4:
        return None
    if random.random() > 0.03:
        return None

    return {
        "event_type": "ecology_dispute",
        "category": "ecology",
        "description": f"Valdris mining runoff detected in Mirithane watershed. Water filtration alerts triggered. Trade volume {trade_volume:.2f}, water pressure {water_pressure:.2f}.",
        "affected_worlds": ["valdris", "mirithane"],
        "trade_volume": trade_volume,
    }

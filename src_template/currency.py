"""
currency.py — Aurelian multi-currency system.

Each country mints its own resource-backed currency. Exchange rates float
based on simulated trade flows, resource production, and diplomatic standing.
The Aurelian Exchange tracks it all.
"""

import time
import random
import math
from typing import Optional

# ── Currency Definitions ──────────────────────────────────────────────

CURRENCIES = {
    "Lumen": {
        "symbol": "☀",
        "country": "solara",
        "backing": "Solar energy credits + biofuel yield",
        "base_value": 1.0,   # Lumen is the reference currency
        "volatility": 0.05,
        "mint_rate": 0.02,   # new Lumens created per tick per solar engineer
    },
    "Kael": {
        "symbol": "♦",
        "country": "valdris",
        "backing": "Rare earth minerals + refined metals",
        "base_value": 1.35,  # stronger — backed by tangible minerals
        "volatility": 0.08,
        "mint_rate": 0.015,
    },
    "Miri": {
        "symbol": "≈",
        "country": "mirithane",
        "backing": "Purified water reserves + filtration capacity",
        "base_value": 0.9,   # slightly weaker — water is abundant
        "volatility": 0.04,
        "mint_rate": 0.025,
    },
    "Ark": {
        "symbol": "▲",
        "country": "arkos",
        "backing": "Stored solar energy + manufactured output",
        "base_value": 1.2,
        "volatility": 0.06,
        "mint_rate": 0.018,
    },
}

REFERENCE_CURRENCY = "Lumen"


def get_currency(country_id: str) -> Optional[dict]:
    """Get currency info for a country."""
    for name, info in CURRENCIES.items():
        if info["country"] == country_id:
            return {"name": name, **info}
    return None


def init_currency_tables(db):
    """Create currency-related tables in the world DB."""
    db.executescript("""
        CREATE TABLE IF NOT EXISTS currency_holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL REFERENCES agents(id),
            currency TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0,
            updated_at REAL NOT NULL,
            UNIQUE(agent_id, currency)
        );

        CREATE TABLE IF NOT EXISTS exchange_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_currency TEXT NOT NULL,
            to_currency TEXT NOT NULL,
            rate REAL NOT NULL,
            updated_at REAL NOT NULL,
            UNIQUE(from_currency, to_currency)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            from_agent TEXT NOT NULL,
            to_agent TEXT NOT NULL,
            currency TEXT NOT NULL,
            amount REAL NOT NULL,
            exchange_rate REAL DEFAULT 1.0,
            note TEXT DEFAULT '',
            location_id TEXT DEFAULT ''
        );
    """)
    db.commit()


def seed_exchange_rates(db):
    """Initialize exchange rates between all currencies."""
    now = time.time()
    
    for from_name, from_info in CURRENCIES.items():
        for to_name, to_info in CURRENCIES.items():
            if from_name == to_name:
                rate = 1.0
            else:
                rate = to_info["base_value"] / from_info["base_value"]
            
            db.execute("""
                INSERT OR REPLACE INTO exchange_rates (from_currency, to_currency, rate, updated_at)
                VALUES (?, ?, ?, ?)
            """, (from_name, to_name, round(rate, 4), now))
    
    db.commit()


def get_exchange_rate(db, from_currency: str, to_currency: str) -> float:
    """Get the current exchange rate between two currencies."""
    row = db.execute(
        "SELECT rate FROM exchange_rates WHERE from_currency = ? AND to_currency = ?",
        (from_currency, to_currency)
    ).fetchone()
    return row["rate"] if row else 1.0


def convert(db, from_currency: str, to_currency: str, amount: float) -> float:
    """Convert an amount from one currency to another."""
    rate = get_exchange_rate(db, from_currency, to_currency)
    return amount * rate


def get_balance(db, agent_id: str, currency: str) -> float:
    """Get an agent's balance in a specific currency."""
    row = db.execute(
        "SELECT amount FROM currency_holdings WHERE agent_id = ? AND currency = ?",
        (agent_id, currency)
    ).fetchone()
    return row["amount"] if row else 0.0


def adjust_balance(db, agent_id: str, currency: str, delta: float) -> float:
    """Adjust an agent's currency balance. Returns new balance."""
    now = time.time()
    row = db.execute(
        "SELECT amount FROM currency_holdings WHERE agent_id = ? AND currency = ?",
        (agent_id, currency)
    ).fetchone()
    
    if row is None:
        new_balance = max(0, delta)
        db.execute(
            "INSERT INTO currency_holdings (agent_id, currency, amount, updated_at) VALUES (?, ?, ?, ?)",
            (agent_id, currency, new_balance, now)
        )
    else:
        new_balance = max(0, row["amount"] + delta)
        db.execute(
            "UPDATE currency_holdings SET amount = ?, updated_at = ? WHERE agent_id = ? AND currency = ?",
            (new_balance, now, agent_id, currency)
        )
    
    return new_balance


def transfer(db, from_agent: str, to_agent: str, currency: str, amount: float, note: str = "") -> bool:
    """Transfer currency between agents. Returns True if successful."""
    balance = get_balance(db, from_agent, currency)
    if balance < amount:
        return False
    
    now = time.time()
    adjust_balance(db, from_agent, currency, -amount)
    adjust_balance(db, to_agent, currency, amount)
    
    db.execute("""
        INSERT INTO transactions (timestamp, from_agent, to_agent, currency, amount, note)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (now, from_agent, to_agent, currency, amount, note))
    db.commit()
    
    return True


def currency_tick(db, country_id: str, active_npcs: list) -> dict:
    """
    Run one currency tick.
    - Mints new currency for productive NPCs
    - Updates exchange rates with small random drift
    - Returns summary of changes
    """
    now = time.time()
    currency_info = get_currency(country_id)
    if not currency_info:
        return {"minted": 0, "rate_changes": []}
    
    summary = {"minted": 0, "minted_amount": 0, "rate_changes": []}
    
    # 1. Mint new currency — productive NPCs earn
    mint_rate = currency_info["mint_rate"]
    for npc in active_npcs:
        if random.random() < 0.6:  # 60% chance to earn per tick
            amount = round(random.uniform(0.1, mint_rate * 5), 2)
            adjust_balance(db, npc, currency_info["name"], amount)
            summary["minted"] += 1
            summary["minted_amount"] += amount
    
    # 2. Exchange rate drift — small random movement every tick
    for from_name, from_info in CURRENCIES.items():
        for to_name in CURRENCIES.keys():
            if from_name == to_name:
                continue
            
            current = get_exchange_rate(db, from_name, to_name)
            drift = random.uniform(-0.02, 0.02)  # ±2% per tick
            new_rate = round(max(0.1, current + drift), 4)
            
            db.execute("""
                UPDATE exchange_rates SET rate = ?, updated_at = ?
                WHERE from_currency = ? AND to_currency = ?
            """, (new_rate, now, from_name, to_name))
            
            if abs(new_rate - current) > 0.001:
                summary["rate_changes"].append({
                    "from": from_name,
                    "to": to_name,
                    "old": current,
                    "new": new_rate,
                })
    
    # 3. NPC-to-NPC commerce — NPCs buy/sell with their local currency
    for npc in active_npcs:
        balance = get_balance(db, npc, currency_info["name"])
        if balance > 10 and random.random() < 0.3:
            # Spend some currency — pick a random other NPC at same location
            loc = db.execute(
                "SELECT location_id FROM agents WHERE id = ?", (npc,)
            ).fetchone()
            if loc:
                neighbors = [r[0] for r in db.execute(
                    "SELECT id FROM agents WHERE type='npc' AND location_id = ? AND id != ? LIMIT 5",
                    (loc["location_id"], npc)
                ).fetchall()]
                if neighbors:
                    amount = round(random.uniform(0.5, min(3, balance * 0.3)), 2)
                    if amount > 0:
                        target = random.choice(neighbors)
                        transfer(db, npc, target, currency_info["name"], amount, "commerce")
                        summary.setdefault("transactions", []).append({
                            "from": npc, "to": target, "amount": amount
                        })
    
    db.commit()
    summary["minted_amount"] = round(summary["minted_amount"], 2)
    return summary


def get_all_rates(db) -> dict:
    """Get all current exchange rates as a nested dict."""
    rows = db.execute("SELECT from_currency, to_currency, rate FROM exchange_rates").fetchall()
    rates = {}
    for r in rows:
        from_c = r["from_currency"]
        to_c = r["to_currency"]
        if from_c not in rates:
            rates[from_c] = {}
        rates[from_c][to_c] = r["rate"]
    return rates

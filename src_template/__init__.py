"""
Embodied Creative World — An open-ended persistent living world
for embodied AI agents.

Architecture (17 source files, ~7,500 lines):
  world_state.py    — SQLite schema + world state management
  simulation.py     — Full world tick: time, weather, ecology, seasons, emergence, rituals
  text_engine.py    — Rich literary description + NPC dialogue
  agent.py          — Agent loop with 25+ commands
  agent_api.py      — Clean API for any agent harness
  persistence.py    — Snapshots + git versioning
  npc_generation.py — Procedural NPC generation (~200 NPCs)
  ecology.py        — Plants, animals, fish, decay, growth
  psychology.py     — Mood, memory, interests, creative impulses
  creative.py       — Building, crafting, writing, cooking, music, painting
  seasons.py        — Full year cycle with seasonal effects
  web_server.py     — HTTP server + REST API
  events.py         — Emergent event generator
  social.py         — NPC relationship evolution
  narrative.py      — Procedural narrative engine
  npc_ai.py         — Advanced NPC AI: goals, memory, autonomous action
  npc_depth.py      — Deep NPC personalities, context-sensitive dialogue
  rituals.py        — Seasonal events and rituals (8 rituals across 4 seasons)
"""

__version__ = "1.0.0"

"""03 — Trace a causal chain from the federation causal graph.

Researchers typically want to answer: "what fed this event?" rather than
"how many events are there?" This example picks a child event with at
least one parent edge in ``aurelia-federation-causal``, then walks the
chain upstream to depth 3 and prints the events, relations, and ticks.

If the local export is missing, the example prints the HuggingFace
download instructions and exits cleanly.

Usage:
    PYTHONPATH=. python3 examples/03_trace_causal_chain.py
    PYTHONPATH=. python3 examples/03_trace_causal_chain.py --run phase11-density-100y
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from examples import aurelia_dataset_loader as loader  # noqa: E402

HF_FALLBACK = """\
Local export not found at {root}.

To fetch the federation causal dataset from HuggingFace:
    python3 -c 'from datasets import load_dataset; \\
        load_dataset("OusiaResearch/aurelia-federation-causal")'

Or pass --export-root to point at an existing local mirror."""


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------

def build_parent_index(edges: list[dict]) -> dict[str, list[dict]]:
    """Group edges by their child event id.

    Returns a ``{child_event_id: [edge, …]}`` mapping. Each edge is left
    as the input dict, so callers can read ``parent_event_id``,
    ``relation``, ``weight`` directly.
    """
    index: dict[str, list[dict]] = {}
    for edge in edges:
        child = edge.get("child_event_id")
        if not child:
            continue
        index.setdefault(child, []).append(edge)
    return index


def walk_ancestors(
    start_event_id: str,
    parent_index: dict[str, list[dict]],
    *,
    depth: int = 3,
) -> list[dict]:
    """BFS upstream from ``start_event_id`` to ``depth`` hops.

    Returns a list of ``{"event_id", "depth", "via_relation", "via_weight"}``
    entries in BFS order, including the start as depth 0.
    """
    visited: set[str] = set()
    queue: list[tuple[str, int, Optional[str], Optional[float]]] = [(start_event_id, 0, None, None)]
    out: list[dict] = []
    while queue:
        ev_id, d, via_rel, via_w = queue.pop(0)
        if ev_id in visited:
            continue
        visited.add(ev_id)
        out.append({
            "event_id": ev_id,
            "depth": d,
            "via_relation": via_rel,
            "via_weight": via_w,
        })
        if d >= depth:
            continue
        for parent_edge in parent_index.get(ev_id, []):
            parent = parent_edge.get("parent_event_id")
            if parent and parent not in visited:
                queue.append((
                    parent,
                    d + 1,
                    parent_edge.get("relation"),
                    parent_edge.get("weight"),
                ))
    return out


# ---------------------------------------------------------------------------
# Data path
# ---------------------------------------------------------------------------

def _load_events_edges(run: str, root: Path) -> Optional[tuple[list[dict], list[dict]]]:
    """Load events and edges for ``run`` from the local export if present."""
    base = root / "aurelia-federation-causal" / "data" / run
    if not base.exists():
        return None
    import pyarrow.parquet as pqlib
    events_pq = base / "events.parquet"
    edges_pq = base / "edges.parquet"
    if not events_pq.exists() or not edges_pq.exists():
        return None
    events = pqlib.read_table(events_pq).to_pylist()
    edges = pqlib.read_table(edges_pq).to_pylist()
    return events, edges


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Trace a causal chain from the federation causal graph")
    p.add_argument("--export-root", default=str(loader.DEFAULT_LOCAL_ROOT))
    p.add_argument("--run", default="phase11-100y", help="Run id to inspect (default: phase11-100y)")
    p.add_argument("--depth", type=int, default=3)
    args = p.parse_args(argv)

    root = Path(args.export_root)
    if not root.exists():
        print(HF_FALLBACK.format(root=root))
        return 0

    loaded = _load_events_edges(args.run, root)
    if loaded is None:
        print(f"Could not find events.parquet/edges.parquet under {root}/aurelia-federation-causal/data/{args.run}")
        return 0

    events, edges = loaded
    if not edges:
        print(f"no edges in {args.run}")
        return 0

    by_id = {e["event_id"]: e for e in events}
    parent_index = build_parent_index(edges)

    # Pick a child event with at least one parent — prefer one with the
    # longest reachable ancestor chain.
    candidates = sorted(
        parent_index.keys(),
        key=lambda c: len(walk_ancestors(c, parent_index, depth=args.depth)),
        reverse=True,
    )
    start = candidates[0]
    chain = walk_ancestors(start, parent_index, depth=args.depth)
    chain_ids = [n["event_id"] for n in chain]
    chain_set = set(chain_ids)

    print(f"Causal chain trace — run: {args.run}, depth: {args.depth}")
    print(f"  start event: {start}\n")

    for node in chain:
        ev = by_id.get(node["event_id"], {})
        indent = "  " * (1 + node["depth"])
        prefix = "" if node["depth"] == 0 else "↳ "
        tick = ev.get("tick_number", "?")
        etype = ev.get("event_type", "?")
        world = ev.get("world_id", "?")
        if node["via_relation"] is not None:
            via = f"[{node['via_relation']} | w={node['via_weight']}]"
        else:
            via = ""
        print(f"{indent}{prefix}{node['event_id']}")
        print(f"{indent}    tick={tick}  type={etype}  world={world}  {via}")

    # Also show the downstream children of the start event, if any.
    child_edges = [e for e in edges if e.get("parent_event_id") == start]
    if child_edges:
        print(f"\n  start event also parents {len(child_edges)} downstream event(s):")
        for edge in child_edges[:5]:
            child = edge.get("child_event_id")
            print(f"    {child}  [{edge.get('relation')}]")

    print(f"\nReached {len(chain)} nodes from {start} in {len(chain) - 1} ancestor hops.")
    print(f"({len(chain_ids)} unique events visited.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

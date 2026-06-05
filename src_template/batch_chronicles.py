#!/usr/bin/env python3
"""
batch_chronicles.py — Post-simulation batch chronicle generator.

Loads a GGUF model ONCE, then generates all yearly chronicles from the
accumulated event logs and world DBs produced by a speed_run. Designed to
saturate a 96GB Blackwell GPU:

- 1× Gemma 27B Q5_K_M (~17GB) = excellent prose, ~30-50 tok/s
- 1× Qwen 72B Q4_K_M (~40GB)   = best prose, ~20-35 tok/s
- 5× Gemma 12B Q4_K_M (~35GB)   = max parallelism, ~50-80 tok/s each

Pipeline:
  Phase 1: speed_run.py --years 200 --npcs 12000  (no LLM, fast)
  Phase 2: batch_chronicles.py --model-path ... --output output/
            → reads output/*.db + output/yearly_events.json
            → generates output/chronicles/<world>_Y<year>.txt

With 96GB VRAM and 5 parallel Gemma 12B instances:
  ~1000 chronicles × 5 concurrent = 200 batches
  ~15s per chronicle batch = ~1h for 1000 chronicles

Usage:
  python3 batch_chronicles.py --model-path gemma-12b-Q4.gguf \
      --output /content/drive/MyDrive/aurelia-output --n-workers 5
"""

import os, sys, time, json, argparse, sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

COUNTRIES = ["solara", "valdris", "mirithane", "arkos", "verge"]

# ═══════════════════════════════════════════════════════════════════
# PROSE PROMPTS (standalone — no imports from rich_narrative needed)
# ═══════════════════════════════════════════════════════════════════

WORLD_PROFILES = {
    "solara": "Solara, the agricultural heartland. Rolling fields, orchards, and the gentle River Luthien. "
              "The oldest continuous human settlement in the Federation. Known for its grain, its festivals, "
              "and its quiet conservatism.",
    "valdris": "Valdris, the northern industrial power. Iron mines, forges, and the smoke-stained city of "
              "Dunmir. The Vorn population is concentrated here, working the deep seams. Cold winters, "
              "hard people, harder politics.",
    "mirithane": "Mirithane, the coastal republic of scholars and sailors. The great library at Caer Myrthin, "
                 "the shipyards at Port Selwyn. A tradition of intellectual freedom and maritime trade.",
    "arkos": "Arkos, the desert citadel. Sand-glass towers rise from the red wastes. Ancient, proud, "
             "isolated. The Glim population was decanted here first.",
    "verge": "The Verge, the frontier. A wild territory of deep forests and unmapped valleys. No central "
             "government — a patchwork of settlements, outcasts, and pioneers.",
}

SPECIES_CONTEXT = (
    "Four sentient species share this world: Humans (baseline), Threns (circuitry-integrated, "
    "emotion-reading), Vorns (stone-skinned, deep-earth attuned), and Glims (decommissioned AI, "
    "latency field capable)."
)

VOICE = (
    "Write in a literary, grounded style. Avoid fantasy clichés. "
    "This is a post-Collapse world where something was lost and something else is being built. "
    "The tone is elegiac but unsentimental, precise, attentive to sensory detail. "
    "Weather matters. Light matters. The weight of history matters. "
    "Anchor everything in specific places and named individuals."
)


def summarize_world_for_prompt(db) -> str:
    """Build a compact state summary from a world DB for LLM prompting."""
    parts = []

    # Population
    pop = db.execute(
        "SELECT COUNT(*) as c FROM agents WHERE type='npc' AND state='active'"
    ).fetchone()
    if pop:
        parts.append(f"Population: {pop['c']:,} active.")

    # Species
    species = {}
    for t in ["human", "thren", "vorn", "glim"]:
        row = db.execute(
            "SELECT COUNT(*) as c FROM agents a WHERE a.type='npc' "
            "AND a.state='active' AND json_extract(a.properties, '$.npc_type') = ?", (t,)
        ).fetchone()
        if row and row["c"]:
            species[t] = row["c"]
    if species:
        parts.append("Species: " + ", ".join(f"{k}={v}" for k, v in species.items()))

    # Time
    wt = db.execute(
        "SELECT year, month, day, season FROM world_time WHERE id=1"
    ).fetchone()
    if wt:
        parts.append(f"Year {wt['year']}, Season: {wt['season']}")

    # Factions
    active = db.execute(
        "SELECT COUNT(*) as c FROM factions WHERE status NOT IN ('dissolved','sovereign')"
    ).fetchone()
    at_war = db.execute("SELECT COUNT(*) as c FROM factions WHERE status='war'").fetchone()
    if active and active["c"] > 0:
        parts.append(f"Factions: {active['c']} active, {at_war['c']} at war")

    # Notable factions
    factions = db.execute(
        "SELECT name, status, grievance_type, member_count FROM factions "
        "WHERE status NOT IN ('dissolved','sovereign') ORDER BY member_count DESC LIMIT 5"
    ).fetchall()
    if factions:
        parts.append("Notable factions: " + "; ".join(
            f"{f['name']} ({f['status']}, {f['member_count']} members)" for f in factions
        ))

    # Economy
    eco = db.execute(
        "SELECT AVG(CAST(json_extract(variables, '$.economic_stability') AS REAL)) as e, "
        "AVG(CAST(json_extract(variables, '$.satisfaction') AS REAL)) as s "
        "FROM npc_decision_state"
    ).fetchone()
    if eco and eco["e"] is not None:
        parts.append(f"Stability: {eco['e']:.2f}, Satisfaction: {eco['s']:.2f}")

    # Discoveries, great persons
    for table, label in [("discoveries", "Discoveries"), ("great_persons", "Great Persons")]:
        c = db.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
        if c and c["c"] > 0:
            parts.append(f"{label}: {c['c']}")

    return "\n".join(parts)


def format_year_events(events: list) -> str:
    """Format a year's events into a compact summary for the prompt."""
    if not events:
        return "A quiet year. Daily life continued its rhythms."

    by_cat = defaultdict(list)
    for ev in events:
        by_cat[ev.get("category", "other")].append(ev)

    parts = []
    for cat, evs in sorted(by_cat.items()):
        if len(evs) == 1:
            e = evs[0]
            parts.append(f"[{cat}] {e['title']}: {e['description'][:200]}")
        else:
            titles = "; ".join(e.get("title", "event")[:60] for e in evs[:5])
            parts.append(f"[{cat}] {len(evs)} events: {titles}")

    return "\n".join(parts[:12])


def build_chronicle_messages(world_id: str, world_context: str, year_summary: str,
                              year_number: int) -> list:
    """Build the messages array for a single chronicle generation."""
    system = (
        f"You are the narrator of the Aurelia Federation simulation: {world_id.title()}.\n\n"
        f"{WORLD_PROFILES.get(world_id, '')}\n\n{SPECIES_CONTEXT}\n\n{VOICE}"
    )
    prompt = (
        f"This is the end of Year {year_number} in {world_id.title()}.\n\n"
        f"Events of the year:\n{year_summary}\n\n"
        f"Current state:\n{world_context}\n\n"
        f"Write a chronicle entry for Year {year_number}. Structure:\n"
        f"1. Header: 'Year {year_number} — {world_id.title()}'\n"
        f"2. 1-2 paragraph overview of the year's major developments\n"
        f"3. Notable individuals — name them, describe their actions\n"
        f"4. The mood of the world as the year closes\n\n"
        f"This should read like a history, not a report. Ground everything in sensory texture. "
        f"Make it feel REAL."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]


# ═══════════════════════════════════════════════════════════════════
# BATCH PROCESSOR
# ═══════════════════════════════════════════════════════════════════

def generate_one_chronicle(client, messages: list, year_num: int, max_tokens: int = 800) -> Optional[str]:
    """Generate a single chronicle. Returns None on failure."""
    try:
        return client.chat(messages, temperature=0.7, max_tokens=max_tokens)
    except Exception:
        return None


def batch_generate(worlds: List[str], year_range: range, events_data: dict,
                   world_db_paths: Dict[str, str], client, output_dir: Path,
                   max_tokens: int = 800):
    """Generate all chronicles for all worlds across a year range."""
    chronicles_dir = output_dir / "chronicles"
    chronicles_dir.mkdir(exist_ok=True)

    total = len(worlds) * len(year_range)
    done = 0
    t0 = time.time()

    for year_num in year_range:
        for world_id in worlds:
            # Skip if already generated
            chronicle_path = chronicles_dir / f"{world_id}_Y{year_num:04d}.txt"
            if chronicle_path.exists():
                done += 1
                continue

            # Get events for this year+world
            year_events = events_data.get(str(year_num), {}).get(world_id, [])
            summary = format_year_events(year_events)

            # Get world context
            context = "World state unavailable."
            if world_id in world_db_paths:
                try:
                    db = sqlite3.connect(world_db_paths[world_id])
                    db.row_factory = sqlite3.Row
                    context = summarize_world_for_prompt(db)
                    db.close()
                except Exception:
                    pass

            # Generate
            messages = build_chronicle_messages(world_id, context, summary, year_num)
            result = generate_one_chronicle(client, messages, year_num, max_tokens)

            if result:
                with open(chronicle_path, "w") as f:
                    f.write(result)
                done += 1

                if done % 10 == 0 or done == total:
                    elapsed = time.time() - t0
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (total - done) / rate if rate > 0 else 0
                    print(f"  [{done}/{total}] {rate:.1f}/s | ETA: {eta/60:.0f}m")
            else:
                # Template fallback
                fallback = f"Year {year_num} — {world_id.title()}\n\n{summary}\n"
                with open(chronicle_path, "w") as f:
                    f.write(fallback)
                done += 1
                print(f"  [{done}/{total}] {world_id} Y{year_num}: fallback")

    print(f"  Complete: {done} chronicles in {time.time()-t0:.0f}s")


# ═══════════════════════════════════════════════════════════════════
# GRID SCHEDULER (parallel workers, one model each)
# ═══════════════════════════════════════════════════════════════════

class WorldWorker:
    """A worker that handles one world's chronicle generation."""
    
    def __init__(self, model_path: str, world_id: str, n_ctx: int = 4096, 
                 n_gpu_layers: int = -1):
        self.world_id = world_id
        self.model_path = model_path
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            from llama_cpp import Llama
            self._client = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
                n_threads=4,
            )
        return self._client
    
    def generate(self, messages: list, max_tokens: int = 800) -> Optional[str]:
        try:
            result = self.client.create_chat_completion(
                messages=messages, temperature=0.7, max_tokens=max_tokens
            )
            return result["choices"][0]["message"]["content"].strip()
        except Exception:
            return None


def grid_generate(worlds: List[str], year_range: range, events_data: dict,
                  world_db_paths: Dict[str, str], model_path: str, output_dir: Path,
                  n_workers: int = 5, n_ctx: int = 4096, max_tokens: int = 800):
    """
    Generate chronicles using one llama.cpp instance PER WORLD, all in parallel.
    Saturates a large-GPU VRAM budget. With 5× Gemma 12B Q4 (~35GB), 
    96GB Blackwell handles this comfortably.
    """
    chronicles_dir = output_dir / "chronicles"
    chronicles_dir.mkdir(exist_ok=True)

    # Create one worker per world (up to n_workers)
    active_workers = []
    for world_id in worlds[:n_workers]:
        worker = WorldWorker(model_path, world_id, n_ctx, n_gpu_layers=-1)
        active_workers.append(worker)
    
    print(f"  Loaded {len(active_workers)} parallel model instances ({len(active_workers)}× model in VRAM)")
    
    # Build task list: (worker_idx, year, world_id)
    tasks = []
    worker_map = {w.world_id: i for i, w in enumerate(active_workers)}
    
    for year_num in year_range:
        for world_id in worlds:
            if world_id in worker_map:
                tasks.append((worker_map[world_id], year_num))
    
    # Skip already-generated
    pending_tasks = []
    for worker_idx, year_num in tasks:
        world_id = active_workers[worker_idx].world_id
        chronicle_path = chronicles_dir / f"{world_id}_Y{year_num:04d}.txt"
        if not chronicle_path.exists():
            pending_tasks.append((worker_idx, year_num, world_id))
    
    skipped = len(tasks) - len(pending_tasks)
    if skipped:
        print(f"  Skipping {skipped} already-generated chronicles")
    
    total = len(pending_tasks)
    print(f"  Generating {total} chronicles across {len(active_workers)} parallel workers...")
    
    done = 0
    t0 = time.time()
    
    def process_task(worker_idx, year_num, world_id):
        worker = active_workers[worker_idx]
        
        # Get events
        year_events = events_data.get(str(year_num), {}).get(world_id, [])
        summary = format_year_events(year_events)
        
        # World context
        context = "World state unavailable."
        if world_id in world_db_paths:
            try:
                db = sqlite3.connect(world_db_paths[world_id])
                db.row_factory = sqlite3.Row
                context = summarize_world_for_prompt(db)
                db.close()
            except Exception:
                pass
        
        messages = build_chronicle_messages(world_id, context, summary, year_num)
        result = worker.generate(messages, max_tokens)
        
        chronicle_path = chronicles_dir / f"{world_id}_Y{year_num:04d}.txt"
        if result:
            with open(chronicle_path, "w") as f:
                f.write(result)
        else:
            with open(chronicle_path, "w") as f:
                f.write(f"Year {year_num} — {world_id.title()}\n\n{summary}\n")
        
        return (year_num, world_id, bool(result))
    
    # Process with ThreadPoolExecutor — llama.cpp GPU ops are parallel-friendly
    # since each worker has its own model instance
    with ThreadPoolExecutor(max_workers=len(active_workers)) as executor:
        futures = {}
        for worker_idx, year_num, world_id in pending_tasks[:len(active_workers)]:
            f = executor.submit(process_task, worker_idx, year_num, world_id)
            futures[f] = (worker_idx, year_num, world_id)
        
        pending = pending_tasks[len(active_workers):]
        
        while futures:
            for f in as_completed(futures):
                year_num, world_id, success = f.result()
                done += 1
                del futures[f]
                
                # Submit next pending task
                if pending:
                    worker_idx, year_num, world_id = pending.pop(0)
                    new_f = executor.submit(process_task, worker_idx, year_num, world_id)
                    futures[new_f] = (worker_idx, year_num, world_id)
                
                if done % 10 == 0 or done == total:
                    elapsed = time.time() - t0
                    rate = done / elapsed if elapsed > 0 else 0
                    eta = (total - done) / rate if rate > 0 else 0
                    print(f"  [{done}/{total}] {rate:.1f}/s | ETA: {eta/60:.0f}m")
    
    print(f"  Complete: {done} chronicles in {time.time()-t0:.0f}s")


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Batch-generate Aurelia yearly chronicles from speed_run output"
    )
    parser.add_argument("--model-path", required=True, help="Path to GGUF model file")
    parser.add_argument("--output", required=True, help="Path to speed_run output directory")
    parser.add_argument("--n-workers", type=int, default=1,
                       help="Parallel model instances (1-8). With 96GB VRAM: "
                            "3x Gemma 27B Q5 (~51GB), 5x Gemma 12B Q4 (~35GB), "
                            "8x Gemma 4B Q4 (~20GB)")
    parser.add_argument("--n-ctx", type=int, default=4096)
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument("--worlds", type=str, default="solara,valdris,mirithane,arkos,verge")
    parser.add_argument("--years", type=int, default=None,
                       help="Override years (default: detect from DB)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    worlds = [w.strip() for w in args.worlds.split(",")]

    if not output_dir.exists():
        print(f"ERROR: Output dir not found: {output_dir}")
        sys.exit(1)

    # Load yearly events
    events_path = output_dir / "yearly_events.json"
    events_data = {}
    if events_path.exists():
        with open(events_path) as f:
            events_data = json.load(f)
        print(f"Loaded events: {sum(len(v) for v in events_data.values())} year buckets")
    else:
        print("No yearly_events.json — all years treated as quiet")
        events_data = {}

    # Find world DBs
    world_db_paths = {}
    for world_id in worlds:
        db_path = output_dir / f"{world_id}.db"
        if db_path.exists():
            world_db_paths[world_id] = str(db_path)
        else:
            print(f"WARNING: No DB for {world_id} at {db_path}")

    # Detect year range
    if args.years:
        year_range = range(1, args.years + 1)
    else:
        # Detect from events or DB
        if events_data:
            max_year = max(int(y) for y in events_data.keys())
            year_range = range(1, max_year + 1)
        elif world_db_paths:
            db_path = list(world_db_paths.values())[0]
            db = sqlite3.connect(db_path)
            db.row_factory = sqlite3.Row
            wt = db.execute("SELECT year FROM world_time WHERE id=1").fetchone()
            db.close()
            max_year = wt["year"] if wt else 200
            year_range = range(1, max_year + 1)
        else:
            year_range = range(1, 201)  # default

    print("=" * 60)
    print("AURELIA BATCH CHRONICLES")
    print(f"  Model: {args.model_path}")
    print(f"  Workers: {args.n_workers} parallel")
    print(f"  Worlds: {worlds}")
    print(f"  Years: {year_range.start}-{year_range.stop - 1} ({len(year_range) * len(worlds)} chronicles)")
    print(f"  VRAM: ~{args.n_workers * 7:.0f}-{args.n_workers * 17:.0f}GB (est)")
    print(f"  Output: {output_dir}")
    print("=" * 60)

    if args.n_workers > 1:
        grid_generate(
            worlds, year_range, events_data, world_db_paths,
            args.model_path, output_dir, args.n_workers,
            args.n_ctx, args.max_tokens
        )
    else:
        # Single-worker mode: load model once, sequential
        print("\n── Loading model ──")
        from llama_cpp import Llama
        client = Llama(
            model_path=args.model_path,
            n_ctx=args.n_ctx,
            n_gpu_layers=-1,
            verbose=False,
        )
        print(f"  Model loaded.")

        batch_generate(
            worlds, year_range, events_data, world_db_paths,
            client, output_dir, args.max_tokens
        )

    print(f"\nDone. Chronicles: {output_dir}/chronicles/")
    chronicle_files = list((output_dir / "chronicles").glob("*.txt"))
    if chronicle_files:
        total_chars = sum(f.stat().st_size for f in chronicle_files)
        print(f"  {len(chronicle_files)} files, {total_chars/1024:.0f}KB total")


if __name__ == "__main__":
    main()

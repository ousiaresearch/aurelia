"""
web_server.py — Serves the web visual layer and bridges to the simulation.

Runs an HTTP server that:
- Serves the HTML/CSS/JS frontend
- Provides a REST API for world state
- Runs a WebSocket for live updates
- Bridges player actions to the simulation engine
"""

import json
import time
import threading
import asyncio
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Optional, Set
import socket
import os

from .world_state import get_db as _module_get_db, get_world, init_world, seed_world, DB_PATH, canonicalize_location_id, get_world_identity
from .agent import Agent
from .simulation import tick
from .ecology import init_ecology
from .persistence import save_snapshot, commit_snapshot

# Try to import websockets for live updates
try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False
    websockets = None


WEB_DIR = Path(__file__).parent.parent / "web"
API_PREFIX = "/api"


# ── WEBSOCKET BROADCAST MANAGER ──────────────────────────────────────────────

class BroadcastManager:
    """Thread-safe WebSocket broadcast manager.

    Runs an async event loop in a daemon thread, broadcasting world-state
    snapshots to all connected clients whenever the simulation advances.
    """

    def __init__(self):
        self._clients: Set = set()
        self._lock = threading.Lock()
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._runner: threading.Thread | None = None
        self._stop_event = threading.Event()
        # Queue of broadcast payloads; enqueued from HTTP thread, dequeued in event loop
        self._queue: list = []
        self._queue_lock = threading.Lock()

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        if self._event_loop is None or self._event_loop.is_closed():
            self._event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._event_loop)
        return self._event_loop

    def start(self):
        """Start the async broadcast thread."""
        if not HAS_WEBSOCKETS:
            return
        if self._runner is not None and self._runner.is_alive():
            return

        self._stop_event.clear()
        self._runner = threading.Thread(target=self._run_loop, daemon=True, name="ws-broadcast")
        self._runner.start()

    def _run_loop(self):
        """Async event loop running in daemon thread — broadcasts queued payloads."""
        loop = self._get_event_loop()
        while not self._stop_event.is_set():
            # Process queued payloads
            payload = None
            with self._queue_lock:
                if self._queue:
                    payload = self._queue.pop(0)

            if payload:
                # Fire-and-forget broadcast; collect dead clients
                dead = set()
                for client in list(self._clients):
                    try:
                        async def send_ws(ws, msg):
                            await ws.send(json.dumps(msg, default=str))
                        loop.run_until_complete(send_ws(client, payload))
                    except Exception:
                        dead.add(client)
                # Prune dead clients
                if dead:
                    with self._lock:
                        self._clients -= dead
            else:
                # No work — sleep briefly before checking again
                time.sleep(0.05)

        # Cleanup
        loop = self._get_event_loop()
        if loop.is_running():
            loop.close()
        self._event_loop = None

    def stop(self):
        """Stop the broadcast thread."""
        self._stop_event.set()
        if self._runner:
            self._runner.join(timeout=2.0)

    def register(self, websocket):
        """Register a new WebSocket client."""
        with self._lock:
            self._clients.add(websocket)

    def unregister(self, websocket):
        """Unregister a WebSocket client."""
        with self._lock:
            self._clients.discard(websocket)

    def enqueue(self, payload: dict):
        """Enqueue a payload for broadcast. Called from HTTP thread."""
        if not HAS_WEBSOCKETS:
            return
        with self._queue_lock:
            self._queue.append(payload)

    @property
    def client_count(self) -> int:
        return len(self._clients)


# ── SHARED BROADCAST INSTANCE ─────────────────────────────────────────────────

_broadcast = BroadcastManager()


def get_broadcast() -> BroadcastManager:
    return _broadcast


# ── HTTP HANDLER ──────────────────────────────────────────────────────────────

class WorldAPIHandler(SimpleHTTPRequestHandler):
    """HTTP handler that serves the frontend, handles API calls, and manages WebSocket upgrades."""

    def __init__(self, *args, agent=None, **kwargs):
        self.agent = agent
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def _player_id(self) -> str:
        return getattr(self.agent, "player_id", "owl")

    def _player_location_id(self) -> str:
        player = self.agent.world.get("agents", {}).get(self._player_id(), {})
        location_id = player.get("location_id", "cabin_bedroom")
        return canonicalize_location_id(self.agent.db, location_id) or "cabin_bedroom"

    def handle(self):
        """Handle one client connection without noisy tracebacks on client disconnects."""
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Browsers and smoke tests can close a socket before large static
            # assets finish streaming. The request is already gone; keep the
            # server alive and avoid dumping traceback noise into launch logs.
            pass

    def copyfile(self, source, outputfile):
        """Stream static files, treating early client disconnects as benign."""
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self):
        if self.path.startswith(API_PREFIX):
            self._handle_api_get()
        elif self.path == "/ws":
            # WebSocket upgrade — handled in do_WS if we had async support,
            # but SimpleHTTPRequestHandler can't do that cleanly.
            # Instead, ws.html handles the handshake via a passthrough server.
            self.send_error(404)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith(API_PREFIX):
            self._handle_api_post()
        else:
            self.send_error(404)

    def _handle_api_get(self):
        """Handle API GET requests."""
        path = self.path[len(API_PREFIX):]

        if path == "/ws_port":
            # Return the WebSocket port so ws.html can discover it
            ws_port = getattr(_broadcast, "_ws_port", None)
            self._json_response({"ws_port": ws_port})
            return

        elif path == "/world-identity":
            db = _module_get_db()
            identity = get_world_identity(db)
            self._json_response(identity if identity else {"world_id": None, "error": "world not registered"})
            return

        elif path == "/world" or path == "/":
            db = _module_get_db()
            world = get_world(db)
            self._json_response(world)

        elif path == "/ui-state":
            from .ui_state import build_ui_state
            self.agent.world = get_world(self.agent.db)
            self._json_response(build_ui_state(self.agent))

        elif path == "/location":
            location_id = self._player_location_id()
            from .text_engine import describe_location
            desc = describe_location(self.agent.db, location_id, self.agent.world)
            self._json_response({"description": desc, "location_id": location_id})

        elif path == "/status":
            body = self.agent.world.get("body", {})
            internal = self.agent.world.get("internal", {})
            time_info = self.agent.world.get("time", {})
            weather = self.agent.world.get("weather", {})
            self._json_response({
                "body": body, "internal": internal, "time": time_info, "weather": weather,
            })

        elif path == "/economy":
            from .economy import get_inventory, get_all_inventories, RESOURCE_DEFINITIONS
            inv = get_inventory(self.agent.db, self._player_id())
            all_inv = get_all_inventories(self.agent.db)
            definitions = {k: {"name": v["name"], "unit": v["unit"]} for k, v in RESOURCE_DEFINITIONS.items()}
            self._json_response({"player_inventory": inv, "all_inventories": all_inv, "definitions": definitions})

        elif path == "/goals":
            from .goals import get_active_goals, get_all_goals
            active = get_active_goals(self.agent.db, self._player_id())
            all_goals = get_all_goals(self.agent.db, self._player_id())
            self._json_response({"active": active, "all": all_goals, "count": len(active)})

        elif path == "/outputs":
            from .creative_output import get_recent_outputs
            outputs = get_recent_outputs(self.agent.db, self._player_id(), limit=20)
            self._json_response({"outputs": outputs, "count": len(outputs)})

        elif path == "/events":
            events = self.agent.db.execute("""
                SELECT * FROM events ORDER BY timestamp DESC LIMIT 50
            """).fetchall()
            self._json_response({"events": [dict(e) for e in events]})

        elif path == "/exits":
            from .world_state import get_exits_from
            location_id = self._player_location_id()
            exits = get_exits_from(self.agent.db, location_id)
            self._json_response({"exits": exits})

        elif path == "/npcs":
            from .world_state import get_agents_in_location
            location_id = self._player_location_id()
            npcs = get_agents_in_location(self.agent.db, location_id)
            self._json_response({"npcs": [n for n in npcs if n.get("type") != "player"]})

        elif path == "/projects":
            from .creative import get_active_projects, get_completed_projects
            active = get_active_projects(self.agent.db)
            completed = get_completed_projects(self.agent.db)
            self._json_response({"active": active, "completed": completed})

        elif path == "/ecology":
            try:
                from .ecology import get_location_ecology, init_ecology
                init_ecology(self.agent.db)
                location_id = self._player_location_id()
                eco = get_location_ecology(self.agent.db, location_id)
                self._json_response(eco)
            except Exception as e:
                self._json_response({"plants": [], "animals": [], "fish": [], "error": str(e)})

        elif path == "/stories":
            try:
                from .narrative_arcs import get_arc_status_summary, init_narrative_tables
                init_narrative_tables(self.agent.db)
                arcs = get_arc_status_summary(self.agent.db)
                self._json_response({"arcs": arcs})
            except Exception as e:
                self._json_response({"arcs": [], "error": str(e)})

        elif path == "/seasonal-tone":
            from .narrative_arcs import get_seasonal_narrative_tone
            season = self.agent.world.get("time", {}).get("season", "spring")
            active_arcs = self.agent.db.execute("SELECT COUNT(*) as c FROM story_arcs WHERE active = 1").fetchone()
            count = active_arcs["c"] if active_arcs else 0
            tone = get_seasonal_narrative_tone(season, count)
            self._json_response({"season": season, "arcs_active": count, "tone": tone})

        elif path.startswith("/npcs-at"):
            from .world_state import get_agents_in_location
            loc = ""
            if "?" in path:
                query = path.split("?", 1)[1]
                params = {}
                for pair in query.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        params[k] = v
                loc = params.get("location_id", "")
            if loc:
                npcs = get_agents_in_location(self.agent.db, loc)
                self._json_response({"npcs": [n for n in npcs if n.get("type") != "player"]})
            else:
                self._json_response({"npcs": []})

        elif path == "/daemon-narrative":
            log_path = os.path.join(os.path.dirname(__file__), "..", "world", "narrative_log.jsonl")
            entries = []
            if os.path.exists(log_path):
                with open(log_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                entries.append(json.loads(line))
                            except json.JSONDecodeError:
                                pass
            entries = entries[-30:]
            self._json_response({"entries": entries})

        elif path == "/upcoming-rituals":
            from .rituals import get_upcoming_rituals
            try:
                upcoming = get_upcoming_rituals(self.agent.db)
                self._json_response({"upcoming": upcoming})
            except Exception as e:
                self._json_response({"upcoming": [], "error": str(e)})

        elif path == "/exploration":
            from .world_state import get_exploration_status
            try:
                status = get_exploration_status(self.agent.db, self._player_id())
                self._json_response(status)
            except Exception as e:
                self._json_response({"discovered": [], "visited": {}, "error": str(e)})

        elif path == "/map":
            from .map_state import build_map_state
            db = _module_get_db()
            self._json_response(build_map_state(db))

        elif path == "/rituals-status":
            from .rituals import get_ritual_status
            db = _module_get_db()
            self._json_response(get_ritual_status(db))

        else:
            self.send_error(404)

    def _handle_api_post(self):
        """Handle API POST requests (player actions)."""
        path = self.path[len(API_PREFIX):]
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        result = {"success": False, "message": "Unknown command"}

        if path == "/action":
            action = data.get("action", "")
            target = data.get("target", None)
            if action:
                result_text = self.agent.act(action, target)
                result = {"success": True, "result": result_text}
                # Refresh world after action
                self.agent.world = get_world(self.agent.db)

        elif path == "/advance":
            hours = data.get("hours", 1.0)
            tick_result = tick(self.agent.db, hours)
            self.agent.world = get_world(self.agent.db)

            # Enqueue a broadcast to all WS clients
            world_snapshot = get_world(self.agent.db)
            _broadcast.enqueue({
                "type": "tick",
                "time": tick_result.get("time", {}),
                "weather": tick_result.get("weather", {}),
                "body": tick_result.get("body", {}),
                "world": world_snapshot,
            })

            result = {
                "success": True,
                "tick": {
                    "time": tick_result.get("time", {}),
                    "weather": tick_result.get("weather", {}),
                    "body": tick_result.get("body", {}),
                    "ritual_events": tick_result.get("ritual_events", []),
                    "narrative_moments": tick_result.get("narrative_moments", []),
                }
            }

        elif path == "/save":
            path_result, msg = self.agent.save(data.get("message", "web save"))
            result = {"success": True, "snapshot": str(path_result)}

        elif path == "/traveler-arrive":
            agent_id = data.get("agent_id", "")
            from_world = data.get("from_world", "")
            route = data.get("route", "")
            entry_loc = self._player_location_id() or "town_hwy58"
            # Insert the arriving agent into this world
            now = time.time()
            db = _module_get_db()
            db.execute("""
                INSERT OR REPLACE INTO agents (id, name, type, location_id, state, properties, created_at, updated_at)
                VALUES (?, ?, 'visitor', ?, 'active', '{}', ?, ?)
            """, (agent_id, agent_id, entry_loc, now, now))
            db.execute("""
                INSERT INTO events (timestamp, event_type, description, agent_id, location_id)
                VALUES (?, 'arrival', ?, ?, ?)
            """, (now, f"{agent_id} arrived from {from_world} via {route}", agent_id, entry_loc))
            db.commit()
            self.agent.world = get_world(self.agent.db)
            result = {
                "success": True,
                "agent_id": agent_id,
                "arrived_at": entry_loc,
                "from_world": from_world,
            }

        self._json_response(result)

    def _json_response(self, data):
        """Send a JSON response."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def log_message(self, format, *args):
        """Suppress default logging to keep output clean."""
        pass


# ── WEBSOCKET SERVER ─────────────────────────────────────────────────────────

async def _ws_handler(websocket, path, agent):
    """Handle a single WebSocket client connection."""
    _broadcast.register(websocket)
    try:
        # Send initial state
        db = _module_get_db()
        world = get_world(db)
        await websocket.send(json.dumps({"type": "init", "world": world}, default=str))

        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            # Client can send { "action": "...", "target": null } to act
            action = data.get("action")
            if action:
                # NOTE: act() is synchronous; run it in a thread pool to avoid
                # blocking the async event loop. The response is not sent back
                # over WS — the HTTP poll (via /advance) is what drives ticks.
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: agent.act(action, data.get("target")))
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        _broadcast.unregister(websocket)


class WSServer:
    """Standalone WebSocket server that shares the agent with the HTTP server."""

    def __init__(self, agent, host="127.0.0.1", port=8766):
        self.agent = agent
        self.host = host
        self.port = port
        self._server = None

    def start(self):
        if not HAS_WEBSOCKETS:
            print("WebSocket server: websockets library not available — WS disabled")
            return

        async def runner():
            self._server = await websockets.serve(
                lambda ws, path: _ws_handler(ws, path, self.agent),
                self.host, self.port,
            )
            print(f"WebSocket server running at ws://{self.host}:{self.port}")

        asyncio.run(runner())

    def stop(self):
        if self._server:
            self._server.close()
            asyncio.run(self._server.wait_closed())


# ── FIND FREE PORT ────────────────────────────────────────────────────────────

def find_free_port(start=8765) -> int:
    """Find an available port starting from `start`."""
    for port in range(start, start + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start


# ── SERVER FACTORY ────────────────────────────────────────────────────────────

def create_handler_class(agent):
    """Create a handler class bound to an agent."""
    class Handler(WorldAPIHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, agent=agent, **kwargs)
    return Handler


def start_web_server(host="127.0.0.1", port=None, agent=None):
    """Start the HTTP + optional WebSocket server."""
    if port is None:
        port = find_free_port(8765)

    handler = create_handler_class(agent)
    server = HTTPServer((host, port), handler)

    if HAS_WEBSOCKETS:
        ws_port = find_free_port(port + 1)
        ws_server = WSServer(agent, host, ws_port)
        _broadcast._ws_port = ws_port  # persist for /api/ws_port endpoint
        # Run WS server in background thread so it doesn't block
        ws_thread = threading.Thread(target=ws_server.start, daemon=True)
        ws_thread.start()
        print(f"Web server running at http://{host}:{port}")
        print(f"WebSocket server running at ws://{host}:{ws_port}")
    else:
        print(f"Web server running at http://{host}:{port}  (WebSocket unavailable — install websockets package)")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


def run_web_mode(host="127.0.0.1", port=None, agent_id=None):
    """Initialize world and start the web server."""
    if not DB_PATH.exists():
        print("Initializing PNW Isildur world...")
        from .main import init_pnw_runtime_world
        init_pnw_runtime_world()

    agent = Agent(player_id=agent_id)
    player_loc = agent.world.get("agents", {}).get(agent.player_id, {}).get("location_id", "?")
    print(f"World loaded. {agent.player_id} is at: {player_loc}")

    # Start the broadcast manager
    _broadcast.start()

    start_web_server(host, port, agent)
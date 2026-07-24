import argparse
import json
import mimetypes
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from algorithms import run_search
from level_loader import get_level_name, load_level


BASE_DIR = Path(__file__).resolve().parent
LEVELS_DIR = BASE_DIR / "levels"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
VISUALIZATION_INTERVAL = 25
MAX_TRACE_STATES = 240


def discover_levels():
    return sorted(
        LEVELS_DIR.glob("*.json"),
        key=lambda path: path.name.lower(),
    )


def serialize_state(state):
    if state is None:
        return None

    return {
        "r": state.r,
        "c": state.c,
        "orient": state.orient,
        "is_split": state.is_split,
        "cube2_r": state.cube2_r,
        "cube2_c": state.cube2_c,
        "active_cube": state.active_cube,
        "positions": [list(position) for position in state.get_positions()],
        "bridge_states": dict(state.bridge_states),
    }


def serialize_board(board):
    bridge_cells = {}

    for bridge_id, info in board.bridges.items():
        for cell in info["cells"]:
            bridge_cells[f"{cell[0]},{cell[1]}"] = bridge_id

    switches = []

    for position, info in board.switches.items():
        switch_data = {
            "position": list(position),
            **info,
        }
        switches.append(switch_data)

    return {
        "rows": board.rows,
        "cols": board.cols,
        "grid": ["".join(row) for row in board.grid],
        "goal_pos": list(board.goal_pos),
        "bridge_cells": bridge_cells,
        "bridges": {
            bridge_id: {
                "cells": [list(cell) for cell in sorted(info["cells"])],
                "initial_open": bool(info.get("initial_open", False)),
            }
            for bridge_id, info in board.bridges.items()
        },
        "switches": switches,
    }


class GameSession:
    def __init__(self):
        self.lock = threading.RLock()
        self.level_path = None
        self.board = None
        self.state = None
        self.lost = False
        self.won = False
        self.last_solution = []
        self.last_algorithm = None

        levels = discover_levels()
        if levels:
            self.load_level(levels[0].name)

    def get_level_path(self, level_name):
        candidate = (LEVELS_DIR / level_name).resolve()

        if candidate.parent != LEVELS_DIR.resolve():
            raise ValueError("Invalid level path.")

        if candidate.suffix.lower() != ".json" or not candidate.exists():
            raise ValueError(f"Unknown level: {level_name}")

        return candidate

    def load_level(self, level_name):
        with self.lock:
            level_path = self.get_level_path(level_name)
            board = load_level(level_path)

            self.level_path = level_path
            self.board = board
            self.state = board.start_state
            self.lost = False
            self.won = False
            self.last_solution = []
            self.last_algorithm = None

            return self.snapshot()

    def restart(self):
        with self.lock:
            if self.board is None:
                raise RuntimeError("No level is loaded.")

            self.state = self.board.start_state
            self.lost = False
            self.won = False
            return self.snapshot()

    def move(self, action):
        with self.lock:
            if self.board is None or self.state is None:
                raise RuntimeError("No level is loaded.")

            if self.lost:
                return {
                    **self.snapshot(),
                    "message": "The game is over. Restart the level to continue.",
                }

            if self.won:
                return {
                    **self.snapshot(),
                    "message": "The level is already solved.",
                }

            if action == "SWITCH_CUBE" and not self.state.is_split:
                return {
                    **self.snapshot(),
                    "message": "The block is not split.",
                }

            next_state = self.board.transition(self.state, action)

            if next_state is None:
                self.lost = True
                self.won = False
                return {
                    **self.snapshot(),
                    "invalid_move": True,
                    "action": action,
                    "message": "Invalid move: the block fell from the board.",
                }

            self.state = next_state
            self.won = self.board.is_goal(self.state)

            return {
                **self.snapshot(),
                "invalid_move": False,
                "action": action,
                "message": "You win!" if self.won else f"Move: {action}",
            }

    def solve(self, algorithm, visualize=True):
        with self.lock:
            if self.level_path is None:
                raise RuntimeError("No level is loaded.")
            level_path = self.level_path

        search_board = load_level(level_path)
        trace = []

        def on_expand(state, expanded_nodes, frontier_size):
            if not visualize:
                return

            if (
                expanded_nodes == 1
                or expanded_nodes % VISUALIZATION_INTERVAL == 0
            ) and len(trace) < MAX_TRACE_STATES:
                trace.append(
                    {
                        "state": serialize_state(state),
                        "expanded_nodes": expanded_nodes,
                        "frontier_size": frontier_size,
                    }
                )

        result = run_search(
            search_board,
            algorithm,
            on_expand=on_expand if visualize else None,
        )

        with self.lock:
            self.last_solution = list(result["path"] or [])
            self.last_algorithm = algorithm

        return {
            **result,
            "search_trace": trace,
        }

    def snapshot(self):
        if self.board is None:
            return {
                "level": None,
                "board": None,
                "state": None,
                "lost": False,
                "won": False,
            }

        return {
            "level": self.level_path.name if self.level_path else None,
            "board": serialize_board(self.board),
            "state": serialize_state(self.state),
            "lost": self.lost,
            "won": self.won,
        }


SESSION = GameSession()


class BloxorzRequestHandler(BaseHTTPRequestHandler):
    server_version = "BloxorzWeb/1.0"

    def log_message(self, format_string, *args):
        print(
            f"[{self.log_date_time_string()}] "
            f"{self.address_string()} - {format_string % args}"
        )

    def send_json(self, payload, status=HTTPStatus.OK):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, file_path, content_type=None):
        if not file_path.exists() or not file_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        data = file_path.read_bytes()
        guessed_type = content_type or mimetypes.guess_type(file_path.name)[0]
        self.send_response(HTTPStatus.OK)
        self.send_header(
            "Content-Type",
            guessed_type or "application/octet-stream",
        )
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length == 0:
            return {}

        raw_body = self.rfile.read(content_length)
        return json.loads(raw_body.decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            if path == "/":
                self.send_file(
                    TEMPLATES_DIR / "index.html",
                    "text/html; charset=utf-8",
                )
                return

            if path == "/api/levels":
                levels = [
                    {
                        "file": level_path.name,
                        "name": get_level_name(level_path),
                    }
                    for level_path in discover_levels()
                ]
                self.send_json({"levels": levels})
                return

            if path == "/api/state":
                with SESSION.lock:
                    self.send_json(SESSION.snapshot())
                return

            if path.startswith("/static/"):
                relative = path[len("/static/") :]
                requested = (STATIC_DIR / relative).resolve()

                if requested.parent != STATIC_DIR.resolve():
                    self.send_error(HTTPStatus.FORBIDDEN)
                    return

                self.send_file(requested)
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        except Exception as error:
            self.send_json(
                {"error": str(error)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            payload = self.read_json_body()

            if path == "/api/new-game":
                level_name = payload.get("level")
                if not level_name:
                    raise ValueError("Missing level name.")
                self.send_json(SESSION.load_level(level_name))
                return

            if path == "/api/restart":
                self.send_json(SESSION.restart())
                return

            if path == "/api/move":
                action = payload.get("action")
                if action not in {
                    "UP",
                    "DOWN",
                    "LEFT",
                    "RIGHT",
                    "SWITCH_CUBE",
                }:
                    raise ValueError(f"Invalid action: {action}")
                self.send_json(SESSION.move(action))
                return

            if path == "/api/solve":
                algorithm = payload.get("algorithm")
                if algorithm not in {"BFS", "DFS", "UCS", "A*"}:
                    raise ValueError(f"Invalid algorithm: {algorithm}")

                visualize = bool(payload.get("visualize", True))
                self.send_json(SESSION.solve(algorithm, visualize=visualize))
                return

            self.send_error(HTTPStatus.NOT_FOUND)

        except ValueError as error:
            self.send_json(
                {"error": str(error)},
                status=HTTPStatus.BAD_REQUEST,
            )
        except Exception as error:
            self.send_json(
                {"error": str(error)},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )


def run_server(host=DEFAULT_HOST, port=DEFAULT_PORT, open_browser=True):
    address = (host, port)
    server = ThreadingHTTPServer(address, BloxorzRequestHandler)
    url = f"http://{host}:{port}"

    print("Bloxorz Web 3D GUI")
    print(f"Server running at: {url}")
    print("Press Ctrl+C to stop the server.")

    if open_browser:
        timer = threading.Timer(
            0.7,
            lambda: webbrowser.open(url),
        )
        timer.daemon = True
        timer.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


def main():
    parser = argparse.ArgumentParser(
        description="Run the Bloxorz HTML/Three.js GUI."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically.",
    )
    args = parser.parse_args()

    run_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
    )


if __name__ == "__main__":
    main()

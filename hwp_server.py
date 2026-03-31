"""Legacy HTTP helper kept for backward compatibility.

The current recommended entry surface is the shell runner plus `hwp_protocol/`
CLI modules. This file remains in the repository because older docs and local
workflows may still reference it.
"""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import subprocess
import tempfile
import os

REPO_ROOT = Path(os.environ.get("HWP_REPO_PATH") or Path(__file__).resolve().parent)
LOGS_DIR = REPO_ROOT / "logs"
RUNNER = REPO_ROOT / "runs" / "run_sequential.sh"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8088

def latest_chain_path() -> str:
    candidates = sorted(LOGS_DIR.glob("chain_hwp_*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"no chain logs found in {LOGS_DIR}")
    return str(candidates[0])

def last_round_inner_json(chain_path: str) -> dict:
    with open(chain_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]
    if not lines:
        raise ValueError(f"chain log is empty: {chain_path}")
    outer = json.loads(lines[-1])
    inner_text = outer["payloads"][0]["text"]
    return json.loads(inner_text)

class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/run":
            return self._send(404, {"error": "not found"})

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else ""
        try:
            data = json.loads(raw) if raw else {}
        except Exception:
            return self._send(400, {"error": "invalid json"})

        text = (data.get("text") or "").strip()
        if not text:
            return self._send(400, {"error": "missing text"})

        with tempfile.NamedTemporaryFile("w+", delete=False) as f:
            f.write(text + "\n")
            tmp_path = f.name

        try:
            # Run runner silently
            subprocess.run(["bash", str(RUNNER), tmp_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            chain = latest_chain_path()
            inner = last_round_inner_json(chain)
            return self._send(200, inner)

        except subprocess.CalledProcessError:
            return self._send(500, {"error": "runner failed"})
        except Exception as e:
            return self._send(500, {"error": "internal error", "detail": str(e)})
        finally:
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 hwp_server.py",
        description="Legacy HWP HTTP helper. Recommended entrypoints are `bash runs/run_sequential.sh` and `python3 -m hwp_protocol.cli`.",
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Bind host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Bind port (default: {DEFAULT_PORT})")
    return parser


def main(argv: list[str] | None = None):
    args = build_parser().parse_args(argv)
    server = HTTPServer((args.host, args.port), Handler)
    print(f"HWP server listening on {args.host}:{args.port}")
    server.serve_forever()

if __name__ == "__main__":
    main()

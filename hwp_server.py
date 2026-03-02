from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import subprocess
import tempfile
import os

BASE = os.path.expanduser("~/hwp-tests")
LOGS_DIR = os.path.join(BASE, "logs")
RUNNER = os.path.join(BASE, "runs", "run_sequential.sh")

def latest_chain_path() -> str:
    cmd = f"ls -t {LOGS_DIR}/chain_hwp_*.jsonl | head -n 1"
    return subprocess.check_output(["bash", "-lc", cmd]).decode().strip()

def last_round_inner_json(chain_path: str) -> dict:
    last_line = subprocess.check_output(["bash", "-lc", f"tail -n 1 {chain_path}"]).decode()
    outer = json.loads(last_line)
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
            subprocess.run(["bash", RUNNER, tmp_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

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

def main():
    server = HTTPServer(("0.0.0.0", 8088), Handler)
    print("HWP server listening on :8088")
    server.serve_forever()

if __name__ == "__main__":
    main()

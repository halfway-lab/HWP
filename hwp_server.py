"""Legacy HTTP helper kept for backward compatibility.

The current recommended entry surface is the shell runner plus `hwp_protocol/`
CLI modules. This file remains in the repository because older docs and local
workflows may still reference it.
"""

import argparse
import csv
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import parse_qs, urlparse
from urllib.parse import urlencode
from pathlib import Path
import subprocess
import tempfile
import os
from html import escape

from runs.report_multi_provider import calculate_provider_score, load_provider_results

REPO_ROOT = Path(os.environ.get("HWP_REPO_PATH") or Path(__file__).resolve().parent)
LOGS_DIR = REPO_ROOT / "logs"
REPORTS_DIR = REPO_ROOT / "reports" / "benchmarks"
RUNNER = REPO_ROOT / "runs" / "run_sequential.sh"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8088

def latest_chain_path() -> str:
    candidates = sorted(LOGS_DIR.glob("chain_hwp_*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"no chain logs found in {LOGS_DIR}")
    return str(candidates[0])


def list_chain_paths(limit: int = 20) -> list[str]:
    candidates = sorted(LOGS_DIR.glob("chain_hwp_*.jsonl"), key=lambda item: item.stat().st_mtime, reverse=True)
    return [str(path) for path in candidates[:limit]]

def last_round_inner_json(chain_path: str) -> dict:
    with open(chain_path, "r", encoding="utf-8") as handle:
        lines = [line.strip() for line in handle if line.strip()]
    if not lines:
        raise ValueError(f"chain log is empty: {chain_path}")
    outer = json.loads(lines[-1])
    inner_text = outer["payloads"][0]["text"]
    return json.loads(inner_text)


def latest_benchmark_report_dir() -> Path | None:
    candidates = sorted(
        [path for path in REPORTS_DIR.glob("20*") if path.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def list_benchmark_report_names(limit: int = 20) -> list[str]:
    candidates = sorted(
        [path.name for path in REPORTS_DIR.glob("20*") if path.is_dir()],
        reverse=True,
    )
    return candidates[:limit]


def latest_multi_provider_report_dir() -> Path | None:
    candidates = sorted(
        [path for path in REPORTS_DIR.glob("multi_*") if path.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def list_multi_provider_report_names(limit: int = 20) -> list[str]:
    candidates = sorted(
        [path.name for path in REPORTS_DIR.glob("multi_*") if path.is_dir()],
        reverse=True,
    )
    return candidates[:limit]


def load_key_value_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def load_tsv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def load_chain_rounds(chain_path: str) -> list[dict]:
    rounds: list[dict] = []
    with open(chain_path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            outer = json.loads(line)
            inner_text = outer.get("payloads", [{}])[0].get("text", "{}")
            try:
                inner = json.loads(inner_text)
            except json.JSONDecodeError:
                inner = {}
            speed = inner.get("speed_metrics") or {}
            rounds.append(
                {
                    "round": inner.get("round", ""),
                    "mode": speed.get("mode", ""),
                    "continuity_score": inner.get("continuity_score", ""),
                    "blind_spot_score": inner.get("blind_spot_score", ""),
                    "collapse_detected": inner.get("collapse_detected", ""),
                    "recovery_applied": inner.get("recovery_applied", ""),
                }
            )
    return rounds


def resolve_chain_path(chain_path: str | None = None) -> str:
    if chain_path:
        candidate = Path(chain_path)
        if not candidate.is_absolute():
            candidate = REPO_ROOT / chain_path
        if not candidate.exists():
            raise FileNotFoundError(f"chain log not found: {candidate}")
        return str(candidate)
    return latest_chain_path()


def resolve_benchmark_report_dir(report_name: str | None = None) -> Path:
    if report_name:
        candidate = REPORTS_DIR / report_name
        if not candidate.exists():
            raise FileNotFoundError(f"benchmark report not found: {candidate}")
        return candidate
    latest = latest_benchmark_report_dir()
    if latest is None:
        raise FileNotFoundError(f"no benchmark reports found in {REPORTS_DIR}")
    return latest


def resolve_multi_provider_report_dir(report_name: str | None = None) -> Path:
    if report_name:
        candidate = REPORTS_DIR / report_name
        if not candidate.exists():
            raise FileNotFoundError(f"multi-provider report not found: {candidate}")
        return candidate
    latest = latest_multi_provider_report_dir()
    if latest is None:
        raise FileNotFoundError(f"no multi-provider reports found in {REPORTS_DIR}")
    return latest


def load_latest_benchmark_snapshot() -> dict:
    report_dir = latest_benchmark_report_dir()
    if report_dir is None:
        return {}
    return load_benchmark_snapshot(report_dir.name)


def load_benchmark_snapshot(report_name: str | None = None) -> dict:
    report_dir = resolve_benchmark_report_dir(report_name)
    return {
        "report_name": report_dir.name,
        "report_dir": str(report_dir),
        "context": load_key_value_file(report_dir / "context.txt"),
        "overview_rows": load_tsv_rows(report_dir / "overview.tsv"),
    }


def load_latest_multi_provider_snapshot() -> dict:
    report_dir = latest_multi_provider_report_dir()
    if report_dir is None:
        return {}
    return load_multi_provider_snapshot(report_dir.name)


def load_multi_provider_snapshot(report_name: str | None = None) -> dict:
    report_dir = resolve_multi_provider_report_dir(report_name)

    provider_data = load_provider_results(report_dir)
    providers = []
    for name, payload in sorted(provider_data.items()):
        score = calculate_provider_score(payload["rows"])
        providers.append(
            {
                "provider": name,
                "source": "overview.tsv" if payload.get("has_overview") else "results.tsv",
                "run_pass": f"{score['run_pass']}/{score['total']}",
                "full_pass": f"{score['verifier_pass']}/{score['total']}",
                "timing": f"{score['timing_coverage']}/{score['total']}",
                "score_percent": f"{score['percentage']:.1f}",
                "avg_chain_sec": f"{score['avg_chain_sec']:.2f}",
                "max_chain_sec": f"{score['max_chain_sec']:.2f}",
            }
        )
    return {
        "report_name": report_dir.name,
        "report_dir": str(report_dir),
        "providers": providers,
    }


def load_chain_snapshot(chain_path: str | None = None) -> dict:
    resolved_path = resolve_chain_path(chain_path)
    rounds = load_chain_rounds(resolved_path)
    return {
        "chain_path": resolved_path,
        "round_count": len(rounds),
        "latest_round": rounds[-1] if rounds else None,
        "rounds": rounds,
    }


def dashboard_snapshot() -> dict:
    snapshot: dict[str, object] = {
        "repo_root": str(REPO_ROOT),
        "latest_chain": None,
        "latest_round": None,
        "chain_rounds": [],
        "benchmark": load_latest_benchmark_snapshot(),
        "multi_provider": load_latest_multi_provider_snapshot(),
    }
    try:
        chain_snapshot = load_chain_snapshot()
    except FileNotFoundError:
        return snapshot

    snapshot["latest_chain"] = chain_snapshot["chain_path"]
    snapshot["chain_rounds"] = chain_snapshot["rounds"]
    snapshot["latest_round"] = chain_snapshot["latest_round"]
    return snapshot


def dashboard_snapshot_with_selection(
    chain_path: str | None = None,
    benchmark_report: str | None = None,
    multi_provider_report: str | None = None,
) -> dict:
    snapshot: dict[str, object] = {
        "repo_root": str(REPO_ROOT),
        "latest_chain": None,
        "latest_round": None,
        "chain_rounds": [],
        "available_chains": list_chain_paths(),
        "available_benchmark_reports": list_benchmark_report_names(),
        "available_multi_provider_reports": list_multi_provider_report_names(),
        "selected_chain": chain_path or "",
        "selected_benchmark_report": benchmark_report or "",
        "selected_multi_provider_report": multi_provider_report or "",
    }

    try:
        snapshot["benchmark"] = load_benchmark_snapshot(benchmark_report)
    except FileNotFoundError:
        snapshot["benchmark"] = {}

    try:
        snapshot["multi_provider"] = load_multi_provider_snapshot(multi_provider_report)
    except FileNotFoundError:
        snapshot["multi_provider"] = {}

    try:
        chain_snapshot = load_chain_snapshot(chain_path)
    except FileNotFoundError:
        return snapshot

    snapshot["latest_chain"] = chain_snapshot["chain_path"]
    snapshot["chain_rounds"] = chain_snapshot["rounds"]
    snapshot["latest_round"] = chain_snapshot["latest_round"]
    return snapshot


def api_index_snapshot() -> dict:
    return {
        "endpoints": {
            "/api/dashboard": "Combined latest snapshot for chain, benchmark, and multi-provider.",
            "/api/chain/latest": "Latest chain rounds and latest round summary.",
            "/api/benchmark/latest": "Latest single-provider benchmark overview and context.",
            "/api/multi-provider/latest": "Latest multi-provider overview table.",
        },
        "query_params": {
            "/api/chain/latest": ["path=<relative-or-absolute-chain-path>"],
            "/api/benchmark/latest": ["report=<benchmark-report-dir-name>"],
            "/api/multi-provider/latest": ["report=<multi-report-dir-name>"],
        },
    }


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "<p class='empty'>No data.</p>"
    head = "".join(f"<th>{escape(item)}</th>" for item in headers)
    body = []
    for row in rows:
        cells = "".join(f"<td>{escape(item)}</td>" for item in row)
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def render_picker(title: str, field_name: str, current_value: str, options: list[str], hint: str) -> str:
    option_tags = ['<option value="">Latest</option>']
    for option in options:
        selected = ' selected' if option == current_value else ""
        option_tags.append(f'<option value="{escape(option)}"{selected}>{escape(option)}</option>')
    return (
        f"<label class='picker'><span>{escape(title)}</span>"
        f"<select name='{escape(field_name)}'>{''.join(option_tags)}</select>"
        f"<small>{escape(hint)}</small></label>"
    )


def render_dashboard_html(snapshot: dict) -> str:
    benchmark = snapshot.get("benchmark") or {}
    benchmark_rows = benchmark.get("overview_rows") or []
    multi_provider = snapshot.get("multi_provider") or {}
    chain_rounds = snapshot.get("chain_rounds") or []
    latest_round = snapshot.get("latest_round") or {}

    benchmark_table = render_table(
        ["benchmark", "run", "verifier", "duration", "avg chain", "max chain"],
        [
            [
                str(row.get("benchmark", "")),
                str(row.get("run_status", "")),
                str(row.get("verifier_status", "")),
                str(row.get("duration_sec", "")),
                str(row.get("chain_avg_sec", "")),
                str(row.get("chain_max_sec", "")),
            ]
            for row in benchmark_rows
        ],
    )
    provider_table = render_table(
        ["provider", "source", "run", "full pass", "timing", "avg chain", "max chain"],
        [
            [
                str(row.get("provider", "")),
                str(row.get("source", "")),
                str(row.get("run_pass", "")),
                str(row.get("full_pass", "")),
                str(row.get("timing", "")),
                str(row.get("avg_chain_sec", "")),
                str(row.get("max_chain_sec", "")),
            ]
            for row in (multi_provider.get("providers") or [])
        ],
    )
    rounds_table = render_table(
        ["round", "mode", "continuity", "blind_spot", "collapse", "recovery"],
        [
            [
                str(row.get("round", "")),
                str(row.get("mode", "")),
                str(row.get("continuity_score", "")),
                str(row.get("blind_spot_score", "")),
                str(row.get("collapse_detected", "")),
                str(row.get("recovery_applied", "")),
            ]
            for row in chain_rounds
        ],
    )

    latest_chain = snapshot.get("latest_chain") or "(none)"
    latest_benchmark_dir = benchmark.get("report_dir") or "(none)"
    latest_multi_dir = multi_provider.get("report_dir") or "(none)"
    chain_options = [Path(item).name for item in (snapshot.get("available_chains") or [])]
    benchmark_options = list(snapshot.get("available_benchmark_reports") or [])
    multi_options = list(snapshot.get("available_multi_provider_reports") or [])
    selected_chain_name = Path(str(snapshot.get("selected_chain") or latest_chain)).name if latest_chain != "(none)" else ""
    selected_benchmark = str(snapshot.get("selected_benchmark_report") or benchmark.get("report_name") or "")
    selected_multi = str(snapshot.get("selected_multi_provider_report") or multi_provider.get("report_name") or "")
    latest_chain_name = Path(str(latest_chain)).name if latest_chain != "(none)" else ""

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HWP Dashboard</title>
  <style>
    :root {{
      --bg: #f4efe5;
      --ink: #1f1b16;
      --muted: #6f6458;
      --card: #fffaf2;
      --line: #d9cdbf;
      --accent: #b44f2f;
      --accent-soft: #f4d8c8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(180,79,47,0.14), transparent 28%),
        linear-gradient(180deg, #f7f1e7 0%, var(--bg) 100%);
    }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1, h2 {{ margin: 0 0 12px; }}
    p {{ margin: 0; color: var(--muted); }}
    .hero {{
      display: grid;
      gap: 16px;
      padding: 28px;
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(255,250,242,0.96), rgba(244,216,200,0.86));
      border-radius: 24px;
      box-shadow: 0 12px 40px rgba(70, 47, 29, 0.08);
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin-top: 24px;
    }}
    .stat, .panel {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 8px 30px rgba(70, 47, 29, 0.05);
    }}
    .stat .label {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); }}
    .stat .value {{ font-size: 28px; margin-top: 6px; color: var(--accent); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 18px;
      margin-top: 24px;
    }}
    .controls {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-top: 24px;
      align-items: end;
    }}
    .picker {{
      display: grid;
      gap: 6px;
      font-size: 14px;
      color: var(--muted);
    }}
    .picker span {{ color: var(--ink); font-weight: 600; }}
    .picker select {{
      width: 100%;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #fffdf8;
      color: var(--ink);
    }}
    .picker small {{ color: var(--muted); }}
    .actions {{
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .button {{
      display: inline-block;
      padding: 10px 14px;
      border-radius: 12px;
      border: 1px solid var(--line);
      text-decoration: none;
      color: var(--ink);
      background: #fffdf8;
    }}
    .button.primary {{
      background: var(--accent);
      border-color: var(--accent);
      color: #fffaf2;
    }}
    .panel.full {{ grid-column: 1 / -1; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid var(--line); vertical-align: top; }}
    th {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 12px;
      margin-right: 8px;
    }}
    .empty {{ color: var(--muted); font-style: italic; }}
    code {{ font-family: "SFMono-Regular", Consolas, monospace; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <div>
        <span class="pill">Legacy Read-Only Dashboard</span>
        <span class="pill">/api/dashboard available</span>
      </div>
      <div>
        <h1>HWP Benchmark And Protocol Dashboard</h1>
        <p>Latest benchmark outputs, multi-provider comparison, and per-round protocol state in one lightweight view.</p>
      </div>
    </section>
    <section class="stats">
      <article class="stat">
        <div class="label">Latest Chain</div>
        <div class="value">{escape(str(latest_round.get("round", "0") or "0"))}</div>
        <p>Latest completed round</p>
      </article>
      <article class="stat">
        <div class="label">Latest Mode</div>
        <div class="value">{escape(str(latest_round.get("mode", "") or "-"))}</div>
        <p>Current speed mode</p>
      </article>
      <article class="stat">
        <div class="label">Continuity</div>
        <div class="value">{escape(str(latest_round.get("continuity_score", "") or "-"))}</div>
        <p>Latest continuity score</p>
      </article>
      <article class="stat">
        <div class="label">Blind Spot</div>
        <div class="value">{escape(str(latest_round.get("blind_spot_score", "") or "-"))}</div>
        <p>Latest blind spot score</p>
      </article>
    </section>
    <form class="controls" method="get" action="/dashboard">
      {render_picker("Chain", "chain", selected_chain_name, chain_options, "Choose a specific chain log or keep Latest.")}
      {render_picker("Benchmark Report", "report", selected_benchmark, benchmark_options, "Choose a benchmark report directory.")}
      {render_picker("Multi-Provider Report", "multi_report", selected_multi, multi_options, "Choose a multi-provider report directory.")}
      <div class="actions">
        <button class="button primary" type="submit">Load Selection</button>
        <a class="button" href="/dashboard">Reset To Latest</a>
      </div>
    </form>
    <section class="grid">
      <article class="panel">
        <h2>Sources</h2>
        <p><strong>Chain:</strong> <code>{escape(str(latest_chain))}</code></p>
        <p><strong>Chain Name:</strong> {escape(latest_chain_name)}</p>
        <p><strong>Benchmark:</strong> <code>{escape(str(latest_benchmark_dir))}</code></p>
        <p><strong>Multi-Provider:</strong> <code>{escape(str(latest_multi_dir))}</code></p>
      </article>
      <article class="panel">
        <h2>Latest Round</h2>
        <p><strong>Round:</strong> {escape(str(latest_round.get("round", "") or "-"))}</p>
        <p><strong>Mode:</strong> {escape(str(latest_round.get("mode", "") or "-"))}</p>
        <p><strong>Continuity:</strong> {escape(str(latest_round.get("continuity_score", "") or "-"))}</p>
        <p><strong>Blind Spot:</strong> {escape(str(latest_round.get("blind_spot_score", "") or "-"))}</p>
        <p><strong>Collapse:</strong> {escape(str(latest_round.get("collapse_detected", "") or "-"))}</p>
        <p><strong>Recovery:</strong> {escape(str(latest_round.get("recovery_applied", "") or "-"))}</p>
      </article>
      <article class="panel full">
        <h2>Latest Benchmark Overview</h2>
        {benchmark_table}
      </article>
      <article class="panel full">
        <h2>Latest Multi-Provider Overview</h2>
        {provider_table}
      </article>
      <article class="panel full">
        <h2>Latest Chain Rounds</h2>
        {rounds_table}
      </article>
    </section>
  </div>
</body>
</html>"""

class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, code: int, html: str):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query)

        if route in ("/", "/dashboard"):
            chain_name = query.get("chain", [None])[0]
            benchmark_report = query.get("report", [None])[0]
            multi_report = query.get("multi_report", [None])[0]
            chain_path = None
            if chain_name:
                chain_path = str(LOGS_DIR / chain_name)
            return self._send_html(
                200,
                render_dashboard_html(
                    dashboard_snapshot_with_selection(
                        chain_path=chain_path,
                        benchmark_report=benchmark_report,
                        multi_provider_report=multi_report,
                    )
                ),
            )
        if route == "/api":
            return self._send(200, api_index_snapshot())
        if route == "/api/dashboard":
            return self._send(200, dashboard_snapshot())
        if route == "/api/chain/latest":
            try:
                chain_path = query.get("path", [None])[0]
                return self._send(200, load_chain_snapshot(chain_path))
            except FileNotFoundError as exc:
                return self._send(404, {"error": "not found", "detail": str(exc)})
        if route == "/api/benchmark/latest":
            try:
                report_name = query.get("report", [None])[0]
                return self._send(200, load_benchmark_snapshot(report_name))
            except FileNotFoundError as exc:
                return self._send(404, {"error": "not found", "detail": str(exc)})
        if route == "/api/multi-provider/latest":
            try:
                report_name = query.get("report", [None])[0]
                return self._send(200, load_multi_provider_snapshot(report_name))
            except FileNotFoundError as exc:
                return self._send(404, {"error": "not found", "detail": str(exc)})
        return self._send(404, {"error": "not found"})

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

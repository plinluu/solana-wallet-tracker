#!/usr/bin/env python3
"""Solana wallet tracker web UI. Stdlib only.

Run:  python3 app.py
Then open the printed URL (e.g. http://127.0.0.1:8080) in your browser.
"""

import json
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from tracker import get_balance, get_recent_txs, get_sol_usd

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Solana Wallet Tracker</title>
<style>
  body { font-family: system-ui, sans-serif; background: #0d1117; color: #e6edf3; margin: 0; padding: 2rem; }
  .wrap { max-width: 860px; margin: 0 auto; }
  h1 { font-size: 1.5rem; }
  h1 span { color: #14f195; }
  .row { display: flex; gap: .5rem; margin: 1rem 0; }
  input { flex: 1; padding: .6rem; border-radius: 8px; border: 1px solid #30363d; background: #161b22; color: #e6edf3; font-size: 1rem; }
  button { padding: .6rem 1.2rem; border: 0; border-radius: 8px; background: #14f195; color: #04281c; font-weight: 700; cursor: pointer; }
  button:disabled { opacity: .5; }
  .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 1rem 1.2rem; margin: 1rem 0; }
  .bal { font-size: 2rem; font-weight: 800; }
  .usd { color: #8b949e; }
  table { width: 100%; border-collapse: collapse; margin-top: .5rem; }
  th, td { text-align: left; padding: .5rem; border-bottom: 1px solid #21262d; font-size: .9rem; }
  .pos { color: #14f195; } .neg { color: #ff6b6b; } .fail { color: #ffb86b; }
  .err { color: #ff6b6b; }
  code { font-size: .8rem; color: #8b949e; }
</style>
</head>
<body>
<div class="wrap">
  <h1>◎ Solana Wallet <span>Tracker</span></h1>
  <div class="row">
    <input id="addr" placeholder="Paste a Solana wallet address…" spellcheck="false">
    <button id="go" onclick="lookup()">Track</button>
  </div>
  <div id="out"></div>
</div>
<script>
async function lookup() {
  const addr = document.getElementById('addr').value.trim();
  const out = document.getElementById('out');
  const btn = document.getElementById('go');
  if (!addr) return;
  btn.disabled = true;
  out.innerHTML = '<p>Loading…</p>';
  try {
    const r = await fetch('/api/wallet?address=' + encodeURIComponent(addr) + '&limit=10');
    const d = await r.json();
    if (d.error) { out.innerHTML = '<p class="err">Error: ' + d.error + '</p>'; return; }
    let html = '<div class="card"><div>Balance</div><div class="bal">' + d.balance.toFixed(9) + ' SOL</div>';
    if (d.usd_price) html += '<div class="usd">≈ $' + (d.balance * d.usd_price).toFixed(2) + ' @ $' + d.usd_price.toFixed(2) + '/SOL</div>';
    html += '</div><div class="card"><div>Last ' + d.txs.length + ' transactions</div><table><tr><th>Time</th><th>Change (SOL)</th><th>Status</th><th>Signature</th></tr>';
    for (const t of d.txs) {
      const cls = t.change_sol < 0 ? 'neg' : 'pos';
      const sign = t.change_sol >= 0 ? '+' : '';
      html += '<tr><td>' + t.time + '</td><td class="' + cls + '">' + sign + t.change_sol.toFixed(9) + '</td>'
        + '<td class="' + (t.status === 'ok' ? '' : 'fail') + '">' + t.status + '</td>'
        + '<td><code>' + t.signature.slice(0, 20) + '…</code></td></tr>';
    }
    out.innerHTML = html + '</table></div>';
  } catch (e) {
    out.innerHTML = '<p class="err">Request failed: ' + e + '</p>';
  }
  btn.disabled = false;
}
document.getElementById('addr').addEventListener('keydown', e => { if (e.key === 'Enter') lookup(); });
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # quiet

    def _send(self, body, content_type="text/html"):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self._send(PAGE)
        elif parsed.path == "/api/wallet":
            qs = urllib.parse.parse_qs(parsed.query)
            address = qs.get("address", [""])[0]
            try:
                limit = int(qs.get("limit", ["10"])[0])
            except ValueError:
                limit = 10
            try:
                balance = get_balance(address)
                try:
                    usd_price = get_sol_usd()
                except Exception:
                    usd_price = None
                txs = get_recent_txs(address, limit)
                self._send(
                    json.dumps(
                        {"balance": balance, "usd_price": usd_price, "txs": txs}
                    ),
                    "application/json",
                )
            except RuntimeError as exc:
                self._send(json.dumps({"error": str(exc)}), "application/json")
        else:
            self.send_response(404)
            self.end_headers()


def main():
    port = 8080
    while True:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            port += 1
    print(f"Serving on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()

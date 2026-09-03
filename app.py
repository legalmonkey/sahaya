"""A loopback-only Day 1 web shell for the Sahaya pipeline (documented in docs/day1-validation.md).

Usage:
  python app.py       # runs local web interface on http://127.0.0.1:8080
"""
from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.config import SETTINGS
from src.rag.pipeline import answer_query

PAGE = """<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Sahaya — Day 1</title>
<style>
  body{font-family:system-ui,-apple-system,sans-serif;max-width:720px;margin:2rem auto;padding:0 1rem;color:#17352b;background:#fafcfb}
  textarea,button{font:inherit}
  textarea{box-sizing:border-box;width:100%;min-height:6rem;padding:.8rem;border:1px solid #b4d1c6;border-radius:.5rem}
  button{margin-top:.7rem;margin-right:.5rem;padding:.75rem 1.2rem;background:#126b50;color:white;border:0;border-radius:.5rem;cursor:pointer;font-weight:600}
  button:hover{background:#0e523d}
  button.secondary{background:#e2eee9;color:#126b50}
  .card,#result{white-space:pre-wrap;background:#f2f7f4;padding:1rem;margin-top:1rem;border-radius:.5rem;border:1px solid #dcebe4;line-height:1.5}
  .note{color:#57665f;font-size:0.9rem}
  .view{display:none}
  .view.active{display:block}
  .meta{font-size:0.85rem;color:#496156;margin-top:0.8rem;border-top:1px dashed #c0ded2;padding-top:0.5rem}
</style>
<main>
  <h1>Sahaya</h1>
  <p class='note'>Day 1 • Local-only CPU pipeline • On-Device Protocol Support</p>
  
  <section id='households' class='view active'>
    <h2>Households</h2>
    <div class='card'><b>Village Priority Queue (Day 1 Preview)</b><br>Sample household triage queue. Tap below to inspect household details and immunization records.</div>
    <button onclick="show('detail')">Open household</button>
  </section>

  <section id='detail' class='view'>
    <h2>Household detail</h2>
    <div class='card'>Household: <b>Meena Devi (Village: Rampur)</b><br>Child: Aarav (DOB: 6 months ago) • Overdue: OPV-2, Pentavalent-2<br>ANC: Registered • High Risk Flag: None</div>
    <button onclick="show('ask')">Ask a protocol question</button> 
    <button class='secondary' onclick="show('households')">Back</button>
  </section>

  <section id='ask' class='view'>
    <h2>Ask a protocol question</h2>
    <textarea id='q' placeholder='Example: When are oral polio vaccine doses due?'></textarea><br>
    <button onclick='ask()'>Ask Sahaya</button> 
    <button class='secondary' onclick="show('detail')">Back</button>
    <div id='result' aria-live='polite'>Type a protocol question above. Retrieval and generation run 100% offline and on-device.</div>
  </section>
</main>

<script>
function show(id){
  document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}
async function ask(){
  let r = document.getElementById('result'), q = document.getElementById('q').value.trim();
  if(!q) return;
  r.innerHTML = '<i>Retrieving local corpus sources and running inference…</i>';
  try {
    let res = await fetch('/api/ask', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({query: q})
    });
    let d = await res.json();
    if(d.status === 'error' || d.error){
      r.textContent = 'Error: ' + (d.error || 'Unknown error');
      return;
    }
    let srcText = '';
    if(d.sources && d.sources.length){
      srcText = '\n\nSources Cited:\n' + d.sources.map((s, i) => ` ${i+1}. ${s.document} (p.${s.page}${s.section ? ' — ' + s.section : ''}) [sim: ${s.similarity}]`).join('\n');
    }
    let lat = d.latency_ms || {};
    let metaText = `\n\nRetrieval Confidence: ${(d.confidence || 0).toFixed(2)}\nLatency: retrieval ${lat.retrieval || 0}ms · LLM ${lat.llm || 0}ms · total ${lat.total || 0}ms`;
    r.textContent = d.answer + srcText + metaText;
  } catch(err) {
    r.textContent = 'Request failed: ' + err.message;
  }
}
</script>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        payload = PAGE.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if self.path != "/api/ask":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(size).decode("utf-8"))
            query = data.get("query", "")
            response = answer_query(query)
            status = HTTPStatus.OK
        except Exception as exc:  # noqa: BLE001
            response = {"status": "error", "error": str(exc)}
            status = HTTPStatus.UNPROCESSABLE_ENTITY

        encoded = json.dumps(response).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, format, *args):  # noqa: A002
        return


def main() -> None:
    server_address = ("127.0.0.1", 8080)
    httpd = ThreadingHTTPServer(server_address, Handler)
    print(f"Sahaya Day 1 web validation shell running at http://{server_address[0]}:{server_address[1]}")
    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()

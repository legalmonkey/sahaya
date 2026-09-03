"""A loopback-only Day 1 shell for the local Sahaya pipeline."""
from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.database import initialise
from src.inference import InferenceUnavailable, SahayaPipeline
from src.retrieval import LocalTfidfRetriever

ROOT = Path(__file__).parent
initialise(ROOT / "data" / "sahaya.db", ROOT / "db" / "migrations" / "001_shared_schema.sql")
PIPELINE = SahayaPipeline(LocalTfidfRetriever(ROOT / "data" / "corpus.json"))

PAGE = """<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Sahaya — Day 1</title><style>body{font-family:system-ui;max-width:720px;margin:2rem auto;padding:0 1rem;color:#17352b}textarea,button{font:inherit}textarea{box-sizing:border-box;width:100%;min-height:6rem;padding:.8rem}button{margin-top:.7rem;padding:.75rem 1rem;background:#126b50;color:white;border:0;border-radius:.5rem}.card,#result{white-space:pre-wrap;background:#f2f7f4;padding:1rem;margin-top:1rem;border-radius:.5rem}.note{color:#57665f}.view{display:none}.view.active{display:block}</style>
<main><h1>Sahaya</h1><p class='note'>Day 1 • Local-only CPU pipeline • Typed question</p>
<section id='households' class='view active'><h2>Households</h2><div class='card'><b>Temporary Day 1 shell data</b><br>Demo household — details are not yet connected to the database.</div><button onclick="show('detail')">Open household</button></section>
<section id='detail' class='view'><h2>Household detail</h2><div class='card'>Temporary Day 1 route. Immunization, risk, schemes, and priority are Day 2+ modules.</div><button onclick="show('ask')">Ask a protocol question</button> <button onclick="show('households')">Back</button></section>
<section id='ask' class='view'><h2>Ask a protocol question</h2><textarea id='q' placeholder='Example: When are OPV doses scheduled?'></textarea><br><button onclick='ask()'>Ask Sahaya</button> <button onclick="show('detail')">Back</button><div id='result' aria-live='polite'>Answers require a configured local Gemma model. No cloud or canned-answer fallback is used.</div></section></main>
<script>function show(id){document.querySelectorAll('.view').forEach(x=>x.classList.remove('active'));document.getElementById(id).classList.add('active')}async function ask(){let r=document.getElementById('result'),q=document.getElementById('q').value;r.textContent='Retrieving local sources and running local inference…';let x=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q})});let d=await x.json();r.textContent=d.error?'Error: '+d.error:d.answer+'\n\nConfidence: '+d.confidence+'\n\nSources:\n'+d.source_chunks.map(s=>'['+s.id+'] '+s.title+' — '+s.url).join('\n')}</script></html>"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND); return
        payload = PAGE.encode(); self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", len(payload)); self.end_headers(); self.wfile.write(payload)

    def do_POST(self):
        if self.path != "/api/ask":
            self.send_error(HTTPStatus.NOT_FOUND); return
        try:
            size = int(self.headers.get("Content-Length", "0")); data = json.loads(self.rfile.read(size))
            response, status = PIPELINE.answer(data.get("query", "")), HTTPStatus.OK
        except (ValueError, InferenceUnavailable) as exc:
            response, status = {"error": str(exc)}, HTTPStatus.UNPROCESSABLE_ENTITY
        encoded = json.dumps(response).encode(); self.send_response(status)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", len(encoded)); self.end_headers(); self.wfile.write(encoded)

    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    print("Sahaya Day 1 running only at http://127.0.0.1:8080")
    ThreadingHTTPServer(("127.0.0.1", 8080), Handler).serve_forever()

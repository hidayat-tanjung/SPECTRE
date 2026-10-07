#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  SPECTRE v5.0 - WEB UI
#  FastAPI + WebSocket
#  👻 AUTHOR: イズミー (IZUMI)
# ============================================================

import os
import sys
import json
import asyncio
from typing import Optional

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
    from fastapi.responses import HTMLResponse
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from core import cfg, log, C, store, print_banner


if not HAS_FASTAPI:
    print(C.e("FastAPI not installed."))
    print(C.i("Run: pip install fastapi uvicorn[standard] python-multipart"))
    sys.exit(1)


app = FastAPI(title="SPECTRE v5", version="5.0.0")
security = HTTPBasic()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_users():
    return cfg.get("web.auth.users", {"admin": "changeme"})


def check_auth(creds: HTTPBasicCredentials = Depends(security)) -> str:
    users = get_users()
    if not cfg.get("web.auth.enabled", True):
        return creds.username
    if creds.username not in users or creds.password != users[creds.username]:
        raise HTTPException(status_code=401, detail="Invalid",
                             headers={"WWW-Authenticate": "Basic"})
    return creds.username


# ============================================================
# HTML
# ============================================================
HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SPECTRE v5.0</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a0a;color:#00ff88;font-family:'Courier New',monospace;padding:20px;min-height:100vh}
h1{color:#ff0040;text-shadow:0 0 10px #ff0040;margin-bottom:10px}
h2{color:#00ddff;margin:20px 0 10px;border-bottom:1px solid #00ddff33;padding-bottom:5px;font-size:16px}
.banner{font-size:9px;line-height:1.1;color:#ff0040;text-shadow:0 0 5px #ff0040;margin-bottom:20px;white-space:pre}
.grid{display:grid;grid-template-columns:1fr 2fr;gap:20px}
@media(max-width:900px){.grid{grid-template-columns:1fr}}
.card{background:#111;border:1px solid #ff004033;padding:15px;border-radius:4px;margin-bottom:15px}
.card.green{border-color:#00ff8833}
label{display:block;margin:8px 0 4px;color:#00ddff;font-size:12px}
input,select{width:100%;background:#000;color:#00ff88;border:1px solid #00ff8844;padding:8px;font-family:inherit;font-size:13px;border-radius:3px}
button{background:#ff0040;color:#fff;border:none;padding:10px 16px;font-family:inherit;font-size:13px;cursor:pointer;margin:4px 4px 4px 0;border-radius:3px;font-weight:bold}
button:hover{background:#ff2060;box-shadow:0 0 10px #ff0040}
button.sec{background:#00ddff;color:#000}
button.sec:hover{background:#40e8ff}
button.ok{background:#00ff88;color:#000}
pre{background:#000;border:1px solid #00ff8833;padding:12px;overflow:auto;max-height:500px;font-size:12px;line-height:1.4;border-radius:3px;color:#00ff88}
.stat{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #00ff8811}
.stat .l{color:#666}
.stat .v{color:#00ff88;font-weight:bold}
.tag{display:inline-block;padding:2px 8px;border-radius:3px;font-size:11px;margin:2px}
.tag.critical{background:#ff0040;color:#fff}
.tag.high{background:#ff6060;color:#000}
.tag.medium{background:#ffaa00;color:#000}
.tag.low{background:#00ddff;color:#000}
.tag.info{background:#666;color:#fff}
.log-line{padding:2px 0}
.log-line.error{color:#ff4040}
.log-line.success{color:#00ff88}
.log-line.warn{color:#ffaa00}
</style>
</head>
<body>
<div class="banner">
 ███████╗██████╗ ███████╗ ██████╗████████╗██████╗ ███████╗
 ██╔════╝██╔══██╗██╔════╝██╔════╝╚══██╔══╝██╔══██╗██╔════╝
 ███████╗██████╔╝█████╗  ██║        ██║   ██████╔╝█████╗  
 ╚════██║██╔═══╝ ██╔══╝  ██║        ██║   ██╔══██╗██╔══╝  
 ███████║██║     ███████╗╚██████╗   ██║   ██║  ██║███████╗
 ╚══════╝╚═╝     ╚══════╝ ╚═════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝
</div>
<h1>💀 SPECTRE v5.0 Web UI 💀</h1>
<p style="color:#666;font-size:12px;">WebSocket: <span id="ws-st">connecting...</span></p>

<div class="grid">
<div>
  <div class="card">
    <h2>🎯 Target</h2>
    <label>Target</label>
    <input id="target" value="example.com">
    <label>Module</label>
    <select id="module">
      <option value="geoip">GeoIP</option>
      <option value="portscan">Port Scan</option>
      <option value="tech">Tech</option>
      <option value="dns">DNS</option>
      <option value="whois">Whois</option>
      <option value="subdomain">Subdomain</option>
      <option value="dir">Dir Brute</option>
      <option value="ssl">SSL</option>
      <option value="social">Social</option>
      <option value="email">Email</option>
      <option value="sqli">SQLi/XSS</option>
      <option value="async_recon">Async Recon</option>
      <option value="backdoor">Backdoor Gen</option>
      <option value="crypto">Crypto</option>
      <option value="shodan">Shodan</option>
    </select>
    <div style="margin-top:12px;">
      <button onclick="runMod()">▶ RUN</button>
      <button class="sec" onclick="runAll()">⚡ ALL</button>
      <button class="ok" onclick="clr()">Clear</button>
    </div>
  </div>
  <div class="card green">
    <h2>📊 Stats</h2>
    <div class="stat"><span class="l">Scans</span><span class="v" id="s-scans">-</span></div>
    <div class="stat"><span class="l">Targets</span><span class="v" id="s-targets">-</span></div>
    <div class="stat"><span class="l">Findings</span><span class="v" id="s-findings">-</span></div>
    <div class="stat"><span class="l">Driver</span><span class="v" id="s-driver">-</span></div>
    <button class="sec" style="margin-top:10px" onclick="loadStats()">↻ Refresh</button>
  </div>
  <div class="card">
    <h2>📄 Reports</h2>
    <button class="sec" onclick="loadFindings()">Findings</button>
    <button class="sec" onclick="loadHistory()">History</button>
  </div>
</div>
<div>
  <div class="card">
    <h2>🖥️ Console</h2>
    <pre id="log">Waiting...</pre>
  </div>
  <div class="card">
    <h2>🔍 Findings</h2>
    <pre id="findings">Click Findings to load.</pre>
  </div>
  <div class="card">
    <h2>📜 History</h2>
    <pre id="history">Click History to load.</pre>
  </div>
</div>
</div>

<script>
const ws = new WebSocket(`ws://${location.host}/ws`);
const logEl = document.getElementById('log');
const st = document.getElementById('ws-st');

ws.onopen = () => { st.textContent='connected'; st.style.color='#00ff88'; log('[*] WS connected'); };
ws.onclose = () => { st.textContent='disconnected'; st.style.color='#ff4040'; log('[!] WS closed','error'); };
ws.onerror = e => log('[!] WS error','error');
ws.onmessage = e => {
  try {
    const m = JSON.parse(e.data);
    if(m.type==='log') log(m.text, m.level);
    else if(m.type==='result') log(JSON.stringify(m.data,null,2));
    else if(m.type==='done') log('[+] Done: '+m.module,'success');
    else if(m.type==='stats') updStats(m.data);
    else if(m.type==='findings') showFindings(m.data);
    else if(m.type==='history') showHistory(m.data);
  } catch(err){ log(e.data); }
};
function log(t, lvl='info'){
  const cls = lvl==='error'?'error':lvl==='success'?'success':lvl==='warn'?'warn':'';
  const d = document.createElement('div');
  d.className = 'log-line '+cls;
  d.textContent = '> '+t;
  logEl.appendChild(d);
  logEl.scrollTop = logEl.scrollHeight;
}
function clr(){ logEl.textContent=''; }
function runMod(){
  const t = document.getElementById('target').value.trim();
  const m = document.getElementById('module').value;
  if(!t) return alert('Target?');
  ws.send(JSON.stringify({action:'run',module:m,target:t}));
  log(`[+] ${m} on ${t}`,'success');
}
function runAll(){
  const t = document.getElementById('target').value.trim();
  if(!t) return alert('Target?');
  ws.send(JSON.stringify({action:'run_all',target:t}));
  log(`[+] ALL on ${t}`,'success');
}
function loadStats(){ ws.send(JSON.stringify({action:'stats'})); }
function loadFindings(){ ws.send(JSON.stringify({action:'findings'})); }
function loadHistory(){
  const t = document.getElementById('target').value.trim();
  if(!t) return alert('Target?');
  ws.send(JSON.stringify({action:'history',target:t}));
}
function updStats(d){
  document.getElementById('s-scans').textContent = d.scans;
  document.getElementById('s-targets').textContent = d.assets;
  document.getElementById('s-findings').textContent = d.findings;
  document.getElementById('s-driver').textContent = d.driver;
}
function showFindings(rows){
  const el = document.getElementById('findings');
  if(!rows||!rows.length){ el.textContent='No findings.'; return; }
  el.innerHTML = rows.map(r=>{
    const s = (r.severity||'info').toLowerCase();
    return `<div style="margin-bottom:8px"><span class="tag ${s}">${s.toUpperCase()}</span> <b>${r.title||r.module}</b><br><span style="color:#888;font-size:11px">${r.target} | ${r.ts}</span></div>`;
  }).join('');
}
function showHistory(rows){
  const el = document.getElementById('history');
  if(!rows||!rows.length){ el.textContent='No history.'; return; }
  el.textContent = rows.map(r=>`[${r.ts}] ${r.module} | sev=${r.severity}\n  ${(r.data||'').substring(0,300)}`).join('\n\n');
}
setInterval(loadStats, 30000);
setTimeout(loadStats, 1000);
</script>
</body>
</html>"""


# ============================================================
# ROUTES
# ============================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/api/stats")
async def api_stats(user: str = Depends(check_auth)):
    return store().stats()


@app.get("/api/findings")
async def api_findings(target: Optional[str] = None,
                       user: str = Depends(check_auth)):
    if target:
        return {"rows": store().history(target, limit=100)}
    return {"rows": store().dump(limit=200)}


@app.get("/api/targets")
async def api_targets(user: str = Depends(check_auth)):
    return {"targets": store().targets()}


@app.websocket("/ws")
async def ws_ep(ws: WebSocket):
    await ws.accept()

    async def send_log(text, level="info"):
        await ws.send_text(json.dumps({"type": "log", "text": text, "level": level}))

    try:
        await send_log("[+] SPECTRE v5 WebSocket ready", "success")
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except Exception:
                await send_log(f"[!] Bad JSON", "error")
                continue

            action = msg.get("action")

            if action == "stats":
                await ws.send_text(json.dumps({
                    "type": "stats", "data": store().stats()
                }))

            elif action == "findings":
                rows = store().dump(limit=100)
                findings = [
                    {"target": r["target"], "module": r["module"],
                     "severity": r["severity"], "title": r["module"],
                     "ts": r["ts"]}
                    for r in rows
                ]
                await ws.send_text(json.dumps({"type": "findings", "data": findings}))

            elif action == "history":
                target = msg.get("target", "")
                rows = store().history(target, limit=50)
                await ws.send_text(json.dumps({"type": "history", "data": rows}))

            elif action == "run":
                module_name = msg.get("module", "")
                target = msg.get("target", "")
                await send_log(f"[*] Running {module_name} on {target}...")

                try:
                    from modules import ALL_MODULES
                    if module_name not in ALL_MODULES:
                        await send_log(f"[!] Unknown: {module_name}", "error")
                        continue
                    cls = ALL_MODULES[module_name]

                    def _run():
                        try:
                            return cls(target).run()
                        except Exception as e:
                            return {"error": str(e)}

                    result = await asyncio.get_event_loop().run_in_executor(None, _run)
                    await ws.send_text(json.dumps({
                        "type": "result", "module": module_name,
                        "data": result
                    }, default=str))
                    await ws.send_text(json.dumps({
                        "type": "done", "module": module_name
                    }))
                except Exception as e:
                    await send_log(f"[!] {e}", "error")

            elif action == "run_all":
                target = msg.get("target", "")
                await send_log(f"[*] ALL on {target}...", "warn")
                try:
                    from modules import ALL_MODULES
                    def _run_all():
                        out = {}
                        for name, cls in ALL_MODULES.items():
                            try:
                                out[name] = str(cls(target).run())[:200]
                            except Exception as e:
                                out[name] = f"error: {e}"
                        return out
                    result = await asyncio.get_event_loop().run_in_executor(None, _run_all)
                    await ws.send_text(json.dumps({
                        "type": "result", "module": "ALL",
                        "data": result
                    }, default=str))
                    await ws.send_text(json.dumps({
                        "type": "done", "module": "ALL"
                    }))
                except Exception as e:
                    await send_log(f"[!] {e}", "error")

            else:
                await send_log(f"[!] Unknown action: {action}", "error")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error(f"WS: {e}")


def run_web():
    host = cfg.get("web.host", "0.0.0.0")
    port = cfg.get("web.port", 5000)
    print_banner()
    print(C.a(f"🌐 Web UI: http://{host}:{port}"))
    print(C.i(f"Auth: {'on' if cfg.get('web.auth.enabled', True) else 'OFF'}"))
    print(C.w("⚠️ Don't expose without HTTPS + strong auth"))
    print()
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_web()
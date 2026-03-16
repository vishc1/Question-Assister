"""
Local upload server for managing identity documents and rebuilding the RAG index.
Run with: python upload_server.py
Then open: http://localhost:5000
"""

import os
import subprocess
import sys
import threading
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string
import json
import queue as _queue
import threading as _threading

from config import Config
import re
import subprocess as _subprocess
import urllib.request
from html.parser import HTMLParser

app = Flask(__name__)

# SSE broadcast infrastructure
_sse_clients = []
_sse_lock = _threading.Lock()
_sse_history = []

def broadcast_event(event_type, data):
    msg = json.dumps({"type": event_type, "data": data})
    _sse_history.append(msg)
    if len(_sse_history) > 300:
        _sse_history.pop(0)
    with _sse_lock:
        for q in list(_sse_clients):
            try:
                q.put_nowait(msg)
            except Exception:
                pass

SESSION_CONFIG_PATH = Config.IDENTITY_DIR.parent / "identity" / "session_config.json"


def get_session_config():
    p = Path(__file__).parent / "identity" / "session_config.json"
    if p.exists():
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save_session_config(cfg):
    p = Path(__file__).parent / "identity" / "session_config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(cfg, f, indent=2)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "head"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "head"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            d = data.strip()
            if d:
                self._parts.append(d)

    def get_text(self):
        return "\n".join(self._parts)


def _strip_html(html):
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    return p.get_text()


def _fetch_url(url):
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        return _strip_html(html)[:6000]
    except Exception as e:
        return f"Could not fetch URL: {e}"


def _fetch_github(github_url):
    m = re.match(r"https?://github\.com/([^/\s]+)(?:/([^/\s]+))?", github_url.strip())
    if not m:
        return "Invalid GitHub URL"
    username, repo_name = m.group(1), m.group(2)
    parts = [f"GitHub profile: {username}"]
    try:
        if repo_name:
            repos_to_fetch = [(username, repo_name)]
        else:
            api = f"https://api.github.com/users/{username}/repos?sort=updated&per_page=12"
            req = urllib.request.Request(api, headers={"User-Agent": "Interview-Assistant/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                repos = json.loads(resp.read())
            repos_to_fetch = [(username, r["name"]) for r in repos[:8] if not r.get("fork")]
            for r in repos[:10]:
                desc = r.get("description") or ""
                stars = r.get("stargazers_count", 0)
                lang = r.get("language") or ""
                parts.append(f"Repo: {r['name']} ({lang}, ★{stars}) — {desc}")
        for uname, rname in repos_to_fetch[:6]:
            for branch in ("main", "master"):
                try:
                    raw = f"https://raw.githubusercontent.com/{uname}/{rname}/{branch}/README.md"
                    req = urllib.request.Request(raw, headers={"User-Agent": "Interview-Assistant/1.0"})
                    with urllib.request.urlopen(req, timeout=8) as resp:
                        readme = resp.read().decode("utf-8", errors="ignore")[:1500]
                    parts.append(f"\n--- {rname} README ---\n{readme}")
                    break
                except Exception:
                    pass
    except Exception as e:
        parts.append(f"GitHub fetch error: {e}")
    return "\n".join(parts)[:7000]


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".json", ".txt"}

SETUP_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interview Assistant — Setup</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
.card{background:#141414;border:1px solid #1e1e1e;border-radius:16px;padding:32px;width:100%;max-width:400px}
.logo{font-size:1.4rem;font-weight:700;color:#fff;margin-bottom:4px}
.sub{font-size:.82rem;color:#555;margin-bottom:28px}
label{display:block;font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#555;margin-bottom:6px}
input{width:100%;background:#0f0f0f;border:1px solid #222;border-radius:8px;padding:10px 14px;color:#e0e0e0;font-size:.88rem;outline:none;transition:border-color .2s;margin-bottom:18px;font-family:inherit}
input:focus{border-color:#4f8ef7}
input::placeholder{color:#333}
.hint{font-size:.72rem;color:#444;margin-top:-14px;margin-bottom:16px}
.btn{width:100%;padding:12px;background:#4f8ef7;color:#fff;border:none;border-radius:8px;font-size:.9rem;font-weight:600;cursor:pointer;margin-top:6px}
.btn:hover{background:#3d7de8}
.skip{display:block;text-align:center;margin-top:14px;font-size:.78rem;color:#444;cursor:pointer;text-decoration:none}
.skip:hover{color:#888}
#progress-view{display:none}
.prog-title{font-size:.88rem;color:#888;margin-bottom:16px}
.log-item{font-size:.82rem;padding:5px 0;display:flex;align-items:flex-start;gap:8px;border-bottom:1px solid #1a1a1a;animation:fi .2s}
.log-item:last-child{border-bottom:none}
@keyframes fi{from{opacity:0;transform:translateY(3px)}to{opacity:1;transform:translateY(0)}}
.log-item.ok{color:#4ade80}
.log-item.err{color:#f87171}
.log-item.active{color:#fbbf24}
.spin{width:12px;height:12px;border:2px solid #333;border-top-color:#fbbf24;border-radius:50%;animation:sp .7s linear infinite;flex-shrink:0;margin-top:1px}
@keyframes sp{to{transform:rotate(360deg)}}
.ic{flex-shrink:0;width:14px;text-align:center}
</style>
</head>
<body>
<div class="card">
  <div id="form-view">
    <div class="logo">🎯 Interview Assistant</div>
    <div class="sub">Set up your profile for personalized answers</div>

    <label>What is this interview for? <span style="color:#60a5fa">*</span></label>
    <input id="f_role" placeholder="e.g. Software Engineering internship at Google" />

    <label>Your Portfolio or LinkedIn URL <span style="color:#444;font-weight:400;text-transform:none;letter-spacing:0">(optional)</span></label>
    <input id="f_portfolio" placeholder="https://linkedin.com/in/yourname" />

    <label>Your GitHub URL <span style="color:#444;font-weight:400;text-transform:none;letter-spacing:0">(optional)</span></label>
    <input id="f_github" placeholder="https://github.com/yourusername" />

    <button class="btn" onclick="startSetup()">→ Start Session</button>
    <a class="skip" href="/interview">Skip setup →</a>
  </div>

  <div id="progress-view">
    <div class="prog-title" id="prog-title">Setting up your profile...</div>
    <div id="log"></div>
  </div>
</div>
<script>
function log(text, type) {
  const el = document.createElement('div');
  el.className = 'log-item ' + (type||'');
  const icon = type==='ok' ? '✓' : type==='err' ? '✗' : type==='active' ? '' : '•';
  if (type==='active') {
    el.innerHTML = '<div class="spin"></div><span>'+text+'</span>';
  } else {
    el.innerHTML = '<span class="ic">'+icon+'</span><span>'+text+'</span>';
  }
  // replace previous active item if exists
  const prev = document.querySelector('.log-item.active');
  if (prev && type !== 'active') { prev.remove(); }
  document.getElementById('log').appendChild(el);
}
async function startSetup() {
  const role = document.getElementById('f_role').value.trim();
  if (!role) { document.getElementById('f_role').style.borderColor='#f87171'; document.getElementById('f_role').focus(); return; }
  document.getElementById('form-view').style.display='none';
  document.getElementById('progress-view').style.display='block';
  const body = {
    interview_for: role,
    portfolio_url: document.getElementById('f_portfolio').value.trim(),
    github_url: document.getElementById('f_github').value.trim()
  };
  const res = await fetch('/api/setup', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const reader = res.body.getReader(); const dec = new TextDecoder(); let buf='';
  while(true) {
    const {done,value} = await reader.read();
    if(done) break;
    buf += dec.decode(value);
    const lines = buf.split('\\n'); buf = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const raw = line.slice(5).trim(); if (!raw) continue;
      try {
        const ev = JSON.parse(raw);
        if (ev.type==='progress') log(ev.text, ev.status||'');
        if (ev.type==='done') {
          log('All set! Launching...', 'ok');
          setTimeout(()=>{ window.location.href='/interview'; }, 700);
        }
      } catch(e){}
    }
  }
}
</script>
</body>
</html>"""

INTERVIEW_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Interview Assistant</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;height:100vh;display:flex;flex-direction:column;overflow:hidden}
/* draggable title bar for app-mode window */
.header{background:#141414;border-bottom:1px solid #1e1e1e;padding:0 14px;height:44px;display:flex;align-items:center;gap:10px;flex-shrink:0;-webkit-app-region:drag;user-select:none}
.header *{-webkit-app-region:no-drag}
.logo{font-weight:700;font-size:.95rem;color:#fff}
.spacer{flex:1}
.status-pill{font-size:.75rem;padding:4px 12px;border-radius:20px;background:#1e1e1e;color:#888;border:1px solid #2a2a2a;transition:all .3s}
.status-pill.listening{color:#22c55e;border-color:#166534;background:#0a1a0a}
.status-pill.speaking{color:#f59e0b;border-color:#92400e;background:#1a1000}
.status-pill.processing{color:#60a5fa;border-color:#1e40af;background:#0a0f1e}
.mic-dot{width:9px;height:9px;border-radius:50%;background:#333;transition:background .3s;flex-shrink:0}
.mic-dot.active{background:#22c55e}
.mic-dot.speaking{background:#f59e0b;animation:pulse .6s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.8)}}
.nav-btn{font-size:.75rem;padding:5px 12px;border-radius:6px;background:#1e1e1e;color:#888;text-decoration:none;border:1px solid #2a2a2a}
.nav-btn:hover{background:#2a2a2a;color:#ccc}
.tone-bar{background:#0d0d0d;border-bottom:1px solid #161616;padding:7px 14px;display:flex;align-items:center;gap:6px;flex-shrink:0}
.tone-lbl{font-size:.65rem;color:#3a3a3a;text-transform:uppercase;letter-spacing:.1em;margin-right:2px}
.tbtn{font-size:.72rem;padding:3px 11px;border-radius:20px;border:1px solid #222;background:transparent;color:#444;cursor:pointer;transition:all .15s}
.tbtn:hover{color:#aaa;border-color:#444}
.tbtn.active[data-t=confident]{background:#0a1a0a;color:#4ade80;border-color:#166534}
.tbtn.active[data-t=formal]{background:#0a0f1e;color:#60a5fa;border-color:#1e3a8a}
.tbtn.active[data-t=warm]{background:#1e0a00;color:#fb923c;border-color:#7c2d12}
.tbtn.active[data-t=technical]{background:#120a1e;color:#a78bfa;border-color:#4c1d95}
.copy-btn{font-size:.68rem;padding:2px 8px;border-radius:4px;border:1px solid #2a2a2a;background:transparent;color:#555;cursor:pointer;float:right;transition:all .2s}
.copy-btn:hover{color:#aaa;border-color:#555}
.followup{margin:8px 16px 14px;padding:10px 14px;background:#0f0a00;border:1px solid #2a2000;border-radius:8px;animation:fadeIn .3s}
.fq-lbl{font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#78350f;margin-bottom:4px}
.fq-text{font-size:.84rem;color:#d97706;line-height:1.4}
.feed{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:14px}
.feed::-webkit-scrollbar{width:3px}
.feed::-webkit-scrollbar-thumb{background:#2a2a2a;border-radius:2px}
.welcome{display:flex;flex-direction:column;align-items:center;justify-content:center;flex:1;gap:10px;color:#333;text-align:center;padding:60px 20px;pointer-events:none}
.welcome .icon{font-size:2.5rem;margin-bottom:8px}
.welcome h2{font-size:1rem;color:#444;font-weight:500}
.welcome p{font-size:.82rem;color:#333}
.qa-card{background:#141414;border:1px solid #1e1e1e;border-radius:12px;overflow:hidden;animation:slideIn .2s ease-out}
@keyframes slideIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.qa-q{padding:14px 16px;border-bottom:1px solid #1e1e1e}
.qa-a{padding:14px 16px}
.qa-lbl{font-size:.65rem;font-weight:700;text-transform:uppercase;letter-spacing:.12em;margin-bottom:6px}
.qa-lbl.ql{color:#60a5fa}
.qa-lbl.al{color:#22c55e}
.qa-q-text{font-size:.92rem;color:#e0e0e0;line-height:1.5}
.answer-row{display:flex;gap:10px;padding:5px 0;font-size:.86rem;line-height:1.5;color:#d0d0d0;border-bottom:1px solid #1a1a1a;animation:fadeIn .2s}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.answer-row:last-child{border-bottom:none}
.adot{color:#22c55e;flex-shrink:0;margin-top:1px}
.generating{display:flex;align-items:center;gap:8px;color:#444;font-size:.8rem;padding:4px 0}
.dots span{display:inline-block;width:5px;height:5px;background:#555;border-radius:50%;margin:0 1px;animation:bounce 1s infinite}
.dots span:nth-child(2){animation-delay:.15s}
.dots span:nth-child(3){animation-delay:.3s}
@keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-5px)}}
.live-bar{flex-shrink:0;margin:0 20px 12px;background:#0f0f00;border:1px solid #2a2a00;border-radius:8px;padding:10px 14px;display:none}
.live-bar.on{display:block}
.live-lbl{font-size:.62rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#854d0e;margin-bottom:3px}
.live-text{font-size:.85rem;color:#fbbf24}
</style>
</head>
<body>
<div class="header">
  <div class="mic-dot" id="mic"></div>
  <span class="logo">🎯 Interview Assistant</span>
  <div class="spacer"></div>
  <span class="status-pill" id="pill">Connecting...</span>
  <a href="/docs" class="nav-btn">📁 Docs</a>
  <a href="/setup" class="nav-btn" onclick="resetSetup(event)">⚙ Setup</a>
  <button class="nav-btn" onclick="quit()" style="background:#2a0a0a;color:#f87171;border-color:#4a1a1a">✕ Quit</button>
</div>
<div class="tone-bar">
  <span class="tone-lbl">Tone</span>
  <button class="tbtn" data-t="confident" onclick="setTone(this)">Confident</button>
  <button class="tbtn" data-t="formal" onclick="setTone(this)">Formal</button>
  <button class="tbtn" data-t="warm" onclick="setTone(this)">Warm</button>
  <button class="tbtn" data-t="technical" onclick="setTone(this)">Technical</button>
</div>
<div class="feed" id="feed">
  <div class="welcome" id="welcome">
    <div class="icon">🎤</div>
    <h2>Ready to assist</h2>
    <p>Start speaking — your interview coach is listening</p>
  </div>
</div>
<div class="live-bar" id="liveBar">
  <div class="live-lbl">🎤 Live</div>
  <div class="live-text" id="liveText"></div>
</div>
<script>
const feed=document.getElementById('feed'),pill=document.getElementById('pill'),mic=document.getElementById('mic'),liveBar=document.getElementById('liveBar'),liveText=document.getElementById('liveText');
let card=null;
function esc(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML}
function scroll(){feed.scrollTop=feed.scrollHeight}
function rmWelcome(){const w=document.getElementById('welcome');if(w)w.remove()}
const es=new EventSource('/stream');
es.onmessage=e=>{
  const{type,data}=JSON.parse(e.data);
  if(type==='status'){
    pill.textContent=data;
    pill.className='status-pill';
    const d=data.toLowerCase();
    if(d.includes('listening'))pill.classList.add('listening');
    else if(d.includes('speaking'))pill.classList.add('speaking');
    else if(d.includes('transcrib')||d.includes('generat')||d.includes('processing'))pill.classList.add('processing');
  }
  if(type==='mic'){mic.className='mic-dot'+(data?' active':'')}
  if(type==='speaking'){mic.className='mic-dot speaking'}
  if(type==='live'){liveBar.classList.add('on');liveText.textContent=data}
  if(type==='question'){
    liveBar.classList.remove('on');liveText.textContent='';rmWelcome();
    card=document.createElement('div');card.className='qa-card';
    card.dataset.q=data;
    card.innerHTML=`<div class="qa-q"><div class="qa-lbl ql">❓ Interviewer</div><div class="qa-q-text">${esc(data)}</div></div><div class="qa-a"><div class="qa-lbl al" style="display:flex;align-items:center;justify-content:space-between">💬 Say this<button class="copy-btn" onclick="copyAnswers(this)">📋 Copy</button></div><div class="generating"><div class="dots"><span></span><span></span><span></span></div>Generating...</div></div>`;
    feed.appendChild(card);scroll();
  }
  if(type==='answer'&&card){
    const gen=card.querySelector('.generating');if(gen)gen.remove();
    const a=card.querySelector('.qa-a');
    const row=document.createElement('div');row.className='answer-row';
    row.innerHTML=`<span class="adot">•</span><span>${esc(data)}</span>`;
    a.appendChild(row);scroll();
  }
  if(type==='followup'&&card){
    // remove old followup if any
    const old=card.querySelector('.followup');if(old)old.remove();
    const fq=document.createElement('div');fq.className='followup';
    fq.innerHTML=`<div class="fq-lbl">🔮 They might ask next</div><div class="fq-text">${esc(data)}</div>`;
    card.appendChild(fq);scroll();
  }
};
es.onerror=()=>{pill.textContent='Reconnecting...';pill.className='status-pill'};
async function quit(){if(!confirm('Stop the interview assistant?'))return;await fetch('/quit',{method:'POST'});window.close()}
async function resetSetup(e){e.preventDefault();await fetch('/api/reset-setup',{method:'POST'});window.location.href='/setup';}
function copyAnswers(btn){
  const rows=[...btn.closest('.qa-card').querySelectorAll('.answer-row span:last-child')].map(s=>s.textContent);
  navigator.clipboard.writeText(rows.map((r,i)=>`${i+1}. ${r}`).join('\n'));
  btn.textContent='✓ Copied';setTimeout(()=>btn.textContent='📋 Copy',2000);
}
function setTone(btn){
  document.querySelectorAll('.tbtn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  fetch('/api/tone',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tone:btn.dataset.t})});
  localStorage.setItem('itone',btn.dataset.t);
}
// restore tone on load
(()=>{
  fetch('/api/session-config').then(r=>r.json()).then(cfg=>{
    const t=cfg.tone||localStorage.getItem('itone')||'confident';
    const b=document.querySelector(`.tbtn[data-t="${t}"]`);
    if(b){document.querySelectorAll('.tbtn').forEach(x=>x.classList.remove('active'));b.classList.add('active');}
  });
})();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(INTERVIEW_HTML)


@app.route("/interview")
def interview():
    return render_template_string(INTERVIEW_HTML)


@app.route("/setup")
def setup_page():
    return render_template_string(SETUP_HTML)


@app.route("/stream")
def sse_stream():
    def generate():
        client_q = _queue.Queue()
        with _sse_lock:
            _sse_clients.append(client_q)
        for msg in list(_sse_history):
            yield f"data: {msg}\n\n"
        try:
            while True:
                try:
                    msg = client_q.get(timeout=20)
                    yield f"data: {msg}\n\n"
                except _queue.Empty:
                    yield ": ping\n\n"
        finally:
            with _sse_lock:
                if client_q in _sse_clients:
                    _sse_clients.remove(client_q)

    from flask import Response
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Question Assister — Document Manager</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f0f0f; color: #e0e0e0; min-height: 100vh; padding: 40px 20px; }
  h1 { font-size: 1.6rem; font-weight: 600; margin-bottom: 4px; color: #fff; }
  .subtitle { color: #666; font-size: 0.9rem; margin-bottom: 32px; }
  .card { background: #1a1a1a; border: 1px solid #2a2a2a; border-radius: 12px; padding: 24px; margin-bottom: 24px; max-width: 800px; }
  .card h2 { font-size: 1rem; font-weight: 600; margin-bottom: 16px; color: #aaa; text-transform: uppercase; letter-spacing: 0.08em; }
  .drop-zone { border: 2px dashed #333; border-radius: 8px; padding: 40px 20px; text-align: center; cursor: pointer; transition: all 0.2s; }
  .drop-zone:hover, .drop-zone.dragover { border-color: #4f8ef7; background: #111d33; }
  .drop-zone p { color: #888; margin-bottom: 12px; }
  .drop-zone input[type=file] { display: none; }
  .btn { display: inline-block; padding: 10px 20px; border-radius: 8px; border: none; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s; }
  .btn-primary { background: #4f8ef7; color: #fff; }
  .btn-primary:hover { background: #3d7de8; }
  .btn-danger { background: #e74c3c; color: #fff; }
  .btn-danger:hover { background: #c0392b; }
  .btn-success { background: #27ae60; color: #fff; }
  .btn-success:hover { background: #219a52; }
  .btn-sm { padding: 5px 12px; font-size: 0.8rem; }
  .file-list { list-style: none; }
  .file-list li { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #222; }
  .file-list li:last-child { border-bottom: none; }
  .file-name { display: flex; align-items: center; gap: 10px; }
  .badge { font-size: 0.7rem; padding: 2px 8px; border-radius: 20px; font-weight: 600; text-transform: uppercase; }
  .badge-pdf { background: #4a1a1a; color: #f87171; }
  .badge-docx { background: #1a2e4a; color: #60a5fa; }
  .badge-json { background: #1a3a2a; color: #4ade80; }
  .badge-txt { background: #2a2a1a; color: #facc15; }
  #log { background: #0a0a0a; border: 1px solid #222; border-radius: 8px; padding: 16px; font-family: 'SF Mono', monospace; font-size: 0.8rem; color: #4ade80; height: 200px; overflow-y: auto; white-space: pre-wrap; }
  .status-msg { padding: 10px 16px; border-radius: 8px; margin-top: 12px; font-size: 0.88rem; }
  .status-ok { background: #0d2a1a; color: #4ade80; border: 1px solid #166534; }
  .status-err { background: #2a0d0d; color: #f87171; border: 1px solid #991b1b; }
  .empty-state { color: #555; text-align: center; padding: 20px 0; font-size: 0.9rem; }
  .actions { display: flex; gap: 10px; flex-wrap: wrap; }
</style>
</head>
<body>
<h1>Question Assister</h1>
<p class="subtitle">Upload documents to your identity knowledge base</p>

<div class="card">
  <h2>Session Setup <span style="font-size:0.75rem;color:#555;font-weight:400;text-transform:none;letter-spacing:0">— optional</span></h2>
  <div style="display:flex;flex-direction:column;gap:10px;">
    <div>
      <label style="font-size:0.8rem;color:#888;margin-bottom:4px;display:block;">What is this interview for?</label>
      <input id="s_role" type="text" placeholder="e.g. Software Engineering internship at Google" style="width:100%;background:#0f0f0f;border:1px solid #222;border-radius:6px;padding:8px 12px;color:#e0e0e0;font-size:0.88rem;outline:none;">
    </div>
    <div>
      <label style="font-size:0.8rem;color:#888;margin-bottom:4px;display:block;">Portfolio / LinkedIn URL</label>
      <input id="s_portfolio" type="text" placeholder="https://linkedin.com/in/yourname" style="width:100%;background:#0f0f0f;border:1px solid #222;border-radius:6px;padding:8px 12px;color:#e0e0e0;font-size:0.88rem;outline:none;">
    </div>
    <div>
      <label style="font-size:0.8rem;color:#888;margin-bottom:4px;display:block;">GitHub URL</label>
      <input id="s_github" type="text" placeholder="https://github.com/yourusername" style="width:100%;background:#0f0f0f;border:1px solid #222;border-radius:6px;padding:8px 12px;color:#e0e0e0;font-size:0.88rem;outline:none;">
    </div>
    <button class="btn btn-primary" onclick="saveSetup()">Save &amp; Build Index</button>
  </div>
  <div id="setupStatus"></div>
</div>

<div class="card">
  <h2>Upload Documents</h2>
  <div class="drop-zone" id="dropZone">
    <p>Drag &amp; drop files here, or click to browse</p>
    <p style="font-size:0.8rem;color:#555;">Supported: PDF, DOCX, JSON, TXT</p>
    <label class="btn btn-primary" style="margin-top:8px;">
      Choose Files
      <input type="file" id="fileInput" multiple accept=".pdf,.docx,.json,.txt">
    </label>
  </div>
  <div id="uploadStatus"></div>
</div>

<div class="card">
  <h2>Identity Documents</h2>
  <ul class="file-list" id="fileList"><li class="empty-state">Loading...</li></ul>
</div>

<div class="card">
  <h2>RAG Index</h2>
  <div class="actions">
    <button class="btn btn-success" onclick="buildIndex(false)">Build Index</button>
    <button class="btn btn-danger" onclick="buildIndex(true)">Rebuild Index (Force)</button>
  </div>
  <div id="indexStatus"></div>
  <div style="margin-top:16px;">
    <div style="color:#555;font-size:0.8rem;margin-bottom:8px;">Output</div>
    <div id="log">Waiting for action...</div>
  </div>
</div>

<script>
async function loadFiles() {
  const res = await fetch('/api/files');
  const data = await res.json();
  const list = document.getElementById('fileList');
  if (!data.files.length) {
    list.innerHTML = '<li class="empty-state">No documents yet. Upload some files above.</li>';
    return;
  }
  list.innerHTML = data.files.map(f => `
    <li>
      <div class="file-name">
        <span class="badge badge-${f.ext}">${f.ext}</span>
        <span>${f.name}</span>
        <span style="color:#555;font-size:0.8rem;">${f.size}</span>
      </div>
      <button class="btn btn-danger btn-sm" onclick="deleteFile('${f.name}')">Delete</button>
    </li>
  `).join('');
}

async function uploadFiles(files) {
  const statusEl = document.getElementById('uploadStatus');
  statusEl.innerHTML = '';
  for (const file of files) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch('/api/upload', { method: 'POST', body: fd });
    const data = await res.json();
    const cls = data.success ? 'status-ok' : 'status-err';
    statusEl.innerHTML += `<div class="status-msg ${cls}">${data.message}</div>`;
  }
  loadFiles();
}

async function deleteFile(name) {
  if (!confirm(`Delete "${name}"?`)) return;
  const res = await fetch('/api/delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename: name })
  });
  const data = await res.json();
  loadFiles();
}

async function buildIndex(force) {
  const logEl = document.getElementById('log');
  const statusEl = document.getElementById('indexStatus');
  logEl.textContent = 'Building index...\\n';
  statusEl.innerHTML = '';

  const res = await fetch('/api/build-index', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force })
  });
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    logEl.textContent += decoder.decode(value);
    logEl.scrollTop = logEl.scrollHeight;
  }
  statusEl.innerHTML = '<div class="status-msg status-ok">Index build complete. You can now run the assistant.</div>';
}

// Drag & drop
const dz = document.getElementById('dropZone');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('dragover'); });
dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));
dz.addEventListener('drop', e => {
  e.preventDefault();
  dz.classList.remove('dragover');
  uploadFiles([...e.dataTransfer.files]);
});
document.getElementById('fileInput').addEventListener('change', e => {
  uploadFiles([...e.target.files]);
  e.target.value = '';
});

loadFiles();

// Pre-populate session setup fields
fetch('/api/session-config').then(r=>r.json()).then(cfg=>{
  if(cfg.interview_for) document.getElementById('s_role').value=cfg.interview_for;
  if(cfg.portfolio_url) document.getElementById('s_portfolio').value=cfg.portfolio_url;
  if(cfg.github_url) document.getElementById('s_github').value=cfg.github_url;
});

async function saveSetup() {
  const statusEl = document.getElementById('setupStatus');
  const logEl = document.getElementById('log');
  statusEl.innerHTML = '';
  logEl.textContent = 'Setting up session...\\n';
  const body = {
    interview_for: document.getElementById('s_role').value.trim(),
    portfolio_url: document.getElementById('s_portfolio').value.trim(),
    github_url: document.getElementById('s_github').value.trim()
  };
  const res = await fetch('/api/setup', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const reader = res.body.getReader(); const dec = new TextDecoder(); let buf='';
  while(true) {
    const {done,value} = await reader.read(); if(done) break;
    buf += dec.decode(value);
    const lines = buf.split('\\n'); buf = lines.pop();
    for(const line of lines) {
      if(!line.startsWith('data:')) continue;
      const raw = line.slice(5).trim(); if(!raw) continue;
      try {
        const ev = JSON.parse(raw);
        if(ev.type==='progress') { logEl.textContent += ev.text+'\\n'; logEl.scrollTop=logEl.scrollHeight; }
        if(ev.type==='done') { statusEl.innerHTML='<div class="status-msg status-ok">Setup complete! Session is ready.</div>'; }
      } catch(e){}
    }
  }
}
</script>
</body>
</html>
"""


def human_size(n):
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


@app.route("/api/setup", methods=["POST"])
def api_setup():
    data = request.get_json()
    interview_for = (data.get("interview_for") or "").strip()
    portfolio_url = (data.get("portfolio_url") or "").strip()
    github_url = (data.get("github_url") or "").strip()

    def generate():
        def ev(text, status="", etype="progress"):
            return f"data: {json.dumps({'type': etype, 'text': text, 'status': status})}\n\n"

        Config.ensure_directories()

        # 1. Save context file
        yield ev(f"Saving: {interview_for}", "active")
        ctx_file = Path(__file__).parent / "identity" / "interview_context.txt"
        with open(ctx_file, "w") as f:
            f.write(f"Interview Target: {interview_for}\n")
            if portfolio_url:
                f.write(f"Portfolio URL: {portfolio_url}\n")
            if github_url:
                f.write(f"GitHub URL: {github_url}\n")
        save_session_config({"interview_for": interview_for, "portfolio_url": portfolio_url,
                             "github_url": github_url, "setup_complete": True})
        yield ev("Interview context saved", "ok")

        # 2. Portfolio
        if portfolio_url:
            yield ev(f"Fetching portfolio...", "active")
            text = _fetch_url(portfolio_url)
            if not text.startswith("Could not"):
                pf = Path(__file__).parent / "identity" / "portfolio_web.txt"
                with open(pf, "w") as f:
                    f.write(f"Portfolio/LinkedIn from {portfolio_url}:\n\n{text}")
                yield ev(f"Portfolio saved ({len(text):,} chars)", "ok")
            else:
                yield ev(f"Portfolio skipped — {text[:60]}", "err")

        # 3. GitHub
        if github_url:
            yield ev("Fetching GitHub repos & READMEs...", "active")
            text = _fetch_github(github_url)
            if text:
                gf = Path(__file__).parent / "identity" / "github_profile.txt"
                with open(gf, "w") as f:
                    f.write(f"GitHub data from {github_url}:\n\n{text}")
                yield ev(f"GitHub data saved ({len(text):,} chars)", "ok")
            else:
                yield ev("GitHub fetch returned nothing", "err")

        # 4. Build RAG
        yield ev("Building RAG index...", "active")
        script = Path(__file__).parent / "rag_pipeline.py"
        proc = subprocess.Popen(
            [sys.executable, str(script), "build", "--force"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=str(Path(__file__).parent),
        )
        for line in proc.stdout:
            line = line.strip()
            if line and ("✓" in line or "Loaded" in line or "Built" in line):
                yield ev(line, "ok")
        proc.wait()
        if proc.returncode == 0:
            yield ev("RAG index ready", "ok")
        else:
            yield ev("RAG build had issues — rebuild in /docs if needed", "err")

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    from flask import Response
    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/tone", methods=["POST"])
def set_tone():
    tone = (request.get_json() or {}).get("tone", "confident")
    cfg = get_session_config() or {}
    cfg["tone"] = tone
    save_session_config(cfg)
    return jsonify({"ok": True})

@app.route("/api/session-config")
def session_config():
    return jsonify(get_session_config() or {})


@app.route("/api/reset-setup", methods=["POST"])
def reset_setup():
    p = Path(__file__).parent / "identity" / "session_config.json"
    if p.exists():
        p.unlink()
    return jsonify({"ok": True})


@app.route("/quit", methods=["POST"])
def quit_app():
    import os
    os._exit(0)


@app.route("/docs")
def docs_page():
    return render_template_string(HTML)


@app.route("/api/files")
def list_files():
    Config.ensure_directories()
    files = []
    for p in sorted(Config.IDENTITY_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS:
            files.append({
                "name": p.name,
                "ext": p.suffix.lstrip(".").lower(),
                "size": human_size(p.stat().st_size),
            })
    return jsonify({"files": files})


@app.route("/api/upload", methods=["POST"])
def upload():
    Config.ensure_directories()
    f = request.files.get("file")
    if not f:
        return jsonify({"success": False, "message": "No file provided"})

    suffix = Path(f.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return jsonify({"success": False, "message": f"Unsupported file type: {suffix}"})

    dest = Config.IDENTITY_DIR / f.filename
    f.save(dest)
    return jsonify({"success": True, "message": f"Uploaded: {f.filename}"})


@app.route("/api/delete", methods=["POST"])
def delete():
    data = request.get_json()
    filename = data.get("filename", "")
    target = Config.IDENTITY_DIR / filename
    if target.exists() and target.is_file():
        target.unlink()
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "File not found"})


@app.route("/api/build-index", methods=["POST"])
def build_index():
    data = request.get_json()
    force = data.get("force", False)

    def generate():
        script = Path(__file__).parent / "rag_pipeline.py"
        args = [sys.executable, str(script), "build"]
        if force:
            args.append("--force")

        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=str(Path(__file__).parent),
        )
        for line in process.stdout:
            yield line
        process.wait()
        yield f"\nProcess exited with code {process.returncode}\n"

    from flask import Response
    return Response(generate(), mimetype="text/plain")


if __name__ == "__main__":
    Config.ensure_directories()
    print("\n" + "=" * 60)
    print("  Question Assister — Upload Server")
    print("=" * 60)
    print(f"\n  Open in browser: http://localhost:5001")
    print(f"  Identity folder: {Config.IDENTITY_DIR.resolve()}")
    print(f"  Vector store:    {Config.VECTOR_STORE_PATH.resolve()}")
    print("\n  Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=5001, debug=False)

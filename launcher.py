"""
Launcher server — runs on port 5002.
Shows a Start button in Chrome. Clicking it starts the interview assistant.
"""
import os
import subprocess
import threading
import time

from flask import Flask, jsonify, render_template_string

PYTHON = "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
SCRIPT = os.path.join(os.path.dirname(__file__), "main_orchestrator_macos.py")

app = Flask(__name__)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Interview Assistant</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0a0a0a;color:#e0e0e0;height:100vh;display:flex;align-items:center;justify-content:center;-webkit-app-region:drag}
.wrap{text-align:center;padding:40px;-webkit-app-region:no-drag}
.icon{font-size:3.2rem;margin-bottom:18px;display:block}
h1{font-size:1.35rem;font-weight:700;color:#fff;margin-bottom:6px}
.sub{font-size:.82rem;color:#444;margin-bottom:44px;line-height:1.5}
.btn{padding:14px 40px;background:#4f8ef7;color:#fff;border:none;border-radius:10px;font-size:.95rem;font-weight:600;cursor:pointer;transition:all .2s;letter-spacing:.02em}
.btn:hover{background:#3d7de8;transform:translateY(-1px)}
.btn:active{transform:translateY(0)}
.btn.loading{background:#0f1e33;color:#60a5fa;cursor:default;transform:none}
.status{font-size:.75rem;color:#444;margin-top:18px;min-height:18px}
.dots span{display:inline-block;animation:b 1.2s infinite;opacity:0}
.dots span:nth-child(2){animation-delay:.2s}
.dots span:nth-child(3){animation-delay:.4s}
@keyframes b{0%,80%,100%{opacity:0}40%{opacity:1}}
</style>
</head>
<body>
<div class="wrap">
  <span class="icon">🎯</span>
  <h1>Interview Assistant</h1>
  <p class="sub">AI-powered real-time coaching<br>for your next interview</p>
  <button class="btn" id="btn" onclick="launch()">▶&nbsp; Start Session</button>
  <div class="status" id="status"></div>
</div>
<script>
async function launch() {
  const btn = document.getElementById('btn');
  const st = document.getElementById('status');
  btn.className = 'btn loading';
  btn.innerHTML = 'Starting<span class="dots"><span>.</span><span>.</span><span>.</span></span>';
  st.textContent = 'Launching interview assistant...';
  await fetch('/launch', {method:'POST'});
  st.textContent = 'Opening in a moment...';
  // Poll until port 5001 is up, then redirect
  for (let i = 0; i < 20; i++) {
    await new Promise(r => setTimeout(r, 1000));
    try {
      const r = await fetch('http://localhost:5001/', {mode:'no-cors'});
      window.location.href = 'http://localhost:5001';
      return;
    } catch(e) {}
  }
  window.location.href = 'http://localhost:5001';
}
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/launch", methods=["POST"])
def launch():
    subprocess.Popen(["pkill", "-f", "main_orchestrator_macos.py"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.4)
    subprocess.Popen(
        [PYTHON, SCRIPT],
        stdout=open("/tmp/interview_assistant.log", "w"),
        stderr=subprocess.STDOUT,
    )
    return jsonify({"ok": True})


def _open_chrome():
    time.sleep(1.2)
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    if os.path.exists(chrome):
        subprocess.Popen([
            chrome,
            "--app=http://localhost:5002",
            "--window-size=380,480",
            "--window-position=1060,100",
        ])
    else:
        import webbrowser
        webbrowser.open("http://localhost:5002")


if __name__ == "__main__":
    threading.Thread(target=_open_chrome, daemon=True).start()
    app.run(port=5002, debug=False)

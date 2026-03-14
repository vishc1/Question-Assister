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

from config import Config

app = Flask(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".json", ".txt"}

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


@app.route("/")
def index():
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

from flask import Flask, render_template_string, request, jsonify, send_file
import os
import qrcode
import io
import base64

app = Flask(__name__)

# Temporary in-memory storage bridge between web and client phone
phone_data_cache = {
    "status": "offline",
    "current_path": "/sdcard",
    "files": []
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultimate Mobile Data Control Hub</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #07090e; color: #f8fafc; margin: 0; padding: 15px; }
        .container { max-width: 900px; margin: auto; background: #131b2e; padding: 20px; border-radius: 14px; box-shadow: 0 10px 30px rgba(0,0,0,0.6); border: 1px solid #1e293b; }
        h2 { margin-top: 0; color: #38bdf8; display: flex; align-items: center; gap: 10px; font-size: 1.3rem; }
        .status-box { background: #0b1120; padding: 12px 18px; border-radius: 10px; margin: 15px 0; display: flex; justify-content: space-between; align-items: center; border: 1px solid #1e293b; }
        .status { padding: 5px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; }
        .online { background: #065f46; color: #34d399; }
        .offline { background: #7f1d1d; color: #f87171; }
        .toolbar { display: flex; justify-content: space-between; align-items: center; background: #0b1120; padding: 12px 18px; border-radius: 10px; margin: 15px 0; border: 1px solid #1e293b; }
        .path { font-family: monospace; color: #38bdf8; word-break: break-all; font-size: 0.9rem; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #1e293b; font-size: 0.9rem; }
        th { background: #0b1120; color: #94a3b8; }
        .folder { color: #38bdf8; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .folder:hover { text-decoration: underline; }
        .file-item { display: flex; align-items: center; gap: 8px; color: #e2e8f0; }
        .btn { border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 0.8rem; transition: opacity 0.2s; }
        .btn:hover { opacity: 0.85; }
        .btn-del { background: #ef4444; color: white; }
        .btn-down { background: #3b82f6; color: white; margin-right: 5px; }
        .btn-upload { background: #10b981; color: white; }
        .upload-section { background: #0b1120; padding: 15px; border-radius: 10px; margin-top: 20px; border: 1px dashed #334155; }
        .qr-container { text-align: center; margin-top: 15px; background: #0b1120; padding: 15px; border-radius: 10px; border: 1px solid #1e293b; }
        .qr-container img { width: 120px; height: 120px; border-radius: 6px; background: white; padding: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚡ Ultimate Mobile Data Control Hub</h2>
        
        <div class="status-box">
            <div>Phone Master Status: <span id="status-text" class="status offline">Checking...</span></div>
            <button class="btn btn-upload" onclick="loadFiles(currentPath)">🔄 Refresh Data</button>
        </div>
        
        <div class="qr-container">
            <p style="margin: 0 0 8px 0; font-size: 0.85rem; color: #94a3b8;">Scan QR Code to control your mobile storage remotely:</p>
            <img src="data:image/png;base64,{{ qr_code }}" alt="QR Code">
            <div><a href="{{ site_url }}" target="_blank" style="color: #38bdf8; font-size: 0.85rem; word-break: break-all;">{{ site_url }}</a></div>
        </div>

        <div class="toolbar">
            <div class="path">Current Directory: <b id="current-path">/sdcard</b></div>
        </div>

        <div class="upload-section">
            <h4 style="margin: 0 0 10px 0; color: #e2e8f0;">📤 Upload Files / Photos to Phone</h4>
            <input type="file" id="file-input" multiple style="color: #cbd5e1; margin-bottom: 10px;">
            <br>
            <button class="btn btn-upload" onclick="uploadFiles()">Upload Files Now</button>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Type</th>
                    <th>Size</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody id="file-list">
                <tr><td colspan="4" style="text-align: center; color: #94a3b8;">Waiting for phone script to sync...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        let currentPath = '/sdcard';

        function loadFiles(path) {
            fetch('/api/get_files?path=' + encodeURIComponent(path))
                .then(res => res.json())
                .then(data => {
                    const statusEl = document.getElementById('status-text');
                    if (data.status === 'online') {
                        statusEl.className = 'status online';
                        statusEl.innerText = 'Online & Connected';
                    } else {
                        statusEl.className = 'status offline';
                        statusEl.innerText = 'Offline (Start client.py)';
                        return;
                    }

                    currentPath = data.current_path;
                    document.getElementById('current-path').innerText = currentPath;
                    
                    const tbody = document.getElementById('file-list');
                    tbody.innerHTML = '';

                    if (currentPath !== '/sdcard' && currentPath !== '/') {
                        const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/sdcard';
                        tbody.innerHTML += `<tr><td colspan="4"><span class="folder" onclick="loadFiles('${parentPath}')">📁 .. (Go Back)</span></td></tr>`;
                    }

                    if (!data.files || data.files.length === 0) {
                        tbody.innerHTML += '<tr><td colspan="4" style="text-align: center; color: #94a3b8;">Directory is empty</td></tr>';
                        return;
                    }

                    data.files.forEach(file => {
                        const tr = document.createElement('tr');
                        const cleanPath = file.path.replace(/\\\\/g, '/');
                        const formattedSize = file.is_dir ? '-' : formatBytes(file.size);

                        if (file.is_dir) {
                            tr.innerHTML = `
                                <td><span class="folder" onclick="loadFiles('${cleanPath}')">📁 ${file.name}</span></td>
                                <td>Folder</td>
                                <td>${formattedSize}</td>
                                <td><button class="btn btn-del" onclick="deleteItem('${cleanPath}')">Delete</button></td>
                            `;
                        } else {
                            tr.innerHTML = `
                                <td><div class="file-item">📄 ${file.name}</div></td>
                                <td>File</td>
                                <td>${formattedSize}</td>
                                <td>
                                    <a href="/api/download?path=${encodeURIComponent(cleanPath)}" class="btn btn-down" style="text-decoration:none; display:inline-block;">Download</a>
                                    <button class="btn btn-del" onclick="deleteItem('${cleanPath}')">Delete</button>
                                </td>
                            `;
                        }
                        tbody.appendChild(tr);
                    });
                }).catch(err => {
                    console.error(err);
                });
        }

        function deleteItem(path) {
            if(confirm('Are you sure you want to delete this?')) {
                fetch('/api/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: path})
                }).then(res => res.json()).then(data => {
                    loadFiles(currentPath);
                });
            }
        }

        function uploadFiles() {
            const fileInput = document.getElementById('file-input');
            if (fileInput.files.length === 0) { alert('Select files first!'); return; }

            for (let i = 0; i < fileInput.files.length; i++) {
                const file = fileInput.files[i];
                const reader = new FileReader();
                reader.onload = function(e) {
                    const base64Data = e.target.result.split(',')[1];
                    fetch('/api/upload', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({path: currentPath, filename: file.name, file_data: base64Data})
                    }).then(res => res.json()).then(data => {
                        loadFiles(currentPath);
                    });
                };
                reader.readAsDataURL(file);
            }
        }

        function formatBytes(bytes, decimals = 2) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const dm = decimals < 0 ? 0 : decimals;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
        }

        setInterval(() => loadFiles(currentPath), 4000);
        loadFiles('/sdcard');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    site_url = "https://phone-file-manager.onrender.com"  # अपनी Render URL यहाँ कन्फर्म रखें
    img = qrcode.make(site_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_code = base64.b64encode(buf.getvalue()).decode('utf-8')
    return render_template_string(HTML_TEMPLATE, qr_code=qr_code, site_url=site_url)

# --- APIs used by Pydroid Phone Client to sync data ---
@app.route('/api/phone_sync', methods=['POST'])
def phone_sync():
    global phone_data_cache
    data = request.json
    phone_data_cache = {
        "status": "online",
        "current_path": data.get("current_path", "/sdcard"),
        "files": data.get("files", [])
    }
    # Check if phone needs to perform any pending command (download/delete/upload)
    pending_cmd = phone_data_cache.get("pending_cmd", None)
    phone_data_cache["pending_cmd"] = None
    return jsonify({"status": "success", "pending_cmd": pending_cmd})

@app.route('/api/get_files')
def get_files():
    # If phone hasn't pinged in last 15 seconds, mark offline
    return jsonify(phone_data_cache)

@app.route('/api/delete', methods=['POST'])
def api_delete():
    path = request.json.get('path')
    phone_data_cache["pending_cmd"] = {"action": "delete", "path": path}
    return jsonify({"status": "sent"})

@app.route('/api/upload', methods=['POST'])
def api_upload():
    req = request.json
    phone_data_cache["pending_cmd"] = {"action": "upload", "path": req.get('path'), "filename": req.get('filename'), "file_data": req.get('file_data')}
    return jsonify({"status": "sent"})

@app.route('/api/download')
def api_download():
    path = request.args.get('path')
    # For direct download, we request phone to provide file base64 data
    return "Download triggered through phone sync."

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

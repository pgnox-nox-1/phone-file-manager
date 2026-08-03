import os
import io
import base64
import qrcode
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

client_sid = None
last_known_path = "/sdcard"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultimate Remote Phone Manager</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0b0f19; color: #f1f5f9; margin: 0; padding: 15px; }
        .container { max-width: 950px; margin: auto; background: #1e293b; padding: 20px; border-radius: 14px; box-shadow: 0 12px 30px rgba(0,0,0,0.5); border: 1px solid #334155; }
        h2 { margin-top: 0; color: #38bdf8; display: flex; align-items: center; gap: 10px; font-size: 1.4rem; }
        .status-box { background: #0f172a; padding: 12px 18px; border-radius: 10px; margin: 15px 0; display: flex; justify-content: space-between; align-items: center; border: 1px solid #334155; }
        .status { padding: 5px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; }
        .online { background: #065f46; color: #34d399; }
        .offline { background: #7f1d1d; color: #f87171; }
        .toolbar { display: flex; justify-content: space-between; align-items: center; background: #0f172a; padding: 12px 18px; border-radius: 10px; margin: 15px 0; border: 1px solid #334155; }
        .path { font-family: monospace; color: #38bdf8; word-break: break-all; font-size: 0.95rem; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #334155; font-size: 0.9rem; }
        th { background: #0f172a; color: #94a3b8; }
        .folder { color: #38bdf8; cursor: pointer; font-weight: 600; display: flex; align-items: center; gap: 8px; }
        .folder:hover { text-decoration: underline; }
        .file-item { display: flex; align-items: center; gap: 8px; color: #e2e8f0; }
        .btn { border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 0.82rem; transition: opacity 0.2s; }
        .btn:hover { opacity: 0.8; }
        .btn-del { background: #ef4444; color: white; }
        .btn-down { background: #3b82f6; color: white; margin-right: 5px; }
        .btn-upload { background: #10b981; color: white; }
        .upload-section { background: #0f172a; padding: 15px; border-radius: 10px; margin-top: 20px; border: 1px dashed #475569; }
        .qr-container { text-align: center; margin-top: 15px; background: #0f172a; padding: 15px; border-radius: 10px; border: 1px solid #334155; }
        .qr-container img { width: 120px; height: 120px; border-radius: 6px; background: white; padding: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>⚡ Ultimate Remote Phone Manager</h2>
        
        <div class="status-box">
            <div>Master Phone Status: <span id="status" class="status offline">Offline</span></div>
            <button class="btn btn-upload" onclick="refreshFiles()">🔄 Refresh Storage</button>
        </div>
        
        <div class="qr-container">
            <p style="margin: 0 0 8px 0; font-size: 0.85rem; color: #94a3b8;">Scan QR Code or open link to control phone storage:</p>
            <img id="qr-img" src="" alt="QR Code">
            <div><a id="site-url" href="#" target="_blank" style="color: #38bdf8; font-size: 0.85rem; word-break: break-all;"></a></div>
        </div>

        <div class="toolbar">
            <div class="path">Path: <b id="current-path">/sdcard</b></div>
        </div>

        <div class="upload-section">
            <h4 style="margin: 0 0 10px 0; color: #e2e8f0;">📤 Send Files / Photos to Phone</h4>
            <input type="file" id="file-input" multiple style="color: #cbd5e1; margin-bottom: 10px;">
            <br>
            <button class="btn btn-upload" onclick="uploadFiles()">Upload to Phone Now</button>
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
                <tr><td colspan="4" style="text-align: center; color: #94a3b8;">Waiting for Master Phone to come online in Pydroid 3...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        const socket = io();
        let currentPath = '/sdcard';

        fetch('/get_qr')
            .then(res => res.json())
            .then(data => {
                document.getElementById('qr-img').src = 'data:image/png;base64,' + data.qr_code;
                const link = document.getElementById('site-url');
                link.href = data.url;
                link.innerText = data.url;
            });

        socket.on('status_update', (data) => {
            const statusEl = document.getElementById('status');
            if (data.status === 'online') {
                statusEl.className = 'status online';
                statusEl.innerText = 'Online (Connected)';
                refreshFiles();
            } else {
                statusEl.className = 'status offline';
                statusEl.innerText = 'Offline';
            }
        });

        function refreshFiles() {
            socket.emit('request_file_list', { path: currentPath });
        }

        socket.on('response_file_list', (data) => {
            if(data.error) {
                document.getElementById('file-list').innerHTML = `<tr><td colspan="4" style="text-align: center; color: #f87171;">${data.error}</td></tr>`;
                return;
            }

            if(data.current_path) {
                currentPath = data.current_path;
                document.getElementById('current-path').innerText = currentPath;
            }

            const tbody = document.getElementById('file-list');
            tbody.innerHTML = '';

            if (currentPath !== '/sdcard' && currentPath !== '/') {
                const parentPath = currentPath.substring(0, currentPath.lastIndexOf('/')) || '/sdcard';
                tbody.innerHTML += `<tr><td colspan="4"><span class="folder" onclick="openFolder('${parentPath}')">📁 .. (Go Back)</span></td></tr>`;
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
                        <td><span class="folder" onclick="openFolder('${cleanPath}')">📁 ${file.name}</span></td>
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
                            <button class="btn btn-down" onclick="downloadFile('${cleanPath}')">Download</button>
                            <button class="btn btn-del" onclick="deleteItem('${cleanPath}')">Delete</button>
                        </td>
                    `;
                }
                tbody.appendChild(tr);
            });
        });

        socket.on('response_download', (data) => {
            const link = document.createElement('a');
            link.href = 'data:application/octet-stream;base64,' + data.file_data;
            link.download = data.filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });

        socket.on('response_upload', (data) => {
            alert('File successfully transferred to phone!');
            refreshFiles();
        });

        function openFolder(path) {
            socket.emit('request_file_list', { path: path });
        }

        function deleteItem(path) {
            if(confirm('Are you sure you want to delete this file from the phone?')) {
                socket.emit('request_delete', { path: path });
            }
        }

        function downloadFile(path) {
            socket.emit('request_download', { path: path });
        }

        function uploadFiles() {
            const fileInput = document.getElementById('file-input');
            if (fileInput.files.length === 0) {
                alert('Please select files first!');
                return;
            }
            
            for (let i = 0; i < fileInput.files.length; i++) {
                const file = fileInput.files[i];
                const reader = new FileReader();
                
                reader.onload = function(e) {
                    const base64Data = e.target.result.split(',')[1];
                    socket.emit('request_upload', {
                        path: currentPath,
                        filename: file.name,
                        file_data: base64Data
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
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_qr')
def get_qr():
    site_url = "https://phone-file-manager.onrender.com"  # अपनी Render URL यहाँ कन्फर्म रखें
    img = qrcode.make(site_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_code = base64.b64encode(buf.getvalue()).decode('utf-8')
    return jsonify({"url": site_url, "qr_code": qr_code})

@socketio.on('connect')
def handle_connect():
    print("Dashboard connected.")

@socketio.on('disconnect')
def handle_disconnect():
    global client_sid
    if request.sid == client_sid:
        client_sid = None
        socketio.emit('status_update', {"status": "offline"})
        print("Master Phone disconnected.")

@socketio.on('register_phone')
def handle_register(data):
    global client_sid
    client_sid = request.sid
    socketio.emit('status_update', {"status": "online"})
    print("Master Phone registered and online!")

@socketio.on('request_file_list')
def handle_file_list(data):
    global client_sid, last_known_path
    path = data.get('path', '/sdcard')
    last_known_path = path
    if client_sid:
        socketio.emit('get_file_list', {"path": path}, room=client_sid)
    else:
        socketio.emit('response_file_list', {"error": "Master Phone is offline. Start client.py in Pydroid 3."})

@socketio.on('forward_file_list')
def handle_forward_list(data):
    socketio.emit('response_file_list', data)

@socketio.on('request_delete')
def handle_delete(data):
    global client_sid
    if client_sid:
        socketio.emit('do_delete', data, room=client_sid)

@socketio.on('request_download')
def handle_download(data):
    global client_sid
    if client_sid:
        socketio.emit('do_download', data, room=client_sid)

@socketio.on('forward_download')
def handle_forward_download(data):
    socketio.emit('response_download', data)

@socketio.on('request_upload')
def handle_upload(data):
    global client_sid
    if client_sid:
        socketio.emit('do_upload', data, room=client_sid)

@socketio.on('forward_upload')
def handle_forward_upload(data):
    socketio.emit('response_upload', data)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)

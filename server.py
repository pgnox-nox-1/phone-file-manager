import os
import io
import base64
import qrcode
from flask import Flask, render_template_string, request, jsonify
from flask_sock import Sock

app = Flask(__name__)
sock = Sock(app)

phone_ws = None
browser_ws = set()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All-in-One Phone Data Manager</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 15px; }
        .container { max-width: 900px; margin: auto; background: #1e293b; padding: 20px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h2 { color: #38bdf8; margin-top: 0; display: flex; align-items: center; gap: 10px; }
        .status-box { background: #0f172a; padding: 12px 16px; border-radius: 8px; margin: 15px 0; display: flex; justify-content: space-between; align-items: center; }
        .status { padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: bold; }
        .online { background: #065f46; color: #34d399; }
        .offline { background: #7f1d1d; color: #f87171; }
        .qr-box { text-align: center; background: #0f172a; padding: 15px; border-radius: 8px; margin: 15px 0; }
        .qr-box img { width: 140px; height: 140px; background: white; padding: 5px; border-radius: 6px; }
        .toolbar { background: #0f172a; padding: 10px 15px; border-radius: 8px; margin-bottom: 15px; font-family: monospace; color: #38bdf8; word-break: break-all; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #334155; font-size: 0.9rem; }
        th { background: #0f172a; color: #94a3b8; }
        .folder { color: #38bdf8; cursor: pointer; font-weight: bold; }
        .folder:hover { text-decoration: underline; }
        .btn { border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 0.8rem; }
        .btn-down { background: #3b82f6; color: white; margin-right: 5px; }
        .btn-del { background: #ef4444; color: white; }
        .btn-refresh { background: #10b981; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <h2>📱 All-in-One Phone Data Manager</h2>
        
        <div class="status-box">
            <div>फोन कनेक्शन स्टेटस: <span id="status" class="status offline">Offline</span></div>
            <button class="btn btn-refresh" onclick="refreshFiles()">🔄 रिफ्रेश करें</button>
        </div>

        <div class="qr-box">
            <p style="margin: 0 0 8px 0; font-size: 0.85rem; color: #94a3b8;">इस QR कोड को स्कैन करके सीधे मोबाइल से भी मैनेज कर सकते हैं:</p>
            <img id="qr-img" src="" alt="QR Code">
            <div><a id="site-url" href="#" target="_blank" style="color: #38bdf8; font-size: 0.8rem;"></a></div>
        </div>

        <div class="toolbar">
            करेंट पाथ: <b id="current-path">/sdcard</b>
        </div>

        <table>
            <thead>
                <tr>
                    <th>नाम (Name)</th>
                    <th>प्रकार</th>
                    <th>साइज</th>
                    <th>एक्शन (Actions)</th>
                </tr>
            </thead>
            <tbody id="file-list">
                <tr><td colspan="4" style="text-align: center; color: #94a3b8;">फोन को Pydroid 3 से ऑनलाइन करें...</td></tr>
            </tbody>
        </table>
    </div>

    <script>
        let ws;
        let currentPath = '/sdcard';

        // QR कोड लोड करना
        fetch('/get_qr')
            .then(res => res.json())
            .then(data => {
                document.getElementById('qr-img').src = 'data:image/png;base64,' + data.qr_code;
                const link = document.getElementById('site-url');
                link.href = data.url;
                link.innerText = data.url;
            });

        function connectWS() {
            const proto = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            ws = new WebSocket(proto + window.location.host + '/ws');

            ws.onmessage = function(event) {
                const msg = JSON.parse(event.data);
                
                if(msg.type === 'status') {
                    const statusEl = document.getElementById('status');
                    if(msg.status === 'online') {
                        statusEl.className = 'status online';
                        statusEl.innerText = 'Online (जुड़ गया)';
                        refreshFiles();
                    } else {
                        statusEl.className = 'status offline';
                        statusEl.innerText = 'Offline';
                        document.getElementById('file-list').innerHTML = `<tr><td colspan="4" style="text-align: center; color: #f87171;">फोन ऑफलाइन है। कृपया Pydroid 3 में client.py चलाएं।</td></tr>`;
                    }
                }
                else if(msg.type === 'file_list') {
                    renderFiles(msg.data);
                }
                else if(msg.type === 'download_resp') {
                    const link = document.createElement('a');
                    link.href = 'data:application/octet-stream;base64,' + msg.file_data;
                    link.download = msg.filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
            };

            ws.onclose = function() {
                setTimeout(connectWS, 3000);
            };
        }

        connectWS();

        function refreshFiles() {
            if(ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({action: 'request_file_list', path: currentPath}));
            }
        }

        function renderFiles(data) {
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
                tbody.innerHTML += `<tr><td colspan="4"><span class="folder" onclick="openFolder('${parentPath}')">📁 .. (वापस जाएं)</span></td></tr>`;
            }

            if (!data.files || data.files.length === 0) {
                tbody.innerHTML += '<tr><td colspan="4" style="text-align: center; color: #94a3b8;">यह फोल्डर खाली है</td></tr>';
                return;
            }

            data.files.forEach(file => {
                const tr = document.createElement('tr');
                const cleanPath = file.path;
                const sizeStr = file.is_dir ? '-' : formatBytes(file.size);

                if (file.is_dir) {
                    tr.innerHTML = `
                        <td><span class="folder" onclick="openFolder('${cleanPath}')">📁 ${file.name}</span></td>
                        <td>फोल्डर</td>
                        <td>${sizeStr}</td>
                        <td><button class="btn btn-del" onclick="deleteItem('${cleanPath}')">डिलीट</button></td>
                    `;
                } else {
                    tr.innerHTML = `
                        <td>📄 ${file.name}</td>
                        <td>फाइल</td>
                        <td>${sizeStr}</td>
                        <td>
                            <button class="btn btn-down" onclick="downloadFile('${cleanPath}')">डाउनलोड</button>
                            <button class="btn btn-del" onclick="deleteItem('${cleanPath}')">डिलीट</button>
                        </td>
                    `;
                }
                tbody.appendChild(tr);
            });
        }

        function openFolder(path) {
            currentPath = path;
            refreshFiles();
        }

        function deleteItem(path) {
            if(confirm('क्या आप वाकई इस फाइल/फोल्डर को डिलीट करना चाहते हैं?')) {
                ws.send(JSON.stringify({action: 'delete', path: path}));
                setTimeout(refreshFiles, 500);
            }
        }

        function downloadFile(path) {
            ws.send(JSON.stringify({action: 'download', path: path}));
        }

        function formatBytes(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024, sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
    site_url = request.host_url.rstrip('/') # आपकी Render URL ऑटो-डिटेक्ट हो जाएगी
    img = qrcode.make(site_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_code = base64.b64encode(buf.getvalue()).decode('utf-8')
    return jsonify({"url": site_url, "qr_code": qr_code})

@sock.route('/ws')
def ws_handler(ws):
    global phone_ws
    user_agent = request.headers.get('User-Agent', '')
    is_phone = 'Python' in user_agent or 'websockets' in user_agent
    
    if is_phone:
        phone_ws = ws
        print("Master Phone connected!")
        broadcast_status("online")
        try:
            while True:
                msg = ws.receive()
                if msg is None: break
                for b_ws in list(browser_ws):
                    try: b_ws.send(msg)
                    except: browser_ws.remove(b_ws)
        finally:
            phone_ws = None
            print("Master Phone disconnected!")
            broadcast_status("offline")
    else:
        browser_ws.add(ws)
        ws.send('{"type": "status", "status": "%s"}' % ("online" if phone_ws else "offline"))
        try:
            while True:
                msg = ws.receive()
                if msg is None: break
                if phone_ws:
                    try: phone_ws.send(msg)
                    except: pass
        finally:
            browser_ws.remove(ws)

def broadcast_status(status_str):
    for b_ws in list(browser_ws):
        try: b_ws.send('{"type": "status", "status": "%s"}' % status_str)
        except: browser_ws.remove(b_ws)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
            

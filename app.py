from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
import qrcode
import io
import base64

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'secure_phone_manager_secret_key_2026'

# 200MB buffer size for heavy photos, videos, and screenshots sharing
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=200 * 1024 * 1024)

# Connected devices list
connected_devices = {}

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/get_qr')
def get_qr():
    url = "https://phone-file-manager.onrender.com"  # अपनी Render URL यहाँ डालें
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded_img = base64.b64encode(buf.getvalue()).decode('utf-8')
    return {'qr_code': encoded_img, 'url': url}

@socketio.on('connect')
def handle_connect():
    print(f'[Server] Client connected: {request.sid}')

@socketio.on('register_device')
def handle_register(data):
    device_name = data.get('device_name', 'Android Phone')
    connected_devices[request.sid] = device_name
    print(f"[Server] Mobile device registered: {device_name} ({request.sid})")
    emit('status_update', {'status': 'connected', 'devices': list(connected_devices.values())}, broadcast=True)

@socketio.on('fetch_file_list')
def handle_fetch(data):
    target_sid = data.get('target_sid')
    if target_sid:
        emit('fetch_file_list', data, room=target_sid)
    else:
        # Agar koi specific target nahi hai, toh pehle registered phone ko bhejo
        for sid, name in connected_devices.items():
            emit('fetch_file_list', data, room=sid)
            break

@socketio.on('response_file_list')
def handle_response_files(data):
    emit('response_file_list', data, broadcast=True)

@socketio.on('download_file')
def handle_download(data):
    target_sid = data.get('target_sid')
    if target_sid:
        emit('download_file', data, room=target_sid)

@socketio.on('response_download')
def handle_response_download(data):
    emit('response_download', data, broadcast=True)

@socketio.on('execute_delete')
def handle_delete(data):
    target_sid = data.get('target_sid')
    if target_sid:
        emit('execute_delete', data, room=target_sid)

@socketio.on('upload_file_chunk')
def handle_upload_chunk(data):
    target_sid = data.get('target_sid')
    if target_sid:
        emit('upload_file_chunk', data, room=target_sid)

@socketio.on('response_upload')
def handle_response_upload(data):
    emit('response_upload', data, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in connected_devices:
        del connected_devices[request.sid]
        print(f"[Server] Mobile device disconnected: {request.sid}")
        emit('status_update', {'status': 'disconnected', 'devices': list(connected_devices.values())}, broadcast=True)
    else:
        print(f"[Server] Web client disconnected: {request.sid}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
        

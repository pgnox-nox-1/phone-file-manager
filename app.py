from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
import qrcode
import io
import base64

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'secure_phone_manager_secret_key_2026'

socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=300 * 1024 * 1024)

# Storage for connected nodes
phone_sid = None
web_clients = {}

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/get_qr')
def get_qr():
    url = "https://phone-file-manager.onrender.com"  # अपनी Render URL यहाँ कन्फर्म रखें
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
    global phone_sid
    phone_sid = request.sid
    device_name = data.get('device_name', 'Android Master Phone')
    print(f"[Server] Master Phone Registered Successfully! SID: {phone_sid}")
    emit('status_update', {'status': 'connected', 'device': device_name}, broadcast=True)

@socketio.on('request_permission')
def handle_permission_req(data):
    # Friend requests permission to access/share data
    if phone_sid:
        emit('incoming_permission_request', {'requester_sid': request.sid, 'requester_name': data.get('name', 'Friend')}, room=phone_sid)
    else:
        emit('permission_response', {'status': 'rejected', 'msg': 'Master phone offline'}, room=request.sid)

@socketio.on('grant_permission')
def handle_grant_permission(data):
    requester_sid = data.get('requester_sid')
    status = data.get('status') # 'approved' or 'denied'
    emit('permission_response', {'status': status}, room=requester_sid)
    if status == 'approved':
        print(f"[Server] Permission granted to client: {requester_sid}")

@socketio.on('fetch_file_list')
def handle_fetch(data):
    if phone_sid:
        emit('fetch_file_list', data, room=phone_sid)

@socketio.on('response_file_list')
def handle_response_files(data):
    emit('response_file_list', data, broadcast=True)

@socketio.on('download_file')
def handle_download(data):
    if phone_sid:
        emit('download_file', data, room=phone_sid)

@socketio.on('response_download')
def handle_response_download(data):
    emit('response_download', data, broadcast=True)

@socketio.on('execute_delete')
def handle_delete(data):
    if phone_sid:
        emit('execute_delete', data, room=phone_sid)

@socketio.on('upload_file_chunk')
def handle_upload_chunk(data):
    if phone_sid:
        emit('upload_file_chunk', data, room=phone_sid)

@socketio.on('response_upload')
def handle_response_upload(data):
    emit('response_upload', data, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global phone_sid
    if request.sid == phone_sid:
        phone_sid = None
        print("[Server] Master Phone Disconnected!")
        emit('status_update', {'status': 'disconnected', 'device': 'None'}, broadcast=True)
    else:
        print(f"[Server] Web/Friend client disconnected: {request.sid}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)

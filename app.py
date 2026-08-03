from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
import qrcode
import io
import base64

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'secure_phone_manager_secret_key_2026'

# Large buffer size (200MB) for seamless media and file transfers
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=200 * 1024 * 1024)

phone_sid = None

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/get_qr')
def get_qr():
    # Update with your actual Render service URL
    url = "https://phone-file-manager.onrender.com"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded_img = base64.b64encode(buf.getvalue()).decode('utf-8')
    return {'qr_code': encoded_img, 'url': url}

@socketio.on('connect')
def handle_connect():
    print(f'[Server] Web client connected: {request.sid}')

@socketio.on('register_device')
def handle_register():
    global phone_sid
    phone_sid = request.sid
    print(f"[Server] Mobile device registered successfully with SID: {phone_sid}")
    emit('status_update', {'status': 'connected'}, broadcast=True)

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
        print("[Server] Mobile device disconnected.")
        emit('status_update', {'status': 'disconnected'}, broadcast=True)
    else:
        print(f"[Server] Web client disconnected: {request.sid}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
    

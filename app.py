from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit
import os
import qrcode
import io
import base64

app = Flask(__name__, template_folder='.')
app.config['SECRET_KEY'] = 'manish_ultimate_secure_hub_2026'

# Optimized for stable streaming and data sync
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', max_http_buffer_size=500 * 1024 * 1024)

phone_sid = None

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
    print(f'[Server] Connected client SID: {request.sid}')

@socketio.on('register_master')
def handle_register(data):
    global phone_sid
    phone_sid = request.sid
    print(f"[Server SUCCESS] Master Phone Registered! SID: {phone_sid}")
    emit('status_update', {'status': 'online', 'device': data.get('device_name', 'Master Phone')}, broadcast=True)

@socketio.on('ping_master')
def handle_ping():
    if phone_sid:
        emit('pong_master', room=phone_sid)

@socketio.on('request_file_list')
def handle_fetch(data):
    if phone_sid:
        emit('fetch_file_list', data, room=phone_sid)
    else:
        emit('response_file_list', {'error': 'Master phone is offline. Please check Pydroid 3 script.'}, room=request.sid)

@socketio.on('response_file_list')
def handle_response_files(data):
    emit('response_file_list', data, broadcast=True)

@socketio.on('request_download')
def handle_download(data):
    if phone_sid:
        emit('download_file', data, room=phone_sid)

@socketio.on('response_download')
def handle_response_download(data):
    emit('response_download', data, broadcast=True)

@socketio.on('request_delete')
def handle_delete(data):
    if phone_sid:
        emit('execute_delete', data, room=phone_sid)

@socketio.on('request_upload')
def handle_upload(data):
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
        print("[Server WARNING] Master Phone Disconnected!")
        emit('status_update', {'status': 'offline', 'device': 'None'}, broadcast=True)
    else:
        print(f"[Server] Web client disconnected: {request.sid}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
    

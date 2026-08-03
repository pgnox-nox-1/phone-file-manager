from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit
import qrcode
import io
import base64
import os

app = Flask(__name__, root_path='.')
app.config['SECRET_KEY'] = 'remote_file_manager_secret'
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=100 * 1024 * 1024)

DEVICE_SID = None

@app.route('/')
def index():
    server_url = request.url_root
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(server_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    qr_code_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            html_content = f.read()
        return render_template_string(html_content, qr_code=qr_code_base64, server_url=server_url)
    except Exception as e:
        return f"Error reading index.html: {str(e)}"

@socketio.on('register_device')
def handle_device_register():
    global DEVICE_SID
    DEVICE_SID = request.sid
    print("Mobile Device Connected!")
    emit('device_status', {'connected': True}, broadcast=True)

@socketio.on('get_files')
def get_files(data):
    if DEVICE_SID:
        emit('fetch_file_list', data, room=DEVICE_SID)

@socketio.on('response_file_list')
def response_file_list(data):
    emit('render_file_list', data, broadcast=True)

@socketio.on('delete_file_request')
def delete_file_request(data):
    if DEVICE_SID:
        emit('execute_delete', data, room=DEVICE_SID)

@socketio.on('download_file_request')
def download_file_request(data):
    if DEVICE_SID:
        emit('execute_download', data, room=DEVICE_SID)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
  

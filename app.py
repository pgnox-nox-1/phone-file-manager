from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret_key_123'
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=100 * 1024 * 1024)

phone_sid = None

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('register_device')
def handle_register():
    global phone_sid
    phone_sid = request.sid
    print("Phone registered:", phone_sid)
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

@socketio.on('disconnect')
def handle_disconnect():
    global phone_sid
    if request.sid == phone_sid:
        phone_sid = None
        emit('status_update', {'status': 'disconnected'}, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
    

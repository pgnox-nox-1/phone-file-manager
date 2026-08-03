import socketio
import os
sio = socketio.Client()

# Render deployed URL
SERVER_URL = 'https://phone-file-manager-1.onrender.com'

@sio.event
def connect():
    print("Successfully connected to the server!")
    sio.emit('register_device')

@sio.on('fetch_file_list')
def send_file_list(data):
    req_path = data.get('path', '/sdcard')
    files_data = []
    try:
        for item in os.listdir(req_path):
            full_path = os.path.join(req_path, item)
            is_dir = os.path.isdir(full_path)
            size = os.path.getsize(full_path) if not is_dir else 0
            files_data.append({
                'name': item,
                'path': full_path,
                'is_dir': is_dir,
                'size': f"{round(size / (1024*1024), 2)} MB" if not is_dir else "-"
            })
    except Exception as e:
        print("Read Error:", e)
    
    sio.emit('response_file_list', {'files': files_data})

@sio.on('execute_delete')
def handle_delete(data):
    file_path = data.get('path')
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Deleted File: {file_path}")
        elif os.path.isdir(file_path):
            os.rmdir(file_path)
            print(f"Deleted Directory: {file_path}")
        send_file_list({'path': '/sdcard'})
    except Exception as e:
        print("Delete Error:", e)

try:
    sio.connect(SERVER_URL)
    sio.wait()
except Exception as e:
    print("Connection Error:", e)
            

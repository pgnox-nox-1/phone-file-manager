import socketio
import os
import time
import base64
import shutil

sio = socketio.Client(logger=False, engineio_logger=False)
SERVER_URL = 'https://phone-file-manager.onrender.com'  # अपनी Render URL यहाँ डालें
DEVICE_NAME = "Manish Ultimate Phone"

def get_dir_contents(req_path):
    files_data = []
    if not req_path or not os.path.exists(req_path):
        req_path = '/sdcard'
    try:
        for item in os.listdir(req_path):
            if item.startswith('.'):
                continue
            full_path = os.path.join(req_path, item)
            is_dir = os.path.isdir(full_path)
            
            file_size = 0
            if not is_dir:
                try:
                    file_size = os.path.getsize(full_path)
                except:
                    file_size = 0
                    
            files_data.append({
                'name': item,
                'path': full_path,
                'is_dir': is_dir,
                'size': file_size
            })
    except Exception as e:
        print(f"[Client Error] Directory read error at {req_path}: {e}")
    return files_data, req_path

@sio.event
def connect():
    print(f"\n[Client SUCCESS] Connected to Render Server! Registering as Master...")
    sio.emit('register_master', {'device_name': DEVICE_NAME})
    # Initial load send
    files_data, current_path = get_dir_contents('/sdcard')
    sio.emit('response_file_list', {'files': files_data, 'current_path': current_path})

@sio.event
def disconnect():
    print("[Client WARNING] Disconnected from server. Trying to reconnect...")

@sio.on('fetch_file_list')
def send_file_list(data):
    req_path = data.get('path', '/sdcard') if data else '/sdcard'
    print(f"[Client] Fetching path: {req_path}")
    files_data, current_path = get_dir_contents(req_path)
    sio.emit('response_file_list', {'files': files_data, 'current_path': current_path})

@sio.on('download_file')
def handle_download(data):
    file_path = data.get('path')
    print(f"[Client] Uploading/Sending file to web requester: {file_path}")
    try:
        if os.path.isfile(file_path):
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode('utf-8')
            sio.emit('response_download', {
                'filename': os.path.basename(file_path),
                'file_data': encoded
            })
    except Exception as e:
        print(f"[Client Error] Download failed: {e}")

@sio.on('execute_delete')
def handle_delete(data):
    file_path = data.get('path')
    current_dir = os.path.dirname(file_path)
    if not current_dir or not os.path.exists(current_dir):
        current_dir = '/sdcard'
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
        print(f"[Client] Deleted: {file_path}")
    except Exception as e:
        print(f"[Client Error] Delete failed: {e}")
    
    files_data, current_path = get_dir_contents(current_dir)
    sio.emit('response_file_list', {'files': files_data, 'current_path': current_path})

@sio.on('upload_file_chunk')
def handle_upload(data):
    target_path = data.get('path', '/sdcard/Download')
    if not os.path.exists(target_path):
        target_path = '/sdcard'
    filename = data.get('filename')
    file_bytes = base64.b64decode(data.get('file_data'))
    
    full_save_path = os.path.join(target_path, filename)
    try:
        with open(full_save_path, 'wb') as f:
            f.write(file_bytes)
        print(f"[Client SUCCESS] Received file from remote hub: {full_save_path}")
    except Exception as e:
        print(f"[Client Error] Save failed: {e}")
        
    files_data, current_path = get_dir_contents(target_path)
    sio.emit('response_upload', {'files': files_data, 'current_path': current_path})

if __name__ == '__main__':
    print("=== PYDROID 3 ULTRA MASTER NODE STARTED ===")
    print("Connecting to Render Cloud... Keep this Pydroid screen open.")
    while True:
        try:
            if not sio.connected:
                sio.connect(SERVER_URL, transports=['websocket', 'polling'])
            sio.sleep(2)
        except Exception as e:
            print(f"[Connection Retry] Waiting for network/server... ({e})")
            time.sleep(3)
    

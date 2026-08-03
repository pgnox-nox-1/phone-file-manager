import os
import shutil
import base64
import socketio

sio = socketio.Client()
SERVER_URL = 'https://phone-file-manager.onrender.com'  # अपनी Render URL यहाँ डालें

@sio.event
def connect():
    print("Connected to Cloud Server! Registering phone...")
    sio.emit('register_phone', {})

@sio.event
def disconnect():
    print("Disconnected from server. Reconnecting...")

@sio.on('get_file_list')
def on_get_file_list(data):
    path = data.get('path', '/sdcard')
    files_data = []
    if not os.path.exists(path):
        path = '/sdcard'
    
    try:
        for item in os.listdir(path):
            if item.startswith('.'):
                continue
            full_path = os.path.join(path, item)
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
        print(f"Error reading path: {e}")

    sio.emit('forward_file_list', {
        "current_path": path,
        "files": files_data
    })

@sio.on('do_delete')
def on_do_delete(data):
    target_path = data.get('path')
    try:
        if os.path.isfile(target_path):
            os.remove(target_path)
        elif os.path.isdir(target_path):
            shutil.rmtree(target_path)
        print(f"Deleted: {target_path}")
    except Exception as e:
        print(f"Delete failed: {e}")
    sio.emit('request_file_list', {"path": os.path.dirname(target_path)})

@sio.on('do_download')
def on_do_download(data):
    target_path = data.get('path')
    try:
        with open(target_path, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
        sio.emit('forward_download', {
            "filename": os.path.basename(target_path),
            "file_data": b64_data
        })
        print(f"Downloaded and sent: {target_path}")
    except Exception as e:
        print(f"Download failed: {e}")

@sio.on('do_upload')
def on_do_upload(data):
    folder = data.get('path')
    filename = data.get('filename')
    b64_data = data.get('file_data')
    save_path = os.path.join(folder, filename)
    try:
        with open(save_path, 'wb') as f:
            f.write(base64.b64decode(b64_data))
        sio.emit('forward_upload', {"status": "success"})
        print(f"Uploaded file saved to: {save_path}")
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == '__main__':
    print("=== PYDROID 3 LIVE SOCKET CLIENT STARTED ===")
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except Exception as e:
            print(f"Connection error: {e}, retrying in 3 seconds...")
            import time
            time.sleep(3)
    

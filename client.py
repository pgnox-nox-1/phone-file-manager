import os
import base64
import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to server successfully!")
    sio.emit('register_device')

@sio.on('fetch_file_list')
def on_fetch_files(data):
    path = data.get('path', '/sdcard')
    
    # If path is empty or invalid, default to /sdcard
    if not path or not os.path.exists(path):
        path = '/sdcard'
        
    try:
        files = []
        for item in os.listdir(path):
            # Skip hidden files starting with a dot
            if item.startswith('.'):
                continue
            item_path = os.path.join(path, item)
            is_dir = os.path.isdir(item_path)
            files.append({
                'name': item,
                'path': item_path,
                'is_dir': is_dir
            })
        sio.emit('response_file_list', {'current_path': path, 'files': files})
    except Exception as e:
        print("Error reading path:", e)
        # Fallback to /sdcard if permission or error occurs
        sio.emit('response_file_list', {'current_path': '/sdcard', 'files': []})

@sio.on('download_file')
def on_download(data):
    path = data.get('path')
    try:
        if os.path.isfile(path):
            with open(path, 'rb') as f:
                encoded_data = base64.b64encode(f.read()).decode('utf-8')
                filename = os.path.basename(path)
                sio.emit('response_download', {'file_data': encoded_data, 'filename': filename})
    except Exception as e:
        print("Error downloading file:", e)

@sio.on('execute_delete')
def on_delete(data):
    path = data.get('path')
    try:
        if os.path.isdir(path):
            os.rmdir(path)
        else:
            os.remove(path)
        parent_dir = os.path.dirname(path)
        on_fetch_files({'path': parent_dir})
    except Exception as e:
        print("Error deleting:", e)

if __name__ == '__main__':
    while True:
        try:
            sio.connect('https://phone-file-manager.onrender.com')
            sio.wait()
            break
        except Exception as e:
            print("Connection lost, retrying...", e)
            

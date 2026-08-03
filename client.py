import os
import time
import requests
import shutil
import base64

SERVER_URL = 'https://phone-file-manager.onrender.com'  # अपनी Render URL यहाँ डालें
current_path = '/sdcard'

def get_dir_contents(path):
    files_data = []
    if not path or not os.path.exists(path):
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
        print(f"Error reading path {path}: {e}")
    return files_data, path

print("=== PYDROID 3 SMART SYNC CLIENT STARTED ===")
print("Syncing with Cloud Server. Keep this app open in background...")

while True:
    try:
        files, current_path = get_dir_contents(current_path)
        payload = {
            "current_path": current_path,
            "files": files
        }
        
        response = requests.post(f"{SERVER_URL}/api/phone_sync", json=payload, timeout=10)
        if response.status_code == 200:
            res_data = response.json()
            cmd = res_data.get("pending_cmd")
            if cmd:
                action = cmd.get("action")
                target_path = cmd.get("path")
                if action == "delete":
                    if os.path.isfile(target_path):
                        os.remove(target_path)
                    elif os.path.isdir(target_path):
                        shutil.rmtree(target_path)
                    print(f"Executed delete on: {target_path}")
                elif action == "upload":
                    folder = cmd.get("path")
                    fname = cmd.get("filename")
                    b64_data = cmd.get("file_data")
                    save_path = os.path.join(folder, fname)
                    with open(save_path, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    print(f"Saved uploaded file to: {save_path}")
        print(".", end="", flush=True)
    except Exception as e:
        print(f"\n[Sync Retry] Waiting for connection... ({e})")
    
    time.sleep(3)
                    

import os
import json
import base64
import time
import shutil
import zipfile
from simple_websocket import client

SERVER_WS_URL = 'wss://phone-file-manager.onrender.com/ws'  # अपनी Render URL यहाँ डालें

def run_client():
    print("Connecting to Cloud Server...")
    try:
        ws = client.connect(SERVER_WS_URL)
        print("Connected! Multi-select & Batch download ready.")
        
        while ws.connected:
            raw_data = ws.receive()
            if not raw_data: break
            
            data = json.loads(raw_data)
            action = data.get('action')
            
            if action == 'request_file_list':
                req_path = data.get('path', '/sdcard')
                files_data = []
                if not os.path.exists(req_path): req_path = '/sdcard'
                
                try:
                    for item in os.listdir(req_path):
                        if item.startswith('.'): continue
                        full_path = os.path.join(req_path, item)
                        is_dir = os.path.isdir(full_path)
                        size = 0
                        if not is_dir:
                            try: size = os.path.getsize(full_path)
                            except: size = 0
                        files_data.append({
                            'name': item,
                            'path': full_path,
                            'is_dir': is_dir,
                            'size': size
                        })
                    
                    resp = {
                        "type": "file_list",
                        "data": {"current_path": req_path, "files": files_data}
                    }
                    ws.send(json.dumps(resp))
                except Exception as e:
                    resp = {
                        "type": "file_list",
                        "data": {"error": str(e), "current_path": req_path}
                    }
                    ws.send(json.dumps(resp))
            
            elif action == 'delete':
                target_path = data.get('path')
                try:
                    if os.path.isfile(target_path):
                        os.remove(target_path)
                    elif os.path.isdir(target_path):
                        shutil.rmtree(target_path)
                    print(f"Deleted: {target_path}")
                except Exception as e:
                    print(f"Delete error: {e}")

            elif action == 'batch_delete':
                paths = data.get('paths', [])
                for target_path in paths:
                    try:
                        if os.path.isfile(target_path):
                            os.remove(target_path)
                        elif os.path.isdir(target_path):
                            shutil.rmtree(target_path)
                        print(f"Batch Deleted: {target_path}")
                    except Exception as e:
                        print(f"Batch Delete error for {target_path}: {e}")
            
            elif action == 'download':
                target_path = data.get('path')
                try:
                    if os.path.isdir(target_path):
                        # अगर फोल्डर है तो उसे ज़िप बनाकर भेजें
                        zip_filename = target_path.strip('/').replace('/', '_') + '.zip'
                        zip_path = os.path.join('/sdcard', zip_filename)
                        shutil.make_archive(zip_path[:-4], 'zip', target_path)
                        with open(zip_path, 'rb') as f:
                            b64_data = base64.b64encode(f.read()).decode('utf-8')
                        os.remove(zip_path)
                        resp = {
                            "type": "download_resp",
                            "filename": zip_filename,
                            "file_data": b64_data
                        }
                    else:
                        with open(target_path, 'rb') as f:
                            b64_data = base64.b64encode(f.read()).decode('utf-8')
                        resp = {
                            "type": "download_resp",
                            "filename": os.path.basename(target_path),
                            "file_data": b64_data
                        }
                    ws.send(json.dumps(resp))
                    print(f"Sent download: {target_path}")
                except Exception as e:
                    print(f"Download error: {e}")

            elif action == 'batch_download':
                paths = data.get('paths', [])
                try:
                    zip_filename = "selected_phone_data.zip"
                    zip_path = os.path.join('/sdcard', zip_filename)
                    
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for p in paths:
                            if os.path.isfile(p):
                                zipf.write(p, arcname=os.path.basename(p))
                            elif os.path.isdir(p):
                                for root, dirs, files in os.walk(p):
                                    for file in files:
                                        full_p = os.path.join(root, file)
                                        rel_p = os.path.relpath(full_p, os.path.dirname(p))
                                        zipf.write(full_p, arcname=rel_p)
                    
                    with open(zip_path, 'rb') as f:
                        b64_data = base64.b64encode(f.read()).decode('utf-8')
                    os.remove(zip_path)
                    
                    resp = {
                        "type": "batch_download_resp",
                        "filename": zip_filename,
                        "file_data": b64_data
                    }
                    ws.send(json.dumps(resp))
                    print("Batch zip created and sent successfully!")
                except Exception as e:
                    print(f"Batch download error: {e}")

    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == '__main__':
    while True:
        try: run_client()
        except: pass
        print("Reconnecting in 3 seconds...")
        time.sleep(3)
                        

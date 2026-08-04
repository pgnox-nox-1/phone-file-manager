import os
import urllib.parse
import mimetypes
import shutil
from flask import Flask, render_template_string, request, send_file, redirect, url_for

app = Flask(__name__)

# यदि Render पर चलेगा तो क्लाउड पाथ या करंट फोल्डर लेगा, फोन पर चलने पर /sdcard या /storage/emulated/0 लेगा
DEFAULT_STORAGE = '/storage/emulated/0' if os.path.exists('/storage/emulated/0') else os.getcwd()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ultimate Mobile Data Control Hub</title>
    <style>
        :root {
            --bg: #07090e;
            --card: #121824;
            --accent: #38bdf8;
            --text: #f8fafc;
            --muted: #94a3b8;
            --danger: #ef4444;
            --success: #10b981;
            --border: #1e293b;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 12px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        .hub-card {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.4);
        }
        .title {
            color: var(--accent);
            font-size: 1.3rem;
            font-weight: 700;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .status-box {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #07090e;
            padding: 10px 14px;
            border-radius: 10px;
            border: 1px solid var(--border);
            margin-bottom: 12px;
        }
        .badge-online {
            background: var(--success);
            color: white;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.78rem;
            font-weight: bold;
        }
        .btn {
            background: var(--accent);
            color: #07090e;
            border: none;
            padding: 8px 14px;
            border-radius: 8px;
            font-weight: bold;
            font-size: 0.85rem;
            cursor: pointer;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-danger { background: var(--danger); color: white; }
        .path-display {
            background: #07090e;
            color: var(--accent);
            font-family: monospace;
            padding: 10px;
            border-radius: 8px;
            font-size: 0.85rem;
            border: 1px solid var(--border);
            margin-bottom: 12px;
            word-break: break-all;
        }
        .file-row {
            background: #07090e;
            padding: 10px 12px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid var(--border);
            margin-bottom: 6px;
        }
        .file-info { display: flex; align-items: center; gap: 10px; overflow: hidden; flex: 1; }
        .file-name {
            color: var(--text);
            text-decoration: none;
            font-size: 0.9rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: block;
        }
        .file-name:hover { color: var(--accent); }
        .meta { font-size: 0.75rem; color: var(--muted); }
        .quick-chips {
            display: flex;
            gap: 6px;
            overflow-x: auto;
            padding-bottom: 6px;
            margin-bottom: 12px;
        }
        .chip {
            background: #07090e;
            border: 1px solid var(--border);
            color: var(--text);
            padding: 6px 14px;
            border-radius: 15px;
            font-size: 0.8rem;
            text-decoration: none;
            white-space: nowrap;
        }
        .chip:hover { background: var(--accent); color: #07090e; }
        .upload-section {
            border: 2px dashed var(--border);
            padding: 12px;
            border-radius: 10px;
            background: #07090e;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="hub-card">
            <div class="title">⚡ Ultimate Mobile Data Control Hub</div>
            <div class="status-box">
                <div>
                    <span style="font-size:0.85rem; color:var(--muted);">Server Status:</span><br>
                    <span class="badge-online">🟢 Active & Connected</span>
                </div>
                <a class="btn" href="/?path={{ current_path }}">🔄 Refresh Data</a>
            </div>

            <div style="font-size:0.85rem; color:var(--muted); margin-bottom:6px;">Current Directory:</div>
            <div class="path-display">{{ current_path }}</div>

            <div class="quick-chips">
                <a class="chip" href="/?path={{ root_path }}">🏠 Root Storage</a>
                <a class="chip" href="/?path={{ root_path }}/Download">📥 Download</a>
                <a class="chip" href="/?path={{ root_path }}/DCIM">🖼️ DCIM</a>
                <a class="chip" href="/?path={{ root_path }}/Pictures">🌅 Pictures</a>
                <a class="chip" href="/?path={{ root_path }}/Movies">🎬 Movies</a>
            </div>

            <div class="upload-section">
                <form action="/upload" method="POST" enctype="multipart/form-data" style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
                    <input type="hidden" name="path" value="{{ current_path }}">
                    <input type="file" name="file" style="color:var(--muted); font-size:0.85rem;" required>
                    <button type="submit" class="btn">📤 Upload File Now</button>
                </form>
            </div>
        </div>

        <div class="hub-card">
            <div class="title">📂 Storage Files & Folders</div>

            {% if current_path != root_path and current_path != '/' %}
            <div class="file-row">
                <div class="file-info">
                    <span>📁</span>
                    <div>
                        <a class="file-name" href="/?path={{ parent_path }}">.. (Parent Folder)</a>
                        <div class="meta">Go Back</div>
                    </div>
                </div>
            </div>
            {% endif %}

            {% for item in items %}
            <div class="file-row">
                <div class="file-info">
                    <span>{{ '📁' if item.is_dir else '📄' }}</span>
                    <div>
                        {% if item.is_dir %}
                        <a class="file-name" href="/?path={{ item.full_path }}">{{ item.name }}</a>
                        <div class="meta">Folder</div>
                        {% else %}
                        <a class="file-name" href="/view?path={{ item.full_path }}" target="_blank">{{ item.name }}</a>
                        <div class="meta">{{ item.size }} MB</div>
                        {% endif %}
                    </div>
                </div>
                <div style="display:flex; gap:6px;">
                    {% if not item.is_dir %}
                    <a class="btn" style="padding:4px 8px; font-size:0.75rem;" href="/view?path={{ item.full_path }}" target="_blank">View/Get</a>
                    {% endif %}
                    <a class="btn btn-danger" style="padding:4px 8px; font-size:0.75rem;" href="/delete?target={{ item.full_path }}&current={{ current_path }}" onclick="return confirm('Delete {{ item.name }}?');">Delete</a>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    root_path = DEFAULT_STORAGE
    current_path = request.args.get('path', root_path)
    
    if not os.path.exists(current_path) or not os.path.isdir(current_path):
        current_path = root_path

    parent_path = os.path.dirname(current_path)
    
    items = []
    try:
        for entry in sorted(os.listdir(current_path)):
            if entry.startswith('.'):
                continue
            full_path = os.path.join(current_path, entry)
            is_dir = os.path.isdir(full_path)
            size_mb = 0
            if not is_dir:
                try:
                    size_mb = round(os.path.getsize(full_path) / (1024 * 1024), 2)
                except:
                    size_mb = 0
            items.append({
                'name': entry,
                'full_path': full_path,
                'is_dir': is_dir,
                'size': size_mb
            })
    except Exception as e:
        print(f"Error reading directory: {e}")

    return render_template_string(HTML_TEMPLATE, 
                                  current_path=current_path, 
                                  root_path=root_path, 
                                  parent_path=parent_path, 
                                  items=items)

@app.route('/view')
def view_file():
    file_path = request.args.get('path', '')
    if file_path and os.path.exists(file_path) and os.path.isfile(file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        return send_file(file_path, mimetype=mime_type or 'application/octet-stream', as_attachment=False)
    return "File not found", 404

@app.route('/delete')
def delete_item():
    target = request.args.get('target', '')
    current = request.args.get('current', DEFAULT_STORAGE)
    if target and os.path.exists(target):
        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            else:
                os.remove(target)
        except Exception as e:
            print(f"Delete failed: {e}")
    return redirect(url_for('index', path=current))

@app.route('/upload', methods=['POST'])
def upload_file():
    target_path = request.form.get('path', DEFAULT_STORAGE)
    uploaded_file = request.files.get('file')
    if uploaded_file and uploaded_file.filename:
        save_path = os.path.join(target_path, uploaded_file.filename)
        try:
            uploaded_file.save(save_path)
        except Exception as e:
            print(f"Upload failed: {e}")
    return redirect(url_for('index', path=target_path))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

import os
import time
import glob
import threading
import sys
from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp

# 1. অ্যাপ স্টার্ট হওয়ার লগ (লগ প্যানেলে দেখার জন্য)
print("--> Application is starting...", flush=True)

# 2. টেমপ্লেট ফোল্ডার ফিক্স (যাতে index.html খুঁজে পায়)
app = Flask(__name__, template_folder='.')

# ফোল্ডার কনফিগারেশন
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
    print(f"--> Created folder: {DOWNLOAD_FOLDER}", flush=True)

# অটোমেটিক ফাইল ডিলেট করার ফাংশন (৭ মিনিট পর)
def cleanup_old_files():
    print("--> Cleanup thread started", flush=True)
    while True:
        try:
            now = time.time()
            cutoff = now - 420 # ৭ মিনিট
            files = glob.glob(os.path.join(DOWNLOAD_FOLDER, "*"))
            for f in files:
                if os.stat(f).st_mtime < cutoff:
                    os.remove(f)
                    print(f"Deleted old file: {f}", flush=True)
        except Exception as e:
            print(f"Error in cleanup: {e}", flush=True)
        time.sleep(60)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    return render_template('index.html') 

@app.route('/get-info', methods=['POST'])
def get_info():
    url = request.json.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400

    try:
        ydl_opts = {
            'quiet': True, 
            'no_warnings': True,
            'extractor_args': {'facebook': {'skip_groups': False}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen_resolutions = set()
            
            for f in info.get('formats', []):
                if f.get('ext') == 'mp4' and f.get('height'):
                    resolution = f"{f.get('height')}p"
                    if resolution not in seen_resolutions:
                        formats.append({
                            'format_id': f['format_id'],
                            'resolution': resolution,
                            'ext': f['ext'],
                            'filesize': f.get('filesize', 0)
                        })
                        seen_resolutions.add(resolution)
            
            formats.sort(key=lambda x: int(x['resolution'].replace('p', '')), reverse=True)

            return jsonify({
                'title': info.get('title', 'Video'),
                'thumbnail': info.get('thumbnail'),
                'formats': formats
            })
    except Exception as e:
        error_msg = str(e)
        print(f"Error extracting info: {error_msg}", flush=True)
        return jsonify({'error': "Failed to fetch video info"}), 500

@app.route('/process-download', methods=['POST'])
def process_download():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    
    filename_template = f"{DOWNLOAD_FOLDER}/%(title)s_%(id)s.%(ext)s"

    ydl_opts = {
        'format': f"{format_id}+bestaudio/best",
        'outtmpl': filename_template,
        'merge_output_format': 'mp4',
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            base, _ = os.path.splitext(filename)
            final_filename = base + ".mp4"
            
            if not os.path.exists(final_filename) and os.path.exists(filename):
                final_filename = filename

            return jsonify({'status': 'ready', 'filename': os.path.basename(final_filename)})
    except Exception as e:
        print(f"Error downloading: {e}", flush=True)
        return jsonify({'error': "Download failed"}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found or expired", 404

# লোকাল টেস্টিং এবং প্রোডাকশন কনফিগারেশন
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"--> Starting Flask Server on port {port}", flush=True)
    app.run(host='0.0.0.0', port=port)



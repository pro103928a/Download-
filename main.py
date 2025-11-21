from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import time
import glob
import threading

app = Flask(__name__)

# ফোল্ডার কনফিগারেশন
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# অটোমেটিক ফাইল ডিলেট করার ফাংশন (৭ মিনিট পর)
def cleanup_old_files():
    while True:
        now = time.time()
        # ৭ মিনিট = ৪২০ সেকেন্ড
        cutoff = now - 420 
        files = glob.glob(os.path.join(DOWNLOAD_FOLDER, "*"))
        for f in files:
            try:
                if os.stat(f).st_mtime < cutoff:
                    os.remove(f)
                    print(f"Deleted old file: {f}")
            except Exception as e:
                print(f"Error deleting file: {e}")
        time.sleep(60)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/')
def index():
    # মনে রাখবেন: আপনার অবশ্যই templates ফোল্ডারে index.html থাকতে হবে
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
                    # ডুপ্লিকেট রেজোলিউশন বাদ দেওয়া এবং খুব ছোট সাইজ বাদ দেওয়া
                    if resolution not in seen_resolutions:
                        formats.append({
                            'format_id': f['format_id'],
                            'resolution': resolution,
                            'ext': f['ext'],
                            'filesize': f.get('filesize', 0)
                        })
                        seen_resolutions.add(resolution)
            
            # রেজোলিউশন অনুযায়ী সর্ট করা (বড় থেকে ছোট)
            formats.sort(key=lambda x: int(x['resolution'].replace('p', '')), reverse=True)

            return jsonify({
                'title': info.get('title', 'Video'),
                'thumbnail': info.get('thumbnail'),
                'formats': formats
            })
    except Exception as e:
        error_msg = str(e)
        
        if 'Cannot parse data' in error_msg or 'private' in error_msg.lower():
            error_msg = 'Private video or private group video download not allowed'
        elif 'Video unavailable' in error_msg:
            error_msg = 'Video is unavailable or private'
        
        print(f"Error extracting info: {error_msg}")
        return jsonify({'error': error_msg}), 500

@app.route('/process-download', methods=['POST'])
def process_download():
    data = request.json
    url = data.get('url')
    format_id = data.get('format_id')
    
    # ফাইলের নাম ক্লিন করা
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
        error_msg = str(e)
        
        if 'Cannot parse data' in error_msg or 'private' in error_msg.lower():
            error_msg = 'Private video or private group video download not allowed'
        
        print(f"Error downloading: {error_msg}")
        return jsonify({'error': error_msg}), 500

@app.route('/download/<path:filename>')
def download_file(filename):
    file_path = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found or expired", 404

if __name__ == '__main__':
    # হোস্টিংয়ের জন্য পোর্ট এনভায়রনমেন্ট ভেরিয়েবল থেকে নেওয়া হচ্ছে
    port = int(os.environ.get("PORT", 5000)) # 5000 default if logic fails
    app.run(host='0.0.0.0', port=port, debug=True)

      

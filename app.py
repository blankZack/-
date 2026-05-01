from flask import Flask, render_template, request, jsonify, send_from_directory
import cv2
import os
import shutil
import subprocess
import socket

# 修复 Windows 中文环境下的编码问题
_original_getfqdn = socket.getfqdn
def _safe_getfqdn(name=''):
    try:
        return _original_getfqdn(name)
    except UnicodeDecodeError:
        return name or 'localhost'
socket.getfqdn = _safe_getfqdn

app = Flask(__name__)
UPLOAD_DIR = "mov"
OUTPUT_BASE = "pic"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_BASE, exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("video")
    if not f:
        return jsonify(error="未选择文件"), 400
    path = os.path.join(UPLOAD_DIR, f.filename)
    f.save(path)
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return jsonify(error="无法读取视频"), 400
    info = {
        "filename": f.filename,
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    info["duration"] = round(info["total_frames"] / info["fps"], 2) if info["fps"] else 0
    cap.release()
    return jsonify(info)


@app.route("/preview_frame", methods=["POST"])
def preview_frame():
    data = request.json
    path = os.path.join(UPLOAD_DIR, data["filename"])
    cap = cv2.VideoCapture(path)
    frame_no = int(data.get("frame", 0))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return jsonify(error="无法读取该帧"), 400
    preview_dir = os.path.join(OUTPUT_BASE, "_preview")
    os.makedirs(preview_dir, exist_ok=True)
    out_path = os.path.join(preview_dir, "preview.jpg")
    cv2.imwrite(out_path, frame)
    return jsonify(url="/output/_preview/preview.jpg")


@app.route("/extract", methods=["POST"])
def extract():
    data = request.json
    filename = data["filename"]
    path = os.path.join(UPLOAD_DIR, filename)
    fmt = data.get("format", "png")
    quality = int(data.get("quality", 95))
    interval = int(data.get("interval", 1))
    start_frame = int(data.get("start_frame", 0))
    end_frame = int(data.get("end_frame", -1))

    name_no_ext = os.path.splitext(filename)[0]
    out_dir = os.path.join(OUTPUT_BASE, name_no_ext + "_frames")
    if os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir)

    cap = cv2.VideoCapture(path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if end_frame < 0 or end_frame > total:
        end_frame = total

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    saved = 0
    idx = start_frame
    while idx < end_frame:
        ret, frame = cap.read()
        if not ret:
            break
        if (idx - start_frame) % interval == 0:
            ext = "jpg" if fmt == "jpg" else "png"
            fname = os.path.join(out_dir, f"frame_{idx:06d}.{ext}")
            if fmt == "jpg":
                cv2.imwrite(fname, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            else:
                cv2.imwrite(fname, frame)
            saved += 1
        idx += 1
    cap.release()
    return jsonify(saved=saved, output_dir=out_dir)


@app.route("/output/<path:filepath>")
def serve_output(filepath):
    return send_from_directory(OUTPUT_BASE, filepath)


CLIP_DIR = os.path.join(OUTPUT_BASE, "clips")
os.makedirs(CLIP_DIR, exist_ok=True)


@app.route("/clip", methods=["POST"])
def clip():
    data = request.json
    filename = data.get("filename")
    start = data.get("start", "00:00:00")  # HH:MM:SS or MM:SS
    end = data.get("end", "00:00:10")

    src = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(src):
        return jsonify(error="视频文件不存在"), 400

    name_no_ext = os.path.splitext(filename)[0]
    out_name = f"{name_no_ext}_{start.replace(':', '')}_{end.replace(':', '')}.mp4"
    out_path = os.path.join(CLIP_DIR, out_name)

    cmd = [
        "ffmpeg", "-y",
        "-i", src,
        "-ss", start,
        "-to", end,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-movflags", "+faststart",
        out_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return jsonify(error=result.stderr[-500:] if result.stderr else "ffmpeg 执行失败"), 500
    except subprocess.TimeoutExpired:
        return jsonify(error="剪辑超时"), 500

    return jsonify(
        output=out_name,
        download_url=f"/output/clips/{out_name}"
    )


if __name__ == '__main__':
    app.run(host='127.0.0.1', debug=False)
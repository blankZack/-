import cv2
import os

video_path = "mov/1.mp4"
output_dir = "pic/frames"

os.makedirs(output_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
if not cap.isOpened():
    print(f"无法打开视频: {video_path}")
    exit(1)

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    filename = os.path.join(output_dir, f"frame_{frame_idx:06d}.png")
    cv2.imwrite(filename, frame)
    frame_idx += 1

cap.release()
print(f"完成，共提取 {frame_idx} 帧到 {output_dir}")

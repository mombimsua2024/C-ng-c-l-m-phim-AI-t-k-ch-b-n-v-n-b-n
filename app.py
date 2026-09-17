import streamlit as st
import asyncio
import edge_tts
import requests
import json
import os
import time
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips

st.set_page_config(page_title="AI Movie Generator", page_icon="🎬", layout="wide")

st.title("🎬 Trang Web Làm Phim AI Từ Văn Bản")
st.caption("Chuyển đổi ý tưởng/kịch bản thành phim hoàn chỉnh với giọng đọc và video AI.")

st.sidebar.header("🔑 Cấu hình API Keys")
replicate_api_key = st.sidebar.text_input("Replicate API Key (để tạo Video)", type="password")

VOICE_OPTIONS = {
    "Nữ - Hoài My": "vi-VN-HoaiMyNeural",
    "Nam - Nam Minh": "vi-VN-NamMinhNeural"
}
selected_voice = st.sidebar.selectbox("🎙️ Chọn giọng lồng tiếng:", list(VOICE_OPTIONS.keys()))

async def generate_audio_async(text, output_file, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def generate_audio(text, output_file, voice):
    asyncio.run(generate_audio_async(text, output_file, voice))

def generate_video_from_prompt(prompt, api_key):
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    url = "https://api.replicate.com/v1/predictions"
    payload = {
        "version": "50a2940e4f62e84d43e26b15e21950a31eb2e5d9967eef277e3aa00ef58cb443",
        "input": {
            "prompt": prompt,
            "num_frames": 49,
            "guidance_scale": 6
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 201:
        st.error(f"Lỗi khởi tạo video: {response.text}")
        return None
    
    prediction_id = response.json()["id"]
    get_url = f"https://api.replicate.com/v1/predictions/{prediction_id}"
    
    with st.spinner("Đang khởi tạo khung hình AI (có thể mất 1-2 phút)..."):
        while True:
            res = requests.get(get_url, headers=headers).json()
            status = res.get("status")
            if status == "succeeded":
                return res["output"][0]
            elif status == "failed":
                st.error("Tạo video thất bại.")
                return None
            time.sleep(5)

user_script = st.text_area(
    "📝 Nhập ý tưởng hoặc kịch bản phim của bạn:",
    height=150,
    placeholder="Ví dụ: Một chú rô-bốt nhỏ đi lang thang trong thành phố tương lai rực rỡ đèn neon dưới mưa."
)

col1, col2 = st.columns(2)
with col1:
    style = st.selectbox("🎨 Phong cách phim:", ["Cinematic, 8k, Photorealistic", "Anime style, Ghibli", "Cyberpunk, Sci-Fi", "3D Pixar Animation"])
with col2:
    num_scenes = st.slider("🎞️ Số lượng cảnh phim:", min_value=1, max_value=5, value=2)

if st.button("🚀 Bắt đầu làm phim AI", type="primary"):
    if not replicate_api_key:
        st.warning("Vui lòng nhập Replicate API Key ở thanh bên để tiếp tục!")
        st.stop()
    if not user_script:
        st.warning("Vui lòng nhập nội dung kịch bản!")
        st.stop()

    os.makedirs("temp", exist_ok=True)
    st.info("🔄 Bước 1: Đang phân tích kịch bản và chia phân cảnh...")
    
    sentences = [s.strip() for s in user_script.split(".") if len(s.strip()) > 5][:num_scenes]
    if not sentences:
        sentences = [user_script]

    clips = []
    for idx, sentence in enumerate(sentences):
        st.subheader(f"🎬 Cảnh {idx+1}: {sentence}")
        
        audio_path = f"temp/audio_{idx}.mp3"
        voice_code = VOICE_OPTIONS[selected_voice]
        generate_audio(sentence, audio_path, voice_code)
        
        video_prompt = f"{sentence}, {style}, highly detailed, smooth motion, masterpiece"
        video_url = generate_video_from_prompt(video_prompt, replicate_api_key)
        
        if video_url:
            video_data = requests.get(video_url).content
            video_path = f"temp/video_{idx}.mp4"
            with open(video_path, "wb") as f:
                f.write(video_data)
                
            video_clip = VideoFileClip(video_path)
            audio_clip = AudioFileClip(audio_path)
            
            if video_clip.duration < audio_clip.duration:
                video_clip = video_clip.loop(duration=audio_clip.duration)
            else:
                video_clip = video_clip.subclip(0, audio_clip.duration)
                
            final_clip = video_clip.set_audio(audio_clip)
            final_clip_path = f"temp/final_{idx}.mp4"
            final_clip.write_videofile(final_clip_path, codec="libx264", audio_codec="aac")
            
            clips.append(VideoFileClip(final_clip_path))
            st.video(final_clip_path)

    if clips:
        st.info("🍿 Bước 2: Đang ghép các phân cảnh thành phim hoàn chỉnh...")
        final_movie = concatenate_videoclips(clips)
        output_movie_path = "final_movie.mp4"
        final_movie.write_videofile(output_movie_path, codec="libx264", audio_codec="aac")
        
        st.balloons()
        st.success("🎉 Bộ phim AI của bạn đã hoàn thành!")
        st.video(output_movie_path)
  

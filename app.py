import streamlit as st
import whisper
import os
import tempfile
import zipfile
from googletrans import Translator
import subprocess
import threading
import time

st.set_page_config(
    page_title="YouTube Arabic Transcriber", 
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 YouTube Arabic Transcriber & Translator")
st.markdown("Upload YouTube URLs to get Arabic transcripts and English translations")

# Initialize session state
if 'processed_videos' not in st.session_state:
    st.session_state.processed_videos = []
if 'processing' not in st.session_state:
    st.session_state.processing = False

@st.cache_resource
def load_whisper_model():
    """Load Whisper model (cached for performance)"""
    return whisper.load_model("large")

@st.cache_resource
def load_translator():
    """Load Google Translator (cached for performance)"""
    return Translator()

def download_video(url, output_path):
    """Download video using yt-dlp"""
    try:
        cmd = ["yt-dlp", url, "-o", f"{output_path}.%(ext)s"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Find the downloaded file
        files = [f for f in os.listdir(os.path.dirname(output_path)) 
                if f.startswith(os.path.basename(output_path))]
        
        if files:
            return os.path.join(os.path.dirname(output_path), files[0])
        return None
    except Exception as e:
        st.error(f"Download failed: {str(e)}")
        return None

def process_video(url, video_index, model, translator, progress_bar, status_text):
    """Process a single video"""
    try:
        status_text.text(f"Downloading video {video_index}...")
        progress_bar.progress(0.1)
        
        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, f"video_{video_index}")
            downloaded_file = download_video(url, video_path)
            
            if not downloaded_file:
                return None
            
            status_text.text(f"Transcribing video {video_index}...")
            progress_bar.progress(0.4)
            
            # Transcribe
            result = model.transcribe(downloaded_file, language="ar")
            arabic_text = result["text"]
            
            status_text.text(f"Translating video {video_index}...")
            progress_bar.progress(0.7)
            
            # Translate
            try:
                translation = translator.translate(arabic_text, src='ar', dest='en')
                english_text = translation.text
            except Exception as e:
                english_text = f"Translation failed: {str(e)}"
            
            progress_bar.progress(1.0)
            status_text.text(f"Completed video {video_index}!")
            
            return {
                'url': url,
                'arabic': arabic_text,
                'english': english_text,
                'index': video_index
            }
            
    except Exception as e:
        st.error(f"Error processing video {video_index}: {str(e)}")
        return None

# Sidebar for URLs
st.sidebar.header("📋 YouTube URLs")
url_input = st.sidebar.text_area(
    "Enter YouTube URLs (one per line):",
    height=200,
    placeholder="https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=..."
)

# Process button
if st.sidebar.button("🚀 Start Processing", disabled=st.session_state.processing):
    urls = [url.strip() for url in url_input.split('\n') if url.strip()]
    
    if not urls:
        st.sidebar.error("Please enter at least one YouTube URL")
    else:
        st.session_state.processing = True
        st.session_state.processed_videos = []
        
        # Load models
        with st.spinner("Loading AI models..."):
            model = load_whisper_model()
            translator = load_translator()
        
        # Process each video
        for i, url in enumerate(urls, 1):
            st.write(f"### Processing Video {i}/{len(urls)}")
            st.write(f"**URL:** {url}")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            result = process_video(url, i, model, translator, progress_bar, status_text)
            
            if result:
                st.session_state.processed_videos.append(result)
                st.success(f"✅ Video {i} completed!")
            else:
                st.error(f"❌ Video {i} failed!")
        
        st.session_state.processing = False
        st.success("🎉 All videos processed!")

# Display results
if st.session_state.processed_videos:
    st.header("📄 Results")
    
    # Create tabs for each video
    if len(st.session_state.processed_videos) == 1:
        video = st.session_state.processed_videos[0]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🇸🇦 Arabic Transcript")
            st.text_area("", value=video['arabic'], height=300, key=f"arabic_{video['index']}")
        
        with col2:
            st.subheader("🇺🇸 English Translation")
            st.text_area("", value=video['english'], height=300, key=f"english_{video['index']}")
    
    else:
        tab_names = [f"Video {video['index']}" for video in st.session_state.processed_videos]
        tabs = st.tabs(tab_names)
        
        for tab, video in zip(tabs, st.session_state.processed_videos):
            with tab:
                st.write(f"**URL:** {video['url']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("🇸🇦 Arabic Transcript")
                    st.text_area("", value=video['arabic'], height=300, key=f"arabic_{video['index']}")
                
                with col2:
                    st.subheader("🇺🇸 English Translation")
                    st.text_area("", value=video['english'], height=300, key=f"english_{video['index']}")
    
    # Download all transcripts as ZIP
    if st.button("📥 Download All Transcripts"):
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_path = os.path.join(temp_dir, "transcripts.zip")
            
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for video in st.session_state.processed_videos:
                    # Arabic file
                    arabic_content = f"Video URL: {video['url']}\n\nARABIC TRANSCRIPT:\n{video['arabic']}"
                    zipf.writestr(f"transcript_arabic_{video['index']}.txt", arabic_content.encode('utf-8'))
                    
                    # English file
                    english_content = f"Video URL: {video['url']}\n\nENGLISH TRANSLATION:\n{video['english']}"
                    zipf.writestr(f"transcript_english_{video['index']}.txt", english_content.encode('utf-8'))
                    
                    # Combined file
                    combined_content = f"Video URL: {video['url']}\n\nARABIC TRANSCRIPT:\n{video['arabic']}\n\n{'='*50}\n\nENGLISH TRANSLATION:\n{video['english']}"
                    zipf.writestr(f"transcript_both_{video['index']}.txt", combined_content.encode('utf-8'))
            
            with open(zip_path, "rb") as f:
                st.download_button(
                    label="📁 Download ZIP file",
                    data=f.read(),
                    file_name="youtube_transcripts.zip",
                    mime="application/zip"
                )

# Footer
st.markdown("---")
st.markdown("Built with ❤️ using Streamlit, Whisper AI, and Google Translate")

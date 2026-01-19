import streamlit as st
import re
import random
import datetime
import requests
import statistics
import pandas as pd
from googleapiclient.discovery import build
import json
from collections import Counter

# --- 1. CONFIG & STYLE ---
st.set_page_config(page_title="VidIQ Clone Pro", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .main {background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 1rem;}
    .stButton>button {width: 100%; border-radius: 8px;}
    .metric-card {background: white; padding: 1rem; border-radius: 8px; color: black; box-shadow: 0 2px 5px rgba(0,0,0,0.1);}
    h1, h2, h3 {color: white !important;}
    .stMarkdown p {color: #e0e0e0;}
    .stDataFrame {background-color: white; border-radius: 10px; padding: 10px;}
</style>
""", unsafe_allow_html=True)

# --- 2. DATABASE & CONSTANTS ---
URL_DATABASE_ONLINE = "https://gist.githubusercontent.com/rhanierex/f2d76f11df8d550376d81b58124d3668/raw/0b58a1eb02a7cffc2261a1c8d353551f3337001c/gistfile1.txt"
FALLBACK_POWER_WORDS = ["secret", "best", "exposed", "tutorial", "guide", "ultimate", "proven", "hack", "tips", "crazy"]

@st.cache_data(ttl=600) 
def load_power_words(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json(), "🟢 Online DB"
    except: pass
    return FALLBACK_POWER_WORDS, "🟠 Offline DB"

POWER_WORDS_DB, db_status = load_power_words(URL_DATABASE_ONLINE)

# --- 3. API VALIDATION FUNCTIONS ---
def validate_gemini_connection(api_key):
    """Cek koneksi Gemini"""
    if not api_key: return False, "Kunci kosong"
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        model.generate_content("Hi", generation_config={'max_output_tokens': 1})
        return True, "✅ Terhubung"
    except Exception as e:
        return False, f"❌ Gagal: {str(e)[:30]}..."

def validate_youtube_connection(api_key):
    """Cek koneksi YouTube"""
    if not api_key: return False, "Kunci kosong"
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        youtube.search().list(part='id', q='test', maxResults=1).execute()
        return True, "✅ Terhubung"
    except Exception as e:
        if "quota" in str(e).lower(): return False, "❌ Kuota Habis"
        return False, f"❌ Gagal: {str(e)[:30]}..."

# --- 4. CORE LOGIC FUNCTIONS ---
@st.cache_data(ttl=3600)
def ask_gemini_ai(api_key, prompt_type, topic=""):
    """Fungsi AI Generatif"""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompts = {
            "daily_ideas": f"Give 3 viral YouTube video ideas for '{topic}'. Format: 1. [Title] - [Why]. Plain text.",
            "script": f"Write a YouTube script for '{topic}'. Include Hook, Intro, 3 Points, CTA.",
            "audit": f"Analyze channel niche '{topic}'. Give 3 tips for growth in 2026."
        }
        return model.generate_content(prompts.get(prompt_type, "")).text, "Success"
    except Exception as e: return None, str(e)

def analyze_title(title, keyword=""):
    """Logika Scoring Judul"""
    score = 0
    checks = []
    
    # 1. Length Check
    length = len(title)
    if 40 <= length <= 65: score += 30; checks.append("✅ Panjang Ideal")
    elif length < 30: score += 10; checks.append("❌ Terlalu Pendek")
    else: score += 15; checks.append("⚠️ Terlalu Panjang")
    
    # 2. Keyword Check
    if keyword and keyword.lower() in title.lower():
        score += 30
        checks.append("✅ Ada Keyword")
    elif keyword:
        checks.append("❌ Keyword Hilang")
    else:
        score += 20 # Bonus jika tidak ada target keyword spesifik
        
    # 3. Power Words
    has_power = any(pw in title.lower() for pw in POWER_WORDS_DB)
    if has_power: score += 20; checks.append("✅ Kata Power")
    else: checks.append("⚠️ Tambah Kata Power")
    
    # 4. Numbers & CTR Triggers
    if re.search(r'\d+', title): score += 10; checks.append("✅ Ada Angka")
    if '?' in title or '!' in title: score += 10; checks.append("✅ Tanda Baca Emosional")
    
    return min(score, 100), checks

def get_keyword_metrics(api_key, keyword):
    """Mengambil data pencarian YouTube"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        search = youtube.search().list(q=keyword, type='video', part='id,snippet', maxResults=20).execute()
        
        video_ids = [item['id']['videoId'] for item in search.get('items', [])]
        if not video_ids: return None, "Tidak ada video ditemukan"
        
        stats = youtube.videos().list(id=','.join(video_ids), part='statistics,snippet').execute()
        
        metrics = []
        for item in stats.get('items', []):
            st_data = item['statistics']
            metrics.append({
                'title': item['snippet']['title'],
                'views': int(st_data.get('viewCount', 0)),
                'likes': int(st_data.get('likeCount', 0)),
                'channel': item['snippet']['channelTitle']
            })
            
        df = pd.DataFrame(metrics)
        avg_views = df['views'].mean()
        
        # Simple Difficulty Logic
        difficulty = "High" if avg_views > 500000 else "Medium" if avg_views > 100000 else "Low"
        score = 30 if difficulty == "High" else 60 if difficulty == "Medium" else 90
        
        return {'score': score, 'difficulty': difficulty, 'avg_views': avg_views, 'top_videos': df}, None
    except Exception as e: return None, str(e)

def get_channel_audit(api_key, channel_id):
    """Audit Channel sederhana"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        res = youtube.channels().list(id=channel_id, part='snippet,statistics').execute()
        if not res.get('items'): return None, "Channel tidak ditemukan"
        
        item = res['items'][0]
        return {
            'title': item['snippet']['title'],
            'subs': int(item['statistics']['subscriberCount']),
            'views': int(item['statistics']['viewCount']),
            'videos': int(item['statistics']['videoCount']),
            'thumb': item['snippet']['thumbnails']['default']['url']
        }, None
    except Exception as e: return None, str(e)

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # 1. Gemini
    st.subheader("🤖 Gemini API")
    gemini_key = st.text_input("Gemini Key:", type="password")
    if gemini_key:
        is_valid_gemini, msg_gemini = validate_gemini_connection(gemini_key)
        st.caption(msg_gemini)
    else: st.warning("Belum Konek")

    # 2. YouTube
    st.subheader("📺 YouTube API")
    yt_key = st.text_input("YouTube Key:", type="password")
    if yt_key:
        is_valid_yt, msg_yt = validate_youtube_connection(yt_key)
        st.caption(msg_yt)
    else: st.warning("Belum Konek")
    
    st.divider()
    
    # Daily Ideas
    st.subheader("💡 Daily Ideas")
    idea_niche = st.text_input("Niche:", placeholder="e.g. Cooking")
    if st.button("Generate Ideas", disabled=not gemini_key):
        with st.spinner("Thinking..."):
            res, _ = ask_gemini_ai(gemini_key, "daily_ideas", idea_niche)
            st.info(res if res else "Error")

# --- 6. MAIN APP ---
st.title("🚀 VidIQ Clone Pro")

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Keyword Research", "✍️ Title & Bulk Analysis", "🏥 Channel Audit", "⚔️ Competitor Spy"])

# === TAB 1: KEYWORD RESEARCH ===
with tab1:
    col1, col2 = st.columns([3, 1])
    kw = col1.text_input("Keyword:", placeholder="Tutorial Python")
    if col2.button("Analyze Keyword") and yt_key:
        with st.spinner("Analyzing..."):
            data, err = get_keyword_metrics(yt_key, kw)
            if data:
                m1, m2, m3 = st.columns(3)
                m1.metric("Score", f"{data['score']}/100")
                m2.metric("Competition", data['difficulty'])
                m3.metric("Avg Views", f"{data['avg_views']:,.0f}")
                
                st.subheader("Top Competitors")
                st.dataframe(data['top_videos'][['title', 'views', 'channel']], use_container_width=True)
            else: st.error(err)

# === TAB 2: OPTIMIZATION & BULK ANALYZER ===
with tab2:
    mode = st.radio("Pilih Mode:", ["Single Title Optimizer", "📦 Bulk Title Analyzer"], horizontal=True)
    
    # --- SUB-FEATURE: SINGLE TITLE ---
    if mode == "Single Title Optimizer":
        st.subheader("Single Title Analysis")
        t_kw = st.text_input("Target Keyword:", key="s_kw")
        t_title = st.text_input("Video Title:", key="s_title")
        
        if t_title:
            score, checks = analyze_title(t_title, t_kw)
            st.progress(score/100, text=f"SEO Score: {score}/100")
            
            c1, c2 = st.columns(2)
            with c1:
                st.write("Analysis:")
                for c in checks: st.write(c)
            with c2:
                if st.button("Generate AI Script", disabled=not gemini_key):
                    s, _ = ask_gemini_ai(gemini_key, "script", t_title)
                    st.text_area("Script:", s, height=200)

    # --- SUB-FEATURE: BULK ANALYZER ---
    else:
        st.subheader("📦 Bulk Title Analyzer")
        st.markdown("Analisa puluhan judul sekaligus untuk memilih yang terbaik.")
        
        b_kw = st.text_input("Target Keyword (Optional):", key="b_kw")
        b_text = st.text_area("Paste Judul (Satu judul per baris):", height=150, placeholder="Cara Belajar Python\nTutorial Python untuk Pemula\nBelajar Coding Cepat")
        
        if st.button("⚡ Analyze All Titles"):
            if not b_text.strip():
                st.warning("Masukkan judul dulu!")
            else:
                titles_list = [t.strip() for t in b_text.split('\n') if t.strip()]
                results = []
                
                progress_bar = st.progress(0)
                for i, t in enumerate(titles_list):
                    score, checks = analyze_title(t, b_kw)
                    # Convert checks list to string
                    issues = ", ".join([c for c in checks if '❌' in c or '⚠️' in c])
                    good = ", ".join([c for c in checks if '✅' in c])
                    
                    results.append({
                        "Title": t,
                        "Score": score,
                        "Length": len(t),
                        "Good Points": good,
                        "Issues": issues
                    })
                    progress_bar.progress((i + 1) / len(titles_list))
                
                df_bulk = pd.DataFrame(results)
                
                # Menampilkan Dataframe dengan highlight
                st.markdown("### 📊 Hasil Analisa")
                
                # Highlight judul terbaik (Score > 70)
                def highlight_score(val):
                    color = '#d4edda' if val >= 80 else '#fff3cd' if val >= 50 else '#f8d7da'
                    return f'background-color: {color}; color: black'

                st.dataframe(
                    df_bulk.style.applymap(highlight_score, subset=['Score']),
                    use_container_width=True,
                    column_config={
                        "Score": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=100)
                    }
                )
                
                # Rekomendasi Juara
                best_title = df_bulk.loc[df_bulk['Score'].idxmax()]
                st.success(f"🏆 Judul Terbaik: **{best_title['Title']}** (Score: {best_title['Score']})")

# === TAB 3: CHANNEL AUDIT ===
with tab3:
    st.subheader("Channel Health Check")
    cid = st.text_input("Channel ID:", placeholder="UC...")
    if st.button("Audit") and yt_key:
        data, err = get_channel_audit(yt_key, cid)
        if data:
            c1, c2 = st.columns([1,3])
            c1.image(data['thumb'])
            c1.markdown(f"**{data['title']}**")
            
            m1, m2, m3 = c2.columns(3)
            m1.metric("Subs", f"{data['subs']:,}")
            m2.metric("Views", f"{data['views']:,}")
            m3.metric("Videos", data['videos'])
            
            if gemini_key:
                st.info(ask_gemini_ai(gemini_key, "audit", data['title'])[0])
        else: st.error(err)

# === TAB 4: COMPETITOR SPY ===
with tab4:
    st.subheader("Competitor Analysis")
    comp_kw = st.text_input("Competitor Topic:")
    if st.button("Spy Competitor") and yt_key:
        data, err = get_keyword_metrics(yt_key, comp_kw)
        if data:
            df = data['top_videos']
            st.bar_chart(df.set_index('title')['views'])
            st.dataframe(df)

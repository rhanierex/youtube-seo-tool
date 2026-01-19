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
import matplotlib.pyplot as plt

# --- 1. CONFIG ---
st.set_page_config(page_title="VidIQ Clone Pro", page_icon="🚀", layout="wide")

# --- 2. CUSTOM STYLING ---
st.markdown("""
<style>
    .main {background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 1rem;}
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .suggestion-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        transition: transform 0.2s;
    }
    .suggestion-box:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }
    .api-badge {
        display: inline-block;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. DATABASE CONFIG ---
URL_DATABASE_ONLINE = "https://gist.githubusercontent.com/rhanierex/f2d76f11df8d550376d81b58124d3668/raw/0b58a1eb02a7cffc2261a1c8d353551f3337001c/gistfile1.txt"
FALLBACK_POWER_WORDS = ["secret", "best", "exposed", "tutorial", "guide", "how to", "tips", "tricks", "hacks", "ultimate", "complete", "full", "master", "proven", "amazing", "incredible", "perfect", "easy", "simple", "advanced"]
VIRAL_EMOJIS = ["🔥", "😱", "🔴", "✅", "❌", "🎵", "⚠️", "⚡", "🚀", "💰", "💯", "🤯", "😭", "😡", "😴", "🌙", "✨", "💤", "🌧️", "🎹", "👀", "💪", "🎯", "⭐", "🏆"]
STOP_WORDS = {"the", "and", "or", "for", "to", "in", "on", "at", "by", "with", "a", "an", "is", "it", "of", "that", "this", "video", "i", "you", "me", "we", "my", "your"}

# --- 4. INTEGRASI API & DATA ---

@st.cache_data(ttl=3600)
def ask_gemini_ai(api_key, prompt_type, topic=""):
    """
    Fungsi AI Serbaguna untuk: Power Words, Daily Ideas, Scripts, dan Audit
    """
    if not api_key or len(api_key) < 30:
        return None, "Invalid API Key"
    
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompts = {
            "power_words": f"Generate 30 powerful, high-CTR words for YouTube video titles in the {topic} niche. Format: Return ONLY a JSON array of strings. No markdown.",
            "daily_ideas": f"Give me 3 viral YouTube video ideas for the '{topic}' niche. Format: 1. [Title] - [Brief Why]. Return plain text.",
            "script": f"Write a structured YouTube video script for the title: '{topic}'. Include: Hook (0-30s), Intro, Main Content (3 points), and CTA. Keep it concise.",
            "audit": f"Analyze this channel topic '{topic}'. Give 3 specific actionable tips to grow this specific niche on YouTube in 2026."
        }
        
        selected_prompt = prompts.get(prompt_type, "")
        response = model.generate_content(selected_prompt)
        text = response.text.strip()
        
        # Khusus untuk power words yang butuh format JSON
        if prompt_type == "power_words":
            text = text.replace('```json', '').replace('```', '').strip()
            import json
            return json.loads(text), "🟢 Gemini AI"
            
        return text, "🟢 Gemini AI"
            
    except Exception as e:
        return None, f"Error: {str(e)}"

@st.cache_data(ttl=600) 
def load_power_words(url):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0: 
                return data, "🟢 GitHub Online"
    except:
        pass
    return FALLBACK_POWER_WORDS, "🟠 Offline Fallback"

POWER_WORDS_DB, db_status = load_power_words(URL_DATABASE_ONLINE)

# --- 5. FUNGSI HELPER YOUTUBE ---

def get_channel_audit(api_key, channel_id):
    """Mengambil statistik channel untuk fitur Audit"""
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # 1. Get Channel Stats
        res = youtube.channels().list(
            id=channel_id,
            part='snippet,statistics,contentDetails'
        ).execute()
        
        if not res.get('items'):
            return None, "Channel not found"
            
        channel = res['items'][0]
        stats = channel['statistics']
        
        # 2. Get Last 10 Videos for Avg Calc
        uploads_playlist = channel['contentDetails']['relatedPlaylists']['uploads']
        videos_res = youtube.playlistItems().list(
            playlistId=uploads_playlist,
            part='snippet',
            maxResults=10
        ).execute()
        
        video_ids = [item['snippet']['resourceId']['videoId'] for item in videos_res['items']]
        if not video_ids:
             return {
                'title': channel['snippet']['title'],
                'subs': int(stats.get('subscriberCount', 0)),
                'total_views': int(stats.get('viewCount', 0)),
                'video_count': int(stats.get('videoCount', 0)),
                'avg_recent_views': 0,
                'thumb_url': channel['snippet']['thumbnails']['default']['url']
            }, None

        vid_stats_res = youtube.videos().list(
            id=','.join(video_ids),
            part='statistics'
        ).execute()
        
        recent_views = []
        for item in vid_stats_res['items']:
            recent_views.append(int(item['statistics'].get('viewCount', 0)))
            
        avg_views_recent = sum(recent_views) / len(recent_views) if recent_views else 0
        
        return {
            'title': channel['snippet']['title'],
            'subs': int(stats.get('subscriberCount', 0)),
            'total_views': int(stats.get('viewCount', 0)),
            'video_count': int(stats.get('videoCount', 0)),
            'avg_recent_views': int(avg_views_recent),
            'thumb_url': channel['snippet']['thumbnails']['default']['url']
        }, None
        
    except Exception as e:
        return None, str(e)

def calculate_engagement_rate(stats):
    try:
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        if views == 0: return 0
        engagement = ((likes + comments) / views) * 100
        return round(engagement, 2)
    except: return 0

def extract_core_theme(title, keyword):
    if not title: return ""
    if keyword:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        core = pattern.sub("", title).strip()
    else:
        core = title
    core = re.sub(r'\s+', ' ', core)
    core = re.sub(r'^[:\-\|,\.\s]+', '', core)
    core = re.sub(r'[:\-\|,\.\s]+$', '', core)
    return core.strip() if len(core) > 2 else "Guide"

def smart_truncate(text, max_length):
    if not text or len(text) <= max_length: return text
    truncated = text[:max_length-3]
    last_space = truncated.rfind(' ')
    if last_space > 0: truncated = truncated[:last_space]
    return truncated + "..."

def analyze_title(title, keyword=""):
    score = 0
    checks = []
    
    # Ambil power words dari session atau default
    if 'power_words' in st.session_state:
        power_words_list = st.session_state['power_words']
    else:
        power_words_list = POWER_WORDS_DB
    
    if not title: return 0, [("error", "Title is empty")]
    
    title_len = len(title)
    if 40 <= title_len <= 70:
        score += 25
        checks.append(("success", f"✅ Perfect Length ({title_len} chars)"))
    elif title_len < 30:
        score += 10
        checks.append(("error", f"❌ Too Short ({title_len} chars)"))
    else:
        score += 5
        checks.append(("error", f"❌ Too Long ({title_len} chars)"))
    
    if keyword:
        if keyword.lower() in title.lower():
            if title.lower().startswith(keyword.lower()):
                score += 20
                checks.append(("success", "✅ Keyword at Beginning"))
            else:
                score += 15
                checks.append(("success", "✅ Keyword Present"))
        else:
            checks.append(("error", "❌ Keyword Missing"))
    else:
        score += 20
    
    found_power = [pw for pw in power_words_list if pw.lower() in title.lower()]
    if found_power:
        score += 15
        checks.append(("success", f"✅ Power Words: {', '.join(found_power[:2])}"))
    else:
        checks.append(("warning", "⚠️ No Power Words"))
    
    if re.search(r'\d+', title):
        score += 15
        checks.append(("success", "✅ Numbers Included"))
    else:
        checks.append(("info", "💡 Add Numbers"))
        
    engagement_score = 0
    if '[' in title or '(' in title: engagement_score += 5
    if '?' in title: engagement_score += 5
    if str(datetime.datetime.now().year) in title: engagement_score += 5
    score += min(engagement_score, 15)
    
    if title.isupper():
        score -= 10
        checks.append(("error", "❌ Avoid ALL CAPS"))

    return min(score, 100), checks

def get_keyword_metrics(api_key, keyword):
    if not api_key or len(api_key) < 30: return None, "❌ Invalid API Key"
    if not keyword: return None, "❌ Keyword required"
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        search_res = youtube.search().list(
            q=keyword, type='video', part='id,snippet', maxResults=20, order='relevance', regionCode='ID'
        ).execute()
        
        if not search_res.get('items'): return None, f"❌ No videos found"
        
        video_ids = [item['id']['videoId'] for item in search_res['items'] if 'videoId' in item.get('id', {})]
        
        stats_res = youtube.videos().list(id=','.join(video_ids), part='statistics,snippet').execute()
        
        metrics = []
        all_tags = []
        
        for item in stats_res.get('items', []):
            snippet = item.get('snippet', {})
            stats = item.get('statistics', {})
            
            views = int(stats.get('viewCount', 0))
            engagement = calculate_engagement_rate(stats)
            tags = snippet.get('tags', [])
            all_tags.extend(tags)
            
            metrics.append({
                'title': snippet.get('title', ''),
                'Views': views,
                'Engagement': engagement,
                'Channel': snippet.get('channelTitle', 'Unknown'),
                'tags': tags
            })
        
        if not metrics: return None, "❌ No data available"
        
        view_counts = [m['Views'] for m in metrics]
        median_views = statistics.median(view_counts) if view_counts else 0
        avg_views = statistics.mean(view_counts) if view_counts else 0
        
        trending_tags = [tag for tag, _ in Counter(all_tags).most_common(15)]
        
        if median_views > 500000:
            difficulty = "🔴 High"
            score = 30
        elif median_views > 100000:
            difficulty = "🟡 Medium"
            score = 60
        else:
            difficulty = "🟢 Low"
            score = 90
            
        return {
            'median_views': median_views,
            'avg_views': avg_views,
            'score': score,
            'difficulty': difficulty,
            'trending_tags': trending_tags,
            'total_videos': len(metrics),
            'top_videos': pd.DataFrame(metrics)
        }, None
        
    except Exception as e:
        return None, f"❌ Error: {str(e)}"

def draw_competitor_chart(df):
    if df is None or df.empty: return
    
    st.markdown("### 📊 Top Videos")
    max_views = df['Views'].max() if df['Views'].max() > 0 else 1
    
    for idx, row in df.head(5).iterrows():
        title = row['title'][:50] + "..."
        width = int((row['Views'] / max_views) * 100)
        color = "#10b981" if row['Engagement'] > 5 else "#f59e0b"
        
        st.markdown(f"""
        <div style="background: #1e1e1e; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.5rem;">
            <div style="color: white; font-weight: bold; font-size: 13px;">{title}</div>
            <div style="color: #aaa; font-size: 11px;">{row['Channel']} • {row['Views']:,} views • {row['Engagement']}% eng</div>
            <div style="background: #333; width: 100%; height: 6px; border-radius: 3px; margin-top:5px;">
                <div style="background: {color}; width: {width}%; height: 6px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- 6. SIDEBAR & SETTINGS ---
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    if "Gemini" in st.session_state.get('db_source', ''):
        st.success(st.session_state.get('db_source', db_status))
    else:
        st.success(db_status)
    
    st.divider()
    
    # API KEYS
    gemini_key = st.text_input("Gemini API Key:", type="password", key="gemini_key")
    api_key = st.text_input("YouTube API Key:", type="password", key="yt_key")
    
    st.divider()
    
    # === DAILY IDEAS (Fitur #4) ===
    st.markdown("### 💡 Daily Ideas")
    niche_input = st.text_input("Your Niche:", placeholder="e.g. Coding")
    if st.button("Generate Ideas", use_container_width=True):
        if not gemini_key:
            st.warning("⚠️ Need Gemini API Key")
        else:
            with st.spinner("Thinking..."):
                ideas, status = ask_gemini_ai(gemini_key, "daily_ideas", niche_input)
                if ideas: st.info(ideas)
                else: st.error(status)
    
    st.divider()
    
    # POWER WORDS GENERATOR
    st.markdown("### 🧠 AI Power Words")
    pw_niche = st.text_input("Niche for words:", placeholder="General")
    if st.button("Update Power Words", use_container_width=True):
        if gemini_key:
            words, status = ask_gemini_ai(gemini_key, "power_words", pw_niche)
            if isinstance(words, list):
                st.session_state['power_words'] = words
                st.session_state['db_source'] = f"🤖 Gemini ({pw_niche})"
                st.success(f"Loaded {len(words)} words!")
                st.rerun()

# --- 7. MAIN APP ---
st.markdown("""
<div style='text-align: center; color: white; margin-bottom: 2rem;'>
    <h1 style='font-size: 3rem; font-weight: 800;'>🚀 VidIQ Clone Pro</h1>
    <p style='color: #ddd;'>All-in-One YouTube Growth Tool</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Keyword Research", "✍️ Optimization & AI", "🏥 Channel Audit", "⚔️ Competitor Analysis"])

# === TAB 1: KEYWORD RESEARCH (Fitur #1) ===
with tab1:
    st.markdown("### 🔍 Intelligent Keyword Research")
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        kw_input = st.text_input("Enter Topic:", placeholder="e.g., python tutorial", key="kw_search")
    with col_btn:
        st.write("")
        st.write("")
        analyze_btn = st.button("🚀 Research", type="primary", use_container_width=True)
    
    if analyze_btn and api_key:
        with st.spinner(f"Analyzing market for '{kw_input}'..."):
            data, err = get_keyword_metrics(api_key, kw_input)
            if data:
                c1, c2, c3 = st.columns(3)
                with c1: st.metric("Overall Score", f"{data['score']}/100")
                with c2: st.metric("Search Volume (Est)", f"{int(data['avg_views']):,}")
                with c3: st.metric("Competition", data['difficulty'])
                
                col_chart, col_tag = st.columns([2,1])
                with col_chart:
                    draw_competitor_chart(data['top_videos'])
                with col_tag:
                    st.markdown("#### Trending Tags")
                    st.write(", ".join(data['trending_tags'][:10]))

# === TAB 2: OPTIMIZATION & AI SCRIPT (Fitur #2 & #4) ===
with tab2:
    st.markdown("### 📝 Video Optimization")
    col_opt_1, col_opt_2 = st.columns([1, 1])
    
    with col_opt_1:
        st.subheader("1. Title Validator")
        target_kw = st.text_input("Target Keyword:", key="opt_kw")
        video_title = st.text_input("Video Title:", key="opt_title")
        
        if video_title:
            score, checks = analyze_title(video_title, target_kw)
            st.progress(score/100, text=f"SEO Score: {score}/100")
            for status, msg in checks:
                if status == 'success': st.success(msg)
                elif status == 'error': st.error(msg)
                else: st.warning(msg)

    with col_opt_2:
        st.subheader("2. 🤖 AI Script Generator")
        if st.button("Generate Script", type="primary"):
            if not gemini_key or not video_title:
                st.error("⚠️ Need Gemini Key & Title")
            else:
                with st.spinner("Writing script..."):
                    script_content, _ = ask_gemini_ai(gemini_key, "script", video_title)
                    st.text_area("Script:", value=script_content, height=300)

    st.markdown("---")
    st.subheader("✅ SEO Checklist")
    c1, c2, c3 = st.columns(3)
    with c1: st.checkbox("Keyword in Title (First 60 chars)")
    with c2: st.checkbox("Filename = keyword.mp4")
    with c3: st.checkbox("High Quality Thumbnail")

# === TAB 3: CHANNEL AUDIT (Fitur #5) ===
with tab3:
    st.markdown("### 🏥 Channel Health Audit")
    channel_id_input = st.text_input("Enter Channel ID:", placeholder="e.g. UC_x5XG...")
    
    if st.button("Audit Channel"):
        if not api_key: st.error("⚠️ YouTube API Key Required")
        else:
            with st.spinner("Auditing..."):
                ch_data, err = get_channel_audit(api_key, channel_id_input)
                if ch_data:
                    col_h1, col_h2 = st.columns([1, 4])
                    with col_h1: st.image(ch_data['thumb_url'], width=80)
                    with col_h2: st.title(ch_data['title'])
                    
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Subscribers", f"{ch_data['subs']:,}")
                    m2.metric("Total Views", f"{ch_data['total_views']:,}")
                    m3.metric("Videos", ch_data['video_count'])
                    m4.metric("Avg Views (Recent)", f"{ch_data['avg_recent_views']:,}")
                    
                    if gemini_key:
                        st.markdown("#### 🤖 AI Advice")
                        advice, _ = ask_gemini_ai(gemini_key, "audit", ch_data['title'])
                        st.info(advice)
                else: st.error(err)

# === TAB 4: COMPETITOR ANALYSIS (Fitur #3) ===
with tab4:
    st.markdown("### ⚔️ Competitor Intelligence")
    comp_kw = st.text_input("Competitor Topic:", placeholder="e.g. productivity hacks")
    
    if st.button("Analyze Competitors"):
        if not api_key: st.error("⚠️ API Key needed")
        else:
            with st.spinner("Spying..."):
                res, _ = get_keyword_metrics(api_key, comp_kw)
                if res and res.get('top_videos') is not None:
                    df = res['top_videos']
                    top_channel = df['Channel'].mode()[0] if not df.empty else "N/A"
                    st.success(f"🏆 Dominant Creator: **{top_channel}**")
                    
                    st.dataframe(
                        df[['title', 'Views', 'Engagement', 'Channel']].sort_values('Views', ascending=False),
                        column_config={
                            "Views": st.column_config.NumberColumn(format="%d"),
                            "Engagement": st.column_config.ProgressColumn(format="%.2f%%", min_value=0, max_value=10),
                        },
                        hide_index=True,
                        use_container_width=True
                    )

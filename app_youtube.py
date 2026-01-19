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
st.set_page_config(page_title="YouTube VidIQ Clone", page_icon="🚀", layout="wide")

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
    .score-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: bold;
        font-size: 1.2rem;
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

# --- 4. GEMINI API INTEGRATION ---
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_power_words_from_gemini(api_key, niche="general"):
    """
    Get trending power words from Gemini API based on niche
    """
    if not api_key or len(api_key) < 30:
        return None, "Invalid API Key"
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""Generate 30 powerful, high-CTR words for YouTube video titles in the {niche} niche.
        
Requirements:
- Words must be proven to increase click-through rates
- Include a mix of: urgency words, power words, emotional triggers
- Format: Return ONLY a JSON array of strings
- No explanations, just the array

Example format: ["ULTIMATE", "SECRET", "EXPOSED", "PROVEN", "SHOCKING"]

Generate 30 words now:"""
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Extract JSON array
        import json
        # Remove markdown code blocks if present
        text = text.replace('```json', '').replace('```', '').strip()
        
        words = json.loads(text)
        
        if isinstance(words, list) and len(words) > 0:
            return words, "🟢 Gemini AI"
        else:
            return None, "Invalid response"
            
    except Exception as e:
        return None, f"Error: {str(e)}"

@st.cache_data(ttl=600) 
def load_power_words(url):
    """Load power words from GitHub Gist"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0: 
                return data, "🟢 GitHub Online"
    except:
        pass
    return FALLBACK_POWER_WORDS, "🟠 Offline Fallback"

# Initialize power words database
POWER_WORDS_DB, db_status = load_power_words(URL_DATABASE_ONLINE)

# --- 5. HELPER FUNCTIONS ---
def calculate_engagement_rate(stats):
    """Calculate video engagement rate"""
    try:
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0))
        comments = int(stats.get('commentCount', 0))
        if views == 0:
            return 0
        engagement = ((likes + comments) / views) * 100
        return round(engagement, 2)
    except:
        return 0

def extract_core_theme(title, keyword):
    """
    Extract the actual theme/context from the title
    This preserves the original meaning while removing only the keyword
    """
    if not title:
        return ""
    
    # Remove keyword but keep the rest intact
    if keyword:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        core = pattern.sub("", title).strip()
    else:
        core = title
    
    core = re.sub(r'\s+', ' ', core)
    core = re.sub(r'^[:\-\|,\.\s]+', '', core)
    core = re.sub(r'[:\-\|,\.\s]+$', '', core)
    
    if not core or len(core) < 3:
        words = re.findall(r'\b\w+\b', title.lower())
        meaningful = [w for w in words if w not in STOP_WORDS and (not keyword or w != keyword.lower())]
        
        if meaningful:
            core = ' '.join(meaningful[:5])
        else:
            core = "Guide"
    
    return core.strip()

def smart_truncate(text, max_length):
    """Smart text truncation at word boundaries"""
    if not text or len(text) <= max_length:
        return text
    
    truncated = text[:max_length-3]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."

def extract_keywords_from_title(title, top_n=5):
    """Extract important keywords from title"""
    if not title:
        return []
    words = re.findall(r'\b[a-z]{3,}\b', title.lower())
    filtered = [w for w in words if w not in STOP_WORDS]
    counter = Counter(filtered)
    return [word for word, _ in counter.most_common(top_n)]

def generate_tags(title, keyword, competitor_tags=None):
    """Generate SEO-optimized tags"""
    if not title:
        return [keyword.lower()] if keyword else []
    
    tags = set()
    year = datetime.datetime.now().year
    
    if keyword:
        tags.add(keyword.lower())
        tags.add(f"{keyword.lower()} {year}")
        
        kw_words = keyword.lower().split()
        if len(kw_words) > 1:
            tags.add(kw_words[0])
            tags.add(' '.join(kw_words[:2]))
    
    clean_title = re.sub(r'[^\w\s]', '', title.lower())
    words = clean_title.split()
    
    for word in words:
        if word not in STOP_WORDS and len(word) > 2:
            tags.add(word)
            if len(tags) >= 12:
                break
    
    if competitor_tags:
        for tag in competitor_tags[:5]:
            if len(tags) < 18:
                tags.add(tag.lower())
    
    if keyword:
        tags.add(f"{keyword.lower()} tutorial")
        tags.add(f"how to {keyword.lower()}")
    
    return list(tags)[:20]

def generate_description(title, keyword, tags, video_length="10:00"):
    """Generate SEO-optimized description"""
    year = datetime.datetime.now().year
    month = datetime.datetime.now().strftime("%B")
    
    try:
        duration_mins = int(video_length.split(':')[0])
    except:
        duration_mins = 10
    
    tag_text = ', '.join(tags[:5]) if tags else keyword
    hashtags = ' '.join([f"#{tag.replace(' ', '')}" for tag in tags[:5]]) if tags else f"#{keyword.replace(' ', '')}"
    
    return f"""🎬 {title}

📌 **About This Video:**
In this comprehensive {video_length} video, we dive deep into **{keyword}**. Whether you're a beginner or looking to advance your skills, this {year} guide will help you master {keyword}.

⏱️ **Timestamps:**
0:00 - Introduction
0:45 - What is {keyword}?
2:30 - Step-by-step {keyword} tutorial
{max(duration_mins-3, 5)}:00 - Pro tips and advanced techniques
{max(duration_mins-2, 7)}:00 - Common mistakes to avoid
{max(duration_mins-1, 9)}:00 - Conclusion & next steps

🔥 **What You'll Learn:**
✅ Complete {keyword} fundamentals
✅ Practical examples and demonstrations
✅ Expert insights and strategies
✅ Proven techniques that work in {year}

💡 **Related Topics:**
{tag_text}

🔔 **Don't Forget to:**
• SUBSCRIBE for more {keyword} content
• LIKE if this video helped you
• COMMENT your questions below
• SHARE with anyone who needs this

📱 **Connect With Us:**
[Add your social media links here]

{hashtags}

---
© {year} | {keyword.title()} Tutorial | All Rights Reserved
"""

def generate_smart_suggestions(original_title, keyword, api_key=None, competitor_data=None):
    """Generate suggestions that preserve the original title's theme"""
    suggestions = []
    year = datetime.datetime.now().year
    
    if 'power_words' in st.session_state:
        power_words_list = st.session_state['power_words']
    else:
        power_words_list = POWER_WORDS_DB
    
    theme = extract_core_theme(original_title, keyword)
    
    if not theme or theme.lower() in ['guide', 'tutorial', 'video']:
        theme_words = extract_keywords_from_title(original_title, top_n=3)
        if theme_words:
            theme = ' '.join(theme_words[:3])
        else:
            theme = "Complete Guide"
    
    power_word = random.choice(power_words_list).upper()
    number = random.choice(['5', '7', '10'])
    emoji = random.choice(VIRAL_EMOJIS)
    
    if competitor_data and len(competitor_data) > 0:
        top_title = competitor_data[0].get('title', '')
        
        numbers = re.findall(r'\d+', top_title)
        if numbers:
            number = numbers[0]
        
        for word in power_words_list:
            if word.lower() in top_title.lower():
                power_word = word.upper()
                break
    
    extra_1 = len(keyword) + len(power_word) + len(str(year)) + len(emoji) + 10
    allowed_theme_1 = 100 - extra_1
    theme_1 = smart_truncate(theme.title(), allowed_theme_1)
    sug1 = f"{keyword.title()}: {theme_1} - {power_word} {year} {emoji}"
    suggestions.append(sug1)
    
    extra_2 = len(number) + len(keyword) + len(str(year)) + len(emoji) + 15
    allowed_theme_2 = 100 - extra_2
    theme_2 = smart_truncate(theme.title(), allowed_theme_2)
    sug2 = f"{number} {keyword.title()} {theme_2} You Need ({year}) {emoji}"
    suggestions.append(sug2)
    
    extra_3 = len(keyword) + len(power_word) + len(str(year)) + len(emoji) + 18
    allowed_theme_3 = 100 - extra_3
    theme_3 = smart_truncate(theme, allowed_theme_3)
    sug3 = f"How to {keyword.title()}: {theme_3} {emoji} [{year} {power_word}]"
    suggestions.append(sug3)
    
    extra_4 = len(keyword) + len(power_word) + len(str(year)) + len(emoji) + 12
    allowed_theme_4 = 100 - extra_4
    theme_4 = smart_truncate(theme.title(), allowed_theme_4)
    sug4 = f"{theme_4} - {keyword.title()} {power_word} Guide {year} {emoji}"
    suggestions.append(sug4)
    
    extra_5 = len(keyword) + len(power_word) + len(str(year)) + len(emoji) + 15
    allowed_theme_5 = 100 - extra_5
    theme_5 = smart_truncate(theme, allowed_theme_5)
    sug5 = f"{power_word} {keyword.title()} {theme_5} | {year} Tutorial {emoji}"
    suggestions.append(sug5)
    
    return suggestions

def analyze_title(title, keyword=""):
    """Comprehensive title SEO analysis"""
    score = 0
    checks = []
    
    if 'power_words' in st.session_state:
        power_words_list = st.session_state['power_words']
    else:
        power_words_list = POWER_WORDS_DB
    
    if not title:
        return 0, [("error", "Title is empty")]
    
    title_len = len(title)
    
    if 40 <= title_len <= 70:
        score += 25
        checks.append(("success", f"✅ Perfect Length ({title_len} chars) - Ideal for SEO"))
    elif 30 <= title_len <= 90:
        score += 20
        checks.append(("warning", f"⚠️ Good Length ({title_len} chars) - Can be optimized"))
    elif title_len < 30:
        score += 10
        checks.append(("error", f"❌ Too Short ({title_len} chars) - Add more details"))
    else:
        score += 5
        checks.append(("error", f"❌ Too Long ({title_len} chars) - Will be truncated"))
    
    if keyword:
        kw_lower = keyword.lower()
        title_lower = title.lower()
        
        if kw_lower in title_lower:
            position = title_lower.find(kw_lower)
            title_start = re.sub(r'^[^a-zA-Z0-9]+', '', title_lower).strip()
            
            if title_start.startswith(kw_lower):
                score += 20
                checks.append(("success", "✅ Keyword at Beginning - Perfect for SEO!"))
            elif position < 30:
                score += 15
                checks.append(("success", "✅ Keyword in First Half - Good placement"))
            else:
                score += 10
                checks.append(("warning", "⚠️ Keyword Present - Move closer to start"))
        else:
            checks.append(("error", "❌ Keyword Missing - Critical for ranking!"))
    else:
        score += 20
    
    found_power = [pw for pw in power_words_list if pw.lower() in title.lower()]
    if found_power:
        score += 15
        checks.append(("success", f"✅ Power Words: {', '.join(found_power[:2])}"))
    else:
        checks.append(("warning", "⚠️ No Power Words - Add 'BEST', 'ULTIMATE', etc."))
    
    numbers = re.findall(r'\d+', title)
    if numbers:
        score += 15
        checks.append(("success", f"✅ Numbers: {', '.join(numbers)} - Boosts CTR by 36%"))
    else:
        checks.append(("info", "💡 Add Numbers - Proven to increase clicks"))
    
    emojis = [e for e in VIRAL_EMOJIS if e in title]
    if emojis:
        score += 10
        checks.append(("success", f"✅ Emoji: {' '.join(emojis)} - Eye-catching"))
    else:
        checks.append(("info", "💡 Add Emoji - Increases visibility"))
    
    engagement_score = 0
    if '[' in title or '(' in title:
        engagement_score += 5
        checks.append(("success", "✅ Brackets Used - Adds context"))
    
    if '?' in title:
        engagement_score += 5
        checks.append(("success", "✅ Question Format - Creates curiosity"))
    
    current_year = str(datetime.datetime.now().year)
    if current_year in title:
        engagement_score += 5
        checks.append(("success", f"✅ Current Year ({current_year}) - Shows freshness"))
    
    if title.isupper():
        engagement_score -= 10
        checks.append(("error", "❌ ALL CAPS - Looks spammy"))
    
    score += min(engagement_score, 15)
    
    return min(score, 100), checks

def get_keyword_metrics(api_key, keyword):
    """Get comprehensive keyword metrics from YouTube"""
    if not api_key or len(api_key) < 30:
        return None, "❌ Invalid API Key"
    
    if not keyword:
        return None, "❌ Keyword required"
    
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        search_res = youtube.search().list(
            q=keyword,
            type='video',
            part='id,snippet',
            maxResults=20,
            order='relevance',
            regionCode='ID'
        ).execute()
        
        if not search_res.get('items'):
            return None, f"❌ No videos found for '{keyword}'"
        
        video_ids = [item['id']['videoId'] for item in search_res['items'] if 'videoId' in item.get('id', {})]
        
        if not video_ids:
            return None, "❌ No valid videos found"
        
        stats_res = youtube.videos().list(
            id=','.join(video_ids),
            part='statistics,snippet,contentDetails'
        ).execute()
        
        metrics = []
        all_tags = []
        upload_times = []
        
        for item in stats_res.get('items', []):
            snippet = item.get('snippet', {})
            stats = item.get('statistics', {})
            
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            comments = int(stats.get('commentCount', 0))
            engagement = calculate_engagement_rate(stats)
            
            tags = snippet.get('tags', [])
            all_tags.extend(tags)
            
            published = snippet.get('publishedAt', '')
            if published:
                upload_times.append(published)
            
            metrics.append({
                'title': snippet.get('title', ''),
                'Views': views,
                'Likes': likes,
                'Comments': comments,
                'Engagement': engagement,
                'Channel': snippet.get('channelTitle', 'Unknown'),
                'Date': published[:10] if published else 'N/A',
                'tags': tags,
                'publishedAt': published
            })
        
        if not metrics:
            return None, "❌ No data available"
        
        df = pd.DataFrame(metrics)
        
        view_counts = [m['Views'] for m in metrics if m['Views'] > 0]
        engagement_rates = [m['Engagement'] for m in metrics if m['Engagement'] > 0]
        
        median_views = statistics.median(view_counts) if view_counts else 0
        avg_views = statistics.mean(view_counts) if view_counts else 0
        avg_engagement = statistics.mean(engagement_rates) if engagement_rates else 0
        
        trending_tags = []
        if all_tags:
            tag_counts = Counter(all_tags)
            trending_tags = [tag for tag, _ in tag_counts.most_common(15)]
        
        best_time = "Unknown"
        if upload_times:
            hours = [int(t[11:13]) for t in upload_times if len(t) > 13]
            if hours:
                most_common_hour = Counter(hours).most_common(1)[0][0]
                best_time = f"{most_common_hour:02d}:00 - {(most_common_hour+1):02d}:00 WIB"
        
        if median_views > 500000:
            difficulty = "🔴 High"
            diff_score = 30
        elif median_views > 100000:
            difficulty = "🟡 Medium"
            diff_score = 60
        else:
            difficulty = "🟢 Low"
            diff_score = 90
        
        opportunity_score = diff_score
        
        return {
            'median_views': median_views,
            'avg_views': avg_views,
            'avg_engagement': avg_engagement,
            'score': opportunity_score,
            'difficulty': difficulty,
            'difficulty_score': diff_score,
            'trending_tags': trending_tags,
            'best_upload_time': best_time,
            'total_videos': len(metrics),
            'top_videos': df,
            'competitor_data': metrics
        }, None
        
    except Exception as e:
        error_msg = str(e)
        if "API key not valid" in error_msg:
            return None, "❌ API Key tidak valid!"
        elif "quota" in error_msg.lower():
            return None, "❌ Quota API habis!"
        else:
            return None, f"❌ Error: {error_msg}"

# --- 6. UI COMPONENTS ---
def draw_competitor_chart(df):
    """Visualize competitor data"""
    if df is None or df.empty:
        st.warning("No data available")
        return
    
    st.markdown("### 📊 Top Competitor Videos")
    
    max_views = df['Views'].max()
    if max_views == 0:
        max_views = 1
    
    for idx, row in df.head(10).iterrows():
        title = row['Title']
        if len(title) > 60:
            title = title[:60] + "..."
        
        views = row['Views']
        engagement = row.get('Engagement', 0)
        width_pct = int((views / max_views) * 100)
        
        if engagement > 5:
            color = "#10b981"
        elif engagement > 2:
            color = "#f59e0b"
        else:
            color = "#ef4444"
        
        st.markdown(f"""
        <div style="background: #1e1e1e; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <div style="color: white; font-weight: bold; font-size: 14px; margin-bottom: 0.5rem;">{title}</div>
            <div style="color: #888; font-size: 12px; margin-bottom: 0.5rem;">
                {row['Channel']} • {views:,} views • {engagement}% engagement
            </div>
            <div style="background: #333; width: 100%; height: 10px; border-radius: 5px; overflow: hidden;">
                <div style="background: {color}; width: {width_pct}%; height: 10px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    
    if "Gemini" in st.session_state.get('db_source', ''):
        st.success(st.session_state.get('db_source', db_status))
    elif "GitHub" in db_status:
        st.success(db_status)
    else:
        st.warning(db_status)
    
    st.divider()
    
    # === GEMINI API SECTION ===
    st.markdown("### 🤖 Gemini AI (Optional)")
    gemini_key = st.text_input("Gemini API Key:", type="password", placeholder="AIzaSy...", key="gemini_key")
    
    if gemini_key and len(gemini_key) > 30:
        st.success("🟢 Gemini Connected")
        
        niche_option = st.selectbox(
            "AI Power Words Niche:",
            ["general", "gaming", "tech", "cooking", "music", "fitness", "education", "entertainment", "business", "lifestyle"],
            help="Generate power words specific to your niche"
        )
        
        if st.button("🚀 Generate AI Power Words", use_container_width=True):
            with st.spinner("🤖 Asking Gemini for trending power words..."):
                ai_words, ai_status = get_power_words_from_gemini(gemini_key, niche_option)
                
                if ai_words:
                    st.session_state['power_words'] = ai_words
                    st.session_state['db_source'] = f"🤖 Gemini AI ({niche_option})"
                    st.success(f"✅ Loaded {len(ai_words)} AI power words!")
                    st.rerun()
                else:
                    st.error(f"❌ {ai_status}")
    elif gemini_key:
        st.warning("⚠️ Key too short")
    else:
        st.info("💡 Add Gemini API for AI-powered words")
    
    with st.expander("📖 Get Gemini API Key"):
        st.markdown("""
        1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
        2. Click "Create API Key"
        3. Copy the key
        4. Paste above ↑
        
        **Benefits:**
        - AI-generated power words
        - Niche-specific recommendations
        - Always up-to-date trends
        - Free tier: 60 requests/minute
        """)
    
    st.divider()
    
    # === YOUTUBE API SECTION ===
    st.markdown("### 🔑 YouTube API")
    api_key = st.text_input("YouTube API Key:", type="password", placeholder="AIzaSy...", key="yt_key")
    
    if api_key and len(api_key) > 30:
        st.success("🟢 YouTube Connected")
    elif api_key:
        st.warning("⚠️ Key too short")
    
    with st.expander("📖 Get YouTube API Key"):
        st.markdown("""
        1. Visit [Google Cloud Console](https://console.cloud.google.com)
        2. Create new project
        3. Enable YouTube Data API v3
        4. Create credentials (API Key)
        5. Copy & paste above
        
        **Free Quota:** 10,000 units/day
        """)
    
    st.divider()
    
    # === STATS ===
    st.markdown("### 📊 Database Stats")
    
    if 'power_words' in st.session_state:
        current_words = st.session_state['power_words']
        source = st.session_state.get('db_source', 'Custom')
    else:
        current_words = POWER_WORDS_DB
        source = db_status
    
    st.metric("Power Words", len(current_words))
    st.metric("Viral Emojis", len(VIRAL_EMOJIS))
    
    if "Gemini" in source:
        st.markdown('<span class="api-badge" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">🤖 AI-Powered</span>', unsafe_allow_html=True)
    elif "GitHub" in source:
        st.markdown('<span class="api-badge" style="background: #10b981; color: white;">🌐 Online DB</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="api-badge" style="background: #f59e0b; color: white;">💾 Offline DB</span>', unsafe_allow_html=True)
    
    st.divider()
    
    # === QUICK ACTIONS ===
    st.markdown("### ⚡ Quick Actions")
    
    if st.button("🔄 Reset to Default", use_container_width=True):
        if 'power_words' in st.session_state:
            del st.session_state['power_words']
        if 'db_source' in st.session_state:
            del st.session_state['db_source']
        st.rerun()
    
    if 'power_words' in st.session_state:
        with st.expander("👁️ View Current Power Words"):
            words_preview = st.session_state['power_words'][:20]
            st.write(", ".join(words_preview))
            if len(st.session_state['power_words']) > 20:
                st.caption(f"...and {len(st.session_state['power_words']) - 20} more")

# --- 8. MAIN APP ---
st.markdown("""
<div style='text-align: center; color: white; margin-bottom: 2rem;'>
    <h1 style='font-size: 3.5rem; font-weight: 800; text-shadow: 2px 2px 10px rgba(0,0,0,0.3);'>🚀 YouTube VidIQ Clone</h1>
    <p style='color: #ddd; font-size: 1.2rem;'>Advanced YouTube SEO & Analytics Tool</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["🔍 Keyword Research", "📝 Title Optimizer", "📺 Channel Audit", "🎯 Trend Finder"])

# TAB 1: KEYWORD RESEARCH
with tab1:
    st.markdown("### 🔍 Keyword Research & Analysis")
    
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        kw_input = st.text_input("Enter Keyword/Topic:", placeholder="e.g., lullaby sleeping music")
    with col_btn:
        st.write("")
        st.write("")
        analyze_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)
    
    if analyze_btn:
        if not api_key or len(api_key) < 30:
            st.error("⚠️ Please enter valid API Key in sidebar")
        elif not kw_input:
            st.warning("⚠️ Enter a keyword first")
        else:
            with st.spinner(f"🔄 Analyzing '{kw_input}'..."):
                data, err = get_keyword_metrics(api_key, kw_input)
                
                if err:
                    st.error(err)
                elif data:
                    st.success(f"✅ Analysis complete for '{kw_input}'")
                    
                    # Metrics
                    st.markdown("### 📊 Market Overview")
                    m1, m2, m3, m4 = st.columns(4)
                    
                    with m1:
                        st.metric("Opportunity", f"{data['score']}/100")
                    with m2:
                        st.metric("Competition", data['difficulty'])
                    with m3:
                        st.metric("Avg Views", f"{int(data['avg_views']):,}")
                    with m4:
                        st.metric("Videos Analyzed", data['total_videos'])
                    
                    st.divider()
                    
                    # Visuals
                    col_chart, col_tags = st.columns([2, 1])
                    
                    with col_chart:
                        draw_competitor_chart(data['top_videos'])
                    
                    with col_tags:
                        st.markdown("### 🏷️ Trending Tags")
                        if data['trending_tags']:
                            for tag in data['trending_tags'][:10]:
                                st.code(tag, language='text')
                        
                        st.divider()
                        st.markdown("### ⏰ Best Upload Time")
                        st.info(data['best_upload_time'])

# TAB 2: TITLE OPTIMIZER (FIXED)
with tab2:
    st.markdown("### ✍️ Title Optimizer")
    
    col_kw, col_title = st.columns([1, 2])
    with col_kw:
        keyword = st.text_input("🎯 Target Keyword:", placeholder="e.g., lullaby sleeping")
    with col_title:
        title = st.text_input("📝 Your Title:", placeholder="Paste your title here...")
    
    if st.button("🔍 Analyze & Get Suggestions", type="primary"):
        if not title:
            st.warning("⚠️ Enter a title to analyze")
        else:
            score, checks = analyze_title(title, keyword)
            
            # Display score
            st.markdown("---")
            if score >= 80:
                color = "#10b981"
                grade = "A"
                msg = "Excellent!"
            elif score >= 60:
                color = "#f59e0b"
                grade = "B"
                msg = "Good"
            else:
                color = "#ef4444"
                grade = "C"
                msg = "Needs Work"
            
            col_score, col_grade = st.columns([4, 1])
            with col_score:
                st.markdown(f"""
                <div style='background: {color}22; padding: 1.5rem; border-radius: 10px; border-left: 5px solid {color};'>
                    <h2 style='color: {color}; margin: 0;'>SEO Score: {score}/100</h2>
                    <p style='color: #666; margin: 0.5rem 0 0 0;'>{msg} - Grade {grade}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col_grade:
                st.markdown(f"<h1 style='color:{color}; text-align:center; font-size:4rem; margin:0;'>{grade}</h1>", unsafe_allow_html=True)
            
            # Analysis details
            st.markdown("---")
            st.markdown("### 📋 SEO Analysis")
            
            cols = st.columns(3)
            for i, (status, message) in enumerate(checks):
                with cols[i % 3]:
                    if status == "success":
                        st.success(message, icon="✅")
                    elif status == "warning":
                        st.warning(message, icon="⚠️")
                    elif status == "info":
                        st.info(message, icon="💡")
                    else:
                        st.error(message, icon="❌")
            
            # Generate suggestions if needed
            if score < 85 and keyword:
                st.markdown("---")
                st.markdown("### 💡 AI-Powered Title Suggestions")
                st.caption(f"**Original Theme Preserved:** These suggestions maintain your title's original context")
                
                extracted_theme = extract_core_theme(title, keyword)
                st.info(f"🎯 **Detected Theme:** {extracted_theme}")
                
                # Get competitor data if API available
                competitor_data = None
                if api_key and len(api_key) > 30:
                    with st.spinner("📊 Analyzing competitors..."):
                        result, _ = get_keyword_metrics(api_key, keyword)
                        if result:
                            competitor_data = result.get('competitor_data', [])
                
                suggestions = generate_smart_suggestions(title, keyword, api_key, competitor_data)
                
                for i, sug in enumerate(suggestions, 1):
                    sug_score, _ = analyze_title(sug, keyword)
                    
                    if sug_score > score:
                        badge_color = "#10b981"
                        badge_text = f"🔥 +{sug_score - score} Better"
                    elif sug_score == score:
                        badge_color = "#3b82f6"
                        badge_text = "📊 Same Score"
                    else:
                        badge_color = "#f59e0b"
                        badge_text = "📝 Alternative"
                    
                    st.markdown(f"""
                    <div class="suggestion-box" style="border-left: 4px solid {badge_color};">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span style="font-weight: bold; font-size: 0.9rem;">{badge_text}</span>
                            <span style="font-weight: bold;">Score: {sug_score}/100</span>
                        </div>
                        <div style="font-size: 1rem; line-height: 1.4;">{sug}</div>
                        <div style="margin-top: 0.5rem; font-size: 0.85rem; opacity: 0.8;">
                            Length: {len(sug)} chars
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Copy button
                    if st.button(f"📋 Copy Suggestion #{i}", key=f"copy_sug_{i}"):
                        st.code(sug, language='text')
            
            # Tags & Description
            st.markdown("---")
            st.markdown("### 🎁 Complete Metadata Package")
            
            tab_tags, tab_desc = st.tabs(["🏷️ Tags", "📄 Description"])
            
           

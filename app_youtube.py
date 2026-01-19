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

# Function for generating suggestions based on trends
def generate_trending_titles(trend_keywords, niche="general"):
    """Generate trending titles based on common keywords"""
    suggestions = []
    
    # Example: Generate titles using the top trending keywords and phrases
    for trend in trend_keywords:
        suggestions.append(f"{trend} {niche.title()} tutorial {random.choice(VIRAL_EMOJIS)}")
        suggestions.append(f"How to {trend} in {niche.title()} {random.choice(VIRAL_EMOJIS)}")
    
    return suggestions

# Function for analyzing competitors' videos
def analyze_competitors(api_key, keyword):
    """Analyze competitors' videos for keyword performance"""
    youtube = build('youtube', 'v3', developerKey=api_key)
    search_res = youtube.search().list(
        q=keyword,
        type='video',
        part='id,snippet',
        maxResults=10,
        order='relevance',
    ).execute()

    competitors = []
    for item in search_res['items']:
        competitors.append({
            'title': item['snippet']['title'],
            'channel': item['snippet']['channelTitle'],
            'views': item['snippet']['viewCount'],
            'engagement': calculate_engagement_rate(item['statistics']),
            'tags': item['snippet'].get('tags', [])
        })
    
    return competitors

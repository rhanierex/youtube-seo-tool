import streamlit as st
import re
import random
import datetime

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="YouTube SEO Optimizer By Sab", page_icon="🚀", layout="centered")

# --- DATABASE ---
POWER_WORDS_DB = [
    "secret", "exposed", "hidden", "revealed", "mystery", "confession", 
    "truth", "lies", "myth", "banned", "illegal", "private", "unknown",
    "what happened", "nobody knows", "strange", "weird",
    "now", "today", "finally", "limited", "only", "last chance", "hurry", 
    "urgent", "alert", "warning", "stop", "don't", "never", "before", 
    "mistake", "worst", "fatal", "risk",
    "shocking", "insane", "crazy", "unbelievable", "mind blowing", "scary",
    "emotional", "sad", "heartbreaking", "hilarious", "best", "greatest",
    "legendary", "epic", "fail", "perfect", "satisfying",
    "easy", "fast", "quick", "simple", "hack", "trick", "tips", "guide",
    "tutorial", "how to", "step by step", "free", "cheap", "profit", "money",
    "growth", "result", "proven", "guaranteed", "instant", "automatic",
    "relaxing", "calming", "deep sleep", "healing", "stress relief", "insomnia",
    "brain", "focus", "study", "ambient", "4k", "8k", "60fps", "hd", "loop",
    "endless", "hours", "satisfying", "hypnotic", "live"
]

VIRAL_EMOJIS = ["🔥", "😱", "🔴", "✅", "❌", "🎵", "⚠️", "⚡", "🚀", "💰", "💯", "🤯", "😭", "😡", "😴", "🌙", "✨", "💤", "🌧️", "🎹"]

STOP_WORDS = ["the", "and", "or", "for", "to", "in", "on", "at", "by", "with", "a", "an", "is", "it", "of", "that", "this", "from", "how", "what", "why", "video"]

# --- FUNGSI LOGIKA (Backend) ---
def clean_title_text(title, keyword):
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    clean = pattern.sub("", title)
    clean = clean.strip()
    clean = re.sub(r'^[:\-\|]\s*', '', clean)
    clean = re.sub(r'\[.*?\]', '', clean)
    clean = re.sub(r'\(.*?\)', '', clean)
    if len(clean) > 45:
        clean = clean[:45].rsplit(' ', 1)[0] + "..." 
    return clean.strip()

def generate_tags(title, keyword):
    clean_t = re.sub(r'[^\w\s]', '', title.lower())
    words = clean_t.split()
    tags = [keyword.lower()]
    current_year = datetime.datetime.now().year
    
    for w in words:
        if w not in STOP_WORDS and w not in tags and len(w) > 2:
            tags.append(w)
    tags.append(f"{keyword.lower()} {current_year}")
    return tags[:15]

def generate_suggestions(original_title, keyword):
    suggestions = []
    pw1 = random.choice(POWER_WORDS_DB).upper()
    pw2 = random.choice(POWER_WORDS_DB).upper()
    emo = random.choice(["🎵", "🌙", "✨", "💤", "🔥", "🔴"])
    current_year = datetime.datetime.now().year
    
    core_text = clean_title_text(original_title, keyword)
    if not core_text: core_text = "Video"

    suggestions.append(f"{keyword.title()}: {core_text} ({pw1} {current_year}) {emo}")
    suggestions.append(f"{emo} {keyword.title()} {pw2}: {core_text} [{current_year}]")
    suggestions.append(f"{core_text} - {keyword.upper()} {emo} [{pw1} METHOD]")
    return suggestions

def analyze(title, keyword):
    score = 0
    checks = []
    
    # 1. Length
    length = len(title)
    if 20 <= length <= 80:
        score += 20
        checks.append(("success", f"Length Optimal ({length} chars)"))
    elif length > 80:
        score += 10
        checks.append(("warning", "Length Risk (>80 chars)"))
    else:
        checks.append(("error", "Too Short"))

    # 2. Keyword Position
    lower_title = title.lower()
    lower_keyword = keyword.lower()
    clean_start_title = re.sub(r'^[^a-zA-Z0-9]+', '', lower_title).strip()

    if lower_keyword in lower_title:
        score += 15
        if clean_start_title.startswith(lower_keyword):
            score += 15
            checks.append(("success", "Keyword at Front (High SEO)"))
        else:
            checks.append(("warning", "Keyword present, but not at start"))
    else:
        checks.append(("error", "Keyword Missing"))

    # 3. Power Words
    found_power = [pw for pw in POWER_WORDS_DB if pw in lower_title]
    if found_power:
        score += 20
        checks.append(("success", f"Power Word Found: {found_power[0].upper()}"))
    else:
        checks.append(("warning", "No Emotional Trigger Words"))

    # 4. Formatting
    if re.search(r'\d+', title):
        score += 10
        checks.append(("success", "Contains Numbers"))
    else:
        checks.append(("info", "Tip: Add Numbers"))

    if re.search(r'[\[\(\]\)]', title):
        score += 10
        checks.append(("success", "Contains Brackets"))
    else:
        checks.append(("info", "Tip: Add Brackets"))

    # 5. Emoji
    found_emojis = [char for char in title if char in VIRAL_EMOJIS or ord(char) > 10000]
    if 0 < len(found_emojis) <= 2:
        score += 10
        checks.append(("success", "Visual Hook (Emoji)"))
    elif len(found_emojis) > 2:
        score += 5
        checks.append(("warning", "Too Many Emojis"))
    else:
        checks.append(("info", "Tip: Add 1 Emoji"))

    return score, checks

# --- TAMPILAN USER INTERFACE (Frontend) ---
st.title("🚀 YouTube SEO Command Center")
st.markdown("Optimization tool similar to vidIQ/TubeBuddy but **Customizable**.")

col1, col2 = st.columns(2)
with col1:
    keyword = st.text_input("Target Keyword (SEO)", placeholder="e.g. relaxing music")
with col2:
    title = st.text_input("Video Title", placeholder="Draft your title here...")

if st.button("Analyze Now", type="primary"):
    if keyword and title:
        score, logs = analyze(title, keyword)
        
        # Tampilkan Skor Bar
        st.divider()
        st.subheader("📊 Performance Score")
        my_bar = st.progress(0, text=f"Score: {score}/100")
        my_bar.progress(score, text=f"Score: {score}/100")
        
        if score >= 95:
            st.balloons()
            st.success("PERFECT TITLE! Ready to Publish.")
        elif score >= 80:
            st.success("Great Title! Minor tweaks possible.")
        elif score >= 60:
            st.warning("Good, but needs optimization.")
        else:
            st.error("Needs improvement.")

        # Tampilkan Checklist
        st.subheader("🔍 Analysis Details")
        for type_log, msg in logs:
            if type_log == "success": st.success(msg, icon="✅")
            elif type_log == "warning": st.warning(msg, icon="⚠️")
            elif type_log == "error": st.error(msg, icon="❌")
            else: st.info(msg, icon="ℹ️")

        # Generator Solusi
        st.divider()
        col_gen1, col_gen2 = st.columns(2)
        
        with col_gen1:
            st.subheader("💡 Title Suggestions")
            if score < 100:
                suggestions = generate_suggestions(title, keyword)
                for s in suggestions:
                    st.code(s, language="text")
            else:
                st.info("Title is already perfect!")

        with col_gen2:
            st.subheader("🏷️ Generated Tags")
            tags = generate_tags(title, keyword)
            st.text_area("Copy for YouTube Tags:", ", ".join(tags), height=100)

        # Deskripsi Generator
        st.subheader("📝 Description Template")
        desc_template = f"""
🔴 **{title}**

In this video, I will show you **{keyword}** and {title}. This is the best guide for {datetime.datetime.now().year}.

👇 **Timestamps:**
0:00 Intro
0:30 {keyword.title()}
5:00 Conclusion

🔔 **Don't forget to SUBSCRIBE!**

#Hashtags:
#{keyword.replace(" ", "")} #Video #{tags[1] if len(tags)>1 else 'Shorts'}
        """
        st.text_area("Copy for YouTube Description:", desc_template, height=200)

    else:

        st.error("Please enter both Keyword and Title.")

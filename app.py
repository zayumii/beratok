# app.py
import streamlit as st
import tweepy
import time
import requests
import re
import pandas as pd
from dateutil import parser
from datetime import timedelta

# Set up Twitter API
BEARER_TOKEN = st.secrets["BEARER_TOKEN"]
client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

# --- Token Scoring ---
TOKEN_KEYWORDS = ['airdrop', 'token', 'launch', 'points', 'claim', 'rewards', 'mainnet']

def score_token_likelihood(tweets):
    text = " ".join(tweets).lower()
    return min(100, sum(1 for kw in TOKEN_KEYWORDS if kw in text) * 15)

def extract_tge_info(tweets):
    text = " ".join(tweets)
    patterns = [
        r'(TGE|token launch|airdrop claim).*?(on|around)?\s*(\w+\s\d{1,2}(st|nd|rd|th)?(,?\s*\d{4})?)',
        r'launching\s+(this|next)?\s*(month|week|quarter|year)',
        r'(Q[1-4])\s?(\d{4})'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                date_string = match.group(3) if match.lastindex >= 3 else match.group(0)
                date = parser.parse(date_string, fuzzy=True)
                return date.strftime('%Y-%m-%d')
            except:
                return match.group(0)
    return None

# --- Fetch Smokey's Followed Users (safe) ---
@st.cache_data(ttl=3600)
def get_smokey_followed_users(max_users=3):
    smokey_id = client.get_user(username="SmokeyTheBera").data.id
    users = []
    paginator = tweepy.Paginator(
        client.get_users_following,
        id=smokey_id,
        max_results=100,
        user_fields=["username", "name"]
    )
    for page in paginator:
        if page.data:
            for user in page.data:
                users.append({'id': user.id, 'name': user.name, 'username': user.username})
                if len(users) >= max_users:
                    return users
    return users

# --- Project Scanner ---
def discover_projects_from_smokey(stop_flag):
    users = get_smokey_followed_users()
    results = []
    sleep_duration = 1.5

    for i, user in enumerate(users):
        if stop_flag():
            st.warning("🚫 Scan manually stopped.")
            break

        try:
            with st.spinner(f"🔍 Scanning @{user['username']}..."):
                tweets = client.get_users_tweets(id=user["id"], max_results=3).data
                tweet_texts = [t.text for t in tweets] if tweets else []

                score = score_token_likelihood(tweet_texts)
                tge = extract_tge_info(tweet_texts) if score > 60 else None

                results.append({
                    "Project": user["name"],
                    "Twitter": f"https://twitter.com/{user['username']}",
                    "Token Likelihood": f"{score}%",
                    "TGE Schedule": tge or "-"
                })

        except Exception as e:
            st.warning(f"Error with @{user['username']}: {e}")

        minutes = int(sleep_duration // 60)
        seconds = int(sleep_duration % 60)
        st.info(f"🕒 Rate limit buffer: waiting {minutes:02d}:{seconds:02d} before next call...")
        time.sleep(sleep_duration)

    return pd.DataFrame(results)

# --- Streamlit UI ---
st.set_page_config(page_title="Berachain Token Scanner", layout="wide")
st.title("🧭 Berachain Token Launch Scanner - Rate Limit Safe")

run = st.button("▶️ Run Scan")
stop = st.button("🛑 Stop Scan")

def should_stop():
    return stop

if run and not stop:
    with st.spinner("Running safe scan..."):
        df = discover_projects_from_smokey(should_stop)
        if not df.empty:
            st.success("✅ Scan complete!")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "projects.csv", "text/csv")
        else:
            st.info("No projects found.")

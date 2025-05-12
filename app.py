# app.py
import streamlit as st
import time
import requests
import re
import pandas as pd
from dateutil import parser
import subprocess
import json

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

# --- Get Profile Bios Using CLI ---
def get_profile_bio(username):
    command = f"snscrape --jsonl twitter-user {username}"
    try:
        result = subprocess.check_output(command, shell=True, text=True)
        return json.loads(result.strip())["description"]
    except Exception as e:
        st.error(f"❌ Error getting bio for @{username}: {e}")
        return ""

# --- Get Tweets using CLI ---
def get_recent_tweets(username, max_count=5):
    command = f"snscrape --jsonl --max-results {max_count} twitter-user {username}"
    try:
        result = subprocess.check_output(command, shell=True, text=True)
        tweets = [json.loads(line)["content"] for line in result.strip().split("\n")]
        return tweets
    except Exception as e:
        st.error(f"❌ Error scraping @{username}: {e}")
        return []

# --- Fetch all users followed by @SmokeyTheBera ---
def get_followed_usernames():
    usernames = []
    command = f"snscrape --jsonl twitter-user SmokeyTheBera following"
    try:
        result = subprocess.check_output(command, shell=True, text=True)
        for line in result.strip().split("\n"):
            data = json.loads(line)
            if "on @Berachain" in data.get("description", ""):
                usernames.append(data["username"])
    except Exception as e:
        st.error(f"❌ Error retrieving followed users: {e}")
    return usernames

# --- Project Scanner ---
def discover_projects_with_snscrape(stop_flag):
    usernames = get_followed_usernames()
    st.info(f"Found {len(usernames)} users with 'on @Berachain' in bio")
    results = []

    for username in usernames:
        if stop_flag():
            st.warning("🚫 Scan manually stopped.")
            break

        st.info(f"🔍 Scanning @{username}...")
        tweets = get_recent_tweets(username, max_count=5)

        if not tweets:
            continue  # Skip inactive accounts

        score = score_token_likelihood(tweets)
        tge = extract_tge_info(tweets) if score > 60 else None

        results.append({
            "Project": username,
            "Twitter": f"https://twitter.com/{username}",
            "Token Likelihood": f"{score}%",
            "TGE Schedule": tge or "-"
        })

        time.sleep(1)

    df = pd.DataFrame(results)
    if "Token Likelihood" in df.columns:
        return df.sort_values(by="Token Likelihood", ascending=False, key=lambda col: col.str.rstrip('%').astype(int))
return df


# --- Streamlit UI ---
st.set_page_config(page_title="Berachain Token Scanner", layout="wide")
st.title("🧭 Berachain Token Launch Scanner - Free Mode (No Twitter API)")

run = st.button("▶️ Run Scan")
stop = st.button("🛑 Stop Scan")

def should_stop():
    return stop

if run and not stop:
    with st.spinner("Running free-mode scan..."):
        df = discover_projects_with_snscrape(should_stop)
        if not df.empty:
            st.success("✅ Scan complete!")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "projects.csv", "text/csv")
        else:
            st.info("No projects found.")

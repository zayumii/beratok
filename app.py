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

# --- Score tweet content ---
def score_token_likelihood(tweets):
    text = " ".join(tweets).lower()
    return min(100, sum(1 for kw in TOKEN_KEYWORDS if kw in text) * 15)

# --- Extract possible TGE info ---
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

# --- Get Tweets using CLI ---
def get_recent_tweets(username, max_count=5):
    command = f"snscrape --jsonl --max-results {max_count} twitter-user {username}"
    try:
        result = subprocess.check_output(command, shell=True, text=True)
        tweets = [json.loads(line)["content"] for line in result.strip().split("\n") if line.strip()]
        return tweets
    except Exception as e:
        st.warning(f"❌ Error scraping @{username}: {e}")
        return []

# --- Fallback: Fetch Projects from BeraLand ---
def fetch_beraland_projects():
    url = "https://app.beraland.xyz/api/ecosystem"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to fetch BeraLand projects: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Failed to reach BeraLand API: {e}")
        return []

# --- Parse twitter handles ---
def extract_twitter_handles(projects):
    handles = []
    for project in projects:
        url = project.get("twitter")
        if url and "twitter.com" in url:
            handle = url.rstrip("/").split("/")[-1].replace("@", "")
            if handle and handle not in handles:
                handles.append(handle)
    return handles

# --- Attempt CLI scrape of users with "on @Berachain" in bio ---
def try_scrape_on_berachain_usernames():
    usernames = []
    command = f"snscrape --jsonl --max-results 1000 twitter-search 'on @berachain'"
    try:
        result = subprocess.check_output(command, shell=True, text=True)
        seen = set()
        for line in result.strip().split("\n"):
            data = json.loads(line)
            author = data.get("user", {}).get("username")
            bio = data.get("user", {}).get("description", "")
            if author and author not in seen and "on @berachain" in bio.lower():
                usernames.append(author)
                seen.add(author)
    except Exception as e:
        st.warning(f"⚠️ Could not scrape 'on @berachain' bios. Reason: {e}")
    return usernames

# --- Scanner ---
def discover_projects_from_beraland(stop_flag):
    usernames = try_scrape_on_berachain_usernames()
    if not usernames:
        st.info("🔁 Falling back to project list from BeraLand")
        projects = fetch_beraland_projects()
        usernames = extract_twitter_handles(projects)

    st.info(f"🔎 Scanning {len(usernames)} project accounts...")

    results = []
    for handle in usernames:
        if stop_flag():
            st.warning("🚫 Scan manually stopped.")
            break

        st.info(f"📡 Fetching tweets from @{handle}...")
        tweets = get_recent_tweets(handle, max_count=5)
        if not tweets:
            continue

        score = score_token_likelihood(tweets)
        tge = extract_tge_info(tweets) if score > 60 else None

        results.append({
            "Project": handle,
            "Twitter": f"https://twitter.com/{handle}",
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
st.title("🧭 Berachain Token Launch Scanner")

run = st.button("▶️ Run Scan")
stop = st.button("🛑 Stop Scan")

def should_stop():
    return stop

if run and not stop:
    with st.spinner("Running ecosystem scan..."):
        df = discover_projects_from_beraland(should_stop)
        if not df.empty:
            st.success("✅ Scan complete!")
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "projects.csv", "text/csv")
        else:
            st.info("No projects found.")

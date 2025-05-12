import time
import tweepy
import streamlit as st
import tweepy
import requests
import re
import pandas as pd
from dateutil import parser

import streamlit as st

BEARER_TOKEN = st.secrets["BEARER_TOKEN"]
client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

# === Twitter API Setup ===
BEARER_TOKEN = st.secrets["BEARER_TOKEN"]  # Replace this with your token
client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

# === Helper: Discover Berachain Projects ===
def get_followed_users(smokey_username="SmokeyTheBera", max_users=10):
    """Return a list of users followed by @SmokeyTheBera"""
    smokey_user = client.get_user(username=smokey_username)
    smokey_id = smokey_user.data.id

    users = []
    paginator = tweepy.Paginator(
        client.get_users_following,
        id=smokey_id,
        max_results=100,
        user_fields=["username", "name", "description"]
    )

    for page in paginator:
        if page.data:
            for user in page.data:
                users.append({'id': user.id, 'name': user.name, 'username': user.username})
                if len(users) >= max_users:
                    return users
    return users

def discover_projects_from_smokey():
    smokey_user = client.get_user(username="SmokeyTheBera")
    smokey_id = smokey_user.data.id

    users = get_followed_users(user_id=smokey_id, max_users=10)

    results = []
    for user in users:
        try:
            with st.spinner(f"🔍 Scanning @{user['username']}..."):
                tweets = client.get_users_tweets(id=user["id"], max_results=5).data
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
        time.sleep(0.5)
    return results

def get_followed_users(user_id, max_users=50):
    users = []
    pagination = tweepy.Paginator(
        client.get_users_following,
        id=user_id,
        max_results=100,
        user_fields=["username", "name", "description"]
    )
    for page in pagination:
        if page.data:
            for user in page.data:
                users.append({'name': user.name, 'username': user.username})
                if len(users) >= max_users:
                    return users
    return users

# === Token Check ===
def has_token_on_coingecko(project_name):
    try:
        url = f"https://api.coingecko.com/api/v3/search?query={project_name}"
        res = requests.get(url)
        return any(project_name.lower() in coin["name"].lower() for coin in res.json().get("coins", []))
    except:
        return False

# === Tweet Scoring ===
TOKEN_KEYWORDS = ['airdrop', 'token', 'launch', 'points', 'claim', 'rewards', 'mainnet']

def score_token_likelihood(tweets):
    text = " ".join(tweets).lower()
    return min(100, sum(1 for kw in TOKEN_KEYWORDS if kw in text) * 15)

# === TGE Extractor ===
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

# === Streamlit UI ===
st.set_page_config(page_title="Berachain Token Scanner", layout="wide")
st.title("🧭 Berachain Token Launch Scanner")

if st.button("Scan Twitter"):
    with st.spinner("Searching Twitter and analyzing projects..."):
        projects = discover_projects_from_smokey()

        results = []
        for proj in projects:
            username = proj['username']
            name = proj['name']
            try:
                user = client.get_user(username=username)
                tweets = client.get_users_tweets(id=user.data.id, max_results=20).data
                tweet_texts = [tweet.text for tweet in tweets] if tweets else []

                token_exists = has_token_on_coingecko(name)
                score = score_token_likelihood(tweet_texts)
                tge = extract_tge_info(tweet_texts) if score > 60 else None

                results.append({
                    "Project": name,
                    "Twitter": f"https://twitter.com/{username}",
                    "Token Exists": "✅" if token_exists else "❌",
                    "Token Likelihood": f"{score}%",
                    "TGE Schedule": tge or "-"
                })
            except Exception as e:
                st.warning(f"Error with @{username}: {e}")

        df = pd.DataFrame(results)

        if not df.empty:
            st.success("Scan complete. Here are the results:")
            st.dataframe(df, use_container_width=True)

            # CSV Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="⬇️ Download CSV",
                data=csv,
                file_name='berachain_token_candidates.csv',
                mime='text/csv',
            )
        else:
            st.info("No results found.")

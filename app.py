import tweepy
import streamlit as st
import tweepy
import requests
import re
import pandas as pd
from dateutil import parser

import streamlit as st

BEARER_TOKEN = st.secrets["BEARER_TOKEN"]  # Your token from secrets
client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

# === Twitter API Setup ===
BEARER_TOKEN = st.secrets["BEARER_TOKEN"]  # Replace this with your token
client = tweepy.Client(bearer_token=BEARER_TOKEN, wait_on_rate_limit=True)

# === Helper: Discover Berachain Projects ===
def discover_projects(client, max_projects=20):
    query = '"on @berachain" -is:retweet lang:en'
    tweets = client.search_recent_tweets(
        query=query,
        max_results=100,
        tweet_fields=["author_id"]
    )

    projects = []
    seen_users = set()

    if tweets.data:
        for tweet in tweets.data:
            user_id = tweet.author_id
            if user_id in seen_users:
                continue
            try:
                user = client.get_user(id=user_id, user_fields=["username", "name"])
                if user.data:
                    username = user.data.username
                    name = user.data.name
                    projects.append({'name': name, 'username': username})
                    seen_users.add(user_id)
                if len(projects) >= max_projects:
                    break
            except Exception as e:
                print(f"Error fetching user {user_id}: {e}")
    return projects


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
        projects = discover_projects(client)

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

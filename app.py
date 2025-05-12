import streamlit as st
import subprocess
import json
import pandas as pd
import os

# Function to install required packages
def install_packages():
    try:
        subprocess.run(["pip", "install", "snscrape"], check=True)
        subprocess.run(["pip", "install", "pandas"], check=True) # Add pandas installation
        subprocess.run(["pip", "install", "--upgrade", "pip"], check=False)  # Update pip
        print("Packages installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Error installing packages: {e}")
        return False

# Function to scrape Twitter accounts
def scrape_twitter_accounts(query, max_results=1000):
    try:
        # Ensure snscrape is installed
        result = subprocess.run(
            ["snscrape", "--jsonl", f"--max-results={max_results}", "twitter-search", query],
            capture_output=True,
            text=True,  # Get output as text
            check=True, # Raise exception on non-zero exit
        )
        output = result.stdout
        # print(f"Snscrape Output: {output}") # Debugging: Print the raw output
        lines = output.strip().split('\n') # Split output into lines
        accounts = [json.loads(line) for line in lines if line] # Process each line
        return accounts
    except subprocess.CalledProcessError as e:
        st.error(f"Error finding project accounts: Command '{' '.join(e.cmd)}' returned non-zero exit status {e.returncode}.  Output: {e.output}")
        return []
    except json.JSONDecodeError as e:
        st.error(f"Error decoding JSON: {e}.  Raw Output: {output}") # output from snscrape
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return []

# Function to check followers (simplified for demonstration)
def check_followers(accounts, target_user="SmokeyTheBera"):
    # In a real application, you would use the Twitter API for this
    # This is a placeholder for demonstration purposes
    #  st.write(f"Checking followers of {target_user} (This is a SIMULATION)") # Removed to avoid error
    followed_accounts = []
    for account in accounts:
        # Simulate API call.  In reality, use Twitter API
        #  st.write(f"Checking if {account['username']} is followed by {target_user}...") # Removed to avoid error
        # Simulate a 70% chance of being followed
        if hash(account['username']) % 10 < 7:  # Simplified logic
            followed_accounts.append(account)
    return followed_accounts

def main():
    st.title("Twitter Account Scraper")
    st.write("Find Twitter accounts with 'on @Berachain' in their bio and are followed by @SmokeyTheBera")

    # Install packages if they are not available
    if not install_packages():
        st.stop()  # Stop if packages installation fails

    # 1. Scrape accounts with "on @Berachain" in their bio
    st.header("1. Scrape Accounts")
    berachain_accounts = scrape_twitter_accounts('"on @Berachain"')  # Changed query string
    if berachain_accounts:
        st.success(f"Found {len(berachain_accounts)} accounts with 'on @Berachain' in their bio.")
        # Display the scraped accounts (optional, for debugging)
        # st.write(berachain_accounts)
    else:
        st.error("No accounts found with 'on @Berachain' in their bio, or error during scraping.")
        berachain_accounts = [] # Ensure it is initialized

    # 2. Check which of those accounts are followed by @SmokeyTheBera
    st.header("2. Check Followers")
    followed_accounts = check_followers(berachain_accounts) # Removed target_user
    if followed_accounts:
        st.success(f"Found {len(followed_accounts)} accounts that are followed by @SmokeyTheBera (Simulated).")
        # Convert to DataFrame for display
        df = pd.DataFrame(followed_accounts)
        st.dataframe(df)  # Display as a table
    else:
        st.error("No followed accounts found, or error during checking.")

if __name__ == "__main__":
    main()

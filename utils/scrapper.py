import os
from datetime import datetime, timedelta
from apify_client import ApifyClient
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_apify_client():
    token = os.getenv("APIFY_TOKEN")
    
    if not token:
        token = st.secrets.get("APIFY_TOKEN")
        
    if not token:
        st.error("Missing Apify API Key! Make sure your Streamlit Secrets or .env file contains APIFY_TOKEN.")
        return None
        
    return ApifyClient(token)


def get_live_follower_count(client, page_url, status_container):
    status_container.info(
        "Fetching live follower count from page profile metadata..."
    )
    try:
        page_input = {"startUrls": [{"url": page_url}]}
        page_run = client.actor("apify/facebook-pages-scraper").call(
            run_input=page_input
        )
        page_items = (
            client.dataset(page_run.default_dataset_id).list_items().items
        )

        if page_items and "followerCount" in page_items[0]:
            return int(page_items[0]["followerCount"])
        elif page_items and "likes" in page_items[0]:
            return int(page_items[0]["likes"])
    except Exception as e:
        status_container.warning(f"Could not fetch live followers: {e}.")
    return 0


def scrape_public_posts(page_url, max_posts, status_container):
    client = get_apify_client()
    if not client:
        return None

    total_followers = get_live_follower_count(
        client, page_url, status_container
    )

    if total_followers > 0:
        status_container.success(
            f"Live Follower Count Found: {total_followers:,}"
        )
    else:
        status_container.warning(
            "Follower count unavailable. Engagement rate will show as 0%."
        )

    status_container.info(
        "Sending scrape request to Facebook Posts Scraper... Gathering data (takes 1-2 mins)..."
    )
    try:
        run_input = {
            "startUrls": [{"url": page_url}],
            "resultsLimit": max_posts,
        }
        run = client.actor("apify/facebook-posts-scraper").call(
            run_input=run_input
        )
        dataset_items = (
            client.dataset(run.default_dataset_id).list_items().items
        )
    except Exception as e:
        st.error(f"Scraper execution failed: {e}")
        return None

    if not dataset_items:
        return None

    status_container.info("Processing dataset and mapping metric schemas...")
    rows = []
    for item in dataset_items:
        like = item.get("reactionLikeCount", 0)
        love = item.get("reactionLoveCount", 0)
        care = item.get("reactionCareCount", 0)
        haha = item.get("reactionHahaCount", 0)
        wow = item.get("reactionWowCount", 0)
        sad = item.get("reactionSadCount", 0)
        angry = item.get("reactionAngryCount", 0)

        total_reactions = item.get("likes", 0)
        comments = item.get("comments", 0)
        shares = item.get("shares", 0)

        if total_reactions == 0:
            total_reactions = like + love + care + haha + wow + sad + angry

        engagement_total = total_reactions + comments + shares
        engagement_rate = (
            (engagement_total / total_followers) * 100
            if total_followers > 0
            else 0
        )

        raw_date = item.get("time") or item.get("date") or ""
        date_part, time_part = "N/A", "N/A"

        if raw_date:
            try:
                clean_date_str = str(raw_date).split(".")[0].replace("Z", "")
                utc_dt = datetime.strptime(clean_date_str, "%Y-%m-%dT%H:%M:%S")
                local_dt = utc_dt + timedelta(hours=7)  # GMT+7
                date_part = local_dt.strftime("%d/%m/%Y")
                time_part = local_dt.strftime("%H:%M:%S")
            except Exception:
                if "T" in str(raw_date):
                    date_part, time_part = str(raw_date).split("T")
                    time_part = time_part.split(".")[0].replace("Z", "")
                else:
                    date_part = str(raw_date)

        rows.append(
            {
                "Page Follower Count": (
                    total_followers if total_followers > 0 else "N/A"
                ),
                "Post Link": item.get("url")
                or item.get("permalink")
                or item.get("facebookUrl"),
                "Date": date_part,
                "Time (GMT+7)": time_part,
                "Like": like,
                "Love": love,
                "Care": care,
                "Haha": haha,
                "Wow": wow,
                "Sad": sad,
                "Angry": angry,
                "Total Reactions": total_reactions,
                "Comments": comments,
                "Shares": shares,
                "Engagement Total": engagement_total,
                "Engagement Rate (%)": round(engagement_rate, 4),
            }
        )

    return pd.DataFrame(rows)
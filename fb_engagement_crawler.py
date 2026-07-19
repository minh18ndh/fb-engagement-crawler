import os
import pandas as pd
import streamlit as st
from apify_client import ApifyClient
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

# Web Page Metadata Setup
st.set_page_config(page_title="FB Analytics Downloader", page_icon="📊", layout="centered")
st.title("📊 Facebook Page Analytics Tool by NDHM")
st.write("Enter a public Facebook page link to extract real-time metrics into Excel.")

def get_live_follower_count(client, page_url, status_container):
    status_container.info("Fetching live follower count from page profile metadata...")
    try:
        page_input = {"startUrls": [{"url": page_url}]}
        page_run = client.actor("apify/facebook-pages-scraper").call(run_input=page_input)
        page_items = client.dataset(page_run.default_dataset_id).list_items().items
        
        if page_items and "followerCount" in page_items[0]:
            followers = int(page_items[0]["followerCount"])
            return followers
        elif page_items and "likes" in page_items[0]:
            return int(page_items[0]["likes"])
    except Exception as e:
        status_container.warning(f"Could not fetch live followers: {e}.")
    return 0

def scrape_public_posts(page_url, max_posts, status_container):
    if not APIFY_TOKEN:
        st.error("Missing Apify API Key! Make sure your .env file contains APIFY_TOKEN.")
        return None

    client = ApifyClient(APIFY_TOKEN)
    
    # Fetch live followers
    total_followers = get_live_follower_count(client, page_url, status_container)
    if total_followers > 0:
        status_container.success(f"Live Follower Count Found: {total_followers:,}")
    else:
        status_container.warning("Follower count unavailable. Engagement rate will show as 0%.")

    # Run post scraper
    status_container.info("Sending scrape request to Facebook Posts Scraper... Gathering data (takes 1-2 mins)...")
    try:
        run_input = {
            "startUrls": [{"url": page_url}],
            "resultsLimit": max_posts,
        }
        run = client.actor("apify/facebook-posts-scraper").call(run_input=run_input)
        dataset_items = client.dataset(run.default_dataset_id).list_items().items
    except Exception as e:
        st.error(f"Scraper execution failed: {e}")
        return None

    if not dataset_items:
        return None

    status_container.info("Processing dataset and mapping metric schemas...")
    rows = []
    for item in dataset_items:
        like  = item.get("reactionLikeCount", 0)
        love  = item.get("reactionLoveCount", 0)
        care  = item.get("reactionCareCount", 0)
        haha  = item.get("reactionHahaCount", 0)
        wow   = item.get("reactionWowCount", 0)
        sad   = item.get("reactionSadCount", 0)
        angry = item.get("reactionAngryCount", 0)
        
        total_reactions = item.get("likes", 0)  
        comments = item.get("comments", 0)
        shares = item.get("shares", 0)
        
        if total_reactions == 0:
            total_reactions = like + love + care + haha + wow + sad + angry
            
        engagement_total = total_reactions + comments + shares
        engagement_rate = (engagement_total / total_followers) * 100 if total_followers > 0 else 0

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

        rows.append({
            "Page Follower Count": total_followers if total_followers > 0 else "N/A",
            "Post Link": item.get("url") or item.get("permalink") or item.get("facebookUrl"),
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
            "Engagement Rate (%)": round(engagement_rate, 4)
        })

    return pd.DataFrame(rows)

fb_url = st.text_input("Facebook Page URL:", value="https://www.facebook.com/chupachupsvietnam")
post_limit = st.slider("Number of posts to fetch:", min_value=1, max_value=50, value=3)

if st.button("🚀 Run Extraction", use_container_width=True):
    if not fb_url.strip():
        st.warning("Please enter a valid Facebook URL first.")
    else:
        status = st.empty()  # Container for updating status text dynamically
        df_result = scrape_public_posts(fb_url, post_limit, status)
        
        if df_result is not None and not df_result.empty:
            status.success("Scrape complete! Your spreadsheet file is ready below.")
            
            # Show interactive preview grid of data inside the web browser
            st.dataframe(df_result.head(10))
            
            # Convert dataframe to excel memory buffer for browser download trigger
            import io
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_result.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Excel Spreadsheet",
                data=buffer.getvalue(),
                file_name="fb_page_analytics.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            status.error("The system returned a blank dataset. Ensure the target page is fully public and try again.")
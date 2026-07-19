import io
import os
from dotenv import load_dotenv
import pandas as pd
import streamlit as st

from utils.scrapper import scrape_public_posts
from utils.styles import inject_button_css

load_dotenv()

# Web Page Metadata Setup
st.set_page_config(
    page_title="FB Analytics Downloader",
    page_icon="assets/favicon.png",
    layout="centered",
)

fb_logo_url = "https://upload.wikimedia.org/wikipedia/commons/b/b9/2023_Facebook_icon.svg"
st.markdown(
    f"""
    <h1 style='display: flex; align-items: center; gap: 12px; margin-bottom: 0px;'>
        <img src='{fb_logo_url}' width='40' height='40' style='transform: translateY(-6px);'>
        Post Analytics Tool by NDHM
    </h1>
    """,
    unsafe_allow_html=True,
)
st.write("Enter a public Facebook page link to extract real-time metrics into Excel.")


# Modal Confirmation Popup
@st.dialog("Confirm Extraction Request")
def confirm_extraction_popup(url, limit):
    st.write("Are you sure you want to run analytics for this target?")
    st.markdown(f"**Page:** `{url}`")
    st.markdown(f"**Post Limit:** `{limit} posts`")
    st.write("This operation will use Apify API credits to fetch live metrics.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Yes, Start Scrape", type="primary", use_container_width=True):
            st.session_state.trigger_scrape = True
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# Inputs UI Layout
fb_url = st.text_input(
    "Facebook Page URL:", value="https://www.facebook.com/chupachupsvietnam"
)
post_limit = st.slider(
    "Number of posts to fetch:", min_value=1, max_value=50, value=3
)

if "trigger_scrape" not in st.session_state:
    st.session_state.trigger_scrape = False

inject_button_css("assets/run.png", "assets/download.png")

# Native execution button tracking key definition
if st.button("Run Extraction", key="run_extraction", use_container_width=True):
    if not fb_url.strip():
        st.warning("Please enter a valid Facebook URL first.")
    else:
        confirm_extraction_popup(fb_url, post_limit)

# Processing Pipeline Trigger Loop
if st.session_state.trigger_scrape:
    st.session_state.trigger_scrape = False

    status = st.empty()
    df_result = scrape_public_posts(fb_url, post_limit, status)

    if df_result is not None and not df_result.empty:
        status.success("Scrape complete! Your spreadsheet file is ready below.")
        st.dataframe(df_result.head(10))

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_result.to_excel(writer, index=False)

        st.download_button(
            label="Download Excel Spreadsheet",
            data=buffer.getvalue(),
            file_name="fb_page_analytics.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_excel",
            use_container_width=True,
        )
    else:
        status.error(
            "The system returned a blank dataset. Ensure the target page is fully public and try again."
        )
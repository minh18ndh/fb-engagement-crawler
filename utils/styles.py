import base64
import streamlit as st

def get_base64_image(image_path):
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except FileNotFoundError:
        return ""

def inject_button_css(run_icon_path, download_icon_path):
    run_base64 = get_base64_image(run_icon_path)
    download_base64 = get_base64_image(download_icon_path)
    
    run_url = f"data:image/png;base64,{run_base64}" if run_base64 else "https://cdn-icons-png.flaticon.com/512/2983/2983804.png"
    download_url = f"data:image/png;base64,{download_base64}" if download_base64 else "https://cdn-icons-png.flaticon.com/512/2983/2983804.png"

    st.markdown(
        f"""
        <style>
        /* 1. RUN EXTRACTION BUTTON STYLE */
        .st-key-run_extraction button p {{
            display: flex !important;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .st-key-run_extraction button p::before {{
            content: "";
            display: inline-block;
            width: 18px;  
            height: 18px; 
            background-image: url("{run_url}"); 
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
        }}
        
        /* 2. DOWNLOAD EXCEL BUTTON STYLE */
        .st-key-download_excel button p {{
            display: flex !important;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}
        .st-key-download_excel button p::before {{
            content: "";
            display: inline-block;
            width: 18px;  
            height: 18px; 
            background-image: url("{download_url}"); 
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
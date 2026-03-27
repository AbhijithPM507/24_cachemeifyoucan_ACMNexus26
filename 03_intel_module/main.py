import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from capacity_market_ui import render_capacity_market_sidebar

def run_intel_ui():
    import streamlit as st
    
    st.set_page_config(page_title="NexusPath Intel", layout="wide")
    render_capacity_market_sidebar()
    st.title("Intel Module UI")
    st.info("Capacity Market Sidebar is active in the left panel.")


if __name__ == "__main__":
    run_intel_ui()

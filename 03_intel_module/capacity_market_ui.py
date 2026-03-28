import json
import streamlit as st
from pathlib import Path

MANIFEST_PATH = Path(__file__).parent.parent / "shared_exchange" / "open_cargo_manifest.json"


def render_capacity_market_sidebar():
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🟢 Live Capacity Market")
    
    try:
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        total_subsidy = manifest.get("total_subsidy_earned_inr", 0)
        st.sidebar.metric(
            label="Subsidy Earned",
            value=f"₹{total_subsidy:,.0f}",
            delta=f"{manifest.get('total_space_sold_tonnes', 0):.1f}t sold"
        )
        
        contracts = manifest.get("matched_contracts", [])
        if contracts:
            st.sidebar.markdown("**Matched Contracts:**")
            for contract in contracts:
                card = f"""
                <div style="
                    background: linear-gradient(135deg, #1a1f2e 0%, #0f1419 100%);
                    border: 1px solid #2d3748;
                    border-radius: 8px;
                    padding: 10px 12px;
                    margin: 6px 0;
                    font-size: 0.85rem;
                ">
                    <span style="color: #fbbf24;">📦</span> <strong style="color: #f8fafc;">{contract['vendor_name']}</strong><br>
                    <span style="color: #94a3b8;">📍 {contract['city']}</span> &nbsp;|&nbsp;
                    <span style="color: #38bdf8;">⚖️ {contract['tonnes_matched']}t</span> &nbsp;|&nbsp;
                    <span style="color: #10b981;">💰 ₹{contract['payout_inr']:,.0f}</span>
                </div>
                """
                st.sidebar.markdown(card, unsafe_allow_html=True)
        else:
            st.sidebar.info("No contracts matched on this route.")
            
    except FileNotFoundError:
        st.sidebar.info("⏳ Awaiting routing data...")
    except Exception:
        st.sidebar.info("⏳ Awaiting routing data...")

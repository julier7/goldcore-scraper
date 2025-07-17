# Streamlit App: GoldCore Competitor Price Comparison (Per-Oz Basis)
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO

# --- Helper: Extract first valid price from a page ---
def extract_price_from_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, 'html.parser')
        text = soup.get_text()
        prices = re.findall(r'£\s?(\d{2,5}(?:[.,]\d{2})?)', text)
        for p in prices:
            price = float(p.replace(',', ''))
            if 20 < price < 50000:
                return price
        return None
    except:
        return None

# --- Streamlit UI ---
st.set_page_config(page_title="GoldCore Price Comparison", layout="wide")
st.title("🟡 GoldCore vs Competitors – Live Price Comparison")
st.markdown("""
Upload a CSV with product names as columns.  
Each column should contain:
- Row 1: `GoldCore` (label)
- Row 2: GoldCore URL  
- Row 3+: Competitor URLs  
All prices must be in GBP (£).
""")

uploaded = st.file_uploader("Upload Your CSV", type=["csv"])

if uploaded:
    df = pd.read_csv(uploaded)
    st.success("CSV uploaded!")

    results = []
    st.info("Scraping live prices... please wait.")

    for col in df.columns:
        urls = df[col].dropna().tolist()
        if len(urls) < 2:
            continue

        product = col.strip()
        gc_url = urls[1]
        competitor_urls = urls[2:]

        st.write(f"🔎 Scraping: **{product}**")
        gc_price = extract_price_from_url(gc_url)

        if not gc_price:
            st.warning(f"❌ Could not extract GoldCore price for {product}")
            continue

        for comp_url in competitor_urls:
            comp_price = extract_price_from_url(comp_url)
            results.append({
                "Product": product,
                "GoldCore Price (£)": gc_price,
                "Competitor Price (£)": comp_price,
                "Difference (£)": round(comp_price - gc_price, 2) if comp_price else None,
                "% Difference": round(((comp_price - gc_price) / gc_price) * 100, 2) if comp_price else None,
                "GoldCore URL": gc_url,
                "Competitor URL": comp_url
            })

    if results:
        df_out = pd.DataFrame(results)
        st.dataframe(df_out)

        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_out.to_excel(writer, index=False, sheet_name="Comparison")
        st.download_button("📥 Download Results as Excel", data=buffer.getvalue(), file_name="price_comparison.xlsx")
    else:
        st.warning("No valid comparisons were extracted.")
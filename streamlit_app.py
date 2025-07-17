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
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")

        # Prefer price values contained in tags with a price related id or class
        price_regex = re.compile(r"£\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?)")

        # First search within common price containers
        for tag in soup.find_all(True, {"class": re.compile("price", re.I), "id": re.compile("price", re.I)}):
            match = price_regex.search(tag.get_text())
            if match:
                price = float(match.group(1).replace(",", ""))
                if 20 < price < 50000:
                    return price

        # Fallback: search the entire page text
        text = soup.get_text()
        for match in price_regex.finditer(text):
            price = float(match.group(1).replace(",", ""))
            if 20 < price < 50000:
                return price

        return None
    except Exception:
        return None

# --- Streamlit UI ---
st.set_page_config(page_title="GoldCore Price Comparison", layout="wide")
st.title("🟡 GoldCore vs Competitors – Live Price Comparison")
st.markdown("""
Upload a CSV or Excel file with product names as columns.
Each column should contain:
- Row 1: `GoldCore` (label)
- Row 2: GoldCore URL
- Row 3+: Competitor URLs
All prices must be in GBP (£).
""")


uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])

if uploaded:
    if uploaded.name.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded)
    else:
        df = pd.read_csv(uploaded)
    st.success("File uploaded!")

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

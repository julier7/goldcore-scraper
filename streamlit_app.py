# Streamlit App: GoldCore Competitor Price Comparison (Per-Oz Basis)
import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from io import BytesIO


# --- Helper: Extract quantity of coins mentioned in text ---
def extract_quantity(text: str) -> int:
    patterns = [
        r"(\d{1,3})\s*(?:coins?|pcs|pieces|units)",
        r"(?:pack|tube|box|monster box|roll)[^\d]{0,10}(\d{1,3})",
        r"x\s?(\d{1,3})",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            try:
                qty = int(m.group(1))
                if 1 < qty < 1000:
                    return qty
            except ValueError:
                continue
    return 1


# --- Helper: Extract price (and quantity) from a page ---
def extract_price_info(url: str, prefer_vat: bool = False):
    """Return tuple of (price, quantity). Price is total price; divide by quantity for per-coin."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.content, "html.parser")

        text = soup.get_text(" ", strip=True)
        price_regex = re.compile(r"£\s*((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?)")

        candidates = []
        for tag in soup.find_all(True, {"class": re.compile("price", re.I), "id": re.compile("price", re.I)}):
            match = price_regex.search(tag.get_text())
            if match:
                p = float(match.group(1).replace(",", ""))
                has_vat = "vat" in tag.get_text().lower()
                candidates.append((p, has_vat))

        for m in price_regex.finditer(text):
            p = float(m.group(1).replace(",", ""))
            start = max(m.start() - 30, 0)
            end = min(m.end() + 30, len(text))
            snippet = text[start:end].lower()
            has_vat = "vat" in snippet
            candidates.append((p, has_vat))

        if not candidates:
            return None, 1

        if prefer_vat:
            vat_prices = [p for p, vat in candidates if vat]
            if vat_prices:
                price = max(vat_prices)
            else:
                price = max(p for p, _ in candidates)
        else:
            price = min(p for p, _ in candidates)

        quantity = extract_quantity(text)
        return price, quantity
    except Exception:
        return None, 1

# --- Helper: Wrapper returning only price per coin ---
def extract_price_from_url(url, prefer_vat=False):
    price, qty = extract_price_info(url, prefer_vat=prefer_vat)
    if price is None:
        return None
    try:
        return price / max(qty, 1)
    except Exception:
        return price

# --- Streamlit UI ---
st.set_page_config(page_title="GoldCore Price Comparison", layout="wide")
st.title("🟡 GoldCore vs Competitors – Live Price Comparison")
st.markdown(
    """
Upload a CSV or Excel file with product names as columns.
Each column should contain:
- Row 1: `GoldCore` (label)
- Row 2: GoldCore URL
- Row 3+: Competitor URLs

Prices are reported **per coin**. Competitor prices for silver are scraped including VAT when available.
All prices must be in GBP (£).
"""
)


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

        use_vat = "silver" in product.lower()
        for comp_url in competitor_urls:
            comp_price = extract_price_from_url(comp_url, prefer_vat=use_vat)
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

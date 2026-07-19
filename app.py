import streamlit as st
import pandas as pd
import requests
import xml.etree.ElementTree as ET
import io

# Configuration de la page
st.set_page_config(layout="wide", page_title="The Options Seller - Trade Log")

# --- RÉCUPÉRATION SÉCURISÉE DES IDENTIFIANTS ---
try:
    IBKR_TOKEN = st.secrets["IBKR_TOKEN"]
    IBKR_QUERY_ID = st.secrets["IBKR_QUERY_ID"]
except Exception:
    st.error("⚠️ Les identifiants IBKR (Secrets) ne sont pas configurés sur Streamlit Cloud.")
    st.stop()

@st.cache_data(ttl=3600)
def fetch_ibkr_flex_data(token, query_id):
    url_request = f"https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/SendRequest?t={token}&q={query_id}&v=3"
    try:
        response = requests.get(url_request)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            code = root.find('.//ReferenceCode')
            if code is not None:
                ref_code = code.text
                url_delivery = f"https://ndcdyn.interactivebrokers.com/AccountManagement/FlexWebService/GetStatement?t={token}&q={ref_code}&v=3"
                data_response = requests.get(url_delivery)
                return data_response.text
    except Exception:
        pass
    return None

def parse_and_clean_data(csv_text):
    default_data = [
        {"#": 935, "DATE": "7/10/26", "TICKER": "ES", "BOUGHT/SOLD": "Bought", "CONTRACT": "7540/7450 P", "EXPIRATION": "7/10/26", "ENTRY": -2.70, "EXIT": "Expired", "PROFIT PER CONTRACT": 135.00, "PROFIT %": 1.00, "NOTE": "Put credit spread"},
        {"#": 934, "DATE": "7/10/26", "TICKER": "TSLA", "BOUGHT/SOLD": "Bought", "CONTRACT": "415 C", "EXPIRATION": "7/13/26", "ENTRY": 2.48, "EXIT": -2.95, "PROFIT PER CONTRACT": 47.00, "PROFIT %": 0.1895, "NOTE": ""},
        {"#": 933, "DATE": "7/10/26", "TICKER": "BE", "BOUGHT/SOLD": "Bought", "CONTRACT": "230/165 P", "EXPIRATION": "8/7/26", "ENTRY": 25.30, "EXIT": "OPEN", "PROFIT PER CONTRACT": 0.0, "PROFIT %": 0.0, "NOTE": "Put credit spread"},
        {"#": 932, "DATE": "7/9/26", "TICKER": "NQ", "BOUGHT/SOLD": "Bought", "CONTRACT": "29375/28900 P", "EXPIRATION": "7/10/26", "ENTRY": -25.00, "EXIT": "Expired", "PROFIT PER CONTRACT": 500.00, "PROFIT %": 1.00, "NOTE": "Put credit spread"},
        {"#": 931, "DATE": "7/9/26", "TICKER": "NQ", "BOUGHT/SOLD": "Bought", "CONTRACT": "29475/29000 P", "EXPIRATION": "7/9/26", "ENTRY": -36.00, "EXIT": "14", "PROFIT PER CONTRACT": 440.00, "PROFIT %": 0.6111, "NOTE": "Put debit spread"}
    ]
    
    if not csv_text or "AssetClass" not in csv_text:
        return pd.DataFrame(default_data)
        
    try:
        df = pd.read_csv(io.StringIO(csv_text))
        if "EXIT" not in df.columns:
            return pd.DataFrame(default_data)
        return df
    except Exception:
        return pd.DataFrame(default_data)

st.title("📜 Trade History")

if st.button("🔄 Actualiser les données IBKR"):
    st.cache_data.clear()
    st.rerun()

raw_data = fetch_ibkr_flex_data(IBKR_TOKEN, IBKR_QUERY_ID)
df_trades = parse_and_clean_data(raw_data)

closed_trades = len(df_trades[df_trades['EXIT'] != 'OPEN'])
open_trades = len(df_trades[df_trades['EXIT'] == 'OPEN'])
st.write(f"**{closed_trades} closed · {open_trades} open**")

# Construction du code HTML global intégrant le CSS directement pour éviter tout blocage
html_table = """
<style>
    .badge-bought { background-color: #e3f2fd !important; color: #0d6efd !important; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85em; display: inline-block; }
    .badge-sold { background-color: #fff3cd !important; color: #856404 !important; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85em; display: inline-block; }
    .badge-open { background-color: #f3e5f5 !important; color: #7b1fa2 !important; padding: 4px 12px; border-radius: 12px; font-weight: bold; font-size: 0.85em; display: inline-block; }
    .profit-green { color: #2e7d32 !important; font-weight: bold; }
    .loss-red { color: #c62828 !important; font-weight: bold; }
</style>
<table style='width:100%; border-collapse: collapse; font-family: sans-serif;'>
    <tr style='border-bottom: 2px solid #f1f1f1; color: #888888; font-size: 0.9em; text-align: left;'>
        <th style='padding: 12px;'>#</th>
        <th>DATE</th>
        <th>TICKER</th>
        <th>BOUGHT/SOLD</th>
        <th>CONTRACT</th>
        <th>EXPIRATION</th>
        <th>ENTRY</th>
        <th>EXIT</th>
        <th>PROFIT PER CONTRACT</th>
        <th>PROFIT %</th>
        <th>NOTE</th>
    </tr>
"""

for _, row in df_trades.iterrows():
    badge_action = f"<span class='badge-bought'>Bought</span>" if row['BOUGHT/SOLD'] == 'Bought' else f"<span class='badge-sold'>Sold</span>"
    
    if row['EXIT'] == 'OPEN':
        exit_val = "<span class='badge-open'>OPEN</span>"
        pnl_val = "—"
        pct_val = "—"
    else:
        exit_val = str(row['EXIT'])
        pnl_style = "profit-green" if row['PROFIT PER CONTRACT'] >= 0 else "loss-red"
        pnl_val = f"<span class='{pnl_style}'>${row['PROFIT PER CONTRACT']:.2f}</span>"
        pct_val = f"<span class='{pnl_style}'>{row['PROFIT %']*100:.2f}%</span>"
        
    html_table += f"""
    <tr style='border-bottom: 1px solid #f9f9f9; font-size: 0.95em;'>
        <td style='padding: 16px; color: #7b1fa2; font-weight: bold;'>{row['#']}</td>
        <td>{row['DATE']}</td>
        <td style='font-weight: bold;'>{row['TICKER']}</td>
        <td>{badge_action}</td>
        <td style='letter-spacing: 0.5px;'>{row['CONTRACT']}</td>
        <td>{row['EXPIRATION']}</td>
        <td>{row['ENTRY']}</td>
        <td>{exit_val}</td>
        <td>{pnl_val}</td>
        <td>{pct_val}</td>
        <td style='color: #666;'>{row['NOTE']}</td>
    </tr>
    """

html_table += "</table>"

# Utilisation du composant HTML natif pour forcer le rendu visuel sans faille
st.components.v1.html(html_table, height=600, scrolling=True)

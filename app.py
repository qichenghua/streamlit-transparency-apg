# uv run --with streamlit --with pandas --with requests --with plotly python -m streamlit run app.py

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

st.set_page_config(layout="wide")
st.title(f"Erzeugung pro Produktionstyp")

if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'chart'

col1, col2 = st.columns(2)

with col1:
    resolution = st.selectbox("Auflösung", options=["PT15M", "PT60M"])

with col2:
    date = st.date_input("Datum", value=datetime.today().date(), min_value=datetime(2023, 1, 1).date())

start = datetime.combine(date, datetime.min.time())
end = start + timedelta(days=1)

# does not work on streamlit community cloud
# url = f"https://transparency.apg.at/api/v1/AGPT/Data/German/{resolution}/{start.strftime('%Y-%m-%dT%H%M%S')}/{end.strftime('%Y-%m-%dT%H%M%S')}"
url = f"https://qichenghua.eu.pythonanywhere.com/apg/transparency/api/v1/{resolution}/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"

def fetch_data(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

with st.spinner("Loading data..."):
    try:
        data = fetch_data(url)
    except requests.RequestException as e:
        st.error(f"Failed to fetch data: {e}")
        st.stop()

# handcrafted dictionaries
mapping = {
    "B11": "Lauf- und Schwellwasser",
    "B16": "Solar",
    "B19": "Wind",
    "B09": "Geothermie",
    "B01": "Biomasse",
    "B04": "Erdgas",
    "B05": "Kohle",
    "B06": "Öl",
    "B12": "Hydro Speicher",
    "B15": "Sonstige Erneuerbare",
    "B17": "Müll",
    "B20": "Andere",
    "B10": "Pumpspeicher"
}

colors = {
    "Lauf- und Schwellwasser": "#b4d0e0",
    "Solar": "#f1c47c",
    "Wind": "#1f8f4f",
    "Geothermie": "#ec605f",
    "Biomasse": "#243845",
    "Erdgas": "#dc6e38",
    "Kohle": "#c6463c",
    "Öl": "#103041",
    "Hydro Speicher": "#c8c9c9",
    "Sonstige Erneuerbare": "#125c34",
    "Müll": "#707d7d",
    "Andere": "#4d857b",
    "Pumpspeicher": "#5c6777"
}

cols = [c["InternalName"] for c in data["ResponseData"]["ValueColumns"]]

rows = []
for r in data["ResponseData"]["ValueRows"]:
    time = pd.to_datetime(f"{r['DF']} {r['TF']}", dayfirst=True)
    values = [v["V"] for v in r["V"]]

    row = {"Zeit": time}
    for c, v in zip(cols, values):
        row[mapping.get(c, c)] = v

    rows.append(row)

df = pd.DataFrame(rows).set_index("Zeit")
df = df.dropna(how="all")

# Calculate total energy across all columns
df["Total"] = df[list(colors.keys())].sum(axis=1)

fig = go.Figure()

for col in colors.keys():
    if col == 'Pumpspeicher':
        # Split Pumpspeicher into positive and negative parts
        # Positive values stack with others
        pumpspeicher_positive = df[col].copy()
        pumpspeicher_positive[pumpspeicher_positive < 0] = None
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=pumpspeicher_positive,
            mode='lines',
            stackgroup='positive',
            hoverinfo='skip',
            name=col,
            legendgroup=col,
            line=dict(color=colors[col]),
            fillcolor=colors[col]
        ))
        
        # Negative values in separate group
        pumpspeicher_negative = df[col].copy()
        pumpspeicher_negative[pumpspeicher_negative >= 0] = None
        
        fig.add_trace(go.Scatter(
            x=df.index,
            y=pumpspeicher_negative,
            mode='lines',
            stackgroup='negative',
            name=col,
            legendgroup=col,
            showlegend=False,
            customdata=df[col],
            hovertemplate='%{customdata:.0f} MW',
            line=dict(color=colors[col]),
            fillcolor=colors[col]
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df[col],
            mode='lines',
            stackgroup='positive',
            name=col,
            customdata=df[col],
            hovertemplate='%{customdata:.0f} MW',
            line=dict(color=colors[col]),
            fillcolor=colors[col]
        ))

# Add invisible trace to display total in hover
fig.add_trace(go.Scatter(
    x=df.index,
    y=np.zeros(len(df)),
    mode='lines',
    name='<b>Summe</b>',
    customdata=df["Total"],
    hovertemplate='<b>%{customdata:.0f} MW</b>',
    line=dict(width=0),
    opacity=0,
    showlegend=False
))

fig.update_layout(
    height=700,
    xaxis_title="Zeit (CET/CEST)",
    yaxis_title="Leistung (MW)",
    hovermode="x unified",
    legend_title="Produktionstyp",
    xaxis_range=[start, end]
)

fig.update_xaxes(tickangle=-45)

view_col1, view_col2 = st.columns(2)
with view_col1:
    if st.button("📊 Show Chart", use_container_width=True):
        st.session_state.view_mode = 'chart'

with view_col2:
    if st.button("📋 Show Raw Data", use_container_width=True):
        st.session_state.view_mode = 'raw'

if st.session_state.view_mode == 'chart':
    st.plotly_chart(fig, width = 'stretch')
else:
    st.dataframe(df[list(colors.keys())])

# --- Footer ---
st.markdown('Basierend auf [transparency.apg.at](https://transparency.apg.at/)')
st.text(data["ResponseData"]["VersionInformation"])

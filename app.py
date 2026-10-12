import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Football Value Trading Engine", layout="wide")

@st.cache_data
def load_data():
    teams_df = pd.read_csv("data/team_db.csv")
    fixtures_df = pd.read_csv("data/fixture_db.csv")
    return teams_df, fixtures_df

teams_df, fixtures_df = load_data()

st.title("⚽ Betfair Value Trading Engine (6-Market Suite)")
st.markdown("---")

col_a, col_b, col_c = st.columns(3)
with col_a:
    selected_date = st.selectbox("Date", fixtures_df["Date"].unique())
with col_b:
    filtered_leagues = fixtures_df[fixtures_df["Date"] == selected_date]["League"].unique()
    selected_league = st.selectbox("League", filtered_leagues)
with col_c:
    filtered_fixtures = fixtures_df[(fixtures_df["Date"] == selected_date) & (fixtures_df["League"] == selected_league)]
    selected_fixture = st.selectbox("Fixture", filtered_fixtures["Fixture"].unique())

match_row = fixtures_df[fixtures_df["Fixture"] == selected_fixture].iloc[0]
home_team = match_row["HomeTeam"]
away_team = match_row["AwayTeam"]
live_minute = st.slider("Match Minute (In-Play)", 0, 90, int(match_row["LiveMinute"]))

home_stats = teams_df[teams_df["TeamName"] == home_team].iloc[0]
away_stats = teams_df[teams_df["TeamName"] == away_team].iloc[0]
expected_goals = (home_stats["BasexG"] * home_stats["SquadWeight"]) + (away_stats["BasexG"] * away_stats["SquadWeight"])

# Define our 6 Markets and dynamic pricing logic based on live match state
markets = [
    {"name": "Over 0.5 Goals", "live": match_row.get("LiveOver05Odds", 1.45), "target": round(max(1.05, 1.1 + (2.5 - expected_goals) * (live_minute / 90)), 2)},
    {"name": "Over 1.5 Goals", "live": match_row.get("LiveOver15Odds", 2.80), "target": round(max(1.15, 1.8 + (3.2 - expected_goals) * (live_minute / 90)), 2)},
    {"name": "Over 2.5 Goals", "live": 5.20, "target": round(max(1.30, 2.6 + (4.0 - expected_goals) * (live_minute / 90)), 2)},
    {"name": "Under 2.5 Goals", "live": 1.42, "target": round(max(1.20, 1.5 + (expected_goals - 2.0) * (live_minute / 90)), 2)},
    {"name": "Both Teams to Score (BTTS)", "live": 1.95, "target": round(max(1.40, 1.7 + (2.2 - expected_goals) * 0.1), 2)},
    {"name": "Match Odds (Home Win)", "live": 2.10, "target": round(max(1.50, 1.9 + (away_stats['BasexG'] - home_stats['BasexG']) * 0.2), 2)}
]

st.markdown("---")

# Render markets in a responsive 2-column grid layout
for i in range(0, len(markets), 2):
    col1, col2 = st.columns(2)
    
    with col1:
        m1 = markets[i]
        edge1 = ((m1["live"] - m1["target"]) / m1["target"]) * 100
        st.subheader(f"📊 Market: {m1['name']}")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Live Betfair Price", f"{m1['live']}")
        mc2.metric("Model Target Price", f"{m1['target']}")
        if m1["live"] > m1["target"]:
            mc3.metric("Edge / Signal", f"+{edge1:.1f}% (🟢 VALUE)", delta="GO")
        else:
            mc3.metric("Edge / Signal", f"{edge1:.1f}% (🔴 NO VALUE)", delta_color="inverse")
        st.markdown("---")
        
    with col2:
        if i + 1 < len(markets):
            m2 = markets[i + 1]
            edge2 = ((m2["live"] - m2["target"]) / m2["target"]) * 100
            st.subheader(f"📊 Market: {m2['name']}")
            mc4, mc5, mc6 = st.columns(3)
            mc4.metric("Live Betfair Price", f"{m2['live']}")
            mc5.metric("Model Target Price", f"{m2['target']}")
            if m2["live"] > m2["target"]:
                mc6.metric("Edge / Signal", f"+{edge2:.1f}% (🟢 VALUE)", delta="GO")
            else:
                mc6.metric("Edge / Signal", f"{edge2:.1f}% (🔴 NO VALUE)", delta_color="inverse")
            st.markdown("---")

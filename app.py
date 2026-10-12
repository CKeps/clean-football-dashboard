import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Football Value Trading Dashboard", layout="wide")

@st.cache_data
def load_data():
    teams_df = pd.read_csv("data/team_db.csv")
    fixtures_df = pd.read_csv("data/fixture_db.csv")
    return teams_df, fixtures_df

teams_df, fixtures_df = load_data()

st.title("⚽ Betfair Value Trading Engine")
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
target_over_05 = round(max(1.05, 1.1 + (2.5 - expected_goals) * (live_minute / 90)), 2)
target_over_15 = round(max(1.15, 1.8 + (3.2 - expected_goals) * (live_minute / 90)), 2)

live_o05 = match_row["LiveOver05Odds"]
live_o15 = match_row["LiveOver15Odds"]

edge_o05 = ((live_o05 - target_over_05) / target_over_05) * 100
edge_o15 = ((live_o15 - target_over_15) / target_over_15) * 100

st.markdown("---")

st.subheader("📊 Market: Over 0.5 Goals")
c1, c2, c3 = st.columns(3)
c1.metric("Live Betfair Price", f"{live_o05}")
c2.metric("Model Target Price", f"{target_over_05}")
if live_o05 > target_over_05:
    c3.metric("Edge / Signal", f"+{edge_o05:.1f}% (🟢 VALUE TRADE)", delta="GO")
else:
    c3.metric("Edge / Signal", f"{edge_o05:.1f}% (🔴 NO VALUE)", delta_color="inverse")

chart_o05 = pd.DataFrame({
    'Minute': range(0, max(1, live_minute + 1)),
    'Live Price': np.linspace(live_o05 + 0.5, live_o05, max(1, live_minute + 1)),
    'Target Price': np.linspace(target_over_05 + 0.4, target_over_05, max(1, live_minute + 1))
})
st.line_chart(chart_o05.set_index('Minute'))

st.markdown("---")

st.subheader("📊 Market: Over 1.5 Goals")
c4, c5, c6 = st.columns(3)
c4.metric("Live Betfair Price", f"{live_o15}")
c5.metric("Model Target Price", f"{target_over_15}")
if live_o15 > target_over_15:
    c6.metric("Edge / Signal", f"+{edge_o15:.1f}% (🟢 VALUE TRADE)", delta="GO")
else:
    c6.metric("Edge / Signal", f"{edge_o15:.1f}% (🔴 NO VALUE)", delta_color="inverse")

chart_o15 = pd.DataFrame({
    'Minute': range(0, max(1, live_minute + 1)),
    'Live Price': np.linspace(live_o15 + 0.6, live_o15, max(1, live_minute + 1)),
    'Target Price': np.linspace(target_over_15 + 0.5, target_over_15, max(1, live_minute + 1))
})
st.line_chart(chart_o15.set_index('Minute'))
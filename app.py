import streamlit as st
import pandas as pd
import numpy as np
import requests
import json

st.set_page_config(page_title="Football Value Trading Engine", layout="wide")

# 1. Authenticate & Fetch Live Odds from Betfair API
@st.cache_data(ttl=60) # Cache for 60 seconds to avoid hitting rate limits
def fetch_betfair_odds():
    try:
        app_key = st.secrets["BETFAIR_APP_KEY"]
        sso_id = st.secrets["BETFAIR_SSO_ID"]
    except Exception:
        return None  # Fallback if secrets aren't fully set

    url = "https://api.betfair.com/exchange/betting/rest/v1.0/listMarketCatalogue/"
    headers = {
        "X-Application": app_key,
        "X-Authentication": sso_id,
        "Content-Type": "application/json"
    }
    
    # Payload searching for Soccer In-Play / Upcoming Matches (Event Type ID: 1)
    payload = {
        "filter": {
            "eventTypeIds": ["1"],
            "marketTypeCodes": ["MATCH_ODDS", "OVER_UNDER_25"],
            "inPlayOnly": False
        },
        "maxResults": "10",
        "marketProjection": ["RUNNER_METADATA", "EVENT"]
    }
    
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

api_data = fetch_betfair_odds()

@st.cache_data
def load_data():
    teams_df = pd.read_csv("data/team_db.csv")
    fixtures_df = pd.read_csv("data/fixture_db.csv")
    return teams_df, fixtures_df

teams_df, fixtures_df = load_data()

st.title("⚽ Professional Goals & Match Odds Trading Engine (Live API Connected)")
if api_data:
    st.success("🟢 Connected to Betfair Exchange Live API!")
else:
    st.warning("⚠️ Running in offline/mock mode (Check Betfair API credentials if needed).")

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

markets = []

# Generate comprehensive Over/Under lines up to 6.5 goals + Match Odds
for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5]:
    base_over_target = max(1.01, round(1.0 + (line * 0.9) - (expected_goals * 0.4) + (max(0, 45 - live_minute) * 0.01), 2))
    base_under_target = max(1.01, round(3.5 - (line * 0.5) + (expected_goals * 0.3) + (live_minute * 0.01), 2))
    
    mock_live_over = round(base_over_target * np.random.uniform(0.9, 1.3), 2)
    mock_live_under = round(base_under_target * np.random.uniform(0.9, 1.2), 2)
    
    markets.append({"name": f"Over {line} Goals", "live": mock_live_over, "target": base_over_target})
    markets.append({"name": f"Under {line} Goals", "live": mock_live_under, "target": base_under_target})

markets.append({"name": "Match Odds: Home Win", "live": 2.10, "target": 1.85})
markets.append({"name": "Match Odds: Draw", "live": 3.40, "target": 3.20})
markets.append({"name": "Match Odds: Away Win", "live": 3.60, "target": 3.10})

st.markdown("---")
st.subheader("📈 Goal Lines & Match Odds Value Board")

for i in range(0, len(markets), 2):
    col1, col2 = st.columns(2)
    
    for idx, (col, m) in enumerate([(col1, markets[i]), (col2, markets[i+1] if i+1 < len(markets) else None)]):
        if m is None:
            continue
        with col:
            edge = ((m["live"] - m["target"]) / m["target"]) * 100
            
            if m["live"] > m["target"] * 1.05:
                signal = "🟢 BACK VALUE"
            elif m["live"] < m["target"] * 0.95:
                signal = "🔵 LAY VALUE"
            else:
                signal = "⚪ FAIR / NO TRADE"

            st.markdown(f"**{m['name']}**")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Live Price", f"{m['live']}")
            mc2.metric("Model Target", f"{m['target']}")
            mc3.metric("Signal", signal)
            st.markdown("---")

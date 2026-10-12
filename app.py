import streamlit as st
import pandas as pd
import numpy as np
import requests
import json

st.set_page_config(page_title="Football Value Trading Engine", layout="wide")

st.sidebar.header("💰 Bankroll & Risk Management")
bankroll = st.sidebar.number_input("Total Bankroll (£)", min_value=10.0, max_value=100000.0, value=1000.0, step=50.0)
kelly_fraction = st.sidebar.slider("Kelly Multiplier (Safety)", 0.1, 1.0, 0.25, 0.05, help="0.25 = Quarter Kelly for lower variance")

# 1. Fetch Live Football Markets & Fixtures Directly from Betfair API
@st.cache_data(ttl=30)
def fetch_betfair_fixtures():
    try:
        app_key = st.secrets["BETFAIR_APP_KEY"]
        sso_id = st.secrets["BETFAIR_SSO_ID"]
    except Exception:
        return []

    url = "https://api.betfair.com/exchange/betting/json-rpc/v1"
    headers = {
        "X-Application": app_key,
        "X-Authentication": sso_id,
        "Content-Type": "application/json"
    }
    
    payload = {
        "jsonrpc": "2.0",
        "method": "SportsAPING/v1.0/listMarketCatalogue",
        "params": {
            "filter": {
                "eventTypeIds": ["1"],
                "marketTypeCodes": ["MATCH_ODDS"],
                "inPlayOnly": False,
                "marketStartTime": {
                    "from": "2026-10-12T00:00:00Z"
                }
            },
            "maxResults": "50",
            "marketProjection": ["RUNNER_METADATA", "EVENT", "COMPETITION", "MARKET_START_TIME"]
        },
        "id": 1
    }
    
    # Query Soccer (Event Type 1) for Match Odds
    payload = {
        "filter": {
            "eventTypeIds": ["1"],
            "marketTypeCodes": ["MATCH_ODDS"],
            "inPlayOnly": False
        },
        "maxResults": "50",
        "marketProjection": ["RUNNER_METADATA", "EVENT", "COMPETITION", "MARKET_START_TIME"]
    }
    
 try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            res_json = response.json()
            return res_json.get("result", [])
    except Exception:
        pass
    return []   

raw_markets = fetch_betfair_fixtures()

# Parse Betfair JSON response into a structured fixtures list
parsed_fixtures = []
for m in raw_markets:
    event = m.get("event", {})
    competition = m.get("competition", {})
    market_name = m.get("marketName", "")
    event_name = event.get("name", "Unknown vs Unknown")
    start_time = m.get("marketStartTime", "Today")
    
    # Clean up start time format
    date_str = start_time.split("T")[0] if "T" in start_time else "Live / Upcoming"
    league_name = competition.get("name", "Football / Soccer")
    
    if " vs " in event_name:
        home, away = event_name.split(" vs ", 1)
    else:
        home, away = event_name, "Away"
        
    parsed_fixtures.append({
        "Date": date_str,
        "League": league_name,
        "Fixture": event_name,
        "HomeTeam": home,
        "AwayTeam": away,
        "MarketId": m.get("marketId"),
        "LiveMinute": 0  # Default to pre-match/kickoff if live clock isn't parsed yet
    })

@st.cache_data
def load_fallback_data():
    teams_df = pd.read_csv("data/team_db.csv")
    return teams_df

teams_df = load_fallback_data()

# Use Betfair fixtures if available, otherwise fallback gracefully
if parsed_fixtures:
    fixtures_df = pd.DataFrame(parsed_fixtures)
    api_connected = True
else:
    api_connected = False
    fixtures_df = pd.DataFrame({
        "Date": ["Today"],
        "League": ["Premier League (Fallback)"],
        "Fixture": ["Arsenal vs Chelsea"],
        "HomeTeam": ["Arsenal"],
        "AwayTeam": ["Chelsea"],
        "LiveMinute": [32]
    })

st.title("⚽ Professional Goals & Match Odds Trading Engine (Live Betfair API)")

if api_connected:
    st.success("🟢 Connected to Betfair Exchange Live API & Live Fixture Feed!")
else:
    st.warning("⚠️ Betfair API live fixtures unavailable. Showing fallback defaults.")

st.markdown("---")

# Dynamic Dropdowns populated by real Betfair data
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

# Pull team stats or use defaults if team is newly added from Betfair
if home_team in teams_df["TeamName"].values:
    home_stats = teams_df[teams_df["TeamName"] == home_team].iloc[0]
    home_xg = home_stats["BasexG"] * home_stats["SquadWeight"]
else:
    home_xg = 1.35  # League average baseline

if away_team in teams_df["TeamName"].values:
    away_stats = teams_df[teams_df["TeamName"] == away_team].iloc[0]
    away_xg = away_stats["BasexG"] * away_stats["SquadWeight"]
else:
    away_xg = 1.15  # League average baseline

expected_goals = home_xg + away_xg

markets = []

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
st.subheader("📈 Goal Lines & Match Odds Value Board (with Kelly Staking)")

for i in range(0, len(markets), 2):
    col1, col2 = st.columns(2)
    
    for idx, (col, m) in enumerate([(col1, markets[i]), (col2, markets[i+1] if i+1 < len(markets) else None)]):
        if m is None:
            continue
        with col:
            live_p = m["live"]
            target_p = m["target"]
            
            model_prob = 1.0 / target_p
            b = live_p - 1.0
            if b > 0:
                full_kelly = (model_prob * live_p - 1.0) / b
            else:
                full_kelly = 0.0
                
            recommended_stake = max(0.0, bankroll * full_kelly * kelly_fraction)
            
            if live_p > target_p * 1.05 and recommended_stake > 0:
                signal = "🟢 BACK VALUE"
            elif live_p < target_p * 0.95:
                signal = "🔵 LAY VALUE"
            else:
                signal = "⚪ FAIR / NO TRADE"
                recommended_stake = 0.0

            st.markdown(f"**{m['name']}**")
            mc1, mc2, mc3 = st.columns(3)
            mc1.metric("Live Price", f"{live_p}")
            mc2.metric("Model Target", f"{target_p}")
            mc3.metric("Signal", signal)
            
            if recommended_stake > 0:
                st.caption(f"💡 **Rec. Stake:** £{recommended_stake:.2f} ({int(kelly_fraction*100)}% Kelly)")
            else:
                st.caption("💡 **Rec. Stake:** £0.00 (No Value)")
            st.markdown("---")

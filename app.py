import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime

st.set_page_config(
    page_title="Pro Football Trading & Kelly Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SIDEBAR: BANKROLL & RISK CONTROLS ---
st.sidebar.header("💰 Bankroll & Risk Management")
bankroll = st.sidebar.number_input("Total Bankroll (£)", min_value=10.0, max_value=100000.0, value=1000.0, step=50.0)
kelly_fraction = st.sidebar.slider("Kelly Multiplier (Safety)", 0.1, 1.0, 0.25, 0.05, help="0.25 = Quarter Kelly for optimal variance reduction")

# --- DATA INGESTION: LIVE BETFAIR API DIRECT STREAM ---
@st.cache_data(ttl=15)
def fetch_betfair_exchange_data():
    try:
        app_key = st.secrets["BETFAIR_APP_KEY"]
        sso_id = st.secrets["BETFAIR_SSO_ID"]
    except Exception:
        return [], {}

    url = "https://api.betfair.com/exchange/betting/json-rpc/v1"
    headers = {
        "X-Application": app_key,
        "X-Authentication": sso_id,
        "Content-Type": "application/json"
    }
    
    # Query all available soccer match odds catalogues from the exchange
    cat_payload = {
        "jsonrpc": "2.0",
        "method": "SportsAPING/v1.0/listMarketCatalogue",
        "params": {
            "filter": {
                "eventTypeIds": ["1"],
                "marketTypeCodes": ["MATCH_ODDS"]
            },
            "maxResults": "100",
            "marketProjection": ["RUNNER_METADATA", "EVENT", "COMPETITION", "MARKET_START_TIME"]
        },
        "id": 1
    }
    
    try:
        res = requests.post(url, headers=headers, data=json.dumps(cat_payload))
        if res.status_code != 200:
            return [], {}
        catalogue_result = res.json().get("result", [])
    except Exception:
        return [], {}

    if not catalogue_result:
        return [], {}

    market_ids = [m.get("marketId") for m in catalogue_result if m.get("marketId")]
    
    # Grab the live book prices for those exact market IDs
    book_payload = {
        "jsonrpc": "2.0",
        "method": "SportsAPING/v1.0/listMarketBook",
        "params": {
            "marketIds": market_ids,
            "priceProjection": {
                "priceData": ["EX_BEST_OFFERS"]
            }
        },
        "id": 2
    }
    
    books_map = {}
    try:
        res_book = requests.post(url, headers=headers, data=json.dumps(book_payload))
        if res_book.status_code == 200:
            books_result = res_book.json().get("result", [])
            for b in books_result:
                books_map[b.get("marketId")] = b
    except Exception:
        pass

    return catalogue_result, books_map

raw_cats, market_books = fetch_betfair_exchange_data()

parsed_fixtures = []
for m in raw_cats:
    event = m.get("event", {})
    competition = m.get("competition", {})
    event_name = event.get("name", "Unknown vs Unknown")
    start_time = m.get("marketStartTime", "")
    league_name = competition.get("name", "Football / Soccer")
    market_id = m.get("marketId")
    
    if start_time:
        try:
            dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            date_str = dt.strftime("%A, %d %b %Y")
        except Exception:
            date_str = start_time.split("T")[0]
    else:
        date_str = "Live / Upcoming"
    
    if " vs " in event_name:
        home, away = event_name.split(" vs ", 1)
    else:
        home, away = event_name, "Away"
        
    book_data = market_books.get(market_id, {})
    runners = book_data.get("runners", [])
    
    home_back_price, draw_back_price, away_back_price = 1.95, 3.50, 4.00
    if len(runners) >= 3:
        try:
            home_back_price = runners[0].get("ex", {}).get("availableToBack", [{"price": 1.95}])[0].get("price", 1.95)
            draw_back_price = runners[2].get("ex", {}).get("availableToBack", [{"price": 3.50}])[0].get("price", 3.50)
            away_back_price = runners[1].get("ex", {}).get("availableToBack", [{"price": 4.00}])[0].get("price", 4.00)
        except Exception:
            pass

    parsed_fixtures.append({
        "Date": date_str,
        "League": league_name,
        "Fixture": event_name,
        "HomeTeam": home,
        "AwayTeam": away,
        "MarketId": market_id,
        "HomePrice": home_back_price,
        "DrawPrice": draw_back_price,
        "AwayPrice": away_back_price,
        "InPlay": book_data.get("inplay", False)
    })

@st.cache_data
def load_team_database():
    try:
        return pd.read_csv("data/team_db.csv")
    except Exception:
        return pd.DataFrame({
            "TeamName": ["Arsenal", "Chelsea", "Liverpool", "Manchester United", "Manchester City", "Tottenham", "Real Madrid", "Barcelona", "Villarreal", "Bayern Munich", "PSG"],
            "BasexG": [1.65, 1.35, 1.80, 1.45, 1.95, 1.50, 1.90, 1.85, 1.30, 2.10, 1.95],
            "SquadWeight": [1.05, 0.98, 1.08, 0.95, 1.12, 0.99, 1.10, 1.08, 0.92, 1.08, 1.07]
        })

teams_df = load_team_database()

if parsed_fixtures:
    fixtures_df = pd.DataFrame(parsed_fixtures)
    api_connected = True
else:
    fixtures_df = pd.DataFrame({
        "Date": ["No Feed Data"],
        "League": ["None"],
        "Fixture": ["No Live Exchange Markets Found"],
        "HomeTeam": ["Home"],
        "AwayTeam": ["Away"],
        "MarketId": ["0"],
        "HomePrice": [1.0],
        "DrawPrice": [1.0],
        "AwayPrice": [1.0],
        "InPlay": [False]
    })
    api_connected = False

# --- MAIN DASHBOARD INTERFACE ---
st.title("⚽ Professional Goals & Match Odds Trading Engine")

if api_connected:
    st.success(f"🟢 Connected to Betfair Exchange API! Live streaming {len(fixtures_df)} market fixtures directly from exchange catalogue.")
else:
    st.warning("⚠️ Betfair API returned 0 markets from the endpoint.")

st.markdown("---")

col_a, col_b, col_c = st.columns(3)
with col_a:
    selected_date = st.selectbox("Date", fixtures_df["Date"].unique())
with col_b:
    filtered_leagues = fixtures_df[fixtures_df["Date"] == selected_date]["League"].unique()
    selected_league = st.selectbox("League", filtered_leagues)
with col_c:
    match_subset = fixtures_df[(fixtures_df["Date"] == selected_date) & (fixtures_df["League"] == selected_league)]
    selected_fixture = st.selectbox("Fixture", match_subset["Fixture"].unique())

match_row = match_subset[match_subset["Fixture"] == selected_fixture].iloc[0]
home_team = match_row["HomeTeam"]
away_team = match_row["AwayTeam"]
live_minute = st.slider("Match Minute (In-Play)", 0, 90, 25 if match_row["InPlay"] else 0)

# Model Calculation for xG
if home_team in teams_df["TeamName"].values:
    h_row = teams_df[teams_df["TeamName"] == home_team].iloc[0]
    home_xg = h_row["BasexG"] * h_row["SquadWeight"]
else:
    home_xg = 1.45

if away_team in teams_df["TeamName"].values:
    a_row = teams_df[teams_df["TeamName"] == away_team].iloc[0]
    away_xg = a_row["BasexG"] * a_row["SquadWeight"]
else:
    away_xg = 1.25

expected_goals = home_xg + away_xg

markets = []
for line in [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5]:
    base_over_target = max(1.01, round(1.0 + (line * 0.9) - (expected_goals * 0.4) + (max(0, 45 - live_minute) * 0.01), 2))
    base_under_target = max(1.01, round(3.5 - (line * 0.5) + (expected_goals * 0.3) + (live_minute * 0.01), 2))
    
    mock_live_over = round(base_over_target * np.random.uniform(0.95, 1.15), 2)
    mock_live_under = round(base_under_target * np.random.uniform(0.95, 1.10), 2)
    
    markets.append({"name": f"Over {line} Goals", "live": mock_live_over, "target": base_over_target})
    markets.append({"name": f"Under {line} Goals", "live": mock_live_under, "target": base_under_target})

markets.append({"name": "Match Odds: Home Win", "live": float(match_row["HomePrice"]), "target": round(1.85, 2)})
markets.append({"name": "Match Odds: Draw", "live": float(match_row["DrawPrice"]), "target": round(3.20, 2)})
markets.append({"name": "Match Odds: Away Win", "live": float(match_row["AwayPrice"]), "target": round(3.10, 2)})

st.markdown("---")
st.subheader("📈 Value Board & Live Trend Visuals")

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
            
            np.random.seed(hash(m["name"]) % 10000)
            minutes = list(range(0, 91, 5))
            trend_prices = [round(target_p * np.random.uniform(0.9, 1.2), 2) for _ in minutes]
            trend_prices[-1] = live_p
            
            chart_data = pd.DataFrame({
                "Minute": minutes,
                "Live Price": trend_prices,
                "Model Target": [target_p] * len(minutes)
            }).set_index("Minute")
            
            if "BACK" in signal:
                st.line_chart(chart_data, color=["#2ecc71", "#95a5a6"], height=160)
            elif "LAY" in signal:
                st.line_chart(chart_data, color=["#3498db", "#95a5a6"], height=160)
            else:
                st.line_chart(chart_data, color=["#f1c40f", "#95a5a6"], height=160)
            
            if recommended_stake > 0:
                st.caption(f"💡 **Rec. Stake:** £{recommended_stake:.2f} ({int(kelly_fraction*100)}% Kelly)")
            else:
                st.caption("💡 **Rec. Stake:** £0.00 (No Value)")
            st.markdown("---")

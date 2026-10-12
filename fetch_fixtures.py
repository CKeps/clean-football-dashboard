import pandas as pd
import os

def generate_fixtures():
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    data = {
        "Date": ["Today (12 Oct)", "Today (12 Oct)", "Tomorrow (13 Oct)"],
        "League": ["Premier League", "Premier League", "La Liga"],
        "Fixture": ["Arsenal vs Chelsea", "Liverpool vs Man City", "Real Madrid vs Barcelona"],
        "HomeTeam": ["Arsenal", "Liverpool", "Real Madrid"],
        "AwayTeam": ["Chelsea", "Man City", "Barcelona"],
        "LiveMinute": [32, 15, 0]
    }
    df = pd.DataFrame(data)
    df.to_csv("data/fixture_db.csv", index=False)
    print("Fixture database updated successfully.")

if __name__ == "__main__":
    generate_fixtures()

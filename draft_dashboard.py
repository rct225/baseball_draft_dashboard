
import streamlit as st
import pandas as pd
from collections import defaultdict

# Constants
NUM_TEAMS = 10
ROSTER_SLOTS = [
    'C', '1B', '2B', '3B', 'SS',
    'OF', 'OF', 'OF', 'UTIL',
    'SP', 'SP', 'SP', 'SP', 'SP',
    'RP', 'RP',
    'BENCH', 'BENCH', 'BENCH', 'BENCH', 'BENCH'
]

# Load Data
hitters = pd.read_csv('data/fangraphs_hitters_2024.csv')
pitchers = pd.read_csv('data/fangraphs_pitchers_2024.csv')

# Fantasy Points Calculation
def calculate_hitter_points(df):
    points = (
        df['H'] * 1 + df['1B'] * 1 + df['2B'] * 2 + df['3B'] * 3 +
        df['HR'] * 4 + df['RBI'] * 1 + df['SB'] * 1 + df['CS'] * -1 +
        df['K'] * -1 + df['SAC'] * 0.5
    )
    df['FantasyPoints'] = points
    return df

def calculate_pitcher_points(df):
    points = (
        df['GS'] * 5 + df['IP'] * 1 + df['BB'] * -0.5 + df['ER'] * -1 +
        df['PO'] * 1 + df['QS'] * 3 + df['W'] * 7 + df['L'] * -3 +
        df['SV'] * 7 + df['BS'] * -3 + df['CG'] * 10 + df['NH'] * 25 + df['PG'] * 35
    )
    df['FantasyPoints'] = points
    return df

hitters = calculate_hitter_points(hitters)
pitchers = calculate_pitcher_points(pitchers)
all_players = pd.concat([hitters, pitchers]).reset_index(drop=True)

# PORP Calculation
def calculate_replacement_levels(player_pool):
    slots_needed = {pos: ROSTER_SLOTS.count(pos) * NUM_TEAMS for pos in set(ROSTER_SLOTS) if pos not in ['UTIL', 'BENCH']}
    replacement = {}
    for pos, count in slots_needed.items():
        eligible = player_pool[player_pool['Pos'].apply(lambda x: pos in str(x))].sort_values(by='FantasyPoints', ascending=False)
        replacement[pos] = eligible.iloc[count - 1]['FantasyPoints'] if len(eligible) >= count else 0
    return replacement

def calculate_por(player_pool, replacements):
    def get_level(pos_list):
        return min([replacements.get(pos, 0) for pos in eval(pos_list)]) if pos_list else 0
    player_pool['ReplacementLevel'] = player_pool['Pos'].apply(get_level)
    player_pool['PORP'] = player_pool['FantasyPoints'] - player_pool['ReplacementLevel']
    return player_pool.sort_values(by='PORP', ascending=False)

# Streamlit Setup
st.set_page_config(page_title="Fantasy Baseball Draft Assistant", layout="wide")
st.title("⚾ Fantasy Baseball Draft Assistant - Final Enhanced Version")

# Session Initialization
if "drafted_players" not in st.session_state:
    st.session_state.drafted_players = []
if "team_rosters" not in st.session_state:
    st.session_state.team_rosters = {f'Team_{i+1}': [] for i in range(NUM_TEAMS)}
if "draft_history" not in st.session_state:
    st.session_state.draft_history = []

# Draft Tracker UI
st.sidebar.header("Draft Tracker")
remaining_pool = all_players[~all_players['Player'].isin(st.session_state.drafted_players)]
replacements = calculate_replacement_levels(remaining_pool)
remaining_pool = calculate_por(remaining_pool, replacements)

draft_pick = st.sidebar.selectbox("Select Player to Draft", remaining_pool['Player'].tolist())
draft_team = st.sidebar.selectbox("Assign to Team", [f'Team_{i+1}' for i in range(NUM_TEAMS)])
if st.sidebar.button("Draft Player"):
    st.session_state.drafted_players.append(draft_pick)
    st.session_state.team_rosters[draft_team].append(draft_pick)
    st.session_state.draft_history.append((draft_team, draft_pick))
    st.sidebar.success(f"{draft_pick} drafted to {draft_team}")

# Positional Needs Alerts
st.subheader("📣 Positional Need Alerts")
for team, players in st.session_state.team_rosters.items():
    pos_counts = defaultdict(int)
    for p in players:
        pos_list = all_players[all_players['Player'] == p]['Pos'].values
        if len(pos_list):
            for pos in eval(pos_list[0]):
                pos_counts[pos] += 1
    needs = {}
    for pos in set(ROSTER_SLOTS):
        required = ROSTER_SLOTS.count(pos)
        if pos not in ['UTIL', 'BENCH'] and pos_counts.get(pos, 0) < required:
            needs[pos] = required - pos_counts.get(pos, 0)
    if needs:
        st.markdown(f"**{team} Needs:** {needs}")

# Suggested Picks Based on Team Needs
st.subheader("🎯 Suggested Picks Based on Team Needs")
suggestions = {}
for team, players in st.session_state.team_rosters.items():
    needs = []
    pos_counts = defaultdict(int)
    for p in players:
        pos_list = all_players[all_players['Player'] == p]['Pos'].values
        if len(pos_list):
            for pos in eval(pos_list[0]):
                pos_counts[pos] += 1
    for pos in set(ROSTER_SLOTS):
        if pos not in ['UTIL', 'BENCH'] and pos_counts.get(pos, 0) < ROSTER_SLOTS.count(pos):
            needs.append(pos)
    filtered = remaining_pool[remaining_pool['Pos'].apply(lambda x: any(n in str(x) for n in needs))].head(5)
    suggestions[team] = filtered[['Player', 'Pos', 'FantasyPoints', 'PORP']]

for team, df in suggestions.items():
    st.markdown(f"**Top Picks for {team} (based on current needs):**")
    st.dataframe(df)

# Draft History
st.subheader("📜 Draft History")
if st.session_state.draft_history:
    history_df = pd.DataFrame(st.session_state.draft_history, columns=['Team', 'Player'])
    st.dataframe(history_df)

# Team Rosters
st.subheader("🏟️ Team Rosters")
for team, players in st.session_state.team_rosters.items():
    st.markdown(f"### {team}")
    st.write(players)

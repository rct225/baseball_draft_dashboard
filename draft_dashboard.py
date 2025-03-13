
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
st.title("⚾ Fantasy Baseball Draft Assistant - Autopick Enabled")

# Session Initialization
if "drafted_players" not in st.session_state:
    st.session_state.drafted_players = []
if "team_rosters" not in st.session_state:
    st.session_state.team_rosters = {f'Team_{i+1}': [] for i in range(NUM_TEAMS)}
if "draft_history" not in st.session_state:
    st.session_state.draft_history = []
if "draft_round" not in st.session_state:
    st.session_state.draft_round = 0
if "draft_pick_index" not in st.session_state:
    st.session_state.draft_pick_index = 0

# Calculate draft order (snake style)
def get_next_team(round_num, pick_index):
    order = list(range(NUM_TEAMS))
    if round_num % 2 != 0:
        order.reverse()
    return f"Team_{order[pick_index]+1}"

# Calculate Remaining Player Pool
remaining_pool = all_players[~all_players['Player'].isin(st.session_state.drafted_players)]
replacements = calculate_replacement_levels(remaining_pool)
remaining_pool = calculate_por(remaining_pool, replacements)

# Draft Picker
current_team = get_next_team(st.session_state.draft_round, st.session_state.draft_pick_index)
st.sidebar.header(f"Drafting Now: {current_team}")
available_players = remaining_pool['Player'].tolist()
pick = st.sidebar.selectbox("Select Player to Draft", available_players)

if st.sidebar.button("Confirm Draft Pick"):
    st.session_state.drafted_players.append(pick)
    st.session_state.team_rosters[current_team].append(pick)
    st.session_state.draft_history.append((current_team, pick))

    # Move to next team
    st.session_state.draft_pick_index += 1
    if st.session_state.draft_pick_index >= NUM_TEAMS:
        st.session_state.draft_pick_index = 0
        st.session_state.draft_round += 1
    st.sidebar.success(f"{pick} drafted to {current_team}")

# Display Suggestions
st.subheader("📈 Top Suggested Picks (Based on PORP)")
st.dataframe(remaining_pool[['Player', 'Pos', 'FantasyPoints', 'PORP']].head(15))

# Display Draft History
st.subheader("📜 Draft History")
if st.session_state.draft_history:
    st.dataframe(pd.DataFrame(st.session_state.draft_history, columns=['Team', 'Player']))

# Display Team Rosters
st.subheader("🏟️ Team Rosters")
for team, players in st.session_state.team_rosters.items():
    st.markdown(f"### {team}")
    st.write(players)

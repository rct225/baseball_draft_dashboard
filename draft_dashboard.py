
# draft_dashboard.py (Streamlit UI for Live Draft Assistant - FIXED VERSION)

import streamlit as st
import pandas as pd

# 🔁 GLOBAL CONSTANTS MOVED HERE
NUM_TEAMS = 10
ROSTER_SLOTS = [
    'C', '1B', '2B', '3B', 'SS',
    'OF', 'OF', 'OF', 'UTIL',
    'SP', 'SP', 'SP', 'SP', 'SP',
    'RP', 'RP',
    'BENCH', 'BENCH', 'BENCH', 'BENCH', 'BENCH'
]
ALL_PLAYERS_PATH = "data/all_players_with_points.csv"

# 🔁 IMPORT LOCAL MODULE FUNCTIONS (they must be in same directory on Streamlit Cloud)
from draft_value_analysis import calculate_positional_replacement_levels, calculate_por
from live_draft_assistant import live_draft_suggestions, analyze_opponent_builds, build_draft_contingency_tree, add_pick

st.set_page_config(page_title="Fantasy Baseball Draft Assistant", layout="wide")

st.title("⚾ Live Draft Assistant Dashboard")

# Load data
all_players = pd.read_csv(ALL_PLAYERS_PATH)

# Session state
if "drafted_players" not in st.session_state:
    st.session_state.drafted_players = []
if "user_team_roster" not in st.session_state:
    st.session_state.user_team_roster = []
if "all_teams_rosters" not in st.session_state:
    st.session_state.all_teams_rosters = {}

# Sidebar Controls
st.sidebar.header("Draft Tracker")
player_pick = st.sidebar.selectbox("Select Player to Draft", all_players[~all_players['Player'].isin(st.session_state.drafted_players)]['Player'].tolist())
user_team = st.sidebar.selectbox("Assign to Team (optional)", ["None"] + [f"Team_{i+1}" for i in range(NUM_TEAMS)])

if st.sidebar.button("Draft Player"):
    add_pick(
        player_pick,
        st.session_state.drafted_players,
        st.session_state.all_teams_rosters,
        None if user_team == "None" else user_team,
        all_players
    )
    st.sidebar.success(f"{player_pick} drafted")

# Live Suggestions
st.header("📈 Top Suggested Picks")
best, best_by_position = live_draft_suggestions(
    all_players,
    st.session_state.drafted_players,
    ROSTER_SLOTS,
    NUM_TEAMS,
    st.session_state.user_team_roster
)

st.subheader("Top Overall by PORP")
st.dataframe(best)

with st.expander("Top Picks By Position"):
    for pos, df in best_by_position.items():
        st.markdown(f"### {pos}")
        st.dataframe(df)

# Opponent Build Tracker
st.subheader("📊 Opponent Position Draft Summary")
st.dataframe(analyze_opponent_builds(st.session_state.all_teams_rosters, ROSTER_SLOTS))

# Draft Contingency Tree
st.subheader("🌳 Draft Contingency Tree")
targets = st.multiselect("Your Target Players", all_players['Player'].tolist())
if targets:
    tree = build_draft_contingency_tree(
        all_players,
        st.session_state.drafted_players,
        targets,
        ROSTER_SLOTS,
        NUM_TEAMS
    )
    for player, df in tree.items():
        st.markdown(f"### If {player} is taken, consider:")
        st.dataframe(df)

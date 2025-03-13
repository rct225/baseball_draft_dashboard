
# draft_dashboard_FULL.py (Fully Self-Contained Streamlit App)

import streamlit as st
import pandas as pd
from collections import defaultdict

# ====== GLOBALS (inlined) ======
NUM_TEAMS = 10
ROSTER_SLOTS = [
    'C', '1B', '2B', '3B', 'SS',
    'OF', 'OF', 'OF', 'UTIL',
    'SP', 'SP', 'SP', 'SP', 'SP',
    'RP', 'RP',
    'BENCH', 'BENCH', 'BENCH', 'BENCH', 'BENCH'
]
ALL_PLAYERS_PATH = "data/all_players_with_points.csv"

# ====== DRAFT VALUE ANALYSIS FUNCTIONS (inlined) ======
def calculate_positional_replacement_levels(player_pool, roster_slots, num_teams):
    replacement_levels = {}
    slots_needed = {pos: roster_slots.count(pos) * num_teams for pos in set(roster_slots) if pos != 'UTIL' and pos != 'BENCH'}
    for pos, total_slots in slots_needed.items():
        eligible_players = player_pool[player_pool['Pos'].apply(lambda x: pos in x)].sort_values(by='FantasyPoints', ascending=False)
        if len(eligible_players) >= total_slots:
            replacement_levels[pos] = eligible_players.iloc[total_slots - 1]['FantasyPoints']
        else:
            replacement_levels[pos] = eligible_players['FantasyPoints'].min()
    return replacement_levels

def calculate_por(player_pool, replacement_levels):
    def get_replacement_level(pos_list):
        pos_scores = [replacement_levels.get(pos, 0) for pos in pos_list]
        return min(pos_scores) if pos_scores else 0
    player_pool['ReplacementLevel'] = player_pool['Pos'].apply(get_replacement_level)
    player_pool['PORP'] = player_pool['FantasyPoints'] - player_pool['ReplacementLevel']
    return player_pool.sort_values(by='PORP', ascending=False)

# ====== LIVE DRAFT ASSISTANT FUNCTIONS (inlined) ======
def update_player_pool(player_pool, drafted_players):
    return player_pool[~player_pool['Player'].isin(drafted_players)].reset_index(drop=True)

def update_replacement_levels(player_pool, roster_slots, num_teams):
    return calculate_positional_replacement_levels(player_pool, roster_slots, num_teams)

def get_team_needs(team_roster, roster_slots):
    pos_counts = defaultdict(int)
    for pos_list in team_roster:
        for pos in pos_list:
            pos_counts[pos] += 1
    needs = {}
    for pos in set(roster_slots):
        if pos not in ['UTIL', 'BENCH']:
            current = pos_counts.get(pos, 0)
            required = roster_slots.count(pos)
            if current < required:
                needs[pos] = required - current
    return needs

def live_draft_suggestions(player_pool, drafted_players, roster_slots, num_teams, user_team_roster):
    updated_pool = update_player_pool(player_pool, drafted_players)
    replacement_levels = update_replacement_levels(updated_pool, roster_slots, num_teams)
    updated_pool = calculate_por(updated_pool, replacement_levels)
    team_needs = get_team_needs(user_team_roster, roster_slots)
    best_overall = updated_pool.sort_values(by='PORP', ascending=False).head(10)
    best_by_position = {}
    for pos in team_needs:
        eligible = updated_pool[updated_pool['Pos'].apply(lambda x: pos in x)].sort_values(by='PORP', ascending=False).head(5)
        best_by_position[pos] = eligible[['Player', 'Pos', 'FantasyPoints', 'PORP']]
    return best_overall, best_by_position

def analyze_opponent_builds(all_teams_rosters, roster_slots):
    team_summary = {}
    for team, roster in all_teams_rosters.items():
        pos_counts = defaultdict(int)
        for pos_list in roster:
            for pos in pos_list:
                pos_counts[pos] += 1
        team_summary[team] = {pos: pos_counts.get(pos, 0) for pos in set(roster_slots)}
    return pd.DataFrame(team_summary)

def build_draft_contingency_tree(player_pool, drafted_players, targets, roster_slots, num_teams):
    updated_pool = update_player_pool(player_pool, drafted_players)
    replacement_levels = update_replacement_levels(updated_pool, roster_slots, num_teams)
    updated_pool = calculate_por(updated_pool, replacement_levels)
    tree = {}
    for player in targets:
        if player in updated_pool['Player'].values:
            alt_pool = updated_pool[updated_pool['Player'] != player]
            fallback = alt_pool.sort_values(by='PORP', ascending=False).head(3)
            tree[player] = fallback[['Player', 'Pos', 'FantasyPoints', 'PORP']]
    return tree

def add_pick(player_name, drafted_players, all_teams_rosters=None, team_name=None, player_data=None):
    drafted_players.append(player_name)
    if all_teams_rosters is not None and team_name is not None and player_data is not None:
        pos_list = player_data[player_data['Player'] == player_name]['Pos'].values
        if len(pos_list) > 0:
            all_teams_rosters.setdefault(team_name, []).append(pos_list[0])

# ====== STREAMLIT UI CODE ======
st.set_page_config(page_title="Fantasy Baseball Draft Assistant", layout="wide")

st.title("⚾ Live Draft Assistant Dashboard")

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

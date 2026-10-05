import json

import pandas as pd
import streamlit as st
from streamlit_js_eval import streamlit_js_eval

from pokemon_team_optimizer import cli, config

STORAGE_KEY = "pokemon-team-optimizer-inputs"
FOSSIL_OPTIONS = ("all", "one", "none")
GEN_OPTIONS = list(range(1, config.NGENS + 1))
default_inputs = {
    "legendaries": True,
    "plegendaries": True,
    "starters": True,
    "fossils": "all",
    "version": "nat",
    "size_team": 6,
    "gens": [],
    "in_team": [],
    "out_team": [],
    "captured": [],
}

data_all = pd.read_csv(config.get_file_loc("nat"))
all_pkmn_names = data_all["name"]

# Restore the input parameters saved in the browser's local storage. The browser answers asynchronously:
# the first run gets None, then the app reruns with the saved JSON ("" if nothing was saved yet).
with st.sidebar:
    saved_inputs = streamlit_js_eval(js_expressions=f"localStorage.getItem('{STORAGE_KEY}') ?? ''", key="load_inputs")
if saved_inputs is not None and "inputs_restored" not in st.session_state:
    st.session_state.inputs_restored = True
    try:
        restored_inputs = json.loads(saved_inputs) if saved_inputs else {}
    except json.JSONDecodeError:
        restored_inputs = {}
    if isinstance(restored_inputs, dict):
        for key in default_inputs.keys() & restored_inputs.keys():
            st.session_state[key] = restored_inputs[key]
for key, value in default_inputs.items():
    st.session_state.setdefault(key, value)

# Reset values the widgets would reject (e.g. from a save made by an older version of the app)
if st.session_state.fossils not in FOSSIL_OPTIONS:
    st.session_state.fossils = default_inputs["fossils"]
if st.session_state.version not in config.list_games:
    st.session_state.version = default_inputs["version"]
if not isinstance(st.session_state.size_team, int) or not 1 <= st.session_state.size_team <= len(all_pkmn_names):
    st.session_state.size_team = default_inputs["size_team"]
st.session_state.gens = [gen for gen in st.session_state.gens if gen in GEN_OPTIONS]
st.session_state.in_team = [name for name in st.session_state.in_team if name in set(all_pkmn_names)]
st.session_state.out_team = [name for name in st.session_state.out_team if name in set(all_pkmn_names)]

# Streamlit UI
st.title("Pokemon Team Optimizer")
st.write(
    "This is a demo of a linear optimization algorithm to build efficient teams in Pokemon games."
    " Teams are built under the constraints set in the sidebar in order to maximize the base total"
    " and such that every type can be resisted by at least one Pokemon in the team."
)
st.sidebar.html("""
<a href="https://github.com/NicolasChagnet/pokemon-team-optimizer">
<img alt="github" src="https://badgen.net/badge/icon/github?icon=github&label=NicolasChagnet">
<style>
          a {
            margin-right: 4px;
          }
          /* Hide the invisible local storage components */
          div[data-testid="stElementContainer"]:has(iframe[title*="streamlit_js_eval"]) {
            display: none;
          }
</style>
</a>
""")

st.sidebar.header("Input Parameters")
legendaries = st.sidebar.toggle("Include legendaries", key="legendaries")
plegendaries = st.sidebar.toggle("Include pseudo-legendaries", key="plegendaries")
starters = st.sidebar.toggle("Allow more than one starter?", key="starters")
fossils = st.sidebar.selectbox("Include fossils?", FOSSIL_OPTIONS, key="fossils")
version = st.sidebar.selectbox(
    "Version restriction",
    config.list_games.keys(),
    format_func=lambda x: config.list_games_names[x],
    key="version",
)
size_team = st.sidebar.number_input("Size of the team: ", min_value=1, max_value=len(all_pkmn_names), key="size_team")
gens = st.sidebar.multiselect("What generations should be included (empty means all)?", GEN_OPTIONS, key="gens")
in_team = st.sidebar.multiselect("Pokemon to include:", all_pkmn_names, key="in_team")
out_team = st.sidebar.multiselect("Pokemon to exclude:", all_pkmn_names, key="out_team")
# The captured Pokemon depend on the version, drop the ones not available in the selected one
version_pkmn_names = pd.read_csv(config.get_file_loc(version))["name"]
st.session_state.captured = [name for name in st.session_state.captured if name in set(version_pkmn_names)]
captured = st.sidebar.multiselect(
    "Captured Pokemon to build the team from (empty means all):",
    version_pkmn_names,
    key="captured",
)

# Save the input parameters in the browser's local storage, once the saved ones have been restored
if st.session_state.get("inputs_restored"):
    inputs_json = json.dumps({key: st.session_state[key] for key in default_inputs})
    with st.sidebar:
        streamlit_js_eval(
            js_expressions=f"localStorage.setItem('{STORAGE_KEY}', {json.dumps(inputs_json)})",
            want_output=False,
            key="save_inputs",
        )


if st.button("Solve"):
    try:
        team, resistances = cli.team_optimizer(
            gen_cap=None,
            gens=gens,
            version=version,
            size_team=size_team,
            fossils=fossils,
            include_legendaries=legendaries,
            include_pseudolegendaries=plegendaries,
            allow_multiple_starters=starters,
            in_team=in_team,
            out_team=out_team,
            captured=captured,
        )
        if team is not None:
            team = team.rename(columns={"name": "Pokemon", "type1": "Type 1", "type2": "Type 2"})
            resistances = resistances.rename(
                index={0: "Type"}, columns={"min_val": "Minimal factor", "min_pkmn": "Optimal defender"}
            )
    except ValueError:
        team = None

    st.subheader("Result")
    if team is None:
        st.write("Status: Error!")
    else:
        st.write("Status: Success!")
        st.data_editor(
            team[["img", "Pokemon", "Type 1", "Type 2"]],
            column_config={"img": st.column_config.ImageColumn("Sprite", help="Pokemon sprite")},
            hide_index=True,
            width=500,
            disabled=True,
        )
        # Transposed columns mix factors and names, display them as text so Arrow can serialize them
        st.dataframe(
            resistances[["Minimal factor", "Optimal defender"]].transpose().astype(str),
            width=500,
        )

    # st.subheader("Variable Values")
    # for var, value in result["Variables"].items():
    #     st.write(f"{var}: {value}")

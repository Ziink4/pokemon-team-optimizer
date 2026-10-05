import sys

from pokemon_team_optimizer import config


def main():
    """Runs the Streamlit app, forwarding extra arguments to `streamlit run` (e.g. --server.port 8502)."""
    try:
        from streamlit.web import cli as stcli
    except ImportError:
        sys.exit('Streamlit is not installed, install the app extra with: pip install -e ".[app]"')

    sys.argv = ["streamlit", "run", str(config.path_root_folder / "app" / "streamlit_app.py"), *sys.argv[1:]]
    sys.exit(stcli.main())

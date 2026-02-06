"""
AvatarFactory Dashboard.

Provides a Streamlit-based web dashboard for visualizing and managing
personas, content, connectors, and scheduled tasks.
"""

__all__ = ["run_dashboard"]


def run_dashboard(port: int = 8501, host: str = "localhost") -> None:
    """Run the Streamlit dashboard."""
    import subprocess
    import sys
    from pathlib import Path

    app_path = Path(__file__).parent / "Dashboard.py"

    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.address", host,
    ])


import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("LiveVisualizer")

class LiveVisualizer:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()

    def open_workspace(self):
        """Opens the folder in VS Code (or Antigravity if configured)."""
        logger.info(f"👀 Opening Workspace: {self.project_root}")
        try:
            # If you want to use Google Antigravity, replace 'code' with its CLI command if available
            subprocess.Popen(["code", "-r", "."], cwd=str(self.project_root), shell=os.name == "nt")
        except Exception as e:
            logger.error(f"❌ Visualizer Error: {e}")

    def focus_file(self, relative_path: str):
        """Forces VS Code to open the specific file being written."""
        try:
            subprocess.Popen(["code", "-r", str(relative_path)], cwd=str(self.project_root), shell=os.name == "nt")
        except: pass

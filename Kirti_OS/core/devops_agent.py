# Kirti_OS/core/devops_agent.py

import os
import logging
import subprocess
import sys
import time
from pathlib import Path
from data_structures import ProjectContext, BuildResult

logger = logging.getLogger("DevOpsAgent")
logger.setLevel(logging.INFO)

class DevOpsAgent:
    """
    The Builder.
    - Creates Folders & Files.
    - Manages Virtual Environments.
    - Installs Dependencies (Visible Window).
    - Robust Error Logging.
    """

    def __init__(self, workspace_root: str = r"D:\test_bot"):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    async def save_code_to_file(self, file_name: str, code: str, context: ProjectContext) -> BuildResult:
        """Saves code to file, handling subdirectories."""
        try:
            clean_name = file_name.strip().strip("'").strip('"')
            project_path = self.workspace_root / context.project_name.replace(" ", "_")
            full_path = project_path / clean_name
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"💾 Saving file: {full_path}")
            full_path.write_text(code, encoding="utf-8")
            
            return BuildResult(
                file_name=clean_name,
                success=True,
                message=f"Saved to {full_path}",
                stderr=""
            )
        except Exception as e:
            logger.error(f"❌ Failed to save file {file_name}: {e}")
            return BuildResult(file_name, False, str(e), str(e))

    async def create_virtual_env(self, context: ProjectContext):
        """Creates Venv in a Visible Window."""
        project_path = self.workspace_root / context.project_name.replace(" ", "_")
        venv_path = project_path / "venv"
        
        if venv_path.exists():
            logger.info("✅ Venv already exists.")
            return

        logger.info("📦 Creating Virtual Environment (Visible)...")
        # Use sys.executable to ensure we use the same python version
        cmd = f'"{sys.executable}" -m venv "{venv_path}"'
        await self._run_visible(cmd, cwd=project_path, title="Kirti: Creating Venv")

    async def install_dependencies(self, context: ProjectContext):
        """Installs requirements.txt in a Visible Window."""
        project_path = self.workspace_root / context.project_name.replace(" ", "_")
        req_file = project_path / "requirements.txt"
        
        if not req_file.exists():
            return

        logger.info("⬇️ Installing Dependencies (Visible)...")
        
        # Determine pip path inside venv
        if sys.platform == "win32":
            pip_exe = project_path / "venv" / "Scripts" / "pip.exe"
        else:
            pip_exe = project_path / "venv" / "bin" / "pip"

        # Fallback if venv pip missing
        if not pip_exe.exists():
            logger.warning("⚠️ Venv pip not found, using system pip.")
            pip_exe = sys.executable + " -m pip"

        cmd = f'"{pip_exe}" install -r requirements.txt'
        await self._run_visible(cmd, cwd=project_path, title="Kirti: Installing Dependencies")

    async def _run_visible(self, command: str, cwd: Path, title: str = "Kirti Task"):
        """
        Runs a command in a visible window.
        - Creates a log file.
        - Shows output in the window (by typing the log).
        - Waits for completion.
        """
        log_dir = cwd / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"cmd_{int(time.time())}.log"
        
        logger.info(f"🖥️  Running Visible Task: {title}")
        
        if sys.platform == "win32":
            # LOGIC:
            # 1. Run command > log
            # 2. Print "Task Complete"
            # 3. Show the log content on screen (type log_file)
            # 4. Wait 5 seconds so user can read
            
            chained_cmd = (
                f'{command} > "{log_file}" 2>&1 '
                f'&& echo. && echo ✅ TASK COMPLETE '
                f'&& type "{log_file}" '
                f'&& timeout /t 5'
            )
            
            # start /WAIT ensures Python waits for the window to close
            full_cmd = f'start "{title}" /WAIT cmd /c "{chained_cmd}"'
            
            subprocess.run(full_cmd, shell=True, cwd=str(cwd))
            
            # Verify Log
            if log_file.exists():
                content = log_file.read_text(encoding='utf-8', errors='ignore')
                if "ERROR" in content or "Traceback" in content:
                    logger.warning(f"⚠️ Possible error in {title}. Check logs.")
        else:
            # Non-Windows Fallback
            subprocess.run(command, shell=True, cwd=str(cwd))
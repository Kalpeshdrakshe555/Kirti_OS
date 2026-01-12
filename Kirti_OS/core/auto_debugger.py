# Kirti_OS/core/auto_debugger.py

import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any
from data_structures import ProjectContext, DebugResult

logger = logging.getLogger("AutoDebugger")
logger.setLevel(logging.INFO)

class AutoDebugger:
    """
    The Fixer.
    - Handles Missing Modules (Direct Install).
    - Handles Logic Errors (AI Fix via ProScraper).
    """

    def __init__(self, scraper):
        self.scraper = scraper

    async def analyze_and_fix(self, file_name: str, code: str, error_msg: str, context: ProjectContext) -> DebugResult:
        logger.info(f"🚑 Starting Debugging for {file_name}...")
        
        # --------------------------------------------------------
        # ERROR TYPE 1: MISSING MODULE (e.g., No module named 'pygame')
        # --------------------------------------------------------
        if "ModuleNotFoundError" in error_msg or "No module named" in error_msg:
            # Extract package name using Regex
            match = re.search(r"No module named ['\"]([^'\"]+)['\"]", error_msg)
            if match:
                missing_pkg = match.group(1)
                logger.info(f"📦 Missing Package Detected: {missing_pkg}. Installing via Pip...")
                
                success = await self._install_package(missing_pkg, context)
                if success:
                    return DebugResult(
                        file_name=file_name,
                        fixed=True,
                        final_code=code, # Code didn't change, env did
                        error_summary=f"Installed missing package: {missing_pkg}"
                    )
        
        # --------------------------------------------------------
        # ERROR TYPE 2: CODE LOGIC / SYNTAX ERROR (Ask AI)
        # --------------------------------------------------------
        try:
            # Delegate to ProScraper (Smart Context Aware)
            fixed_code = await self.scraper.debug_code(file_name, error_msg, code)
            
            if fixed_code:
                logger.info(f"✅ AI provided a fix for {file_name}")
                return DebugResult(
                    file_name=file_name,
                    fixed=True,
                    final_code=fixed_code,
                    error_summary="Fixed by AI"
                )
            else:
                logger.error(f"❌ AI could not fix {file_name}")
                return DebugResult(
                    file_name=file_name,
                    fixed=False,
                    error_summary="AI returned no code"
                )

        except Exception as e:
            logger.error(f"❌ Debugger Error: {e}")
            return DebugResult(file_name, False, str(e))

    async def _install_package(self, package_name: str, context: ProjectContext) -> bool:
        """Installs a single package via pip in a VISIBLE WINDOW."""
        try:
            project_path = Path(r"D:\test_bot") / context.project_name.replace(" ", "_")
            
            if sys.platform == "win32":
                pip_exe = project_path / "venv" / "Scripts" / "pip.exe"
            else:
                pip_exe = project_path / "venv" / "bin" / "pip"
            
            if not pip_exe.exists():
                pip_exe = sys.executable + " -m pip"

            logger.info(f"🖥️  Launching Installer for: {package_name}")
            
            # Visible Command Structure
            cmd_str = f'"{pip_exe}" install {package_name} && echo ✅ INSTALLED && timeout /t 3'
            full_cmd = f'start "Auto-Fixing: Installing {package_name}" /WAIT cmd /c "{cmd_str}"'
            
            subprocess.run(full_cmd, shell=True, cwd=str(project_path))
            return True
            
        except Exception as e:
            logger.error(f"❌ Installation Failed: {e}")
            return False
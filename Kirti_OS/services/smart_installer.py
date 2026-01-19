
import logging
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger("SmartInstaller")

class SmartInstaller:
    HEAVY_PACKAGES = {"torch", "tensorflow", "transformers", "spacy"}
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        if sys.platform == "win32":
            self.pip_exe = project_root / "venv" / "Scripts" / "pip.exe"
            self.python_exe = project_root / "venv" / "Scripts" / "python.exe"
        else:
            self.pip_exe = project_root / "venv" / "bin" / "pip"
            self.python_exe = project_root / "venv" / "bin" / "python"
            
        if not self.pip_exe.exists():
            self.pip_exe = sys.executable
            self.python_exe = sys.executable

    def install_all(self):
        req_file = self.project_root / "requirements.txt"
        if not req_file.exists(): return
        
        timeout = 300
        content = req_file.read_text().lower()
        if any(p in content for p in self.HEAVY_PACKAGES): timeout = 900
        
        logger.info(f"⬇️ Installing Dependencies (Timeout: {timeout}s)...")
        
        # Visible Install
        if sys.platform == "win32":
            cmd = f'"{self.pip_exe}" install -r requirements.txt && echo DONE && timeout /t 5'
            subprocess.run(f'start "Installing Deps" /WAIT cmd /c "{cmd}"', shell=True, cwd=str(self.project_root))
        else:
            subprocess.run([str(self.pip_exe), "install", "-r", "requirements.txt"], cwd=str(self.project_root))
            
        self._verify_imports(req_file)

    def _verify_imports(self, req_file):
        logger.info("🔍 Verifying installations...")
        packages = [l.split("=")[0].strip() for l in req_file.read_text().splitlines() if l.strip()]
        for pkg in packages:
            try:
                subprocess.run([str(self.python_exe), "-c", f"import {pkg}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                logger.warning(f"⚠️ Warning: Could not verify '{pkg}'. It might be missing.")

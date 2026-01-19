import os
from pathlib import Path

# Define Base Path
BASE_DIR = Path("Kirti_OS")

# Define Structure
STRUCTURE = {
    "core": ["__init__.py", "orchestrator.py", "pro_scraper.py", "browser_tools.py"],
    "services": ["__init__.py", "live_visualizer.py", "smart_installer.py"],
    "utils": ["__init__.py", "code_sanitizer.py"],
    "validators": ["__init__.py", "syntax_guard.py"],
}

# 1. utils/code_sanitizer.py (Kimi's Logic - Regex Only, No Tokens)
CODE_SANITIZER = '''
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SanitizedCode:
    code: str
    language: Optional[str]
    all_blocks: List[str]
    source_had_fences: bool

class CodeSanitizer:
    FENCE_PATTERN = re.compile(r"```(?:\\s*(?P<lang>[a-zA-Z0-9_+-]+))?\\s*(?P<code>[\\s\\S]*?)```", re.MULTILINE)
    FILLER_PREFIXES = ("here is the code", "here's the code", "the code is as follows", "example:", "sure", "certainly")

    @classmethod
    def extract_code_blocks(cls, text: str) -> List[str]:
        if not text: return []
        blocks = []
        for match in cls.FENCE_PATTERN.finditer(text):
            code = match.group("code") or ""
            code = cls._strip_filler_lines(code)
            if code.strip(): blocks.append(code.strip())
        return blocks

    @classmethod
    def sanitize(cls, raw_text: str) -> SanitizedCode:
        if not raw_text: return SanitizedCode("", "python", [], False)
        blocks = cls.extract_code_blocks(raw_text)
        if blocks:
            # Pick largest block
            primary = max(blocks, key=len)
            return SanitizedCode(primary, "python", blocks, True)
        
        # Fallback: Return raw text stripped
        return SanitizedCode(cls._strip_filler_lines(raw_text), "python", [], False)

    @classmethod
    def _strip_filler_lines(cls, code: str) -> str:
        lines = code.splitlines()
        cleaned = []
        for line in lines:
            if not any(line.strip().lower().startswith(p) for p in cls.FILLER_PREFIXES):
                cleaned.append(line)
        return "\\n".join(cleaned)
'''

# 2. validators/syntax_guard.py (Python AST Check)
SYNTAX_GUARD = '''
import ast
from dataclasses import dataclass
from typing import Optional

@dataclass
class SyntaxCheckResult:
    ok: bool
    error: Optional[str] = None

class SyntaxGuard:
    @staticmethod
    def validate(code: str, filename: str = "<string>") -> SyntaxCheckResult:
        try:
            ast.parse(code, filename=filename, mode="exec")
            return SyntaxCheckResult(ok=True)
        except SyntaxError as e:
            return SyntaxCheckResult(ok=False, error=f"Line {e.lineno}: {e.msg}")
        except Exception as e:
            return SyntaxCheckResult(ok=False, error=str(e))
'''

# 3. services/live_visualizer.py (Glass Box)
LIVE_VISUALIZER = '''
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
'''

# 4. services/smart_installer.py (Smart Dependency Loop)
SMART_INSTALLER = '''
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
'''

def create_structure():
    print("🚀 Migrating Kirti OS to v2.0 Architecture...")
    
    for folder, files in STRUCTURE.items():
        folder_path = BASE_DIR / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        for f in files:
            file_path = folder_path / f
            if not file_path.exists():
                file_path.touch()
    
    # Write Logic
    (BASE_DIR / "utils" / "code_sanitizer.py").write_text(CODE_SANITIZER, encoding="utf-8")
    (BASE_DIR / "validators" / "syntax_guard.py").write_text(SYNTAX_GUARD, encoding="utf-8")
    (BASE_DIR / "services" / "live_visualizer.py").write_text(LIVE_VISUALIZER, encoding="utf-8")
    (BASE_DIR / "services" / "smart_installer.py").write_text(SMART_INSTALLER, encoding="utf-8")
    
    print("✅ Migration Complete! Professional Structure Ready.")

if __name__ == "__main__":
    create_structure()
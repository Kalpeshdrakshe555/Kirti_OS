# Kirti_OS/core/self_healing_orchestrator.py

import asyncio
import logging
import sys
import subprocess
import os
import time
from pathlib import Path
from typing import Optional, Tuple

# --- INTERNAL IMPORTS ---
from data_structures import ProjectContext, FileRequest
from pro_scraper import ProScraper
from devops_agent import DevOpsAgent
from auto_debugger import AutoDebugger

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
logger = logging.getLogger("Orchestrator")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('⚡ %(asctime)s - [%(levelname)s] - %(message)s', datefmt='%H:%M:%S')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# ============================================================================
# THE ORCHESTRATOR CLASS (THE BOSS)
# ============================================================================
class SelfHealingOrchestrator:
    """
    THE BOSS AGENT.
    Manages the full lifecycle of software generation:
    1. Planning (Blueprint)
    2. Coding (File Generation)
    3. Building (DevOps - Visible)
    4. Verification (Running - Visible)
    5. Healing (Debugging - Context Aware)
    """

    def __init__(self):
        self.scraper = ProScraper()
        self.devops = DevOpsAgent()
        self.debugger = AutoDebugger(self.scraper)
        self.context: Optional[ProjectContext] = None

    async def create_project(self, user_request: str, service: str = "perplexity") -> str:
        """
        Main entry point called by Router/Telegram.
        Args:
            user_request: Description of app to build
            service: "perplexity", "chatgpt", "gemini"
        Returns a formatted string summarizing the result.
        """
        print(f"\n🚀 STARTING PROJECT: '{user_request}' using [{service.upper()}]")
        logger.info(f"Received request: {user_request}")
        
        try:
            # ---------------------------------------------------------
            # PHASE 1: INITIALIZATION & PLANNING
            # ---------------------------------------------------------
            logger.info(f"🧠 Phase 1: Initializing Brain ({service}) & Planning...")
            
            # Start Browser Session with specific model
            await self.scraper.initialize(model=service)

            # Get Blueprint from Model + Groq
            blueprint = await self.scraper.get_project_blueprint(user_request)
            
            # Create Project Context
            self.context = ProjectContext(
                project_name=blueprint.get('project_name', 'Auto_Project'),
                user_request=user_request,
                tech_stack=blueprint.get('tech_stack', []),
                file_list=[], 
                total_files=len(blueprint.get('files', [])),
                folder_structure=blueprint.get('folder_structure', {}),
                dependencies={} 
            )
            
            # Log the Plan
            print(f"\n📋 PLAN: {self.context.project_name}")
            print(f"📚 Stack: {self.context.tech_stack}")
            print(f"📂 Files to Create: {len(blueprint.get('files', []))}\n")

            # ---------------------------------------------------------
            # PHASE 2: CODING & BUILDING (FILE BY FILE)
            # ---------------------------------------------------------
            logger.info("👨‍💻 Phase 2: Coding & Building...")
            
            files_to_create = blueprint.get('files', [])
            
            for index, file_info in enumerate(files_to_create):
                self.context.current_file_index = index
                file_name = file_info['name']
                purpose = file_info['purpose']
                
                logger.info(f"Drafting File ({index+1}/{len(files_to_create)}): {file_name}...")
                
                # A. Generate Code via ProScraper
                req = FileRequest(
                    file_name=file_name,
                    purpose=purpose,
                    context=self.context
                )
                response = await self.scraper.generate_file(req)
                
                if response.success and response.code.strip():
                    # Update Context
                    self.context.generated_files.append(file_name)
                    
                    # B. Save File via DevOps Agent
                    build_res = await self.devops.save_code_to_file(
                        file_name, 
                        response.code, 
                        self.context
                    )
                    
                    if build_res.success:
                        logger.info(f"✅ Saved: {file_name}")
                    else:
                        logger.error(f"❌ Save Failed for {file_name}: {build_res.message}")
                        self.context.failed_files.append(file_name)
                else:
                    logger.error(f"❌ Generation Failed for {file_name} (Empty or Extraction Failed)")
                    self.context.failed_files.append(file_name)

            # ---------------------------------------------------------
            # 🛑 CRITICAL CHECK: STOP IF EXTRACTION FAILED
            # ---------------------------------------------------------
            if not self.context.generated_files:
                err_msg = "❌ Project Failed: No files were generated/extracted. Check Browser/Selectors."
                logger.error(err_msg)
                return err_msg

            # ---------------------------------------------------------
            # PHASE 3: ENVIRONMENT SETUP
            # ---------------------------------------------------------
            logger.info("\n📦 Phase 3: Environment Setup (Visible Windows)...")
            
            # Create Virtual Environment
            await self.devops.create_virtual_env(self.context)
            
            # Install Dependencies (if requirements.txt exists)
            await self.devops.install_dependencies(self.context)

            # ---------------------------------------------------------
            # PHASE 4: VERIFICATION & SELF-HEALING
            # ---------------------------------------------------------
            logger.info("\n🩺 Phase 4: Verification & Healing...")
            heal_summary = await self.verify_and_heal()

            # ---------------------------------------------------------
            # FINALIZE & RETURN RESULT
            # ---------------------------------------------------------
            project_path = self.devops.workspace_root / self.context.project_name.replace(" ", "_")
            
            result_msg = (
                f"✨ **PROJECT COMPLETED: {self.context.project_name}**\n"
                f"📂 **Location:** `{project_path}`\n"
                f"📚 **Tech Stack:** {', '.join(self.context.tech_stack)}\n"
                f"📄 **Files Generated:** {len(self.context.generated_files)}/{self.context.total_files}\n"
                f"🔧 **Self-Healing:** {heal_summary}"
            )
            
            print(f"\n{result_msg}\n")
            return result_msg

        except Exception as e:
            logger.error(f"❌ Critical Orchestrator Failure: {e}")
            return f"❌ Critical Error in Orchestrator: {str(e)}"
            
        finally:
            # Ensure browser is closed
            logger.info("🔴 Shutting down Orchestrator resources...")
            await self.scraper.shutdown()

    async def verify_and_heal(self) -> str:
        """
        Tries to run the project via VISIBLE CONSOLE. 
        If it crashes, reads logs and calls Auto-Debugger to fix it.
        """
        entry_point = self._find_entry_point()
        
        if not entry_point:
            logger.warning("⚠️ No obvious entry point (main.py/app.py) found. Skipping Run Verification.")
            return "Skipped (No entry point found)"

        logger.info(f"▶️  Attempting to run entry point: {entry_point}")
        
        # Try running up to 3 times (Original + 2 Fix Attempts)
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            # Run via Visible Console and capture success
            success, error_output = await self._run_project_visible(entry_point)
            
            if success:
                logger.info(f"✅ Project Ran Successfully (Attempt {attempt})")
                if attempt == 1:
                    return "Pass (First Try)"
                else:
                    return f"Fixed & Passed (After {attempt-1} repairs)"
            
            # IF FAILED:
            logger.warning(f"💥 Crash Detected (Attempt {attempt}/{max_attempts})")
            logger.info(f"Error Snippet: {error_output[:200]}...")
            
            if attempt < max_attempts:
                logger.info(f"🚑 calling Auto-Debugger to fix {entry_point}...")
                
                # 1. Read the Broken Code
                try:
                    project_path = self.devops.workspace_root / self.context.project_name.replace(" ", "_")
                    full_path = project_path / entry_point
                    broken_code = full_path.read_text(encoding='utf-8')
                    
                    # 2. Call Debugger (Delegates to ProScraper)
                    fix_result = await self.debugger.analyze_and_fix(
                        file_name=entry_point,
                        code=broken_code,
                        error_msg=error_output,
                        context=self.context
                    )
                    
                    if fix_result.fixed:
                        logger.info("✅ Debugger returned fixed code. Applying...")
                        # 3. Save the Fixed Code
                        await self.devops.save_code_to_file(entry_point, fix_result.final_code, self.context)
                        logger.info("🔄 Retrying run...")
                    else:
                        logger.error("❌ Debugger could not fix the code.")
                        return "Failed (Debugger couldn't fix)"
                        
                except Exception as e:
                    logger.error(f"❌ Error during healing process: {e}")
                    return f"Failed (Healing Error: {e})"
            else:
                logger.error("❌ Max attempts reached. Project is still broken.")
                return "Failed (Max attempts reached)"

        return "Failed (Unknown)"

    def _find_entry_point(self) -> Optional[str]:
        """Guesses the main file to run based on common names."""
        candidates = ["main.py", "app.py", "index.py", "run.py", "start.py", "game.py", "gui.py"]
        
        for f in self.context.generated_files:
            if f in candidates: return f
        for f in self.context.generated_files:
            if f.endswith(".py") and "test" not in f:
                if "main" in f or "app" in f or "game" in f: return f
        
        for f in self.context.generated_files:
            if f.endswith(".py"): return f     
        return None

    async def _run_project_visible(self, entry_file: str) -> Tuple[bool, str]:
        """
        Runs the python script in a VISIBLE console window.
        Logs output to a file and monitors it for crashes.
        Uses 'start /WAIT' to ensure the window stays open long enough to be useful.
        """
        project_path = self.devops.workspace_root / self.context.project_name.replace(" ", "_")
        
        # Determine Python Executable
        if sys.platform == "win32":
            python_exe = project_path / "venv" / "Scripts" / "python.exe"
        else:
            python_exe = project_path / "venv" / "bin" / "python"
            
        if not python_exe.exists():
            logger.warning("⚠️ Venv python not found, falling back to system python.")
            python_exe = sys.executable

        # Create Logs Directory
        log_dir = project_path / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"run_{int(time.time())}.log"
        
        try:
            logger.info(f"🖥️  Launching App: {entry_file} (Check new window)")
            
            if sys.platform == "win32":
                # Logic: Run, Redirect to log. If fail (||), type log and wait.
                # 'start /WAIT' allows us to launch a separate window but wait for it to finish.
                chained_cmd = (
                    f'"{python_exe}" {entry_file} > "{log_file}" 2>&1 '
                    f'|| (echo. && echo ❌ CRASHED && type "{log_file}" && timeout /t 10)'
                )
                
                full_cmd = f'start "Kirti App: {entry_file}" /WAIT cmd /c "{chained_cmd}"'
                
                subprocess.run(full_cmd, shell=True, cwd=str(project_path))
            else:
                # Non-windows fallback
                subprocess.Popen([str(python_exe), entry_file], cwd=str(project_path))
            
            # Monitor Log for Errors (Double Check)
            if log_file.exists():
                try:
                    content = log_file.read_text(encoding='utf-8', errors='ignore')
                    # Check for Python Crash Signatures
                    if "Traceback (most recent call last)" in content or "ModuleNotFoundError" in content or "SyntaxError" in content:
                        return False, content
                except: pass

            return True, ""
                
        except Exception as e:
            return False, str(e)

# ============================================================================
# 🧪 INTELLIGENT TEST BLOCK (Auto-Switching)
# ============================================================================
if __name__ == "__main__":
    async def test_god_mode():
        orchestrator = SelfHealingOrchestrator()
        
        # 👇 YAHAN APNA PROMPT LIKH
        # Examples:
        # 1. "Create a Calculator using Gemini"
        # 2. "Create a To-Do list using ChatGPT"
        # 3. "Create a Snake Game" (Defaults to Perplexity)
        
        TEST_PROMPT = "create a website similar to zomato using html, css, js, python and sql lite database create a interactive gui and frontend"
        
        # --- 🧠 AUTO-DETECT MODEL LOGIC ---
        prompt_lower = TEST_PROMPT.lower()
        
        if "chatgpt" in prompt_lower:
            SERVICE = "chatgpt"
        elif "gemini" in prompt_lower:
            SERVICE = "gemini"
        elif "perplexity" in prompt_lower:
            SERVICE = "perplexity"
        else:
            SERVICE = "perplexity" # Default
            
        print(f"\n🤖 Auto-Detected Model: [{SERVICE.upper()}]")
        print(f"🧪 Testing Orchestrator with prompt: '{TEST_PROMPT}'")
        
        # Run with detected service
        result = await orchestrator.create_project(TEST_PROMPT, service=SERVICE)
        
        print("\n\n" + "="*50)
        print("FINAL OUTPUT FOR TELEGRAM:")
        print("="*50)
        print(result)

    try:
        asyncio.run(test_god_mode())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by User")
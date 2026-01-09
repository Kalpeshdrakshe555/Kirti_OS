# core/tools.py
"""
Kirti OS - System Tools (Fixed: Crash-Proof Arguments & Browser Support)
Purpose: Handles tools safely even if AI forgets arguments.
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path
from typing import Dict, Any
import pyautogui
import psutil

# Import Browser Tool (Make sure browser_tool.py exists!)
from Kirti_OS.core.browser_tool import BrowserToolWrapper as RawBrowserWrapper

logger = logging.getLogger(__name__)
IS_WINDOWS = sys.platform == "win32"
WORKSPACE_DIR = Path(r"D:\test_bot")

# ============================================================================
# HELPER: SAFE PATH
# ============================================================================
def get_safe_path(path_str: str) -> Path:
    try:
        clean_path = str(path_str).replace("'", "").replace('"', "").strip()
        if ":" in clean_path: clean_path = os.path.splitdrive(clean_path)[1]
        clean_path = clean_path.lstrip("/\\")
        full_path = WORKSPACE_DIR / clean_path
        return full_path
    except:
        return WORKSPACE_DIR / "unknown_file.txt"

# ============================================================================
# 1. FILE SYSTEM (Safe)
# ============================================================================
class FileManager:
    @staticmethod
    async def create_file(**kwargs) -> str:
        # Smart Argument Extraction
        path = kwargs.get('path') or kwargs.get('filename')
        content = kwargs.get('content') or kwargs.get('code') or ""
        
        if not path: return "❌ Error: Missing 'path' argument for create_file."
        
        try:
            final_path = get_safe_path(path)
            final_path.parent.mkdir(parents=True, exist_ok=True)
            final_path.write_text(content, encoding='utf-8')
            return f"✅ File Created: `{final_path}`"
        except Exception as e:
            return f"❌ Create Failed: {e}"
    
    @staticmethod
    async def read_file(**kwargs) -> str:
        path = kwargs.get('path')
        if not path: return "❌ Error: Missing path."
        try:
            p = get_safe_path(path)
            if not p.exists(): return "⚠️ File not found."
            return p.read_text(encoding='utf-8')[:2000]
        except Exception as e: return f"❌ Error: {e}"

    @staticmethod
    async def list_directory(**kwargs) -> str:
        path = kwargs.get('path', '')
        try:
            target = get_safe_path(path) if path else WORKSPACE_DIR
            if not target.exists(): return "⚠️ Folder not found."
            items = [f"{'📁' if i.is_dir() else '📄'} {i.name}" for i in target.iterdir()]
            return f"📂 Files in `{target.name}`:\n" + "\n".join(items[:20])
        except Exception as e: return f"❌ Error: {e}"

# ============================================================================
# 2. BROWSER TOOLS (Crash-Proof Wrapper)
# ============================================================================
class SafeBrowserWrapper:
    @staticmethod
    async def search_web(**kwargs) -> str:
        """
        Handles AI mistakes. If 'project_type' is missing, it guesses from 'query'.
        """
        # Try to find arguments in various keys the AI might use
        p_type = kwargs.get('project_type') or kwargs.get('query') or kwargs.get('topic') or "Modern Website"
        tech = kwargs.get('tech_stack') or kwargs.get('technology') or "HTML/CSS"
        
        logger.info(f"🌐 Browsing for: {p_type} using {tech}")
        
        # Call the actual browser tool
        return await RawBrowserWrapper.search_web(project_type=p_type, tech_stack=tech)

    @staticmethod
    async def quick_search(**kwargs) -> str:
        query = kwargs.get('query') or kwargs.get('q') or "Latest tech news"
        return await RawBrowserWrapper.quick_search(query=query)

# ============================================================================
# 3. APP & SYSTEM (Safe)
# ============================================================================
class AppManager:
    @staticmethod
    async def open_app(**kwargs) -> str:
        # Handle if AI forgets app_name
        app_name = kwargs.get('app_name') or kwargs.get('name') or kwargs.get('app')
        
        if not app_name: return "❌ Error: Tell me which app to open (e.g., 'Open Notepad')."
        
        try:
            if IS_WINDOWS: os.startfile(app_name)
            else: subprocess.Popen(app_name, shell=True)
            return f"✅ Opened {app_name}"
        except:
            pyautogui.press("win"); time.sleep(0.5)
            pyautogui.write(app_name); time.sleep(0.5)
            pyautogui.press("enter")
            return f"✅ Searched & Opened {app_name}"

    @staticmethod
    async def close_app(**kwargs) -> str:
        app_name = kwargs.get('app_name') or kwargs.get('name')
        if not app_name: return "❌ Missing app name."
        count = 0
        for p in psutil.process_iter(['name']):
            if app_name.lower() in (p.info['name'] or "").lower():
                try: p.kill(); count+=1
                except: pass
        return f"💀 Killed {count} processes."

# ============================================================================
# 4. BASIC CONTROLS
# ============================================================================
class SystemTools:
    @staticmethod
    async def volume_control(**kwargs):
        action = kwargs.get('action', 'mute') # Internal helper logic if needed
        # But usually called directly via wrapper
        return "Executed"

# ============================================================================
# REGISTRY (Mapping)
# ============================================================================
class ToolRegistry:
    # Lambda functions used to map specific calls to general handlers or specific params
    TOOLS = {
        # Power
        "shutdown": lambda **k: PowerControl.shutdown(10),
        "restart": lambda **k: PowerControl.restart(10),
        "lock": lambda **k: PowerControl.lock_screen(),
        
        # Audio (Wrap in lambda to ignore extra args)
        "mute": lambda **k: VolumeControl.mute(),
        "volume_up": lambda **k: VolumeControl.volume_up(),
        "volume_down": lambda **k: VolumeControl.volume_down(),
        
        # Apps
        "open_app": AppManager.open_app,
        "close_app": AppManager.close_app,
        
        # Window / Keyboard
        "minimize_all": lambda **k: WindowManager.minimize_all(),
        "type_text": lambda **k: WindowManager.type_text(k.get('text', '')),
        "press_key": lambda **k: WindowManager.press_key(k.get('key', 'enter')),
        
        # Files (Using the Safe Classes)
        "create_file": FileManager.create_file,
        "read_file": FileManager.read_file,
        "list_directory": FileManager.list_directory,
        "execute_command": lambda **k: CommandExecutor.execute(k.get('command', 'echo')),
        
        # Browser (The Fix)
        "search_web": SafeBrowserWrapper.search_web,
        "quick_search": SafeBrowserWrapper.quick_search
    }
    
    @classmethod
    async def execute(cls, name, **kwargs):
        if name in cls.TOOLS:
            # Pass all arguments (kwargs) to the function
            return await cls.TOOLS[name](**kwargs)
        return f"❌ Unknown Tool: {name}"

# --- Minimal implementations for dependencies to avoid import errors ---
class PowerControl:
    @staticmethod
    def shutdown(t): os.system(f"shutdown /s /t {t}") if IS_WINDOWS else ""
    @staticmethod
    def restart(t): os.system(f"shutdown /r /t {t}") if IS_WINDOWS else ""
    @staticmethod
    def lock_screen(): os.system("rundll32.exe user32.dll,LockWorkStation") if IS_WINDOWS else ""

class VolumeControl:
    @staticmethod
    def mute(): pyautogui.press("volumemute"); return "🔇 Muted"
    @staticmethod
    def volume_up(): pyautogui.press("volumeup"); return "🔊 Up"
    @staticmethod
    def volume_down(): pyautogui.press("volumedown"); return "🔉 Down"

class WindowManager:
    @staticmethod
    def minimize_all(): pyautogui.hotkey('win','d'); return "Desktop"
    @staticmethod
    def type_text(t): pyautogui.write(t); return "Typed"
    @staticmethod
    def press_key(k): pyautogui.press(k); return f"Key {k}"

class CommandExecutor:
    @staticmethod
    def execute(c):
        try: return subprocess.run(c, shell=True, capture_output=True, text=True, cwd=WORKSPACE_DIR).stdout[:500]
        except Exception as e: return str(e)
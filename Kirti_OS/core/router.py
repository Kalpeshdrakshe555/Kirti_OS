# Kirti_OS/core/router.py
"""
Kirti OS - Task Router (Self-Healing Edition)
Purpose: Routes complex projects to the Self-Healing Orchestrator (Pro Models)
and handles simple tasks via Local/Groq Brain.
State: Preserves ALL previous features (Circuit Breaker, Key Rotation, System Collector).
UPDATED: Added Multi-Model Selection for Project Building.
"""

import asyncio
import logging
import os
import re
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import psutil
from dotenv import load_dotenv

from groq import AsyncGroq
from google import genai
from google.genai import types

# 🔥 NEW: Import the Self-Healing Orchestrator
# Make sure self_healing_orchestrator.py is in the same directory (core)
try:
    from Kirti_OS.core.self_healing_orchestrator import SelfHealingOrchestrator
except ImportError:
    # Fallback for local testing if running from root
    from self_healing_orchestrator import SelfHealingOrchestrator

# Load Env Vars
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, "../../.env")
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS (SMART MODEL LADDER - UNTOUCHED)
# ============================================================================

LOGIC_MODEL_ID = "llama-3.3-70b-versatile"

VISION_MODELS = [
    "gemini-2.0-flash",                     # 💎 BEST & FRESH
    "gemini-2.0-flash-lite-preview-02-05", # 🥈 BACKUP
    "gemini-1.5-flash",                     # 🥉 STABLE
    "gemini-1.5-pro",                       # OLD RELIABLE
    "gemini-1.5-flash-8b"                   # FALLBACK
]

# ============================================================================
# DATA STRUCTURES (UNTOUCHED + NEW TYPE)
# ============================================================================

class TaskType(Enum):
    CODING = "coding"
    VISION = "vision"
    ACTION = "action"
    SYSTEM_STATUS = "system_status"
    PROJECT_BUILD = "project_build"  # 🔥 NEW: For Self-Healing Projects
    GENERIC = "generic"

@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any]

@dataclass
class RouterResponse:
    success: bool
    result: str
    model_used: str
    latency_ms: float
    task_type: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    error: Optional[str] = None

@dataclass
class CircuitBreakerState:
    model_name: str
    failures: int = 0
    last_failure_time: Optional[datetime] = None
    is_open: bool = False
    open_until: Optional[datetime] = None

# ============================================================================
# CIRCUIT BREAKER (UNTOUCHED - FULL LOGIC)
# ============================================================================

class CircuitBreaker:
    FAILURE_THRESHOLD = 3
    OPEN_TIMEOUT = 300  # 5 minutes
    
    def __init__(self):
        self.state: Dict[str, CircuitBreakerState] = {}
    
    def record_failure(self, model_name: str) -> None:
        if model_name not in self.state:
            self.state[model_name] = CircuitBreakerState(model_name=model_name)
        
        breaker = self.state[model_name]
        breaker.failures += 1
        breaker.last_failure_time = datetime.now()
        
        if breaker.failures >= self.FAILURE_THRESHOLD:
            breaker.is_open = True
            breaker.open_until = datetime.now() + timedelta(seconds=self.OPEN_TIMEOUT)
            logger.error(f"🔴 Circuit OPEN for {model_name}")
    
    def record_success(self, model_name: str) -> None:
        if model_name in self.state:
            self.state[model_name].failures = 0
            self.state[model_name].is_open = False
    
    def is_available(self, model_name: str) -> bool:
        if model_name not in self.state: return True
        breaker = self.state[model_name]
        
        if breaker.is_open and breaker.open_until:
            if datetime.now() < breaker.open_until:
                return False
            else:
                breaker.is_open = False
                breaker.failures = 0
                return True
        return True
    
    def get_status(self) -> Dict:
        return {name: {"failures": b.failures, "open": b.is_open} for name, b in self.state.items()}

# ============================================================================
# HELPERS (Dual-Mode Parser Preserved)
# ============================================================================

class IntentParser:
    """
    Supports creating files with complex code blocks AND folders AND simple tools.
    """
    @staticmethod
    def extract_tool_calls(text: str) -> List[ToolCall]:
        tool_calls = []
        
        # 1. ARCHITECT MODE: Multi-line tool calls (For creating files/folders)
        multiline_pattern = r'<TOOL:(\w+)>\s*\n(.*?)\n</TOOL>'
        
        for match in re.finditer(multiline_pattern, text, re.DOTALL):
            tool_name = match.group(1)
            body = match.group(2)
            arguments = {}
            
            path_match = re.search(r'PATH:\s*(.+?)(?:\n|$)', body)
            if path_match:
                arguments['path'] = path_match.group(1).strip()
            
            content_match = re.search(r'CONTENT:\s*\n(.*)', body, re.DOTALL)
            if content_match:
                content = content_match.group(1)
                arguments['content'] = content.rstrip()
            
            tool_calls.append(ToolCall(tool_name, arguments))

        # 2. SIMPLE MODE: Single-line tool calls (Mute, Volume, Search Web)
        simple_pattern = r'<TOOL:(\w+)(?:\|([^>]+))?>'
        
        clean_text = re.sub(multiline_pattern, '', text, flags=re.DOTALL)
        
        for name, args_str in re.findall(simple_pattern, clean_text):
            args = {}
            if args_str:
                for part in args_str.split('|'):
                    if '=' in part:
                        k, v = part.split('=', 1)
                        args[k.strip()] = v.strip()
            tool_calls.append(ToolCall(name, args))
            
        return tool_calls

class TaskClassifier:
    VISION_KEYWORDS = {'see', 'look', 'screenshot', 'what is this', 'image', 'photo', 'scan', 'analyze', 'dekho', 'screen'}
    
    # 🔥 UPDATED: Project Keywords for Self-Healing Orchestrator
    PROJECT_KEYWORDS = {
        'create a', 'full stack', 'build a', 'make an app', 'create a game', 
        'develop a', 'new project', 'snake game', 'write a program', 'code for',
        'software', 'application', 'website'
    }

    ACTION_KEYWORDS = {
        'open', 'close', 'shutdown', 'mute', 'volume', 'lock', 'minimize', 'type', 'run', 
        'create file', 'save', 'get file', 'download', 'make file', 
        'search', 'find', 'modern', 'latest', 'tailwind', 'documentation', 'example', 'fetch'
    }
    
    STATUS_KEYWORDS = {'status', 'ram', 'cpu', 'battery', 'health'}

    async def classify(self, prompt: str, has_image: bool) -> TaskType:
        prompt = prompt.lower()
        
        # 🚀 PRIORITY FIX: Check for Project Build FIRST (Even if image is present)
        # This allows "Create a game based on this screenshot"
        if any(k in prompt for k in self.PROJECT_KEYWORDS): 
            return TaskType.PROJECT_BUILD
            
        if has_image: return TaskType.VISION
        
        if any(k in prompt for k in self.STATUS_KEYWORDS): return TaskType.SYSTEM_STATUS
        if any(k in prompt for k in self.ACTION_KEYWORDS): return TaskType.ACTION
        if any(k in prompt for k in self.VISION_KEYWORDS): return TaskType.VISION
        return TaskType.CODING

class SystemCollector:
    @staticmethod
    async def get_status():
        try:
            ram = psutil.virtual_memory()
            cpu = psutil.cpu_percent()
            battery = psutil.sensors_battery()
            plugged = "🔌" if battery and battery.power_plugged else "🔋"
            return f"💻 CPU: {cpu}% | RAM: {ram.percent}% | BAT: {battery.percent if battery else 'N/A'}% {plugged}"
        except:
            return "🖥️ System Status Unavailable"

# ============================================================================
# AI BRAINS (Groq + Gemini Preserved)
# ============================================================================

class GroqBrain:
    # Keeps the old prompt for simple tasks
    SYSTEM_PROMPT = """You are Kirti OS. Use tools for simple PC tasks.
    Tools: open_app, shutdown, mute, search_web, create_file (for single files).
    Format: <TOOL:name|arg=val>"""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None

    async def generate(self, prompt: str) -> str:
        if not self.client: return "❌ Groq Key Missing"
        try:
            completion = await self.client.chat.completions.create(
                messages=[{"role": "system", "content": self.SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                model=LOGIC_MODEL_ID, 
                temperature=0.1,
                max_tokens=4096 
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"❌ Groq Error: {e}"

class GeminiBrain:
    """Handles Vision with Key Rotation & Smart Model Selection (UNTOUCHED)"""
    
    def __init__(self):
        self.keys = []
        if os.getenv("GEMINI_API_KEY"): self.keys.append(os.getenv("GEMINI_API_KEY"))
        if os.getenv("GEMINI_API_KEY_1"): self.keys.append(os.getenv("GEMINI_API_KEY_1"))
        if os.getenv("GEMINI_API_KEY_2"): self.keys.append(os.getenv("GEMINI_API_KEY_2"))
        
        self.current_key_index = 0
        self.client = None
        self._refresh_client()

    def _refresh_client(self):
        if not self.keys:
            logger.error("❌ No Gemini Keys Found!")
            self.client = None
            return
        
        current_key = self.keys[self.current_key_index]
        try:
            self.client = genai.Client(api_key=current_key)
            logger.info(f"🔑 Using Gemini Key #{self.current_key_index + 1}")
        except Exception as e:
            logger.error(f"❌ Failed to init Gemini Key: {e}")

    def _rotate_key(self):
        if len(self.keys) <= 1: return False
        self.current_key_index = (self.current_key_index + 1) % len(self.keys)
        logger.info(f"🔄 Rotating to Gemini Key #{self.current_key_index + 1}")
        self._refresh_client()
        return True

    async def analyze(self, prompt: str, image_bytes: bytes) -> str:
        if not self.client: return "❌ Gemini Client Not Initialized"
        contents = [types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"), prompt]
        
        for model in VISION_MODELS:
            try:
                logger.info(f"👁️ Testing Model: {model} with Key #{self.current_key_index + 1}...")
                response = await self.client.aio.models.generate_content(model=model, contents=contents)
                return response.text
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "quota" in err or "exhausted" in err:
                    if self._rotate_key():
                        try:
                            response = await self.client.aio.models.generate_content(model=model, contents=contents)
                            return response.text
                        except Exception: pass
                continue
        return "❌ Vision Failed: All Models & Keys Exhausted."

# ============================================================================
# MAIN ROUTER (UPDATED FOR SELF-HEALING)
# ============================================================================

class TaskRouter:
    def __init__(self):
        self.classifier = TaskClassifier()
        self.circuit_breaker = CircuitBreaker()
        self.groq = GroqBrain()
        self.gemini = GeminiBrain()
        self.parser = IntentParser()
        self.sys = SystemCollector()
        
        # 🔥 Initialize the Self-Healing Orchestrator
        self.orchestrator = SelfHealingOrchestrator()
        
        # Stats
        self.stats = {'requests': 0, 'actions': 0}
        logger.info("TaskRouter (God Mode + Self-Healing) Initialized")

    async def route(self, prompt: str, image_bytes: bytes = None) -> RouterResponse:
        start = asyncio.get_event_loop().time()
        self.stats['requests'] += 1
        
        has_image = bool(image_bytes)
        task = await self.classifier.classify(prompt, has_image)
        
        result = ""
        model = "none"
        tool_calls = []
        
        try:
            # 🚀 TASK 1: PROJECT BUILD (Self-Healing Orchestrator)
            if task == TaskType.PROJECT_BUILD:
                # 🔥 MODEL SELECTION LOGIC
                model_choice = "perplexity" # Default
                if "chatgpt" in prompt.lower(): model_choice = "chatgpt"
                elif "gemini" in prompt.lower(): model_choice = "gemini"
                elif "perplexity" in prompt.lower(): model_choice = "perplexity"

                logger.info(f"🔀 Routing to Self-Healing Orchestrator (Model: {model_choice.upper()})...")
                
                # Execute via Pro Models - Orchestrator handles everything
                # Note: create_project returns a String message now
                project_msg = await self.orchestrator.create_project(prompt, service=model_choice)
                
                result = project_msg
                model = f"God-Mode-{model_choice.capitalize()}"
            
            # 🚀 TASK 2: SYSTEM STATUS
            elif task == TaskType.SYSTEM_STATUS:
                result = await self.sys.get_status()
                model = "local_system"
            
            # 🚀 TASK 3: VISION
            elif task == TaskType.VISION:
                if not has_image:
                    result = await self.groq.generate(prompt)
                    model = LOGIC_MODEL_ID
                    tool_calls = self.parser.extract_tool_calls(result)
                else:
                    if self.circuit_breaker.is_available("gemini"):
                        try:
                            result = await self.gemini.analyze(prompt, image_bytes)
                            model = "gemini-smart-ladder"
                            self.circuit_breaker.record_success("gemini")
                        except Exception as e:
                            self.circuit_breaker.record_failure("gemini")
                            result = f"❌ Vision Error: {e}"
                    else:
                        result = "⚠️ Vision Circuit Open"
            
            # 🚀 TASK 4: GENERIC CODING / ACTIONS (Old Groq Logic)
            else:
                if self.circuit_breaker.is_available("groq"):
                    try:
                        result = await self.groq.generate(prompt)
                        model = LOGIC_MODEL_ID
                        tool_calls = self.parser.extract_tool_calls(result)
                        if tool_calls: self.stats['actions'] += len(tool_calls)
                        self.circuit_breaker.record_success("groq")
                    except Exception as e:
                        self.circuit_breaker.record_failure("groq")
                        result = f"❌ Logic Error: {e}"
                else:
                    result = "⚠️ Logic Circuit Open"

            latency = (asyncio.get_event_loop().time() - start) * 1000
            return RouterResponse(True, result, model, latency, task.value, tool_calls)
            
        except Exception as e:
            logger.error(f"Routing Critical Error: {e}")
            return RouterResponse(False, str(e), "error", 0, "error")

    async def get_statistics(self): 
        return {**self.stats, "circuit": self.circuit_breaker.get_status()}
    
    async def health_check(self): 
        return {"status": "healthy", "gemini_key_idx": self.gemini.current_key_index}
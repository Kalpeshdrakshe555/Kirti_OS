# core/agent_manager.py
"""
Kirti OS - Multi-Agent Orchestrator (God Mode - Enterprise Edition)
Purpose: Sequential agent chain for professional full-stack project generation.
Architecture: 5 specialized agents with shared state machine.
"""

import asyncio
import logging
import json
import re
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from dotenv import load_dotenv
from groq import AsyncGroq

# Tools
from Kirti_OS.core.tools import ToolRegistry
from Kirti_OS.core.browser_tool import BrowserToolWrapper

load_dotenv()
logger = logging.getLogger(__name__)

# ============================================================================
# LOCAL LLM CLIENT (To avoid Circular Import with Router)
# ============================================================================
class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = AsyncGroq(api_key=self.api_key)
        self.model = "llama-3.3-70b-versatile"

    async def generate(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        try:
            kwargs = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "model": self.model,
                "temperature": 0.2,
                "max_tokens": 4096
            }
            if json_mode: kwargs["response_format"] = {"type": "json_object"}
            
            completion = await self.client.chat.completions.create(**kwargs)
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM Error: {e}")
            return "{}" if json_mode else ""

# ============================================================================
# SHARED STATE MACHINE
# ============================================================================
@dataclass
class ProjectState:
    user_request: str
    project_name: str = ""
    project_type: str = ""
    tech_stack: List[str] = field(default_factory=list)
    folder_structure: Dict[str, Any] = field(default_factory=dict)
    database_schema: Dict[str, Any] = field(default_factory=dict)
    file_list: List[str] = field(default_factory=list)
    file_descriptions: Dict[str, str] = field(default_factory=dict)
    code_snippets: Dict[str, str] = field(default_factory=dict)
    created_files: List[str] = field(default_factory=list)
    logo_path: str = ""
    images_added: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    errors: List[str] = field(default_factory=list)

# ============================================================================
# AGENT 1: BLUEPRINT MAKER
# ============================================================================
class Agent1_Blueprint:
    SYSTEM_PROMPT = """You are a Principal Software Architect.
    Plan a PRODUCTION-GRADE file structure.
    
    RULES:
    1. **Avoid "Basic" structures.** Use modularity.
    2. If Flask: Include `app.py`, `models.py`, `config.py`, `requirements.txt`.
    3. If Frontend: Include `templates/base.html`, `static/css/style.css`.
    4. Be EXHAUSTIVE. List every file needed.
    
    OUTPUT JSON:
    {
      "project_name": "Name",
      "project_type": "web_app",
      "tech_stack": ["flask", "tailwind", "sqlite"],
      "folder_structure": { "ProjectName": ["file1", "file2"] },
      "file_descriptions": { "file1": "purpose" },
      "dependencies": ["flask", "sqlalchemy"]
    }
    """
    
    def __init__(self, brain: LLMClient): self.brain = brain

    async def execute(self, state: ProjectState) -> ProjectState:
        logger.info("🏗️ AGENT 1: Blueprint Maker Starting...")
        res = await self.brain.generate(self.SYSTEM_PROMPT, state.user_request, json_mode=True)
        
        try:
            data = json.loads(res)
            state.project_name = data.get("project_name", "Project")
            state.tech_stack = data.get("tech_stack", [])
            state.file_descriptions = data.get("file_descriptions", {})
            
            # Extract flat file list
            structure = data.get("folder_structure", {})
            for folder, files in structure.items():
                state.file_list.extend(files)
                
            logger.info(f"✅ Blueprint: {len(state.file_list)} files planned for {state.project_name}")
        except:
            logger.error("❌ Blueprint Failed")
        return state

# ============================================================================
# AGENT 2: RESEARCHER
# ============================================================================
class Agent2_Researcher:
    def __init__(self, brain: LLMClient): self.brain = brain

    async def execute(self, state: ProjectState) -> ProjectState:
        logger.info("🔬 AGENT 2: Researcher Starting...")
        
        queries = []
        if "flask" in state.tech_stack: queries.append("flask production best practices 2025")
        if "tailwind" in state.tech_stack: queries.append("modern glassmorphism dashboard tailwind css design")
        
        for q in queries[:2]:
            logger.info(f"🔎 Searching: {q}")
            res = await BrowserToolWrapper.search_web(project_type=q, tech_stack="modern")
            state.code_snippets[q] = res[:4000] # Store snippet
            await asyncio.sleep(2)
            
        return state

# ============================================================================
# AGENT 3: BUILDER (ITERATIVE + PRO UI)
# ============================================================================
class Agent3_Builder:
    def __init__(self, brain: LLMClient): self.brain = brain

    def _order_files(self, files: List[str]) -> List[str]:
        # Smart Ordering: Config -> Models -> App -> Templates
        ordered = []
        priority = ["requirements", "config", "models", "database", "app.py", "main.py", "base.html"]
        
        for p in priority:
            for f in files:
                if p in f and f not in ordered: ordered.append(f)
        
        for f in files: 
            if f not in ordered: ordered.append(f)
        return ordered

    async def execute(self, state: ProjectState) -> ProjectState:
        logger.info("🏭 AGENT 3: Builder Starting (Pro Mode)...")
        ordered_files = self._order_files(state.file_list)
        total = len(ordered_files)
        
        for i, filename in enumerate(ordered_files):
            logger.info(f"   [{i+1}/{total}] Building: {filename}")
            
            # 🔥 PRO UI PROMPT
            prompt = f"""You are a Senior Developer.
            Project: {state.project_name} | Stack: {state.tech_stack}
            File: {filename}
            Purpose: {state.file_descriptions.get(filename, 'Code')}
            
            RESEARCH CONTEXT:
            {list(state.code_snippets.values())[0] if state.code_snippets else 'Standard Best Practices'}
            
            🔥 VISUAL RULES (If HTML/CSS):
            1. **Dark Mode & Glassmorphism:** Use `bg-slate-900`, `backdrop-blur-xl`, `bg-white/10`.
            2. **Typography:** `font-sans antialiased text-gray-100`.
            3. **Modern Components:** Rounded corners (`rounded-2xl`), deep shadows (`shadow-2xl`).
            4. **No Basic White Pages.**
            
            🔥 LOGIC RULES:
            1. **Production Ready:** No "TODOs". Full implementation.
            2. **Error Handling:** Try/Except blocks.
            
            Output ONLY the code.
            """
            
            code = await self.brain.generate(prompt, f"Generate {filename}")
            
            # Clean
            code = re.sub(r'^```\w*\n', '', code)
            code = re.sub(r'\n```$', '', code)
            
            # Save
            path = f"{state.project_name}/{filename}"
            await ToolRegistry.execute("create_file", path=path, content=code)
            state.created_files.append(filename)
            await asyncio.sleep(1) # Rate limit safety
            
        return state

# ============================================================================
# AGENT 4: VISUALIZER
# ============================================================================
class Agent4_Visualizer:
    def __init__(self, brain: LLMClient): self.brain = brain

    async def execute(self, state: ProjectState) -> ProjectState:
        logger.info("🎨 AGENT 4: Visualizer (UI Injection)...")
        
        html_files = [f for f in state.created_files if f.endswith(".html")]
        if not html_files: return state
        
        # 1. Generate Logo
        logo_svg = f"""<svg width="40" height="40" xmlns="http://www.w3.org/2000/svg"><rect width="40" height="40" rx="10" fill="#3B82F6"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="Arial" font-size="24" fill="white">{state.project_name[0]}</text></svg>"""
        await ToolRegistry.execute("create_file", path=f"{state.project_name}/static/images/logo.svg", content=logo_svg)
        
        # 2. Inject Images & Logo into HTML
        for f in html_files[:3]:
            path = f"{state.project_name}/{f}"
            content = await ToolRegistry.execute("read_file", path=path)
            
            if "Error" in content: continue
            
            # Inject Logo
            if "<nav" in content and "logo.svg" not in content:
                content = content.replace("<nav", f'<nav>\n<img src="/static/images/logo.svg" class="h-10 w-10 mr-2">')
            
            # Inject Unsplash
            if "<img" not in content and "body" in content:
                 # Add Hero Image if missing
                 theme = state.tech_stack[0] if state.tech_stack else "technology"
                 img = f'<img src="https://source.unsplash.com/random/1200x400/?{theme},dark" class="w-full h-64 object-cover rounded-2xl shadow-lg mb-8">'
                 content = content.replace("<main", f"<main>\n{img}")
            
            await ToolRegistry.execute("create_file", path=path, content=content)
            
        return state

# ============================================================================
# MAIN ORCHESTRATOR (Renamed to AgentManager for compatibility)
# ============================================================================
class AgentManager:
    def __init__(self):
        self.brain = LLMClient()
        self.agent1 = Agent1_Blueprint(self.brain)
        self.agent2 = Agent2_Researcher(self.brain)
        self.agent3 = Agent3_Builder(self.brain)
        self.agent4 = Agent4_Visualizer(self.brain)

    async def execute_project(self, user_request: str) -> str:
        state = ProjectState(user_request=user_request)
        
        # Execute Chain
        state = await self.agent1.execute(state)
        state = await self.agent2.execute(state)
        state = await self.agent3.execute(state)
        state = await self.agent4.execute(state)
        
        return f"""
✨ **God-Level Project Built: {state.project_name}**
📂 Location: `D:\\test_bot\\{state.project_name}`
🛠️ Stack: {state.tech_stack}
📄 Files: {len(state.created_files)}

**Next Steps:**
1. `cd {state.project_name}`
2. `pip install -r requirements.txt`
3. `python app.py`
"""
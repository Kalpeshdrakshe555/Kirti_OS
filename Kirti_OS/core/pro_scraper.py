# Kirti_OS/core/pro_scraper.py

import asyncio
import logging
import json
import os
import re
from datetime import datetime
from typing import Dict, Any

from dotenv import load_dotenv
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, "../../.env")
load_dotenv(env_path)

from data_structures import ProjectContext, FileRequest, FileResponse
from browser_tool import init_browser, get_browser, close_browser, PersistentBrowser
from groq import AsyncGroq

logger = logging.getLogger("ProScraper")
logger.setLevel(logging.INFO)

class ProScraper:
    """
    The Brain that talks to Models.
    UPDATED: Includes 'Double Filtration' (Groq + Regex) to guarantee clean code.
    """

    def __init__(self):
        self.browser: PersistentBrowser = None
        
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.error("❌ CRITICAL: GROQ_API_KEY not found!")
            raise ValueError("GROQ_API_KEY is missing")
            
        self.groq_client = AsyncGroq(api_key=api_key)
        self.last_file_context: Dict[str, datetime] = {}

    async def initialize(self, model="perplexity"):
        logger.info(f"🤖 ProScraper Initializing Browser ({model})...")
        self.browser = await init_browser(headless=False, model=model)

    async def get_project_blueprint(self, user_request: str) -> Dict[str, Any]:
        if not self.browser: await self.initialize()
        logger.info(f"📋 Requesting Blueprint for: {user_request}")

        prompt = (
            f"Hi, I want to build a software project: '{user_request}'. "
            "Can you help me plan the file structure? Just list the files and their purpose. "
            "No code yet, just the plan."
        )

        await self.browser.send_prompt_to_perplexity(prompt, is_new_chat=True)
        response = await self.browser.get_latest_response()
        
        if not response or not response.text:
            raise RuntimeError("❌ Failed to get blueprint")

        return await self._parse_with_groq(response.text)

    async def _parse_with_groq(self, raw_text: str) -> Dict[str, Any]:
        """Convert raw plan text to JSON"""
        try:
            completion = await self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Extract JSON plan: {project_name, tech_stack, files: [{name, purpose}]}"},
                    {"role": "user", "content": raw_text[:6000]}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(completion.choices[0].message.content)
        except:
            return {"project_name": "Project_Auto", "files": []}

    async def generate_file(self, request: FileRequest) -> FileResponse:
        """Generates code and CLEANS it using Groq + Regex."""
        if not self.browser: await self.initialize()

        logger.info(f"🏗️  Generating File: {request.file_name}")

        prompt = (
            f"Okay, let's write the code for `{request.file_name}`. "
            f"Here is what it should do: {request.purpose}. "
            "IMPORTANT: Provide the FULL COMPLETE CODE."
        )

        await self.browser.send_prompt_to_perplexity(prompt, is_new_chat=False)
        response = await self.browser.get_latest_response()

        if not response or not response.primary_code:
            logger.warning(f"⚠️ No code content found for {request.file_name}")
            return FileResponse(request.file_name, "", {}, False)

        # 1. Groq Cleaning
        logger.info(f"🧼 Cleaning code for {request.file_name} with Groq...")
        groq_cleaned = await self._clean_code_with_groq(response.primary_code)
        
        # 2. 🔥 FINAL POLISH (Remove Markdown Backticks)
        final_code = self._post_process_code(groq_cleaned)

        self.last_file_context[request.file_name] = datetime.now()

        return FileResponse(
            file_name=request.file_name,
            code=final_code,
            metadata=response.metadata,
            success=True
        )

    async def _clean_code_with_groq(self, raw_content: str) -> str:
        """Uses Groq to extract valid code from conversation."""
        try:
            if len(raw_content) < 10: return raw_content

            prompt = f"""
            I have a raw text response that contains code.
            Extract ONLY the code. 
            - Do NOT include "Here is the code" or "I hope this helps".
            - You MAY include markdown backticks (```), I will strip them later.
            
            RAW TEXT:
            {raw_content[:15000]} 
            """
            # Truncated input to avoid token limits
            
            completion = await self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a Strict Code Extractor."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ Groq Cleaning Failed: {e}")
            return raw_content 

    def _post_process_code(self, code: str) -> str:
        """
        🔥 HARD CLEANER: Removes ```python and ``` wrappers manually.
        This guarantees the file starts with actual code.
        """
        # Remove top ```python or ```
        code = re.sub(r"^```[a-zA-Z]*\n", "", code.strip())
        # Remove bottom ```
        code = re.sub(r"\n```$", "", code.strip())
        
        # Fallback check if regex missed (sometimes specific newlines differ)
        if code.startswith("```"):
            lines = code.split('\n')
            if len(lines) > 1:
                code = '\n'.join(lines[1:]) # Drop first line
        
        if code.endswith("```"):
            code = code.rsplit('\n', 1)[0] # Drop last line
            
        return code.strip()

    async def debug_code(self, file_name: str, error_msg: str, full_code: str) -> str:
        is_fresh = False
        if file_name in self.last_file_context:
            if (datetime.now() - self.last_file_context[file_name]).total_seconds() < 600:
                is_fresh = True

        if is_fresh:
            logger.info(f"🧠 Context Fresh. Sending Error Only.")
            prompt = f"I got this error:\n{error_msg[-1000:]}\n\nFix it and return FULL CODE."
        else:
            logger.info(f"🧠 Context Stale. Sending Full Code.")
            prompt = f"File `{file_name}`:\n{full_code[:4000]}\nError:\n{error_msg}\nFix and return FULL CODE."

        await self.browser.send_prompt_to_perplexity(prompt, is_new_chat=False)
        response = await self.browser.get_latest_response()
        
        if response and response.primary_code:
            groq_clean = await self._clean_code_with_groq(response.primary_code)
            return self._post_process_code(groq_clean)
        return ""

    async def shutdown(self):
        await close_browser()
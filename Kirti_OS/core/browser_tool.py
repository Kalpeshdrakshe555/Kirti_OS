# Kirti_OS/core/browser_tools.py

"""
Persistent Browser Tools - STABLE SELECTOR EDITION
Purpose: Uses Model-Specific Selectors to extract text/code.
Reliable navigation and element interaction.
"""

import asyncio
import logging
import re
import os
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass

from playwright.async_api import async_playwright, BrowserContext, Page

# Logging
logger = logging.getLogger("BrowserTools")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('🌐 %(asctime)s - [%(levelname)s] - %(message)s', datefmt='%H:%M:%S')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# Config
@dataclass
class CodeBlockResponse:
    text: str
    code_blocks: List[str]
    primary_code: str
    metadata: Dict[str, Any]
    extraction_success: bool
    extraction_method: str

@dataclass
class SelectorConfig:
    name: str
    base_url: str
    textarea: List[str]
    send_button: List[str]
    stop_generating: List[str]
    copy_button: List[str] # Added back
    message_content: List[str] 

MODEL_SELECTORS: Dict[str, SelectorConfig] = {
    "perplexity": SelectorConfig(
        name="perplexity",
        base_url="https://www.perplexity.ai",
        textarea=["textarea", "[contenteditable='true']", "textarea[placeholder*='Ask']"],
        send_button=["button[aria-label*='send' i]", "button:has-text('Send')", "button[type='submit']"],
        stop_generating=["button:has-text('Stop')", "[aria-label*='stop' i]"],
        copy_button=["button:has-text('Copy')", "[data-testid*='copy' i]"],
        message_content=[".prose", "div[class*='prose']", "div[class*='answer']", "[dir='auto']"]
    ),
    "chatgpt": SelectorConfig(
        name="chatgpt",
        base_url="https://chat.openai.com",
        textarea=["#prompt-textarea", "textarea[data-id='root']"],
        send_button=["[data-testid='send-button']"],
        stop_generating=["[data-testid='stop-button']"],
        copy_button=["button:has-text('Copy code')", ".copy-btn"],
        message_content=[".markdown", "[data-message-author-role='assistant']"]
    ),
    "gemini": SelectorConfig(
        name="gemini",
        base_url="https://gemini.google.com",
        textarea=["[contenteditable='true']", "rich-textarea"],
        send_button=["button[aria-label*='Send']", ".send-button"],
        stop_generating=["[aria-label*='Stop']"],
        copy_button=["[aria-label*='Copy']"],
        message_content=["message-content", ".model-response-text"]
    )
}

class PersistentBrowser:
    MAX_WAIT_TIME = 300 
    POLLING_INTERVAL = 2

    def __init__(self, headless: bool = False, user_data_dir: Optional[Path] = None, model: str = "perplexity"):
        self.headless = headless
        self.user_data_dir = user_data_dir or self._get_default_user_data_dir()
        self.current_model = model
        self.selectors = MODEL_SELECTORS.get(model, MODEL_SELECTORS["perplexity"])
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_active = False

    def _get_default_user_data_dir(self) -> Path:
        home = Path.home()
        user_data = home / ".kirti_os" / "browser_profile"
        user_data.mkdir(parents=True, exist_ok=True)
        return user_data

    async def start_session(self) -> bool:
        if self.session_active: return True
        try:
            logger.info("🚀 Launching Browser Engine...")
            self.playwright = await async_playwright().start()
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-infobars"],
                viewport={"width": 1280, "height": 720}
            )
            # Still grant permissions, just in case
            await self.context.grant_permissions(["clipboard-read", "clipboard-write"])
            
            self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            
            logger.info(f"🌐 Navigating to {self.selectors.base_url}...")
            await self.page.goto(self.selectors.base_url, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            self.session_active = True
            logger.info("✅ Browser Session Ready!")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start browser: {e}")
            return False

    async def send_prompt_to_perplexity(self, prompt: str, is_new_chat: bool = False) -> bool:
        if not self.session_active: return False
        try:
            if is_new_chat:
                logger.info("🆕 Starting New Thread...")
                new_btn = await self._find_element([
                    "button:has-text('New Thread')", "button:has-text('New')", "[aria-label='New Thread']",
                    "[data-testid='new-chat-button']"
                ])
                if new_btn: 
                    await new_btn.click()
                    await asyncio.sleep(2)

            logger.info("🔍 Finding input...")
            textarea = await self._find_element(self.selectors.textarea)
            if not textarea:
                logger.error("❌ Input box not found!")
                return False

            await textarea.click()
            await textarea.fill("")
            logger.info(f"⌨️  Pasting prompt ({len(prompt)} chars)...")
            await textarea.fill(prompt)
            await asyncio.sleep(0.5)

            logger.info("🚀 Clicking Send...")
            send_btn = await self._find_element(self.selectors.send_button)
            if send_btn:
                await send_btn.click()
            else:
                logger.warning("⚠️ Send button not found, using Enter...")
                await self.page.keyboard.press("Enter")
            
            logger.info("⏳ Waiting for AI Thinking...")
            return await self._wait_for_response_complete()

        except Exception as e:
            logger.error(f"❌ Error sending prompt: {e}")
            return False

    async def _wait_for_response_complete(self) -> bool:
        start_time = asyncio.get_event_loop().time()
        await asyncio.sleep(3)
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.MAX_WAIT_TIME:
                logger.error("❌ Timeout waiting for response!")
                return False
            stop_btn = await self._find_element(self.selectors.stop_generating, timeout=500)
            if stop_btn:
                if int(elapsed) % 10 == 0: logger.debug(f"   Still thinking... ({int(elapsed)}s)")
                await asyncio.sleep(self.POLLING_INTERVAL)
            else:
                await asyncio.sleep(2)
                if not await self._find_element(self.selectors.stop_generating, timeout=500):
                    logger.info(f"✅ Generation Complete! (Took {int(elapsed)}s)")
                    return True
    
    async def get_latest_response(self) -> Optional[CodeBlockResponse]:
        """
        Original Robust Extraction: Text + Code Blocks via Selectors/Regex.
        The RAW text is returned to ProScraper for cleaning.
        """
        try:
            logger.info("📦 Extracting Response Data...")
            
            # 1. Get Text (Selector Based)
            full_text = await self._extract_text()
            if not full_text:
                full_text = await self.page.inner_text("body")

            # 2. Get Code Blocks (Copy Button + Pre Tags + Regex)
            code_blocks, method = await self._extract_code_blocks()
            
            primary_code = ""
            if code_blocks:
                # Still pick the largest to be safe
                primary_code = max(code_blocks, key=len)
            
            # If no code blocks found but text exists, maybe it's just raw code?
            if not primary_code and len(full_text) > 50:
                logger.info("⚠️ No code blocks found, using full text as primary.")
                primary_code = full_text
            
            logger.info(f"✅ Extracted {len(code_blocks)} code blocks via {method}")
            
            return CodeBlockResponse(
                text=full_text,
                code_blocks=code_blocks,
                primary_code=primary_code,
                metadata={"method": method},
                extraction_success=bool(primary_code),
                extraction_method=method
            )
        except Exception as e:
            logger.error(f"❌ Extraction Failed: {e}")
            return None

    async def _extract_text(self) -> str:
        try:
            for selector in self.selectors.message_content:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    return await elements[-1].inner_text()
            elements = await self.page.query_selector_all("[dir='auto']")
            if elements:
                return await elements[-1].inner_text()
            return ""
        except:
            return ""

    async def _extract_code_blocks(self) -> Tuple[List[str], str]:
        # Method A: Clipboard Button (Most Accurate for Code)
        if self.selectors.copy_button:
            copy_btns = await self.page.query_selector_all(self.selectors.copy_button[0])
            # Fallback generic
            if not copy_btns: 
                copy_btns = await self.page.query_selector_all("button:has-text('Copy')")

            if copy_btns:
                try:
                    last_btn = copy_btns[-1]
                    await last_btn.scroll_into_view_if_needed()
                    await last_btn.click()
                    await asyncio.sleep(0.5)
                    clipboard = await self.page.evaluate("navigator.clipboard.readText()")
                    if clipboard and len(clipboard.strip()) > 5:
                        return [clipboard], "clipboard_button"
                except: pass

        # Method B: Pre Tags
        pre_elements = await self.page.query_selector_all("pre")
        blocks = []
        if pre_elements:
            for pre in pre_elements:
                text = await pre.inner_text()
                if text: blocks.append(text)
            if blocks: return blocks, "pre_tags"

        # Method C: Regex
        text = await self.page.inner_text("body")
        matches = re.findall(r'```(?:\w+)?\s*(.*?)\s*```', text, re.DOTALL)
        if matches: return matches, "markdown_regex"

        return [], "none"

    async def _find_element(self, selectors: List[str], timeout: int = 2000):
        for sel in selectors:
            try:
                el = await self.page.wait_for_selector(sel, timeout=timeout)
                if el and await el.is_visible(): return el
            except: continue
        return None

    async def close_session(self):
        try:
            if self.playwright: await self.playwright.stop()
            self.session_active = False
            logger.info("🔴 Browser Session Closed.")
        except: pass

# Global Helpers
_browser_instance: Optional[PersistentBrowser] = None

async def init_browser(headless=False, model="perplexity"):
    global _browser_instance
    _browser_instance = PersistentBrowser(headless=headless, model=model)
    await _browser_instance.start_session()
    return _browser_instance

async def get_browser(): return _browser_instance

async def close_browser():
    global _browser_instance
    if _browser_instance: await _browser_instance.close_session(); _browser_instance = None
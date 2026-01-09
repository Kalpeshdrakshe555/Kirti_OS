# core/browser_tool.py
"""
Kirti OS - Web Browser Automation Tool (Fixed: Slow & Human-like)
Purpose: Fetches modern code accurately by waiting for pages to fully load.
"""

import asyncio
import logging
from typing import List
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)

class BrowserTool:
    GOOGLE_SEARCH_URL = "https://www.google.com/search?q="
    
    # Fake User Agent to look like a real Chrome Browser
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self):
        self.browser: Browser = None
        self.playwright = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        try:
            self.playwright = await async_playwright().start()
            # Headless=True (Background) but with Real Browser args
            self.browser = await self.playwright.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
            )
            logger.info("🌐 Browser Engine Started (Human Mode)")
        except Exception as e:
            logger.error(f"Browser Start Error: {e}")
            raise

    async def close(self):
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    async def _create_page(self) -> Page:
        # Create context with User Agent so websites don't block us
        context = await self.browser.new_context(user_agent=self.USER_AGENT)
        page = await context.new_page()
        # Block heavy media only (images/fonts) to save data, but allow scripts
        await page.route("**/*.{png,jpg,jpeg,gif,woff,woff2}", lambda route: route.abort())
        return page

    async def search_google(self, query: str, max_results: int = 3):
        try:
            page = await self._create_page()
            await page.goto(self.GOOGLE_SEARCH_URL + query.replace(" ", "+"), wait_until="domcontentloaded")
            
            # 🔥 Wait for Google Results to actually appear
            try:
                await page.wait_for_selector("div.g", timeout=5000)
            except:
                pass

            results = []
            elements = await page.query_selector_all("div.g")
            
            for elem in elements[:max_results]:
                try:
                    title = await (await elem.query_selector("h3")).inner_text()
                    link = await (await elem.query_selector("a")).get_attribute("href")
                    if link and title and "http" in link: 
                        results.append({"title": title, "url": link})
                except: continue
                
            await page.close()
            return results
        except Exception as e:
            logger.error(f"Google Search Failed: {e}")
            return []

    async def extract_code(self, url: str) -> List[str]:
        """Visits a URL and steals code blocks (With Smart Waiting)"""
        try:
            page = await self._create_page()
            logger.info(f"⏳ Visiting: {url}")
            
            # 1. Load Page
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            
            # 2. 🔥 CRITICAL FIX: Wait for Network to settle (Sites like React need this)
            try:
                await page.wait_for_load_state('networkidle', timeout=8000)
            except:
                pass # Proceed even if timeout happens
            
            # 3. Extra Sleep to be safe
            await asyncio.sleep(2) 
            
            code_blocks = []
            # Improved Selectors for Code
            selectors = ["pre", "code", ".highlight", ".code-block", "textarea[readonly]"]
            
            for sel in selectors:
                elements = await page.query_selector_all(sel)
                for elem in elements:
                    text = await elem.inner_text()
                    # Filter garbage (too short or too long)
                    if len(text) > 30 and len(text) < 10000: 
                        code_blocks.append(text)
            
            await page.close()
            logger.info(f"✅ Extracted {len(code_blocks)} code blocks from {url}")
            return code_blocks[:3] # Return top 3
        except Exception as e:
            logger.error(f"Extraction Error for {url}: {e}")
            return []

    async def get_modern_code(self, project_type: str, tech_stack: str) -> str:
        query = f"{project_type} example code using {tech_stack} modern tutorial"
        logger.info(f"🔎 Searching Web: {query}")
        
        results = await self.search_google(query)
        if not results: return "❌ No search results found."
        
        final_report = f"🌐 **Web Research for {tech_stack}:**\n\n"
        
        # Only visit top 2 results to save time
        found_code = False
        for res in results[:2]:
            url = res['url']
            final_report += f"🔗 Source: {url}\n"
            
            codes = await self.extract_code(url)
            if codes:
                found_code = True
                final_report += f"💻 **Code Snippet:**\n```\n{codes[0][:1500]}...\n```\n(Code truncated)\n\n"
            else:
                final_report += "⚠️ No readable code found here.\n\n"
        
        if not found_code:
            final_report += "⚠️ I couldn't find exact code, so I will generate it myself using best practices."
            
        return final_report

class BrowserToolWrapper:
    @staticmethod
    async def search_web(project_type: str, tech_stack: str) -> str:
        try:
            async with BrowserTool() as browser:
                return await browser.get_modern_code(project_type, tech_stack)
        except Exception as e:
            return f"❌ Browser Error: {e}"
            
    @staticmethod
    async def quick_search(query: str) -> str:
        try:
            async with BrowserTool() as browser:
                results = await browser.search_google(query, max_results=1)
                if results: return f"🔎 Found: {results[0]['title']} - {results[0]['url']}"
                return "❌ No results."
        except Exception as e:
            return f"❌ Search Error: {e}"
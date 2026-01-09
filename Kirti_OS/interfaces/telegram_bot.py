# interfaces/telegram_bot.py
"""
Kirti OS - Telegram Bot (God Mode Interface)
Purpose: Connects Telegram to Router & Tool Registry.
Fixed: Timeout settings moved to HTTPXRequest to prevent TypeError.
"""
import sys
import os
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Telegram Imports
from telegram import Update
from telegram.constants import ParseMode, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, Defaults
from telegram.request import HTTPXRequest 

# Image/System Imports
import mss
import pyautogui
from PIL import Image

# PATH FIX
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(root_dir)

# Import Core
from Kirti_OS.core.router import TaskRouter
from Kirti_OS.core.tools import ToolRegistry

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

class BotConfig:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID", "0"))
    SCREENSHOT_DIR = Path("screenshots")
    DOWNLOAD_DIR = Path("downloads")
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_BOT_TOKEN: raise ValueError("Token Missing")
        cls.SCREENSHOT_DIR.mkdir(exist_ok=True)
        cls.DOWNLOAD_DIR.mkdir(exist_ok=True)

class KirtiOSBot:
    def __init__(self):
        self.router = TaskRouter()

    async def _send_safe(self, update: Update, text: str):
        """Prevents crashes due to markdown errors"""
        try:
            await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        except:
            # Fallback to plain text if Markdown fails
            await update.message.reply_text(text, parse_mode=None)

    async def _check_auth(self, update):
        if update.effective_user.id != BotConfig.ALLOWED_USER_ID:
            return False
        return True

    async def start(self, update, context):
        if not await self._check_auth(update): return
        msg = """
🤖 **Kirti OS (God Mode) Is Ready!**

**You can say:**
• "Open Chrome"
• "Mute volume"
• "Shutdown the PC"
• "What is on my screen?"
• "Create a file named log.txt"

Use `/help` for more options.
"""
        await self._send_safe(update, msg)

    async def screenshot_cmd(self, update, context):
        """Takes a screenshot instantly"""
        if not await self._check_auth(update): return
        try:
            await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
            path = BotConfig.SCREENSHOT_DIR / "temp.png"
            
            # Try MSS first (Faster), Fallback to PyAutoGUI
            try:
                with mss.mss() as sct:
                    sct.shot(mon=-1, output=str(path))
            except:
                pyautogui.screenshot(path)
            
            with open(path, 'rb') as f:
                await update.message.reply_photo(f, caption="📸 Screen Capture")
        except Exception as e:
            await self._send_safe(update, f"❌ Screenshot failed: {e}")

    async def handle_all(self, update, context):
        """The Main Handler for Text, Photos, and Files"""
        if not await self._check_auth(update): return
        
        text = update.message.text or update.message.caption or "Analyze this"
        img_bytes = None
        
        try:
            await update.message.chat.send_action(ChatAction.TYPING)
            
            # 1. Handle Photos (User sent an image)
            if update.message.photo:
                f = await update.message.photo[-1].get_file()
                img_bytes = bytes(await f.download_as_bytearray())
            
            # 2. Handle Documents (Save to PC)
            elif update.message.document:
                doc = update.message.document
                f = await doc.get_file()
                # Default save to Downloads folder
                path = BotConfig.DOWNLOAD_DIR / doc.file_name
                await f.download_to_drive(path)
                await self._send_safe(update, f"✅ File Saved: `{path}`")
                return

            # 3. Auto-Screenshot Trigger
            # If user asks "what is on screen" but didn't send an image, take one automatically
            if not img_bytes and any(k in text.lower() for k in ['screen', 'display', 'monitor']):
                try:
                    with mss.mss() as sct:
                        s = sct.grab(sct.monitors[1])
                        from io import BytesIO
                        bio = BytesIO()
                        Image.frombytes('RGB', s.size, s.rgb).save(bio, 'JPEG')
                        img_bytes = bio.getvalue()
                        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
                        await update.message.reply_photo(img_bytes, caption="📸 Auto-View")
                except Exception as e:
                    logger.error(f"Auto-screenshot failed: {e}")

            # 4. Route to AI (The Brain)
            resp = await self.router.route(text, img_bytes)
            
            # 5. Execute Tools (The God Mode Part)
            action_log = ""
            if resp.tool_calls:
                for tool in resp.tool_calls:
                    res = await ToolRegistry.execute(tool.tool_name, **tool.arguments)
                    action_log += f"\n⚙️ **Action:** {res}"
            
            # 6. Reply to User
            final_msg = resp.result + action_log + f"\n\n_🧠 {resp.model_used}_"
            
            if len(final_msg) > 4000:
                await self._send_safe(update, final_msg[:4000])
            else:
                await self._send_safe(update, final_msg)

        except Exception as e:
            await self._send_safe(update, f"❌ System Error: {e}")

# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================

def main():
    try: BotConfig.validate()
    except ValueError as e: return print(f"❌ Configuration Error: {e}")
    
    bot = KirtiOSBot()
    
    # Configure Connection Settings (Timeout Fix)
    # Increased timeouts for stable connection
    request = HTTPXRequest(connection_pool_size=8, read_timeout=30.0, write_timeout=30.0, connect_timeout=30.0)
    
    app = Application.builder().token(BotConfig.TELEGRAM_BOT_TOKEN).request(request).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("help", bot.start))
    app.add_handler(CommandHandler("screenshot", bot.screenshot_cmd))
    app.add_handler(MessageHandler(filters.ALL, bot.handle_all))
    
    print(f"🚀 Kirti OS Started! (ID: {BotConfig.ALLOWED_USER_ID})")
    
    # Start Polling (Allowed updates ensures we get everything)
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
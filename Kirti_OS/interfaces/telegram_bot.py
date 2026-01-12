# interfaces/telegram_bot.py
"""
Kirti OS - Telegram Bot (God Mode Interface)
Purpose: Connects Telegram to Router & Tool Registry.
Updated: Handles Long-Running Tasks (God Mode) with Status Updates.
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
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest 

# Image/System Imports
import mss
import pyautogui
from PIL import Image
from io import BytesIO

# PATH FIX
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(root_dir)

# Import Core
# Note: Ensure these imports work based on your folder structure
try:
    from Kirti_OS.core.router import TaskRouter
    from Kirti_OS.core.tools import ToolRegistry
except ImportError:
    # Fallback if running from root
    from core.router import TaskRouter
    from core.tools import ToolRegistry

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

    async def _edit_safe(self, update: Update, message_id: int, text: str):
        """Edits a message safely (handling Markdown errors)"""
        try:
            await update.get_bot().edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            await update.get_bot().edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=text,
                parse_mode=None
            )

    async def _check_auth(self, update):
        if update.effective_user.id != BotConfig.ALLOWED_USER_ID:
            logger.warning(f"⚠️ Unauthorized access attempt from ID: {update.effective_user.id}")
            return False
        return True

    async def start(self, update, context):
        if not await self._check_auth(update): return
        msg = """
🤖 **Kirti OS (God Mode) Is Ready!**

**You can say:**
• "Create a Snake Game in Python" (God Mode)
• "Open Chrome"
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
        
        # 1. Send Initial "Thinking" Status
        processing_msg = await update.message.reply_text("⚡ Thinking...")
        
        try:
            await update.message.chat.send_action(ChatAction.TYPING)
            
            # --- HANDLE MEDIA ---
            if update.message.photo:
                f = await update.message.photo[-1].get_file()
                img_bytes = bytes(await f.download_as_bytearray())
            
            elif update.message.document:
                doc = update.message.document
                f = await doc.get_file()
                path = BotConfig.DOWNLOAD_DIR / doc.file_name
                await f.download_to_drive(path)
                await self._edit_safe(update, processing_msg.message_id, f"✅ File Saved: `{path}`")
                return

            # --- AUTO SCREENSHOT ---
            if not img_bytes and any(k in text.lower() for k in ['screen', 'display', 'monitor']):
                try:
                    with mss.mss() as sct:
                        s = sct.grab(sct.monitors[1])
                        bio = BytesIO()
                        Image.frombytes('RGB', s.size, s.rgb).save(bio, 'JPEG')
                        img_bytes = bio.getvalue()
                        await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)
                        # We send a new photo message, so we can delete the "thinking" text
                        await update.message.reply_photo(img_bytes, caption="📸 Auto-View")
                        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=processing_msg.message_id)
                        return # We stop here for simple screenshot requests
                except Exception as e:
                    logger.error(f"Auto-screenshot failed: {e}")

            # --- CHECK FOR GOD MODE (PROJECT BUILD) ---
            # If user asks to create/build, update status immediately because it takes time
            project_keywords = ['create', 'build', 'develop', 'make a project', 'make an app']
            if any(k in text.lower() for k in project_keywords) and len(text) > 10:
                await self._edit_safe(
                    update, 
                    processing_msg.message_id, 
                    "🏗️ **God Mode Activated**\n\nInitializing Architect Agent...\nThis may take 2-5 minutes. Please wait. ☕"
                )
                # Keep typing action active periodically if possible, but for now we just wait

            # --- ROUTE TO AI (THE BRAIN) ---
            # This call might take 5 mins if it's a project build
            resp = await self.router.route(text, img_bytes)
            
            # --- EXECUTE TOOLS ---
            action_log = ""
            if resp.tool_calls:
                for tool in resp.tool_calls:
                    res = await ToolRegistry.execute(tool.tool_name, **tool.arguments)
                    action_log += f"\n⚙️ **Action:** {res}"
            
            # --- FORMAT FINAL RESPONSE ---
            final_msg = resp.result + action_log
            
            # Add Model Footer
            footer = f"\n\n_🧠 {resp.model_used}_"
            if len(final_msg) + len(footer) < 4000:
                final_msg += footer
            
            # --- REPLY TO USER (EDIT THE STATUS MESSAGE) ---
            if len(final_msg) > 4000:
                # If too long, split or send as file? For now, truncate safely
                await self._edit_safe(update, processing_msg.message_id, final_msg[:4000])
                await update.message.reply_text(final_msg[4000:]) # Send rest as new msg
            else:
                await self._edit_safe(update, processing_msg.message_id, final_msg)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._edit_safe(update, processing_msg.message_id, f"❌ System Error: {e}")

# ============================================================================
# MAIN APPLICATION ENTRY POINT
# ============================================================================

def main():
    try: BotConfig.validate()
    except ValueError as e: return print(f"❌ Configuration Error: {e}")
    
    bot = KirtiOSBot()
    
    # Configure Connection Settings (Important for Long Tasks)
    # read_timeout=300s (5 mins) ensures Telegram doesn't disconnect during Project Build
    request = HTTPXRequest(
        connection_pool_size=8, 
        read_timeout=300.0, 
        write_timeout=300.0, 
        connect_timeout=60.0
    )
    
    app = Application.builder().token(BotConfig.TELEGRAM_BOT_TOKEN).request(request).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", bot.start))
    app.add_handler(CommandHandler("help", bot.start))
    app.add_handler(CommandHandler("screenshot", bot.screenshot_cmd))
    app.add_handler(MessageHandler(filters.ALL, bot.handle_all))
    
    print(f"🚀 Kirti OS Started! (ID: {BotConfig.ALLOWED_USER_ID})")
    print("   Waiting for commands...")
    
    # Start Polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
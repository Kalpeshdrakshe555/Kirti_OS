import sys
import os
import asyncio

# --- FIX 1: Add current directory to System Path ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# --- FIX 2: Correct Filename (browser_tool vs browser_tools) ---
try:
    # Pehle Singular naam try karte hain (Jo tumhare PC par hai)
    from browser_tool import init_browser, close_browser
except ImportError:
    try:
        # Agar wo nahi mila, to Plural try karte hain
        from browser_tools import init_browser, close_browser
    except ImportError:
        print("❌ Error: Na 'browser_tool.py' mila na 'browser_tools.py'. File name check karo!")
        sys.exit(1)

async def manual_login():
    print("\n⚡ OPENING KIRTI'S BROWSER FOR LOGIN...")
    print("⚠️  Browser will stay open for 5 minutes.")
    print("👉 Please Log in to Perplexity Pro manually now.")
    
    # Browser open karega
    try:
        browser = await init_browser(headless=False)
    except Exception as e:
        print(f"❌ Error initializing browser: {e}")
        return
    
    # 5 Minute ka wait
    for i in range(300, 0, -1):
        if i % 10 == 0:
            print(f"⏳ Time remaining to login: {i} seconds...", end="\r")
        await asyncio.sleep(1)
        
    print("\n✅ Time up! Saving session and closing...")
    await close_browser()

if __name__ == "__main__":
    asyncio.run(manual_login())
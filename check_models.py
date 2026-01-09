"""
Kirti OS - Gemini Model Lister (Fixed)
Purpose: List Gemini models without attribute errors.
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def list_gemini():
    print(f"\n{GREEN}=== GEMINI MODELS CHECK ==={RESET}")
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY_1")
    
    if not api_key:
        print(f"{RED}❌ API Key missing{RESET}")
        return

    try:
        client = genai.Client(api_key=api_key)
        
        print(f"{'MODEL ID':<50} | {'DISPLAY NAME'}")
        print("-" * 70)
        
        # Iterate and print basic info only to avoid attribute errors
        for m in client.models.list():
            # Handle potential missing attributes gracefully
            name = getattr(m, 'name', 'Unknown')
            display_name = getattr(m, 'display_name', 'N/A')
            
            # Clean up the ID
            clean_id = name.replace("models/", "")
            
            # Highlight Flash/Pro models
            if "flash" in clean_id:
                print(f"{GREEN}{clean_id:<50} | {display_name} ✅{RESET}")
            else:
                print(f"{clean_id:<50} | {display_name}")
                
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")

if __name__ == "__main__":
    list_gemini()
    input("\nPress Enter to close...")
#!/usr/bin/env python3
"""
Quick helper: Prints your Telegram Chat ID.
Run this AFTER setting TELEGRAM_BOT_TOKEN in .env,
then send any message to your bot.
"""
import sys, os, time, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TOKEN or TOKEN == "your-bot-token-here":
    print("❌ Set TELEGRAM_BOT_TOKEN in your .env first.")
    sys.exit(1)

print(f"✅ Using bot token: {TOKEN[:15]}...")
print("📱 Now send ANY message to your bot on Telegram.")
print("   Waiting...\n")

seen = set()
url  = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

for _ in range(60):   # Wait up to 60 seconds
    try:
        r = requests.get(url, params={"timeout": 5}, timeout=10)
        for update in r.json().get("result", []):
            msg = update.get("message", {})
            cid = msg.get("chat", {}).get("id")
            name = msg.get("from", {}).get("first_name", "?")
            if cid and cid not in seen:
                seen.add(cid)
                print(f"🎉 Found chat!")
                print(f"   Name    : {name}")
                print(f"   Chat ID : {cid}")
                print(f"\n👉 Add this to your .env:")
                print(f"   TELEGRAM_CHAT_ID={cid}")
                sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(2)

print("⏰ Timed out. Make sure you sent a message to your bot.")

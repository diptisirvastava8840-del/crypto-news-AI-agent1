import os
import requests
from datetime import datetime, timezone
from openai import OpenAI

# === SETTINGS ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Mode: "daily" or "monitor"
MODE = os.getenv("MODE", "daily")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload)

def get_news(limit=12):
    r = requests.get(f"https://cryptocurrency.cv/api/news?limit={limit}")
    return r.json().get("articles", [])

def get_prices():
    r = requests.get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids": "bitcoin,ethereum,solana",
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
    )
    return r.json()

def ask_ai(prompt):
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",   # fast + free
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=600
    )
    return response.choices[0].message.content.strip()

def run_daily_report():
    news = get_news(15)
    prices = get_prices()

    headlines = "\n".join([f"- {a['title']} ({a.get('source', '')})" for a in news[:10]])

    btc = prices.get("bitcoin", {})
    eth = prices.get("ethereum", {})
    sol = prices.get("solana", {})

    price_text = f"""
Current prices:
• Bitcoin: ${btc.get('usd', 0):,.0f} ({btc.get('usd_24h_change', 0):+.1f}%)
• Ethereum: ${eth.get('usd', 0):,.0f} ({eth.get('usd_24h_change', 0):+.1f}%)
• Solana: ${sol.get('usd', 0):,.0f} ({sol.get('usd_24h_change', 0):+.1f}%)
"""

    prompt = f"""
You are a helpful crypto news assistant. Create a short daily report.

Today's main headlines:
{headlines}

{price_text}

Write a clear report with these sections:
1. What happened today (3-5 key points)
2. Market snapshot
3. Should I take trades today? (give a cautious, balanced opinion)
4. Important disclaimer that this is NOT financial advice

Keep the whole message under 3500 characters. Use simple language.
"""

    report = ask_ai(prompt)
    send_telegram(f"📰 *Daily Crypto Report*\n\n{report}")

def run_monitor():
    news = get_news(8)
    recent = [a for a in news if "m ago" in a.get("timeAgo", "") or "h ago" in a.get("timeAgo", "")]

    if not recent:
        return

    headlines = "\n".join([f"- {a['title']}" for a in recent[:6]])

    prompt = f"""
Look at these recent crypto headlines:
{headlines}

Is there any HIGH IMPACT / BIG news that a trader should know immediately?
(Examples: major hack, SEC action, big ETF news, exchange problems, huge price crash/pump, government ban, etc.)

Reply in this exact format:
BIG: yes or no
REASON: short explanation (1-2 sentences)
SUMMARY: one short message I can send as an alert (max 280 characters)
"""

    result = ask_ai(prompt)

    if "BIG: yes" in result.lower():
        # Extract the summary part
        summary = result.split("SUMMARY:")[-1].strip() if "SUMMARY:" in result else result
        send_telegram(f"🚨 *BIG CRYPTO NEWS*\n\n{summary}")

# === MAIN ===
if __name__ == "__main__":
    if MODE == "monitor":
        run_monitor()
    else:
        run_daily_report()

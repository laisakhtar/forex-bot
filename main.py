import os
import threading
import time
import json
import urllib.request
import concurrent.futures
from datetime import datetime, timezone, timedelta
from flask import Flask

# 1. Keep-Alive Web Server
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QUOTEX FOREX H1 ACTIVE ENGINE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

def render_anti_freeze():
    time.sleep(10)
    external_url = os.environ.get("RENDER_EXTERNAL_URL", f"http://127.0.0.1:{os.environ.get('PORT', 10000)}")
    url = f"{external_url}/health"
    while True:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'KeepAlivePing'})
            with urllib.request.urlopen(req, timeout=5) as r:
                pass
        except Exception:
            pass
        time.sleep(240)

threading.Thread(target=render_anti_freeze, daemon=True).start()

# 2. Telegram Credentials
BOT_TOKEN = "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw"
CHAT_ID = "5883050661"

try:
    urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=4)
except Exception:
    pass

# Turnover safe compounding (1% to 2% risk recommended)
LEVELS_STAKE = {
    1: 3.00, 2: 5.50, 3: 10.00, 4: 18.00, 5: 32.00,
    6: 58.00, 7: 105.00, 8: 190.00, 9: 345.00, 10: 620.00
}

PAIRS = [
    {"name": "EUR/USD", "deriv": "frxEURUSD", "yahoo": "EURUSD=X", "digits": 5},
    {"name": "GBP/USD", "deriv": "frxGBPUSD", "yahoo": "GBPUSD=X", "digits": 5},
    {"name": "USD/JPY", "deriv": "frxUSDJPY", "yahoo": "JPY=X", "digits": 3},
    {"name": "AUD/USD", "deriv": "frxAUDUSD", "yahoo": "AUDUSD=X", "digits": 5},
    {"name": "USD/CAD", "deriv": "frxUSDCAD", "yahoo": "CAD=X", "digits": 5},
    {"name": "USD/CHF", "deriv": "frxUSDCHF", "yahoo": "CHF=X", "digits": 5},
    {"name": "NZD/USD", "deriv": "frxNZDUSD", "yahoo": "NZDUSD=X", "digits": 5},
    {"name": "EUR/GBP", "deriv": "frxEURGBP", "yahoo": "EURGBP=X", "digits": 5},
    {"name": "EUR/JPY", "deriv": "frxEURJPY", "yahoo": "EURJPY=X", "digits": 3},
    {"name": "GBP/JPY", "deriv": "frxGBPJPY", "yahoo": "GBPJPY=X", "digits": 3},
    {"name": "GOLD (XAU/USD)", "deriv": "frxXAUUSD", "yahoo": "GC=F", "digits": 2},
    {"name": "BTC/USD", "deriv": "cryBTCUSD", "yahoo": "BTC-USD", "digits": 2},
    {"name": "ETH/USD", "deriv": "cryETHUSD", "yahoo": "ETH-USD", "digits": 2}
]

def get_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def send_tg(text):
    def _worker():
        for _ in range(3): 
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "Connection": "close"})
                with urllib.request.urlopen(req, timeout=10):
                    break 
            except Exception:
                time.sleep(2)
    threading.Thread(target=_worker, daemon=True).start()

def fetch_1h_candles(pair_info):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair_info['yahoo']}?interval=1h&range=10d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4.5) as res:
            data = json.loads(res.read().decode('utf-8'))
            res_data = data['chart']['result'][0]
            timestamps = res_data['timestamp']
            quote = res_data['indicators']['quote'][0]
            candles = []
            for i in range(len(timestamps)):
                if quote['close'][i] is not None and quote['open'][i] is not None:
                    candles.append({
                        'open': float(quote['open'][i]),
                        'high': float(quote['high'][i]),
                        'low': float(quote['low'][i]),
                        'close': float(quote['close'][i])
                    })
            if len(candles) >= 15:
                return candles[-20:] 
    except Exception:
        pass

    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={pair_info['deriv']}&granularity=3600&count=20"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            if 'candles' in data and len(data['candles']) >= 10:
                return data['candles']
    except Exception:
        pass
    return []

def calculate_ema(prices, period):
    if len(prices) < period:
        return [prices[-1]]
    multiplier = 2 / (period + 1)
    ema = [sum(prices[:period]) / period]
    for price in prices[period:]:
        ema.append((price - ema[-1]) * multiplier + ema[-1])
    return ema

# -------------------------------------------------------------
# H1 ACTIVE FLOW ENGINE (Guarantees Top Pair)
# -------------------------------------------------------------
def analyze_h1_active(candles):
    if not candles or len(candles) < 15:
        return None

    closes = [float(c['close']) for c in candles]
    opens = [float(c['open']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]

    ema10 = calculate_ema(closes, 10)[-1]
    
    c_close = closes[-1]
    c_open = opens[-1]
    prev_close = closes[-2]

    call_pts = 50
    put_pts = 50
    reason = "H1 General Momentum"

    # Active Flow Scoring
    if c_close > ema10:
        call_pts += 20
        if c_close > c_open: call_pts += 15
        if c_close > prev_close: call_pts += 10
        reason = "H1 Bullish Flow (Price > EMA10)"
    else:
        put_pts += 20
        if c_close < c_open: put_pts += 15
        if c_close < prev_close: put_pts += 10
        reason = "H1 Bearish Flow (Price < EMA10)"

    if call_pts >= put_pts:
        return "CALL (UP) 🟢", call_pts, reason
    else:
        return "PUT (DOWN) 🔴", put_pts, reason

def telegram_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=5"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get("ok"):
                    for item in data.get("result", []):
                        offset = item["update_id"] + 1
                        msg = item.get("message", {})
                        text = msg.get("text", "").strip()
                        c_id = str(msg.get("chat", {}).get("id", ""))
                        if c_id == CHAT_ID and ("/status" in text or "/start" in text or "status" in text.lower()):
                            send_tg(
                                f"🟢 <b>FOREX H1 ACTIVE ENGINE ONLINE</b>\n\n"
                                f"🕒 <b>Clock:</b> <code>{get_ist().strftime('%H:%M:%S IST')}</code>\n"
                                f"📉 <b>Mode:</b> 1-Hour Zero-Skip Delivery\n"
                            )
        except Exception:
            time.sleep(2)
        time.sleep(1)

threading.Thread(target=telegram_listener, daemon=True).start()

def process_pair(p):
    candles = fetch_1h_candles(p)
    if candles:
        res = analyze_h1_active(candles)
        if res:
            action, score, reason = res
            return {
                "pair": p,
                "action": action,
                "score": score,
                "reason": reason,
                "price": float(candles[-1]['close'])
            }
    return None

def market_engine():
    time.sleep(2)
    send_tg(
        "🏛️ <b>FOREX H1 ACTIVE ENGINE DEPLOYED</b>\n\n"
        "• <b>Skip Filter Removed:</b> Ab bot har 30 minute par H1 chart ka sabse best setup guarantee ke sath bhejega.\n"
        "• <b>Action:</b> Signal milte hi Quotex par 1 ghante ki expiry wali trade set karein."
    )

    while True:
        try:
            # Check every 30 minutes (00:00, 00:30, 01:00...)
            now = time.time()
            wait_sec = 1800 - (now % 1800)
            if wait_sec < 5:
                wait_sec += 1800

            time.sleep(wait_sec)

            best_setup = None
            highest_score = -1 # NO MINIMUM SCORE (Ensures 100% signal delivery)
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                results = list(executor.map(process_pair, PAIRS))
                
            for res in results:
                if res and res["score"] > highest_score:
                    highest_score = res["score"]
                    best_setup = res

            if not best_setup:
                now_ist = get_ist().strftime('%H:%M IST')
                send_tg(f"⚠️ <b>NETWORK WARNING ({now_ist})</b>\n<i>Data servers busy. Retrying...</i>")
                continue

            pair_info = best_setup['pair']
            cur_price = best_setup['price']
            action = best_setup['action']
            score = best_setup['score']
            reason = best_setup['reason']
            d = pair_info['digits']

            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M IST")
            exp_1h = (now_ist + timedelta(hours=1)).strftime("%H:%M IST")
            exp_2h = (now_ist + timedelta(hours=2)).strftime("%H:%M IST")

            alert = (
                f"🏛️ <b>FOREX H1 ACTIVE SIGNAL</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_info['name']}</code>\n"
                f"🚀 <b>Direction:</b> <b>{action}</b>\n"
                f"🔥 <b>Trend Strength:</b> <b>{score}/100</b>\n\n"
                f"⏳ <b>TRADING WINDOW:</b>\n"
                f"🟢 <b>Entry Time:</b> <code>{ent_str}</code> (Now)\n"
                f"🛑 <b>Expiry Set 1:</b> <code>{exp_1h}</code> (1 Hour)\n"
                f"🛑 <b>Expiry Set 2:</b> <code>{exp_2h}</code> (2 Hours)\n\n"
                f"💵 <b>Recommended Stake:</b> 1% to 2% of Balance\n"
                f"📍 <b>Current Price:</b> <code>{cur_price:.{d}f}</code>\n"
                f"🔬 <b>Logic:</b> <i>{reason}</i>"
            )
            send_tg(alert)

        except Exception as err:
            print(f">> [Runtime Error]: {err}")
            time.sleep(5)

threading.Thread(target=market_engine, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)

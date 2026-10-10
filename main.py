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
    return "QUOTEX 15M STOCHASTIC ENGINE LIVE", 200

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

LEVELS_STAKE = {
    1: 1.61, 2: 2.93, 3: 5.33, 4: 9.71, 5: 17.67,
    6: 32.15, 7: 58.52, 8: 106.51, 9: 193.85, 10: 352.80,
    11: 642.10, 12: 1168.62, 13: 2126.89, 14: 3870.94, 15: 7045.11,
    16: 12822.10, 17: 23336.23, 18: 42471.93, 19: 77298.92, 20: 140684.03,
    21: 256044.94, 22: 466001.78, 23: 848123.25, 24: 1543584.31, 25: 2809323.45,
    26: 5112968.68, 27: 9305603.00, 28: 16936197.46, 29: 30823879.37, 30: 56099460.46
}

# 18 Pairs (Crypto highlighted for Weekends)
PAIRS = [
    {"name": "BTC/USD", "deriv": "cryBTCUSD", "yahoo": "BTC-USD", "digits": 2, "is_crypto": True},
    {"name": "ETH/USD", "deriv": "cryETHUSD", "yahoo": "ETH-USD", "digits": 2, "is_crypto": True},
    {"name": "EUR/USD", "deriv": "frxEURUSD", "yahoo": "EURUSD=X", "digits": 5, "is_crypto": False},
    {"name": "GBP/USD", "deriv": "frxGBPUSD", "yahoo": "GBPUSD=X", "digits": 5, "is_crypto": False},
    {"name": "USD/JPY", "deriv": "frxUSDJPY", "yahoo": "JPY=X", "digits": 3, "is_crypto": False},
    {"name": "AUD/USD", "deriv": "frxAUDUSD", "yahoo": "AUDUSD=X", "digits": 5, "is_crypto": False},
    {"name": "USD/CAD", "deriv": "frxUSDCAD", "yahoo": "CAD=X", "digits": 5, "is_crypto": False},
    {"name": "USD/CHF", "deriv": "frxUSDCHF", "yahoo": "CHF=X", "digits": 5, "is_crypto": False},
    {"name": "NZD/USD", "deriv": "frxNZDUSD", "yahoo": "NZDUSD=X", "digits": 5, "is_crypto": False},
    {"name": "EUR/GBP", "deriv": "frxEURGBP", "yahoo": "EURGBP=X", "digits": 5, "is_crypto": False},
    {"name": "EUR/JPY", "deriv": "frxEURJPY", "yahoo": "EURJPY=X", "digits": 3, "is_crypto": False},
    {"name": "GBP/JPY", "deriv": "frxGBPJPY", "yahoo": "GBPJPY=X", "digits": 3, "is_crypto": False},
    {"name": "AUD/JPY", "deriv": "frxAUDJPY", "yahoo": "AUDJPY=X", "digits": 3, "is_crypto": False},
    {"name": "CAD/JPY", "deriv": "frxCADJPY", "yahoo": "CADJPY=X", "digits": 3, "is_crypto": False},
    {"name": "EUR/AUD", "deriv": "frxEURAUD", "yahoo": "EURAUD=X", "digits": 5, "is_crypto": False},
    {"name": "EUR/CAD", "deriv": "frxEURCAD", "yahoo": "EURCAD=X", "digits": 5, "is_crypto": False},
    {"name": "GBP/AUD", "deriv": "frxGBPAUD", "yahoo": "GBPAUD=X", "digits": 5, "is_crypto": False},
    {"name": "GOLD (XAU/USD)", "deriv": "frxXAUUSD", "yahoo": "GC=F", "digits": 2, "is_crypto": False}
]

class SafeEngineState:
    def __init__(self):
        self.level = 1
        self.trade_step = 1
        self.consecutive_losses = 0
        self.active_trade = None
        self.state_lock = threading.Lock()

state = SafeEngineState()

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

def fetch_live_price(pair_info):
    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={pair_info['deriv']}&granularity=900&count=2"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            candles = data.get('candles', [])
            if candles:
                return float(candles[-1]['close'])
    except Exception:
        pass
        
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair_info['yahoo']}?interval=1m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            return float(meta.get('regularMarketPrice', 0))
    except Exception:
        pass
    return None

def fetch_15m_candles(pair_info):
    try:
        url = f"https://api.deriv.com/api/v1/candles?symbol={pair_info['deriv']}&granularity=900&count=20"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4.0) as res:
            data = json.loads(res.read().decode('utf-8'))
            if 'candles' in data and len(data['candles']) > 0:
                return data['candles']
    except Exception:
        pass

    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair_info['yahoo']}?interval=15m&range=3d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4.0) as res:
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
            if len(candles) > 0:
                return candles[-20:]
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

def calculate_stochastic(highs, lows, closes, k_period=14, d_period=3):
    if len(closes) < k_period:
        return [], []
    k_values = []
    for i in range(k_period, len(closes) + 1):
        highest_high = max(highs[i-k_period:i])
        lowest_low = min(lows[i-k_period:i])
        current_close = closes[i-1]
        if highest_high == lowest_low:
            k = 50
        else:
            k = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100
        k_values.append(k)
        
    d_values = []
    if len(k_values) >= d_period:
        for i in range(d_period, len(k_values) + 1):
            d_values.append(sum(k_values[i-d_period:i]) / d_period)
            
    return k_values, d_values

# -------------------------------------------------------------
# STOCHASTIC ZERO-SKIP ENGINE (Guarantees Trade Every 15 Min)
# -------------------------------------------------------------
def score_pair_stochastic(candles, is_crypto):
    if not candles or len(candles) < 15:
        return None

    closes = [float(c['close']) for c in candles]
    opens = [float(c['open']) for c in candles]
    highs = [float(c['high']) for c in candles]
    lows = [float(c['low']) for c in candles]

    # Technicals
    ema10 = calculate_ema(closes, 10)[-1]
    k_vals, d_vals = calculate_stochastic(highs, lows, closes, 14, 3)
    
    if not k_vals or not d_vals:
        return None

    current_k = k_vals[-1]
    current_d = d_vals[-1]
    
    c_close = closes[-1]
    c_open = opens[-1]

    call_score = 50
    put_score = 50

    # STOCHASTIC LOGIC
    # Bullish: K crosses above D, or K is rising from bottom
    if current_k > current_d:
        call_score += 20
        if current_k < 40: call_score += 15 # Bounce from bottom
    
    # Bearish: K crosses below D, or K is falling from top
    if current_k < current_d:
        put_score += 20
        if current_k > 60: put_score += 15 # Drop from top

    # TREND LOGIC
    if c_close > ema10: call_score += 15
    if c_close < ema10: put_score += 15

    # CANDLE MOMENTUM LOGIC
    if c_close > c_open: call_score += 10
    if c_close < c_open: put_score += 10

    # WEEKEND BONUS: If it's crypto on a weekend, boost the score because Forex is dead
    today = datetime.now(timezone(timedelta(hours=5, minutes=30))).weekday()
    if today >= 5 and is_crypto: # 5 is Saturday, 6 is Sunday
        call_score += 25
        put_score += 25

    if call_score >= put_score:
        return "CALL (UP) 🟢", min(call_score, 98), "Stochastic Bullish Crossover & Trend"
    else:
        return "PUT (DOWN) 🔴", min(put_score, 98), "Stochastic Bearish Crossover & Trend"

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
                            with state.state_lock:
                                max_t = 4 if state.level <= 20 else 6
                                reply = (
                                    f"🟢 <b>QUOTEX STOCHASTIC ENGINE ONLINE</b>\n\n"
                                    f"🕒 <b>Clock:</b> <code>{get_ist().strftime('%H:%M:%S IST')}</code>\n"
                                    f"📉 <b>Mode:</b> Zero-Skip Guaranteed Delivery\n"
                                    f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                    f"💵 <b>Current Stake:</b> ${LEVELS_STAKE[state.level]}"
                                )
                            send_tg(reply)
        except Exception:
            time.sleep(2)
        time.sleep(1)

threading.Thread(target=telegram_listener, daemon=True).start()

def analyze_pair(p):
    candles = fetch_15m_candles(p)
    if candles:
        res = score_pair_stochastic(candles, p.get("is_crypto", False))
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
        "🔥 <b>STOCHASTIC ZERO-SKIP ENGINE ACTIVATED</b>\n\n"
        "• <b>Skip Filter Removed:</b> Ab bot kabhi skip nahi karega. Har 15 minute signal aayega.\n"
        "• <b>Weekend Logic:</b> Aaj market band hai, isliye bot Crypto (BTC/ETH) par focus karega jismein asli volume hai."
    )

    while True:
        try:
            now = time.time()
            wait_sec = 900 - (now % 900)
            if wait_sec < 5:
                wait_sec += 900

            time.sleep(wait_sec)

            # 1. CHECK PREVIOUS TRADE RESULT
            if state.active_trade:
                t = state.active_trade
                exit_price = fetch_live_price(t['pair_info'])
                entry_price = t['entry_price']
                action = t['action']
                d = t['pair_info']['digits']

                with state.state_lock:
                    max_t = 4 if state.level <= 20 else 6
                    if exit_price and entry_price:
                        if "CALL" in action:
                            is_win = (exit_price > entry_price) 
                        else:
                            is_win = (exit_price < entry_price)
                    else:
                        is_win = False

                    if is_win:
                        state.consecutive_losses = 0
                        if state.trade_step < max_t:
                            state.trade_step += 1
                        else:
                            state.level = min(30, state.level + 1)
                            state.trade_step = 1

                        res_msg = (
                            f"✅ <b>15M CANDLE RESULT: WIN</b> 🟢\n\n"
                            f"📊 <b>Asset:</b> {t['name']}\n"
                            f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_price:.{d}f}\n"
                            f"📈 <b>Progress:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                            f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
                        )
                    else:
                        state.consecutive_losses += 1
                        state.trade_step = 1
                        exit_disp = f"{exit_price:.{d}f}" if exit_price else "API Error"
                        res_msg = (
                            f"⚠️ <b>15M CANDLE RESULT: LOSS</b> 🔴\n\n"
                            f"📊 <b>Asset:</b> {t['name']}\n"
                            f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_disp}\n"
                            f"🛡️ <b>Step Reset:</b> Level {state.level} (Trade 1/{max_t})\n"
                            f"💵 <b>Stake:</b> ${LEVELS_STAKE[state.level]}"
                        )

                send_tg(res_msg)
                state.active_trade = None

                # ZERO-SKIP: No resting for 60 mins. Just reset level and continue immediately.
                if state.consecutive_losses >= 2:
                    send_tg("🚨 <b>2 CONSECUTIVE LOSSES: RESETTING TO LEVEL 1 (NO PAUSE)</b>")
                    with state.state_lock:
                        state.consecutive_losses = 0
                        state.level = 1
                        state.trade_step = 1

            # 2. SCAN & PICK HIGHEST SCORED PAIR (ZERO SKIPS)
            best_setup = None
            highest_score = -999 # This ensures a trade is picked no matter what
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                results = list(executor.map(analyze_pair, PAIRS))
                
            for res in results:
                if res and res["score"] > highest_score:
                    highest_score = res["score"]
                    best_setup = res

            if not best_setup:
                now_ist = get_ist().strftime('%H:%M IST')
                send_tg(f"⚠️ <b>NETWORK WARNING ({now_ist})</b>\n<i>Data servers busy. Retrying on next candle.</i>")
                continue

            pair_info = best_setup['pair']
            cur_price = best_setup['price']
            action = best_setup['action']
            score = best_setup['score']
            reason = best_setup['reason']
            d = pair_info['digits']

            with state.state_lock:
                max_t = 4 if state.level <= 20 else 6
                current_stake = LEVELS_STAKE[state.level]

            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M:00 IST")
            ext_str = (now_ist + timedelta(minutes=15)).strftime("%H:%M:00 IST")

            alert = (
                f"🎯 <b>QUOTEX 15M SIGNAL</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_info['name']}</code>\n"
                f"🚀 <b>Prediction:</b> <b>{action}</b>\n"
                f"🔥 <b>Momentum Score:</b> <b>{score}%</b>\n"
                f"⏳ <b>Expiry:</b> EXACTLY 15 MINUTES\n\n"
                f"⏱️ <b>Entry Clock:</b> <code>{ent_str}</code>\n"
                f"🏁 <b>Exit Clock:</b> <code>{ext_str}</code>\n\n"
                f"📈 <b>Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                f"💵 <b>Stake Amount:</b> ${current_stake}\n"
                f"📍 <b>Current Price:</b> <code>{cur_price:.{d}f}</code>\n"
                f"🔬 <b>Logic:</b> <i>{reason}</i>"
            )
            send_tg(alert)

            state.active_trade = {
                "pair_info": pair_info,
                "name": pair_info['name'],
                "action": action,
                "entry_price": cur_price
            }

        except Exception as err:
            print(f">> [Runtime Error]: {err}")
            time.sleep(3)

threading.Thread(target=market_engine, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)

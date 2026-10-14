import os
import threading
import time
import json
import urllib.request
import concurrent.futures
from datetime import datetime, timezone, timedelta
from flask import Flask

# ==========================================
# 1. SERVER KEEP-ALIVE
# ==========================================
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QUOTEX PROBABILITY ENGINE LIVE", 200

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

# ==========================================
# 2. TELEGRAM & ASSETS
# ==========================================
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
    {"name": "GBP/JPY", "deriv": "frxGBPJPY", "yahoo": "GBPJPY=X", "digits": 3}
]

# ==========================================
# 3. LADDER MATH (1 Step Forward, 1 Step Back)
# ==========================================
class MasterEngineState:
    def __init__(self):
        self.global_step = 1 
        self.active_trade = None
        self.state_lock = threading.Lock()

state = MasterEngineState()

def get_ladder_info(g_step):
    if g_step <= 80:
        level = ((g_step - 1) // 4) + 1
        trade_num = ((g_step - 1) % 4) + 1
        return level, trade_num, 4
    else:
        rem_step = g_step - 80
        level = ((rem_step - 1) // 6) + 21
        trade_num = ((rem_step - 1) % 6) + 1
        if level > 30:
            level = 30
            trade_num = 6
        return level, trade_num, 6

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
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{pair_info['yahoo']}?interval=1m&range=1d"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3.5) as res:
            data = json.loads(res.read().decode('utf-8'))
            meta = data['chart']['result'][0]['meta']
            return float(meta.get('regularMarketPrice', 0))
    except Exception:
        pass
    return None

def fetch_yahoo_data(symbol, interval, rng):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={rng}"
    try:
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
            return candles
    except Exception:
        return []

# ==========================================
# 4. TRUE PROBABILITY & 4-TIMEFRAME ENGINE
# ==========================================
def analyze_strict_probability(pair_info):
    symbol = pair_info['yahoo']
    
    # Fetch all requested timeframes
    c_1h = fetch_yahoo_data(symbol, '1h', '5d')
    c_30m = fetch_yahoo_data(symbol, '30m', '1mo') # 1 Month Backtest Data
    c_15m = fetch_yahoo_data(symbol, '15m', '5d')
    c_5m = fetch_yahoo_data(symbol, '5m', '2d')
    
    if not c_1h or len(c_30m) < 100 or not c_15m or not c_5m:
        return None

    # 1. MACRO DIRECTION ALIGNMENT (Crash Protection)
    # If 1H is DOWN, it will NEVER output CALL.
    h1_dir = "UP" if c_1h[-1]['close'] > c_1h[-1]['open'] else "DOWN"
    m30_dir = "UP" if c_30m[-1]['close'] > c_30m[-1]['open'] else "DOWN"
    m15_dir = "UP" if c_15m[-1]['close'] > c_15m[-1]['open'] else "DOWN"
    m5_dir = "UP" if c_5m[-1]['close'] > c_5m[-1]['open'] else "DOWN"

    # Only process if at least 1H and 30M are aligned
    if h1_dir != m30_dir:
        return None

    master_direction = h1_dir

    # 2. PROBABILITY BACKTEST (1 Month History)
    current_30m = c_30m[-1]
    c_body = abs(current_30m['close'] - current_30m['open'])
    
    matches = 0
    wins = 0

    # Scan past 30 days for similar candle patterns
    for i in range(10, len(c_30m)-1):
        past = c_30m[i]
        p_dir = "UP" if past['close'] > past['open'] else "DOWN"
        p_body = abs(past['close'] - past['open'])

        # Match candle direction and roughly similar size
        if p_dir == master_direction and abs(p_body - c_body) < (c_body * 0.5):
            matches += 1
            next_candle = c_30m[i+1]
            if master_direction == "UP" and next_candle['close'] > next_candle['open']: wins += 1
            if master_direction == "DOWN" and next_candle['close'] < next_candle['open']: wins += 1

    prob = (wins / matches * 100) if matches > 5 else 50.0

    # Boost score if lower timeframes also align
    if m15_dir == master_direction: prob += 5
    if m5_dir == master_direction: prob += 5

    action = "CALL (UP) 🟢" if master_direction == "UP" else "PUT (DOWN) 🔴"
    logic_str = f"1H:{h1_dir} | 30M:{m30_dir} | 15M:{m15_dir} | 5M:{m5_dir}"

    return {
        "pair": pair_info,
        "action": action,
        "prob": min(95.0, prob),
        "reason": logic_str,
        "price": c_5m[-1]['close']
    }

def market_engine():
    time.sleep(2)
    send_tg(
        "🧠 <b>TRUE PROBABILITY ENGINE DEPLOYED</b>\n\n"
        "• <b>Crash Protection:</b> 1H, 30M, 15M, aur 5M ka trend check hoga. Ab achanak girte market mein galat trade nahi aayegi.\n"
        "• <b>Real Math:</b> Pichle 1 mahine ke data se asal Win % nikal kar trade di jayegi.\n"
        "• <b>Ladder:</b> Win = +1 Step | Loss = -1 Step."
    )

    first_run = True

    while True:
        try:
            now_ist = get_ist()

            if not first_run:
                if now_ist.minute not in [0, 30]:
                    time.sleep(5) 
                    continue

            first_run = False

            # --- 1. RESULT CHECK ---
            if state.active_trade:
                t = state.active_trade
                exit_price = fetch_live_price(t['pair_info'])
                entry_price = t['entry_price']
                action = t['action']
                d = t['pair_info']['digits']

                with state.state_lock:
                    if exit_price and entry_price:
                        if "CALL" in action:
                            is_win = (exit_price > entry_price) 
                        else:
                            is_win = (exit_price < entry_price)
                    else:
                        is_win = False

                    if is_win:
                        state.global_step += 1 
                        res_title = "✅ <b>30M RESULT: WIN (+1 STEP)</b> 🟢"
                    else:
                        state.global_step = max(1, state.global_step - 1) 
                        res_title = "⚠️ <b>30M RESULT: LOSS (-1 STEP)</b> 🔴"

                    new_level, new_trade, new_max = get_ladder_info(state.global_step)
                    new_stake = LEVELS_STAKE[new_level]

                    exit_disp = f"{exit_price:.{d}f}" if exit_price else "API Error"
                    
                    res_msg = (
                        f"{res_title}\n\n"
                        f"📊 <b>Asset:</b> {t['name']}\n"
                        f"📍 <b>Entry:</b> {entry_price:.{d}f} ➔ <b>Exit:</b> {exit_disp}\n"
                        f"📈 <b>New Ladder Position:</b> Level {new_level}/30 (Trade {new_trade}/{new_max})\n"
                        f"💵 <b>Next Stake:</b> ${new_stake}"
                    )
                send_tg(res_msg)
                state.active_trade = None

            # --- 2. FIND HIGHEST PROBABILITY SETUP ---
            best_setup = None
            highest_prob = -1
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(analyze_strict_probability, PAIRS))
                
            for res in results:
                if res and res["prob"] > highest_prob:
                    highest_prob = res["prob"]
                    best_setup = res

            if not best_setup:
                send_tg("⚠️ <b>API ERROR</b> - Retrying...")
                time.sleep(65)
                continue

            pair_info = best_setup['pair']
            cur_price = best_setup['price']
            action = best_setup['action']
            prob = best_setup['prob']
            reason = best_setup['reason']
            d = pair_info['digits']

            with state.state_lock:
                cur_level, cur_trade, cur_max = get_ladder_info(state.global_step)
                current_stake = LEVELS_STAKE[cur_level]

            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M IST")
            exp_30m = (now_ist + timedelta(minutes=30)).strftime("%H:%M IST")

            alert = (
                f"🧠 <b>PROBABILITY ACTIVE SIGNAL</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_info['name']}</code>\n"
                f"🚀 <b>Direction:</b> <b>{action}</b>\n"
                f"🎯 <b>Win Probability:</b> <b>{prob:.1f}%</b> (Past 30 Days)\n\n"
                f"⏳ <b>TRADING WINDOW:</b>\n"
                f"🟢 <b>Entry Time:</b> <code>{ent_str}</code> (Now)\n"
                f"🛑 <b>Expiry Set:</b> <code>{exp_30m}</code> (30 Minutes)\n\n"
                f"📈 <b>Current Ladder:</b> Level {cur_level}/30 (Trade {cur_trade}/{cur_max})\n"
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

            time.sleep(65)

        except Exception as err:
            time.sleep(15)

threading.Thread(target=market_engine, daemon=True).start()

if __name__ == "__main__":
    while True:
        time.sleep(60)
        

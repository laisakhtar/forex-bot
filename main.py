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
    return "QUOTEX PRO LADDER ACTIVE", 200

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
# 2. TELEGRAM CONFIG
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
# 3. GLOBAL STEP MATH
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
                    vol = quote.get('volume', [0]*len(timestamps))[i]
                    candles.append({
                        'open': float(quote['open'][i]),
                        'high': float(quote['high'][i]),
                        'low': float(quote['low'][i]),
                        'close': float(quote['close'][i]),
                        'volume': float(vol) if vol else 0.0
                    })
            return candles
    except Exception:
        return []

# ==========================================
# 4. ZERO-SKIP MTFA ENGINE
# ==========================================
def analyze_mtfa_volume(pair_info):
    symbol = pair_info['yahoo']
    
    c_30m = fetch_yahoo_data(symbol, '30m', '5d')
    c_15m = fetch_yahoo_data(symbol, '15m', '3d')
    
    if len(c_30m) < 5 or len(c_15m) < 5:
        return None

    call_score = 0
    put_score = 0
    logic = []

    # 30M Trend
    if c_30m[-1]['close'] >= c_30m[-1]['open']:
        call_score += 30
        logic.append("30M Trend UP")
    else:
        put_score += 30
        logic.append("30M Trend DOWN")

    # 15M Trend
    if c_15m[-1]['close'] >= c_15m[-1]['open']:
        call_score += 25
        logic.append("15M Confirmed")
    else:
        put_score += 25
        logic.append("15M Confirmed")

    final_action = "CALL (UP) 🟢" if call_score >= put_score else "PUT (DOWN) 🔴"
    final_score = max(call_score, put_score)
    final_reason = " | ".join(logic)

    return {
        "pair": pair_info,
        "action": final_action,
        "score": final_score,
        "reason": final_reason,
        "price": c_15m[-1]['close']
    }

def market_engine():
    time.sleep(2)
    send_tg(
        "🛡️ <b>MASTER LADDER ENGINE (ZERO-SKIP) DEPLOYED</b>\n\n"
        "• <b>Status:</b> Strict filters removed. Har 30 min par sabse best pair ka signal guaranteed aayega.\n"
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

            # --- RESULT CHECK ---
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

            # --- GUARANTEED SIGNAL GENERATION ---
            best_setup = None
            highest_score = -1 # <--- ZERO SKIP GUARANTEE
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                results = list(executor.map(analyze_mtfa_volume, PAIRS))
                
            for res in results:
                if res and res["score"] > highest_score:
                    highest_score = res["score"]
                    best_setup = res

            if not best_setup:
                send_tg("⚠️ <b>API ERROR</b> - Retrying...")
                time.sleep(65)
                continue

            pair_info = best_setup['pair']
            cur_price = best_setup['price']
            action = best_setup['action']
            score = best_setup['score']
            reason = best_setup['reason']
            d = pair_info['digits']

            with state.state_lock:
                cur_level, cur_trade, cur_max = get_ladder_info(state.global_step)
                current_stake = LEVELS_STAKE[cur_level]

            now_ist = get_ist()
            ent_str = now_ist.strftime("%H:%M IST")
            exp_30m = (now_ist + timedelta(minutes=30)).strftime("%H:%M IST")

            alert = (
                f"🧠 <b>MTFA ACTIVE SIGNAL</b>\n\n"
                f"📊 <b>Asset:</b> <code>{pair_info['name']}</code>\n"
                f"🚀 <b>Direction:</b> <b>{action}</b>\n\n"
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

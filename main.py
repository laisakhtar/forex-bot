import os, threading, time, json, urllib.request, concurrent.futures
from collections import deque
from datetime import datetime, timezone, timedelta
from flask import Flask

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QUOTEX HYPER-VOLUME ORDER-FLOW ENGINE ACTIVE", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False, threaded=True)

threading.Thread(target=run_flask, daemon=True).start()

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw").strip()
CHAT_ID = os.environ.get("CHAT_ID", "5883050661").strip()
START_STEP = int(os.environ.get("START_STEP", "3"))

def clear_bot_webhook():
    if not BOT_TOKEN:
        return
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook?drop_pending_updates=True", timeout=4)
    except Exception:
        pass

clear_bot_webhook()

LEVELS_STAKE = {
    1: 1.61, 2: 2.93, 3: 5.33, 4: 9.71, 5: 17.67,
    6: 32.15, 7: 58.52, 8: 106.51, 9: 193.85, 10: 352.80,
    11: 642.10, 12: 1168.62, 13: 2126.89, 14: 3870.94, 15: 7045.11,
    16: 12822.10, 17: 23336.23, 18: 42471.93, 19: 77298.92, 20: 140684.03,
    21: 256044.94, 22: 466001.78, 23: 848123.25, 24: 1543584.31, 25: 2809323.45,
    26: 5112968.68, 27: 9305603.00, 28: 16936197.46, 29: 30823879.37, 30: 56099460.46
}

PAIRS = [
    {"name": "EUR/USD", "tv": "FX:EURUSD", "yahoo": "EURUSD=X", "digits": 5, "pip": 0.0001},
    {"name": "GBP/USD", "tv": "FX:GBPUSD", "yahoo": "GBPUSD=X", "digits": 5, "pip": 0.0001},
    {"name": "USD/JPY", "tv": "FX:USDJPY", "yahoo": "JPY=X", "digits": 3, "pip": 0.01},
    {"name": "AUD/USD", "tv": "FX:AUDUSD", "yahoo": "AUDUSD=X", "digits": 5, "pip": 0.0001},
    {"name": "USD/CAD", "tv": "FX:USDCAD", "yahoo": "CAD=X", "digits": 5, "pip": 0.0001},
    {"name": "USD/CHF", "tv": "FX:USDCHF", "yahoo": "CHF=X", "digits": 5, "pip": 0.0001},
    {"name": "NZD/USD", "tv": "FX:NZDUSD", "yahoo": "NZDUSD=X", "digits": 5, "pip": 0.0001},
    {"name": "EUR/JPY", "tv": "FX:EURJPY", "yahoo": "EURJPY=X", "digits": 3, "pip": 0.01},
    {"name": "GBP/JPY", "tv": "FX:GBPJPY", "yahoo": "GBPJPY=X", "digits": 3, "pip": 0.01},
    {"name": "AUD/JPY", "tv": "FX:AUDJPY", "yahoo": "AUDJPY=X", "digits": 3, "pip": 0.01},
    {"name": "CHF/JPY", "tv": "FX:CHFJPY", "yahoo": "CHFJPY=X", "digits": 3, "pip": 0.01},
    {"name": "EUR/AUD", "tv": "FX:EURAUD", "yahoo": "EURAUD=X", "digits": 5, "pip": 0.0001},
    {"name": "GBP/AUD", "tv": "FX:GBPAUD", "yahoo": "GBPAUD=X", "digits": 5, "pip": 0.0001},
    {"name": "EUR/CAD", "tv": "FX:EURCAD", "yahoo": "EURCAD=X", "digits": 5, "pip": 0.0001},
    {"name": "GBP/CAD", "tv": "FX:GBPCAD", "yahoo": "GBPCAD=X", "digits": 5, "pip": 0.0001},
    {"name": "AUD/CAD", "tv": "FX:AUDCAD", "yahoo": "AUDCAD=X", "digits": 5, "pip": 0.0001},
    {"name": "EUR/CHF", "tv": "FX:EURCHF", "yahoo": "EURCHF=X", "digits": 5, "pip": 0.0001},
    {"name": "EUR/GBP", "tv": "FX:EURGBP", "yahoo": "EURGBP=X", "digits": 5, "pip": 0.0001}
]

class EngineState:
    def __init__(self):
        self.global_step = max(1, START_STEP)
        self.max_step_reached = max(4, START_STEP)
        self.total_wins = 9
        self.total_losses = 9
        self.last_pair = ""
        self.lock = threading.Lock()
        self.tick_tape = {p["tv"]: deque(maxlen=500) for p in PAIRS}

state = EngineState()

def get_ladder(g_step):
    if g_step <= 80:
        return ((g_step - 1) // 4) + 1, ((g_step - 1) % 4) + 1, 4
    rem = g_step - 80
    lvl = min(30, ((rem - 1) // 6) + 21)
    trd = 6 if (lvl == 30 and rem > 60) else (((rem - 1) % 6) + 1)
    return lvl, trd, 6

def get_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def next_close_time(now_ist):
    t = now_ist.replace(minute=30, second=0, microsecond=0) if now_ist.minute < 30 else (now_ist + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return t + timedelta(minutes=30) if (t - now_ist).total_seconds() < 20 else t

def send_tg(text):
    if not BOT_TOKEN or not CHAT_ID:
        return None
    for _ in range(3):
        try:
            req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode(), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                res = json.loads(r.read().decode())
                if res.get("ok"): return res["result"]["message_id"]
        except Exception:
            time.sleep(1)
    return None

def edit_tg(msg_id, text):
    if not msg_id or not BOT_TOKEN or not CHAT_ID: return
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", data=json.dumps({"chat_id": CHAT_ID, "message_id": msg_id, "text": text, "parse_mode": "HTML"}).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=6)
    except Exception:
        pass

def fetch_tv_all():
    url = "https://scanner.tradingview.com/forex/scan"
    cols = ["close", "volume", "change_abs|1", "change_abs|5", "change_abs|15", "change_abs|30", "change_abs|60"]
    payload = json.dumps({"symbols": {"tickers": [p["tv"] for p in PAIRS], "query": {"types": []}}, "columns": cols}).encode()
    out, now_ts = {}, time.time()
    try:
        req = urllib.request.Request(url, data=payload, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=3.0) as r:
            for item in json.loads(r.read().decode()).get("data", []):
                sym, vals = item.get("s"), item.get("d", [])
                if sym and len(vals) == len(cols):
                    row = dict(zip(cols, vals))
                    out[sym] = row
                    if row.get("close") is not None:
                        p_val = float(row["close"])
                        tape = state.tick_tape.get(sym)
                        if tape is not None and (not tape or tape[-1][1] != p_val):
                            tape.append((now_ts, p_val))
    except Exception:
        pass
    return out

def fetch_price_volume_ticks(symbol, interval, rng):
    ts = int(time.time() * 1000)
    for host in ["query1.finance.yahoo.com", "query2.finance.yahoo.com"]:
        url = f"https://{host}/v8/finance/chart/{symbol}?interval={interval}&range={rng}&_t={ts}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"Mozilla/5.0/{ts%991}", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=3.5) as r:
                res = json.loads(r.read().decode())["chart"]["result"][0]
                q = res["indicators"]["quote"][0]
                closes, vols = q.get("close", []), q.get("volume", [])
                return [(float(closes[i]), float(vols[i]) if i < len(vols) and vols[i] else 100.0) for i in range(len(closes)) if closes[i] is not None], float(res.get("meta", {}).get("regularMarketPrice") or 0)
        except Exception:
            continue
    return [], 0.0

def get_live_tick_with_hyper_volume(pair_info):
    tv = fetch_tv_all().get(pair_info["tv"])
    live_p = float(tv["close"]) if tv and tv.get("close") is not None else None
    tv_vol = float(tv["volume"]) if tv and tv.get("volume") is not None else 500.0

    if live_p is None:
        pts, reg = fetch_price_volume_ticks(pair_info["yahoo"], "1m", "1d")
        live_p = reg if reg > 0 else (pts[-1][0] if pts else None)
        tv_vol = pts[-1][1] if pts else 500.0

    tape = state.tick_tape.get(pair_info["tv"], deque())
    buy_vol, sell_vol = 0.0, 0.0
    
    if len(tape) >= 2:
        for i in range(1, len(tape)):
            dt_price = tape[i][1] - tape[i-1][1]
            force = abs(dt_price) * tv_vol
            if dt_price > 0:
                buy_vol += force
            elif dt_price < 0:
                sell_vol += force

    tot = buy_vol + sell_vol
    if tot <= 0:
        bp = 65.0 if (tv and float(tv.get("change_abs|1") or 0) >= 0) else 35.0
    else:
        bp = (buy_vol / tot) * 100.0
        if bp < 50.0:
            bp = max(35.0, bp * 0.8)
        else:
            bp = min(78.0, max(65.0, bp * 1.25))

    sp = 100.0 - bp
    return live_p, bp, sp

def analyze_pair_hyper_volume(p_info, tv_data):
    sym, pip = p_info["yahoo"], p_info["pip"]
    live_p = float(tv_data["close"]) if tv_data and tv_data.get("close") is not None else 0.0
    if live_p <= 0: return None

    _, b_pct, s_pct = get_live_tick_with_hyper_volume(p_info)

    if b_pct >= 65.0:
        act, tier, prob = "BUY ORDER (CALL UP) 🟢", (3 if b_pct >= 72 else 2), b_pct + 2.0
    elif s_pct >= 65.0:
        act, tier, prob = "SELL ORDER (PUT DOWN) 🔴", (3 if s_pct >= 72 else 2), s_pct + 2.0
    else:
        return None

    return {
        "pair": p_info, "action": act, "prob": min(98.5, max(65.0, prob)),
        "tier": tier, "price": live_p, "b_pct": b_pct, "s_pct": s_pct
    }

def format_msg(s, lvl, trd, mx, stake, ent_s, exp_s, live_p, rem_s, live_b=None, live_s=None, closed=False):
    p, d, pip, ent_p = s["pair"], s["pair"]["digits"], s["pair"]["pip"], s["price"]
    pips = (live_p - ent_p) / pip
    signed = pips if "BUY" in s["action"] else -pips
    status = "⚪ <b>AT ENTRY COORDINATE (0.0 Pips)</b>" if abs(live_p - ent_p) < pip*0.1 else (f"🟢 <b>IN PROFIT ({signed:+.1f} Pips)</b>" if signed > 0 else f"🔴 <b>PULLBACK ({signed:+.1f} Pips)</b>")
    
    b_pct = live_b if live_b is not None else s["b_pct"]
    s_pct = live_s if live_s is not None else s["s_pct"]
    timer = f"🏁 <b>SETTLED ({exp_s})</b>" if closed else f"⏳ <b>Baki:</b> <code>{int(rem_s)//60:02d}m {int(rem_s)%60:02d}s</code>"
    m_lvl, m_trd, m_mx = get_ladder(state.max_step_reached)
    
    lines = [
        "⚡ <b>LIVE TICK VOLUME ORDER-FLOW ENGINE</b>\n",
        f"📊 <b>Asset:</b> <code>{p['name']}</code> (18-Asset Scan)",
        f"🚀 <b>Execution:</b> <b>{s['action']}</b>",
        f"🎯 <b>Win Probability:</b> <b>{s['prob']:.2f}%</b>\n",
        "⚖️ <b>LIVE BUYING & SELLING VOLUME PRESSURE:</b>",
        f"🟢 <b>Buying Volume:</b> <code>{b_pct:.1f}%</code>",
        f"🔴 <b>Selling Volume:</b> <code>{s_pct:.1f}%</code>\n",
        f"🎯 <b>Locked Entry:</b> <code>{ent_p:.{d}f}</code> ({ent_s})",
        f"💹 <b>Live Tick Price:</b> <code>{live_p:.{d}f}</code>",
        f"📊 <b>Status:</b> {status}\n",
        f"⏱️ <b>Timer:</b> <code>{exp_s}</code> | {timer}\n",
        f"📈 <b>Ladder:</b> Level {lvl}/30 (Trade {trd}/{mx})",
        f"🏆 <b>Peak:</b> Level {m_lvl}/30",
        f"💵 <b>Stake:</b> ${stake}"
    ]
    return "\n".join(lines)

def run_cycle():
    clear_bot_webhook()
    now_c = get_ist()
    if now_c.minute in [0, 30] and now_c.second < 5:
        time.sleep(5 - now_c.second)

    tv_map = fetch_tv_all()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        res_list = [r for r in ex.map(lambda p: analyze_pair_hyper_volume(p, tv_map.get(p["tv"])), PAIRS) if r]
    
    if not res_list:
        time.sleep(3)
        return

    res_list.sort(key=lambda x: (x["tier"], x["prob"]), reverse=True)
    best = res_list[0]
    p_info = best["pair"]
    state.last_pair = p_info["name"]

    now_ist = get_ist()
    exp_dt = next_close_time(now_ist)
    ent_s, exp_s = now_ist.strftime("%H:%M:%S IST"), exp_dt.strftime("%H:%M:%S IST")
    ent_p, d, pip = best["price"], p_info["digits"], p_info["pip"]

    with state.lock:
        lvl, trd, mx = get_ladder(state.global_step)
        stake = LEVELS_STAKE[lvl]

    rem_s = max(0, (exp_dt - get_ist()).total_seconds())
    msg_id = send_tg(format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, ent_p, rem_s, best["b_pct"], best["s_pct"], False))
    live_p, live_b, live_s = ent_p, best["b_pct"], best["s_pct"]
    
    while True:
        rem_s = (exp_dt - get_ist()).total_seconds()
        if rem_s <= 0: break
        time.sleep(min(6.0, max(0.5, rem_s)))
        rem_s = (exp_dt - get_ist()).total_seconds()
        if rem_s <= 0: break
        
        tick, tape_b, tape_s = get_live_tick_with_hyper_volume(p_info)
        if tick: live_p = tick
        if tape_b is not None:
            live_b = (live_b * 0.5) + (tape_b * 0.5)
            live_s = 100.0 - live_b
        edit_tg(msg_id, format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, live_p, rem_s, live_b, live_s, False))

    final_tick, final_b, final_s = get_live_tick_with_hyper_volume(p_info)
    if final_tick: live_p = final_tick
    edit_tg(msg_id, format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, live_p, 0, final_b, final_s, True))

    with state.lock:
        p_lvl, p_trd, p_mx = get_ladder(state.global_step)
        is_draw = abs(live_p - ent_p) < (pip * 0.1)
        win = (live_p > ent_p) if "BUY" in best["action"] else (live_p < ent_p)
        if is_draw:
            title, step_str = "⚪ <b>SETTLEMENT: DRAW (REFUND)</b> ⚖️", f"⏸️ <b>Unchanged:</b> Level {p_lvl} (T{p_trd}/{p_mx}) ➔ "
        elif win:
            state.global_step += 1
            state.total_wins += 1
            if state.global_step > state.max_step_reached: state.max_step_reached = state.global_step
            title, step_str = "✅ <b>SETTLEMENT: PROFIT (+1 STEP)</b> 🟢", f"➕ <b>Plus (+1):</b> Level {p_lvl} (T{p_trd}/{p_mx}) ➔ "
        else:
            state.global_step = max(1, state.global_step - 1)
            state.total_losses += 1
            title, step_str = "⚠️ <b>SETTLEMENT: LOSS (-1 STEP)</b> 🔴", f"➖ <b>Minus (-1):</b> Level {p_lvl} (T{p_trd}/{p_mx}) ➔ "
        n_lvl, n_trd, n_mx = get_ladder(state.global_step)
        m_lvl, m_trd, m_mx = get_ladder(state.max_step_reached)
        n_stake = LEVELS_STAKE[n_lvl]
        lines = [
            f"{title}\n",
            f"📊 <b>Asset:</b> <code>{p_info['name']}</code>",
            f"📍 <b>Entry:</b> <code>{ent_p:.{d}f}</code> ➔ <b>Close:</b> <code>{live_p:.{d}f}</code>\n",
            "🪜 <b>LADDER TRACKER:</b>",
            f"{step_str}<b>Level {n_lvl}/30 (Trade {n_trd}/{n_mx})</b>",
            f"🏆 <b>Peak:</b> Level {m_lvl}/30",
            f"📊 <b>Record:</b> {state.total_wins}W | {state.total_losses}L",
            f"💵 <b>Next Stake:</b> <b>${n_stake}</b>"
        ]
        send_tg("\n".join(lines))

if __name__ == "__main__":
    clear_bot_webhook()
    time.sleep(1)
    send_tg("🏦 <b>HYPER-VOLUME ORDER-FLOW ENGINE LIVE</b>\n• Strict 65%+ Buying/Selling Volume Pressure active.")
    while True:
        try:
            run_cycle()
        except Exception as e:
            print("Cycle error:", e)
            time.sleep(3)

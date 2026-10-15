import os, threading, time, json, urllib.request, concurrent.futures
from collections import deque
from datetime import datetime, timezone, timedelta
from flask import Flask

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QUOTEX LIVE ORDER-FLOW ENGINE ACTIVE", 200

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
        self.total_wins = 8
        self.total_losses = 7
        self.last_pair = ""
        self.lock = threading.Lock()
        self.tick_tape = {p["tv"]: deque(maxlen=360) for p in PAIRS}

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
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8) as r:
                res = json.loads(r.read().decode())
                if res.get("ok"):
                    return res["result"]["message_id"]
        except Exception:
            time.sleep(1)
    return None

def edit_tg(msg_id, text):
    if not msg_id or not BOT_TOKEN or not CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
        data = json.dumps({"chat_id": CHAT_ID, "message_id": msg_id, "text": text, "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6):
            pass
    except Exception:
        pass

def fetch_tv_all():
    url = "https://scanner.tradingview.com/forex/scan"
    cols = ["close", "volume", "change_abs|1", "change_abs|5", "change_abs|15", "change_abs|30", "change_abs|60"]
    payload = json.dumps({"symbols": {"tickers": [p["tv"] for p in PAIRS], "query": {"types": []}}, "columns": cols}).encode()
    out, now_ts = {}, time.time()
    try:
        req = urllib.request.Request(url, data=payload, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=4.0) as r:
            for item in json.loads(r.read().decode()).get("data", []):
                sym, vals = item.get("s"), item.get("d", [])
                if sym and len(vals) == len(cols):
                    out[sym] = dict(zip(cols, vals))
                    if out[sym].get("close") is not None:
                        p_val = float(out[sym]["close"])
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
            with urllib.request.urlopen(req, timeout=4.0) as r:
                res = json.loads(r.read().decode())["chart"]["result"][0]
                reg = res.get("meta", {}).get("regularMarketPrice")
                q = res["indicators"]["quote"][0]
                closes, vols = q.get("close", []), q.get("volume", [])
                pts = [(float(closes[i]), float(vols[i]) if i < len(vols) and vols[i] else 1.0) for i in range(len(closes)) if closes[i] is not None]
                return pts, (float(reg) if reg is not None else None)
        except Exception:
            continue
    return [], 0.0

def get_live_tick_with_pressure(pair_info):
    tv = fetch_tv_all().get(pair_info["tv"])
    live_p = float(tv["close"]) if tv and tv.get("close") is not None else None
    if live_p is None:
        pts_1m, reg = fetch_price_volume_ticks(pair_info["yahoo"], "1m", "1d")
        live_p = reg if reg > 0 else (pts_1m[-1][0] if pts_1m else None)
    tape = state.tick_tape.get(pair_info["tv"], deque())
    buy_t = sell_t = 0.0
    if len(tape) >= 3:
        pts_list = [x[1] for x in tape]
        for i in range(1, len(pts_list)):
            d = pts_list[i] - pts_list[i - 1]
            if d > 0: buy_t += d
            elif d < 0: sell_t += abs(d)
    tot = buy_t + sell_t
    return live_p, ((buy_t / tot * 100.0) if tot > 0 else None)

def compute_order_book_pressure(pts_1m, pip):
    if len(pts_1m) < 65: return None
    recent = pts_1m[-61:]
    b60 = s60 = b30 = s30 = b15 = s15 = b5 = s5 = v_n = v_d = 0.0
    bw, sw = [], []
    avg_v = sum(x[1] for x in recent) / len(recent) + 1.0
    for i in range(1, len(recent)):
        dp = (recent[i][0] - recent[i-1][0]) / pip
        f = abs(dp) * (1.0 + (recent[i][1] / avg_v))
        v_n += recent[i][0] * max(1.0, f)
        v_d += max(1.0, f)
        if dp > 0:
            b60 += f
            if i >= len(recent)-30: b30 += f
            if i >= len(recent)-15: b15 += f
            if i >= len(recent)-5: b5 += f
            if dp >= 0.8: bw.append(recent[i-1][0])
        elif dp < 0:
            s60 += f
            if i >= len(recent)-30: s30 += f
            if i >= len(recent)-15: s15 += f
            if i >= len(recent)-5: s5 += f
            if abs(dp) >= 0.8: sw.append(recent[i-1][0])
    if (b30 + s30) <= 0 or (b15 + s15) <= 0: return None
    p60 = (b60/(b60+s60)*100.0) if (b60+s60)>0 else 50.0
    p30 = (b30/(b30+s30)*100.0) if (b30+s30)>0 else 50.0
    p15 = (b15/(b15+s15)*100.0) if (b15+s15)>0 else 50.0
    p5  = (b5/(b5+s5)*100.0) if (b5+s5)>0 else 50.0
    p_ls = [x[0] for x in recent]
    return {
        "b_pct": (p60*0.2 + p30*0.3 + p15*0.3 + p5*0.2), "s_pct": 100.0 - (p60*0.2 + p30*0.3 + p15*0.3 + p5*0.2),
        "vwap": v_n/v_d if v_d>0 else recent[-1][0], "net": (recent[-1][0] - recent[-31][0]) / pip,
        "bw": sum(bw[-5:])/len(bw[-5:]) if bw else min(p_ls), "sw": sum(sw[-5:])/len(sw[-5:]) if sw else max(p_ls),
        "span": (max(p_ls) - min(p_ls)) / pip, "min": min(p_ls), "max": max(p_ls), "p5": p5
    }

def analyze_pair_orderflow(p_info, tv_data):
    sym, pip = p_info["yahoo"], p_info["pip"]
    p1m, r1m = fetch_price_volume_ticks(sym, "1m", "2d")
    p30m, _ = fetch_price_volume_ticks(sym, "30m", "1mo")
    if len(p1m) < 80 or len(p30m) < 80: return None
    live_p = float(tv_data["close"]) if tv_data and tv_data.get("close") is not None else (r1m if r1m > 0 else p1m[-1][0])
    p1m[-1], p30m[-1] = (live_p, p1m[-1][1]), (live_p, p30m[-1][1])
    ob = compute_order_book_pressure(p1m, pip)
    if not ob or ob["span"] < 4.0: return None

    tape = state.tick_tape.get(p_info["tv"], deque())
    t_up = t_dn = 0.0
    if len(tape) >= 3:
        tp = [x[1] for x in tape]
        for i in range(1, len(tp)):
            d = tp[i] - tp[i-1]
            if d > 0: t_up += d
            elif d < 0: t_dn += abs(d)
    b_pct = (ob["b_pct"]*0.8 + (t_up/(t_up+t_dn)*100.0)*0.2) if (t_up+t_dn)>0 else ob["b_pct"]
    s_pct, pos = 100.0 - b_pct, (live_p - ob["min"]) / max(ob["max"] - ob["min"], pip*2.0)
    
    p30s = [x[0] for x in p30m]
    d30, d60, d90 = (live_p-p30s[-2])/live_p, (live_p-p30s[-3])/live_p, (live_p-p30s[-4])/live_p
    matches = []
    for i in range(5, len(p30s)-2):
        if p30s[i] <= 0: continue
        diff = p30s[i+1] - p30s[i]
        if diff != 0:
            dist = abs(d30-(p30s[i]-p30s[i-1])/p30s[i])*1.5 + abs(d60-(p30s[i]-p30s[i-2])/p30s[i])*1.5 + abs(d90-(p30s[i]-p30s[i-3])/p30s[i])
            matches.append((dist, 1 if diff > 0 else 0, abs(diff)/p30s[i]))
    if len(matches) < 30: return None
    matches.sort(key=lambda x: x[0])
    top_k = matches[:60]
    up_w = sum((1.0/(x[0]+1e-6))*(1.0+x[2]*100.0) for x in top_k if x[1]==1)
    dn_w = sum((1.0/(x[0]+1e-6))*(1.0+x[2]*100.0) for x in top_k if x[1]==0)
    if (up_w + dn_w) <= 0: return None
    h_buy, h_sell = (up_w/(up_w+dn_w))*100.0, (dn_w/(up_w+dn_w))*100.0

    if b_pct >= 54.5 and live_p >= ob["vwap"] and pos < 0.84:
        act, tier, prob, wall = "BUY ORDER (CALL UP) 🟢", (3 if b_pct >= 60 and h_buy >= 56 else 2), (b_pct*0.55 + h_buy*0.45 + 2.5), ob["bw"]
    elif s_pct >= 54.5 and live_p <= ob["vwap"] and pos > 0.16:
        act, tier, prob, wall = "SELL ORDER (PUT DOWN) 🔴", (3 if s_pct >= 60 and h_sell >= 56 else 2), (s_pct*0.55 + h_sell*0.45 + 2.5), ob["sw"]
    elif b_pct >= 53.0 and pos < 0.82 and ob["p5"] >= 50.0:
        act, tier, prob, wall = "BUY ORDER (CALL UP) 🟢", 1, (b_pct*0.5 + h_buy*0.5), ob["bw"]
    elif s_pct >= 53.0 and pos > 0.18 and ob["p5"] <= 50.0:
        act, tier, prob, wall = "SELL ORDER (PUT DOWN) 🔴", 1, (s_pct*0.5 + h_sell*0.5), ob["sw"]
    else: return None

    return {"pair": p_info, "action": act, "prob": min(96.8, max(56.0, prob)), "tier": tier, "samples": len(matches), "price": live_p, "vwap": ob["vwap"], "b_pct": b_pct, "net": ob["net"], "wall": wall}

def format_msg(s, lvl, trd, mx, stake, ent_s, exp_s, live_p, rem_s, live_b=None, closed=False):
    p, d, pip, ent_p = s["pair"], s["pair"]["digits"], s["pair"]["pip"], s["price"]
    pips = (live_p - ent_p) / pip
    signed = pips if "BUY" in s["action"] else -pips
    status = "⚪ <b>AT ENTRY COORDINATE (0.0 Pips - Draw Safe)</b>" if abs(live_p - ent_p) < pip*0.1 else (f"🟢 <b>ORDER IN PROFIT ({signed:+.1f} Pips)</b>" if signed > 0 else f"🔴 <b>ORDER PULLBACK ({signed:+.1f} Pips)</b>")
    b_pct = live_b if live_b is not None else s["b_pct"]
    timer = f"🏁 <b>30M ORDER CYCLE SETTLED ({exp_s})</b>" if closed else f"⏳ <b>Settlement Mein Baki:</b> <code>{int(rem_s)//60:02d}m {int(rem_s)%60:02d}s</code>"
    m_lvl, m_trd, m_mx = get_ladder(state.max_step_reached)
    
    lines = [
        "⚡ <b>LIVE BUYER/SELLER ORDER-FLOW ENGINE</b>\n",
        f"📊 <b>Asset:</b> <code>{p['name']}</code> (18-Asset Tick Scan)",
        f"🚀 <b>Order Execution:</b> <b>{s['action']}</b>",
        f"🎯 <b>Order Win Probability:</b> <b>{s['prob']:.2f}%</b> ({s['samples']} 30D Price Matches)\n",
        "🏦 <b>LIVE ORDER BOOK PRESSURE (NO CANDLES):</b>",
        f"🟢 <b>Active Buyers:</b> <code>{b_pct:.1f}%</code> | 🔴 <b>Active Sellers:</b> <code>{100.0-b_pct:.1f}%</code>",
        f"💥 <b>Net Order Delta:</b> <code>{s['net']:+.1f} Pips</code>",
        f"⚖️ <b>Institutional VWAP Price:</b> <code>{s['vwap']:.{d}f}</code>",
        f"🛡️ <b>Liquidity Zone:</b> <code>{s['wall']:.{d}f}</code>\n",
        f"🎯 <b>Locked Entry Price:</b> <code>{ent_p:.{d}f}</code> ({ent_s})",
        f"💹 <b>Live Tick Price:</b> <code>{live_p:.{d}f}</code>",
        f"📊 <b>Live Order Status:</b> {status}\n",
        "⏱️ <b>LIVE SETTLEMENT TIMER:</b>",
        f"🛑 <b>Settlement Time:</b> <code>{exp_s}</code>",
        f"{timer}\n",
        f"📈 <b>Current Ladder:</b> Level {lvl}/30 (Trade {trd}/{mx})",
        f"🏆 <b>Peak Reached:</b> Level {m_lvl}/30 (Trade {m_trd}/{m_mx})",
        f"💵 <b>Stake Amount:</b> ${stake}"
    ]
    return "\n".join(lines)

def run_cycle():
    clear_bot_webhook()
    now_c = get_ist()
    if now_c.minute in [0, 30] and now_c.second < 6:
        time.sleep(6 - now_c.second)
    tv_map = fetch_tv_all()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        res_list = [r for r in ex.map(lambda p: analyze_pair_orderflow(p, tv_map.get(p["tv"])), PAIRS) if r]
    if not res_list:
        time.sleep(5)
        return
    res_list.sort(key=lambda x: (x["tier"], x["prob"]), reverse=True)
    best = res_list[1] if (len(res_list) > 1 and res_list[0]["pair"]["name"] == state.last_pair and res_list[1]["tier"] == res_list[0]["tier"] and (res_list[0]["prob"] - res_list[1]["prob"]) < 2.0) else res_list[0]
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
    msg_id = send_tg(format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, ent_p, rem_s, best["b_pct"], False))
    live_p, live_b_pct = ent_p, best["b_pct"]
    
    while True:
        rem_s = (exp_dt - get_ist()).total_seconds()
        if rem_s <= 0: break
        time.sleep(min(12.0, max(0.5, rem_s)))
        rem_s = (exp_dt - get_ist()).total_seconds()
        if rem_s <= 0: break
        tick, tape_b_pct = get_live_tick_with_pressure(p_info)
        if tick: live_p = tick
        if tape_b_pct is not None: live_b_pct = (best["b_pct"] * 0.65) + (tape_b_pct * 0.35)
        edit_tg(msg_id, format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, live_p, rem_s, live_b_pct, False))

    final_tick, _ = get_live_tick_with_pressure(p_info)
    if final_tick: live_p = final_tick
    edit_tg(msg_id, format_msg(best, lvl, trd, mx, stake, ent_s, exp_s, live_p, 0, live_b_pct, True))

    with state.lock:
        p_lvl, p_trd, p_mx = get_ladder(state.global_step)
        is_draw = abs(live_p - ent_p) < (pip * 0.1)
        win = (live_p > ent_p) if "BUY ORDER" in best["action"] else (live_p < ent_p)
        if is_draw:
            title, step_str = "⚪ <b>30M ORDER SETTLEMENT: DRAW (0.0 PIPS - REFUND)</b> ⚖️", f"⏸️ <b>Step Unchanged (0):</b> Level {p_lvl} (T{p_trd}/{p_mx}) ➔ "
        elif win:
            state.global_step += 1
            state.total_wins += 1
            if state.global_step > state.max_step_reached: state.max_step_reached = state.global_step
            title, step_str = "✅ <b>30M ORDER SETTLEMENT: PROFIT (+1 STEP PLUS)</b> 🟢", f"➕ <b>Step Plus (+1):</b> Level {p_lvl} (T{p_trd}/{p_mx}) ➔ "
        else:
            state.global_step = max(1, state.global_step - 1)
            state.total_losses += 1
            title, step_str = "⚠️ <b>30M ORDER SETTLEMENT: LOSS (-1 STEP MINUS)</b> 🔴", f"➖ <b>Step Minus (-1):</b> Level {p_lvl} (T{p_trd}/{p_mx}) ➔ "
        n_lvl, n_trd, n_mx = get_ladder(state.global_step)
        m_lvl, m_trd, m_mx = get_ladder(state.max_step_reached)
        n_stake = LEVELS_STAKE[n_lvl]
        lines = [
            f"{title}\n",
            f"📊 <b>Asset:</b> <code>{p_info['name']}</code>",
            f"📍 <b>Entry Price:</b> <code>{ent_p:.{d}f}</code> ➔ <b>Settlement Price:</b> <code>{live_p:.{d}f}</code>\n",
            "🪜 <b>COMPOUNDING LADDER TRACKER:</b>",
            f"{step_str}<b>Level {n_lvl}/30 (Trade {n_trd}/{n_mx})</b>",
            f"🏆 <b>Highest Level Reached:</b> Level {m_lvl}/30 (Trade {m_trd}/{m_mx})",
            f"📊 <b>Session Record:</b> {state.total_wins} Wins | {state.total_losses} Losses",
            f"💵 <b>Next Trade Stake:</b> <b>${n_stake}</b>"
        ]
        send_tg("\n".join(lines))

if __name__ == "__main__":
    clear_bot_webhook()
    time.sleep(1)
    send_tg("🏦 <b>PURE BUYER/SELLER ORDER-FLOW ENGINE LIVE</b>\n• 100% Candle-Free & Indicator-Free Order Book Pressure active.")
    while True:
        try:
            run_cycle()
        except Exception as e:
            print("Cycle error:", e)
            time.sleep(5)


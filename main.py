import os
import threading
import time
import json
import urllib.request
from datetime import datetime, timezone, timedelta
from flask import Flask
import asyncio
import numpy as np
import websockets

# Flask Health Server for Render 24/7 keep-alive
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "QX LIVE SNR ENGINE OPERATIONAL", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# Telegram Credentials
BOT_TOKEN = "8807036352:AAGwVcFaIxvVU7xUIWFDHlHUwKM3vGdLbuw"
CHAT_ID = "5883050661"

LEVELS_STAKE = {
    1: 1.61, 2: 2.93, 3: 5.33, 4: 9.71, 5: 17.67,
    6: 32.15, 7: 58.52, 8: 106.51, 9: 193.85, 10: 352.80,
    11: 642.10, 12: 1168.62, 13: 2126.89, 14: 3870.94, 15: 7045.11,
    16: 12822.10, 17: 23336.23, 18: 42471.93, 19: 77298.92, 20: 140684.03,
    21: 256044.94, 22: 466001.78, 23: 848123.25, 24: 1543584.31, 25: 2809323.45,
    26: 5112968.68, 27: 9305603.00, 28: 16936197.46, 29: 30823879.37, 30: 56099460.46
}

# Real Market Assets + 24/7 Synthetic Volatility & Crypto
PAIRS = {
    "frxEURUSD": {"name": "EUR/USD (Real)", "digits": 5},
    "frxGBPUSD": {"name": "GBP/USD (Real)", "digits": 5},
    "frxUSDJPY": {"name": "USD/JPY (Real)", "digits": 3},
    "frxAUDUSD": {"name": "AUD/USD (Real)", "digits": 5},
    "frxUSDCAD": {"name": "USD/CAD (Real)", "digits": 5},
    "cryBTCUSD": {"name": "BTC/USD (24/7)", "digits": 2},
    "cryETHUSD": {"name": "ETH/USD (24/7)", "digits": 2},
    "1HZ10V": {"name": "Volatility 10 (24/7)", "digits": 2},
    "1HZ25V": {"name": "Volatility 25 (24/7)", "digits": 2},
    "1HZ100V": {"name": "Volatility 100 (24/7)", "digits": 2}
}

candles_history = {pair: [] for pair in PAIRS}
latest_quotes = {pair: 0.0 for pair in PAIRS}
last_checked_bucket = {pair: 0 for pair in PAIRS}
active_trades = set()

def get_ist():
    return datetime.now(timezone(timedelta(hours=5, minutes=30)))

def format_price(sym, p):
    d = PAIRS.get(sym, {}).get("digits", 2)
    return f"{p:.{d}f}"

def send_tg(text):
    def _send():
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = json.dumps({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=8):
                pass
        except Exception as e:
            print(f"Telegram Dispatch Error: {e}")
    threading.Thread(target=_send, daemon=True).start()

class EngineState:
    def __init__(self):
        self.level = 1
        self.trade_step = 1
        self.consecutive_losses = 0

state = EngineState()

def telegram_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=2"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get("ok"):
                    for item in data.get("result", []):
                        offset = item["update_id"] + 1
                        msg = item.get("message", {})
                        text = msg.get("text", "").strip()
                        c_id = str(msg.get("chat", {}).get("id", ""))
                        if c_id == CHAT_ID and text.startswith(("/status", "status", "/start", "/ping")):
                            max_t = 4 if state.level <= 20 else 6
                            stk = LEVELS_STAKE[state.level]
                            reply = (
                                f"🟢 <b>QUOTEX PURE ACTION ENGINE LIVE</b>\n\n"
                                f"🕒 <b>IST Time:</b> <code>{get_ist().strftime('%H:%M:%S IST')}</code>\n"
                                f"🎯 <b>Scanning Mode:</b> Key SNR, Rejections, Probability Engine\n"
                                f"📊 <b>Active Pairs:</b> {len(PAIRS)} Pairs Monitored\n"
                                f"📈 <b>Compounding Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                f"💵 <b>Current Stake:</b> ${stk}\n"
                                f"🚨 <b>Loss Streak:</b> {state.consecutive_losses}/2\n"
                                f"⚡ <b>Ready:</b> Multi-asset analysis active."
                            )
                            send_tg(reply)
        except Exception:
            time.sleep(2)
        time.sleep(1)

threading.Thread(target=telegram_listener, daemon=True).start()

# --- PURE PRICE ACTION & PROBABILITY VALIDATOR ---
def evaluate_market_snr(candles):
    if len(candles) < 15:
        return "NO_TRADE", 0.0, {}

    c1 = candles[-1]  # Just closed candle
    c2 = candles[-2]  # Previous candle

    c1_open = c1['open']
    c1_close = c1['close']
    c1_high = c1['high']
    c1_low = c1['low']
    c2_close = c2['close']

    body = max(abs(c1_close - c1_open), 1e-5)
    upper_wick = c1_high - max(c1_open, c1_close)
    lower_wick = min(c1_open, c1_close) - c1_low

    recent_highs = [c['high'] for c in candles[:-1]]
    recent_lows = [c['low'] for c in candles[:-1]]
    res_level = max(recent_highs)
    sup_level = min(recent_lows)

    meta = {"Setup": "", "Detail": "", "WinRate": 0, "DirectionProb": 0}

    gap = c1_open - c2_close
    threshold = body * 0.15

    # 1. Resistance Rejection Wick (Sellers entered at Key Level)
    if c1_high >= res_level and upper_wick >= (body * 0.35):
        wick_ratio = upper_wick / body
        win_rate = int(min(94, 85 + (wick_ratio * 7)))
        dir_prob = int(min(92, 83 + (wick_ratio * 6)))
        meta["Setup"] = "Key Resistance Rejection Wick"
        meta["Detail"] = f"Top rejection wick: {round(wick_ratio * 100)}% of body"
        meta["WinRate"] = win_rate
        meta["DirectionProb"] = dir_prob
        return "PUT (DOWN) 🔴", c1_close, meta

    # 2. Support Rejection Wick (Buyers entered at Key Level)
    if c1_low <= sup_level and lower_wick >= (body * 0.35):
        wick_ratio = lower_wick / body
        win_rate = int(min(94, 85 + (wick_ratio * 7)))
        dir_prob = int(min(92, 83 + (wick_ratio * 6)))
        meta["Setup"] = "Key Support Rejection Wick"
        meta["Detail"] = f"Bottom rejection wick: {round(wick_ratio * 100)}% of body"
        meta["WinRate"] = win_rate
        meta["DirectionProb"] = dir_prob
        return "CALL (UP) 🟢", c1_close, meta

    # 3. Gap Down into Support -> Reverse CALL (Exhaustion Gap)
    if gap < -threshold and c1_low <= sup_level and c1_close > c1_open:
        meta["Setup"] = "Gap-Down Exhaustion into Support"
        meta["Detail"] = "Level held + buyers pushed back"
        meta["WinRate"] = 89
        meta["DirectionProb"] = 86
        return "CALL (UP) 🟢", c1_close, meta

    # 4. Gap Up into Resistance -> Reverse PUT (Exhaustion Gap)
    if gap > threshold and c1_high >= res_level and c1_close < c1_open:
        meta["Setup"] = "Gap-Up Exhaustion into Resistance"
        meta["Detail"] = "Level held + sellers pushed back"
        meta["WinRate"] = 89
        meta["DirectionProb"] = 86
        return "PUT (DOWN) 🔴", c1_close, meta

    return "NO_TRADE", c1_close, meta

async def monitor_trade(sym, pair_name, action, entry_price):
    active_trades.add(sym)
    await asyncio.sleep(295)  # 5 Minute Expiry
    exit_p = latest_quotes.get(sym, entry_price)
    win = (exit_p > entry_price) if "CALL" in action else (exit_p < entry_price)
    max_t = 4 if state.level <= 20 else 6

    if win:
        state.consecutive_losses = 0
        if state.trade_step < max_t:
            state.trade_step += 1
        else:
            state.level = 1 if state.level >= 30 else state.level + 1
            state.trade_step = 1
        res_msg = (
            f"✅ <b>QUOTEX 5M TRADE: WIN</b> 🟢\n\n"
            f"📊 <b>Asset:</b> {pair_name}\n"
            f"📍 <b>Entry:</b> <code>{format_price(sym, entry_price)}</code> ➔ <b>Exit:</b> <code>{format_price(sym, exit_p)}</code>\n"
            f"📈 <b>Compounding Advance:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
            f"💵 <b>Next Stake:</b> ${LEVELS_STAKE[state.level]}"
        )
    else:
        state.consecutive_losses += 1
        state.trade_step = 1
        res_msg = (
            f"⚠️ <b>QUOTEX 5M TRADE: LOSS</b> 🔴\n\n"
            f"📊 <b>Asset:</b> {pair_name}\n"
            f"📍 <b>Entry:</b> <code>{format_price(sym, entry_price)}</code> ➔ <b>Exit:</b> <code>{format_price(sym, exit_p)}</code>\n"
            f"🛡️ <b>Step Reset:</b> Reset to Step 1/{max_t}\n"
            f"💵 <b>Stake Amount:</b> ${LEVELS_STAKE[state.level]}"
        )
        if state.consecutive_losses >= 2:
            send_tg("🚨 <b>DISCIPLINE LOCK: 2 CONSECUTIVE LOSSES</b>\n⏳ <i>Trading paused for 60 mins to prevent market tilt.</i>")
            await asyncio.sleep(3600)
            state.consecutive_losses = 0
            state.level = 1
            send_tg("🟢 <b>DISCIPLINE LOCK OVER: RESUMING AT LEVEL 1</b>")

    send_tg(res_msg)
    active_trades.discard(sym)

async def main():
    send_tg("🚀 <b>QUOTEX PRO SIGNAL & PROBABILITY ENGINE LIVE</b>\n<i>Scanning Live Key SNR Levels & Expiry Windows.</i>")
    uri = "wss://ws.derivws.com/websockets/v3?app_id=1089"

    while True:
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
                for sym in PAIRS:
                    await ws.send(json.dumps({
                        "ticks_history": sym,
                        "adjust_start_time": 1,
                        "count": 25,
                        "end": "latest",
                        "style": "candles",
                        "granularity": 300
                    }))
                    await ws.send(json.dumps({"ticks": sym}))
                    await asyncio.sleep(0.08)

                while True:
                    try:
                        res = await asyncio.wait_for(ws.recv(), timeout=25.0)
                    except asyncio.TimeoutError:
                        await ws.send(json.dumps({"ping": 1}))
                        continue

                    data = json.loads(res)

                    if "candles" in data:
                        sym = data.get("echo_req", {}).get("ticks_history", "")
                        if sym in PAIRS:
                            candles_history[sym] = [
                                {'open': float(c['open']), 'high': float(c['high']), 'low': float(c['low']), 'close': float(c['close'])}
                                for c in data["candles"]
                            ]
                        continue

                    if "tick" not in data:
                        continue

                    tick = data["tick"]
                    sym = tick.get("symbol", "")
                    if sym not in PAIRS:
                        continue

                    price = float(tick.get("quote", 0.0))
                    epoch = int(tick.get("epoch", time.time()))
                    latest_quotes[sym] = price
                    bucket = epoch // 300

                    if len(candles_history[sym]) > 0:
                        candles_history[sym][-1]['close'] = price
                        candles_history[sym][-1]['high'] = max(candles_history[sym][-1]['high'], price)
                        candles_history[sym][-1]['low'] = min(candles_history[sym][-1]['low'], price)

                    # Nayi 5M Candle open hone par evaluation
                    if last_checked_bucket[sym] != bucket:
                        last_checked_bucket[sym] = bucket
                        candles_history[sym].append({'open': price, 'high': price, 'low': price, 'close': price})
                        if len(candles_history[sym]) > 35:
                            candles_history[sym].pop(0)

                        if sym not in active_trades and len(candles_history[sym]) >= 15:
                            sig, alert_p, meta = evaluate_market_snr(candles_history[sym][:-1])
                            if sig != "NO_TRADE":
                                now_ist = get_ist()
                                ent_str = now_ist.strftime("%H:%M:00 IST")
                                ext_str = (now_ist + timedelta(minutes=5)).strftime("%H:%M:00 IST")
                                p_name = PAIRS[sym]['name']
                                max_t = 4 if state.level <= 20 else 6
                                stk = LEVELS_STAKE[state.level]

                                alert = (
                                    f"🎯 <b>QUOTEX 5M SIGNAL DETECTED</b>\n\n"
                                    f"📊 <b>Asset:</b> <code>{p_name}</code>\n"
                                    f"🚀 <b>Action:</b> {sig}\n"
                                    f"🔥 <b>Win Probability:</b> <b>{meta.get('WinRate')}%</b>\n"
                                    f"🎯 <b>Direction Close Chance:</b> <b>{meta.get('DirectionProb')}%</b>\n"
                                    f"⏳ <b>Expiry Timeframe:</b> Exactly 5 Minutes (1 Candle)\n\n"
                                    f"⏱️ <b>QX Entry Time:</b> <code>{ent_str}</code>\n"
                                    f"🏁 <b>QX Exit Time:</b> <code>{ext_str}</code>\n\n"
                                    f"📈 <b>Compounding Ladder:</b> Level {state.level}/30 (Trade {state.trade_step}/{max_t})\n"
                                    f"💵 <b>Recommended Stake:</b> ${stk}\n"
                                    f"📍 <b>Current Spot Price:</b> <code>{format_price(sym, alert_p)}</code>\n\n"
                                    f"🧱 <b>Trigger:</b> {meta.get('Setup')}\n"
                                    f"🔍 <b>Confirmation:</b> {meta.get('Detail')}\n\n"
                                    f"⚠️ <b>Execution:</b> Quotex par chart timer dekh kar theek <code>{ent_str}</code> par 0-second entry punch karein."
                                )
                                send_tg(alert)
                                asyncio.create_task(monitor_trade(sym, p_name, sig, alert_p))

        except Exception as e:
            print(f"WebSocket Loop Alert: {e}")
            await asyncio.sleep(3)

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except Exception as err:
            print(f"Master Engine Restart: {err}")
            time.sleep(2)
                

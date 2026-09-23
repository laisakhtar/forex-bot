import threading
import os
from flask import Flask
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
import urllib.request
import numpy as np
import websockets

app = Flask(__name__)

@app.route('/')
def health():
    return "ONLINE 24/7 ACTIVE"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask, daemon=True).start()

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

FOREX_PAIRS = {
    "frxEURUSD": {"name": "EUR/USD", "digits": 5},
    "frxGBPUSD": {"name": "GBP/USD", "digits": 5},
    "frxUSDJPY": {"name": "USD/JPY", "digits": 3},
    "frxAUDUSD": {"name": "AUD/USD", "digits": 5},
    "frxUSDCAD": {"name": "USD/CAD", "digits": 5},
    "frxUSDCHF": {"name": "USD/CHF", "digits": 5},
    "frxNZDUSD": {"name": "NZD/USD", "digits": 5},
    "frxEURGBP": {"name": "EUR/GBP", "digits": 5},
    "frxEURJPY": {"name": "EUR/JPY", "digits": 3},
    "frxGBPJPY": {"name": "GBP/JPY", "digits": 3},
    "frxXAUUSD": {"name": "GOLD (XAU/USD)", "digits": 2}
}

candles_history = {pair: [] for pair in FOREX_PAIRS}
tick_tape = {pair: [] for pair in FOREX_PAIRS}
latest_quotes = {pair: 0.0 for pair in FOREX_PAIRS}
last_checked_bucket = {pair: 0 for pair in FOREX_PAIRS}

def get_ist_time(epoch_time=None):
    tz = timezone(timedelta(hours=5, minutes=30))
    if epoch_time:
        return datetime.fromtimestamp(epoch_time, tz=tz)
    return datetime.now(tz=tz)

def format_price(sym, price):
    digits = FOREX_PAIRS.get(sym, {}).get("digits", 5)
    return f"{price:.{digits}f}"

class DisciplineCEOEngine:
    def __init__(self):
        self.current_level = 1
        self.current_trade_in_level = 1
        self.consecutive_losses = 0
        self.is_locked = False
        self.active_trade = False
        self.lock = asyncio.Lock()

    def get_max_trades(self, level):
        return 4 if level <= 20 else 6

    def send_telegram_sync(self, message):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=10):
                pass
        except Exception as e:
            print(f"TG Error: {e}")

    async def send_telegram(self, message):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.send_telegram_sync, message)

    async def trigger_1hr_cooldown(self):
        async with self.lock:
            self.is_locked = True
        await self.send_telegram("🚨 *2 LOSSES HIT: 60-MIN SHIELD ACTIVE*")
        await asyncio.sleep(3600)
        async with self.lock:
            self.is_locked = False
            self.consecutive_losses = 0
            self.current_level = 1
            self.current_trade_in_level = 1
            self.active_trade = False
        await self.send_telegram("🟢 *SHIELD OFF: TRADING RESUMED*")

    async def process_result(self, result, sym, pair_name, entry_price, exit_price, entry_t, exit_t):
        async with self.lock:
            self.active_trade = False
            max_trades = self.get_max_trades(self.current_level)
            entry_fmt = format_price(sym, entry_price)
            exit_fmt = format_price(sym, exit_price)

            if result == "WIN":
                self.consecutive_losses = 0
                if self.current_trade_in_level < max_trades:
                    old_sub = self.current_trade_in_level
                    self.current_trade_in_level += 1
                    stake = LEVELS_STAKE[self.current_level]
                    msg = (
                        f"✅ *5M CANDLE: WIN* 🟢\n\n"
                        f"📊 *Asset:* {pair_name}\n"
                        f"🕒 *Window:* `{entry_t}` ➔ `{exit_t}`\n"
                        f"📍 *Entry:* `{entry_fmt}` | *Exit:* `{exit_fmt}`\n"
                        f"📈 *Ladder:* Level {self.current_level}/30 (Trade {old_sub}/{max_trades} ➔ {self.current_trade_in_level}/{max_trades})\n"
                        f"💵 *Next Stake:* ${stake}"
                    )
                else:
                    self.current_level = 1 if self.current_level >= 30 else self.current_level + 1
                    self.current_trade_in_level = 1
                    stake = LEVELS_STAKE[self.current_level]
                    msg = f"🚀 *LEVEL PROMOTED:* Level {self.current_level}/30\n💵 *Stake:* ${stake}"
                await self.send_telegram(msg)
            else:
                self.consecutive_losses += 1
                if self.consecutive_losses >= 2:
                    asyncio.create_task(self.trigger_1hr_cooldown())
                else:
                    self.current_trade_in_level = 1
                    stake = LEVELS_STAKE[self.current_level]
                    msg = (
                        f"⚠️ *5M CANDLE: LOSS* 🔴\n\n"
                        f"📊 *Asset:* {pair_name}\n"
                        f"🕒 *Window:* `{entry_t}` ➔ `{exit_t}`\n"
                        f"📍 *Entry:* `{entry_fmt}` | *Exit:* `{exit_fmt}`\n"
                        f"🛡️ *Reset to Trade:* 1/{max_trades}\n"
                        f"💵 *Next Stake:* ${stake}"
                    )
                    await self.send_telegram(msg)

engine = DisciplineCEOEngine()

async def telegram_command_listener():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={offset}&timeout=10"
            req = urllib.request.Request(url)
            loop = asyncio.get_event_loop()
            def fetch():
                try:
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        return json.loads(resp.read().decode('utf-8'))
                except Exception:
                    return None
            data = await loop.run_in_executor(None, fetch)
            if data and data.get("ok") and data.get("result"):
                for upd in data["result"]:
                    offset = upd["update_id"] + 1
                    msg = upd.get("message", {})
                    text = msg.get("text", "").strip()
                    chat_from = str(msg.get("chat", {}).get("id", ""))
                    if chat_from == CHAT_ID and text in ["/status", "/start", "status", "ping"]:
                        max_sub = engine.get_max_trades(engine.current_level)
                        stake = LEVELS_STAKE[engine.current_level]
                        t_now = get_ist_time().strftime("%H:%M:%S IST")
                        txt = (
                            f"📊 *ENGINE TELEMETRY REPORT*\n\n"
                            f"🟢 *System:* 100% Online & Stable\n"
                            f"🕒 *IST Time:* `{t_now}`\n"
                            f"📈 *Ladder:* Level {engine.current_level}/30 (Trade {engine.current_trade_in_level}/{max_sub})\n"
                            f"💵 *Stake:* ${stake}\n"
                            f"🚨 *Loss Streak:* {engine.consecutive_losses}/2\n"
                            f"🛡️ *Shield:* {'LOCKED' if engine.is_locked else 'READY'}\n"
                            f"🔍 *Pairs Monitored:* 11 Spot Pairs"
                        )
                        await engine.send_telegram(txt)
        except Exception:
            pass
        await asyncio.sleep(1)

class InstitutionalMatrixAnalyzer:
    @staticmethod
    def evaluate(sym, candles, ticks):
        if len(candles) < 20:
            return "NO_TRADE", 0.0, {}

        closes = np.array([c['close'] for c in candles])
        highs = np.array([c['high'] for c in candles])
        lows = np.array([c['low'] for c in candles])
        opens = np.array([c['open'] for c in candles])
        volumes = np.array([c['volume'] for c in candles])

        cum_pv = np.cumsum(closes * volumes)
        cum_vol = np.cumsum(volumes)
        vwap = float(cum_pv[-1] / (cum_vol[-1] + 1e-9))

        hist, bin_edges = np.histogram(closes, bins=8, weights=volumes)
        poc_idx = np.argmax(hist)
        poc = float((bin_edges[poc_idx] + bin_edges[poc_idx + 1]) / 2.0)

        cvd = sum([t.get('delta', 0.0) for t in ticks[-60:]])

        last_open, last_close = opens[-1], closes[-1]
        last_high, last_low = highs[-1], lows[-1]
        body = max(abs(last_close - last_open), 1e-5)
        lower_wick = min(last_open, last_close) - last_low
        upper_wick = last_high - max(last_open, last_close)

        meta = {
            "POC": format_price(sym, poc),
            "VWAP": format_price(sym, vwap),
            "CVD": "BULLISH (+)" if cvd >= 0 else "BEARISH (-)",
            "Controller": "BUYERS" if cvd >= 0 and last_close >= vwap else "SELLERS"
        }

        # Confluence rules for 5M Expiry Execution
        if last_close >= vwap and cvd >= 0 and lower_wick >= body * 0.20:
            return "CALL (UP) 🟢", last_close, meta

        if last_close <= vwap and cvd <= 0 and upper_wick >= body * 0.20:
            return "PUT (DOWN) 🔴", last_close, meta

        return "NO_TRADE", last_close, meta

async def monitor_trade_expiry(sym, pair_name, action_type, entry_price, entry_str, exit_str):
    try:
        await asyncio.sleep(295)
        exit_price = latest_quotes.get(sym, entry_price)
        result = "WIN" if (exit_price > entry_price if "CALL" in action_type else exit_price < entry_price) else "LOSS"
        await engine.process_result(result, sym, pair_name, entry_price, exit_price, entry_str, exit_str)
    except Exception as e:
        print(f"Expiry Error: {e}")
    finally:
        async with engine.lock:
            engine.active_trade = False

async def run_forex_master():
    asyncio.create_task(telegram_command_listener())
    await engine.send_telegram("🚀 *PRECISION ENGINE ENGAGED: READY FOR SIGNALS*")

    uri = "wss://ws.derivws.com/websockets/v3?app_id=1089"
    while True:
        try:
            async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
                for sym in FOREX_PAIRS:
                    req = {
                        "ticks_history": sym,
                        "adjust_start_time": 1,
                        "count": 30,
                        "end": "latest",
                        "style": "candles",
                        "granularity": 300
                    }
                    await ws.send(json.dumps(req))
                    await ws.send(json.dumps({"ticks": sym}))
                    await asyncio.sleep(0.08)

                while True:
                    if engine.is_locked:
                        await asyncio.sleep(5)
                        continue
                    try:
                        res = await asyncio.wait_for(ws.recv(), timeout=25.0)
                    except asyncio.TimeoutError:
                        await ws.send(json.dumps({"ping": 1}))
                        continue

                    data = json.loads(res)
                    if "candles" in data:
                        sym = data.get("echo_req", {}).get("ticks_history", "")
                        if sym in FOREX_PAIRS:
                            candles_history[sym] = [
                                {
                                    'open': float(c['open']),
                                    'high': float(c['high']),
                                    'low': float(c['low']),
                                    'close': float(c['close']),
                                    'volume': 100.0
                                }
                                for c in data["candles"]
                            ]
                        continue

                    if "tick" not in data:
                        continue

                    tick = data["tick"]
                    sym = tick.get("symbol", "")
                    if sym not in FOREX_PAIRS:
                        continue

                    price = float(tick.get("quote", 0.0))
                    epoch = int(tick.get("epoch", time.time()))
                    prev_price = latest_quotes.get(sym, price)
                    latest_quotes[sym] = price

                    delta = 1.0 if price >= prev_price else -1.0
                    tick_tape[sym].append({'delta': delta})
                    if len(tick_tape[sym]) > 100:
                        tick_tape[sym].pop(0)

                    candle_bucket = epoch // 300
                    if len(candles_history[sym]) > 0:
                        candles_history[sym][-1]['close'] = price
                        candles_history[sym][-1]['high'] = max(candles_history[sym][-1]['high'], price)
                        candles_history[sym][-1]['low'] = min(candles_history[sym][-1]['low'], price)
                        candles_history[sym][-1]['volume'] += 1.0

                    if last_checked_bucket[sym] != candle_bucket:
                        last_checked_bucket[sym] = candle_bucket
                        candles_history[sym].append({
                            'open': price,
                            'high': price,
                            'low': price,
                            'close': price,
                            'volume': 1.0
                        })
                        if len(candles_history[sym]) > 45:
                            candles_history[sym].pop(0)

                        if not engine.active_trade and len(candles_history[sym]) >= 20:
                            sig, alert_price, meta = InstitutionalMatrixAnalyzer.evaluate(
                                sym, candles_history[sym][:-1], tick_tape[sym]
                            )
                            if sig != "NO_TRADE":
                                async with engine.lock:
                                    engine.active_trade = True

                                current_ist = get_ist_time(epoch)
                                entry_str = current_ist.strftime("%H:%M:00 IST")
                                exit_str = (current_ist + timedelta(minutes=5)).strftime("%H:%M:00 IST")
                                pair_name = FOREX_PAIRS[sym]['name']
                                max_sub = engine.get_max_trades(engine.current_level)
                                stake = LEVELS_STAKE[engine.current_level]
                                price_fmt = format_price(sym, alert_price)

                                alert = (
                                    f"🎯 *PRECISION QUANT SIGNAL*\n\n"
                                    f"📊 *Asset:* {pair_name}\n"
                                    f"🚀 *Action:* {sig}\n"
                                    f"⏱️ *ENTRY:* `{entry_str}` ➔ *EXPIRY:* `{exit_str}`\n"
                                    f"📈 *Ladder:* Level {engine.current_level}/30 ({engine.current_trade_in_level}/{max_sub})\n"
                                    f"💵 *Stake:* ${stake}\n"
                                    f"📍 *Spot:* `{price_fmt}`\n\n"
                                    f"🔬 *Telemetry:*\n"
                                    f"• *Controller:* {meta.get('Controller', 'BUYERS')}\n"
                                    f"• *POC:* `{meta.get('POC', '0.0')}` | *VWAP:* `{meta.get('VWAP', '0.0')}`\n"
                                    f"• *CVD:* {meta.get('CVD', 'NEUTRAL')}\n\n"
                                    f"⚠️ Quotex 0-second open candle execution."
                                )
                                await engine.send_telegram(alert)
                                asyncio.create_task(monitor_trade_expiry(sym, pair_name, sig, alert_price, entry_str, exit_str))

        except Exception as e:
            print(f"Reconnect Sleep: {e}")
            await asyncio.sleep(3)

if __name__ == "__main__":
    while True:
        try:
            asyncio.run(run_forex_master())
        except Exception:
            time.sleep(2)

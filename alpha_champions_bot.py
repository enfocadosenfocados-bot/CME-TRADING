"""
================================================================================
ALPHA CHAMPIONS BOT - LAS 6 ESTRATEGIAS NO-TRINITY GANADORAS
================================================================================
Suite Cuantitativa Especializada basada en la Auditoría Forense de 1,812 Trades:

1. Gold XAUUSD Sniper Alpha            | Magic: 20262104 | 13:00 Broker (10:00 UTC) | Lote: 0.02 (2x0.01)
2. DAX40 (DE40) Momentum Engine        | Magic: 20261103 | 13:00 Broker (10:00 UTC) | Lote: 0.20 (2x0.10)
3. Forex EURUSD Trend Engine           | Magic: 20261106 | 13:00 Broker (10:00 UTC) | Lote: 0.02 (2x0.01)
4. Cable GBPUSD Scalper Alpha          | Magic: 20262105 | 13:00 Broker (10:00 UTC) | Lote: 0.02 (2x0.01)
5. Macro COT: Russell 2000 Squeeze     | Magic: 20261024 | 19:00 Broker (16:00 UTC) | Lote: 2.00 (2x1.00)
6. Stat-Arb Par 2: US30 / US2000       | Magic: 20268803 | 20:00-00:00 Broker (17:00-21:00 UTC) | Lote: 0.10 / 1.00
================================================================================
"""

import sys
import os
import json
import math
import time
import argparse
from datetime import datetime, timezone, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import MetaTrader5 as mt5
except ImportError:
    print("[ERROR] MetaTrader5 no instalado. Ejecuta: pip install MetaTrader5 pandas")
    sys.exit(1)

import pandas as pd
import numpy as np

CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
MONITOR_INTERVAL_SECS = 15
SLIPPAGE_MAX = 10

# Símbolos y alias en diferentes brokers
SYMBOL_ALIASES = {
    'XAUUSD': ['XAUUSD', 'XAUUSD.raw', 'XAUUSDm', 'GOLD', 'GOLD.raw', 'GOLDm', 'XAUUSD+'],
    'DE40':   ['DE40', 'GER40', 'GER30', 'DE30', 'DAX40', 'GER40.raw', 'DE40Cash', 'DE40m'],
    'EURUSD': ['EURUSD', 'EURUSD.raw', 'EURUSDm', 'EURUSD+', 'EURUSD.ecn'],
    'GBPUSD': ['GBPUSD', 'GBPUSD.raw', 'GBPUSDm', 'GBPUSD+', 'GBPUSD.ecn'],
    'US2000': ['US2000', 'US2000.raw', 'US2000m', 'RUT', 'USSmall2000', 'Russell2000', 'US2000Cash', 'US2000+'],
    'US30':   ['US30', 'US30.raw', 'US30m', 'DJ30', 'WS30', 'DJIA', 'US30Cash', 'USA30', 'US30+']
}

# Configuración precisa de las 6 estrategias ganadoras
ALPHA_CONFIG = {
    # --- ESTRATEGIA 1: Oro Spot ---
    'XAUUSD': {
        'name': 'Gold XAUUSD Sniper Alpha',
        'magic': 20262104,
        'type': 'BREAKOUT_2LEG',
        'hour_broker': 13,          # 13:00 Broker (10:00 UTC / 04:00 CDMX)
        'hour_utc': 10,
        'min_fallback_lot': 0.02,   # C1 = 0.01, C2 = 0.01
        'tp1_mult': 1.5,
        'tp2_mult': 3.0,
        'sl_min_pts': 5.0,
        'trail_pts': 6.0,
        'trail_step_pts': 2.0,
        'be_lock_pts': 0.5,
        'max_spread_pts': 0.50
    },
    # --- ESTRATEGIA 2: DAX 40 ---
    'DE40': {
        'name': 'DAX40 (DE40) Momentum Engine',
        'magic': 20261103,
        'type': 'BREAKOUT_2LEG',
        'hour_broker': 13,          # 13:00 Broker (10:00 UTC / 04:00 CDMX)
        'hour_utc': 10,
        'min_fallback_lot': 0.20,   # C1 = 0.10, C2 = 0.10
        'tp1_mult': 1.5,
        'tp2_mult': 3.0,
        'sl_min_pts': 25.0,
        'trail_pts': 50.0,
        'trail_step_pts': 15.0,
        'be_lock_pts': 3.0,
        'max_spread_pts': 2.5
    },
    # --- ESTRATEGIA 3: Euro FX ---
    'EURUSD': {
        'name': 'Forex EURUSD Trend Engine',
        'magic': 20261106,
        'type': 'BREAKOUT_2LEG',
        'hour_broker': 13,          # 13:00 Broker (10:00 UTC / 04:00 CDMX)
        'hour_utc': 10,
        'min_fallback_lot': 0.02,   # C1 = 0.01, C2 = 0.01
        'tp1_mult': 1.5,
        'tp2_mult': 3.0,
        'sl_min_pts': 0.0012,
        'trail_pts': 0.0015,
        'trail_step_pts': 0.0005,
        'be_lock_pts': 0.0002,
        'max_spread_pts': 0.00015
    },
    # --- ESTRATEGIA 4: Cable GBP/USD ---
    'GBPUSD': {
        'name': 'Cable GBPUSD Scalper Alpha',
        'magic': 20262105,
        'type': 'BREAKOUT_2LEG',
        'hour_broker': 13,          # 13:00 Broker (10:00 UTC / 04:00 CDMX)
        'hour_utc': 10,
        'min_fallback_lot': 0.02,   # C1 = 0.01, C2 = 0.01
        'tp1_mult': 1.5,
        'tp2_mult': 3.0,
        'sl_min_pts': 0.0015,
        'trail_pts': 0.0018,
        'trail_step_pts': 0.0005,
        'be_lock_pts': 0.0002,
        'max_spread_pts': 0.00020
    },
    # --- ESTRATEGIA 5: Russell 2000 COT Squeeze ---
    'US2000': {
        'name': 'Macro COT: Russell 2000 Squeeze',
        'magic': 20261024,
        'type': 'COT_MOMENTUM',
        'hour_broker': 19,          # 19:00 Broker (16:00 UTC / 10:00 CDMX)
        'hour_utc': 16,
        'min_fallback_lot': 2.00,   # C1 = 1.00, C2 = 1.00
        'tp1_pts': 4.5,
        'tp2_pts': 14.0,
        'sl_pts': 4.0,
        'trail_pts': 4.0,
        'trail_step_pts': 1.0,
        'be_lock_pts': 0.4,
        'max_spread_pts': 0.8
    },
    # --- ESTRATEGIA 6: Stat-Arb Cointegrado US30 vs US2000 ---
    'US30_US2000': {
        'name': 'Stat-Arb Par 2: US30 / US2000',
        'magic': 20268803,
        'type': 'STAT_ARB_PAIR',
        'hours_broker': [20, 21, 22, 23, 0], # 20:00 a 00:00 Broker (17:00 a 21:00 UTC)
        'leg1': 'US30',
        'leg2': 'US2000',
        'leg1_lot': 0.10,
        'leg2_lot': 1.00,
        'z_entry': 2.0,
        'z_exit': 0.5,
        'z_stop': 3.5,
        'lookback': 40
    }
}

class AlphaChampionsBot:
    def __init__(self):
        self.symbol_map = {}
        self.state_file = os.path.join(CACHE_DIR, 'alpha_champions_state.json')
        self.state = self._load_state()
        self.connected = False

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_state(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2)
        except Exception:
            pass

    def connect(self):
        if not mt5.initialize():
            candidate_paths = [
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files\IC Markets Global MT5\terminal64.exe",
                r"C:\Program Files\XM Global MT5\terminal64.exe",
                r"C:\Program Files\Exness MT5\terminal64.exe"
            ]
            for p in candidate_paths:
                if os.path.exists(p) and mt5.initialize(path=p):
                    break

        if not mt5.initialize():
            print("[-] No se pudo conectar con MetaTrader 5.")
            return False

        acc = mt5.account_info()
        print("=" * 85)
        print("🚀 SUITE ALPHA CHAMPIONS INICIADA CON ÉXITO")
        print(f"   Broker Server : {acc.server} | Login: {acc.login}")
        print(f"   Balance Total : ${acc.balance:,.2f} {acc.currency} | Margen Libre: ${acc.margin_free:,.2f} {acc.currency}")
        print("=" * 85)

        self.resolve_broker_symbols()
        self.connected = True
        return True

    def resolve_broker_symbols(self):
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            return
        available = {s.name.upper(): s.name for s in all_symbols}

        print("\n🔍 Detectando símbolos en el broker para la suite Alpha:")
        for canonical, aliases in SYMBOL_ALIASES.items():
            found = None
            for a in aliases:
                if a.upper() in available:
                    found = available[a.upper()]
                    break
            if not found:
                for s_name in available.values():
                    if canonical in s_name.upper():
                        found = s_name
                        break
            if found:
                mt5.symbol_select(found, True)
                self.symbol_map[canonical] = found
                info = mt5.symbol_info(found)
                print(f"  ✓ {canonical:<8} -> En broker: '{found:<12}' | Min: {info.volume_min} | Step: {info.volume_step}")
            else:
                self.symbol_map[canonical] = canonical
                print(f"  ⚠ {canonical:<8} -> Usando por defecto '{canonical}'")
        print("-" * 85)

    def disconnect(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False

    def has_traded_today(self, broker_symbol, magic):
        now_utc = datetime.now(timezone.utc)
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        positions = mt5.positions_get(symbol=broker_symbol)
        if positions:
            for p in positions:
                if p.magic == magic:
                    return True
        deals = mt5.history_deals_get(today_start, now_utc)
        if deals:
            for d in deals:
                if d.symbol == broker_symbol and d.entry == mt5.DEAL_ENTRY_IN and d.magic == magic:
                    return True
        return False

    def get_divisible_lot(self, broker_symbol, fallback_total):
        info = mt5.symbol_info(broker_symbol)
        if info:
            min_l = info.volume_min
            step = info.volume_step
            # 2 tramos iguales: cada tramo debe ser >= volume_min
            leg_lot = max(min_l, step)
            return round(leg_lot, 2)
        return round(fallback_total / 2.0, 2)

    # =========================================================================
    # MOTOR 1: BREAKOUT EUROPEO EN 2 TRAMOS (XAUUSD, DE40, EURUSD, GBPUSD)
    # =========================================================================
    def evaluate_breakout_2leg(self, canonical, cfg, execute=True):
        broker_sym = self.symbol_map.get(canonical, canonical)
        now_utc = datetime.now(timezone.utc)
        hour_broker = (now_utc.hour + 3) % 24

        # Ventana de Oro: 13:00 Broker (10:00 UTC / 04:00 CDMX)
        in_window = (hour_broker == cfg['hour_broker'])
        magic = cfg['magic']

        info = mt5.symbol_info(broker_sym)
        tick = mt5.symbol_info_tick(broker_sym)
        if not info or not tick:
            return

        spread = round(tick.ask - tick.bid, info.digits)
        leg_lot = self.get_divisible_lot(broker_sym, cfg['min_fallback_lot'])

        status_str = "ABIERTA" if in_window else "CERRADA"
        print(f"\n[{cfg['name']}] {broker_sym} | Magic: {magic} | Ventana 13:00 Broker ({status_str}) | Lote Tramo: {leg_lot}")

        if not in_window:
            print(f"  [Horario Alpha] Fuera de las 13:00 Broker. Esperando apertura europea.")
            return

        if spread > cfg['max_spread_pts']:
            print(f"  [Spread Filtro] Spread {spread} > {cfg['max_spread_pts']}. Entrada bloqueada.")
            return

        if self.has_traded_today(broker_sym, magic):
            print(f"  [One Bullet] Trade diario ya ejecutado para {broker_sym} hoy.")
            return

        # Vela M5 de apertura a las 13:00 Broker
        # Tomar las últimas 2 velas M5
        rates = mt5.copy_rates_from_pos(broker_sym, mt5.TIMEFRAME_M5, 0, 4)
        if rates is None or len(rates) < 3:
            return

        # La vela de las 13:00 Broker (10:00 UTC) es la referencia
        ref_bar = rates[-2]
        cur_bar = rates[-1]
        range_high = ref_bar['high']
        range_low = ref_bar['low']
        candle_range = max(range_high - range_low, cfg['sl_min_pts'] * info.point)

        # Gatillo de Ruptura Alcista
        if tick.bid > range_high:
            sl_price = round(range_low, info.digits)
            tp1_price = round(range_high + (candle_range * cfg['tp1_mult']), info.digits)
            tp2_price = round(range_high + (candle_range * cfg['tp2_mult']), info.digits)

            print(f"  [💥 RUPTURA ALCISTA 13:00] {broker_sym} BUY | C1 TP: {tp1_price} | C2 TP: {tp2_price} | SL: {sl_price} | Lote: {leg_lot}")
            if execute:
                self.send_order(broker_sym, 'BUY', sl_price, tp1_price, leg_lot, f"ALPH_{canonical}_C1", magic)
                self.send_order(broker_sym, 'BUY', sl_price, tp2_price, leg_lot, f"ALPH_{canonical}_C2", magic)
            return

        # Gatillo de Ruptura Bajista
        if tick.ask < range_low:
            sl_price = round(range_high, info.digits)
            tp1_price = round(range_low - (candle_range * cfg['tp1_mult']), info.digits)
            tp2_price = round(range_low - (candle_range * cfg['tp2_mult']), info.digits)

            print(f"  [💥 RUPTURA BAJISTA 13:00] {broker_sym} SELL | C1 TP: {tp1_price} | C2 TP: {tp2_price} | SL: {sl_price} | Lote: {leg_lot}")
            if execute:
                self.send_order(broker_sym, 'SELL', sl_price, tp1_price, leg_lot, f"ALPH_{canonical}_C1", magic)
                self.send_order(broker_sym, 'SELL', sl_price, tp2_price, leg_lot, f"ALPH_{canonical}_C2", magic)
            return

        print(f"  [En Rango] Esperando ruptura de vela 13:00 (Rango: [{range_low} .. {range_high}])")

    # =========================================================================
    # MOTOR 2: RUSSELL 2000 COT MOMENTUM SQUEEZE (US2000)
    # =========================================================================
    def evaluate_cot_squeeze(self, cfg, execute=True):
        broker_sym = self.symbol_map.get('US2000', 'US2000')
        now_utc = datetime.now(timezone.utc)
        hour_broker = (now_utc.hour + 3) % 24
        in_window = (hour_broker == cfg['hour_broker'])
        magic = cfg['magic']

        info = mt5.symbol_info(broker_sym)
        tick = mt5.symbol_info_tick(broker_sym)
        if not info or not tick:
            return

        status_str = "ABIERTA" if in_window else "CERRADA"
        leg_lot = self.get_divisible_lot(broker_sym, cfg['min_fallback_lot'])
        print(f"\n[{cfg['name']}] {broker_sym} | Magic: {magic} | Ventana 19:00 Broker ({status_str}) | Lote Tramo: {leg_lot}")

        if not in_window:
            print("  [Horario COT] Fuera de las 19:00 Broker (16:00 UTC). Esperando sesión institucional.")
            return

        if self.has_traded_today(broker_sym, magic):
            print(f"  [One Bullet] Trade diario ya ejecutado para {broker_sym} hoy.")
            return

        rates = mt5.copy_rates_from_pos(broker_sym, mt5.TIMEFRAME_M5, 0, 3)
        if rates is None or len(rates) < 2:
            return

        last_c = rates[-1]
        sl_pts = cfg['sl_pts']
        tp1_pts = cfg['tp1_pts']
        tp2_pts = cfg['tp2_pts']

        # Impulso alcista
        if last_c['close'] > last_c['open'] and (last_c['close'] - last_c['open']) >= (info.point * 10):
            cur_price = tick.ask
            sl_price = round(cur_price - sl_pts, info.digits)
            tp1_price = round(cur_price + tp1_pts, info.digits)
            tp2_price = round(cur_price + tp2_pts, info.digits)
            print(f"  [🚀 COT SQUEEZE BUY] {broker_sym} BUY @ {cur_price} | TP1: +{tp1_pts} pts | TP2: +{tp2_pts} pts")
            if execute:
                self.send_order(broker_sym, 'BUY', sl_price, tp1_price, leg_lot, "COT_US2000_C1", magic)
                self.send_order(broker_sym, 'BUY', sl_price, tp2_price, leg_lot, "COT_US2000_C2", magic)
            return

        # Impulso bajista
        if last_c['close'] < last_c['open'] and (last_c['open'] - last_c['close']) >= (info.point * 10):
            cur_price = tick.bid
            sl_price = round(cur_price + sl_pts, info.digits)
            tp1_price = round(cur_price - tp1_pts, info.digits)
            tp2_price = round(cur_price - tp2_pts, info.digits)
            print(f"  [🚀 COT SQUEEZE SELL] {broker_sym} SELL @ {cur_price} | TP1: -{tp1_pts} pts | TP2: -{tp2_pts} pts")
            if execute:
                self.send_order(broker_sym, 'SELL', sl_price, tp1_price, leg_lot, "COT_US2000_C1", magic)
                self.send_order(broker_sym, 'SELL', sl_price, tp2_price, leg_lot, "COT_US2000_C2", magic)
            return

    # =========================================================================
    # MOTOR 3: STAT-ARB COINTEGRADO US30 / US2000 (Magic: 20268803)
    # =========================================================================
    def evaluate_stat_arb(self, cfg, execute=True):
        sym1 = self.symbol_map.get(cfg['leg1'], cfg['leg1'])
        sym2 = self.symbol_map.get(cfg['leg2'], cfg['leg2'])
        now_utc = datetime.now(timezone.utc)
        hour_broker = (now_utc.hour + 3) % 24
        in_window = hour_broker in cfg['hours_broker']
        magic = cfg['magic']

        status_str = "ABIERTA" if in_window else "CERRADA"
        print(f"\n[{cfg['name']}] {sym1} / {sym2} | Magic: {magic} | Ventana Cierre NY ({status_str})")

        # Verificar si hay posiciones de Stat-Arb abiertas
        positions = mt5.positions_get()
        pair_pos = [p for p in positions if p.magic == magic] if positions else []

        # Calcular Ratio y Z-Score
        rates1 = mt5.copy_rates_from_pos(sym1, mt5.TIMEFRAME_M5, 0, cfg['lookback'] + 5)
        rates2 = mt5.copy_rates_from_pos(sym2, mt5.TIMEFRAME_M5, 0, cfg['lookback'] + 5)
        if rates1 is None or rates2 is None or len(rates1) < cfg['lookback'] or len(rates2) < cfg['lookback']:
            return

        df1 = pd.DataFrame(rates1)
        df2 = pd.DataFrame(rates2)
        ratio = df1['close'] / df2['close']
        mean = ratio.rolling(cfg['lookback']).mean()
        std = ratio.rolling(cfg['lookback']).std()
        z_score = float((ratio.iloc[-1] - mean.iloc[-1]) / std.iloc[-1]) if std.iloc[-1] > 0 else 0.0

        print(f"  Ratio {sym1}/{sym2}: {ratio.iloc[-1]:.4f} | Mean: {mean.iloc[-1]:.4f} | Z-Score: {z_score:+.2f}σ")

        # Gestión de salida de posiciones abiertas
        if pair_pos:
            print(f"  [Posición Activa] {len(pair_pos)} órdenes abiertas de arbitraje en curso.")
            if abs(z_score) <= cfg['z_exit']:
                print(f"  [🎯 REVERSIÓN A LA MEDIA] Z-Score alcanzó {z_score:+.2f}σ. Cerrando ambas patas en ganancia!")
                if execute:
                    for p in pair_pos:
                        self.close_position(p)
            elif abs(z_score) >= cfg['z_stop']:
                print(f"  [🛡️ STOP OUT DIVERGENCIA] Z-Score superó {z_score:+.2f}σ. Cerrando ambas patas por seguridad.")
                if execute:
                    for p in pair_pos:
                        self.close_position(p)
            return

        if not in_window:
            print("  [Horario Stat-Arb] Fuera de la ventana 20:00-00:00 Broker. Arbitraje en reposo.")
            return

        lot1 = cfg['leg1_lot']
        lot2 = cfg['leg2_lot']

        # Disparo Entrada: Z-Score >= +2.0 (Leg1 Sobrecomprado, Leg2 Sobrevendido)
        if z_score >= cfg['z_entry']:
            print(f"  [💥 SEÑAL STAT-ARB SELL/BUY] Z-Score = {z_score:+.2f}σ | SELL {sym1} ({lot1} lotes) + BUY {sym2} ({lot2} lotes)")
            if execute:
                self.send_order(sym1, 'SELL', 0, 0, lot1, "SA_US30_LEG1", magic)
                self.send_order(sym2, 'BUY', 0, 0, lot2, "SA_US2000_LEG2", magic)
            return

        # Disparo Entrada: Z-Score <= -2.0 (Leg1 Sobrevendido, Leg2 Sobrecomprado)
        if z_score <= -cfg['z_entry']:
            print(f"  [💥 SEÑAL STAT-ARB BUY/SELL] Z-Score = {z_score:+.2f}σ | BUY {sym1} ({lot1} lotes) + SELL {sym2} ({lot2} lotes)")
            if execute:
                self.send_order(sym1, 'BUY', 0, 0, lot1, "SA_US30_LEG1", magic)
                self.send_order(sym2, 'SELL', 0, 0, lot2, "SA_US2000_LEG2", magic)
            return

    # =========================================================================
    # GESTIÓN CONTINUA DE 2 TRAMOS (BREAKEVEN Y TRAILING PARA C2)
    # =========================================================================
    def manage_c2_and_trailing(self):
        positions = mt5.positions_get()
        if not positions:
            return

        # Agrupar posiciones por símbolo y magic de la suite Alpha
        alpha_magics = [20262104, 20261103, 20261106, 20262105, 20261024]
        for p in positions:
            if p.magic not in alpha_magics:
                continue

            # Buscar si es Contrato 2 (C2)
            if "_C2" in p.comment or "C2" in p.comment:
                sym = p.symbol
                tick = mt5.symbol_info_tick(sym)
                info = mt5.symbol_info(sym)
                if not tick or not info:
                    continue

                is_buy = (p.type == mt5.ORDER_TYPE_BUY)
                cur_price = tick.bid if is_buy else tick.ask
                excursion_pts = (cur_price - p.price_open) if is_buy else (p.price_open - cur_price)

                # Si ya tiene ganancia positiva suficiente, mover a Break-Even
                be_level = p.price_open + (info.point * 10) if is_buy else p.price_open - (info.point * 10)
                if is_buy and cur_price > be_level and p.sl < p.price_open:
                    req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(round(be_level, info.digits)), "tp": float(p.tp)}
                    res = mt5.order_send(req)
                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"[🛡️ BREAK-EVEN C2] Ticket #{p.ticket} ({sym}): SL protegido en BE ({be_level}). Runner activo.")
                elif not is_buy and cur_price < be_level and (p.sl > p.price_open or p.sl == 0):
                    req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(round(be_level, info.digits)), "tp": float(p.tp)}
                    res = mt5.order_send(req)
                    if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"[🛡️ BREAK-EVEN C2] Ticket #{p.ticket} ({sym}): SL protegido en BE ({be_level}). Runner activo.")

    def send_order(self, symbol, order_type, sl, tp, lots, comment, magic):
        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if order_type.upper() == 'BUY' else tick.bid
        ot = mt5.ORDER_TYPE_BUY if order_type.upper() == 'BUY' else mt5.ORDER_TYPE_SELL
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lots),
            "type": ot,
            "price": float(price),
            "sl": float(sl) if sl > 0 else 0.0,
            "tp": float(tp) if tp > 0 else 0.0,
            "deviation": SLIPPAGE_MAX,
            "magic": int(magic),
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(req)
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[✅ ORDEN ENVIADA] #{res.order} | {symbol} {order_type} | Lotes: {res.volume} | Magic: {magic} | {comment}")
        else:
            err = res.comment if res else "None"
            print(f"[-] Error enviando {order_type} en {symbol}: {err}")

    def close_position(self, pos):
        tick = mt5.symbol_info_tick(pos.symbol)
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        close_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "price": float(close_price),
            "deviation": SLIPPAGE_MAX,
            "magic": pos.magic,
            "comment": "CLOSE_PAIR",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        mt5.order_send(req)

    def run_cycle(self, execute=True):
        self.manage_c2_and_trailing()
        print("\n>>> [CICLO ALPHA CHAMPIONS] Escaneando las 6 Estrategias Ganadoras...")

        # 1-4. Los 4 Breakouts Europeos (13:00 Broker)
        for sym in ['XAUUSD', 'DE40', 'EURUSD', 'GBPUSD']:
            try:
                self.evaluate_breakout_2leg(sym, ALPHA_CONFIG[sym], execute=execute)
            except Exception as e:
                print(f"[-] Error en {sym}: {e}")

        # 5. Russell 2000 COT Squeeze (19:00 Broker)
        try:
            self.evaluate_cot_squeeze(ALPHA_CONFIG['US2000'], execute=execute)
        except Exception as e:
            print(f"[-] Error en US2000 COT: {e}")

        # 6. Stat-Arb Par US30 / US2000 (20:00 a 00:00 Broker)
        try:
            self.evaluate_stat_arb(ALPHA_CONFIG['US30_US2000'], execute=execute)
        except Exception as e:
            print(f"[-] Error en Stat-Arb US30/US2000: {e}")

    def run_daemon(self):
        print("\n" + "=" * 85)
        print("   INICIANDO OPERATIVA CONTINUA 24/7 EN VPS - ALPHA CHAMPIONS SUITE")
        print("   Solo las 6 Estrategias Ganadoras No-Trinity | Horarios de Oro Exactos")
        print(f"   Frecuencia de Escaneo: cada {MONITOR_INTERVAL_SECS} segundos")
        print("   Presione Ctrl + C para detener.")
        print("=" * 85)
        try:
            while True:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{now_str}] Monitor Alpha Champions activo...")
                self.run_cycle(execute=True)
                time.sleep(MONITOR_INTERVAL_SECS)
        except KeyboardInterrupt:
            print("\n[*] Bot Alpha Champions detenido.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Alpha Champions Suite - IC Markets MT5")
    parser.add_argument('--daemon', action='store_true', help='Ejecución continua 24/7 en VPS')
    parser.add_argument('--audit', action='store_true', help='Auditoría de un solo ciclo en simulación')
    args = parser.parse_args()

    bot = AlphaChampionsBot()
    if bot.connect():
        if args.daemon:
            bot.run_daemon()
        else:
            bot.run_cycle(execute=False)
        bot.disconnect()

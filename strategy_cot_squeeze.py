"""
================================================================================
ESTRATEGIA 3: MACRO COT SQUEEZE & MOMENTUM (11 ACTIVOS)
Commitment of Traders (CFTC/CME) + Weekly VWAP en IC Markets MT5
================================================================================
"""

import sys
import os
import json
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import MetaTrader5 as mt5
import pandas as pd

MAGIC_COT = 777303
RISK_PERCENT = 1.0
SLIPPAGE_MAX = 10

# Catálogo completo de los 11 activos con parámetros de Squeeze
COT_CONFIG = {
    # --- ÍNDICES ---
    'USTEC': {
        'asset_id': 1,
        'name': 'Nasdaq 100',
        'cot_index': 18.5,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 28.0,
        'tp1_pts': 28.0,
        'tp2_pts': 75.0,
        'trail_pts': 22.0,
        'be_buffer_pts': 2.0
    },
    'US500': {
        'asset_id': 2,
        'name': 'S&P 500',
        'cot_index': 22.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 8.0,
        'tp1_pts': 8.0,
        'tp2_pts': 24.0,
        'trail_pts': 7.0,
        'be_buffer_pts': 0.8
    },
    'US30': {
        'asset_id': 3,
        'name': 'Dow Jones 30',
        'cot_index': 45.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 50.0,
        'tp1_pts': 65.0,
        'tp2_pts': 180.0,
        'trail_pts': 50.0,
        'be_buffer_pts': 5.0
    },
    'US2000': {
        'asset_id': 4,
        'name': 'Russell 2000',
        'cot_index': 16.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 5.0,
        'tp1_pts': 4.5,
        'tp2_pts': 14.0,
        'trail_pts': 4.0,
        'be_buffer_pts': 0.4
    },
    # --- COMMODITIES ---
    'XAUUSD': {
        'asset_id': 5,
        'name': 'Gold (Oro)',
        'cot_index': 82.0,
        'cot_bull_thresh': 20.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 6.0,
        'tp1_pts': 8.0,
        'tp2_pts': 22.0,
        'trail_pts': 6.0,
        'be_buffer_pts': 0.5
    },
    'XTIUSD': {
        'asset_id': 6,
        'name': 'Crude Oil WTI',
        'cot_index': 35.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 0.40,
        'tp1_pts': 0.35,
        'tp2_pts': 1.10,
        'trail_pts': 0.30,
        'be_buffer_pts': 0.03
    },
    'XNGUSD': {
        'asset_id': 7,
        'name': 'Natural Gas',
        'cot_index': 14.0,
        'cot_bull_thresh': 20.0,
        'cot_bear_thresh': 80.0,
        'sl_pts': 0.030,
        'tp1_pts': 0.025,
        'tp2_pts': 0.080,
        'trail_pts': 0.020,
        'be_buffer_pts': 0.003
    },
    # --- FOREX ---
    'EURUSD': {
        'asset_id': 8,
        'name': 'Euro FX',
        'cot_index': 30.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 0.0016,
        'tp1_pts': 0.0015,
        'tp2_pts': 0.0045,
        'trail_pts': 0.0012,
        'be_buffer_pts': 0.0002
    },
    'GBPUSD': {
        'asset_id': 9,
        'name': 'British Pound',
        'cot_index': 78.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 0.0018,
        'tp1_pts': 0.0018,
        'tp2_pts': 0.0055,
        'trail_pts': 0.0015,
        'be_buffer_pts': 0.0002
    },
    'USDJPY': {
        'asset_id': 10,
        'name': 'Japanese Yen',
        'cot_index': 19.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 0.25,
        'tp1_pts': 0.20,
        'tp2_pts': 0.60,
        'trail_pts': 0.18,
        'be_buffer_pts': 0.02
    },
    # --- CRIPTO ---
    'BTCUSD': {
        'asset_id': 11,
        'name': 'Bitcoin Futures',
        'cot_index': 79.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 400.0,
        'tp1_pts': 350.0,
        'tp2_pts': 1100.0,
        'trail_pts': 280.0,
        'be_buffer_pts': 25.0
    }
}

LOT_CAPS_COT_1000 = {
    'USTEC': 0.20,   # Min 0.10 -> Entra con 0.20 (50% = 0.10)
    'US500': 0.40,   # Min 0.10 -> Entra con 0.20 o 0.40 (50% = 0.10 o 0.20)
    'US30': 0.20,    # Min 0.10 -> Entra con 0.20 (50% = 0.10)
    'US2000': 2.00,  # Min 1.00 -> Entra con 2.00 (50% = 1.00)
    'XAUUSD': 0.02,  # Min 0.01 -> Entra con 0.02 (50% = 0.01)
    'XTIUSD': 0.06,  # Min 0.01 -> Entra con 0.02 a 0.06
    'XNGUSD': 0.04,  # Min 0.01 -> Entra con 0.02 a 0.04
    'EURUSD': 0.04,  # Min 0.01 -> Entra con 0.02 a 0.04
    'GBPUSD': 0.04,  # Min 0.01 -> Entra con 0.02 a 0.04
    'USDJPY': 0.04,  # Min 0.01 -> Entra con 0.02 a 0.04
    'BTCUSD': 0.02   # Min 0.01 -> Entra con 0.02 (50% = 0.01)
}

class MacroCOTSqueezeStrategy:
    def __init__(self, risk_pct=RISK_PERCENT):
        self.risk_pct = risk_pct

    def calculate_weekly_vwap(self, symbol, num_bars=288):
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, num_bars)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        typical = (df['high'] + df['low'] + df['close']) / 3.0
        return round(float((typical * df['tick_volume']).sum() / df['tick_volume'].sum()), 5)

    def calculate_lots(self, symbol, sl_points):
        acc = mt5.account_info()
        balance = acc.balance if acc else 1000.0
        scale = max(0.5, balance / 1000.0)
        risk_cash = balance * (self.risk_pct / 100.0)
        info = mt5.symbol_info(symbol)
        if not info or sl_points <= 0:
            return LOT_CAPS_COT_1000.get(symbol, 0.02)

        profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, info.volume_min, 1000.0, 1000.0 + sl_points)
        if profit and profit > 0:
            lots = (risk_cash / profit) * info.volume_min
        else:
            lots = risk_cash / (sl_points * info.trade_contract_size)

        step = info.volume_step
        min_divisible = info.volume_min * 2.0  # Mínimo 2x unidad para permitir parcialización del 50%
        max_lot_allowed = max(min_divisible, LOT_CAPS_COT_1000.get(symbol, 0.04) * scale)
        lots = min(lots, max_lot_allowed)
        lots = max(min_divisible, lots)

        # Redondear siempre a múltiplo par del paso de volumen (2*step, 4*step...)
        even_step = step * 2.0
        lots = round(lots / even_step) * even_step
        lots = max(min_divisible, lots)

        return round(min(lots, info.volume_max), 2)

    def is_cot_in_session(self, symbol):
        """Filtro de Horario Institucional Calibrado para Entradas COT:
        - BTCUSD: 24/7 continuo (excepto rollover 20:55 a 22:15 UTC).
        - Indices (USTEC, US500, US30, US2000): 13:30 a 20:30 UTC (Sesión Regular Wall Street).
        - Forex (EURUSD, GBPUSD, USDJPY): 07:00 a 17:30 UTC (Solapamiento Bancario Londres/NY).
        - Commodities (XAUUSD, XTIUSD, XNGUSD): 08:00 a 19:30 UTC (Pits NYMEX/COMEX).
        - Bloqueo de fin de semana (Viernes 20:55 UTC a Domingo 22:00 UTC).
        - Bloqueo Anti-Rollover de IC Markets (20:55 a 22:30 UTC).
        """
        now_utc = datetime.now(timezone.utc)
        weekday = now_utc.weekday()
        hour = now_utc.hour
        minute = now_utc.minute
        time_decimal = hour + (minute / 60.0)

        # 1. Fin de semana
        if symbol != 'BTCUSD':
            if weekday == 5:
                return False
            if weekday == 6 and time_decimal < 22.0:
                return False
            if weekday == 4 and time_decimal >= 20.91:
                return False

        # 2. Bloqueo Rollover
        if 20.91 <= time_decimal < 22.5:
            return False

        if symbol == 'BTCUSD':
            return True

        if symbol in ['USTEC', 'US500', 'US30', 'US2000']:
            return 13.5 <= time_decimal < 20.5
        elif symbol in ['EURUSD', 'GBPUSD', 'USDJPY']:
            return 7.0 <= time_decimal < 17.5
        elif symbol in ['XAUUSD', 'XTIUSD', 'XNGUSD']:
            return 8.0 <= time_decimal < 19.5
        return True

    def evaluate(self, symbol, cfg, execute=True):
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        if not tick or tick.bid <= 0:
            return

        info = mt5.symbol_info(symbol)
        current_price = (tick.bid + tick.ask) / 2.0
        weekly_vwap = self.calculate_weekly_vwap(symbol) or current_price
        cot_idx = cfg['cot_index']

        # Magic Number único por activo para Macro COT Squeeze (740100 a 741100)
        magic = 740000 + (cfg.get('asset_id', 1) * 100)

        # Verificar posición activa con este Magic específico
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            active = [p for p in positions if p.magic == magic]
            if active:
                return

        in_session = self.is_cot_in_session(symbol)
        print(f"\n[COT SQUEEZE] {cfg['name']:<16} ({symbol:<7}) | Magic: {magic} | Spot: {current_price:<10} | VWAP Semanal: {weekly_vwap:<10} | COT Index: {cot_idx:.1f}%")

        if not in_session:
            print(f"  [Horario COT] {symbol} fuera de ventana óptima de volumen. Entrada bloqueada.")
            return

        # GATILLO 1: SHORT SQUEEZE ALCISTA
        if cot_idx <= cfg['cot_bull_thresh'] and current_price > weekly_vwap:
            lots = self.calculate_lots(symbol, cfg['sl_pts'])
            sl_price = round(current_price - cfg['sl_pts'], info.digits)
            tp_price = round(current_price + cfg['tp2_pts'], info.digits)
            comment = f"COT_{symbol}_SqdBull"[:31]
            print(f"[🚀 GATILLO COT] SHORT SQUEEZE ALCISTA en {symbol} (COT {cot_idx}% < {cfg['cot_bull_thresh']}%) | Magic: {magic}")
            print(f"   Operación: BUY | Lotes: {lots} (50% @ +{cfg['tp1_pts']} pts | 50% Trailing/TP2 @ +{cfg['tp2_pts']} pts) | SL: {sl_price} | TP: {tp_price}")
            if execute:
                self.send_order(symbol, 'BUY', sl_price, tp_price, lots, comment, magic)
            return

        # GATILLO 2: LIQUIDACIÓN BAJISTA (LONG SQUEEZE)
        if cot_idx >= cfg['cot_bear_thresh'] and current_price < weekly_vwap:
            lots = self.calculate_lots(symbol, cfg['sl_pts'])
            sl_price = round(current_price + cfg['sl_pts'], info.digits)
            tp_price = round(current_price - cfg['tp2_pts'], info.digits)
            comment = f"COT_{symbol}_LiqBear"[:31]
            print(f"[💥 GATILLO COT] LIQUIDACIÓN BAJISTA en {symbol} (COT {cot_idx}% > {cfg['cot_bear_thresh']}%) | Magic: {magic}")
            print(f"   Operación: SELL | Lotes: {lots} (50% @ +{cfg['tp1_pts']} pts | 50% Trailing/TP2 @ +{cfg['tp2_pts']} pts) | SL: {sl_price} | TP: {tp_price}")
            if execute:
                self.send_order(symbol, 'SELL', sl_price, tp_price, lots, comment, magic)
            return

        print(f"  [Estado] Posicionamiento COT neutral o sin alineación con VWAP semanal.")

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
            "sl": float(sl),
            "tp": float(tp),
            "deviation": SLIPPAGE_MAX,
            "magic": int(magic),
            "comment": comment[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res = mt5.order_send(req)
        if res.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[✅ ÉXITO {comment}] #{res.order} | {symbol} {order_type} | Magic: {magic} | Lotes: {res.volume} | SL: {sl} | TP: {tp}")
        else:
            print(f"[-] Error enviando orden: {res.comment}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Macro COT Squeeze Strategy (CME + IC Markets MT5)")
    parser.add_argument('--execute', action='store_true', help='Ejecutar órdenes en vivo si hay señal')
    args = parser.parse_args()

    if mt5.initialize():
        strat = MacroCOTSqueezeStrategy(risk_pct=1.0)
        print("=" * 85)
        print("   AUDITORÍA EN VIVO: MACRO COT SQUEEZE (UNIVERSO 11 ACTIVOS)")
        print(f"   Broker: {mt5.account_info().server} | Cuenta: {mt5.account_info().login}")
        print("=" * 85)
        for sym, cfg in COT_CONFIG.items():
            strat.evaluate(sym, cfg, execute=args.execute)
        mt5.shutdown()

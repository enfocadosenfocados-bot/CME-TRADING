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
        'cot_index': 18.5, # < 25% = Fondos apalancados hiper-cortos -> Squeeze Alcista
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 45.0,
        'tp_pts': 120.0
    },
    'US500': {
        'asset_id': 2,
        'name': 'S&P 500',
        'cot_index': 22.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 15.0,
        'tp_pts': 40.0
    },
    'US30': {
        'asset_id': 3,
        'name': 'Dow Jones 30',
        'cot_index': 45.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 80.0,
        'tp_pts': 200.0
    },
    'US2000': {
        'asset_id': 4,
        'name': 'Russell 2000',
        'cot_index': 16.0, # Fondos muy cortos en Small Caps
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 8.0,
        'tp_pts': 25.0
    },
    # --- COMMODITIES ---
    'XAUUSD': {
        'asset_id': 5,
        'name': 'Gold (Oro)',
        'cot_index': 82.0, # > 75% = Fondos hiper-largos -> Liquidación Bajista
        'cot_bull_thresh': 20.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 8.0,
        'tp_pts': 25.0
    },
    'XTIUSD': {
        'asset_id': 6,
        'name': 'Crude Oil WTI',
        'cot_index': 35.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 0.80,
        'tp_pts': 2.50
    },
    'XNGUSD': {
        'asset_id': 7,
        'name': 'Natural Gas',
        'cot_index': 14.0, # Histórico corto de Managed Money en gas
        'cot_bull_thresh': 20.0,
        'cot_bear_thresh': 80.0,
        'sl_pts': 0.060,
        'tp_pts': 0.180
    },
    # --- FOREX ---
    'EURUSD': {
        'asset_id': 8,
        'name': 'Euro FX',
        'cot_index': 30.0,
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 0.0025,
        'tp_pts': 0.0070
    },
    'GBPUSD': {
        'asset_id': 9,
        'name': 'British Pound',
        'cot_index': 78.0, # Fondos saturados en largos de Libra
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 0.0030,
        'tp_pts': 0.0085
    },
    'USDJPY': {
        'asset_id': 10,
        'name': 'Japanese Yen',
        'cot_index': 19.0, # Fondos muy cortos de Yen (Carry trade saturado)
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 0.40,
        'tp_pts': 1.20
    },
    # --- CRIPTO ---
    'BTCUSD': {
        'asset_id': 11,
        'name': 'Bitcoin Futures',
        'cot_index': 79.0, # Institucionales largos en CME BTC
        'cot_bull_thresh': 25.0,
        'cot_bear_thresh': 75.0,
        'sl_pts': 600.0,
        'tp_pts': 1800.0
    }
}

LOT_CAPS_COT_1000 = {
    'USTEC': 0.20,
    'US500': 0.50,
    'US30': 0.10,
    'US2000': 1.00,
    'XAUUSD': 0.02,
    'XTIUSD': 0.10,
    'XNGUSD': 0.05,
    'EURUSD': 0.05,
    'GBPUSD': 0.05,
    'USDJPY': 0.05,
    'BTCUSD': 0.02
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
            return LOT_CAPS_COT_1000.get(symbol, 0.01)

        profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, info.volume_min, 1000.0, 1000.0 + sl_points)
        if profit and profit > 0:
            lots = (risk_cash / profit) * info.volume_min
        else:
            lots = risk_cash / (sl_points * info.trade_contract_size)

        step = info.volume_step
        lots = round(lots / step) * step

        max_lot_allowed = LOT_CAPS_COT_1000.get(symbol, 0.05) * scale
        lots = min(lots, max_lot_allowed)

        return round(max(info.volume_min, min(lots, info.volume_max)), 2)

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
            tp_price = round(current_price + cfg['tp_pts'], info.digits)
            comment = f"COT_{symbol}_SqdBull"[:31]
            print(f"[🚀 GATILLO COT] SHORT SQUEEZE ALCISTA en {symbol} (COT {cot_idx}% < {cfg['cot_bull_thresh']}%) | Magic: {magic}")
            print(f"   Operación: BUY | Lotes: {lots} | SL: {sl_price} | TP: {tp_price}")
            if execute:
                self.send_order(symbol, 'BUY', sl_price, tp_price, lots, comment, magic)
            return

        # GATILLO 2: LIQUIDACIÓN BAJISTA (LONG SQUEEZE)
        if cot_idx >= cfg['cot_bear_thresh'] and current_price < weekly_vwap:
            lots = self.calculate_lots(symbol, cfg['sl_pts'])
            sl_price = round(current_price + cfg['sl_pts'], info.digits)
            tp_price = round(current_price - cfg['tp_pts'], info.digits)
            comment = f"COT_{symbol}_LiqBear"[:31]
            print(f"[💥 GATILLO COT] LIQUIDACIÓN BAJISTA en {symbol} (COT {cot_idx}% > {cfg['cot_bear_thresh']}%) | Magic: {magic}")
            print(f"   Operación: SELL | Lotes: {lots} | SL: {sl_price} | TP: {tp_price}")
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

"""
================================================================================
ESTRATEGIA 2: STAT-ARB PAIR TRADING (MULTI-PAR CUANTITATIVO)
Arbitraje Estadístico de Desviación Z-Score en IC Markets MT5
================================================================================
Pares Cointegrados:
1. USTEC vs US500   (Nasdaq vs S&P 500 - Correlación Histórica > 0.92)
2. US30 vs US2000   (Dow Jones vs Russell 2000 - Large Cap vs Small Cap)
3. EURUSD vs GBPUSD (Euro FX vs British Pound - Correlación FX > 0.85)
4. XAUUSD vs XTIUSD (Oro vs Petróleo WTI - Ratio de Materias Primas)
================================================================================
"""

import sys
import os
import time
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

MAGIC_PAIR_BASE = 777200
SLIPPAGE_MAX = 10
RISK_PERCENT = 1.0

MULTI_PAIRS = {
    'USTEC_US500': {
        'name': 'Nasdaq 100 vs S&P 500',
        'sym_a': 'USTEC',
        'sym_b': 'US500',
        'magic': 732100,
        'comment_prefix': 'SA_USTEC_US500',
        'lookback_bars': 40,
        'z_entry': 2.2,
        'z_exit': 0.2,
        'z_stop': 3.5,
        'max_spread_a': 2.5,
        'max_spread_b': 0.8
    },
    'US30_US2000': {
        'name': 'Dow Jones 30 vs Russell 2000',
        'sym_a': 'US30',
        'sym_b': 'US2000',
        'magic': 732200,
        'comment_prefix': 'SA_US30_US2000',
        'lookback_bars': 40,
        'z_entry': 2.2,
        'z_exit': 0.2,
        'z_stop': 3.5,
        'max_spread_a': 3.0,
        'max_spread_b': 0.8
    },
    'EURUSD_GBPUSD': {
        'name': 'Euro FX vs British Pound',
        'sym_a': 'EURUSD',
        'sym_b': 'GBPUSD',
        'magic': 732300,
        'comment_prefix': 'SA_EUR_GBP',
        'lookback_bars': 40,
        'z_entry': 2.2,
        'z_exit': 0.2,
        'z_stop': 3.5,
        'max_spread_a': 0.00015,
        'max_spread_b': 0.00020
    },
    'XAUUSD_XTIUSD': {
        'name': 'Gold vs WTI Crude Oil',
        'sym_a': 'XAUUSD',
        'sym_b': 'XTIUSD',
        'magic': 732400,
        'comment_prefix': 'SA_XAU_XTI',
        'lookback_bars': 40,
        'z_entry': 2.2,
        'z_exit': 0.2,
        'z_stop': 3.5,
        'max_spread_a': 0.50,
        'max_spread_b': 0.05
    }
}

LOT_CAPS_PAIR_1000 = {
    'USTEC': 0.10,
    'US500': 0.30,
    'US30': 0.10,
    'US2000': 1.00,
    'EURUSD': 0.02,
    'GBPUSD': 0.02,
    'XAUUSD': 0.01,
    'XTIUSD': 0.04
}

class MultiPairStatArbStrategy:
    def __init__(self, risk_pct=RISK_PERCENT):
        self.risk_pct = risk_pct

    def calculate_zscore(self, sym_a, sym_b, lookback=40):
        rates_a = mt5.copy_rates_from_pos(sym_a, mt5.TIMEFRAME_M15, 0, lookback + 10)
        rates_b = mt5.copy_rates_from_pos(sym_b, mt5.TIMEFRAME_M15, 0, lookback + 10)
        if rates_a is None or rates_b is None:
            return None, None, None, None

        df_a = pd.DataFrame(rates_a)
        df_b = pd.DataFrame(rates_b)
        min_len = min(len(df_a), len(df_b))
        df_a = df_a.iloc[-min_len:].reset_index(drop=True)
        df_b = df_b.iloc[-min_len:].reset_index(drop=True)

        ratio = df_a['close'] / df_b['close']
        rolling_mean = ratio.rolling(lookback).mean()
        rolling_std = ratio.rolling(lookback).std()
        z_score = (ratio - rolling_mean) / rolling_std

        return float(z_score.iloc[-1]), float(ratio.iloc[-1]), float(rolling_mean.iloc[-1]), float(rolling_std.iloc[-1])

    def calculate_dollar_neutral_lots(self, sym_a, sym_b):
        acc = mt5.account_info()
        balance = acc.balance if acc else 1000.0
        scale = max(0.5, balance / 1000.0)
        target_risk = balance * (self.risk_pct / 100.0)

        info_a = mt5.symbol_info(sym_a)
        info_b = mt5.symbol_info(sym_b)
        tick_a = mt5.symbol_info_tick(sym_a)
        tick_b = mt5.symbol_info_tick(sym_b)

        if not info_a or not info_b or not tick_a or not tick_b:
            return 0.01, 0.01

        price_a = tick_a.bid
        price_b = tick_b.bid

        notional_per_lot_a = price_a * info_a.trade_contract_size
        notional_per_lot_b = price_b * info_b.trade_contract_size

        lots_a = (target_risk / (price_a * 0.012 * info_a.trade_contract_size))
        lots_a = round(lots_a / info_a.volume_step) * info_a.volume_step
        max_cap_a = LOT_CAPS_PAIR_1000.get(sym_a, 0.05) * scale
        lots_a = max(info_a.volume_min, min(lots_a, max_cap_a))

        total_val_a = lots_a * notional_per_lot_a
        lots_b = total_val_a / notional_per_lot_b
        lots_b = round(lots_b / info_b.volume_step) * info_b.volume_step
        max_cap_b = LOT_CAPS_PAIR_1000.get(sym_b, 0.05) * scale
        lots_b = max(info_b.volume_min, min(lots_b, max_cap_b))

        return round(lots_a, 2), round(lots_b, 2)

    def get_open_pair_positions(self, magic):
        positions = mt5.positions_get()
        if not positions:
            return []
        return [p for p in positions if p.magic == magic]

    def close_pair_positions(self, magic, comment="Pair_Close"):
        open_pos = self.get_open_pair_positions(magic)
        for p in open_pos:
            tick = mt5.symbol_info_tick(p.symbol)
            close_price = tick.bid if p.type == mt5.ORDER_TYPE_BUY else tick.ask
            close_type = mt5.ORDER_TYPE_SELL if p.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            req = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": p.ticket,
                "symbol": p.symbol,
                "volume": p.volume,
                "type": close_type,
                "price": float(close_price),
                "deviation": SLIPPAGE_MAX,
                "magic": magic,
                "comment": comment
            }
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"[✅ CIERRE PAR] #{p.ticket} ({p.symbol}) cerrado.")

    def is_pair_in_session(self, p_key):
        """Filtro de Horario Institucional Calibrado por Par:
        - Bloqueo de fin de semana (Viernes 20:55 UTC a Domingo 22:00 UTC)
        - Bloqueo Anti-Rollover de IC Markets (20:55 a 22:30 UTC)
        - USTEC_US500 / US30_US2000: 13:30 a 20:30 UTC (Sesión Cash Wall Street)
        - EURUSD_GBPUSD: 07:00 a 17:00 UTC (Solapamiento Londres / Europa)
        - XAUUSD_XTIUSD: 08:00 a 19:30 UTC (Pits Oro / Crudo)
        """
        now_utc = datetime.now(timezone.utc)
        weekday = now_utc.weekday()
        hour = now_utc.hour
        minute = now_utc.minute
        time_decimal = hour + (minute / 60.0)

        # 1. Fin de semana
        if weekday == 5:
            return False
        if weekday == 6 and time_decimal < 22.0:
            return False
        if weekday == 4 and time_decimal >= 20.91:
            return False

        # 2. Bloqueo Rollover
        if 20.91 <= time_decimal < 22.5:
            return False

        # 3. Horarios específicos por par
        if p_key in ['USTEC_US500', 'US30_US2000']:
            return 13.5 <= time_decimal < 20.5 # 13:30 a 20:30 UTC
        elif p_key == 'EURUSD_GBPUSD':
            return 7.0 <= time_decimal < 17.0  # 07:00 a 17:00 UTC
        elif p_key == 'XAUUSD_XTIUSD':
            return 8.0 <= time_decimal < 19.5  # 08:00 a 19:30 UTC
        return True

    def evaluate_pair(self, pair_key, cfg, execute=True):
        mt5.symbol_select(cfg['sym_a'], True)
        mt5.symbol_select(cfg['sym_b'], True)
        tick_a = mt5.symbol_info_tick(cfg['sym_a'])
        tick_b = mt5.symbol_info_tick(cfg['sym_b'])

        if not tick_a or not tick_b:
            return

        spread_a = round(tick_a.ask - tick_a.bid, 5)
        spread_b = round(tick_b.ask - tick_b.bid, 5)

        if spread_a > cfg['max_spread_a'] or spread_b > cfg['max_spread_b']:
            return

        z_score, cur_ratio, mean, std = self.calculate_zscore(cfg['sym_a'], cfg['sym_b'], cfg['lookback_bars'])
        if z_score is None:
            return

        open_pair = self.get_open_pair_positions(cfg['magic'])

        print(f"\n[STAT-ARB] {cfg['name']} | Ratio: {cur_ratio:.4f} | Media: {mean:.4f} | Z-Score: {z_score:+.2f} σ")

        # 1. Monitorear salida si ya hay posición
        if len(open_pair) >= 2:
            if abs(z_score) <= cfg['z_exit']:
                print(f"[🎯 TAKE PROFIT] Par {cfg['name']} regresó a la media (Z = {z_score:+.2f}). Cerrando...")
                if execute:
                    self.close_pair_positions(cfg['magic'], "Pair_TP_MeanRevert")
                return

            if abs(z_score) >= cfg['z_stop']:
                print(f"[🛑 STOP LOSS] Par {cfg['name']} divergencia extrema (Z = {z_score:+.2f}). Protegiendo...")
                if execute:
                    self.close_pair_positions(cfg['magic'], "Pair_SL_Divergence")
                return
            return

        # 2. Evaluar entradas (verificando filtro de sesión institucional)
        if not self.is_pair_in_session(pair_key):
            print(f"  [Horario Stat-Arb] Par {cfg['name']} fuera de sesión óptima. Entrada bloqueada.")
            return

        lots_a, lots_b = self.calculate_dollar_neutral_lots(cfg['sym_a'], cfg['sym_b'])
        pfx = cfg.get('comment_prefix', 'SA_PAIR')

        if z_score >= cfg['z_entry']:
            print(f"[⚡ GATILLO STAT-ARB] {cfg['name']} SOBRE-EXTENDIDO (Z = {z_score:+.2f} σ) | Magic: {cfg['magic']}")
            print(f"   VENDER {cfg['sym_a']} ({lots_a} lotes) + COMPRAR {cfg['sym_b']} ({lots_b} lotes)")
            if execute:
                comm_a = f"{pfx}_{cfg['sym_a']}_S"[:31]
                comm_b = f"{pfx}_{cfg['sym_b']}_B"[:31]
                self.execute_pair(cfg['sym_a'], 'SELL', lots_a, cfg['sym_b'], 'BUY', lots_b, cfg['magic'], comm_a, comm_b)
            return

        if z_score <= -cfg['z_entry']:
            print(f"[⚡ GATILLO STAT-ARB] {cfg['name']} INFRA-EXTENDIDO (Z = {z_score:+.2f} σ) | Magic: {cfg['magic']}")
            print(f"   COMPRAR {cfg['sym_a']} ({lots_a} lotes) + VENDER {cfg['sym_b']} ({lots_b} lotes)")
            if execute:
                comm_a = f"{pfx}_{cfg['sym_a']}_B"[:31]
                comm_b = f"{pfx}_{cfg['sym_b']}_S"[:31]
                self.execute_pair(cfg['sym_a'], 'BUY', lots_a, cfg['sym_b'], 'SELL', lots_b, cfg['magic'], comm_a, comm_b)
            return

        print(f"  [Estado] En rango normal (|Z| < 2.0).")

    def execute_pair(self, sym_a, type_a, lots_a, sym_b, type_b, lots_b, magic, comm_a, comm_b):
        tick_a = mt5.symbol_info_tick(sym_a)
        tick_b = mt5.symbol_info_tick(sym_b)

        p_a = tick_a.ask if type_a == 'BUY' else tick_a.bid
        p_b = tick_b.ask if type_b == 'BUY' else tick_b.bid

        ot_a = mt5.ORDER_TYPE_BUY if type_a == 'BUY' else mt5.ORDER_TYPE_SELL
        ot_b = mt5.ORDER_TYPE_BUY if type_b == 'BUY' else mt5.ORDER_TYPE_SELL

        req_a = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": sym_a,
            "volume": float(lots_a),
            "type": ot_a,
            "price": float(p_a),
            "deviation": SLIPPAGE_MAX,
            "magic": int(magic),
            "comment": comm_a[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        req_b = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": sym_b,
            "volume": float(lots_b),
            "type": ot_b,
            "price": float(p_b),
            "deviation": SLIPPAGE_MAX,
            "magic": int(magic),
            "comment": comm_b[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res_a = mt5.order_send(req_a)
        res_b = mt5.order_send(req_b)
        print(f"[✅ PAR EJECUTADO] #{res_a.order} {sym_a} {type_a} ({comm_a}) | #{res_b.order} {sym_b} {type_b} ({comm_b}) | Magic: {magic}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Statistical Arbitrage Multi-Pair Strategy (IC Markets MT5)")
    parser.add_argument('--execute', action='store_true', help='Ejecutar órdenes en vivo si hay señal')
    args = parser.parse_args()

    if mt5.initialize():
        strat = MultiPairStatArbStrategy(risk_pct=1.0)
        print("=" * 85)
        print("   AUDITORÍA EN VIVO: STATISTICAL ARBITRAGE MULTI-PAR (IC MARKETS)")
        print(f"   Broker: {mt5.account_info().server} | Cuenta: {mt5.account_info().login}")
        print("=" * 85)
        for p_key, cfg in MULTI_PAIRS.items():
            strat.evaluate_pair(p_key, cfg, execute=args.execute)
        mt5.shutdown()

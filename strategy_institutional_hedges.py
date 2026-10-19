"""
================================================================================
SUITE CUANTITATIVA AVANZADA: 6 ESTRATEGIAS INSTITUCIONALES CON HEDGE (CME + IC MARKETS)
================================================================================
1. CVOL Skew Dispersion          (XAUUSD + EURUSD)  - Magic: 777401
2. Pace-of-Roll Liquidity         (US500 + USTEC)    - Magic: 777402
3. FedWatch Parity Hedge          (USDJPY + XAUUSD)  - Magic: 777403
4. OPEX Max Pain Pinning          (US500 vs USTEC)   - Magic: 777404
5. Brent vs WTI Crack Proxy       (XTIUSD vs XBRUSD) - Magic: 777405
6. FX Swap Rate Basis Parity      (EURUSD vs USDJPY) - Magic: 777406
================================================================================
"""

import sys
import os
import time
import math
import json
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import MetaTrader5 as mt5
import pandas as pd
import numpy as np

SLIPPAGE_MAX = 10
DEFAULT_RISK_PCT = 1.0

# Límites máximos estrictos de lotes calibrados para cuenta de 1,000 USD (Micro-Risk)
LOT_CAPS_HEDGE_1000 = {
    'USTEC': 0.10,
    'US500': 0.30,
    'US30': 0.10,
    'EURUSD': 0.02,
    'USDJPY': 0.02,
    'XAUUSD': 0.01,
    'XTIUSD': 0.04,
    'XBRUSD': 0.04
}

class AdvancedHedgeStrategies:
    def __init__(self, risk_pct=DEFAULT_RISK_PCT):
        self.risk_pct = risk_pct
        self.peak_profit = {}    # Registro de ganancia máxima alcanzada por par (para Trailing Stop)
        self.be_activated = {}   # Estado de Break-Even activado por par

    # =========================================================================
    # MOTOR INSTITUCIONAL DE GESTIÓN DE RIESGO: TP, SL, BREAK-EVEN Y TRAILING
    # =========================================================================
    def manage_pair_risk(self, magic, strat_name):
        """Monitorea el PnL neto flotante de la cesta y aplica TP, SL, Break-Even y Trailing Stop"""
        open_pos = self.get_open_positions(magic)
        if len(open_pos) < 2:
            self.peak_profit.pop(magic, None)
            self.be_activated.pop(magic, None)
            return False

        acc = mt5.account_info()
        total_pnl = sum(p.profit + p.swap for p in open_pos)

        target_tp = acc.balance * (self.risk_pct * 2.0 / 100.0)   # +2.0% de la cuenta ($500 en $25k)
        max_sl = -1.0 * acc.balance * (self.risk_pct / 100.0)     # -1.0% de la cuenta (-$250 en $25k)
        be_trigger = target_tp * 0.50                             # Al 50% del TP (+$250)
        be_lock_val = acc.balance * 0.001                         # Cierre con +$25 para cubrir spread

        print(f"  [🛡️ RIESGO HEDGE] {strat_name} | PnL Flotante: ${total_pnl:+.2f} USD | TP: +${target_tp:.2f} | SL: ${max_sl:.2f}")

        # 1. TAKE PROFIT COMBINADO
        if total_pnl >= target_tp:
            print(f"[🎯 TAKE PROFIT ALCANZADO] {strat_name}: Meta de ganancia alcanzada (+${total_pnl:.2f} USD). Cerrando par...")
            self.close_pair_positions(magic, f"{strat_name}_TP_Hit")
            return True

        # 2. STOP LOSS DE CATÁSTROFE / MÁXIMA PÉRDIDA
        if total_pnl <= max_sl:
            print(f"[🛑 STOP LOSS EJECUTADO] {strat_name}: Límite de pérdida alcanzado (${total_pnl:.2f} USD). Cerrando para proteger capital...")
            self.close_pair_positions(magic, f"{strat_name}_SL_Cut")
            return True

        # 3. ACTIVACIÓN Y MONITOREO DE BREAK-EVEN
        if total_pnl >= be_trigger and not self.be_activated.get(magic, False):
            self.be_activated[magic] = True
            print(f"[🛡️ BREAK-EVEN ASEGURADO] {strat_name}: Ganancia al 50% (+${total_pnl:.2f}). Se bloquearon pérdidas.")

        if self.be_activated.get(magic, False) and total_pnl <= be_lock_val:
            print(f"[🛡️ SALIDA BREAK-EVEN] {strat_name}: El precio retrocedió al punto de entrada. Cerrando con ganancia protegida (+${total_pnl:.2f}).")
            self.close_pair_positions(magic, f"{strat_name}_BE_Lock")
            return True

        # 4. TRAILING STOP DINÁMICO (A partir del 60% de ganancia)
        if total_pnl >= (target_tp * 0.60):
            peak = max(self.peak_profit.get(magic, total_pnl), total_pnl)
            self.peak_profit[magic] = peak
            trailing_floor = peak * 0.75 # Si retrocede un 25% desde el pico máximo
            if total_pnl <= trailing_floor:
                print(f"[🏹 TRAILING STOP EJECUTADO] {strat_name}: Pico máximo ${peak:.2f} -> Asegurando ${total_pnl:.2f} USD...")
                self.close_pair_positions(magic, f"{strat_name}_TS_Exit")
                return True

        return False

    # =========================================================================
    # UTILIDADES DE GESTIÓN Y CÁLCULO DOLLAR-NEUTRAL / BETA
    # =========================================================================
    def calculate_dollar_neutral_lots(self, sym_a, sym_b):
        """Calcula el lotaje de dos piernas para que el valor nocional ($) sea 100% equivalente"""
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

        lots_a = target_risk / (price_a * 0.015 * info_a.trade_contract_size)
        lots_a = round(lots_a / info_a.volume_step) * info_a.volume_step
        max_cap_a = LOT_CAPS_HEDGE_1000.get(sym_a, 0.05) * scale
        lots_a = max(info_a.volume_min, min(lots_a, max_cap_a))

        total_notional_a = lots_a * notional_per_lot_a
        lots_b = total_notional_a / notional_per_lot_b
        lots_b = round(lots_b / info_b.volume_step) * info_b.volume_step
        max_cap_b = LOT_CAPS_HEDGE_1000.get(sym_b, 0.05) * scale
        lots_b = max(info_b.volume_min, min(lots_b, max_cap_b))

        return round(lots_a, 2), round(lots_b, 2)

    def get_open_positions(self, magic):
        positions = mt5.positions_get()
        if not positions:
            return []
        return [p for p in positions if p.magic == magic]

    def close_pair_positions(self, magic, comment="Hedge_Close"):
        open_pos = self.get_open_positions(magic)
        for p in open_pos:
            tick = mt5.symbol_info_tick(p.symbol)
            if not tick:
                continue
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
                "comment": comment[:31]
            }
            res = mt5.order_send(req)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"[✅ CIERRE HEDGE #{p.ticket}] {p.symbol} cerrado exitosamente.")

    def execute_hedge_pair(self, sym_a, type_a, lots_a, sym_b, type_b, lots_b, magic, comm_a, comm_b):
        tick_a = mt5.symbol_info_tick(sym_a)
        tick_b = mt5.symbol_info_tick(sym_b)
        info_a = mt5.symbol_info(sym_a)
        info_b = mt5.symbol_info(sym_b)

        p_a = tick_a.ask if type_a.upper() == 'BUY' else tick_a.bid
        p_b = tick_b.ask if type_b.upper() == 'BUY' else tick_b.bid

        ot_a = mt5.ORDER_TYPE_BUY if type_a.upper() == 'BUY' else mt5.ORDER_TYPE_SELL
        ot_b = mt5.ORDER_TYPE_BUY if type_b.upper() == 'BUY' else mt5.ORDER_TYPE_SELL

        # Stop Loss y Take Profit duros de emergencia en el broker (±3.0% de distancia)
        dist_a = p_a * 0.03
        dist_b = p_b * 0.03
        sl_a = round(p_a - dist_a, info_a.digits) if type_a.upper() == 'BUY' else round(p_a + dist_a, info_a.digits)
        tp_a = round(p_a + (dist_a * 2.0), info_a.digits) if type_a.upper() == 'BUY' else round(p_a - (dist_a * 2.0), info_a.digits)

        sl_b = round(p_b - dist_b, info_b.digits) if type_b.upper() == 'BUY' else round(p_b + dist_b, info_b.digits)
        tp_b = round(p_b + (dist_b * 2.0), info_b.digits) if type_b.upper() == 'BUY' else round(p_b - (dist_b * 2.0), info_b.digits)

        req_a = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": sym_a,
            "volume": float(lots_a),
            "type": ot_a,
            "price": float(p_a),
            "sl": float(sl_a),
            "tp": float(tp_a),
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
            "sl": float(sl_b),
            "tp": float(tp_b),
            "deviation": SLIPPAGE_MAX,
            "magic": int(magic),
            "comment": comm_b[:31],
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        res_a = mt5.order_send(req_a)
        res_b = mt5.order_send(req_b)
        print(f"[🚀 HEDGE EJECUTADO] #{res_a.order} {sym_a} {type_a} ({comm_a}) | #{res_b.order} {sym_b} {type_b} ({comm_b}) | Magic: {magic}")

    def is_hedge_in_session(self, hedge_name):
        """Filtro de Horario Institucional Calibrado por Estrategia de Hedge:
        - Bloqueo de fin de semana (Viernes 20:55 UTC a Domingo 22:00 UTC)
        - Bloqueo Anti-Rollover de IC Markets (20:55 a 22:30 UTC)
        - CVOL Skew (XAU+EUR): 08:00 a 17:00 UTC (Solapamiento Londres / NY)
        - Pace of Roll (ES+NQ): 13:30 a 20:30 UTC en semana de vencimiento
        - FedWatch (JPY+XAU): 12:30 a 20:30 UTC (Ventana macro EE.UU.)
        - OPEX Max Pain (ES+NQ): Jueves y Viernes de 13:30 a 20:30 UTC (Expiración semanal Wall St)
        - Crack Proxy (WTI+Brent): 08:00 a 19:30 UTC (Mercado físico de crudo)
        - FX Swap Basis (EUR+JPY): 08:00 a 16:30 UTC (Escritorios de swaps bancarios)
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

        # 3. Horarios específicos por estrategia
        if hedge_name == 'CVOL_Skew':
            return 8.0 <= time_decimal < 17.0
        elif hedge_name == 'Pace_Of_Roll':
            return 13.5 <= time_decimal < 20.5
        elif hedge_name == 'FedWatch':
            return 12.5 <= time_decimal < 20.5
        elif hedge_name == 'OPEX_MaxPain':
            return (weekday in [3, 4]) and (13.5 <= time_decimal < 20.5)
        elif hedge_name == 'Crack_Proxy':
            return 8.0 <= time_decimal < 19.5
        elif hedge_name == 'FX_SwapBasis':
            return 8.0 <= time_decimal < 16.5
        return True

    # =========================================================================
    # ESTRATEGIA 1: CVOL SKEW DISPERSION (XAUUSD + EURUSD) - MAGIC: 750100
    # =========================================================================
    def evaluate_cvol_skew_dispersion(self, execute=True):
        magic = 750100
        sym_gold = 'XAUUSD'
        sym_eur = 'EURUSD'
        mt5.symbol_select(sym_gold, True)
        mt5.symbol_select(sym_eur, True)

        open_pos = self.get_open_positions(magic)
        if len(open_pos) >= 2:
            self.manage_pair_risk(magic, "CVOL_Skew")
            return

        if not self.is_hedge_in_session("CVOL_Skew"):
            print("  [Horario Institucional] CVOL Skew fuera de ventana operativa (08:00 - 17:00 UTC). En reposo.")
            return

        rates_gold = mt5.copy_rates_from_pos(sym_gold, mt5.TIMEFRAME_H1, 0, 48)
        rates_eur = mt5.copy_rates_from_pos(sym_eur, mt5.TIMEFRAME_H1, 0, 48)
        if rates_gold is None or rates_eur is None:
            return

        # Calcular ratio de volatilidad realizada vs retorno
        df_g = pd.DataFrame(rates_gold)
        df_e = pd.DataFrame(rates_eur)
        ret_g = df_g['close'].pct_change()
        ret_e = df_e['close'].pct_change()

        vol_g = ret_g.rolling(24).std().iloc[-1] * math.sqrt(24)
        vol_e = ret_e.rolling(24).std().iloc[-1] * math.sqrt(24)
        vol_ratio = vol_g / (vol_e + 1e-9)

        # Skew relativo (Oro despegando con prima de volatilidad alcista)
        is_gold_skew_bull = ret_g.iloc[-3:].sum() > 0.005 and vol_ratio > 1.8
        is_eur_subdued = abs(ret_e.iloc[-3:].sum()) < 0.002

        print(f"\n[CVOL SKEW DISPERSION] Oro vs Euro | Magic: {magic} | Vol Ratio: {vol_ratio:.2f} | Ret Oro: {ret_g.iloc[-3:].sum()*100:+.2f}%")
        if is_gold_skew_bull and is_eur_subdued:
            lots_g, lots_e = self.calculate_dollar_neutral_lots(sym_gold, sym_eur)
            print(f"[⚡ GATILLO CVOL] Fuga de Volatilidad en Oro con Euro lateralizado | Magic: {magic}")
            print(f"   COMPRAR {sym_gold} ({lots_g} lotes) + VENDER {sym_eur} ({lots_e} lotes)")
            if execute:
                comm_a = "HDG_CVOL_XAU_B"
                comm_b = "HDG_CVOL_EUR_S"
                self.execute_hedge_pair(sym_gold, 'BUY', lots_g, sym_eur, 'SELL', lots_e, magic, comm_a, comm_b)
        else:
            print("  [Estado] Dispersión de volatilidad en equilibrio.")

    # =========================================================================
    # ESTRATEGIA 2: PACE-OF-ROLL LIQUIDITY (US500 + USTEC) - MAGIC: 750200
    # =========================================================================
    def evaluate_pace_of_roll(self, execute=True):
        magic = 750200
        sym_es = 'US500'
        sym_nq = 'USTEC'
        mt5.symbol_select(sym_es, True)
        mt5.symbol_select(sym_nq, True)

        now = datetime.now()
        # Verificar si estamos en mes de expiración trimestral (Marzo=3, Junio=6, Septiembre=9, Diciembre=12)
        is_roll_month = now.month in [3, 6, 9, 12]
        # Tercer viernes cae entre los días 15 y 21 del mes. La semana de roll es del día 8 al 18.
        is_roll_week = is_roll_month and (8 <= now.day <= 18)

        print(f"\n[PACE-OF-ROLL LIQUIDITY] US500 vs USTEC | Magic: {magic} | Mes Roll: {is_roll_month} | Semana de Roll: {is_roll_week}")
        if not is_roll_week:
            print("  [Estado] Fuera de ventana de rollover trimestral. En reposo estratégico.")
            return

        open_pos = self.get_open_positions(magic)
        if len(open_pos) >= 2:
            self.manage_pair_risk(magic, "PaceOfRoll")
            return

        if not self.is_hedge_in_session("Pace_Of_Roll"):
            print("  [Horario Institucional] Pace of Roll fuera de ventana operativa (13:30 - 20:30 UTC). En reposo.")
            return

        # Medir divergencia de base entre ES y NQ
        rates_es = mt5.copy_rates_from_pos(sym_es, mt5.TIMEFRAME_M15, 0, 40)
        rates_nq = mt5.copy_rates_from_pos(sym_nq, mt5.TIMEFRAME_M15, 0, 40)
        if rates_es is None or rates_nq is None:
            return

        ratio = pd.Series(rates_nq['close']) / pd.Series(rates_es['close'])
        z_score = (ratio.iloc[-1] - ratio.rolling(30).mean().iloc[-1]) / ratio.rolling(30).std().iloc[-1]

        if abs(z_score) >= 1.8:
            lots_es, lots_nq = self.calculate_dollar_neutral_lots(sym_es, sym_nq)
            if z_score > 0:
                print(f"[⚡ GATILLO ROLLOVER] NQ adelantado a ES (Z = {z_score:+.2f} σ) | Magic: {magic}")
                print(f"   COMPRAR {sym_es} ({lots_es}) + VENDER {sym_nq} ({lots_nq})")
                if execute:
                    comm_a = "HDG_ROLL_ES_B"
                    comm_b = "HDG_ROLL_NQ_S"
                    self.execute_hedge_pair(sym_es, 'BUY', lots_es, sym_nq, 'SELL', lots_nq, magic, comm_a, comm_b)
            else:
                print(f"[⚡ GATILLO ROLLOVER] ES adelantado a NQ (Z = {z_score:+.2f} σ) | Magic: {magic}")
                print(f"   COMPRAR {sym_nq} ({lots_nq}) + VENDER {sym_es} ({lots_es})")
                if execute:
                    comm_a = "HDG_ROLL_NQ_B"
                    comm_b = "HDG_ROLL_ES_S"
                    self.execute_hedge_pair(sym_nq, 'BUY', lots_nq, sym_es, 'SELL', lots_es, magic, comm_a, comm_b)

    # =========================================================================
    # ESTRATEGIA 3: FEDWATCH PARITY HEDGE (USDJPY + XAUUSD) - MAGIC: 750300
    # =========================================================================
    def evaluate_fedwatch_parity_hedge(self, execute=True):
        magic = 750300
        sym_jpy = 'USDJPY'
        sym_gold = 'XAUUSD'
        mt5.symbol_select(sym_jpy, True)
        mt5.symbol_select(sym_gold, True)

        open_pos = self.get_open_positions(magic)
        if len(open_pos) >= 2:
            self.manage_pair_risk(magic, "FedWatch")
            return

        if not self.is_hedge_in_session("FedWatch"):
            print("  [Horario Institucional] FedWatch fuera de ventana operativa macro (12:30 - 20:30 UTC). En reposo.")
            return

        # Medir aceleración de impulso en USDJPY vs Oro
        rates_jpy = mt5.copy_rates_from_pos(sym_jpy, mt5.TIMEFRAME_M15, 0, 20)
        rates_gold = mt5.copy_rates_from_pos(sym_gold, mt5.TIMEFRAME_M15, 0, 20)
        if rates_jpy is None or rates_gold is None:
            return

        # Si USDJPY rompe a la baja (descuento de tasas) y Oro rompe al alza
        ret_j = (rates_jpy[-1]['close'] - rates_jpy[-5]['close']) / rates_jpy[-5]['close']
        ret_g = (rates_gold[-1]['close'] - rates_gold[-5]['close']) / rates_gold[-5]['close']

        print(f"\n[FEDWATCH PARITY HEDGE] USDJPY vs XAUUSD | Magic: {magic} | Impulso JPY: {ret_j*100:+.2f}% | Impulso Oro: {ret_g*100:+.2f}%")
        # Divergencia de tasas (expectativa de política monetaria laxa)
        if ret_j < -0.0020 and ret_g > 0.0030:
            lots_jpy, lots_gold = self.calculate_dollar_neutral_lots(sym_jpy, sym_gold)
            print(f"[⚡ GATILLO FEDWATCH] Descuento agresivo de tasas en progreso | Magic: {magic}")
            print(f"   VENDER {sym_jpy} ({lots_jpy}) + COMPRAR {sym_gold} ({lots_gold})")
            if execute:
                comm_a = "HDG_FED_JPY_S"
                comm_b = "HDG_FED_XAU_B"
                self.execute_hedge_pair(sym_jpy, 'SELL', lots_jpy, sym_gold, 'BUY', lots_gold, magic, comm_a, comm_b)
        else:
            print("  [Estado] Curva de rendimientos y paridad de tasas en equilibrio.")

    # =========================================================================
    # ESTRATEGIA 4: OPEX MAX PAIN PINNING (US500 vs USTEC) - MAGIC: 750400
    # =========================================================================
    def evaluate_opex_max_pain(self, execute=True):
        magic = 750400
        sym_es = 'US500'
        sym_nq = 'USTEC'
        mt5.symbol_select(sym_es, True)
        mt5.symbol_select(sym_nq, True)

        now = datetime.now()
        # Jueves = 3, Viernes = 4
        is_opex_window = now.weekday() in [3, 4]
        print(f"\n[OPEX MAX PAIN PINNING] US500 vs USTEC | Magic: {magic} | Ventana OPEX (Jue/Vie): {is_opex_window}")

        if not is_opex_window:
            print("  [Estado] Esperando ventana de expiración semanal (Jueves 14:00 GMT - Viernes).")
            return

        open_pos = self.get_open_positions(magic)
        if len(open_pos) >= 2:
            self.manage_pair_risk(magic, "OPEX_MaxPain")
            return

        if not self.is_hedge_in_session("OPEX_MaxPain"):
            print("  [Horario Institucional] OPEX Max Pain fuera de ventana (Jueves/Viernes 13:30 - 20:30 UTC). En reposo.")
            return

        tick_es = mt5.symbol_info_tick(sym_es)
        if not tick_es:
            return

        # Calcular strike de Max Pain sintético (muro central de mayor concentración acumulada)
        rates = mt5.copy_rates_from_pos(sym_es, mt5.TIMEFRAME_D1, 0, 5)
        if rates is None or len(rates) == 0:
            return
        weekly_high = max(r['high'] for r in rates)
        weekly_low = min(r['low'] for r in rates)
        max_pain_synthetic = round((weekly_high + weekly_low) / 2.0 / 25.0) * 25.0

        current_p = tick_es.bid
        dist_pts = max_pain_synthetic - current_p

        print(f"  Max Pain Target: {max_pain_synthetic} | Precio Actual: {current_p} | Distancia: {dist_pts:+.2f} pts")

        if abs(dist_pts) >= 18.0:
            lots_es, lots_nq = self.calculate_dollar_neutral_lots(sym_es, sym_nq)
            if dist_pts > 0:
                print(f"[⚡ GATILLO MAX PAIN] US500 por debajo del Pain Strike -> Atracción Alcista | Magic: {magic}")
                print(f"   COMPRAR {sym_es} ({lots_es}) + VENDER {sym_nq} ({lots_nq} Beta-Hedge)")
                if execute:
                    comm_a = "HDG_OPEX_ES_B"
                    comm_b = "HDG_OPEX_NQ_S"
                    self.execute_hedge_pair(sym_es, 'BUY', lots_es, sym_nq, 'SELL', lots_nq, magic, comm_a, comm_b)
            else:
                print(f"[⚡ GATILLO MAX PAIN] US500 por encima del Pain Strike -> Atracción Bajista | Magic: {magic}")
                print(f"   VENDER {sym_es} ({lots_es}) + COMPRAR {sym_nq} ({lots_nq} Beta-Hedge)")
                if execute:
                    comm_a = "HDG_OPEX_ES_S"
                    comm_b = "HDG_OPEX_NQ_B"
                    self.execute_hedge_pair(sym_es, 'SELL', lots_es, sym_nq, 'BUY', lots_nq, magic, comm_a, comm_b)

    # =========================================================================
    # ESTRATEGIA 5: BRENT VS WTI CRACK PROXY (XTIUSD vs XBRUSD) - MAGIC: 750500
    # =========================================================================
    def evaluate_brent_wti_crack_proxy(self, execute=True):
        magic = 750500
        sym_wti = 'XTIUSD'
        sym_brent = 'XBRUSD'
        mt5.symbol_select(sym_wti, True)
        mt5.symbol_select(sym_brent, True)

        tick_w = mt5.symbol_info_tick(sym_wti)
        tick_b = mt5.symbol_info_tick(sym_brent)
        if not tick_w or not tick_b:
            return

        rates_w = mt5.copy_rates_from_pos(sym_wti, mt5.TIMEFRAME_M15, 0, 50)
        rates_b = mt5.copy_rates_from_pos(sym_brent, mt5.TIMEFRAME_M15, 0, 50)
        if rates_w is None or rates_b is None:
            return

        df_w = pd.DataFrame(rates_w)
        df_b = pd.DataFrame(rates_b)
        min_len = min(len(df_w), len(df_b))
        df_w = df_w.iloc[-min_len:].reset_index(drop=True)
        df_b = df_b.iloc[-min_len:].reset_index(drop=True)

        spread = df_b['close'] - df_w['close'] # Brent - WTI Spread
        rolling_mean = spread.rolling(40).mean()
        rolling_std = spread.rolling(40).std()
        z_score = (spread - rolling_mean) / rolling_std

        cur_spread = spread.iloc[-1]
        cur_z = z_score.iloc[-1]

        open_pos = self.get_open_positions(magic)
        print(f"\n[BRENT vs WTI CRACK PROXY] Spread: ${cur_spread:.3f} | Media: ${rolling_mean.iloc[-1]:.3f} | Z-Score: {cur_z:+.2f} σ | Magic: {magic}")

        # Monitorear salida y riesgo si ya hay posiciones
        if len(open_pos) >= 2:
            if self.manage_pair_risk(magic, "BrentWTI_Crack"):
                return
            if abs(cur_z) <= 0.25:
                print(f"[🎯 TAKE PROFIT] Spread Brent-WTI regresó a su media física (Z={cur_z:+.2f}). Cerrando...")
                if execute:
                    self.close_pair_positions(magic, "CrackProxy_TP")
            return

        if not self.is_hedge_in_session("Crack_Proxy"):
            print("  [Horario Institucional] Crack Proxy fuera de ventana de crudo físico (08:00 - 19:30 UTC). En reposo.")
            return

        # Entradas estadísticas a 2.0 desviaciones
        if cur_z >= 2.0:
            lots_w, lots_b = self.calculate_dollar_neutral_lots(sym_wti, sym_brent)
            print(f"[⚡ GATILLO CRACK PROXY] Brent anormalmente caro vs WTI (Z = {cur_z:+.2f} σ) | Magic: {magic}")
            print(f"   COMPRAR {sym_wti} ({lots_w}) + VENDER {sym_brent} ({lots_b})")
            if execute:
                comm_a = "HDG_CRK_WTI_B"
                comm_b = "HDG_CRK_BRN_S"
                self.execute_hedge_pair(sym_wti, 'BUY', lots_w, sym_brent, 'SELL', lots_b, magic, comm_a, comm_b)
        elif cur_z <= -2.0:
            lots_w, lots_b = self.calculate_dollar_neutral_lots(sym_wti, sym_brent)
            print(f"[⚡ GATILLO CRACK PROXY] WTI anormalmente caro vs Brent (Z = {cur_z:+.2f} σ) | Magic: {magic}")
            print(f"   VENDER {sym_wti} ({lots_w}) + COMPRAR {sym_brent} ({lots_b})")
            if execute:
                comm_a = "HDG_CRK_WTI_S"
                comm_b = "HDG_CRK_BRN_B"
                self.execute_hedge_pair(sym_wti, 'SELL', lots_w, sym_brent, 'BUY', lots_b, magic, comm_a, comm_b)
        else:
            print("  [Estado] Spread en rango físico normal.")

    # =========================================================================
    # ESTRATEGIA 6: FX SWAP RATE BASIS PARITY (EURUSD vs USDJPY) - MAGIC: 750600
    # =========================================================================
    def evaluate_fx_swap_basis_parity(self, execute=True):
        magic = 750600
        sym_eur = 'EURUSD'
        sym_jpy = 'USDJPY'
        mt5.symbol_select(sym_eur, True)
        mt5.symbol_select(sym_jpy, True)

        rates_e = mt5.copy_rates_from_pos(sym_eur, mt5.TIMEFRAME_M15, 0, 40)
        rates_j = mt5.copy_rates_from_pos(sym_jpy, mt5.TIMEFRAME_M15, 0, 40)
        if rates_e is None or rates_j is None:
            return

        # Creación sintética de paridad cruzada: EUR/JPY = EURUSD * USDJPY
        df_e = pd.DataFrame(rates_e)
        df_j = pd.DataFrame(rates_j)
        min_len = min(len(df_e), len(df_j))
        eurjpy_synthetic = df_e['close'].iloc[-min_len:].values * df_j['close'].iloc[-min_len:].values
        series_s = pd.Series(eurjpy_synthetic)

        mean_s = series_s.rolling(30).mean()
        std_s = series_s.rolling(30).std()
        z_score = (series_s - mean_s) / std_s

        cur_val = series_s.iloc[-1]
        cur_z = z_score.iloc[-1]

        open_pos = self.get_open_positions(magic)
        print(f"\n[FX SWAP BASIS PARITY] EURJPY Sintético: {cur_val:.3f} | Z-Score: {cur_z:+.2f} σ | Magic: {magic}")

        if len(open_pos) >= 2:
            if self.manage_pair_risk(magic, "FX_SwapBasis"):
                return
            if abs(cur_z) <= 0.2:
                print(f"[🎯 TAKE PROFIT] Paridad FX Swap retornó al equilibrio (Z={cur_z:+.2f}). Cerrando...")
                if execute:
                    self.close_pair_positions(magic, "FXBasis_TP")
            return

        if not self.is_hedge_in_session("FX_SwapBasis"):
            print("  [Horario Institucional] FX Swap Basis fuera de ventana bancaria (08:00 - 16:30 UTC). En reposo.")
            return

        if cur_z <= -2.0:
            lots_e, lots_j = self.calculate_dollar_neutral_lots(sym_eur, sym_jpy)
            print(f"[⚡ GATILLO FX BASIS] Euro infravalorado con Carry Swap favorable (Z = {cur_z:+.2f} σ) | Magic: {magic}")
            print(f"   COMPRAR {sym_eur} ({lots_e}) + COMPRAR {sym_jpy} ({lots_j}) [Dólar Neutro]")
            if execute:
                comm_a = "HDG_SWAP_EUR_B"
                comm_b = "HDG_SWAP_JPY_B"
                self.execute_hedge_pair(sym_eur, 'BUY', lots_e, sym_jpy, 'BUY', lots_j, magic, comm_a, comm_b)
        elif cur_z >= 2.0:
            lots_e, lots_j = self.calculate_dollar_neutral_lots(sym_eur, sym_jpy)
            print(f"[⚡ GATILLO FX BASIS] Euro sobrevalorado vs Yen (Z = {cur_z:+.2f} σ) | Magic: {magic}")
            print(f"   VENDER {sym_eur} ({lots_e}) + VENDER {sym_jpy} ({lots_j}) [Dólar Neutro]")
            if execute:
                comm_a = "HDG_SWAP_EUR_S"
                comm_b = "HDG_SWAP_JPY_S"
                self.execute_hedge_pair(sym_eur, 'SELL', lots_e, sym_jpy, 'SELL', lots_j, magic, comm_a, comm_b)
        else:
            print("  [Estado] Paridad de swap interbancario en equilibrio.")

    # =========================================================================
    # EJECUTOR MAESTRO DE LAS 6 ESTRATEGIAS
    # =========================================================================
    def run_all(self, execute=True):
        print("\n" + "=" * 85)
        print(f"🚀 EJECUTANDO CICLO: 6 ESTRATEGIAS CUANTITATIVAS CON HEDGE ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
        print("=" * 85)

        self.evaluate_cvol_skew_dispersion(execute=execute)
        self.evaluate_pace_of_roll(execute=execute)
        self.evaluate_fedwatch_parity_hedge(execute=execute)
        self.evaluate_opex_max_pain(execute=execute)
        self.evaluate_brent_wti_crack_proxy(execute=execute)
        self.evaluate_fx_swap_basis_parity(execute=execute)

    def run_daemon(self, interval_secs=30):
        print("\n" + "=" * 85)
        print("   INICIANDO EJECUCIÓN CONTINUA 24/7 DE 6 ESTRATEGIAS INSTITUCIONALES CON HEDGE")
        print(f"   Intervalo de Escaneo: cada {interval_secs} segundos")
        print("   Presione Ctrl + C para detener.")
        print("=" * 85)

        try:
            while True:
                self.run_all(execute=True)
                time.sleep(interval_secs)
        except KeyboardInterrupt:
            print("\n[*] Bot de Hedges detenido de forma segura.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Advanced Institutional Hedges - CME + IC Markets")
    parser.add_argument('--daemon', action='store_true', help='Ejecución continua 24/7')
    parser.add_argument('--audit', action='store_true', help='Modo auditoría / simulación (sin órdenes)')
    parser.add_argument('--run-once', action='store_true', help='Ejecución de un ciclo enviando órdenes reales')
    args = parser.parse_args()

    if mt5.initialize():
        suite = AdvancedHedgeStrategies(risk_pct=DEFAULT_RISK_PCT)
        if args.daemon:
            suite.run_daemon()
        elif args.audit:
            suite.run_all(execute=False)
        else:
            suite.run_all(execute=True)
        mt5.shutdown()

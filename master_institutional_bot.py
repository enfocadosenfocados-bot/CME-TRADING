"""
================================================================================
MASTER INSTITUTIONAL BOT - SUITE CUANTITATIVA CME + IC MARKETS MT5
================================================================================
Orquestador de Portafolio Cuantitativo Multi-Estrategia:
- Estrategia 1A: The Institutional Trinity (LNY: Londres + NY - 07:00 a 21:00 UTC)
- Estrategia 1B: The Institutional Trinity (NY: Solo Nueva York - 13:00 a 21:00 UTC)
- Estrategia 2:  Statistical Arbitrage Multi-Pair (USTEC/ES, YM/RTY, EUR/GBP, XAU/CL)
- Estrategia 3:  Macro COT Squeeze Engine (11 Activos CFTC/CME + Weekly VWAP)
- Estrategia 4:  6 Coberturas Institucionales CME (CVOL, Roll, FedWatch, OPEX, Crack, Swap)

Taxonomía de Magic Numbers y Comentarios:
- 71YY00: TR_LNY_{sym}_{Signal} (Trinity Londres + NY)
- 72YY00: TR_NY_{sym}_{Signal}  (Trinity Solo NY)
- 73YY00: SA_{pair}_{leg}       (Stat-Arb Multi-Par Cointegrado)
- 74YY00: COT_{sym}_{Signal}    (Macro COT Squeeze & Momentum)
- 75YY00: HDG_{type}_{sym}_{leg}(6 Coberturas Institucionales CME)
================================================================================
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import MetaTrader5 as mt5

from strategy_trinity import InstitutionalTrinityStrategy, TRINITY_ASSETS
from strategy_pair_trading import MultiPairStatArbStrategy, MULTI_PAIRS
from strategy_cot_squeeze import MacroCOTSqueezeStrategy, COT_CONFIG
from strategy_institutional_hedges import AdvancedHedgeStrategies

TRADE_RISK_PCT = 1.0           # Riesgo máximo individual por posición (1%)
MONITOR_INTERVAL_SECS = 15     # Intervalo de escaneo continuo en VPS

# Recorridos Empíricos Calibrados Basados en MFE Real de Trades Históricos y en Vivo:
EMPIRICAL_TARGETS = {
    # Activo: (TP1 50% parcial, TP2 objetivo final, Trailing stop pts, BE Buffer pts)
    'USTEC':  {'tp1_pts': 28.0,   'tp2_pts': 75.0,   'trail_pts': 22.0, 'be_buffer_pts': 2.0},
    'US500':  {'tp1_pts': 8.0,    'tp2_pts': 24.0,   'trail_pts': 7.0,  'be_buffer_pts': 0.8},
    'US30':   {'tp1_pts': 65.0,   'tp2_pts': 180.0,  'trail_pts': 50.0, 'be_buffer_pts': 5.0},
    'US2000': {'tp1_pts': 4.5,    'tp2_pts': 14.0,   'trail_pts': 4.0,  'be_buffer_pts': 0.4},
    'XAUUSD': {'tp1_pts': 8.0,    'tp2_pts': 22.0,   'trail_pts': 6.0,  'be_buffer_pts': 0.5},
    'XTIUSD': {'tp1_pts': 0.35,   'tp2_pts': 1.10,   'trail_pts': 0.30, 'be_buffer_pts': 0.03},
    'XNGUSD': {'tp1_pts': 0.025,  'tp2_pts': 0.080,  'trail_pts': 0.020,'be_buffer_pts': 0.003},
    'EURUSD': {'tp1_pts': 0.0015, 'tp2_pts': 0.0045, 'trail_pts': 0.0012,'be_buffer_pts': 0.0002},
    'GBPUSD': {'tp1_pts': 0.0018, 'tp2_pts': 0.0055, 'trail_pts': 0.0015,'be_buffer_pts': 0.0002},
    'USDJPY': {'tp1_pts': 0.20,   'tp2_pts': 0.60,   'trail_pts': 0.18, 'be_buffer_pts': 0.02},
    'BTCUSD': {'tp1_pts': 350.0,  'tp2_pts': 1100.0, 'trail_pts': 280.0,'be_buffer_pts': 25.0},
}

class MasterPortfolioBot:
    def __init__(self, mode='ALL_DUAL'):
        self.mode = mode.upper()
        # Instanciar todas las suites de estrategias
        self.strat_trinity_sniper = InstitutionalTrinityStrategy(session_mode='NY_SNIPER', risk_pct=TRADE_RISK_PCT)
        self.strat_trinity_lny    = InstitutionalTrinityStrategy(session_mode='LNY', risk_pct=TRADE_RISK_PCT)
        self.strat_trinity_ny     = InstitutionalTrinityStrategy(session_mode='NY', risk_pct=TRADE_RISK_PCT)
        self.strat_pair           = MultiPairStatArbStrategy(risk_pct=TRADE_RISK_PCT)
        self.strat_cot            = MacroCOTSqueezeStrategy(risk_pct=TRADE_RISK_PCT)
        self.strat_hedges         = AdvancedHedgeStrategies(risk_pct=TRADE_RISK_PCT)
        self.connected = False

        # Estado de posiciones con parcial 50% ya ejecutado
        self.state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'partial_closed_state.json')
        self.partial_closed = self._load_partial_state()

    def _load_partial_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_partial_state(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.partial_closed, f, indent=2)
        except Exception as e:
            print(f"[-] Error guardando estado de parciales: {e}")

    def connect(self):
        if not mt5.initialize():
            print(f"[-] Error iniciando MT5: {mt5.last_error()}")
            return False
        acc = mt5.account_info()
        print("=" * 85)
        print(f"🚀 CONEXIÓN ESTABLECIDA CON IC MARKETS ({acc.server})")
        print(f"   Cuenta: {acc.login} | Moneda: {acc.currency} | Balance: ${acc.balance:,.2f} USD | Margen Libre: ${acc.margin_free:,.2f} USD")
        print("=" * 85)
        self.connected = True
        return True

    def disconnect(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False

    def manage_directional_partials_and_trailing(self):
        """
        Gestión de Salida Parcial del 50% y Trailing Stop Runner Dinámico
        para posiciones direccionales puras:
        - Trinity LNY: Magic 71xxxx
        - Trinity NY: Magic 72xxxx
        - Macro COT: Magic 74xxxx
        - Legacy Trinity: Magic 777xxx
        
        Excluye estrictamente Hedges (75xxxx) y Stat-Arb (73xxxx) para mantener la neutralidad de la cobertura.
        """
        positions = mt5.positions_get()
        if not positions:
            return

        # Limpieza de tickets cerrados en MT5
        active_tickets = {str(p.ticket) for p in positions}
        keys_to_remove = [t for t in self.partial_closed if t not in active_tickets]
        if keys_to_remove:
            for t in keys_to_remove:
                del self.partial_closed[t]
            self._save_partial_state()

        for p in positions:
            magic_str = str(p.magic)
            # Solo posiciones direccionales
            is_directional = magic_str.startswith(('71', '72', '74', '777'))
            if not is_directional or magic_str.startswith(('73', '75')):
                continue

            sym = p.symbol
            if sym not in EMPIRICAL_TARGETS:
                continue

            cfg = EMPIRICAL_TARGETS[sym]
            tp1_pts = cfg['tp1_pts']
            tp2_pts = cfg['tp2_pts']
            trail_pts = cfg['trail_pts']
            be_buffer = cfg['be_buffer_pts']

            tick = mt5.symbol_info_tick(sym)
            info = mt5.symbol_info(sym)
            if not tick or not info:
                continue

            is_buy = (p.type == mt5.ORDER_TYPE_BUY)
            cur_price = tick.bid if is_buy else tick.ask
            excursion_pts = (cur_price - p.price_open) if is_buy else (p.price_open - cur_price)

            t_key = str(p.ticket)
            already_partial = (t_key in self.partial_closed)

            # FASE 1: Toma del 50% de ganancia en TP1 empírico
            if not already_partial:
                if excursion_pts >= tp1_pts:
                    step = info.volume_step
                    half_vol = p.volume / 2.0
                    close_vol = round(round(half_vol / step) * step, 2)

                    # Validar que podamos cerrar este volumen y dejar al menos el volumen mínimo
                    if close_vol >= info.volume_min and (round(p.volume - close_vol, 2) >= info.volume_min):
                        close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                        close_price = tick.bid if is_buy else tick.ask
                        req = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "position": p.ticket,
                            "symbol": sym,
                            "volume": float(close_vol),
                            "type": close_type,
                            "price": float(close_price),
                            "deviation": 10,
                            "magic": p.magic,
                            "comment": f"PART50_{sym}"[:31],
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_IOC,
                        }
                        res = mt5.order_send(req)
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            self.partial_closed[t_key] = {
                                "symbol": sym,
                                "open_price": p.price_open,
                                "closed_vol": close_vol,
                                "partial_time": datetime.now(timezone.utc).isoformat()
                            }
                            self._save_partial_state()
                            print(f"[💰 TOMA DE BENEFICIO 50%] Ticket #{p.ticket} ({sym}): Cerrado 50% ({close_vol} lotes) con ganancia de +{excursion_pts:.2f} pts!")

                            # Inmediatamente mover SL a Break-Even + Buffer
                            new_sl = round(p.price_open + be_buffer, info.digits) if is_buy else round(p.price_open - be_buffer, info.digits)
                            sl_req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": p.ticket,
                                "sl": float(new_sl),
                                "tp": float(p.tp)
                            }
                            sl_res = mt5.order_send(sl_req)
                            if sl_res and sl_res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"[🛡️ BREAK-EVEN ASEGURADO] Ticket #{p.ticket} ({sym}): SL colocado en {new_sl} (+{be_buffer} buffer). Runner 50% activo hacia TP2 (+{tp2_pts} pts).")
                        else:
                            ret_desc = res.comment if res else "None"
                            print(f"[-] Error enviando parcial para #{p.ticket} ({sym}): {res.retcode if res else 'Error'} - {ret_desc}")

            # FASE 2: Trailing Stop dinámico para el 50% restante (Runner hacia TP2)
            else:
                # La posición ya está parcializada y protegida en Break-Even.
                # Acompañamos el recorrido hacia TP2 mediante un Trailing Stop dinámico.
                stop_level_dist = info.trade_stops_level * info.point
                if is_buy:
                    candidate_sl = round(cur_price - trail_pts, info.digits)
                    be_level = round(p.price_open + be_buffer, info.digits)
                    # Solo avanzar el SL hacia arriba, y mantenerlo al menos en BE
                    if candidate_sl > p.sl and candidate_sl >= be_level:
                        if (cur_price - candidate_sl) >= stop_level_dist:
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": p.ticket,
                                "sl": float(candidate_sl),
                                "tp": float(p.tp)
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"[🏃 TRAILING RUNNER] Ticket #{p.ticket} ({sym}): SL avanzado a {candidate_sl} (Ganancia flotante: +{excursion_pts:.2f} pts | TP2 objetivo: +{tp2_pts} pts)")
                else:
                    candidate_sl = round(cur_price + trail_pts, info.digits)
                    be_level = round(p.price_open - be_buffer, info.digits)
                    # Solo avanzar el SL hacia abajo, y mantenerlo al menos en BE
                    if (p.sl == 0 or candidate_sl < p.sl) and candidate_sl <= be_level:
                        if (candidate_sl - cur_price) >= stop_level_dist:
                            req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": p.ticket,
                                "sl": float(candidate_sl),
                                "tp": float(p.tp)
                            }
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"[🏃 TRAILING RUNNER] Ticket #{p.ticket} ({sym}): SL avanzado a {candidate_sl} (Ganancia flotante: +{excursion_pts:.2f} pts | TP2 objetivo: +{tp2_pts} pts)")

    def manage_portfolio_breakeven(self):
        """Mueve automáticamente a Break-Even cualquier trade que alcance el 50% de ganancia hacia su TP.
        Protege posiciones no direccionales o con TP estático (Stat-Arb, Hedges).
        """
        positions = mt5.positions_get()
        if not positions:
            return
        for p in positions:
            # Las estrategias direccionales son gestionadas por manage_directional_partials_and_trailing
            if str(p.magic).startswith(('71', '72', '74', '777')):
                continue

            if not str(p.magic).startswith('7') or p.tp == 0:
                continue
            tick = mt5.symbol_info_tick(p.symbol)
            info = mt5.symbol_info(p.symbol)
            if not tick or not info:
                continue

            is_buy = p.type == mt5.ORDER_TYPE_BUY
            cur_price = tick.bid if is_buy else tick.ask
            dist_total = abs(p.tp - p.price_open)
            if dist_total <= 0:
                continue

            halfway = p.price_open + (dist_total * 0.5) if is_buy else p.price_open - (dist_total * 0.5)
            buffer = max(info.point * 10, dist_total * 0.02)

            # Fase 1: Break-Even al 50% del TP
            if is_buy and cur_price >= halfway and p.sl < p.price_open:
                new_sl = round(p.price_open + buffer, info.digits)
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(new_sl), "tp": float(p.tp)}
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[🛡️ BREAK-EVEN] Posición #{p.ticket} ({p.symbol}) asegurada en {new_sl} (Magic: {p.magic}).")
            elif not is_buy and cur_price <= halfway and (p.sl > p.price_open or p.sl == 0):
                new_sl = round(p.price_open - buffer, info.digits)
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(new_sl), "tp": float(p.tp)}
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[🛡️ BREAK-EVEN] Posición #{p.ticket} ({p.symbol}) asegurada en {new_sl} (Magic: {p.magic}).")

            # Fase 2: Trailing Lock al 75% del TP -> Asegurar 50% de ganancia neta
            three_quarters = p.price_open + (dist_total * 0.75) if is_buy else p.price_open - (dist_total * 0.75)
            locked_half = p.price_open + (dist_total * 0.50) if is_buy else p.price_open - (dist_total * 0.50)
            if is_buy and cur_price >= three_quarters and p.sl < locked_half:
                new_sl = round(locked_half, info.digits)
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(new_sl), "tp": float(p.tp)}
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[🏹 TRAILING LOCK] Posición #{p.ticket} ({p.symbol}) asegurando +50% de ganancia en {new_sl}!")
            elif not is_buy and cur_price <= three_quarters and (p.sl > locked_half or p.sl == 0):
                new_sl = round(locked_half, info.digits)
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(new_sl), "tp": float(p.tp)}
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[🏹 TRAILING LOCK] Posición #{p.ticket} ({p.symbol}) asegurando +50% de ganancia en {new_sl}!")

    def run_cycle(self, execute=True):
        # 0A. Gestión de Parciales 50% y Trailing Runner para estrategias direccionales (24/7)
        self.manage_directional_partials_and_trailing()

        # 0B. Gestión de Break-Even para otras posiciones
        self.manage_portfolio_breakeven()

        # 1. Trinity Versión NY SNIPER (Apertura 13:30 a 15:30 UTC | 1 Disparo Único por Activo al Día)
        if self.mode in ['ALL_SNIPER', 'NY_SNIPER', 'TRINITY_SNIPER', 'SNIPER']:
            print("\n>>> [CICLO SNIPER] The Institutional Trinity (Apertura NY 13:30 - 15:30 UTC | 1 Trade/Día)...")
            for sym, cfg in TRINITY_ASSETS.items():
                try:
                    self.strat_trinity_sniper.evaluate(sym, cfg, execute=execute)
                except Exception as e:
                    print(f"[-] Error en Trinity Sniper ({sym}): {e}")

        # 1A. Trinity Versión Londres + NY (07:00 a 21:00 UTC)
        if self.mode in ['ALL', 'ALL_DUAL', 'ALL_LNY', 'TRINITY', 'TRINITY_LNY', 'TRINITY_DUAL']:
            print("\n>>> [CICLO] Evaluando Estrategia 1A: The Institutional Trinity (Londres + NY: 07-21 UTC)...")
            for sym, cfg in TRINITY_ASSETS.items():
                try:
                    self.strat_trinity_lny.evaluate(sym, cfg, execute=execute)
                except Exception as e:
                    print(f"[-] Error en Trinity LNY ({sym}): {e}")

        # 1B. Trinity Versión Solo NY (13:00 a 21:00 UTC)
        if self.mode in ['ALL_DUAL', 'ALL_NY', 'TRINITY_NY', 'TRINITY_DUAL']:
            print("\n>>> [CICLO] Evaluando Estrategia 1B: The Institutional Trinity (Solo Nueva York: 13-21 UTC)...")
            for sym, cfg in TRINITY_ASSETS.items():
                try:
                    self.strat_trinity_ny.evaluate(sym, cfg, execute=execute)
                except Exception as e:
                    print(f"[-] Error en Trinity NY ({sym}): {e}")

        # 2. Stat-Arb Multi-Pair Trading (4 Pares Cointegrados)
        if self.mode in ['ALL', 'ALL_DUAL', 'ALL_LNY', 'ALL_NY', 'ALL_SNIPER', 'NY_SNIPER', 'PAIR']:
            print("\n>>> [CICLO] Evaluando Estrategia 2: Stat-Arb Multi-Pair Trading (4 Pares Cointegrados)...")
            for p_key, cfg in MULTI_PAIRS.items():
                try:
                    self.strat_pair.evaluate_pair(p_key, cfg, execute=execute)
                except Exception as e:
                    print(f"[-] Error en Pair Trading ({p_key}): {e}")

        # 3. Macro COT Squeeze Engine (11 Activos CFTC/CME)
        if self.mode in ['ALL', 'ALL_DUAL', 'ALL_LNY', 'ALL_NY', 'ALL_SNIPER', 'NY_SNIPER', 'COT']:
            print("\n>>> [CICLO] Evaluando Estrategia 3: Macro COT Squeeze Engine (11 Activos CFTC/CME)...")
            for sym, cfg in COT_CONFIG.items():
                try:
                    self.strat_cot.evaluate(sym, cfg, execute=execute)
                except Exception as e:
                    print(f"[-] Error en COT ({sym}): {e}")

        # 4. Suite Avanzada: 6 Estrategias Institucionales con Hedge (CME + IC Markets)
        if self.mode in ['ALL', 'ALL_DUAL', 'ALL_LNY', 'ALL_NY', 'ALL_SNIPER', 'NY_SNIPER', 'HEDGES']:
            print("\n>>> [CICLO] Evaluando Estrategia 4: 6 Coberturas Institucionales CME (Hedges)...")
            try:
                self.strat_hedges.run_all(execute=execute)
            except Exception as e:
                print(f"[-] Error en Coberturas Institucionales: {e}")

    def run_daemon(self):
        print("\n" + "=" * 85)
        print("   INICIANDO EJECUCIÓN CONTINUA 24/7 EN VPS")
        print(f"   Modo Operativo: {self.mode}")
        print(f"   Frecuencia de Escaneo: cada {MONITOR_INTERVAL_SECS} segundos")
        print("   Presione Ctrl + C para detener.")
        print("=" * 85)

        try:
            while True:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{now_str}] Escaneando mercados institucionales ({self.mode})...")
                self.run_cycle(execute=True)
                time.sleep(MONITOR_INTERVAL_SECS)
        except KeyboardInterrupt:
            print("\n[*] Bot maestro detenido de forma segura.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Master Institutional Bot - CME + IC Markets MT5")
    parser.add_argument('--mode', type=str, 
                        choices=['ALL_SNIPER', 'NY_SNIPER', 'TRINITY_SNIPER', 'ALL_DUAL', 'ALL_LNY', 'ALL_NY', 'ALL', 'TRINITY_LNY', 'TRINITY_NY', 'TRINITY_DUAL', 'PAIR', 'COT', 'HEDGES'], 
                        default='ALL_SNIPER',
                        help='Modo: ALL_SNIPER (Trinity Sniper en Apertura NY + Stat-Arb + COT + 6 Hedges), TRINITY_SNIPER, ALL_DUAL, ALL_LNY, ALL_NY, PAIR, COT, HEDGES')
    parser.add_argument('--daemon', action='store_true', help='Ejecución continua 24/7 para VPS')
    parser.add_argument('--audit', action='store_true', help='Auditoría de un solo ciclo en modo simulación (sin órdenes)')
    parser.add_argument('--run-once', action='store_true', help='Ejecución de un solo ciclo con envío de órdenes real')
    args = parser.parse_args()

    bot = MasterPortfolioBot(mode=args.mode)
    if bot.connect():
        if args.daemon:
            bot.run_daemon()
        elif args.audit:
            print(f"\n[AUDITORÍA / SIMULACIÓN] Modo: {args.mode}")
            bot.run_cycle(execute=False)
        else:
            bot.run_cycle(execute=True)
        bot.disconnect()

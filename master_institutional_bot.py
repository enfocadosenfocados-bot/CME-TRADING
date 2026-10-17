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

class MasterPortfolioBot:
    def __init__(self, mode='ALL_DUAL'):
        self.mode = mode.upper()
        # Instanciar todas las suites de estrategias
        self.strat_trinity_lny = InstitutionalTrinityStrategy(session_mode='LNY', risk_pct=TRADE_RISK_PCT)
        self.strat_trinity_ny  = InstitutionalTrinityStrategy(session_mode='NY', risk_pct=TRADE_RISK_PCT)
        self.strat_pair        = MultiPairStatArbStrategy(risk_pct=TRADE_RISK_PCT)
        self.strat_cot         = MacroCOTSqueezeStrategy(risk_pct=TRADE_RISK_PCT)
        self.strat_hedges      = AdvancedHedgeStrategies(risk_pct=TRADE_RISK_PCT)
        self.connected = False

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

    def manage_portfolio_breakeven(self):
        """Mueve automáticamente a Break-Even cualquier trade que alcance el 50% de ganancia hacia su TP.
        Protege tanto las órdenes con nueva taxonomía (71*, 72*, 73*, 74*, 75*) como las órdenes existentes (777*).
        """
        positions = mt5.positions_get()
        if not positions:
            return
        for p in positions:
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

            if is_buy and cur_price >= halfway and p.sl < p.price_open:
                new_sl = round(p.price_open + buffer, info.digits)
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(new_sl), "tp": float(p.tp)}
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[🛡️ BREAK-EVEN] Posición #{p.ticket} ({p.symbol}) asegurada con ganancia protegida en {new_sl} (Magic: {p.magic}).")
            elif not is_buy and cur_price <= halfway and (p.sl > p.price_open or p.sl == 0):
                new_sl = round(p.price_open - buffer, info.digits)
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(new_sl), "tp": float(p.tp)}
                res = mt5.order_send(req)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[🛡️ BREAK-EVEN] Posición #{p.ticket} ({p.symbol}) asegurada con ganancia protegida en {new_sl} (Magic: {p.magic}).")

    def run_cycle(self, execute=True):
        self.manage_portfolio_breakeven()

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
        if self.mode in ['ALL', 'ALL_DUAL', 'ALL_LNY', 'ALL_NY', 'PAIR']:
            print("\n>>> [CICLO] Evaluando Estrategia 2: Stat-Arb Multi-Pair Trading (4 Pares Cointegrados)...")
            for p_key, cfg in MULTI_PAIRS.items():
                try:
                    self.strat_pair.evaluate_pair(p_key, cfg, execute=execute)
                except Exception as e:
                    print(f"[-] Error en Pair Trading ({p_key}): {e}")

        # 3. Macro COT Squeeze Engine (11 Activos CFTC/CME)
        if self.mode in ['ALL', 'ALL_DUAL', 'ALL_LNY', 'ALL_NY', 'COT']:
            print("\n>>> [CICLO] Evaluando Estrategia 3: Macro COT Squeeze Engine (11 Activos CFTC/CME)...")
            for sym, cfg in COT_CONFIG.items():
                try:
                    self.strat_cot.evaluate(sym, cfg, execute=execute)
                except Exception as e:
                    print(f"[-] Error en COT ({sym}): {e}")

        # 4. Suite Avanzada: 6 Estrategias Institucionales con Hedge (CME + IC Markets)
        if self.mode in ['ALL', 'ALL_DUAL', 'ALL_LNY', 'ALL_NY', 'HEDGES']:
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
                        choices=['ALL_DUAL', 'ALL_LNY', 'ALL_NY', 'ALL', 'TRINITY_LNY', 'TRINITY_NY', 'TRINITY_DUAL', 'PAIR', 'COT', 'HEDGES'], 
                        default='ALL_DUAL',
                        help='Modo: ALL_DUAL (todas con LNY y NY), ALL_LNY (todas con LNY), ALL_NY (todas con NY), TRINITY_LNY, TRINITY_NY, PAIR, COT, HEDGES')
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

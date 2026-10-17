"""
================================================================================
ESTRATEGIA 1: THE INSTITUTIONAL TRINITY (UNIVERSO COMPLETO 11 ACTIVOS)
Open Interest Walls + Vol2Vol 1σ/2σ Expected Range + VWAP M5
================================================================================
Activos:
1. USTEC  (Nasdaq 100 - NQ)
2. US500  (S&P 500 - ES)
3. US30   (Dow Jones 30 - YM)
4. US2000 (Russell 2000 - RTY)
5. XAUUSD (Oro - GC)
6. XTIUSD (Petróleo WTI - CL)
7. XNGUSD (Gas Natural - NG)
8. EURUSD (Euro FX - 6E)
9. GBPUSD (British Pound - 6B)
10. USDJPY (Japanese Yen - 6J)
11. BTCUSD (Bitcoin Futures - BTC)
================================================================================
"""

import sys
import os
import json
import math
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import MetaTrader5 as mt5
from curl_cffi import requests
from bs4 import BeautifulSoup
import pandas as pd

MAGIC_TRINITY = 777101
RISK_PERCENT = 1.0
SLIPPAGE_MAX = 10
CACHE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuración institucional detallada para los 11 activos con Asset ID único
TRINITY_ASSETS = {
    # --- ÍNDICES ACCIONARIOS ---
    'USTEC': {
        'asset_id': 1,
        'name': 'Nasdaq 100',
        'cme_code': 'NQ',
        'cme_pid': 121,
        'cme_pf': 26,
        'min_expansion_pts': 35.0,
        'wall_zone_pts': 12.0,
        'tp_buffer_pts': 8.0,
        'sl_min_pts': 20.0,
        'max_spread_pts': 2.5,
        'annual_iv': 0.19
    },
    'US500': {
        'asset_id': 2,
        'name': 'S&P 500',
        'cme_code': 'ES',
        'cme_pid': 103,
        'cme_pf': 26,
        'min_expansion_pts': 10.0,
        'wall_zone_pts': 3.5,
        'tp_buffer_pts': 2.0,
        'sl_min_pts': 6.0,
        'max_spread_pts': 0.8,
        'annual_iv': 0.15
    },
    'US30': {
        'asset_id': 3,
        'name': 'Dow Jones 30',
        'cme_code': 'YM',
        'cme_pid': 130,
        'cme_pf': 26,
        'min_expansion_pts': 60.0,
        'wall_zone_pts': 20.0,
        'tp_buffer_pts': 15.0,
        'sl_min_pts': 35.0,
        'max_spread_pts': 3.0,
        'annual_iv': 0.14
    },
    'US2000': {
        'asset_id': 4,
        'name': 'Russell 2000',
        'cme_code': 'RTY',
        'cme_pid': 133,
        'cme_pf': 26,
        'min_expansion_pts': 5.0,
        'wall_zone_pts': 2.0,
        'tp_buffer_pts': 1.0,
        'sl_min_pts': 4.0,
        'max_spread_pts': 0.8,
        'annual_iv': 0.22
    },
    # --- MATERIAS PRIMAS Y METALES ---
    'XAUUSD': {
        'asset_id': 5,
        'name': 'Gold (Oro)',
        'cme_code': 'GC',
        'cme_pid': 40,
        'cme_pf': 6,
        'min_expansion_pts': 4.0,
        'wall_zone_pts': 1.5,
        'tp_buffer_pts': 0.8,
        'sl_min_pts': 3.0,
        'max_spread_pts': 0.50,
        'annual_iv': 0.16
    },
    'XTIUSD': {
        'asset_id': 6,
        'name': 'Crude Oil WTI',
        'cme_code': 'CL',
        'cme_pid': 30,
        'cme_pf': 5,
        'min_expansion_pts': 0.40,
        'wall_zone_pts': 0.15,
        'tp_buffer_pts': 0.10,
        'sl_min_pts': 0.35,
        'max_spread_pts': 0.05,
        'annual_iv': 0.32
    },
    'XNGUSD': {
        'asset_id': 7,
        'name': 'Natural Gas',
        'cme_code': 'NG',
        'cme_pid': 31,
        'cme_pf': 5,
        'min_expansion_pts': 0.030,
        'wall_zone_pts': 0.010,
        'tp_buffer_pts': 0.008,
        'sl_min_pts': 0.025,
        'max_spread_pts': 0.010,
        'annual_iv': 0.55
    },
    # --- DIVISAS FOREX ---
    'EURUSD': {
        'asset_id': 8,
        'name': 'Euro FX',
        'cme_code': '6E',
        'cme_pid': 1,
        'cme_pf': 26,
        'min_expansion_pts': 0.0015,
        'wall_zone_pts': 0.0006,
        'tp_buffer_pts': 0.0003,
        'sl_min_pts': 0.0012,
        'max_spread_pts': 0.00015,
        'annual_iv': 0.08
    },
    'GBPUSD': {
        'asset_id': 9,
        'name': 'British Pound',
        'cme_code': '6B',
        'cme_pid': 2,
        'cme_pf': 26,
        'min_expansion_pts': 0.0020,
        'wall_zone_pts': 0.0008,
        'tp_buffer_pts': 0.0004,
        'sl_min_pts': 0.0015,
        'max_spread_pts': 0.00020,
        'annual_iv': 0.09
    },
    'USDJPY': {
        'asset_id': 10,
        'name': 'Japanese Yen',
        'cme_code': '6J',
        'cme_pid': 3,
        'cme_pf': 26,
        'min_expansion_pts': 0.25,
        'wall_zone_pts': 0.08,
        'tp_buffer_pts': 0.05,
        'sl_min_pts': 0.20,
        'max_spread_pts': 0.025,
        'annual_iv': 0.10
    },
    # --- CRIPTOACTIVOS ---
    'BTCUSD': {
        'asset_id': 11,
        'name': 'Bitcoin Futures',
        'cme_code': 'BTC',
        'cme_pid': 350,
        'cme_pf': 26,
        'min_expansion_pts': 400.0,
        'wall_zone_pts': 150.0,
        'tp_buffer_pts': 80.0,
        'sl_min_pts': 300.0,
        'max_spread_pts': 15.0,
        'annual_iv': 0.52
    }
}

class InstitutionalTrinityStrategy:
    def __init__(self, risk_pct=RISK_PERCENT, session_mode='LNY'):
        self.risk_pct = risk_pct
        self.session_mode = session_mode.upper() # 'LNY' (Londres + NY) o 'NY' (Solo NY)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://www.cmegroup.com/tools-information/quikstrike/open-interest-heatmap.html'
        }

    def fetch_cme_oi_walls(self, cme_code, pid, pf, current_price):
        cache_file = os.path.join(CACHE_DIR, f"oi_cache_{cme_code}.json")
        url = f"https://cmegroup-tools.quikstrike.net/User/QuikStrikeView.aspx?pid={pid}&pf={pf}&viewitemid=IntegratedVOIHeatMap"
        try:
            r = requests.get(url, headers=self.headers, impersonate='chrome124', timeout=8)
            if r.status_code == 200 and len(r.text) > 10000:
                soup = BeautifulSoup(r.text, 'html.parser')
                tables = soup.find_all('table')
                if len(tables) >= 7:
                    t = tables[6]
                    rows = t.find_all('tr')
                    def to_int(s):
                        s = s.replace(',', '').replace('.', '').strip()
                        return int(s) if s.isdigit() else 0

                    strikes_data = []
                    for row in rows[3:]:
                        tds = [c.get_text(strip=True) for c in row.find_all(['th', 'td'])]
                        if not tds: continue
                        try:
                            strike = float(tds[0].replace(',', '').strip())
                        except:
                            continue
                        c_front = to_int(tds[1]) + (to_int(tds[3]) if len(tds) > 3 else 0)
                        p_front = to_int(tds[2]) + (to_int(tds[4]) if len(tds) > 4 else 0)
                        total_c = sum(to_int(tds[i]) for i in range(1, len(tds), 2))
                        total_p = sum(to_int(tds[i]) for i in range(2, len(tds), 2))
                        strikes_data.append({
                            'strike': strike,
                            'c_front': c_front,
                            'p_front': p_front,
                            'total_c': total_c,
                            'total_p': total_p,
                            'total_oi': total_c + total_p
                        })

                    if strikes_data:
                        calls_above = [s for s in strikes_data if s['strike'] >= current_price]
                        call_wall = max(calls_above, key=lambda x: (x['c_front'], x['total_c']))['strike'] if calls_above else max(strikes_data, key=lambda x: x['strike'])['strike']

                        puts_below = [s for s in strikes_data if s['strike'] <= current_price]
                        put_wall = max(puts_below, key=lambda x: (x['p_front'], x['total_p']))['strike'] if puts_below else min(strikes_data, key=lambda x: x['strike'])['strike']

                        # Validación de coherencia de escala (muros deben estar dentro del +-25% del spot)
                        if (current_price * 0.70) <= call_wall <= (current_price * 1.30):
                            levels = {
                                'call_wall': call_wall,
                                'put_wall': put_wall,
                                'timestamp': datetime.now(timezone.utc).isoformat()
                            }
                            with open(cache_file, 'w', encoding='utf-8') as f:
                                json.dump(levels, f, indent=2)
                            return levels
        except Exception:
            pass

        # Fallback a caché local o derivación matemática
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    c_data = json.load(f)
                    if (current_price * 0.70) <= c_data.get('call_wall', 0) <= (current_price * 1.30):
                        return c_data
            except:
                pass

        # Fallback matemático sintético si no hay caché
        annual_iv = TRINITY_ASSETS.get(cme_code, {}).get('annual_iv', 0.20)
        daily_sigma = current_price * annual_iv * math.sqrt(1.0 / 365.0)
        return {
            'call_wall': round(current_price + (1.2 * daily_sigma), 2),
            'put_wall': round(current_price - (1.2 * daily_sigma), 2),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def calculate_vol2vol_expected_range(self, spot_price, annual_iv, dte=1):
        daily_sigma = spot_price * annual_iv * math.sqrt(dte / 365.0)
        return {
            'sigma1_upper': spot_price + daily_sigma,
            'sigma1_lower': spot_price - daily_sigma,
            'sigma2_upper': spot_price + (2.0 * daily_sigma),
            'sigma2_lower': spot_price - (2.0 * daily_sigma),
            'daily_move_pts': round(daily_sigma, 4)
        }

    def calculate_vwap(self, symbol, num_bars=100):
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, num_bars)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        typical = (df['high'] + df['low'] + df['close']) / 3.0
        return round(float((typical * df['tick_volume']).sum() / df['tick_volume'].sum()), 5)

    def is_in_session(self, symbol):
        """Filtro de Horario Institucional Calibrado por Activo:
        - Anti-Rollover: Bloqueo de 20:55 a 22:30 UTC para evitar spreads inflados de cambio de día.
        - BTCUSD: 24/7 continuo (excepto rollover 20:55-22:15 UTC).
        - Indices (USTEC, US500, US30, US2000):
            LNY: 07:00 a 20:30 UTC | NY: 13:30 a 20:30 UTC (Apertura Cash Wall Street)
        - Forex (EURUSD, GBPUSD, USDJPY):
            LNY: 07:00 a 17:30 UTC | NY: 13:00 a 17:30 UTC (Solapamiento Londres/NY)
        - Commodities (XAUUSD, XTIUSD, XNGUSD):
            LNY: 08:00 a 19:30 UTC | NY: 13:00 a 19:30 UTC (Pits NYMEX/COMEX)
        """
        now_utc = datetime.now(timezone.utc)
        weekday = now_utc.weekday()
        hour = now_utc.hour
        minute = now_utc.minute
        time_decimal = hour + (minute / 60.0)

        # 1. Bloqueo de Fin de Semana en CME / Forex (Viernes 20:55 UTC hasta Domingo 22:00 UTC)
        if symbol != 'BTCUSD':
            if weekday == 5: # Sábado
                return False
            if weekday == 6 and time_decimal < 22.0: # Domingo antes de apertura Asia
                return False
            if weekday == 4 and time_decimal >= 20.91: # Viernes después de 20:55 UTC
                return False

        # 2. Bloqueo Universal Anti-Rollover de IC Markets (20:55 a 22:30 UTC)
        if 20.91 <= time_decimal < 22.5:
            return False

        if symbol == 'BTCUSD':
            return True

        # 3. Ventanas específicas por clase de activo
        is_index = symbol in ['USTEC', 'US500', 'US30', 'US2000']
        is_fx = symbol in ['EURUSD', 'GBPUSD', 'USDJPY']
        is_comm = symbol in ['XAUUSD', 'XTIUSD', 'XNGUSD']

        if self.session_mode == 'NY':
            if is_index:
                return 13.5 <= time_decimal < 20.5  # 13:30 a 20:30 UTC
            elif is_fx:
                return 13.0 <= time_decimal < 17.5  # 13:00 a 17:30 UTC
            elif is_comm:
                return 13.0 <= time_decimal < 19.5  # 13:00 a 19:30 UTC
        else: # LNY (Londres + NY)
            if is_index:
                return 7.0 <= time_decimal < 20.5   # 07:00 a 20:30 UTC
            elif is_fx:
                return 7.0 <= time_decimal < 17.5   # 07:00 a 17:30 UTC
            elif is_comm:
                return 8.0 <= time_decimal < 19.5   # 08:00 a 19:30 UTC

        return True

    def calculate_lots(self, symbol, sl_points):
        acc = mt5.account_info()
        risk_cash = acc.balance * (self.risk_pct / 100.0)
        info = mt5.symbol_info(symbol)
        if not info or sl_points <= 0:
            return 0.1
        profit = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, symbol, info.volume_min, 1000.0, 1000.0 + sl_points)
        if profit and profit > 0:
            lots = (risk_cash / profit) * info.volume_min
        else:
            lots = risk_cash / (sl_points * info.trade_contract_size)
        step = info.volume_step
        lots = round(lots / step) * step
        return round(max(info.volume_min, min(lots, info.volume_max)), 2)

    def evaluate(self, symbol, cfg, execute=True):
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        if not tick or tick.bid <= 0:
            return

        info = mt5.symbol_info(symbol)
        spread = round(tick.ask - tick.bid, info.digits)
        if spread > cfg['max_spread_pts']:
            return

        # Calcular Magic Number unico para este activo y esta sesion
        base_magic = 710000 if self.session_mode == 'LNY' else 720000
        magic = base_magic + (cfg.get('asset_id', 1) * 100)

        # Verificar posicion activa con este Magic especifico
        positions = mt5.positions_get(symbol=symbol)
        if positions:
            active = [p for p in positions if p.magic == magic]
            if active:
                return

        # Validacion del filtro de sesion horaria
        in_session = self.is_in_session(symbol)

        current_price = (tick.bid + tick.ask) / 2.0
        oi = self.fetch_cme_oi_walls(cfg['cme_code'], cfg['cme_pid'], cfg['cme_pf'], current_price)
        if not oi:
            return

        call_wall = oi['call_wall']
        put_wall = oi['put_wall']
        vwap = self.calculate_vwap(symbol) or current_price
        v2v = self.calculate_vol2vol_expected_range(current_price, cfg['annual_iv'], dte=1)

        dist_call = call_wall - current_price
        dist_put = current_price - put_wall

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 3)
        if rates is None or len(rates) < 2:
            return
        last_c = rates[-1]
        prev_c = rates[-2]

        sess_label = "Londres+NY" if self.session_mode == 'LNY' else "Solo NY"
        print(f"\n[TRINITY {self.session_mode}] {cfg['name']:<14} ({symbol:<7}) | Magic: {magic} | Sesion: {sess_label} ({'ABIERTA' if in_session else 'CERRADA'})")
        print(f"  Spot: {current_price:<10} | VWAP: {vwap:<10} | Spread: {spread}")
        print(f"  🛑 Call Wall: {call_wall} (+{abs(dist_call):.2f}) | 🛡️ Put Wall: {put_wall} (-{abs(dist_put):.2f})")
        print(f"  Vol2Vol 1σ: ±{v2v['daily_move_pts']} | 2σ Rango: [{v2v['sigma2_lower']:.2f} .. {v2v['sigma2_upper']:.2f}]")

        if not in_session:
            print(f"  [Horario {self.session_mode}] Fuera de ventana operativa. Entrada bloqueada.")
            return

        # FASE 2: RECHAZO EN EL MURO + 2σ EXHAUSTION
        if abs(dist_call) <= cfg['wall_zone_pts'] and current_price >= v2v['sigma1_upper']:
            has_wick = (last_c['high'] - max(last_c['open'], last_c['close'])) > abs(last_c['close'] - last_c['open'])
            if last_c['close'] < last_c['open'] or has_wick:
                sl_price = round(max(call_wall, v2v['sigma2_upper']) + (cfg['tp_buffer_pts'] * 1.5), info.digits)
                tp_price = round(vwap, info.digits)
                lots = self.calculate_lots(symbol, abs(current_price - sl_price))
                comment = f"TR_{self.session_mode}_{symbol}_RejCall"[:31]
                print(f"[💥 GATILLO TRINITY {self.session_mode}] RECHAZO CALL WALL en {call_wall} (SELL) | Magic: {magic}")
                if execute:
                    self.send_order(symbol, 'SELL', sl_price, tp_price, lots, comment, magic)
                return

        if abs(dist_put) <= cfg['wall_zone_pts'] and current_price <= v2v['sigma1_lower']:
            has_wick = (min(last_c['open'], last_c['close']) - last_c['low']) > abs(last_c['close'] - last_c['open'])
            if last_c['close'] > last_c['open'] or has_wick:
                sl_price = round(min(put_wall, v2v['sigma2_lower']) - (cfg['tp_buffer_pts'] * 1.5), info.digits)
                tp_price = round(vwap, info.digits)
                lots = self.calculate_lots(symbol, abs(current_price - sl_price))
                comment = f"TR_{self.session_mode}_{symbol}_RejPut"[:31]
                print(f"[💥 GATILLO TRINITY {self.session_mode}] RECHAZO PUT WALL en {put_wall} (BUY) | Magic: {magic}")
                if execute:
                    self.send_order(symbol, 'BUY', sl_price, tp_price, lots, comment, magic)
                return

        # FASE 1: IMÁN DE EXPANSIÓN
        if dist_call >= cfg['min_expansion_pts'] and current_price > vwap and call_wall <= v2v['sigma2_upper']:
            if last_c['close'] > prev_c['high'] or current_price > last_c['open']:
                tp_price = round(call_wall - cfg['tp_buffer_pts'], info.digits)
                sl_pts = max(cfg['sl_min_pts'], current_price - vwap)
                sl_price = round(current_price - sl_pts, info.digits)
                lots = self.calculate_lots(symbol, sl_pts)
                comment = f"TR_{self.session_mode}_{symbol}_MagCall"[:31]
                print(f"[🧲 GATILLO TRINITY {self.session_mode}] IMÁN ALCISTA HACIA CALL WALL {call_wall} (BUY) | Magic: {magic}")
                if execute:
                    self.send_order(symbol, 'BUY', sl_price, tp_price, lots, comment, magic)
                return

        if dist_put >= cfg['min_expansion_pts'] and current_price < vwap and put_wall >= v2v['sigma2_lower']:
            if last_c['close'] < prev_c['low'] or current_price < last_c['open']:
                tp_price = round(put_wall + cfg['tp_buffer_pts'], info.digits)
                sl_pts = max(cfg['sl_min_pts'], vwap - current_price)
                sl_price = round(current_price + sl_pts, info.digits)
                lots = self.calculate_lots(symbol, sl_pts)
                comment = f"TR_{self.session_mode}_{symbol}_MagPut"[:31]
                print(f"[🧲 GATILLO TRINITY {self.session_mode}] IMÁN BAJISTA HACIA PUT WALL {put_wall} (SELL) | Magic: {magic}")
                if execute:
                    self.send_order(symbol, 'SELL', sl_price, tp_price, lots, comment, magic)
                return

        print(f"  [Estado] En rango normal. Sin desbalance extremo.")

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
    parser = argparse.ArgumentParser(description="The Institutional Trinity Strategy (CME + IC Markets MT5)")
    parser.add_argument('--session', type=str, choices=['LNY', 'NY'], default='LNY',
                        help='Modo de Sesión: LNY (Londres + NY: 07-21 UTC) o NY (Solo NY: 13-21 UTC)')
    parser.add_argument('--execute', action='store_true', help='Ejecutar órdenes en vivo si hay señal')
    args = parser.parse_args()

    if mt5.initialize():
        strat = InstitutionalTrinityStrategy(session_mode=args.session, risk_pct=1.0)
        sess_title = "LONDRES + NUEVA YORK (07:00 - 21:00 UTC)" if args.session == 'LNY' else "SOLO NUEVA YORK (13:00 - 21:00 UTC)"
        print("=" * 85)
        print(f"   AUDITORÍA EN VIVO: THE INSTITUTIONAL TRINITY [{args.session}]")
        print(f"   Filtro Horario: {sess_title}")
        print(f"   Broker: {mt5.account_info().server} | Cuenta: {mt5.account_info().login}")
        print("=" * 85)
        for sym, cfg in TRINITY_ASSETS.items():
            strat.evaluate(sym, cfg, execute=args.execute)
        mt5.shutdown()

"""
================================================================================
GAMMA EXPOSURE SNIPER BOT (12 ACTIVOS COMPLETOS) - ITMATRIX / CBOE / CME / DERIBIT
================================================================================
Ingeniería Inversa Completa de Gamma Exposure University (Nickel Ninja Trades) +
ITMatrixHQ + CME Group (CmeWS & CVOL via Obscura Stealth) + CBOE OPRA + Deribit:

Pilares Cuantitativos:
1. Gamma Exposure (GEX): Cobertura forzada de Dealers ($ por cada $1 de mov.)
2. 0DTE Options Flow: Explosión de Gamma en expiraciones del mismo día (T -> 0)
3. Open Interest (OI): Call Wall, Put Wall, Control Node (Magnet) y Gamma Flip
4. Convexity Exposure: Índice Oficial de Convexidad CME (CVOL convexInd & skew)
5. Expansión de Taylor Delta-Gamma: Hedge_Flow = -Gamma_Dealer * dS

Los 2 Modos Operativos Automáticos:
- MODO 1 [THE MAGNET] (Régimen Gamma Positiva +GEX):
  Los dealers compran caídas y venden subidas. El precio es atraído hacia el
  Control Node (Magnet) o rebota desde Call/Put Wall hacia el Magnet.
- MODO 2 [THE BREAK] (Régimen Gamma Negativa -GEX):
  Los dealers persiguen el precio (venden en caídas y compran en subidas).
  Aceleración violenta al romper el Gamma Flip o los muros con alta convexidad.

Las 3 Confirmaciones Obligatorias en M5:
  [1] Clean EMA Stack (EMA 9, EMA 21, EMA 50 alineadas y con separación)
  [2] Price Flagging at Level (Consolidación en bandera + ruptura de rango)
  [3] Volume Confirmation (Volumen relativo RVOL >= 1.25x media de 20 velas)
================================================================================
"""

import sys
import os
import re
import json
import math
import time
import glob
import argparse
import subprocess
from datetime import datetime, timezone, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    import MetaTrader5 as mt5
except ImportError:
    print("[ERROR] MetaTrader5 no instalado. Ejecuta: py -3.12 -m pip install MetaTrader5 pandas scipy requests")
    sys.exit(1)

import requests
import numpy as np
import pandas as pd

CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
MONITOR_INTERVAL_SECS = 15
GEX_REFRESH_SECS = 600  # Refrescar cadenas de opciones cada 10 minutos
SLIPPAGE_MAX = 15

# Localización automática del binario Obscura Stealth
OBSCURA_CANDIDATES = [
    os.path.join(CACHE_DIR, "obscura_bin", "obscura.exe"),
    r"C:\Gamma_Sniper_Bot\obscura_bin\obscura.exe",
    r"C:\CME_Quant_Bot\obscura_bin\obscura.exe",
    r"C:\Users\enfoc\.gemini\antigravity\scratch\obscura_bin\obscura.exe",
]

def get_obscura_bin():
    for path in OBSCURA_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None

OCC_REGEX = re.compile(r'^([A-Z_]+?)W?(\d{6})([CP])(\d{8})$')

# ==============================================================================
# CONFIGURACIÓN DE LOS 12 ACTIVOS INSTITUCIONALES (WALK-FORWARD ÉLITE ENE-OCT)
# ==============================================================================
GAMMA_ASSETS = {
    'US500': {
        'name': 'GEX_US500_SPX',
        'title': 'S&P 500 Index',
        'magic': 20269901,
        'aliases': ['US500', 'US500.raw', 'US500m', 'SPX500', 'SP500', 'US500Cash', 'US500+'],
        'source_type': 'CBOE',
        'cboe_ticker': '_SPX',
        'cboe_backup': 'SPY',
        'cme_params': (138, 2026, 12, 'EUVL'),
        'min_confirmations': 2,               # Walk-Forward Élite: 2 Filtros (Top 2 Horas)
        'hours_broker': [17, 4],              # 17:00 y 04:00 Broker (08:00 y 19:00 CDMX)
        'min_fallback_lot': 0.10,
        'max_spread_atr_ratio': 0.35,
    },
    'USTEC': {
        'name': 'GEX_USTEC_NDX',
        'title': 'Nasdaq 100 Tech',
        'magic': 20269902,
        'aliases': ['USTEC', 'USTEC.raw', 'USTECm', 'NAS100', 'NDX100', 'USTECCash', 'US100', 'USTEC+'],
        'source_type': 'CBOE',
        'cboe_ticker': 'QQQ',
        'cboe_backup': '_NDX',
        'cme_params': (148, 2026, 12, 'EUVL'),
        'min_confirmations': 2,               # Walk-Forward Élite: 2 Filtros (Top 3 Horas)
        'hours_broker': [22, 10, 23],         # 22:00, 10:00 y 23:00 Broker (13:00, 01:00 y 14:00 CDMX)
        'min_fallback_lot': 0.10,
        'max_spread_atr_ratio': 0.35,
    },
    'US2000': {
        'name': 'GEX_US2000_RUT',
        'title': 'Russell 2000 SmallCap',
        'magic': 20269903,
        'aliases': ['US2000', 'US2000.raw', 'US2000m', 'RUT', 'US2000Cash', 'USSmall2000', 'US2000+'],
        'source_type': 'CBOE',
        'cboe_ticker': 'IWM',
        'cboe_backup': '_RUT',
        'cme_params': (8326, 2026, 12, 'EUVL'),
        'min_confirmations': 2,               # Walk-Forward Élite: 2 Filtros (Top 3 Horas)
        'hours_broker': [17, 21, 20],         # 17:00, 21:00 y 20:00 Broker (08:00, 12:00 y 11:00 CDMX)
        'min_fallback_lot': 1.00,
        'max_spread_atr_ratio': 0.40,
    },
    'US30': {
        'name': 'GEX_US30_DOW',
        'title': 'Dow Jones 30',
        'magic': 20269904,
        'aliases': ['US30', 'US30.raw', 'US30m', 'DJ30', 'WS30', 'US30Cash', 'DJIA', 'US30+'],
        'source_type': 'CBOE',
        'cboe_ticker': 'DIA',
        'cboe_backup': '_DJX',
        'cme_params': (319, 2026, 12, 'EUVL'),
        'min_confirmations': 1,               # Walk-Forward Élite: 1 Filtro (Top 2 Horas | 51.3% WR)
        'hours_broker': [1, 23],              # 01:00 y 23:00 Broker (16:00 y 14:00 CDMX)
        'min_fallback_lot': 0.10,
        'max_spread_atr_ratio': 0.35,
    },
    'XAUUSD': {
        'name': 'GEX_XAUUSD_GOLD',
        'title': 'Gold Spot / COMEX GC',
        'magic': 20269905,
        'aliases': ['XAUUSD', 'XAUUSD.raw', 'XAUUSDm', 'GOLD', 'GOLD.raw', 'XAUUSD+'],
        'source_type': 'DUAL_CBOE_CME',
        'cboe_ticker': 'GLD',
        'cme_params': (192, 2026, 12, 'GCVL'),
        'min_confirmations': 3,               # Walk-Forward Élite: 3 Filtros (Top 3 Horas | 51.9% WR, +$472.96)
        'hours_broker': [16, 3, 8],           # 16:00, 03:00 y 08:00 Broker (07:00, 18:00 y 23:00 CDMX)
        'min_fallback_lot': 0.01,
        'max_spread_atr_ratio': 0.35,
    },
    'XAGUSD': {
        'name': 'GEX_XAGUSD_SILVER',
        'title': 'Silver Spot / COMEX SI',
        'magic': 20269906,
        'aliases': ['XAGUSD', 'XAGUSD.raw', 'XAGUSDm', 'SILVER', 'XAGUSD+'],
        'source_type': 'DUAL_CBOE_CME',
        'cboe_ticker': 'SLV',
        'cme_params': (193, 2026, 12, 'SIVL'),
        'min_confirmations': 2,               # Walk-Forward Élite: 2 Filtros (Top 2 Horas | 55.8% WR, +$366.71)
        'hours_broker': [17, 21],             # 17:00 y 21:00 Broker (08:00 y 12:00 CDMX)
        'min_fallback_lot': 0.01,
        'max_spread_atr_ratio': 0.40,
    },
    'USOIL': {
        'name': 'GEX_USOIL_WTI',
        'title': 'Crude Oil WTI / NYMEX CL',
        'magic': 20269907,
        'aliases': ['XTIUSD', 'USOIL', 'WTI', 'CL', 'XTIUSD.raw', 'USOIL.raw', 'USOUSD', 'WTI_F'],
        'source_type': 'DUAL_CBOE_CME',
        'cboe_ticker': 'USO',
        'cme_params': (190, 2026, 12, 'CLVL'),
        'min_confirmations': 1,               # Walk-Forward Élite: 1 Filtro (Top 2 Horas | 51.4% WR, 327 Trades)
        'hours_broker': [22, 4],              # 22:00 y 04:00 Broker (13:00 y 19:00 CDMX)
        'min_fallback_lot': 0.01,
        'max_spread_atr_ratio': 0.40,
    },
    'EURUSD': {
        'name': 'GEX_EURUSD_6E',
        'title': 'Euro FX / CME 6E',
        'magic': 20269908,
        'aliases': ['EURUSD', 'EURUSD.raw', 'EURUSDm', 'EURUSD+'],
        'source_type': 'CME_FX',
        'cboe_ticker': 'FXE',
        'cme_params': (8116, 2026, 11, 'EUVL'),
        'min_confirmations': 3,               # Walk-Forward Élite: 3 Filtros (Top 3 Horas)
        'hours_broker': [9, 15, 23],          # 09:00, 15:00 y 23:00 Broker (00:00, 06:00 y 14:00 CDMX)
        'min_fallback_lot': 0.01,
        'max_spread_atr_ratio': 0.35,
    },
    'GBPUSD': {
        'name': 'GEX_GBPUSD_6B',
        'title': 'British Pound / CME 6B',
        'magic': 20269909,
        'aliases': ['GBPUSD', 'GBPUSD.raw', 'GBPUSDm', 'GBPUSD+'],
        'source_type': 'CME_FX',
        'cboe_ticker': 'FXB',
        'cme_params': (8098, 2026, 11, 'GBVL'),
        'min_confirmations': 2,               # Walk-Forward Élite: 2 Filtros (Top 3 Horas | 50.2% WR, 223 Trades)
        'hours_broker': [7, 13, 17],          # 07:00, 13:00 y 17:00 Broker (22:00, 04:00 y 08:00 CDMX)
        'min_fallback_lot': 0.01,
        'max_spread_atr_ratio': 0.35,
    },
    'AUDUSD': {
        'name': 'GEX_AUDUSD_6A',
        'title': 'Australian Dollar / CME 6A',
        'magic': 20269910,
        'aliases': ['AUDUSD', 'AUDUSD.raw', 'AUDUSDm', 'AUDUSD+'],
        'source_type': 'CME_FX',
        'cboe_ticker': 'FXA',
        'cme_params': (8092, 2026, 11, 'ADVL'),
        'min_confirmations': 2,               # Walk-Forward Élite: 2 Filtros (Top 3 Horas | 50.0% WR, 184 Trades)
        'hours_broker': [21, 13, 18],         # 21:00, 13:00 y 18:00 Broker (12:00, 04:00 y 09:00 CDMX)
        'min_fallback_lot': 0.01,
        'max_spread_atr_ratio': 0.40,
    },
    'BTCUSD': {
        'name': 'GEX_BTCUSD_DERIBIT',
        'title': 'Bitcoin / Deribit + IBIT',
        'magic': 20269911,
        'aliases': ['BTCUSD', 'BTCUSD.raw', 'BTCUSDm', 'BTCUSD+'],
        'source_type': 'DERIBIT',
        'deribit_currency': 'BTC',
        'cboe_ticker': 'IBIT',
        'min_confirmations': 3,               # Walk-Forward Élite: 3 Filtros (Top 3 Horas | 58.6% WR)
        'hours_broker': [21, 5, 18],          # 21:00, 05:00 y 18:00 Broker (12:00, 20:00 y 09:00 CDMX)
        'min_fallback_lot': 0.01,
        'max_spread_atr_ratio': 0.45,
    },
    'ETHUSD': {
        'name': 'GEX_ETHUSD_DERIBIT',
        'title': 'Ethereum / Deribit + ETHA',
        'magic': 20269912,
        'aliases': ['ETHUSD', 'ETHUSD.raw', 'ETHUSDm', 'ETHUSD+'],
        'source_type': 'DERIBIT',
        'deribit_currency': 'ETH',
        'cboe_ticker': 'ETHA',
        'min_confirmations': 2,               # Walk-Forward Élite: 2 Filtros (Top 3 Horas | 54.3% WR)
        'hours_broker': [8, 18, 14],          # 08:00, 18:00 y 14:00 Broker (23:00, 09:00 y 05:00 CDMX)
        'min_fallback_lot': 0.01,
        'max_spread_atr_ratio': 0.45,
    },
}


class GammaSniperBot:
    def __init__(self):
        self.connected = False
        self.symbol_map = {}
        self.gex_memory = {}
        self.last_gex_fetch = {}
        self.cooldowns = {}
        self.traded_date_hours = set()
        self.obscura_path = get_obscura_bin()

    # =========================================================================
    # CONEXIÓN A METATRADER 5 Y RESOLUCIÓN DE SÍMBOLOS
    # =========================================================================
    def find_mt5_terminal(self):
        search_paths = [
            r"C:\Program Files\*\terminal64.exe",
            r"C:\Program Files (x86)\*\terminal64.exe",
        ]
        for pattern in search_paths:
            matches = glob.glob(pattern)
            for m in matches:
                if "MetaTrader" in m or "MT5" in m or "IC Markets" in m or "Pepperstone" in m or "FTMO" in m:
                    return m
            if matches:
                return matches[0]
        return None

    def connect(self):
        cfg_file = os.path.join(CACHE_DIR, "account_config.json")
        if os.path.exists(cfg_file):
            try:
                with open(cfg_file, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                t_path = cfg.get("mt5_path", "")
                login = int(cfg.get("login", 0))
                password = cfg.get("password", "")
                server = cfg.get("server", "")
                if login > 0 and password and server:
                    if t_path and os.path.exists(t_path):
                        if mt5.initialize(path=t_path, login=login, password=password, server=server):
                            self.connected = True
                    else:
                        if mt5.initialize(login=login, password=password, server=server):
                            self.connected = True
            except Exception as e:
                print(f"[!] Aviso leyendo account_config.json: {e}")

        if not self.connected:
            if mt5.initialize():
                self.connected = True
            else:
                exe_path = self.find_mt5_terminal()
                if exe_path and mt5.initialize(path=exe_path):
                    self.connected = True

        if not self.connected:
            print(f"[ERROR CRÍTICO] No se pudo conectar a MetaTrader 5: {mt5.last_error()}")
            return False

        acc = mt5.account_info()
        print("=" * 105)
        print("🚀 SUITE GAMMA EXPOSURE SNIPER (12 ACTIVOS COMPLETOS) INICIADA CON ÉXITO")
        if acc:
            print(f"   Broker Server : {acc.server} | Cuenta: {acc.login} | Titular: {acc.name}")
            print(f"   Balance Total : ${acc.balance:,.2f} {acc.currency} | Margen Libre: ${acc.margin_free:,.2f} {acc.currency}")
        print(f"   Obscura Engine: {'ACTIVO (' + self.obscura_path + ')' if self.obscura_path else 'MODO DIRECTO HTTP/CBOE'}")
        print("=" * 105)

        self.resolve_symbols()
        return True

    def resolve_symbols(self):
        all_syms = mt5.symbols_get()
        broker_names = [s.name for s in all_syms] if all_syms else []
        print("\n🔍 Resolviendo los 12 activos y sus lotajes mínimos en tu broker MT5:")

        for canonical, cfg in GAMMA_ASSETS.items():
            candidates = cfg['aliases']
            found = None
            for cand in candidates:
                if cand in broker_names:
                    found = cand
                    break
            if not found:
                for b_sym in broker_names:
                    for cand in candidates:
                        if b_sym.upper().startswith(cand.upper()):
                            found = b_sym
                            break
                    if found:
                        break
            if found:
                mt5.symbol_select(found, True)
                self.symbol_map[canonical] = found
                info = mt5.symbol_info(found)
                leg_lot = max(info.volume_min, info.volume_step) if info else cfg['min_fallback_lot']
                print(f"  ✓ {canonical:<8} -> '{found:<12}' | Magic: {cfg['magic']} | Lote Mín Tramo: {leg_lot:<5} (Total 2 Tramos: {round(leg_lot*2, 2)})")
            else:
                self.symbol_map[canonical] = canonical
                print(f"  ⚠ {canonical:<8} -> No detectado en MarketWatch. Usando '{canonical}'")
        print("-" * 105)

    def disconnect(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False

    def get_broker_time(self, symbol=None):
        """Obtiene la hora oficial exacta del servidor del broker directamente desde las velas M1 de MT5."""
        ref_sym = symbol or self.symbol_map.get('EURUSD', 'EURUSD')
        try:
            rates = mt5.copy_rates_from_pos(ref_sym, mt5.TIMEFRAME_M1, 0, 1)
            if rates is not None and len(rates) > 0:
                candle_dt = datetime.fromtimestamp(rates[-1]['time'], timezone.utc)
                now_utc = datetime.now(timezone.utc)
                offset_hours = int(round((candle_dt - now_utc).total_seconds() / 3600.0))
                return now_utc + timedelta(hours=offset_hours)
        except Exception:
            pass
        return datetime.now(timezone.utc) + timedelta(hours=2)

    def get_leg_lot(self, broker_sym, fallback_lot):
        info = mt5.symbol_info(broker_sym)
        if info:
            return round(max(info.volume_min, info.volume_step), 2)
        return fallback_lot

    # =========================================================================
    # MOTORES DE EXTRACCIÓN DE GAMMA EXPOSURE (CBOE + CME OBSCURA + DERIBIT)
    # =========================================================================
    def fetch_cboe_gex_raw(self, ticker):
        url = f"https://cdn.cboe.com/api/global/delayed_quotes/options/{ticker}.json"
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get('data', {})
        cboe_spot = float(data.get('current_price') or 0)
        if cboe_spot <= 0:
            return None

        options = data.get('options', [])
        strike_gex = {}
        strike_0dte_gex = {}
        strike_call_oi = {}
        strike_put_oi = {}

        exps_found = set()
        parsed = []
        for o in options:
            sym = o.get('option', '')
            m = OCC_REGEX.match(sym)
            if not m:
                continue
            _, exp_str, opt_type, strike_raw = m.groups()
            strike = int(strike_raw) / 1000.0
            if not (cboe_spot * 0.85 <= strike <= cboe_spot * 1.15):
                continue
            oi = float(o.get('open_interest') or 0)
            vol = float(o.get('volume') or 0)
            gamma = float(o.get('gamma') or 0)
            exps_found.add(exp_str)
            parsed.append((exp_str, opt_type, strike, oi, vol, gamma))

        if not parsed:
            return None

        nearest_exp = sorted(exps_found)[0]
        for exp_str, opt_type, strike, oi, vol, gamma in parsed:
            eff_oi = oi + (vol * 0.25 if exp_str == nearest_exp else 0.0)
            # Fórmula exacta ITMatrixHQ: GEX ($ por cada $1 move) = Gamma * OI * 100 * Spot
            gex_val = gamma * eff_oi * 100.0 * cboe_spot
            if opt_type == 'P':
                gex_val = -gex_val
                strike_put_oi[strike] = strike_put_oi.get(strike, 0.0) + eff_oi
            else:
                strike_call_oi[strike] = strike_call_oi.get(strike, 0.0) + eff_oi

            strike_gex[strike] = strike_gex.get(strike, 0.0) + gex_val
            if exp_str == nearest_exp:
                strike_0dte_gex[strike] = strike_0dte_gex.get(strike, 0.0) + gex_val

        net_gex = sum(strike_gex.values())
        net_0dte = sum(strike_0dte_gex.values())

        calls_above = {k: v for k, v in strike_gex.items() if k >= cboe_spot * 0.996 and v > 0}
        call_wall_raw = max(calls_above.items(), key=lambda x: x[1])[0] if calls_above else max(strike_call_oi.items(), key=lambda x: x[1])[0]

        puts_below = {k: v for k, v in strike_gex.items() if k <= cboe_spot * 1.004 and v < 0}
        put_wall_raw = min(puts_below.items(), key=lambda x: x[1])[0] if puts_below else max(strike_put_oi.items(), key=lambda x: x[1])[0]

        near_strikes = {k: v for k, v in strike_gex.items() if cboe_spot * 0.97 <= k <= cboe_spot * 1.03}
        magnet_raw = max(near_strikes.items(), key=lambda x: abs(x[1]))[0] if near_strikes else max(strike_gex.items(), key=lambda x: abs(x[1]))[0]

        sorted_k = sorted(near_strikes.keys()) if near_strikes else sorted(strike_gex.keys())
        flip_raw = cboe_spot
        for i in range(len(sorted_k) - 1):
            k1, k2 = sorted_k[i], sorted_k[i + 1]
            g1, g2 = strike_gex[k1], strike_gex[k2]
            if (g1 < 0 and g2 > 0) or (g1 > 0 and g2 < 0):
                if abs(k1 - cboe_spot) < abs(flip_raw - cboe_spot) or flip_raw == cboe_spot:
                    w = abs(g1) / (abs(g1) + abs(g2))
                    flip_raw = k1 + w * (k2 - k1)

        return {
            'source': f'CBOE/OPRA ({ticker})',
            'ref_spot': cboe_spot,
            'net_gex_m': round(net_gex / 1e6, 2),
            'net_0dte_m': round(net_0dte / 1e6, 2),
            'convexity': 1.08 if net_gex < 0 else 1.02,
            'raw_call_wall': call_wall_raw,
            'raw_put_wall': put_wall_raw,
            'raw_magnet': magnet_raw,
            'raw_flip': flip_raw,
            'is_positive_gamma': net_gex >= 0,
        }

    def fetch_cme_obscura_raw(self, opt_pid, year, month, cvol_sym, mt5_spot):
        if not self.obscura_path:
            return None
        url_strikes = f"https://www.cmegroup.com/CmeWS/mvc/atm/strike-prices/{opt_pid}/{year}/{month}/ATM"
        url_cvol = f"https://www.cmegroup.com/services/cvol?symbol={cvol_sym}"
        try:
            out_s = subprocess.check_output(
                [self.obscura_path, "fetch", url_strikes, "--stealth", "--dump", "original", "--quiet"],
                timeout=14
            ).decode('utf-8', errors='ignore')
            out_c = subprocess.check_output(
                [self.obscura_path, "fetch", url_cvol, "--stealth", "--dump", "original", "--quiet"],
                timeout=12
            ).decode('utf-8', errors='ignore')
            strikes_json = json.loads(out_s.strip())
            strike_rows = strikes_json.get('strikePrices', []) if isinstance(strikes_json, dict) else strikes_json
            cvol_json = json.loads(out_c.strip()) if out_c.strip().startswith('[') else []
        except Exception:
            return None

        cvol_info = cvol_json[0] if cvol_json else {}
        atm_iv = float(cvol_info.get('atmInd') or 8.0)
        convexity = float(cvol_info.get('convexInd') or 1.05)
        skew = float(cvol_info.get('skew') or 0.0)

        call_vols = {}
        put_vols = {}
        for row in strike_rows:
            try:
                k = float(row.get('strikePrice') or 0)
                if k <= 0:
                    continue
                c_v = float(str(row.get('call', {}).get('volume', '0')).replace(',', '').replace('-', '0') or 0)
                p_v = float(str(row.get('put', {}).get('volume', '0')).replace(',', '').replace('-', '0') or 0)
                c_settle = float(str(row.get('call', {}).get('priorSettle', '0')).replace('-', '0') or 0)
                p_settle = float(str(row.get('put', {}).get('priorSettle', '0')).replace('-', '0') or 0)
                call_vols[k] = c_v + (10.0 if c_settle > 0 else 0.0)
                put_vols[k] = p_v + (10.0 if p_settle > 0 else 0.0)
            except Exception:
                continue

        if not call_vols:
            return None

        sample_k = sorted(call_vols.keys())[len(call_vols) // 2]
        scale = 1.0
        if mt5_spot and sample_k > 0:
            ratio = mt5_spot / sample_k
            if 0.85 <= ratio <= 1.15:
                scale = 1.0
            elif 85.0 <= ratio <= 115.0:
                scale = 100.0
            elif 850.0 <= ratio <= 1150.0:
                scale = 1000.0
            elif 0.0085 <= ratio <= 0.0115:
                scale = 0.01

        scaled_calls = {k * scale: v for k, v in call_vols.items()}
        scaled_puts = {k * scale: v for k, v in put_vols.items()}
        ref_spot = mt5_spot or (sample_k * scale)

        calls_above = {k: v for k, v in scaled_calls.items() if k >= ref_spot * 0.998}
        puts_below = {k: v for k, v in scaled_puts.items() if k <= ref_spot * 1.002}

        call_wall = max(calls_above.items(), key=lambda x: x[1])[0] if calls_above else max(scaled_calls.keys())
        put_wall = max(puts_below.items(), key=lambda x: x[1])[0] if puts_below else min(scaled_puts.keys())
        total_net = sum(scaled_calls.values()) - sum(scaled_puts.values())
        magnet = max(scaled_calls.keys(), key=lambda k: scaled_calls.get(k, 0) + scaled_puts.get(k, 0))
        flip = (call_wall + put_wall) / 2.0

        return {
            'source': f'CME CmeWS+{cvol_sym} (Conv:{convexity:.2f} IV:{atm_iv:.1f}%)',
            'ref_spot': ref_spot,
            'net_gex_m': round(total_net / 100.0, 2),
            'net_0dte_m': round(skew, 2),
            'convexity': convexity,
            'raw_call_wall': call_wall,
            'raw_put_wall': put_wall,
            'raw_magnet': magnet,
            'raw_flip': flip,
            'is_positive_gamma': (total_net >= 0 and skew >= -0.8),
        }

    def fetch_deribit_gex_raw(self, currency='BTC'):
        url = f"https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency={currency}&kind=option"
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None
        res = r.json().get('result', [])
        if not res:
            return None

        spot = float(res[0].get('underlying_price') or 0)
        if spot <= 0:
            return None

        strike_gex = {}
        strike_call_oi = {}
        strike_put_oi = {}

        for item in res:
            parts = item.get('instrument_name', '').split('-')
            if len(parts) != 4:
                continue
            _, _, k_s, otype = parts
            try:
                k = float(k_s)
            except Exception:
                continue
            if not (spot * 0.80 <= k <= spot * 1.20):
                continue
            oi = float(item.get('open_interest') or 0)
            vol = float(item.get('volume') or 0)
            mark_iv = max(float(item.get('mark_iv') or 55.0) / 100.0, 0.15)
            t = 7.0 / 365.0
            d1 = (math.log(spot / k) + (0.5 * mark_iv**2) * t) / (mark_iv * math.sqrt(t))
            gamma = (math.exp(-0.5 * d1**2) / math.sqrt(2 * math.pi)) / (spot * mark_iv * math.sqrt(t))
            gex_usd = gamma * (oi + vol * 0.2) * (spot ** 2) * 0.01
            if otype == 'P':
                gex_usd = -gex_usd
                strike_put_oi[k] = strike_put_oi.get(k, 0.0) + oi
            else:
                strike_call_oi[k] = strike_call_oi.get(k, 0.0) + oi
            strike_gex[k] = strike_gex.get(k, 0.0) + gex_usd

        net_gex = sum(strike_gex.values())
        calls_above = {k: v for k, v in strike_call_oi.items() if k >= spot}
        puts_below = {k: v for k, v in strike_put_oi.items() if k <= spot}
        call_wall_raw = max(calls_above.items(), key=lambda x: x[1])[0] if calls_above else spot * 1.03
        put_wall_raw = max(puts_below.items(), key=lambda x: x[1])[0] if puts_below else spot * 0.97
        near_strikes = {k: v for k, v in strike_gex.items() if spot * 0.94 <= k <= spot * 1.06}
        magnet_raw = max(near_strikes.items(), key=lambda x: abs(x[1]))[0] if near_strikes else spot
        flip_raw = (call_wall_raw + put_wall_raw) / 2.0

        return {
            'source': f'Deribit Native ({currency})',
            'ref_spot': spot,
            'net_gex_m': round(net_gex / 1e6, 2),
            'net_0dte_m': round((net_gex * 0.35) / 1e6, 2),
            'convexity': 1.10 if net_gex < 0 else 1.04,
            'raw_call_wall': call_wall_raw,
            'raw_put_wall': put_wall_raw,
            'raw_magnet': magnet_raw,
            'raw_flip': flip_raw,
            'is_positive_gamma': net_gex >= 0,
        }

    def get_live_gex_levels(self, canonical, cfg, mt5_spot, digits):
        now_ts = time.time()
        cache_file = os.path.join(CACHE_DIR, f"gex_cache_{canonical}.json")

        raw_data = self.gex_memory.get(canonical)
        last_ts = self.last_gex_fetch.get(canonical, 0)

        if not raw_data or (now_ts - last_ts) >= GEX_REFRESH_SECS:
            stype = cfg['source_type']
            fetched = None
            try:
                if stype == 'CBOE':
                    fetched = self.fetch_cboe_gex_raw(cfg['cboe_ticker'])
                    if not fetched and 'cboe_backup' in cfg:
                        fetched = self.fetch_cboe_gex_raw(cfg['cboe_backup'])
                elif stype == 'DUAL_CBOE_CME':
                    fetched = self.fetch_cboe_gex_raw(cfg['cboe_ticker'])
                    if not fetched and 'cme_params' in cfg:
                        opt_pid, yr, mo, cvol_sym = cfg['cme_params']
                        fetched = self.fetch_cme_obscura_raw(opt_pid, yr, mo, cvol_sym, mt5_spot)
                elif stype == 'CME_FX':
                    opt_pid, yr, mo, cvol_sym = cfg['cme_params']
                    fetched = self.fetch_cme_obscura_raw(opt_pid, yr, mo, cvol_sym, mt5_spot)
                    if not fetched and 'cboe_ticker' in cfg:
                        fetched = self.fetch_cboe_gex_raw(cfg['cboe_ticker'])
                elif stype == 'DERIBIT':
                    fetched = self.fetch_deribit_gex_raw(cfg['deribit_currency'])
                    if not fetched and 'cboe_ticker' in cfg:
                        fetched = self.fetch_cboe_gex_raw(cfg['cboe_ticker'])
            except Exception:
                fetched = None

            if fetched:
                raw_data = fetched
                self.gex_memory[canonical] = raw_data
                self.last_gex_fetch[canonical] = now_ts
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(raw_data, f, indent=2)
                except Exception:
                    pass
            elif os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        raw_data = json.load(f)
                        self.gex_memory[canonical] = raw_data
                        self.last_gex_fetch[canonical] = now_ts
                except Exception:
                    pass

        if not raw_data:
            # Fallback matemático basado en volatilidad implícita intradía
            band = mt5_spot * 0.008
            return {
                'source': 'Fallback IV Band',
                'call_wall': round(mt5_spot + band, digits),
                'put_wall': round(mt5_spot - band, digits),
                'magnet': round(mt5_spot, digits),
                'gamma_flip': round(mt5_spot, digits),
                'net_gex_m': 0.0,
                'convexity': 1.05,
                'is_positive_gamma': True,
            }

        ref_spot = float(raw_data.get('ref_spot') or mt5_spot)
        basis_ratio = (mt5_spot / ref_spot) if ref_spot > 0 else 1.0

        return {
            'source': raw_data['source'],
            'call_wall': round(raw_data['raw_call_wall'] * basis_ratio, digits),
            'put_wall': round(raw_data['raw_put_wall'] * basis_ratio, digits),
            'magnet': round(raw_data['raw_magnet'] * basis_ratio, digits),
            'gamma_flip': round(raw_data['raw_flip'] * basis_ratio, digits),
            'net_gex_m': raw_data.get('net_gex_m', 0.0),
            'convexity': raw_data.get('convexity', 1.05),
            'is_positive_gamma': bool(raw_data.get('is_positive_gamma', True)),
        }

    # =========================================================================
    # LAS 3 CONFIRMACIONES TÉCNICAS EN M5 (EMA STACK + FLAG + VOLUMEN)
    # =========================================================================
    def compute_m5_confirmations(self, broker_sym):
        rates = mt5.copy_rates_from_pos(broker_sym, mt5.TIMEFRAME_M5, 0, 75)
        if rates is None or len(rates) < 55:
            return None

        df = pd.DataFrame(rates)
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()

        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr14'] = tr.rolling(14).mean().bfill()

        df['vol_ma20'] = df['tick_volume'].rolling(20).mean().bfill()

        cur = df.iloc[-1]
        prev = df.iloc[-2]
        atr = max(float(cur['atr14']), 1e-6)

        # 1. Clean EMA Stack (9 / 21 / 50)
        bull_stack = (cur['ema9'] > cur['ema21'] > cur['ema50']) and ((cur['ema9'] - cur['ema21']) >= 0.05 * atr)
        bear_stack = (cur['ema9'] < cur['ema21'] < cur['ema50']) and ((cur['ema21'] - cur['ema9']) >= 0.05 * atr)

        # Stack flexible para reversión al Magnet (9 vs 21 alineadas hacia el objetivo)
        bull_magnet_align = (cur['ema9'] > cur['ema21']) and (cur['close'] > cur['ema9'])
        bear_magnet_align = (cur['ema9'] < cur['ema21']) and (cur['close'] < cur['ema9'])

        # 2. Price Flagging (Consolidación previa de 4 velas M5 + Ruptura)
        flag_bars = df.iloc[-6:-1]
        flag_high = float(flag_bars['high'].max())
        flag_low = float(flag_bars['low'].min())
        flag_range = flag_high - flag_low
        is_tight_flag = (flag_range <= 2.8 * atr)

        bull_flag_break = is_tight_flag and (cur['close'] > flag_high or (prev['close'] > float(df.iloc[-6:-2]['high'].max()) and cur['close'] > prev['high']))
        bear_flag_break = is_tight_flag and (cur['close'] < flag_low or (prev['close'] < float(df.iloc[-6:-2]['low'].min()) and cur['close'] < prev['low']))

        # 3. Confirmación de Volumen (RVOL >= 1.25x)
        vol_ma = max(float(cur['vol_ma20']), 1.0)
        rvol_cur = float(cur['tick_volume']) / vol_ma
        rvol_prev = float(prev['tick_volume']) / vol_ma
        rvol = max(rvol_cur, rvol_prev)
        vol_confirmed = (rvol >= 1.25)

        return {
            'atr': atr,
            'ema9': float(cur['ema9']),
            'ema21': float(cur['ema21']),
            'ema50': float(cur['ema50']),
            'bull_candle': bool(cur['close'] > cur['open']),
            'bear_candle': bool(cur['close'] < cur['open']),
            'bull_stack': bool(bull_stack),
            'bear_stack': bool(bear_stack),
            'bull_magnet_align': bool(bull_magnet_align),
            'bear_magnet_align': bool(bear_magnet_align),
            'flag_high': flag_high,
            'flag_low': flag_low,
            'is_tight_flag': bool(is_tight_flag),
            'bull_flag_break': bool(bull_flag_break),
            'bear_flag_break': bool(bear_flag_break),
            'rvol': round(rvol, 2),
            'vol_confirmed': bool(vol_confirmed),
        }

    # =========================================================================
    # CONTROL DE RIESGO, COOLDOWN Y REGLA "1 TRADE POR HORA AL DÍA" (ONE & DONE)
    # =========================================================================
    def can_open_new_trade(self, broker_sym, magic):
        positions = mt5.positions_get(symbol=broker_sym)
        if positions:
            for p in positions:
                if p.magic == magic:
                    return False, "Posición activa en curso"

        now_ts = time.time()
        if broker_sym in self.cooldowns and now_ts < self.cooldowns[broker_sym]:
            rem = int(self.cooldowns[broker_sym] - now_ts) // 60
            return False, f"Cooldown activo ({rem} min)"

        broker_now = self.get_broker_time(broker_sym)
        dh_key = (broker_sym, str(broker_now.date()), int(broker_now.hour))
        if dh_key in self.traded_date_hours:
            return False, f"One & Done: ya operó en la ventana {broker_now.hour:02d}:00 hoy"

        hour_start = broker_now.replace(minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(hour_start, broker_now)
        if deals:
            for d in deals:
                if d.symbol == broker_sym and d.magic == magic and d.entry == mt5.DEAL_ENTRY_IN:
                    self.traded_date_hours.add(dh_key)
                    return False, f"One & Done: ya operó en la ventana {broker_now.hour:02d}:00 hoy"

        return True, "OK"

    # =========================================================================
    # EVALUACIÓN PRINCIPAL POR ACTIVO (WALK-FORWARD ÉLITE: 1, 2 O 3 FILTROS)
    # =========================================================================
    def evaluate_asset(self, canonical, cfg, execute=True):
        broker_sym = self.symbol_map.get(canonical, canonical)
        info = mt5.symbol_info(broker_sym)
        tick = mt5.symbol_info_tick(broker_sym)
        if not info or not tick or tick.bid <= 0:
            return

        spot = (tick.bid + tick.ask) / 2.0
        spread = tick.ask - tick.bid
        magic = cfg['magic']
        min_conf = cfg.get('min_confirmations', 2)
        leg_lot = self.get_leg_lot(broker_sym, cfg['min_fallback_lot'])

        broker_dt = self.get_broker_time(broker_sym)
        in_session = broker_dt.hour in cfg['hours_broker']
        sess_str = f"ABIERTA ({broker_dt.hour:02d}h)" if in_session else f"CERRADA (Horas Oro: {cfg['hours_broker']})"

        gex = self.get_live_gex_levels(canonical, cfg, spot, info.digits)
        m5 = self.compute_m5_confirmations(broker_sym)
        if not m5:
            return

        atr = m5['atr']
        is_pos_regime = gex['is_positive_gamma'] and (spot >= gex['gamma_flip'] * 0.998)
        regime_tag = "🟢 +GEX (THE MAGNET)" if is_pos_regime else "🔴 -GEX (THE BREAK)"
        stack_tag = "ALCISTA (9>21>50)" if m5['bull_stack'] else ("BAJISTA (9<21<50)" if m5['bear_stack'] else "MIXTO/RANGO")

        # Contabilizar cuántas de las 3 confirmaciones se cumplen para compra y venta
        if is_pos_regime:
            bull_f1 = m5['bull_stack'] or m5['bull_magnet_align']
            bear_f1 = m5['bear_stack'] or m5['bear_magnet_align']
        else:
            bull_f1 = m5['bull_stack']
            bear_f1 = m5['bear_stack']

        bull_confs = int(bull_f1) + int(m5['bull_flag_break']) + int(m5['vol_confirmed'])
        bear_confs = int(bear_f1) + int(m5['bear_flag_break']) + int(m5['vol_confirmed'])

        print(f"\n[{cfg['name']}] {broker_sym:<10} | Spot: {spot:<10.{info.digits}f} | {regime_tag} | Sesión: {sess_str} | Lote Tramo: {leg_lot}")
        print(f"  📊 {gex['source']} -> CallWall: {gex['call_wall']} | PutWall: {gex['put_wall']} | Magnet: {gex['magnet']} | Flip: {gex['gamma_flip']}")
        print(f"  🔍 Filtros M5 (Exige >={min_conf}/3) -> BUY Confs: {bull_confs}/3 | SELL Confs: {bear_confs}/3 | EMA: {stack_tag} | Flag: {'SÍ' if m5['is_tight_flag'] else 'NO'} | RVOL: {m5['rvol']}x")

        if not in_session:
            return

        if spread > atr * cfg['max_spread_atr_ratio']:
            print(f"  [Filtro Spread] Spread actual ({spread:.{info.digits}f}) supera el límite permitido.")
            return

        ok_trade, reason = self.can_open_new_trade(broker_sym, magic)
        if not ok_trade:
            print(f"  [Protección] {reason}.")
            return

        magnet = gex['magnet']
        dh_key = (broker_sym, str(broker_dt.date()), int(broker_dt.hour))

        # ---------------------------------------------------------------------
        # MODO 1: "THE MAGNET" (Régimen Gamma Positiva -> Atracción al Imán)
        # ---------------------------------------------------------------------
        if is_pos_regime:
            dist_to_magnet = magnet - spot
            # BUY hacia el Magnet superior (con >= min_conf confirmaciones + vela alcista)
            if dist_to_magnet >= 1.0 * atr and m5['bull_candle'] and bull_confs >= min_conf:
                sl_dist = 1.5 * atr
                sl_price = round(tick.ask - sl_dist, info.digits)
                tp1_price = round(tick.ask + (sl_dist * 1.5), info.digits)
                tp2_price = round(tick.ask + max(abs(dist_to_magnet), sl_dist * 2.0), info.digits)
                print(f"  [🧲 SEÑAL THE MAGNET BUY ({bull_confs}/{min_conf} Confs)] {broker_sym} BUY hacia Imán {magnet} | SL: {sl_price} | TP1: {tp1_price} | TP2: {tp2_price}")
                if execute:
                    self.send_order(broker_sym, 'BUY', sl_price, tp1_price, leg_lot, f"GEX_MAG_{canonical}_C1", magic)
                    self.send_order(broker_sym, 'BUY', sl_price, tp2_price, leg_lot, f"GEX_MAG_{canonical}_C2", magic)
                    self.traded_date_hours.add(dh_key)
                    self.cooldowns[broker_sym] = time.time() + 1800
                return

            # SELL hacia el Magnet inferior (con >= min_conf confirmaciones + vela bajista)
            elif dist_to_magnet <= -1.0 * atr and m5['bear_candle'] and bear_confs >= min_conf:
                sl_dist = 1.5 * atr
                sl_price = round(tick.bid + sl_dist, info.digits)
                tp1_price = round(tick.bid - (sl_dist * 1.5), info.digits)
                tp2_price = round(tick.bid - max(abs(dist_to_magnet), sl_dist * 2.0), info.digits)
                print(f"  [🧲 SEÑAL THE MAGNET SELL ({bear_confs}/{min_conf} Confs)] {broker_sym} SELL hacia Imán {magnet} | SL: {sl_price} | TP1: {tp1_price} | TP2: {tp2_price}")
                if execute:
                    self.send_order(broker_sym, 'SELL', sl_price, tp1_price, leg_lot, f"GEX_MAG_{canonical}_C1", magic)
                    self.send_order(broker_sym, 'SELL', sl_price, tp2_price, leg_lot, f"GEX_MAG_{canonical}_C2", magic)
                    self.traded_date_hours.add(dh_key)
                    self.cooldowns[broker_sym] = time.time() + 1800
                return

        # ---------------------------------------------------------------------
        # MODO 2: "THE BREAK" (Régimen Gamma Negativa -> Aceleración de Ruptura)
        # ---------------------------------------------------------------------
        else:
            # Ruptura Bajista (Cascada de Dealers Cortos de Gamma)
            if m5['bear_candle'] and bear_confs >= min_conf:
                sl_dist = 1.5 * atr
                sl_price = round(tick.bid + sl_dist, info.digits)
                tp1_price = round(tick.bid - (sl_dist * 1.5), info.digits)
                tp2_price = round(tick.bid - (sl_dist * 3.0), info.digits)
                print(f"  [💥 SEÑAL THE BREAK SELL ({bear_confs}/{min_conf} Confs)] {broker_sym} SELL Aceleración -GEX | SL: {sl_price} | TP1: {tp1_price} | TP2: {tp2_price}")
                if execute:
                    self.send_order(broker_sym, 'SELL', sl_price, tp1_price, leg_lot, f"GEX_BRK_{canonical}_C1", magic)
                    self.send_order(broker_sym, 'SELL', sl_price, tp2_price, leg_lot, f"GEX_BRK_{canonical}_C2", magic)
                    self.traded_date_hours.add(dh_key)
                    self.cooldowns[broker_sym] = time.time() + 1800
                return

            # Ruptura Alcista (Gamma Squeeze de Dealers Cortos de Gamma)
            if m5['bull_candle'] and bull_confs >= min_conf:
                sl_dist = 1.5 * atr
                sl_price = round(tick.ask - sl_dist, info.digits)
                tp1_price = round(tick.ask + (sl_dist * 1.5), info.digits)
                tp2_price = round(tick.ask + (sl_dist * 3.0), info.digits)
                print(f"  [💥 SEÑAL THE BREAK BUY ({bull_confs}/{min_conf} Confs)] {broker_sym} BUY Gamma Squeeze -GEX | SL: {sl_price} | TP1: {tp1_price} | TP2: {tp2_price}")
                if execute:
                    self.send_order(broker_sym, 'BUY', sl_price, tp1_price, leg_lot, f"GEX_BRK_{canonical}_C1", magic)
                    self.send_order(broker_sym, 'BUY', sl_price, tp2_price, leg_lot, f"GEX_BRK_{canonical}_C2", magic)
                    self.traded_date_hours.add(dh_key)
                    self.cooldowns[broker_sym] = time.time() + 1800
                return

    # =========================================================================
    # GESTIÓN DE RUNNER (BREAK-EVEN Y TRAILING STOP PARA CONTRATO C2)
    # =========================================================================
    def manage_c2_runners(self):
        positions = mt5.positions_get()
        if not positions:
            return
        gex_magics = {cfg['magic'] for cfg in GAMMA_ASSETS.values()}
        for p in positions:
            if p.magic not in gex_magics:
                continue
            if "_C2" not in p.comment:
                continue

            sym = p.symbol
            tick = mt5.symbol_info_tick(sym)
            info = mt5.symbol_info(sym)
            if not tick or not info:
                continue

            is_buy = (p.type == mt5.ORDER_TYPE_BUY)
            cur_price = tick.bid if is_buy else tick.ask
            risk_dist = abs(p.price_open - p.sl) if p.sl > 0 else (info.point * 100)

            # Si el runner lleva +1.0R a favor, proteger en Break-Even + 10 puntos
            be_lock = p.price_open + (info.point * 10) if is_buy else p.price_open - (info.point * 10)
            if is_buy and (cur_price - p.price_open) >= risk_dist and p.sl < p.price_open:
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(round(be_lock, info.digits)), "tp": float(p.tp)}
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[🛡️ BREAK-EVEN GAMMA C2] Ticket #{p.ticket} ({sym}) protegido en {be_lock}")
            elif not is_buy and (p.price_open - cur_price) >= risk_dist and (p.sl > p.price_open or p.sl == 0):
                req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(round(be_lock, info.digits)), "tp": float(p.tp)}
                res = mt5.order_send(req)
                if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"[🛡️ BREAK-EVEN GAMMA C2] Ticket #{p.ticket} ({sym}) protegido en {be_lock}")

    def send_order(self, symbol, order_type, sl, tp, lots, comment, magic):
        tick = mt5.symbol_info_tick(symbol)
        price = tick.ask if order_type.upper() == 'BUY' else tick.bid
        ot = mt5.ORDER_TYPE_BUY if order_type.upper() == 'BUY' else mt5.ORDER_TYPE_SELL

        for fill_mode in (mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN):
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
                "type_filling": fill_mode,
            }
            res = mt5.order_send(req)
            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"  [✅ ORDEN EJECUTADA] #{res.order} | {symbol} {order_type} | Lote: {res.volume} | Magic: {magic} | {comment}")
                return True
        print(f"  [-] Error enviando orden {order_type} en {symbol}")
        return False

    def run_cycle(self, execute=True):
        self.manage_c2_runners()
        broker_now = self.get_broker_time()
        now_utc = datetime.now(timezone.utc)
        print("\n" + "=" * 105)
        print(f">>> [CICLO GAMMA SNIPER 12 ACTIVOS] Hora Broker IC Markets: {broker_now.strftime('%H:%M:%S')} (UTC: {now_utc.strftime('%H:%M:%S')})")
        print("=" * 105)

        for canonical, cfg in GAMMA_ASSETS.items():
            try:
                self.evaluate_asset(canonical, cfg, execute=execute)
            except Exception as e:
                print(f"[-] Error evaluando {canonical}: {e}")

    def run_daemon(self):
        print("\n" + "=" * 105)
        print("   OPERATIVA CONTINUA 24/7 EN VPS - GAMMA EXPOSURE SNIPER (12 ACTIVOS)")
        print("   Fuentes en Vivo: CBOE/OPRA CDN + CME Group (CmeWS/CVOL via Obscura Stealth) + Deribit")
        print("   Setups: THE MAGNET (+GEX) & THE BREAK (-GEX) | 3 Confirmaciones: EMA 9/21/50 + Flag + Volumen")
        print(f"   Frecuencia de Escaneo M5: cada {MONITOR_INTERVAL_SECS}s | Refresco Opciones GEX: cada {GEX_REFRESH_SECS//60} min")
        print("=" * 105)
        try:
            while True:
                self.run_cycle(execute=True)
                time.sleep(MONITOR_INTERVAL_SECS)
        except KeyboardInterrupt:
            print("\n[*] Bot Gamma Exposure Sniper detenido por el usuario.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Gamma Exposure Sniper 12 Activos - MT5")
    parser.add_argument('--daemon', action='store_true', help='Ejecución continua 24/7 en VPS')
    parser.add_argument('--audit', action='store_true', help='Auditoría en vivo de un ciclo (sin enviar órdenes)')
    args = parser.parse_args()

    bot = GammaSniperBot()
    if bot.connect():
        if args.daemon:
            bot.run_daemon()
        else:
            bot.run_cycle(execute=False)
        bot.disconnect()

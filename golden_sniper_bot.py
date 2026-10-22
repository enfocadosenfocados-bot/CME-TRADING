"""
================================================================================
GOLDEN SNIPER TRADING SUITE - 6 ACTIVOS CAMPEONES EN HORAS DE ORO
================================================================================
Estrategia Institucional Exclusiva: Open Interest Walls + Vol2Vol + VWAP M5
Compatible con CUALQUIER Broker de MetaTrader 5 (Detección automática de símbolos).

TAXONOMÍA DE MAGICS Y NOMBRES:
- Magic 880100 | GS_US30   | Dow Jones 30    | Horas: 17:00 y 22:00 Broker (14-15 y 19-20 UTC)
- Magic 880200 | GS_USTEC  | Nasdaq 100     | Horas: 17:00 Broker (14-15 UTC)
- Magic 880300 | GS_US2000 | Russell 2000   | Horas: 16:00 a 18:00 Broker (13-16 UTC)
- Magic 880400 | GS_XAUUSD | Gold (Oro)      | Horas: 05:00 y 19:00 Broker (02-03 y 16-17 UTC)
- Magic 880500 | GS_GBPUSD | British Pound   | Horas: 05:00 y 16:00 Broker (02-03 y 13-14 UTC)
- Magic 880600 | GS_BTCUSD | Bitcoin Futures | Horas: 16:00 y 03:00 Broker (13-14 y 00-01 UTC)
================================================================================
"""

import sys
import os
import json
import math
import time
import glob
import argparse
from datetime import datetime, timezone, timedelta

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Importación segura de MetaTrader 5
try:
    import MetaTrader5 as mt5
except ImportError:
    print("[ERROR CRÍTICO] La librería MetaTrader5 no está instalada.")
    print("Ejecute en la consola: pip install MetaTrader5 pandas requests")
    sys.exit(1)

# Importación segura de dependencias HTTP / Scraping
try:
    from curl_cffi import requests
except ImportError:
    import requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

import pandas as pd

CACHE_DIR = os.path.dirname(os.path.abspath(__file__))
MONITOR_INTERVAL_SECS = 15
SLIPPAGE_MAX = 10

# Alias de símbolos en diferentes brokers (IC Markets, Exness, XM, FTMO, Eightcap, etc.)
SYMBOL_ALIASES = {
    'US30':   ['US30', 'US30.raw', 'US30m', 'DJ30', 'WS30', 'DJIA', 'US30Cash', 'USA30', 'US30+'],
    'USTEC':  ['USTEC', 'USTEC.raw', 'USTECm', 'NAS100', 'US100', 'NDX', 'USTECH', 'NAS100m', 'US100Cash', 'US100+'],
    'US2000': ['US2000', 'US2000.raw', 'US2000m', 'RUT', 'USSmall2000', 'Russell2000', 'US2000Cash', 'US2000+'],
    'XAUUSD': ['XAUUSD', 'XAUUSD.raw', 'XAUUSDm', 'GOLD', 'GOLD.raw', 'GOLDm', 'XAUUSD+'],
    'GBPUSD': ['GBPUSD', 'GBPUSD.raw', 'GBPUSDm', 'GBPUSD+', 'GBPUSD.ecn'],
    'BTCUSD': ['BTCUSD', 'BTCUSD.raw', 'BTCUSDm', 'BTCUSD+', 'BITCOIN', 'BTC']
}

# Configuración institucional exclusiva para los 6 activos ganadores
GOLDEN_CONFIG = {
    'US30': {
        'name': 'GS_US30',
        'title': 'Dow Jones 30',
        'magic': 880100,
        'cme_code': 'YM',
        'cme_pid': 130,
        'cme_pf': 26,
        'fallback_lot': 0.20,
        'windows_utc': [(14.0, 15.0), (19.0, 20.0)],
        'windows_broker': ['17:00', '22:00'],
        'windows_cdmx': ['08:00', '13:00'],
        'min_expansion_pts': 60.0,
        'wall_zone_pts': 20.0,
        'tp_buffer_pts': 10.0,
        'sl_min_pts': 45.0,
        'tp1_pts': 65.0,
        'tp2_pts': 180.0,
        'trail_pts': 50.0,
        'be_buffer_pts': 5.0,
        'max_spread_pts': 3.0,
        'annual_iv': 0.14
    },
    'USTEC': {
        'name': 'GS_USTEC',
        'title': 'Nasdaq 100',
        'magic': 880200,
        'cme_code': 'NQ',
        'cme_pid': 121,
        'cme_pf': 26,
        'fallback_lot': 0.20,
        'windows_utc': [(14.0, 15.0)],
        'windows_broker': ['17:00'],
        'windows_cdmx': ['08:00'],
        'min_expansion_pts': 35.0,
        'wall_zone_pts': 12.0,
        'tp_buffer_pts': 5.0,
        'sl_min_pts': 22.0,
        'tp1_pts': 28.0,
        'tp2_pts': 75.0,
        'trail_pts': 22.0,
        'be_buffer_pts': 2.0,
        'max_spread_pts': 2.5,
        'annual_iv': 0.19
    },
    'US2000': {
        'name': 'GS_US2000',
        'title': 'Russell 2000',
        'magic': 880300,
        'cme_code': 'RTY',
        'cme_pid': 133,
        'cme_pf': 26,
        'fallback_lot': 2.00,
        'windows_utc': [(13.0, 16.0)],
        'windows_broker': ['16:00-18:00'],
        'windows_cdmx': ['07:00-10:00'],
        'min_expansion_pts': 5.0,
        'wall_zone_pts': 2.0,
        'tp_buffer_pts': 0.8,
        'sl_min_pts': 4.0,
        'tp1_pts': 4.5,
        'tp2_pts': 14.0,
        'trail_pts': 4.0,
        'be_buffer_pts': 0.4,
        'max_spread_pts': 0.8,
        'annual_iv': 0.22
    },
    'XAUUSD': {
        'name': 'GS_XAUUSD',
        'title': 'Gold (Oro Spot)',
        'magic': 880400,
        'cme_code': 'GC',
        'cme_pid': 40,
        'cme_pf': 6,
        'fallback_lot': 0.02,
        'windows_utc': [(2.0, 3.0), (16.0, 17.0)],
        'windows_broker': ['05:00', '19:00'],
        'windows_cdmx': ['20:00', '10:00'],
        'min_expansion_pts': 4.0,
        'wall_zone_pts': 1.5,
        'tp_buffer_pts': 0.8,
        'sl_min_pts': 6.0,
        'tp1_pts': 8.0,
        'tp2_pts': 22.0,
        'trail_pts': 6.0,
        'be_buffer_pts': 0.5,
        'max_spread_pts': 0.50,
        'annual_iv': 0.16
    },
    'GBPUSD': {
        'name': 'GS_GBPUSD',
        'title': 'British Pound',
        'magic': 880500,
        'cme_code': '6B',
        'cme_pid': 2,
        'cme_pf': 26,
        'fallback_lot': 0.02,
        'windows_utc': [(2.0, 3.0), (13.0, 14.0)],
        'windows_broker': ['05:00', '16:00'],
        'windows_cdmx': ['20:00', '07:00'],
        'min_expansion_pts': 0.0020,
        'wall_zone_pts': 0.0008,
        'tp_buffer_pts': 0.0004,
        'sl_min_pts': 0.0016,
        'tp1_pts': 0.0018,
        'tp2_pts': 0.0055,
        'trail_pts': 0.0015,
        'be_buffer_pts': 0.0002,
        'max_spread_pts': 0.00020,
        'annual_iv': 0.09
    },
    'BTCUSD': {
        'name': 'GS_BTCUSD',
        'title': 'Bitcoin Futures',
        'magic': 880600,
        'cme_code': 'BTC',
        'cme_pid': 350,
        'cme_pf': 26,
        'fallback_lot': 0.02,
        'windows_utc': [(13.0, 14.0), (0.0, 1.0)],
        'windows_broker': ['16:00', '03:00'],
        'windows_cdmx': ['07:00', '18:00'],
        'min_expansion_pts': 400.0,
        'wall_zone_pts': 150.0,
        'tp_buffer_pts': 60.0,
        'sl_min_pts': 320.0,
        'tp1_pts': 350.0,
        'tp2_pts': 1100.0,
        'trail_pts': 280.0,
        'be_buffer_pts': 25.0,
        'max_spread_pts': 15.0,
        'annual_iv': 0.52
    }
}

class GoldenSniperBot:
    def __init__(self):
        self.cooldown_minutes = 30
        self.cooldowns = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Referer': 'https://www.cmegroup.com/tools-information/quikstrike/open-interest-heatmap.html'
        }
        self.state_file = os.path.join(CACHE_DIR, 'golden_sniper_partial_state.json')
        self.partial_closed = self._load_partial_state()
        self.symbol_map = {}  # { 'canonical': 'actual_broker_symbol' }
        self.connected = False

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
        except Exception:
            pass

    def connect(self):
        # 1. Verificar si existe configuración de cuenta personalizada (account_config.json)
        config_path = os.path.join(CACHE_DIR, 'account_config.json')
        custom_cfg = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    custom_cfg = json.load(f)
            except Exception:
                pass

        init_kwargs = {}
        if custom_cfg.get('path'):
            init_kwargs['path'] = custom_cfg['path']
        if custom_cfg.get('login'):
            init_kwargs['login'] = int(custom_cfg['login'])
        if custom_cfg.get('password'):
            init_kwargs['password'] = custom_cfg['password']
        if custom_cfg.get('server'):
            init_kwargs['server'] = custom_cfg['server']

        # 2. Intentar inicializar MT5
        initialized = False
        if init_kwargs:
            initialized = mt5.initialize(**init_kwargs)

        if not initialized:
            # Intento estándar (conecta a cualquier MT5 abierto en la sesión)
            initialized = mt5.initialize()

        if not initialized:
            # Búsqueda automática de terminales instalados en Program Files
            candidate_paths = [
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files\IC Markets Global MT5\terminal64.exe",
                r"C:\Program Files\XM Global MT5\terminal64.exe",
                r"C:\Program Files\Exness MT5\terminal64.exe",
                r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"
            ]
            for p in candidate_paths:
                if os.path.exists(p):
                    if mt5.initialize(path=p):
                        initialized = True
                        break

        if not initialized:
            print("\n" + "=" * 85)
            print("❌ ERROR: NO SE PUDO CONECTAR CON METATRADER 5")
            print(f"   Código de Error MT5: {mt5.last_error()}")
            print("=" * 85)
            print("👉 LISTA DE VERIFICACIÓN PARA RESOLVERLO:")
            print("  1. ¿Está MetaTrader 5 ABIERTO en tu VPS?")
            print("     -> Abre tu terminal MT5 y asegúrate de haber iniciado sesión en tu cuenta.")
            print("  2. ¿Está activado el Trading Automático en MT5?")
            print("     -> El botón 'Algo Trading' (Trading Automático) en la barra superior debe estar en VERDE.")
            print("  3. Permisos en MT5:")
            print("     -> Ve al menú: Herramientas -> Opciones -> Asesores Expertos (Expert Advisors).")
            print("     -> Marca: [✓] 'Permitir trading algorítmico' (Allow Algo Trading).")
            print("     -> Marca: [✓] 'Permitir importación de DLL' (Allow DLL imports).")
            print("  4. Si tu MT5 está en una carpeta distinta o tienes múltiples brokers:")
            print("     -> Crea un archivo 'account_config.json' en la carpeta del bot con:")
            print('        {\n          "path": "C:\\\\Ruta\\\\A\\\\Tu\\\\terminal64.exe"\n        }')
            print("=" * 85 + "\n")
            return False

        acc = mt5.account_info()
        if not acc:
            print("[-] Conectado a terminal MT5 pero sin cuenta activa. Inicie sesión en MT5.")
            return False

        print("=" * 85)
        print(f"🚀 CONEXIÓN EXITOSA CON METATRADER 5")
        print(f"   Broker Server : {acc.server}")
        print(f"   Número Cuenta : {acc.login}")
        print(f"   Nombre Titular: {acc.name}")
        print(f"   Divisa Cuenta : {acc.currency}")
        print(f"   Balance Total : ${acc.balance:,.2f} {acc.currency}")
        print(f"   Margen Libre  : ${acc.margin_free:,.2f} {acc.currency}")
        print("=" * 85)

        # 3. Resolver nombres de símbolos en el broker actual
        self.resolve_broker_symbols()
        self.connected = True
        return True

    def resolve_broker_symbols(self):
        """Detecta automáticamente el nombre exacto de cada símbolo en cualquier broker."""
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            print("[-] No se pudieron cargar símbolos desde MT5.")
            return

        available_names = {s.name.upper(): s.name for s in all_symbols}

        print("\n🔍 Detectando símbolos en el broker:")
        for canonical, aliases in SYMBOL_ALIASES.items():
            found_symbol = None
            for alias in aliases:
                if alias.upper() in available_names:
                    found_symbol = available_names[alias.upper()]
                    break
            
            # Búsqueda parcial difusa si no coincide directo
            if not found_symbol:
                for s_name in available_names.values():
                    if canonical in s_name.upper():
                        found_symbol = s_name
                        break

            if found_symbol:
                mt5.symbol_select(found_symbol, True)
                self.symbol_map[canonical] = found_symbol
                info = mt5.symbol_info(found_symbol)
                min_divisible = round(max(info.volume_min, info.volume_step) * 2.0, 2) if info else GOLDEN_CONFIG[canonical]['fallback_lot']
                print(f"  ✓ {canonical:<7} -> Detectado como: '{found_symbol:<12}' | Lote Mínimo Parcializable: {min_divisible}")
            else:
                self.symbol_map[canonical] = canonical
                print(f"  ⚠ {canonical:<7} -> No encontrado. Usando por defecto '{canonical}'")
        print("-" * 85)

    def disconnect(self):
        if self.connected:
            mt5.shutdown()
            self.connected = False

    def check_cooldown(self, symbol):
        now_ts = datetime.now(timezone.utc).timestamp()
        if symbol in self.cooldowns and now_ts < self.cooldowns[symbol]:
            remaining = int(self.cooldowns[symbol] - now_ts) // 60
            return False, f"En reposo protector ({remaining} min restantes)"

        time_from = datetime.now(timezone.utc) - timedelta(minutes=self.cooldown_minutes)
        deals = mt5.history_deals_get(time_from, datetime.now(timezone.utc))
        if deals:
            sym_deals = [d for d in deals if d.symbol == symbol and d.entry == mt5.DEAL_ENTRY_OUT and d.profit < -1.0]
            if sym_deals:
                last_loss = max(sym_deals, key=lambda d: d.time)
                expiry = last_loss.time + (self.cooldown_minutes * 60)
                if now_ts < expiry:
                    self.cooldowns[symbol] = expiry
                    remaining = int(expiry - now_ts) // 60
                    return False, f"Pérdida reciente (#{last_loss.ticket}: ${last_loss.profit:.2f}). Reposo: {remaining} min"
        return True, "OK"

    def is_in_golden_window(self, canonical_symbol, cfg):
        now_utc = datetime.now(timezone.utc)
        weekday = now_utc.weekday()
        time_decimal = now_utc.hour + (now_utc.minute / 60.0)

        # 1. Fin de semana (Viernes 20:55 UTC a Domingo 22:00 UTC) excepto Bitcoin
        if canonical_symbol != 'BTCUSD':
            if weekday == 5:
                return False
            if weekday == 6 and time_decimal < 22.0:
                return False
            if weekday == 4 and time_decimal >= 20.91:
                return False

        # 2. Bloqueo Anti-Rollover de broker (20:55 a 22:30 UTC)
        if 20.91 <= time_decimal < 22.5:
            return False

        # 3. Ventana horaria de oro
        for start_h, end_h in cfg['windows_utc']:
            if start_h <= time_decimal < end_h:
                return True
        return False

    def has_traded_in_window(self, broker_symbol, magic, cfg):
        """One Bullet Policy: 1 trade por activo en cada ventana horaria de oro."""
        now_utc = datetime.now(timezone.utc)
        time_decimal = now_utc.hour + (now_utc.minute / 60.0)

        current_win = None
        for start_h, end_h in cfg['windows_utc']:
            if start_h <= time_decimal < end_h:
                current_win = (start_h, end_h)
                break

        if not current_win:
            return False

        start_h, _ = current_win
        win_start_dt = now_utc.replace(
            hour=int(start_h),
            minute=int(round((start_h % 1) * 60)),
            second=0,
            microsecond=0
        )

        positions = mt5.positions_get(symbol=broker_symbol)
        if positions:
            for p in positions:
                if p.magic == magic or str(p.magic).startswith('88'):
                    return True

        deals = mt5.history_deals_get(win_start_dt, now_utc)
        if deals:
            for d in deals:
                if d.symbol == broker_symbol and d.entry == mt5.DEAL_ENTRY_IN:
                    if d.magic == magic or str(d.magic).startswith('88'):
                        return True
        return False

    def get_min_divisible_lot(self, broker_symbol, fallback_lot):
        info = mt5.symbol_info(broker_symbol)
        if info:
            step = info.volume_step
            min_lot = info.volume_min
            # 2x mínimo para asegurar que el 50% parcial sea válido en MT5
            calculated = max(min_lot * 2.0, step * 2.0)
            return round(calculated, 2)
        return fallback_lot

    def fetch_oi_walls(self, cme_code, pid, pf, spot_price, annual_iv):
        cache_file = os.path.join(CACHE_DIR, f"oi_cache_{cme_code}.json")
        url = f"https://cmegroup-tools.quikstrike.net/User/QuikStrikeView.aspx?pid={pid}&pf={pf}&viewitemid=IntegratedVOIHeatMap"
        try:
            r = requests.get(url, headers=self.headers, timeout=8)
            if r.status_code == 200 and len(r.text) > 10000 and BeautifulSoup:
                soup = BeautifulSoup(r.text, 'html.parser')
                tables = soup.find_all('table')
                if len(tables) >= 7:
                    rows = tables[6].find_all('tr')
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
                            'total_p': total_p
                        })

                    if strikes_data:
                        calls_above = [s for s in strikes_data if s['strike'] >= spot_price]
                        call_wall = max(calls_above, key=lambda x: (x['c_front'], x['total_c']))['strike'] if calls_above else max(strikes_data, key=lambda x: x['strike'])['strike']
                        puts_below = [s for s in strikes_data if s['strike'] <= spot_price]
                        put_wall = max(puts_below, key=lambda x: (x['p_front'], x['total_p']))['strike'] if puts_below else min(strikes_data, key=lambda x: x['strike'])['strike']

                        if (spot_price * 0.70) <= call_wall <= (spot_price * 1.30):
                            levels = {'call_wall': call_wall, 'put_wall': put_wall, 'timestamp': datetime.now(timezone.utc).isoformat()}
                            with open(cache_file, 'w', encoding='utf-8') as f:
                                json.dump(levels, f, indent=2)
                            return levels
        except Exception:
            pass

        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    c_data = json.load(f)
                    if (spot_price * 0.70) <= c_data.get('call_wall', 0) <= (spot_price * 1.30):
                        return c_data
            except Exception:
                pass

        daily_sigma = spot_price * annual_iv * math.sqrt(1.0 / 365.0)
        return {
            'call_wall': round(spot_price + (1.2 * daily_sigma), 2),
            'put_wall': round(spot_price - (1.2 * daily_sigma), 2),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def calculate_vwap(self, broker_symbol, num_bars=100):
        rates = mt5.copy_rates_from_pos(broker_symbol, mt5.TIMEFRAME_M5, 0, num_bars)
        if rates is None or len(rates) == 0:
            return None
        df = pd.DataFrame(rates)
        typical = (df['high'] + df['low'] + df['close']) / 3.0
        return round(float((typical * df['tick_volume']).sum() / df['tick_volume'].sum()), 5)

    def calculate_vol2vol(self, spot_price, annual_iv):
        daily_sigma = spot_price * annual_iv * math.sqrt(1.0 / 365.0)
        return {
            'sigma1_upper': spot_price + daily_sigma,
            'sigma1_lower': spot_price - daily_sigma,
            'sigma2_upper': spot_price + (2.0 * daily_sigma),
            'sigma2_lower': spot_price - (2.0 * daily_sigma),
            'daily_move_pts': round(daily_sigma, 4)
        }

    def evaluate_asset(self, canonical_symbol, cfg, execute=True):
        broker_symbol = self.symbol_map.get(canonical_symbol, canonical_symbol)
        mt5.symbol_select(broker_symbol, True)
        tick = mt5.symbol_info_tick(broker_symbol)
        if not tick or tick.bid <= 0:
            return

        info = mt5.symbol_info(broker_symbol)
        spread = round(tick.ask - tick.bid, info.digits)
        if spread > cfg['max_spread_pts']:
            return

        magic = cfg['magic']

        # 1. Guardia anti-duplicación
        positions = mt5.positions_get(symbol=broker_symbol)
        if positions:
            active_gs = [p for p in positions if p.magic == magic or str(p.magic).startswith('88')]
            if active_gs:
                return

        # 2. Cooldown anti-ametralladora
        can_trade, cd_msg = self.check_cooldown(broker_symbol)
        if not can_trade:
            print(f"  [🛡️ COOLDOWN] {cfg['name']} ({broker_symbol}): {cd_msg}.")
            return

        # 3. Validación de Ventana de Oro
        in_session = self.is_in_golden_window(canonical_symbol, cfg)
        if in_session and self.has_traded_in_window(broker_symbol, magic, cfg):
            print(f"  [🏆 ONE BULLET] {cfg['name']} ({broker_symbol}): Trade ya ejecutado en esta ventana horaria.")
            return

        current_price = (tick.bid + tick.ask) / 2.0
        oi = self.fetch_oi_walls(cfg['cme_code'], cfg['cme_pid'], cfg['cme_pf'], current_price, cfg['annual_iv'])
        if not oi:
            return

        call_wall = oi['call_wall']
        put_wall = oi['put_wall']
        vwap = self.calculate_vwap(broker_symbol) or current_price
        v2v = self.calculate_vol2vol(current_price, cfg['annual_iv'])

        dist_call = call_wall - current_price
        dist_put = current_price - put_wall

        rates = mt5.copy_rates_from_pos(broker_symbol, mt5.TIMEFRAME_M5, 0, 3)
        if rates is None or len(rates) < 2:
            return
        last_c = rates[-1]
        prev_c = rates[-2]

        win_strs = [f"{int(s):02d}:00-{int(e):02d}:00 UTC" for s, e in cfg['windows_utc']]
        sess_label = f"Horas de Oro ({', '.join(win_strs)})"
        min_lot = self.get_min_divisible_lot(broker_symbol, cfg['fallback_lot'])

        print(f"\n[{cfg['name']}] {cfg['title']:<16} ({broker_symbol:<9}) | Magic: {magic} | Ventana: {sess_label} ({'ABIERTA' if in_session else 'CERRADA'})")
        print(f"  Spot: {current_price:<10} | VWAP: {vwap:<10} | Spread: {spread} | Lote: {min_lot}")
        print(f"  🛑 Call Wall: {call_wall} (+{abs(dist_call):.2f}) | 🛡️ Put Wall: {put_wall} (-{abs(dist_put):.2f})")
        print(f"  Vol2Vol 1σ: ±{v2v['daily_move_pts']} | 2σ Rango: [{v2v['sigma2_lower']:.2f} .. {v2v['sigma2_upper']:.2f}]")
        print(f"  🎯 Recorridos -> TP1 (50% Parcial): +{cfg['tp1_pts']} pts | TP2 (Final): +{cfg['tp2_pts']} pts | Trail: {cfg['trail_pts']} pts")

        if not in_session:
            print(f"  [Horario GS] Fuera de ventana de oro. Esperando apertura institucional.")
            return

        # 4. Filtro de Ruido de VWAP
        dist_from_vwap = abs(current_price - vwap)
        min_vwap_dist = current_price * 0.0010
        if canonical_symbol in ['USTEC', 'US30', 'US2000']:
            if dist_from_vwap < min_vwap_dist:
                print(f"  [🛡️ FILTRO RUIDO VWAP] {broker_symbol} pegado al VWAP ({dist_from_vwap:.2f} < {min_vwap_dist:.2f} pts). Esperando despegue.")
                return

        lots = min_lot

        # GATILLO 1: RECHAZO EN MURO + 2σ EXHAUSTION (SELL)
        if abs(dist_call) <= cfg['wall_zone_pts'] and current_price >= v2v['sigma1_upper']:
            has_wick = (last_c['high'] - max(last_c['open'], last_c['close'])) > abs(last_c['close'] - last_c['open'])
            if last_c['close'] < last_c['open'] or has_wick:
                sl_price = round(max(call_wall, v2v['sigma2_upper']) + (cfg['tp_buffer_pts'] * 1.5), info.digits)
                tp_dist = max(cfg['tp1_pts'] * 1.6, min(abs(current_price - vwap), cfg['tp2_pts']))
                tp_price = round(current_price - tp_dist, info.digits)
                comment = f"GS_{canonical_symbol}_SELL"[:31]
                print(f"[💥 GATILLO RECHAZO CALL] {broker_symbol} SELL @ {current_price} | Lotes: {lots} | Magic: {magic}")
                if execute:
                    self.send_order(broker_symbol, 'SELL', sl_price, tp_price, lots, comment, magic)
                return

        # GATILLO 2: RECHAZO EN MURO + 2σ EXHAUSTION (BUY)
        if abs(dist_put) <= cfg['wall_zone_pts'] and current_price <= v2v['sigma1_lower']:
            has_wick = (min(last_c['open'], last_c['close']) - last_c['low']) > abs(last_c['close'] - last_c['open'])
            if last_c['close'] > last_c['open'] or has_wick:
                sl_price = round(min(put_wall, v2v['sigma2_lower']) - (cfg['tp_buffer_pts'] * 1.5), info.digits)
                tp_dist = max(cfg['tp1_pts'] * 1.6, min(abs(vwap - current_price), cfg['tp2_pts']))
                tp_price = round(current_price + tp_dist, info.digits)
                comment = f"GS_{canonical_symbol}_BUY"[:31]
                print(f"[💥 GATILLO RECHAZO PUT] {broker_symbol} BUY @ {current_price} | Lotes: {lots} | Magic: {magic}")
                if execute:
                    self.send_order(broker_symbol, 'BUY', sl_price, tp_price, lots, comment, magic)
                return

        # GATILLO 3: IMÁN DE EXPANSIÓN ALCISTA HACIA CALL WALL (BUY)
        if dist_call >= cfg['min_expansion_pts'] and current_price > vwap and call_wall <= v2v['sigma2_upper']:
            if last_c['close'] > prev_c['high'] or current_price > last_c['open']:
                tp_dist = max(cfg['tp1_pts'] * 1.6, min(dist_call - cfg['tp_buffer_pts'], cfg['tp2_pts']))
                tp_price = round(current_price + tp_dist, info.digits)
                sl_pts = max(cfg['sl_min_pts'], min(current_price - vwap, cfg['sl_min_pts'] * 1.5))
                sl_price = round(current_price - sl_pts, info.digits)
                comment = f"GS_{canonical_symbol}_BUY_Mag"[:31]
                print(f"[🧲 GATILLO IMÁN ALCISTA] {broker_symbol} BUY @ {current_price} hacia Call Wall {call_wall} | Lotes: {lots} | Magic: {magic}")
                if execute:
                    self.send_order(broker_symbol, 'BUY', sl_price, tp_price, lots, comment, magic)
                return

        # GATILLO 4: IMÁN DE EXPANSIÓN BAJISTA HACIA PUT WALL (SELL)
        if dist_put >= cfg['min_expansion_pts'] and current_price < vwap and put_wall >= v2v['sigma2_lower']:
            if last_c['close'] < prev_c['low'] or current_price < last_c['open']:
                tp_dist = max(cfg['tp1_pts'] * 1.6, min(dist_put - cfg['tp_buffer_pts'], cfg['tp2_pts']))
                tp_price = round(current_price - tp_dist, info.digits)
                sl_pts = max(cfg['sl_min_pts'], min(vwap - current_price, cfg['sl_min_pts'] * 1.5))
                sl_price = round(current_price + sl_pts, info.digits)
                comment = f"GS_{canonical_symbol}_SELL_Mag"[:31]
                print(f"[🧲 GATILLO IMÁN BAJISTA] {broker_symbol} SELL @ {current_price} hacia Put Wall {put_wall} | Lotes: {lots} | Magic: {magic}")
                if execute:
                    self.send_order(broker_symbol, 'SELL', sl_price, tp_price, lots, comment, magic)
                return

        print(f"  [Estado] En rango normal. Sin desbalance institucional extremo.")

    def manage_partials_and_trailing(self):
        """Gestión 24/7 de Salida Parcial del 50% en TP1 y Trailing Stop Runner hacia TP2."""
        positions = mt5.positions_get()
        if not positions:
            return

        active_tickets = {str(p.ticket) for p in positions}
        keys_to_remove = [t for t in self.partial_closed if t not in active_tickets]
        if keys_to_remove:
            for t in keys_to_remove:
                del self.partial_closed[t]
            self._save_partial_state()

        # Invertir symbol_map para buscar config por broker_symbol
        rev_map = {v: k for k, v in self.symbol_map.items()}

        for p in positions:
            if not str(p.magic).startswith('88'):
                continue

            broker_sym = p.symbol
            canonical = rev_map.get(broker_sym, broker_sym)
            if canonical not in GOLDEN_CONFIG:
                continue

            cfg = GOLDEN_CONFIG[canonical]
            tp1_pts = cfg['tp1_pts']
            tp2_pts = cfg['tp2_pts']
            trail_pts = cfg['trail_pts']
            be_buffer = cfg['be_buffer_pts']

            tick = mt5.symbol_info_tick(broker_sym)
            info = mt5.symbol_info(broker_sym)
            if not tick or not info:
                continue

            is_buy = (p.type == mt5.ORDER_TYPE_BUY)
            cur_price = tick.bid if is_buy else tick.ask
            excursion_pts = (cur_price - p.price_open) if is_buy else (p.price_open - cur_price)

            t_key = str(p.ticket)
            already_partial = (t_key in self.partial_closed)

            # FASE 1: Toma del 50% en TP1
            if not already_partial:
                if excursion_pts >= tp1_pts:
                    step = info.volume_step
                    half_vol = p.volume / 2.0
                    close_vol = round(round(half_vol / step) * step, 2)

                    if close_vol >= info.volume_min and (round(p.volume - close_vol, 2) >= info.volume_min):
                        close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
                        close_price = tick.bid if is_buy else tick.ask
                        req = {
                            "action": mt5.TRADE_ACTION_DEAL,
                            "position": p.ticket,
                            "symbol": broker_sym,
                            "volume": float(close_vol),
                            "type": close_type,
                            "price": float(close_price),
                            "deviation": 10,
                            "magic": p.magic,
                            "comment": f"P50_{canonical}"[:31],
                            "type_time": mt5.ORDER_TIME_GTC,
                            "type_filling": mt5.ORDER_FILLING_IOC,
                        }
                        res = mt5.order_send(req)
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            self.partial_closed[t_key] = {
                                "symbol": broker_sym,
                                "open_price": p.price_open,
                                "closed_vol": close_vol,
                                "partial_time": datetime.now(timezone.utc).isoformat()
                            }
                            self._save_partial_state()
                            print(f"[💰 TOMA DE BENEFICIO 50%] Ticket #{p.ticket} ({broker_sym}): Cerrado 50% ({close_vol} lotes) con ganancia de +{excursion_pts:.2f} pts!")

                            # Trasladar inmediatamente SL a Break-Even + Buffer
                            new_sl = round(p.price_open + be_buffer, info.digits) if is_buy else round(p.price_open - be_buffer, info.digits)
                            sl_req = {
                                "action": mt5.TRADE_ACTION_SLTP,
                                "position": p.ticket,
                                "sl": float(new_sl),
                                "tp": float(p.tp)
                            }
                            sl_res = mt5.order_send(sl_req)
                            if sl_res and sl_res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"[🛡️ BREAK-EVEN] Ticket #{p.ticket} ({broker_sym}): SL protegido en {new_sl} (+{be_buffer} buffer). Runner 50% persiguiendo TP2 (+{tp2_pts} pts).")
            # FASE 2: Trailing Stop dinámico para el 50% Runner
            else:
                stop_dist = info.trade_stops_level * info.point
                if is_buy:
                    candidate_sl = round(cur_price - trail_pts, info.digits)
                    be_level = round(p.price_open + be_buffer, info.digits)
                    if candidate_sl > p.sl and candidate_sl >= be_level:
                        if (cur_price - candidate_sl) >= stop_dist:
                            req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(candidate_sl), "tp": float(p.tp)}
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"[🏃 TRAILING RUNNER] Ticket #{p.ticket} ({broker_sym}): SL avanzado a {candidate_sl} (+{excursion_pts:.2f} pts).")
                else:
                    candidate_sl = round(cur_price + trail_pts, info.digits)
                    be_level = round(p.price_open - be_buffer, info.digits)
                    if (p.sl == 0 or candidate_sl < p.sl) and candidate_sl <= be_level:
                        if (candidate_sl - cur_price) >= stop_dist:
                            req = {"action": mt5.TRADE_ACTION_SLTP, "position": p.ticket, "sl": float(candidate_sl), "tp": float(p.tp)}
                            res = mt5.order_send(req)
                            if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                                print(f"[🏃 TRAILING RUNNER] Ticket #{p.ticket} ({broker_sym}): SL avanzado a {candidate_sl} (+{excursion_pts:.2f} pts).")

    def send_order(self, broker_symbol, order_type, sl, tp, lots, comment, magic):
        tick = mt5.symbol_info_tick(broker_symbol)
        price = tick.ask if order_type.upper() == 'BUY' else tick.bid
        ot = mt5.ORDER_TYPE_BUY if order_type.upper() == 'BUY' else mt5.ORDER_TYPE_SELL
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": broker_symbol,
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
        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"[✅ DISPARO EJECUTADO] #{res.order} | {broker_symbol} {order_type} | Lotes: {res.volume} | SL: {sl} | TP: {tp} | Magic: {magic}")
        else:
            err = res.comment if res else "None"
            print(f"[-] Error enviando orden en {broker_symbol}: {err}")

    def run_cycle(self, execute=True):
        self.manage_partials_and_trailing()
        print("\n>>> [CICLO GOLDEN SNIPER] Escaneando los 6 Activos Campeones en Horas de Oro...")
        for canonical, cfg in GOLDEN_CONFIG.items():
            try:
                self.evaluate_asset(canonical, cfg, execute=execute)
            except Exception as e:
                print(f"[-] Error evaluando {canonical}: {e}")

    def run_daemon(self):
        print("\n" + "=" * 85)
        print("   INICIANDO OPERATIVA CONTINUA 24/7 EN VPS - GOLDEN SNIPER SUITE")
        print("   Solo 6 Activos Campeones | Lote Mínimo Divisible | 50% Parcial @ TP1")
        print(f"   Frecuencia de Escaneo: cada {MONITOR_INTERVAL_SECS} segundos")
        print("   Presione Ctrl + C para detener de forma segura.")
        print("=" * 85)
        try:
            while True:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{now_str}] Monitor Golden Sniper activo...")
                self.run_cycle(execute=True)
                time.sleep(MONITOR_INTERVAL_SECS)
        except KeyboardInterrupt:
            print("\n[*] Bot Golden Sniper detenido de forma segura.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Golden Sniper Suite - MT5 Multi-Broker")
    parser.add_argument('--daemon', action='store_true', help='Ejecución continua 24/7 en VPS')
    parser.add_argument('--audit', action='store_true', help='Auditoría de un solo ciclo en modo simulación (sin órdenes)')
    parser.add_argument('--run-once', action='store_true', help='Ejecución de un solo ciclo en vivo')
    args = parser.parse_args()

    bot = GoldenSniperBot()
    if bot.connect():
        if args.daemon:
            bot.run_daemon()
        elif args.audit:
            print("\n[AUDITORÍA / SIMULACIÓN] Golden Sniper Suite")
            bot.run_cycle(execute=False)
        else:
            bot.run_cycle(execute=True)
        bot.disconnect()

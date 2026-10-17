# CME Quantitative Trading Suite - IC Markets MT5

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![MetaTrader 5](https://img.shields.io/badge/MetaTrader-5-red.svg)](https://www.metatrader5.com/)
[![Broker: IC Markets](https://img.shields.io/badge/Broker-IC%20Markets%20Raw%20Spread-green.svg)](https://www.icmarkets.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Suite completa de trading algorítmico cuantitativo e institucional para **MetaTrader 5 (IC Markets)**, impulsada por microestructura del mercado, niveles de **Open Interest y Gamma del CME (Chicago Mercantile Exchange)**, análisis de cointegración estadística, posicionamiento del reporte **COT de la CFTC** y **coberturas delta/dólar-neutrales**.

---

## 🏛️ Arquitectura Cuantitativa

El ecosistema está compuesto por 5 motores cuantitativos independientes y sincronizados, orquestados por un despachador maestro con **gestión de riesgo y break-even 24/7**:

```
                               ┌─────────────────────────────────────────┐
                               │       MASTER INSTITUTIONAL BOT          │
                               │        master_institutional_bot.py      │
                               └────────────────────┬────────────────────┘
                                                    │
         ┌───────────────────┬──────────────────────┼──────────────────────┬───────────────────┐
         │                   │                      │                      │                   │
         ▼                   ▼                      ▼                      ▼                   ▼
┌─────────────────┐ ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ ┌─────────────────┐
│  TRINITY (LNY)  │ │  TRINITY (NY)   │    │    STAT-ARB     │    │   COT SQUEEZE   │ │ 6 CME HEDGES    │
│  London + NY    │ │  Solo NY Cash   │    │  Cointegration  │    │  Macro Spec PnL │ │ Institutional   │
│  [Magic: 71YY00]│ │  [Magic: 72YY00]│    │  [Magic: 73YY00]│    │  [Magic: 74YY00]│ │ [Magic: 75YY00] │
└─────────────────┘ └─────────────────┘    └─────────────────┘    └─────────────────┘ └─────────────────┘
         │                   │                      │                      │                   │
         └───────────────────┴──────────────────────┼──────────────────────┴───────────────────┘
                                                    │
                                                    ▼
                               ┌─────────────────────────────────────────┐
                               │   UNIVERSAL BREAKEVEN & TRAILING ENGINE │
                               │      (Protege Magics 7xxxxx 24/7)       │
                               └─────────────────────────────────────────┘
```

---

## 📊 Estrategias Integradas

### 1. The Institutional Trinity (Dual: LNY & Solo NY)
- **Archivo:** `strategy_trinity.py`
- **Fundamento Matemático:**
  - **Intraday VWAP:** Medición de desvío frente al precio ponderado por volumen institucional.
  - **CME Gamma Walls:** Detección de niveles máximos de Call/Put Open Interest extraídos de la cámara de compensación de CME QuikStrike.
  - **Vol2Vol Bands:** Bandas de volatilidad dinámica calculadas con la volatilidad realizada del activo.
- **Versiones:**
  - **LNY (London + New York):** Activo de 07:00 a 20:30 UTC. Captura el solapamiento europeo y la sesión americana.
  - **NY (Solo New York):** Activo de 13:30 a 20:30 UTC. Opera exclusivamente durante las horas regulares de contado (Cash Market NYSE).

### 2. Stat-Arb Cointegrated Multi-Pair Engine
- **Archivo:** `strategy_pair_trading.py`
- **Fundamento Matemático:** Arbitraje estadístico entre pares cointegrados mediante el modelo Engle-Granger / Johansen. Calcula el ratio de precios, media móvil de 40 periodos y desvío estándar, disparando entradas con **Z-Score $\ge 2.0\sigma$**.
- **Pares Operados:**
  - `USTEC / US500` (Nasdaq 100 vs S&P 500)
  - `US30 / US2000` (Dow Jones 30 vs Russell 2000)
  - `EURUSD / GBPUSD` (Euro vs Libra Esterlina)
  - `XAUUSD / XTIUSD` (Oro vs Petróleo WTI)

### 3. Macro COT Squeeze Engine
- **Archivo:** `strategy_cot_squeeze.py`
- **Fundamento Matemático:** Rastreo semanal del reporte **Commitments of Traders (COT)** de la CFTC. Cuando los *Non-Commercials* (grandes especuladores) acumulan extremos históricos ($\ge 75\%$ o $\le 25\%$), el motor espera una ruptura confirmada sobre el **VWAP Semanal** para unirse al movimiento de liquidación forzada (*Short/Long Squeeze*).

### 4. 6 Advanced CME Institutional Hedges
- **Archivo:** `strategy_institutional_hedges.py`
- **Portafolio de Coberturas:**
  1. **CVOL Skew Dispersion (`750100`):** Explotación de la prima de volatilidad implícita entre Oro (`XAUUSD`) y Euro (`EURUSD`).
  2. **Pace-of-Roll Liquidity (`750200`):** Cobertura de base entre futuros de `US500` y `USTEC` durante la semana de vencimiento trimestral.
  3. **FedWatch Parity Hedge (`750300`):** Descuento de expectativas de política monetaria de la Reserva Federal entre `USDJPY` y `XAUUSD`.
  4. **OPEX Max Pain Pinning (`750400`):** Atracción hacia el precio de mayor concentración de opciones en vencimientos semanales (Jueves y Viernes).
  5. **Brent vs WTI Crack Proxy (`750500`):** Arbitraje de reversión a la media física del spread de crudo (`XBRUSD` vs `XTIUSD`).
  6. **FX Swap Rate Basis Parity (`750600`):** Desviación del par sintético EUR/JPY mediante *cross-currency basis swaps*.

---

## 🛡️ Filtro de Horarios Institucionales & Anti-Rollover

Para evitar los drawdowns causados por spreads nocturnos abiertos y baja liquidez en la sesión asiática, la suite implementa ventanas estrictas de entrada institucional:

| Clase de Activo / Estrategia | Ventana de Entrada Permitida (UTC) | Justificación de Microestructura |
| :--- | :--- | :--- |
| **Índices EE.UU. (NY)** | **13:30 a 20:30 UTC** | Horario oficial NYSE/Nasdaq Cash Market. |
| **Índices EE.UU. (LNY)** | **07:00 a 20:30 UTC** | Apertura de Londres + New York Cash. |
| **Divisas Forex** | **07:00 a 17:00 UTC** | Máxima liquidez interbancaria (London / NY Overlap). |
| **Commodities (Oro / Petróleo)** | **08:00 a 19:30 UTC** | Sesión de corros COMEX y NYMEX. |
| **Cripto (Bitcoin Futures)** | **24/7** | Mercado continuo (excepto filtro de rollover). |
| **Bloqueo Anti-Rollover** | **20:55 a 22:30 UTC (TODOS)** | Bloquea aperturas durante el ensanchamiento de spreads y cobro de swaps de IC Markets. |

> [!NOTE]
> **Gestión de Salidas 24/7:** Las órdenes abiertas nunca se quedan desatendidas. El motor de Break-Even dinámico y Trailing Stop opera ininterrumpidamente las 24 horas del día.

---

## 🏷️ Taxonomía de Magic Numbers y Comentarios

Cada orden enviada por el sistema tiene un identificador único para auditoría contable y gestión independiente de riesgo:

| Módulo | Formato Magic | Ejemplos | Formato de Comentario |
| :--- | :--- | :--- | :--- |
| **Trinity LNY** | `71YY00` | `710100` (Nasdaq), `710500` (Oro) | `TR_LNY_{ACTIVO}_{B/S}` |
| **Trinity NY** | `72YY00` | `720100` (Nasdaq), `720500` (Oro) | `TR_NY_{ACTIVO}_{B/S}` |
| **Stat-Arb** | `732P00` | `732100` (NQ/ES), `732300` (EUR/GBP) | `SA_{PAR}_{SYM}_{B/S}` |
| **COT Squeeze** | `74YY00` | `740100` (Nasdaq), `741100` (Bitcoin) | `COT_{ACTIVO}_{B/S}` |
| **Hedges CME** | `750E00` | `750100` (CVOL), `750500` (Crack) | `HDG_{ESTRATEGIA}_{SYM}_{B/S}` |

**Código de Activos (`YY`):**
`01`=USTEC, `02`=US500, `03`=US30, `04`=US2000, `05`=XAUUSD, `06`=XTIUSD, `07`=XNGUSD, `08`=EURUSD, `09`=GBPUSD, `10`=USDJPY, `11`=BTCUSD.

---

## 💻 Instalación Rápida en Cualquier Computadora / VPS

### Requisitos Previos
1. **Sistema Operativo:** Windows 10, 11 o Windows Server 2019/2022.
2. **Python:** 3.10 o superior (marcar la casilla *"Add Python to PATH"* durante la instalación).
3. **MetaTrader 5:** Instalado con cuenta demo o real de **IC Markets** (cuenta Raw Spread recomendada).

### Paso 1: Clonar el Repositorio
Abre la terminal (PowerShell o CMD) y clona el proyecto:
```bash
git clone https://github.com/enfocadosenfocados-bot/CME-TRADING.git
cd CME-TRADING
```

### Paso 2: Instalación Automática de Librerías
Haz doble clic en **`install.bat`** (o ejecuta en PowerShell: `.\install.ps1`).

El script instalará automáticamente:
- `MetaTrader5`
- `pandas`
- `numpy`
- `requests`
- `scipy`

### Paso 3: Configurar MetaTrader 5
1. Abre tu terminal **MetaTrader 5**.
2. Ve a **Herramientas > Opciones > Asesores Expertos** (Tools > Options > Expert Advisors).
3. Marca las siguientes casillas:
   - ✅ **Permitir trading algorítmico** (Allow Algo Trading).
   - ✅ **Permitir importación de DLL** (Allow DLL imports).
4. Asegúrate de que el botón **Algo Trading** en la barra superior esté en color **Verde**.

---

## 🚀 Modos de Ejecución

Inicia el lanzador maestro haciendo doble clic en **`run_master_vps.bat`**:

```
===============================================================================
    CME INSTITUTIONAL QUANT SUITE - IC MARKETS MT5 AUTONOMOUS TRADER
===============================================================================

 Seleccione la estrategia cuantitativa que desea ejecutar:

  [1] TRINITY [LNY]: Sesion Londres + Nueva York (07:00 a 20:30 UTC) [Magic: 71YY00]
  [2] TRINITY [NY] : Sesion Solo Nueva York      (13:30 a 20:30 UTC) [Magic: 72YY00]
  [3] TRINITY DUAL : Ambas Sesiones en Paralelo                      [Magics 71/72]
  [4] STAT-ARB     : Multi-Par Cointegrado (4 Pares Market-Neutral)  [Magic: 73YY00]
  [5] COT SQUEEZE  : Macro COT Squeeze & Momentum (11 Activos CME)   [Magic: 74YY00]
  [6] HEDGES CME   : 6 Coberturas Institucionales (CVOL, Roll, etc)  [Magic: 75YY00]
  [7] SUITE MASTER TOTAL (Todas las estrategias integradas 24/7)     [RECOMENDADO]
  [8] SUITE MASTER LNY   (Trinity LNY + Stat-Arb + COT + 6 Hedges)
  [9] SUITE MASTER NY    (Trinity NY  + Stat-Arb + COT + 6 Hedges)
  [A] AUDITORIA EN VIVO  (Escanear todo el universo sin enviar ordenes)
  [0] SALIR
```

### Opciones Recomendadas:
- **`[7] SUITE MASTER TOTAL`**: Ejecución continua 24/7 en segundo plano con todas las estrategias activadas y protegidas.
- **`[A] AUDITORIA EN VIVO`**: Simula una pasada por todos los activos sin enviar órdenes reales al broker para verificar conexión y niveles de precios.

---

## 📈 Rendimiento y Auditoría de Trades

En pruebas y operativas de cuenta real/demo ($25,000 USD):
- **Estrategias con mayor rentabilidad:**
  - Cointegración `XAUUSD / XTIUSD` (+$804.00 USD netos).
  - Momentum de VWAP `GBPUSD` (+$763.00 USD netos).
  - Liquidación COT en `BTCUSD` (+$396.00 USD con Stop Loss en Break-Even asegurado).
- **Control de Riesgo:** El algoritmo bloquea el 100% de operaciones cruzadas de índices fuera de sesión, eliminando las pérdidas acumulativas nocturnas por ensanchamiento de spreads.

---

## 📜 Licencia

Distribuido bajo la licencia MIT. Consulta el archivo `LICENSE` para más detalles.

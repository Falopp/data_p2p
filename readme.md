<div align="center">
  <img src="URL_DE_TU_LOGO_O_IMAGEN_AQUI" alt="Logo del Proyecto" width="150"/>
  <h1>🚀 Motor de Análisis Avanzado de Datos P2P 📊</h1>
  <p>
    <strong>Transforma tus datos de transacciones Peer-to-Peer (P2P) en información accionable y estratégica.</strong>
  </p>
  <p>
    <!-- Badges (ejemplos, reemplaza con los tuyos) -->
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+"/>
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License: MIT"/>
    <!-- Añade más badges según sea necesario: build status, version, etc. -->
  </p>
</div>

Este proyecto proporciona una potente herramienta de línea de comandos (CLI) para el análisis exhaustivo de operaciones P2P exportadas desde plataformas de intercambio. Aprovechando la velocidad de Polars para un procesamiento de datos ultraeficiente, genera métricas financieras detalladas, tablas de resumen, visualizaciones impactantes (creadas con `matplotlib`, `seaborn` y `plotly`) y reportes HTML interactivos.

Obtén una comprensión granular de tu historial de _trading_, segmentado por el conjunto completo de datos, por año y, adicionalmente, por el estado de las órdenes (Completadas, Canceladas, Todas). Ideal para optimizar estrategias, preparar declaraciones fiscales o simplemente mantener un registro meticuloso de tus actividades P2P.

<!-- Opcional: Añadir un GIF de demostración aquí -->
<!--
<div align="center">
  <img src="URL_DEL_GIF_DEMOSTRATIVO" alt="Demostración del Analizador P2P" width="600"/>
</div>
-->

## 📜 Tabla de Contenidos

*   [✨ Características Destacadas](#-características-destacadas)
*   [🎯 ¿Por qué este Proyecto?](#-por-qué-este-proyecto)
*   [🎬 Guía de Inicio Rápido](#-guía-de-inicio-rápido)
    *   [Prerrequisitos](#prerrequisitos)
    *   [Instalación](#instalación)
    *   [Ejecución Básica](#ejecución-básica)
    *   [Explorando tus Resultados](#explorando-tus-resultados-)
*   [📖 Guía Detallada](#-guía-detallada)
    *   [🏗️ Estructura del Proyecto](#️-estructura-del-proyecto)
    *   [⚙️ Configuración Avanzada (`config.yaml`)](#️-configuración-avanzada-configyaml)
    *   [⌨️ Argumentos de Línea de Comandos (CLI)](#️-argumentos-de-línea-de-comandos-cli)
    *   [🌊 Flujo del Análisis](#-flujo-del-análisis)
    *   [📊 Tipos de Gráficos Generados](#-tipos-de-gráficos-generados)
*   [🛠️ Funcionalidades Avanzadas y Detalles Técnicos](#️-funcionalidades-avanzadas-y-detalles-técnicos)
    *   [Arquitectura Detallada del Código Fuente (`src/`)](#arquitectura-detallada-del-código-fuente-src)
    *   [🔑 Mapeo de Columnas y Columnas Internas Clave](#-mapeo-de-columnas-y-columnas-internas-clave)
    *   [📈 Métricas Calculadas Clave](#-métricas-calculadas-clave)
*   [👨‍💻 Contribuir y Desarrollar](#-contribuir-y-desarrollar)
*   [🔗 Dependencias Clave](#-dependencias-clave)
*   [📜 Licencia](#-licencia)

## ✨ Características Destacadas

*   **🚀 Rendimiento Superior:** Procesamiento ultra-rápido de grandes volúmenes de datos gracias a **Polars**.
*   **⚙️ Altamente Configurable:** Adapta el análisis con argumentos CLI flexibles y un archivo de configuración `config.yaml` personalizable.
*   **💡 Análisis Multi-dimensional:** Desglosa tus datos por año, estado de orden (Completadas, Canceladas, Todas) y múltiples filtros.
*   **📄 Formatos de Salida Versátiles:** Exporta resultados a CSV, PNG (gráficos estáticos) y reportes HTML interactivos.
*   **📊 Visualizaciones Enriquecedoras:** Una suite completa de gráficos para entender tus datos, incluyendo:
    *   Tendencias temporales (horarias, mensuales, diarias).
    *   Distribuciones de precios y volúmenes.
    *   Análisis de métodos de pago.
    *   Mapas de calor de actividad.
    *   Diagramas Sankey interactivos (Flujo Fiat ↔ Activo).
    *   Comparativas interanuales (YoY).
    *   *¡Y mucho más!*
*   **🔎 Analítica Avanzada:**
    *   Seguimiento de precios máximos y mínimos intradía.
    *   Análisis del tiempo entre operaciones (TBT).
    *   Cálculo de P&L (Pérdidas y Ganancias) y Ratio de Sharpe en ventanas móviles.
    *   Detección de estacionalidad en volumen (FFT) y outliers en precios (`IsolationForest`).
    *   Identificación de "Whale Trades" (operaciones de gran volumen).
    *   Análisis comparativo antes/después de una fecha de evento específica.
    *   Análisis detallado de contrapartes, incluyendo clasificación VIP.
    *   Análisis de sesiones de _trading_.
*   **📁 Salida Organizada:** Estructura de directorios clara y predecible para todos los archivos generados.
*   **💼 Exportación a Excel:** Consolida métricas clave en un archivo Excel multi-hoja.

## 🎯 ¿Por qué este Proyecto?

El _trading_ P2P genera una gran cantidad de datos que, sin las herramientas adecuadas, pueden ser difíciles de interpretar. Este motor de análisis fue creado para:

*   **Ahorrar Tiempo:** Automatiza el tedioso proceso de limpieza, procesamiento y análisis de datos.
*   **Proporcionar Claridad:** Ofrece una visión profunda y segmentada de tu actividad de _trading_.
*   **Facilitar la Toma de Decisiones:** Permite identificar patrones, optimizar estrategias y entender mejor tu rendimiento.
*   **Simplificar la Declaración de Impuestos:** Ayuda a consolidar la información necesaria para fines fiscales.
*   **Mantener un Control Profesional:** Lleva un registro detallado y organizado de todas tus operaciones.

## 🎬 Guía de Inicio Rápido

### Prerrequisitos

*   Python 3.8 o superior.
*   PIP (manejador de paquetes de Python).
*   Git (para clonar el repositorio).

### Instalación

1.  **Clonar el Repositorio:**
    ```bash
    git clone https://github.com/Falopp/data_p2p.git
    cd data_p2p
    ```
2.  **Crear y Activar un Entorno Virtual (Recomendado):**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```
3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    Esto instalará todas las librerías necesarias (Polars, Pandas, Matplotlib, Seaborn, Plotly, etc.).

### Ejecución Básica

1.  Coloca tu archivo de datos de transacciones P2P (en formato CSV) en la carpeta `data/`. Por ejemplo, `data/mis_transacciones.csv`.
2.  Asegúrate de que tu archivo `config.yaml` (o la configuración por defecto en `src/config_loader.py`) mapee correctamente las columnas de tu CSV.
3.  Ejecuta el script desde el directorio raíz del proyecto:
    ```bash
    python src/app.py --csv data/mis_transacciones.csv
    ```
    Este comando iniciará el análisis completo, generando resultados para el conjunto total de datos y para cada año presente.

### Explorando tus Resultados 🧭

Los resultados se organizan de forma clara en el directorio `output/`:

```
output/
├── (General)/            # Análisis para la configuración general de filtros CLI
│   ├── 2023/             # Ejemplo para un año específico
│   │   ├── completadas/  # Solo órdenes 'Completadas'
│   │   │   ├── figures/      # Gráficos PNG
│   │   │   ├── reports/      # Reportes HTML interactivos
│   │   │   └── tables/       # Tablas de métricas CSV
│   │   ├── canceladas/   # Solo órdenes 'Canceladas' (misma estructura)
│   │   └── todas/        # Todas las órdenes (misma estructura)
│   ├── total/            # Análisis del conjunto de datos completo para esta categoría
│   │   └── ...           # (misma estructura que un año)
│   └── consolidated/     # Reportes y datos consolidados para la categoría (General)
│       ├── figures/
│       ├── reports/
│       └── data_exports/
└── ...                   # Otras categorías si se definen en el futuro
```

*   **`figures/`**: Gráficos estáticos en formato PNG.
*   **`reports/`**: Reportes HTML interactivos que consolidan métricas y visualizaciones.
*   **`tables/`**: Tablas de métricas detalladas en formato CSV.
*   **`consolidated/`**: Contiene reportes unificados y exportaciones (como el Excel) que abarcan múltiples periodos/estados dentro de una categoría de análisis.

---

## 📖 Guía Detallada

### 🏗️ Estructura del Proyecto

```
.
├── data/                     # Directorio para tus archivos CSV de entrada
├── output/                   # Directorio donde se guardan todos los resultados
├── src/                      # Código fuente de la aplicación
│   ├── app.py                # Punto de entrada principal (CLI)
│   ├── main_logic.py         # Orquesta el flujo de análisis principal
│   ├── analyzer.py           # Lógica de cálculo de métricas
│   ├── counterparty_analyzer.py # Análisis específico de contrapartes
│   ├── session_analyzer.py   # Análisis específico de sesiones de trading
│   ├── plotting.py           # Funciones para generar gráficos generales
│   ├── counterparty_plotting.py # Funciones para gráficos de contrapartes
│   ├── reporter.py           # Genera archivos de salida (tablas, HTML individuales)
│   ├── unified_reporter.py   # Genera reportes HTML y Excel consolidados
│   ├── finance_utils.py      # Utilidades para cálculos financieros
│   ├── config_loader.py      # Carga y gestiona la configuración
│   └── utils.py              # Funciones de utilidad general
├── templates/                # Plantillas HTML para los reportes
│   ├── report_template.html
│   └── unified_report_template.html
├── config.yaml               # Archivo de configuración personalizado (opcional)
├── requirements.txt          # Dependencias de Python
└── README.md                 # Este archivo
```

### ⚙️ Configuración Avanzada (`config.yaml`)

Personaliza el análisis creando un archivo `config.yaml` en la raíz del proyecto o especificando una ruta con `--config`. Este archivo sobrescribe la configuración por defecto (ver `src/config_loader.py DEFAULT_CONFIG`).

**Secciones Clave:**

*   **`column_mapping`**: **¡Esencial!** Mapea los nombres de las columnas de tu CSV a los nombres internos que espera el script.
    *   Formato: `nombre_interno_script: "Nombre Columna CSV"`
    *   **Acción Requerida:** Revisa y ajusta esta sección según tu archivo CSV. Columnas críticas incluyen: fecha/hora, tipo de activo (ej. USDT), fiat (ej. USD), precio, cantidad, monto total, estado, tipo de orden, método de pago, contraparte y comisiones.
*   **`sell_operation`**: Define cómo identificar operaciones de venta (usado para resúmenes de venta).
    *   `indicator_column`: Nombre interno de la columna (ej. `order_type`).
    *   `indicator_value`: Valor que indica venta (ej. `SELL`).
*   **`status_categories_map`** (Definido internamente, no en `config.yaml` por ahora): Agrupa valores de estado de tu CSV en categorías estandarizadas (`completadas`, `canceladas`, `pendientes_o_apelacion`). La lógica actual en `app.py` y `main_logic.py` maneja "Completed" y "Cancelled" principalmente.
*   **Configuraciones de Filtros y Gráficos:** Parámetros para umbrales de outliers, N principales en gráficos, etc. (Algunos gestionados vía CLI).
*   **`html_report`**: (En `DEFAULT_CONFIG`) Define qué tablas y figuras se incluyen por defecto en los reportes HTML individuales.

**Ejemplo de `column_mapping` en `config.yaml`:**
```yaml
column_mapping:
  order_number: "Order Number"       # Número de Orden
  order_type: "Order Type"         # Tipo: BUY/SELL
  asset_type: "Asset Type"         # Activo: USDT, BTC
  fiat_type: "Fiat Type"           # Fiat: USD, UYU
  total_price: "Total Price"       # Monto total en fiat
  price: "Price"                   # Precio unitario del activo
  quantity: "Quantity"             # Cantidad del activo
  status: "Status"                 # Estado: Completed, Cancelled
  match_time_utc: "Match time(UTC)" # Fecha y hora (UTC)
  payment_method: "Payment Method"   # Método de Pago
  counterparty: "Counterparty"       # Contraparte
  maker_fee: "Maker Fee"           # Comisión Maker
  taker_fee: "Taker Fee"           # Comisión Taker
```

### ⌨️ Argumentos de Línea de Comandos (CLI)

Controla el análisis con los siguientes argumentos:

| Argumento                       | Descripción                                                                                                                               | Ejemplo                                               |
| :------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------- |
| `--csv RUTA_CSV`                | **(Obligatorio)** Ruta a tu archivo CSV.                                                                                                  | `--csv data/p2p_data.csv`                             |
| `--out DIR_SALIDA`              | Directorio base para guardar resultados (Default: `output/`).                                                                             | `--out resultados_analisis/`                          |
| `--config RUTA_YAML`            | Ruta a un `config.yaml` personalizado.                                                                                                    | `--config mi_config.yaml`                             |
| `--log-level NIVEL`             | Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL).                                                                                 | `--log-level DEBUG`                                   |
| `--fiat_filter FIAT [FIAT ...]` | Filtra datos por uno o más tipos de moneda fiat (ej. USD, UYU) **antes** del análisis.                                                    | `--fiat_filter USD UYU`                               |
| `--asset_filter ACTIVO [ACTIVO ...]`| Filtra datos por uno o más tipos de activo (ej. USDT, BTC) **antes** del análisis.                                                      | `--asset_filter USDT`                                 |
| `--status_filter ESTADO [ESTADO ...]`| Filtra por uno o más estados de orden (ej. Completed) **antes** del análisis.                                                       | `--status_filter Completed`                           |
| `--payment_method_filter METODO [METODO ...]`| Filtra por uno o más métodos de pago.                                                                                     | `--payment_method_filter "Banco X"`                   |
| `--mes MES`                     | Analiza solo un mes específico (nombre en español/inglés o número 1-12).                                                                  | `--mes mayo` o `--mes 5`                              |
| `--event_date AAAA-MM-DD`       | (Experimental) Fecha para análisis comparativo Antes/Después.                                                                             | `--event_date 2023-10-28`                           |
| `--no-annual-breakdown`         | No generar análisis anuales individuales, solo el "total" global y por categoría.                                                         | `--no-annual-breakdown`                             |
| `--year AÑO`                    | Analiza un año específico (ej. 2023) o "all". Si se omite, analiza todos los años y "total".                                              | `--year 2023`                                         |
| `--unified-only`                | Genera solo el reporte unificado global y sale (experimental).                                                                            | `--unified-only`                                      |
| `--no-unified-report`           | Omite la generación del reporte unificado global.                                                                                         | `--no-unified-report`                                 |
| `--detect-outliers`             | Activa la detección de outliers en precios (`IsolationForest`).                                                                           | `--detect-outliers`                                   |
| `--outliers_contamination VAL`  | Parámetro 'contamination' para `IsolationForest` (Default: `auto`).                                                                     | `--outliers_contamination 0.01`                       |
| `--outliers_n_estimators NUM`   | Número de estimadores para `IsolationForest` (Default: `100`).                                                                          | `--outliers_n_estimators 150`                         |
| `--outliers_random_state SEED`  | Semilla aleatoria para `IsolationForest` (Default: `42`).                                                                               | `--outliers_random_state 0`                           |
| `--interactive`                 | (Futuro) Habilitar interactividad Plotly en reportes HTML individuales (el reporte unificado ya usa Plotly).                             | `--interactive`                                       |

### 🌊 Flujo del Análisis

1.  **Carga y Configuración Inicial (`app.py`, `main_logic.py`):**
    *   Parseo de argumentos CLI.
    *   Carga de configuración (`config.yaml` o por defecto).
    *   Lectura del CSV con Polars.
    *   Renombrado de columnas según `column_mapping`.
    *   Aplicación de filtros globales iniciales (fiat, asset, status, etc., desde CLI).
    *   Pre-procesamiento de columnas de tiempo (conversión a datetime, extracción de año, mes, hora, etc.).
2.  **Pipeline de Análisis Principal (`main_logic.execute_analysis`):**
    *   Se determinan los **periodos** a analizar: "total" (todos los datos post-filtro CLI) y cada año individual (a menos que se indique lo contrario con `--no-annual-breakdown` o un `--year` específico).
    *   Para cada **periodo** (ej. "total", "2023"):
        *   Se itera sobre las **categorías de estado** predefinidas: `todas`, `completadas`, `canceladas`.
        *   Se filtra el DataFrame del periodo actual para obtener el subconjunto de datos del estado actual.
        *   Si hay datos:
            *   Se invoca `analyzer.analyze()` para calcular métricas detalladas. Esto incluye la llamada a `counterparty_analyzer.analyze_counterparties()` y `session_analyzer.analyze_trading_sessions()`.
            *   Se invoca `reporter.save_outputs()` para generar:
                *   Tablas de resumen en CSV.
                *   Gráficos (PNG) usando `plotting.py` y `counterparty_plotting.py`.
                *   Un reporte HTML individual para ese [periodo]-[estado].
3.  **Reporte Unificado (Opcional, `main_logic.py` -> `unified_reporter.py`):**
    *   Si no se especifica `--no-unified-report`, se recopilan todos los datos y métricas generados.
    *   `UnifiedReporter` genera:
        *   Gráficos consolidados y comparativos.
        *   Un reporte HTML unificado que incluye todos los análisis.
        *   Un archivo Excel (`.xlsx`) multi-hoja con métricas clave.

### 📊 Tipos de Gráficos Generados

La herramienta produce una amplia variedad de gráficos. Algunos ejemplos clave:

*   **Generales (en `plotting.py`):**
    *   Actividad horaria, mensual y por día de la semana.
    *   Distribuciones de precios (histogramas, boxplots).
    *   Volumen vs. Precio (scatter plot).
    *   Evolución de precios y volúmenes a lo largo del tiempo (con medias móviles).
    *   Precio vs. Método de Pago (boxplot/violin).
    *   Mapas de calor de actividad (hora/día).
    *   Análisis de comisiones.
    *   Diagramas Sankey (Flujo Fiat ↔ Activo).
    *   Comparativas Anuales (YoY).
    *   Scatter plot animado de Precio/Volumen (Plotly).
*   **De Contrapartes (en `counterparty_plotting.py`):**
    *   Ranking de contrapartes por volumen.
    *   Scatter plot de volumen vs. frecuencia.
    *   Distribución de Tiers VIP (barras y circular).
    *   Heatmap de preferencias de métodos de pago.
    *   Timeline de evolución temporal de actividad.
    *   Scatter plot de eficiencia vs. volumen.
    *   Radar de patrones de trading.
*   **De Sesiones (Integrados en reportes, lógica en `session_analyzer.py`):**
    *   Características de las sesiones, patrones, eficiencia.

---

## 🛠️ Funcionalidades Avanzadas y Detalles Técnicos

### Arquitectura Detallada del Código Fuente (`src/`)

*   **`app.py`**: Entrada CLI, carga inicial de datos, pre-procesamiento básico, orquestación de alto nivel.
*   **`main_logic.py`**: Controla el pipeline de análisis iterando por periodos (años, total) y estados (completadas, etc.). Llama a `analyzer` y `reporter`. Inicia el `UnifiedReporter`.
*   **`analyzer.py`**: Corazón del análisis. Transforma datos, calcula una amplia gama de métricas agregadas y avanzadas. Llama a los analizadores específicos.
*   **`counterparty_analyzer.py`**: Lógica específica para analizar datos de contrapartes, incluyendo la identificación de VIPs y cálculo de estadísticas relacionadas.
*   **`session_analyzer.py`**: Identifica y analiza sesiones de _trading_ basadas en la inactividad entre operaciones.
*   **`plotting.py`**: Funciones para generar los gráficos generales usando Matplotlib, Seaborn y Plotly.
*   **`counterparty_plotting.py`**: Funciones para generar gráficos específicos del análisis de contrapartes.
*   **`reporter.py`**: Genera los archivos de salida para cada sub-análisis individual (tablas CSV, figuras PNG, reportes HTML individuales).
*   **`unified_reporter.py`**: Consolida todos los resultados de `main_logic` para generar un reporte HTML global interactivo y un archivo Excel.
*   **`finance_utils.py`**: Funciones para cálculos financieros como P&L y Ratio de Sharpe.
*   **`config_loader.py`**: Carga la configuración por defecto y la fusiona con el `config.yaml` del usuario.
*   **`utils.py`**: Funciones de utilidad general (parseo de montos, sanitización de nombres de archivo, etc.).

### 🔑 Mapeo de Columnas y Columnas Internas Clave

La sección `column_mapping` en `config.yaml` es crucial. Permite al script adaptarse a diferentes formatos de CSV.

**Columnas Internas Importantes (generadas o estandarizadas por `analyzer.py`):**

*   `Price_num`, `Quantity_num`, `TotalPrice_num`: Versiones numéricas de las columnas de entrada.
*   `TotalPrice_USD_equivalent`: `TotalPrice_num` convertido a un equivalente en USD para análisis combinados.
*   `TotalFee`: Suma de comisiones.
*   `Match_time_local`: Fecha/hora de la operación en zona horaria local (America/Montevideo por defecto).
*   `hour_local`, `YearMonthStr`, `Year`, `weekday_local`, `date_local`: Componentes de tiempo extraídos.
*   `order_type`: Estandarizado a 'BUY' o 'SELL'.
*   `Status_cleaned`: Estado de la orden limpio (ej. "Completed", "Cancelled").
*   `is_whale_trade`: Booleano que indica si la operación es excepcionalmente grande.
*   `is_outlier_price`: Booleano (si `--detect-outliers`) que indica si el precio es un outlier.
*   Columnas de `vip_tier` y `vip_score` en los datos de contrapartes.
*   Columnas de `session_id` y métricas de sesión si el análisis de sesiones está activo.

### 📈 Métricas Calculadas Clave

El módulo `analyzer.py` (y los sub-analizadores) calculan una gran cantidad de métricas, algunas de las cuales son:

*   **Generales:** `asset_stats`, `fiat_stats`, `price_stats`, `fees_stats`, `monthly_fiat`, `hourly_counts`, `status_counts`.
*   **Contrapartes:** `general_stats` (volumen, operaciones, etc. por contraparte), `temporal_evolution`, `payment_preferences`, `trading_patterns`, `vip_counterparties` (con `vip_tier`, `vip_score`), `efficiency_stats`.
*   **Sesiones:** `session_summary`, `session_duration_distribution`, `ops_per_session_distribution`, `volume_per_session_distribution`, `inter_session_gap_distribution`, etc.
*   **Avanzadas:** High/Low intradía, TBT, P&L rodante, Sharpe, Estacionalidad FFT, Outliers de precio, Índice de Liquidez, Whale Trades, Comparación Antes/Después de evento.

---

## 👨‍💻 Contribuir y Desarrollar

¡Las contribuciones son bienvenidas!

1.  Realiza un Fork del repositorio.
2.  Crea una nueva rama para tu funcionalidad (`git checkout -b feature/nueva-funcionalidad`).
3.  Realiza tus cambios y haz commit (`git commit -am 'Añade nueva funcionalidad X'`).
4.  Empuja tus cambios a la rama (`git push origin feature/nueva-funcionalidad`).
5.  Abre un Pull Request.

Por favor, asegúrate de que tu código sigue las guías de estilo y añade pruebas si es aplicable.

## 🔗 Dependencias Clave

Este proyecto se apoya en las siguientes librerías principales (ver `requirements.txt` para la lista completa):

*   **Polars:** Para manipulación de DataFrames de alto rendimiento.
*   **Pandas:** Para compatibilidad con algunas bibliotecas y exportación a Excel.
*   **Matplotlib & Seaborn:** Para gráficos estáticos.
*   **Plotly:** Para gráficos interactivos.
*   **NumPy:** Para cálculos numéricos.
*   **Scikit-learn:** Para `IsolationForest` (detección de outliers).
*   **Jinja2:** Para plantillas HTML.
*   **Openpyxl:** Para escribir archivos Excel (`.xlsx`).


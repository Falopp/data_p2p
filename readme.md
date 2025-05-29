# 🚀 Motor de Análisis Avanzado de Datos P2P 📊

**¡Transforma tus datos de transacciones Peer-to-Peer (P2P) en información accionable y estratégica!**

Este proyecto proporciona una potente herramienta de línea de comandos (CLI) para el análisis exhaustivo de operaciones P2P exportadas desde plataformas de intercambio. Aprovechando la velocidad de Polars para un procesamiento de datos ultraeficiente, genera métricas financieras detalladas, tablas de resumen, visualizaciones impactantes (creadas con `matplotlib`, `seaborn` y `plotly`) y reportes HTML interactivos.

Obtén una comprensión granular de tu historial de _trading_, segmentado por el conjunto completo de datos, por año y, adicionalmente, por el estado de las órdenes (Completadas, Canceladas, Todas). Ideal para optimizar estrategias, preparar declaraciones fiscales o simplemente mantener un registro meticuloso de tus actividades P2P.

## ✨ Características Destacadas

* **⚙️ Altamente Configurable:** Adapta el análisis con una amplia gama de argumentos CLI y un flexible archivo de configuración YAML.
* **🚀 Automatizado y Veloz:** Olvídate del procesamiento manual. Polars garantiza un análisis de alta velocidad, incluso con grandes volúmenes de datos.
* **💡 Información Granular:** Analiza tus datos por año y por estado de orden (Completadas, Canceladas, Todas).
* **📄 Múltiples Formatos de Salida:** Obtén tus resultados en CSV, PNG (gráficos estáticos) y reportes HTML interactivos.
* **📈 Visualizaciones Enriquecedoras:** Una completa suite de gráficos que incluye:
    * Tendencias de actividad horaria y mensual.
    * Distribuciones de precios y su evolución.
    * Análisis de volumen contra precio y tiempo.
    * Comparativas de métodos de pago.
    * Mapas de calor de actividad (hora/día).
    * Diagramas Sankey interactivos (flujo Fiat ↔ Activo).
    * *¡Y muchos más!*
* **🔎 Analítica Avanzada:**
    * Seguimiento de precios máximos y mínimos intradía.
    * Análisis del tiempo entre operaciones (TBT).
    * Cálculo de P&L (Pérdidas y Ganancias) y Ratio de Sharpe en ventanas móviles (ej. 7 días).
    * Detección de estacionalidad en el volumen usando FFT.
    * Detección de outliers en precios con `IsolationForest`.
    * Identificación de "Whale Trades" (operaciones de gran volumen).
    * Análisis comparativo antes y después de una fecha de evento específica.
* **📁 Salida Organizada:** Estructura de directorios clara y predecible para todos los archivos generados.
* **💼 Exportación a Excel:** Consolida métricas clave en un archivo Excel multi-hoja para compartir y analizar fácilmente.

## 🎬 Guía de Inicio Rápido

¡Pon en marcha el análisis en cuestión de minutos!

### 1. Prerrequisitos

* Python 3.8 o superior.
* PIP (manejador de paquetes de Python).

### 2. Configuración

1.  **Clonar el Repositorio (Opcional):**
    ```bash
    git clone [https://github.com/Falopp/data_p2p](https://github.com/Falopp/data_p2p)
    cd data_p2p
    ```
2.  **Crear y Activar un Entorno Virtual (Recomendado):**
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # macOS/Linux
    source .venv/bin/activate
    ```
3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    Esto instalará todas las librerías necesarias, incluyendo Polars, Pandas, Matplotlib, Seaborn, Plotly, NumPy, Scikit-learn y Jinja2.

### 3. Ejecución Básica

1.  Coloca tu archivo de datos de transacciones P2P (en formato CSV) en la carpeta `data/`. Por ejemplo, `data/mis_transacciones_p2p.csv`.
2.  Ejecuta el script desde el directorio raíz del proyecto:
    ```bash
    python src/app.py --csv data/mis_transacciones_p2p.csv
    ```
    Este comando iniciará el análisis para el conjunto completo de datos y para cada año presente en tus datos.

### 4. Explorando tus Resultados 🧭

Los resultados se organizan de forma clara en el directorio `output/`:

```
output/
├── total/                # Análisis del conjunto de datos completo
│   ├── completadas/      # Solo órdenes 'Completadas'
│   │   ├── figures/      # Gráficos PNG
│   │   ├── reports/      # Reportes HTML interactivos
│   │   └── tables/       # Tablas de métricas CSV
│   ├── canceladas/       # Solo órdenes 'Canceladas' (estructura similar)
│   │   └── ...
│   └── todas/            # Todas las órdenes (estructura similar)
│       └── ...
└── AÑO/                  # Análisis para un año específico (ej. 2023)
    ├── completadas/      # (estructura similar)
    │   └── ...
    ├── canceladas/
    │   └── ...
    └── todas/
        └── ...
```

Navega por estas carpetas para encontrar:
* `figures/`: Gráficos estáticos en formato PNG.
* `reports/`: Reportes HTML interactivos que consolidan métricas y visualizaciones.
* `tables/`: Tablas de métricas detalladas en formato CSV.

---

## 📖 Guía Detallada

### 🎯 Propósito del Proyecto

El objetivo principal es transformar datos crudos de transacciones P2P en información valiosa y accionable. Este motor de análisis facilita una comprensión profunda del historial de operaciones, permitiendo optimizar estrategias de _trading_, preparar declaraciones fiscales de forma más eficiente o simplemente mantener un control detallado y profesional de toda la actividad P2P.

**Beneficios Clave:**

* **Automatización Inteligente:** Ahorra incontables horas de procesamiento manual de datos.
* **Visión Granular:** Desglosa y analiza la información por año y estado de orden para una perspectiva completa.
* **Flexibilidad de Formatos:** Exporta tus resultados a CSV, PNG (gráficos) y reportes HTML interactivos según tus necesidades.
* **Rendimiento Superior:** Utiliza Polars para el manejo eficiente y rápido de grandes volúmenes de datos.
* **Personalización Avanzada:** Adapta cada análisis a tus requerimientos específicos mediante argumentos CLI y archivos de configuración.
* **Organización Impecable:** Disfruta de una estructura de directorios clara y lógica para todas las salidas generadas.

### 🏗️ Estructura del Proyecto

Comprende cómo está organizado el código para facilitar su uso y desarrollo:

```
.
├── data/                     # Directorio para tus archivos CSV de entrada
├── output/                   # Directorio donde se guardan todos los resultados
├── src/                      # Código fuente de la aplicación
│   ├── app.py                # Punto de entrada principal (CLI)
│   ├── main_logic.py         # Orquesta el flujo de análisis
│   ├── analyzer.py           # Realiza los cálculos de métricas y transformaciones
│   ├── reporter.py           # Genera los archivos de salida (tablas, figuras, HTML)
│   ├── plotting.py           # Crea todas las visualizaciones gráficas
│   ├── finance_utils.py      # Funciones para cálculos financieros (P&L, Sharpe)
│   ├── config_loader.py      # Maneja la carga de configuración
│   └── utils.py              # Funciones de utilidad general
├── templates/                # Plantillas HTML para los reportes
│   └── report_template.html
├── config.yaml               # (Opcional) Tu archivo de configuración personalizado
├── requirements.txt          # Dependencias de Python
└── README.md                 # Este archivo
```

### ⚙️ Configuración Avanzada (`config.yaml`)

La aplicación utiliza una configuración interna por defecto (definida en `src/config_loader.py`). Puedes sobrescribir esta configuración parcial o totalmente proporcionando un archivo `config.yaml` personalizado mediante el argumento `--config ruta/a/tu/config.yaml`.

**Secciones Clave de la Configuración:**

* **`column_mapping`**: **¡Esencial!** Mapea los nombres de las columnas de tu CSV a los nombres internos que espera el script.
    * Formato: `Nombre Columna CSV: nombre_interno_script`
    * **Acción Requerida:** Revisa y ajusta esta sección según la estructura de tu archivo CSV. Las columnas clave incluyen información sobre: fecha/hora, tipo de activo (ej. USDT), fiat (ej. USD), precio, cantidad, monto total, estado de la orden, tipo de orden (compra/venta), método de pago y comisiones.
* **`sell_operation`**: Define qué columna y valor identifican una operación de venta (utilizado para el resumen de ventas).
* **`status_categories_map`**: Agrupa los diferentes valores de la columna de estado de tu CSV en categorías estandarizadas: "completadas", "canceladas" o "pendientes/apelación".
    * `completadas`: Lista de strings, ej. `["Completed", "Terminada", "Finalizado"]`
    * `canceladas`: Lista de strings, ej. `["Cancelled", "System cancelled", "Cancelada por el sistema"]`
    * `pendientes_o_apelacion`: Lista de strings, ej. `["Appealing", "Pending", "En apelación"]`
* **`filters_config`**: Parámetros para filtros avanzados (ej. `price_outlier_threshold_iqr` para el umbral de detección de outliers de precios).
* **`plot_config`**: Configuraciones específicas para ciertos gráficos (ej. `top_n_methods_price_vs_payment` para definir cuántos métodos de pago mostrar).
* **`html_report`**: Define qué tablas y (futuramente) figuras se incluyen por defecto en los reportes HTML.

### ⌨️ Argumentos de Línea de Comandos (CLI)

Controla y personaliza el análisis mediante los siguientes argumentos CLI:

| Argumento                       | Descripción                                                                                                                               | Ejemplo                                             |
| :------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------- |
| `--csv FICHERO_CSV`             | **(Obligatorio)** Ruta a tu archivo CSV de entrada.                                                                                       | `--csv data/p2p_data.csv`                           |
| `--out DIRECTORIO_SALIDA`       | Directorio base para guardar los resultados. Por defecto: `output/`.                                                                      | `--out resultados_analisis/`                        |
| `--year AÑO`                    | Analiza un año específico *además* del "total". Si se omite o se usa `--year all`, analiza todos los años presentes + "total".             | `--year 2023`                                       |
| `--config RUTA_CONFIG_YAML`     | Ruta a un archivo `config.yaml` personalizado para sobrescribir la configuración por defecto.                                               | `--config mi_config.yaml`                           |
| `--fiat_filter FIAT [FIAT ...]` | Filtra los datos para uno o más tipos de moneda fiat específicos (ej. USD, UYU) **antes** de cualquier análisis.                            | `--fiat_filter USD UYU`                             |
| `--asset_filter ACTIVO [ACTIVO ...]`| Filtra los datos para uno o más tipos de activo específicos (ej. USDT, BTC) **antes** de cualquier análisis.                            | `--asset_filter USDT BTC`                           |
| `--status_filter ESTADO [ESTADO ...]`| Filtra por uno o más estados de orden específicos **antes** de cualquier análisis.                                                     | `--status_filter Completed`                         |
| `--payment_method_filter METODO [METODO ...]`| Filtra por uno o más métodos de pago **antes** de cualquier análisis.                                                        | `--payment_method_filter "Banco X" "Billetera Y"`    |
| `--no-input`                    | Ejecuta el script sin pedir confirmación al usuario (útil para automatización y scripts).                                                 | `--no-input`                                        |
| `--interactive`                 | (Experimental) Habilita la interactividad en gráficos Plotly dentro de los reportes HTML (ej. zoom, pan).                               | `--interactive`                                     |
| `--detect-outliers`             | (Experimental) Activa la detección de outliers en precios utilizando el algoritmo `IsolationForest`.                                      | `--detect-outliers`                                 |
| `--event_date AAAA-MM-DD`       | (Experimental) Realiza un análisis comparativo 24 horas antes y después de la fecha de evento especificada.                             | `--event_date 2023-10-28`                           |
| `--export-xlsx NOMBRE_ARCHIVO.xlsx` | Exporta métricas clave y resúmenes a un archivo Excel multi-hoja.                                                                         | `--export-xlsx resumen_p2p.xlsx`                    |

### 🌊 Flujo del Análisis

1.  **Carga y Configuración Inicial (`app.py`):**
    * Se parsean los argumentos CLI.
    * Se carga la configuración (por defecto o desde el archivo YAML especificado).
    * Se lee el archivo CSV de entrada utilizando Polars.
    * Se aplica el mapeo de columnas definido en la configuración para estandarizar los nombres.
    * Se aplican los filtros globales especificados por CLI (fiat, activo, estado, etc.).
    * Se realiza un pre-análisis (`analyzer.analyze`) para generar columnas base esenciales (ej. `Year`) necesarias para el desglose posterior.
2.  **Pipeline de Análisis Principal (`main_logic.run_analysis_pipeline`):**
    * Se determinan los periodos a analizar: "total" siempre, y cada año individual si no se especifica un `--year` concreto (o si se usa `--year all`).
    * Para cada **periodo** (ej. "total", "2023"):
        * Se itera sobre las categorías de estado (`todas`, `completadas`, `canceladas`) definidas en `config['status_categories_map']`.
        * Se filtra el DataFrame del periodo actual para obtener el subconjunto de datos correspondiente al estado actual.
        * Si el subconjunto de datos no está vacío:
            * Se invoca `analyzer.analyze` sobre este subconjunto para calcular todas las métricas detalladas. Esto incluye:
                * Conversión de montos y precios a formato numérico.
                * Creación de columnas de tiempo detalladas (hora, día, mes, año).
                * Cálculo de estadísticas agregadas (por activo, por fiat, por estado, etc.).
                * Cálculo de métricas financieras (Precios Máximos/Mínimos, P&L si aplica).
            * Se invoca `reporter.save_outputs` para generar:
                * Tablas de resumen en formato CSV.
                * Gráficos y visualizaciones en formato PNG.
                * Un reporte HTML consolidado.
3.  **Generación de Salidas (`reporter.py`, `plotting.py`):**
    * `reporter.py` organiza la creación de directorios de salida y llama a las funciones de `plotting.py` para generar los gráficos.
    * `plotting.py` crea cada visualización utilizando los datos procesados y las librerías Matplotlib, Seaborn y Plotly.
    * `reporter.py` ensambla los reportes HTML utilizando plantillas Jinja2, incrustando tablas (convertidas a HTML) y enlaces a los gráficos generados.

### 📊 Tipos de Gráficos Generados

La herramienta produce una amplia variedad de gráficos para visualizar diferentes facetas de tus datos P2P. Algunos de los principales incluyen (los nombres de archivo pueden variar ligeramente):

* **Distribución Horaria:** Operaciones por hora del día.
* **Volumen Mensual:** Evolución del volumen (en fiat) a lo largo de los meses, desglosado por tipo de operación (Compra/Venta).
* **Promedio Diario:** Volumen promedio por día de la semana.
* **Gráficos de Torta (Pie Charts):** Para distribución de métodos de pago, tipos de fiat, etc.
* **Distribución de Precios:** Histogramas y boxplots de los precios de los activos.
* **Volumen vs. Precio (Scatter Plot):** Relación entre el volumen de la transacción y el precio.
* **Precio a lo largo del Tiempo:** Evolución del precio de un activo, con medias móviles.
* **Volumen a lo largo del Tiempo:** Evolución del volumen transaccionado (en activo y en fiat), con medias móviles.
* **Precio vs. Método de Pago (Boxplot/Violin Plot):** Comparativa de la distribución de precios entre diferentes métodos de pago.
* **Mapa de Calor de Actividad:** Concentración de operaciones (conteo o volumen) por hora del día y día de la semana.
* **Análisis de Comisiones:** Comisiones totales por activo o categoría.
* **Diagrama Sankey:** Flujo entre Fiat y Activos (requiere `--interactive` para visualización HTML).
* **Comparación Anual (YoY):** Volumen o métrica alineada por mes para comparar diferentes años.
* **Scatter Plot Animado (Plotly):** Evolución de Precio/Volumen a lo largo del tiempo (días).
* *Y otros gráficos especializados según las funcionalidades experimentales activadas.*

---

## 🛠️ Funcionalidades Avanzadas y Detalles Técnicos

Esta sección profundiza en los componentes internos del proyecto, las métricas clave y cómo se procesan los datos.

### Arquitectura Detallada del Código Fuente (`src/`)

* **`app.py`**:
    * **Rol:** Punto de entrada principal y gestión de la interfaz de línea de comandos (CLI).
    * **Responsabilidades:**
        * Define y parsea los argumentos CLI utilizando `argparse`.
        * Carga la configuración (`config_loader.load_config`).
        * Lee el archivo CSV de entrada (`--csv`) con Polars, aplicando inferencia de esquema y manejo inicial de nulos.
        * Aplica el mapeo de columnas (`config['column_mapping']`) para estandarizar nombres.
        * Aplica filtros globales iniciales basados en argumentos CLI (ej. `--fiat_filter`, `--asset_filter`).
        * Invoca `analyzer.analyze` para un pre-procesamiento que genera columnas esenciales (ej. `Year`) necesarias para el desglose.
        * Orquesta el pipeline de análisis principal llamando a `main_logic.run_analysis_pipeline`.

* **`main_logic.py`**:
    * **Rol:** Orquestación del flujo de análisis principal y manejo de la lógica de desglose.
    * **Responsabilidades:**
        * `initialize_analysis()`: Define y parsea los argumentos CLI, y construye sufijos de nombres de archivo y títulos para los reportes basados en los filtros aplicados.
        * `run_analysis_pipeline()`:
            * Recibe el DataFrame global pre-procesado.
            * Determina los "periodos" de análisis: "total" (datos completos) y, si no se indica lo contrario (`--year`), cada año individual encontrado en los datos.
            * Para cada periodo, itera sobre las categorías de estado (`todas`, `completadas`, `canceladas`) definidas en `config['status_categories_map']`.
            * Filtra el DataFrame del periodo para obtener el subconjunto de datos específico (ej., datos de 2023 que son "Completadas").
            * Si el subconjunto no está vacío, invoca `analyzer.analyze` sobre él para calcular métricas detalladas.
            * Luego, llama a `reporter.save_outputs` para generar todos los archivos de salida (tablas CSV, figuras PNG, reporte HTML) para ese subconjunto.

* **`analyzer.py`**:
    * **Rol:** Núcleo del procesamiento de datos y cálculo de métricas. La función principal es `analyze()`.
    * **Responsabilidades:**
        * **Transformación y Creación de Columnas Fundamentales:**
            * Convierte columnas de texto (Precio, Cantidad, etc.) a tipos numéricos (`Float64`) usando `utils.parse_amount`.
            * Calcula `TotalFee_num` sumando comisiones de maker y taker.
            * Asegura y procesa `Match_time_local` (hora local de la operación), derivando `hour_local`, `YearMonthStr`, `Year`, `DayOfWeek`, etc.
            * Limpia y estandariza la columna de estado (`Status_cleaned`) usando `config['status_categories_map']`.
            * Crea `TotalPrice_USD_equivalent` para análisis de volumen combinado.
        * **Cálculo de Métricas Agregadas (Diccionario `metrics`):** Ver la subsección "Métricas Calculadas Clave".
        * **Cálculo de Métricas Avanzadas:** High/Low intradía, TBT, P&L rodante, Sharpe, Estacionalidad FFT, Detección de Outliers, Índice de Liquidez, Whale Trades, Comparación Antes/Después de evento.
        * Devuelve el DataFrame procesado y el diccionario `metrics`.

* **`reporter.py`**:
    * **Rol:** Generación de todos los archivos de salida. La función principal es `save_outputs()`.
    * **Responsabilidades:**
        * Crea la estructura de directorios de salida (`output/[periodo]/[estado_subdir]/...`).
        * Convierte DataFrames de Polars a Pandas para compatibilidad con bibliotecas de gráficos y HTML.
        * Guarda tablas de métricas como archivos CSV.
        * Invoca funciones de `plotting.py` para generar y guardar gráficos PNG y HTML (Plotly).
        * Genera reportes HTML utilizando plantillas Jinja2 (`templates/report_template.html`), inyectando datos, tablas HTML y enlaces/incrustaciones de figuras.
        * Maneja la exportación a archivos Excel (`.xlsx`) multi-hoja.

* **`plotting.py`**:
    * **Rol:** Creación de todas las visualizaciones gráficas.
    * **Responsabilidades:**
        * Contiene funciones `plot_*` (ej. `plot_hourly`, `plot_monthly_fiat_volume`, etc.) para cada tipo de gráfico.
        * Utiliza `matplotlib`, `seaborn` (para gráficos estáticos) y `plotly` (para gráficos interactivos).
        * Configura la estética, etiquetas, títulos y leyendas de los gráficos.
        * Guarda los gráficos como archivos PNG o HTML (para Plotly).

* **`finance_utils.py`**:
    * **Rol:** Contiene funciones específicas para cálculos financieros.
    * **Responsabilidades:**
        * `calculate_daily_returns()`: Calcula retornos diarios.
        * `calculate_rolling_pnl()`: Calcula P&L acumulado en una ventana móvil.
        * `calculate_sharpe_ratio()`: Calcula el Ratio de Sharpe anualizado.

* **`config_loader.py`**:
    * **Rol:** Carga y gestión de la configuración del proyecto.
    * **Responsabilidades:**
        * Define `DEFAULT_CONFIG` con la estructura de configuración base (mapeo de columnas, categorías de estado, etc.).
        * `load_config()`: Carga la configuración. Actualmente retorna la `DEFAULT_CONFIG` pero está preparada para fusionar con un archivo `config.yaml` si se especifica vía CLI (`--config`).
        * `setup_logging()`: Configura el logging básico para la aplicación.

* **`utils.py`**:
    * **Rol:** Funciones de utilidad reutilizables en todo el proyecto.
    * **Responsabilidades:**
        * `parse_amount()`: Convierte strings de montos/precios (con diversos formatos de comas/puntos) a `float`.
        * `format_large_number()`: Formatea números grandes para mejor legibilidad en gráficos y tablas (ej. 15000 a "15K").
        * `sanitize_filename_component()`: Limpia strings para usarlos de forma segura en nombres de archivo.

### 🔑 Mapeo de Columnas y Columnas Internas Clave

La flexibilidad del script para trabajar con diferentes formatos de CSV de entrada reside en la sección `column_mapping` de la configuración. Aquí se definen los nombres de las columnas que el script espera internamente y a qué nombres de columnas del CSV original corresponden.

**Ejemplo de `column_mapping` (en `config.yaml` o `config_loader.py`):**
```yaml
column_mapping:
  # Nombres en tu CSV : Nombres internos usados por el script
  "Date(UTC)": "match_time_utc"
  "Time(UTC)": "match_time_utc_time_part" # Si la hora está separada
  "Order No": "order_number"
  "Order Type": "order_type_original" # Ej: "BUY", "SELL"
  "Asset Type": "asset_type"          # Ej: "USDT", "BTC"
  "Fiat Type": "fiat_type"            # Ej: "USD", "EUR"
  "Total Price": "total_price"        # Monto total en fiat
  "Price": "price"                    # Precio unitario
  "Quantity": "quantity"              # Cantidad del activo
  "Order Status": "status"            # Ej: "Completed", "Cancelled"
  "Counterparty": "counterparty"
  "Payment Method": "payment_method"
  "Maker Fee": "maker_fee_original"
  "Taker Fee": "taker_fee_original"
  # ... y cualquier otra columna que quieras usar o renombrar.
```

**Columnas Internas Generadas o Estandarizadas por `analyzer.py` (ejemplos):**
* `Price_num`: Columna `price` convertida a `float`.
* `Quantity_num`: Columna `quantity` convertida a `float`.
* `TotalPrice_num`: Columna `total_price` convertida a `float`.
* `TotalPrice_USD_equivalent`: `TotalPrice_num` convertido a un equivalente en USD (para análisis combinados).
* `MakerFee_num`, `TakerFee_num`: Comisiones convertidas a `float`.
* `TotalFee`: Suma de `MakerFee_num` y `TakerFee_num`.
* `Match_time_local`: Fecha y hora de la operación, convertida a la zona horaria local (definida en config) y a tipo datetime.
* `hour_local`: Hora de `Match_time_local` (0-23).
* `DayOfWeek`: Día de la semana de `Match_time_local` (0=Lunes, 6=Domingo).
* `DayName`: Nombre del día de la semana (ej. "Lunes").
* `YearMonthStr`: Año y mes en formato 'YYYY-MM'.
* `Year`: Año como entero.
* `order_type`: Estandarizado a 'BUY' o 'SELL' (basado en `order_type_original`).
* `Status_cleaned`: Estado de la orden limpio y categorizado (ej. "completada", "cancelada") según `status_categories_map`.

### 📈 Métricas Calculadas Clave (en `analyzer.py`)

El módulo `analyzer.py` calcula un diccionario de DataFrames de Polars (luego convertidos a Pandas para reporte y algunos gráficos) que resumen diversos aspectos de los datos. Algunas de las principales incluyen:

* **`asset_stats`**: Agregado por `asset_type` y `order_type`.
    * Métricas: `operations` (conteo), `quantity` (suma de `Quantity_num`), `total_fiat` (suma de `TotalPrice_num`), `total_fees`.
* **`fiat_stats`**: Agregado por `fiat_type` y `order_type`.
    * Métricas: `operations`, `total_fiat`, `avg_price` (media de `Price_num`), `total_fees`.
* **`price_stats`**: Agregado por `asset_type` y `fiat_type`.
    * Métricas: Estadísticas descriptivas de `Price_num` (media, mediana, min, max, std, cuartiles, percentiles).
* **`fees_stats`**: Agregado por `asset_type`.
    * Métricas: `total_fees_collected`, `avg_fee_per_op`, `num_ops_with_fees`, `max_fee`.
* **`monthly_fiat`**: Volumen de `TotalPrice_num` agrupado por `YearMonthStr`, `fiat_type`, y `order_type`. Pivotado para tener columnas BUY/SELL.
* **`hourly_counts`**: Conteo de operaciones por `hour_local`.
* **`daily_avg_fiat`**: Volumen promedio (`TotalPrice_num`) por `DayOfWeek` y `fiat_type`.
* **`status_counts`**: Conteo de operaciones por `Status_cleaned`.
* **`side_counts`**: Conteo de operaciones por `order_type` (BUY/SELL).
* **`payment_method_counts`**: Conteo de operaciones por `payment_method` y `fiat_type`.
* **`sales_summary_all_assets_fiat_detailed`**: Resumen de ventas (operaciones 'Completed' y marcadas como venta en `sell_operation` config), agrupado por `asset_type` (vendido) y `fiat_type` (recibido). Calcula `Total Asset Sold`, `Total Fiat Received`, y `Average Sell Price`.
* **Métricas Avanzadas (si están activadas o presentes):**
    * `intraday_high_low`: Precios máximos y mínimos por día.
    * `time_between_trades_stats`: Estadísticas sobre el tiempo entre operaciones consecutivas.
    * `rolling_pl_sharpe`: (Si se implementa `finance_utils.py`) P&L y Ratio de Sharpe rodante.
    * `fft_seasonality_volume`: Componentes de frecuencia del volumen para detectar estacionalidad.
    * `outlier_info`: Información sobre outliers detectados (si `--detect-outliers`).
    * `effective_liquidity_index`: Índice de liquidez efectiva (media_cantidad / mediana_cantidad).
    * `whale_trades`: Identificación de operaciones de gran volumen.
    * `event_comparison_stats`: Comparación de métricas antes y después de una fecha de evento.

### ✨ Funcionalidades Implementadas y Mejoras Recientes

Este proyecto ha sido actualizado con una serie de mejoras significativas y nuevas funcionalidades. A continuación, un resumen:

**Métricas Avanzadas (en `src/analyzer.py`):**
* **High / Low Intradía:** Implementado.
* **Time-Between-Trades (TBT):** Implementado con percentiles.
* **Rolling P&L + Sharpe (7 días):** Implementado utilizando el módulo `src/finance_utils.py`.
* **Estacionalidad (FFT) en Volumen:** Implementado usando `numpy.fft`.
* **Detección de Outliers con IsolationForest:** Implementado con flag CLI `--detect-outliers` y `scikit-learn`.
* **Índice de Liquidez Efectiva:** Calculado (`mean_qty/median_qty`).

**Visualizaciones (en `src/plotting.py` y `src/reporter.py`):**
* **Sankey Fiat → Activo:** Implementado con Plotly.
* **Heatmap Hora × Día:** Implementado con Seaborn (para conteo y volumen).
* **Gráfico de Violín Precio vs. Método de pago:** Implementado con Seaborn.
* **Gráfico de Línea YoY (Año sobre Año) alineado por mes:** Implementado con Matplotlib/Seaborn.
* **Scatter Plot Animado Precio/Volumen:** Implementado con Plotly Express.
* **Gráficos de Boxplot Detallados:** Para Precio y Volumen Fiat vs. Método de Pago, segmentados por par de monedas.
* **Gráfico de Completitud de Órdenes:** Evolución mensual del porcentaje de órdenes completadas, canceladas, etc.
* **Gráfico de Volumen por Día de la Semana:** Para diferentes monedas y volumen combinado.
* **Gráfico de Volumen Compra vs. Venta Mensual:** Comparativa lado a lado.
* **Scatter Plot de Correlación:** Precio vs. Volumen Total Fiat.
* **Gráfico de Profundidad de Mercado Simplificado.**

**Detección de Patrones y Alertas:**
* **Identificación de "Whale Trades"**: Operaciones que superan la media más 3 desviaciones estándar del volumen (`TotalPrice_num`), añadidas al reporte HTML.
* **Análisis Comparativo Antes/Después de Evento**: Implementado con el flag CLI `--event_date` para comparar métricas clave 24 horas antes y después de una fecha específica. Los resultados se incluyen en el reporte HTML.

**Reporting Interactivo y Exportación:**
* **Modo Interactivo (`--interactive`):** Permite la incrustación de gráficos Plotly en los reportes HTML.
* **Tablas HTML con Clase para DataTables.js:** Se añade la clase `datatable-ready` a las tablas HTML para futura integración con la librería DataTables.js (requiere añadir el JS/CSS de DataTables en la plantilla HTML o externamente).
* **Exportación a XLSX Multi-hoja:** Implementada para exportar métricas clave y el detalle de operaciones procesadas a un archivo Excel.

---

## 👨‍💻 Contribuir y Desarrollar

¡Tu contribución es bienvenida! Si deseas mejorar o modificar el proyecto:

1.  Sigue las instrucciones de configuración en la sección "🚀 Inicio Rápido".
2.  Explora el código fuente en el directorio `src/`. Los módulos principales son `app.py` (entrada CLI), `main_logic.py` (orquestador), `analyzer.py` (cálculos), `reporter.py` (salidas) y `plotting.py` (gráficos).
3.  La configuración principal se encuentra en `src/config_loader.py` (valores por defecto) y puede ser extendida o sobrescrita mediante un archivo `config.yaml`.
4.  Asegúrate de que las nuevas funcionalidades o correcciones incluyan documentación clara y, si es aplicable, pruebas.
5.  Considera abrir un *issue* en GitHub para discutir cambios mayores antes de implementarlos.
6.  Envía tus *Pull Requests* al repositorio principal.

## 🔗 Dependencias Clave

Este proyecto se apoya en las siguientes librerías de Python:

* **Polars:** Para la manipulación de DataFrames de alto rendimiento y eficiencia en memoria.
* **Pandas:** Utilizado como puente para algunas bibliotecas de visualización y para la exportación a Excel.
* **Matplotlib & Seaborn:** Para la generación de una amplia variedad de gráficos estáticos de alta calidad.
* **Plotly:** Para la creación de gráficos interactivos y dinámicos, especialmente para reportes HTML.
* **NumPy:** Para cálculos numéricos fundamentales y operaciones con arrays.
* **Scikit-learn:** Para funcionalidades de aprendizaje automático, como `IsolationForest` para la detección de outliers.
* **Jinja2:** Para la generación de reportes HTML dinámicos a partir de plantillas.
* **Openpyxl:** Para escribir archivos en formato `.xlsx` (Excel).

## 📜 Licencia

Este proyecto se distribuye bajo la Licencia MIT. Consulta el archivo `LICENSE` (si existe en el repositorio) para más detalles.

# Análisis Avanzado de Datos P2P 🚀

Este proyecto ofrece una herramienta para el análisis de datos de operaciones Peer-to-Peer (P2P) exportados desde plataformas de intercambio. Utiliza Polars para el procesamiento eficiente de datos y genera análisis detallados, incluyendo métricas financieras, tablas de resumen, visualizaciones (`matplotlib`, `seaborn`, `plotly`) y reportes HTML interactivos.

El análisis se organiza por el conjunto total de datos, por año, y se segmenta adicionalmente por estado de la orden (Completadas, Canceladas, Todas).

## 🚀 Inicio Rápido

### 1. Prerrequisitos
*   Python 3.8 o superior
*   PIP (manejador de paquetes de Python)

### 2. Configuración
1.  **Clonar el Repositorio (si aplica):**
    ```bash
    git clone https://github.com/Falopp/data_p2p
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

### 3. Ejecución Básica
Coloca tu archivo de datos P2P (en formato CSV) en la carpeta `data/`. Por ejemplo, `data/p2p_data.csv`.

Ejecuta el script desde la raíz del proyecto:
```bash
python src/app.py --csv data/p2p_data.csv
```
Esto generará el análisis para el dataset completo y para cada año presente en los datos.

### 4. Salida del Análisis
Los resultados se guardarán en la carpeta `output/`. La estructura será:
```
output/
├── total/                # Análisis del conjunto de datos completo
│   ├── completadas/      # Solo órdenes completadas
│   │   ├── figures/
│   │   ├── reports/
│   │   └── tables/
│   ├── canceladas/       # Solo órdenes canceladas
│   │   └── ...
│   └── todas/            # Todas las órdenes
│       └── ...
└── YYYY/                 # Análisis para el año YYYY (ej. 2023)
    ├── completadas/
    │   └── ...
    ├── canceladas/
    │   └── ...
    └── todas/
        └── ...
```
Dentro de cada subdirectorio encontrarás:
*   `figures/`: Gráficos en formato PNG.
*   `reports/`: Reportes HTML interactivos.
*   `tables/`: Tablas de métricas en formato CSV.

---

## 📖 Guía Detallada

### 🎯 Propósito del Proyecto
El objetivo es convertir datos crudos de transacciones P2P en información accionable. Facilita la comprensión del historial de operaciones para optimizar estrategias, realizar declaraciones fiscales o llevar un control detallado de la actividad P2P.

**Beneficios Clave:**
*   **Análisis Automatizado:** Ahorra tiempo en procesamiento manual.
*   **Comprensión Granular:** Desglose por año y estado de orden.
*   **Múltiples Formatos de Salida:** CSV, PNG (gráficos) y reportes HTML.
*   **Eficiencia:** Usa Polars para el manejo rápido de grandes volúmenes de datos.
*   **Personalización:** Argumentos CLI para adaptar el análisis.
*   **Organización:** Estructura de directorios clara para las salidas.

### 🏗️ Estructura del Proyecto
*   `src/`: Contiene todo el código fuente de la aplicación.
    *   `app.py`: Punto de entrada CLI.
    *   `main_logic.py`: Orquesta el pipeline de análisis.
    *   `analyzer.py`: Realiza los cálculos de métricas y transformaciones.
    *   `reporter.py`: Genera los archivos de salida (tablas, figuras, reportes HTML).
    *   `plotting.py`: Crea todas las visualizaciones gráficas.
    *   `config_loader.py`: Maneja la configuración de la aplicación.
    *   `utils.py`: Funciones de utilidad.
*   `data/`: Directorio para colocar los archivos CSV de entrada.
*   `output/`: Donde se guardan todos los resultados del análisis.
*   `templates/`: Contiene la plantilla HTML para los reportes.
*   `config.yaml`: Archivo de configuración principal (sobrescribe la configuración por defecto si se usa `--config`).
*   `requirements.txt`: Lista de dependencias de Python.
*   `README.md`: Este archivo.

### ⚙️ Configuración (`config.yaml` y Configuración por Defecto)
La aplicación utiliza una configuración interna por defecto (definida en `src/config_loader.py`) que puede ser sobrescrita parcial o totalmente proporcionando un archivo `config.yaml` mediante el argumento `--config ruta/a/tu/config.yaml`.

**Secciones Clave de la Configuración:**
*   **`column_mapping`**: Esencial. Mapea los nombres de las columnas de tu CSV a los nombres internos que espera el script.
    *   Ejemplo: `Original Column Name From CSV: internal_script_name`
    *   Debes revisar y ajustar esto según tu archivo CSV. Columnas clave son las relativas a: fecha/hora, tipo de activo (ej. USDT), fiat (ej. USD), precio, cantidad, monto total, estado de la orden, tipo de orden (compra/venta), método de pago, comisiones.
*   **`sell_operation`**: Define qué columna y valor identifican una operación de venta (usado para el resumen de ventas).
*   **`status_categories_map`**: Define qué valores de la columna de estado se agrupan en "completadas", "canceladas" o "pendientes/apelación".
    *   `completadas`: Lista de strings, ej. `["Completed", "Terminada"]`
    *   `canceladas`: Lista de strings, ej. `["Cancelled", "System cancelled", "Cancelada"]`
    *   `pendientes_o_apelacion`: Lista de strings, ej. `["Appealing", "Pending"]`
*   **`filters_config`**: Configuración para filtros avanzados (ej. `price_outlier_threshold_iqr`).
*   **`plot_config`**: Configuraciones específicas para gráficos (ej. `top_n_methods_price_vs_payment`).
*   **`html_report`**: Define qué tablas y (futuramente) figuras se incluyen por defecto en los reportes HTML.

### Argumentos de Línea de Comandos (CLI)
La herramienta se controla mediante argumentos de línea de comandos:

*   `--csv FICHERO_CSV` (Obligatorio): Ruta al archivo CSV de entrada.
    *   Ejemplo: `--csv data/mis_datos_p2p.csv`
*   `--out DIRECTORIO_SALIDA` (Opcional): Directorio base para guardar los resultados.
    *   Por defecto: `output/`
    *   Ejemplo: `--out resultados_analisis/`
*   `--year AÑO` (Opcional): Analiza solo el año especificado Y el "total". Si no se provee, analiza todos los años presentes en los datos más el "total".
    *   Ejemplo: `--year 2023`
*   `--config RUTA_CONFIG_YAML` (Opcional): Ruta a un archivo `config.yaml` personalizado.
    *   Ejemplo: `--config custom_config.yaml`
*   `--fiat_filter FIAT` (Opcional): Filtra los datos para un tipo de fiat específico (ej. USD, UYU) ANTES de cualquier análisis.
*   `--asset_filter ACTIVO` (Opcional): Filtra los datos para un tipo de activo específico (ej. USDT, BTC) ANTES de cualquier análisis.
*   `--status_filter ESTADO` (Opcional): Filtra por un estado de orden específico ANTES de cualquier análisis.
*   `--payment_method_filter METODO` (Opcional): Filtra por un método de pago ANTES de cualquier análisis.
*   `--no-input`: Ejecuta el script sin pedir confirmación al usuario (útil para automatización).
*   `--interactive`: (Experimental) Habilita la interactividad en gráficos Plotly dentro de los reportes HTML.
*   `--detect-outliers`: (Experimental) Habilita la detección de outliers en precios usando IsolationForest.
*   `--event_date YYYY-MM-DD`: (Experimental) Realiza un análisis comparativo antes/después de esta fecha.
*   `--export-xlsx NOMBRE_ARCHIVO.xlsx`: Exporta métricas clave a un archivo Excel multi-hoja.

### 🌊 Flujo del Análisis
1.  **Carga y Configuración Inicial (`app.py`):**
    *   Se parsean los argumentos CLI.
    *   Se carga la configuración (por defecto o desde archivo YAML).
    *   Se lee el CSV de entrada con Polars.
    *   Se aplica el mapeo de columnas definido en la configuración.
    *   Se aplican los filtros globales especificados por CLI (fiat, asset, etc.).
    *   Se realiza un pre-análisis (`analyzer.analyze`) para generar columnas base como `Year`.
2.  **Pipeline de Análisis Principal (`main_logic.run_analysis_pipeline`):**
    *   Se determinan los periodos a analizar: "total" siempre, y cada año individual si `--year` no se especifica o si se especifica un año concreto.
    *   Para cada **periodo**:
        *   Se itera sobre las categorías de estado (`todas`, `completadas`, `canceladas`) definidas en `status_categories_map`.
        *   Se filtra el DataFrame del periodo actual para obtener el subconjunto correspondiente al estado actual.
        *   Si hay datos en el subconjunto:
            *   Se invoca `analyzer.analyze` sobre este subconjunto para calcular todas las métricas detalladas. Esto incluye:
                *   Conversión de montos y precios a numérico.
                *   Creación de columnas de tiempo detalladas (hora, día, mes, año).
                *   Cálculo de estadísticas agregadas (por activo, por fiat, por estado, etc.).
                *   Cálculo de métricas financieras (High/Low, P&L si aplica).
            *   Se invoca `reporter.save_outputs` para generar:
                *   Tablas de resumen en formato CSV.
                *   Gráficos y visualizaciones en formato PNG.
                *   Un reporte HTML consolidado.
3.  **Generación de Salidas (`reporter.py`, `plotting.py`):**
    *   `reporter.py` organiza la creación de directorios de salida y llama a las funciones de `plotting.py`.
    *   `plotting.py` genera cada gráfico utilizando los datos procesados.
    *   `reporter.py` ensambla los reportes HTML usando plantillas Jinja2, incrustando tablas y enlaces a los gráficos.

### 📊 Tipos de Gráficos Generados
La herramienta genera una variedad de gráficos para visualizar diferentes aspectos de los datos P2P. Algunos de los principales incluyen (los nombres pueden variar ligeramente en los archivos de salida):

*   **Distribución Horaria:** Operaciones por hora del día.
*   **Volumen Mensual:** Evolución del volumen (en fiat) a lo largo de los meses, por tipo de operación (Compra/Venta).
*   **Promedio Diario:** Volumen promedio por día de la semana.
*   **Gráficos de Torta (Pie Charts):** Para distribución de métodos de pago, tipos de fiat, etc.
*   **Distribución de Precios:** Histogramas y boxplots de los precios de los activos.
*   **Volumen vs. Precio (Scatter Plot):** Relación entre el volumen de la transacción y el precio.
*   **Precio a lo largo del Tiempo:** Evolución del precio de un activo, con medias móviles.
*   **Volumen a lo largo del Tiempo:** Evolución del volumen transaccionado (en activo y en fiat), con medias móviles.
*   **Precio vs. Método de Pago (Boxplot):** Comparativa de la distribución de precios entre diferentes métodos de pago.
*   **Heatmap de Actividad:** Concentración de operaciones (conteo o volumen) por hora del día y día de la semana.
*   **Análisis de Comisiones:** Comisiones totales por activo o categoría.
*   **Diagrama Sankey:** Flujo entre Fiat y Activos (requiere `--interactive`).
*   **Gráfico de Violín:** Similar al boxplot para Precio vs. Método de Pago, mostrando la forma de la distribución.
*   **Comparación Anual (YoY):** Volumen o métrica alineada por mes para comparar años.
*   *Y otros gráficos especializados según las funcionalidades experimentales activadas.*

---
## 🛠️ Funcionalidades Avanzadas y Detalles Técnicos

Esta sección profundiza en los componentes internos del proyecto, las métricas clave y cómo se procesan los datos.

### Arquitectura Detallada del Código Fuente (`src/`)

*   **`app.py`**:
    *   **Rol:** Punto de entrada principal y gestión de la interfaz de línea de comandos (CLI).
    *   **Responsabilidades:**
        *   Define y parsea argumentos CLI utilizando `argparse`.
        *   Carga la configuración (`config_loader.load_config`).
        *   Lee el archivo CSV de entrada (`--csv`) con Polars, aplicando inferencia de esquema y manejo inicial de nulos.
        *   Aplica el mapeo de columnas (`config['column_mapping']`) para estandarizar nombres.
        *   Aplica filtros globales iniciales basados en argumentos CLI (ej. `--fiat_filter`, `--asset_filter`).
        *   Invoca `analyzer.analyze` para un pre-procesamiento que genera columnas esenciales (ej. `Year`) necesarias para el desglose.
        *   Orquesta el pipeline de análisis principal llamando a `main_logic.run_analysis_pipeline`.

*   **`main_logic.py`**:
    *   **Rol:** Orquestación del flujo de análisis principal y manejo de la lógica de desglose.
    *   **Responsabilidades:**
        *   `initialize_analysis()`: Define y parsea los argumentos CLI, y construye sufijos de nombres de archivo y títulos para los reportes basados en los filtros aplicados.
        *   `run_analysis_pipeline()`:
            *   Recibe el DataFrame global pre-procesado.
            *   Determina los "periodos" de análisis: "total" (datos completos) y, si no se indica lo contrario (`--year`), cada año individual encontrado en los datos.
            *   Para cada periodo, itera sobre las categorías de estado (`todas`, `completadas`, `canceladas`) definidas en `config['status_categories_map']`.
            *   Filtra el DataFrame del periodo para obtener el subconjunto de datos específico (ej., datos de 2023 que son "Completadas").
            *   Si el subconjunto no está vacío, invoca `analyzer.analyze` sobre él para calcular métricas detalladas.
            *   Luego, llama a `reporter.save_outputs` para generar todos los archivos de salida (tablas CSV, figuras PNG, reporte HTML) para ese subconjunto.

*   **`analyzer.py`**:
    *   **Rol:** Núcleo del procesamiento de datos y cálculo de métricas. La función principal es `analyze()`.
    *   **Responsabilidades:**
        *   **Transformación y Creación de Columnas Fundamentales:**
            *   Convierte columnas de texto (Precio, Cantidad, etc.) a tipos numéricos (`Float64`) usando `utils.parse_amount`.
            *   Calcula `TotalFee_num` sumando comisiones de maker y taker.
            *   Asegura y procesa `Match_time_local` (hora local de la operación), derivando `hour_local`, `YearMonthStr`, `Year`, `DayOfWeek`, etc.
            *   Limpia y estandariza la columna de estado (`Status_cleaned`) usando `config['status_categories_map']`.
        *   **Cálculo de Métricas Agregadas (Diccionario `metrics`):** Ver la subsección "Métricas Calculadas Clave".
        *   Devuelve el DataFrame procesado y el diccionario `metrics`.

*   **`reporter.py`**:
    *   **Rol:** Generación de todos los archivos de salida. La función principal es `save_outputs()`.
    *   **Responsabilidades:**
        *   Crea la estructura de directorios de salida (`output/[periodo]/[estado_subdir]/...`).
        *   Convierte DataFrames de Polars a Pandas para compatibilidad con bibliotecas de gráficos y HTML.
        *   Guarda tablas de métricas como archivos CSV.
        *   Invoca funciones de `plotting.py` para generar y guardar gráficos PNG.
        *   Genera reportes HTML utilizando plantillas Jinja2 (`templates/report_template.html`), inyectando datos, tablas HTML y enlaces a figuras.

*   **`plotting.py`**:
    *   **Rol:** Creación de todas las visualizaciones gráficas.
    *   **Responsabilidades:**
        *   Contiene funciones `plot_*` (ej. `plot_hourly`, `plot_monthly`, etc.) para cada tipo de gráfico.
        *   Utiliza `matplotlib`, `seaborn`, y `plotly` (para gráficos interactivos).
        *   Configura la estética, etiquetas, títulos y leyendas.
        *   Guarda los gráficos como archivos PNG (o HTML para Plotly).

*   **`config_loader.py`**:
    *   **Rol:** Carga y gestión de la configuración del proyecto.
    *   **Responsabilidades:**
        *   Define `DEFAULT_CONFIG` con la estructura de configuración base (mapeo de columnas, categorías de estado, etc.).
        *   `load_config()`: Carga la configuración. Actualmente retorna la `DEFAULT_CONFIG` pero puede extenderse para leer de un archivo `config.yaml` si se especifica vía CLI (`--config`). Si se provee un archivo YAML, este se fusiona con la configuración por defecto, permitiendo sobrescribir valores específicos.
        *   `setup_logging()`: Configura el logging básico para la aplicación.

*   **`utils.py`**:
    *   **Rol:** Funciones de utilidad reutilizables.
    *   **Responsabilidades:**
        *   `parse_amount()`: Convierte strings de montos/precios (con comas/puntos) a `float`.
        *   `format_large_number()`: Formatea números grandes para mejor legibilidad en gráficos (ej. 15000 a "15K").
        *   `sanitize_filename_component()`: Limpia strings para usarlos en nombres de archivo.

### 🔑 Mapeo de Columnas y Columnas Internas Clave

La flexibilidad del script para trabajar con diferentes formatos de CSV de entrada reside en la sección `column_mapping` de la configuración (`config.yaml` o `config_loader.py`). Aquí se definen los nombres de las columnas que el script espera internamente y a qué nombres de columnas del CSV original corresponden.

**Ejemplo de `column_mapping`:**
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
  # ... y cualquier otra columna que quieras usar.
```

**Columnas Internas Generadas o Estandarizadas por `analyzer.py` (ejemplos):**
*   `Price_num`: Columna `price` convertida a `float`.
*   `Quantity_num`: Columna `quantity` convertida a `float`.
*   `TotalPrice_num`: Columna `total_price` convertida a `float`.
*   `MakerFee_num`, `TakerFee_num`: Comisiones convertidas a `float`.
*   `TotalFee_num`: Suma de `MakerFee_num` y `TakerFee_num`.
*   `Match_time_local`: Fecha y hora de la operación, convertida a la zona horaria local (definida en config) y a tipo datetime.
*   `hour_local`: Hora de `Match_time_local` (0-23).
*   `DayOfWeek`: Día de la semana de `Match_time_local` (0=Lunes, 6=Domingo).
*   `DayName`: Nombre del día de la semana.
*   `YearMonthStr`: Año y mes en formato 'YYYY-MM'.
*   `Year`: Año como entero.
*   `order_type`: Estandarizado a 'BUY' o 'SELL' (basado en `order_type_original`).
*   `Status_cleaned`: Estado de la orden limpio y categorizado (ej. "completada", "cancelada") según `status_categories_map`.

### 📈 Métricas Calculadas Clave (en `analyzer.py`)

El módulo `analyzer.py` calcula un diccionario de DataFrames de Polars (luego convertidos a Pandas para reporte) que resumen diversos aspectos de los datos. Algunas de las principales incluyen:

*   **`asset_stats`**: Agregado por `asset_type` y `order_type`.
    *   Métricas: `operations` (conteo), `quantity` (suma de `Quantity_num`), `total_fiat` (suma de `TotalPrice_num`), `total_fees`.
*   **`fiat_stats`**: Agregado por `fiat_type` y `order_type`.
    *   Métricas: `operations`, `total_fiat`, `avg_price` (media de `Price_num`), `total_fees`.
*   **`price_stats`**: Agregado por `asset_type` y `fiat_type`.
    *   Métricas: Estadísticas descriptivas de `Price_num` (media, mediana, min, max, std, cuartiles, percentiles).
*   **`fees_stats`**: Agregado por `asset_type`.
    *   Métricas: `total_fees_collected`, `avg_fee_per_op`, `num_ops_with_fees`, `max_fee`.
*   **`monthly_fiat`**: Volumen de `TotalPrice_num` agrupado por `YearMonthStr`, `fiat_type`, y `order_type`. Pivotado para tener columnas BUY/SELL.
*   **`hourly_counts`**: Conteo de operaciones por `hour_local`.
*   **`daily_avg_fiat`**: Volumen promedio (`TotalPrice_num`) por `DayOfWeek` y `fiat_type`.
*   **`status_counts`**: Conteo de operaciones por `Status_cleaned`.
*   **`side_counts`**: Conteo de operaciones por `order_type` (BUY/SELL).
*   **`payment_method_counts`**: Conteo de operaciones por `payment_method` y `fiat_type`.
*   **`sales_summary_all_assets_fiat_detailed`**: Resumen de ventas (operaciones 'Completed' y marcadas como venta en `sell_operation` config), agrupado por `asset_type` (vendido) y `fiat_type` (recibido). Calcula `Total Asset Sold`, `Total Fiat Received`, y `Average Sell Price`.
*   **Métricas Avanzadas (si activadas o presentes):**
    *   `intraday_high_low`: Precios máximos y mínimos por día.
    *   `time_between_trades_stats`: Estadísticas sobre el tiempo entre operaciones consecutivas.
    *   `rolling_pl_sharpe`: (Si se implementa `finance_utils.py`) P&L y Ratio de Sharpe rodante.
    *   `fft_seasonality_volume`: Componentes de frecuencia del volumen para detectar estacionalidad.
    *   `outlier_info`: Información sobre outliers detectados (si `--detect-outliers`).

### ✨ Funcionalidades Implementadas y Mejoras Recientes
*(Esta subsección se mantiene como en la versión anterior, ya que lista las funcionalidades específicas)*

Este proyecto ha sido recientemente actualizado con una serie de mejoras significativas y nuevas funcionalidades. A continuación, se presenta un resumen de los avances:

**Métricas Avanzadas (en `src/analyzer.py`):**
*   **High / Low Intradía:** Implementado.
*   **Time-Between-Trades (TBT):** Implementado con percentiles.
*   **Rolling P&L + Sharpe (7 días):** Implementado utilizando un nuevo módulo `src/finance_utils.py`.
*   **Estacionalidad (FFT) en Volumen:** Implementado usando `numpy.fft`.
*   **Detección de Outliers con IsolationForest:** Implementado con flag CLI `--detect-outliers` y `scikit-learn`.
*   **Índice de Liquidez Efectiva:** Calculado (`mean_qty/median_qty`).

**Visualizaciones (en `src/plotting.py` y `src/reporter.py`):**
*   **Sankey Fiat → Activo:** Implementado con Plotly.
*   **Heatmap Hora × Día:** Implementado con Seaborn (para conteo y volumen).
*   **Gráfico de Violín Precio vs. Método de pago:** Implementado con Seaborn.
*   **Gráfico de Línea YoY (Año sobre Año) alineado por mes:** Implementado con Matplotlib/Seaborn.
*   **Scatter Plot Animado Precio/Volumen:** Implementado con Plotly Express.

**Detección de Patrones y Alertas:**
*   **Identificación de "Whale Trades"**: Operaciones que superan la media más 3 desviaciones estándar del volumen (`TotalPrice_num`), añadidas al reporte HTML.
*   **Análisis Comparativo Antes/Después de Evento**: Implementado con el flag CLI `--event_date` para comparar métricas clave 24 horas antes y después de una fecha específica. Los resultados se incluyen en el reporte HTML.

**Reporting Interactivo y Exportación:**
*   **Modo Interactivo (`--interactive`):** Permite la incrustación de gráficos Plotly en los reportes HTML.
*   **Tablas HTML Interactivas con DataTables.js:** (Potencial) Se añade la clase `datatable-ready` a las tablas para futura integración.
*   **Exportación a XLSX Multi-hoja:** Implementada para exportar métricas a Excel.

---

## 👨‍💻 Contribuir y Desarrollar
Si deseas contribuir o modificar el proyecto:
1.  Sigue las instrucciones de configuración en la sección "Inicio Rápido".
2.  Explora el código en `src/`. Los módulos principales son `app.py`, `main_logic.py`, `analyzer.py`, `reporter.py`, y `plotting.py`.
3.  La configuración principal se encuentra en `src/config_loader.py` (default) y puede ser extendida con `config.yaml`.
4.  Asegúrate de que las nuevas funcionalidades o correcciones incluyan pruebas (si aplica) y se documenten.

## 🔗 Dependencias Clave
*   **Polars:** Para manipulación de DataFrames de alto rendimiento.
*   **Pandas:** Usado como puente para bibliotecas de visualización y exportación.
*   **Matplotlib & Seaborn:** Para la generación de gráficos estáticos.
*   **Plotly:** Para gráficos interactivos.
*   **NumPy:** Para cálculos numéricos.
*   **Scikit-learn:** Para funcionalidades de machine learning (ej. IsolationForest).
*   **Jinja2:** Para la generación de reportes HTML a partir de plantillas.

## 📜 Licencia
Este proyecto se distribuye bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles (si existe, o especificar aquí).

---
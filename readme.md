# Proyecto de Análisis de Datos P2P (Versión Profesional)

Este proyecto realiza un análisis exhaustivo de datos de operaciones Peer-to-Peer (P2P) exportados desde plataformas como Binance. El script principal procesa un archivo CSV utilizando la biblioteca **Polars**, calcula diversas métricas financieras y de actividad, genera tablas de resumen, visualizaciones detalladas y un reporte HTML. Los resultados se organizan meticulosamente por año y para el consolidado total, y además se segmentan según el estado de la orden (Completadas, Canceladas, Todas) para un análisis más granular.

## 🚀 Resumen para IA

Este proyecto en Python analiza datos de transacciones P2P de un archivo CSV, utilizando **Polars** para el procesamiento de datos.

**Entrada:**
- Archivo CSV con datos de operaciones (configurable mediante ` --csv `).

**Procesamiento:**
1.  Carga y limpieza de datos con **Polars**.
2.  Filtrado opcional mediante argumentos CLI (`--fiat_filter`, `--asset_filter`, `--status_filter`, `--payment_method_filter`). El filtro de estado por defecto es `'Completed'`.
3.  Cálculo de métricas: estadísticas de activos, monedas fiat, precios, comisiones, actividad horaria/mensual.
4.  Generación de resultados para el conjunto de datos **total** (post-filtrado CLI) y opcionalmente para cada **año** individual presente en los datos (se puede desactivar con ` --no_annual_breakdown `).
5.  Para cada periodo (total y cada año), los resultados se subdividen en tres categorías basadas en el estado de la orden:
    *   `completadas/`: Solo operaciones con estado "Completed".
    *   `canceladas/`: Solo operaciones con estado "Cancelled".
    *   `todas/`: Todas las operaciones del periodo, independientemente de su estado (considerando los filtros CLI iniciales).

**Salida:**
*   Estructura de carpetas en `output/` (o la especificada con ` --out `).
*   Dentro de `output/`, carpetas `total/`, `YYYY/` (para cada año).
*   Dentro de cada carpeta de periodo (`total/`, `YYYY/`), subcarpetas `completadas/`, `canceladas/`, `todas/`.
*   Cada una de estas subcarpetas contendrá:
    *   `tables/`: Archivos CSV con datos agregados.
    *   `figures/`: Gráficos PNG.
    *   `reports/`: Reportes HTML individuales.
*   Los nombres de los archivos de salida reflejan los filtros CLI aplicados y la categoría de estado (ej. `asset_stats_fiat_UYU_asset_USDT.csv` dentro de una carpeta `completadas/tables/`).

## ✨ Características Principales

*   📊 **Análisis Detallado con Polars:** Calcula estadísticas sobre activos, monedas fiat, precios, comisiones, y actividad horaria/mensual utilizando **Polars** para un procesamiento eficiente.
*   📅 **Desglose Anual, Total y por Estado:** Genera un conjunto completo de resultados (tablas, gráficos y reportes HTML) para el período total de los datos, para cada año individual, y dentro de cada uno de estos, segmentado por operaciones completadas, canceladas y todas.
*   ⚙️ **Filtrado Avanzado CLI:** Permite filtrar los datos por múltiples criterios (moneda fiat, activo, estado de orden, método de pago) directamente desde la línea de comandos. Estos filtros se aplican *antes* del desglose anual y la segmentación por estado.
*   🖼️ **Visualizaciones Claras:** Genera una amplia gama de gráficos utilizando `matplotlib` y `seaborn`.
*   📄 **Reportes HTML Dinámicos:** Genera un reporte HTML para cada combinación de periodo (total/anual) y estado (completadas/canceladas/todas), que resume los filtros aplicados, métricas clave y las figuras generadas.
*   📂 **Salida Organizada:** Todos los resultados se guardan en una carpeta principal (por defecto `output/`). La estructura interna es: `output/[periodo]/[estado_orden]/[tipo_resultado]/`, donde `[periodo]` puede ser `total` o un año (ej. `2023`), `[estado_orden]` puede ser `completadas`, `canceladas` o `todas`, y `[tipo_resultado]` es `tables`, `figures`, o `reports`.
*   💪 **Robustez:** Manejo mejorado de formatos numéricos, columnas de datos faltantes y errores en la generación de gráficos individuales, con el soporte de **Polars** para el manejo de datos.

## 🔄 Flujo de Procesamiento de Datos

1.  📥 **Carga de Datos:** El script carga el archivo CSV especificado usando **Polars**.
2.  ✂️ **Filtrado Inicial (CLI):** Se aplican los filtros opcionales proporcionados por el usuario a través de los argumentos de la línea de comandos (`--fiat_filter`, `--asset_filter`, `--status_filter`, `--payment_method_filter`).
    > **Nota:** Si se usa ` --status_filter ` aquí, este filtro prevalecerá para la selección inicial de datos *antes* de la segmentación `completadas`/`canceladas`/`todas`. Por ejemplo, si se usa ` --status_filter Cancelled `, la carpeta `completadas` estará vacía, y `todas` contendrá solo las canceladas. Si no se especifica ` --status_filter `, por defecto se trabaja con `Completed` para la lógica principal del script, pero la segmentación `completadas`/`canceladas`/`todas` opera sobre el conjunto de datos *después* de este filtro inicial si fue aplicado. Para un análisis completo de todos los estados, se recomienda no usar ` --status_filter ` en CLI y dejar que la segmentación interna maneje los estados.
3.  🌍 **Procesamiento Total:**
    *   El conjunto de datos (ya filtrado por CLI) se procesa en su totalidad.
    *   Se generan tres subconjuntos: operaciones completadas, canceladas y todas las operaciones.
    *   Para cada subconjunto, se calculan métricas, se generan tablas, figuras y un reporte HTML, guardándose en `output/total/[completadas|canceladas|todas]/`.
4.  🗓️ **Procesamiento Anual (Opcional):**
    *   Si no se especifica ` --no_annual_breakdown `, el script identifica todos los años únicos presentes en los datos (post-filtrado CLI).
    *   Para cada año:
        *   Se filtra el conjunto de datos para ese año específico.
        *   Se generan tres subconjuntos: operaciones completadas, canceladas y todas las operaciones de ese año.
        *   Para cada subconjunto, se calculan métricas, se generan tablas, figuras y un reporte HTML, guardándose en `output/[año]/[completadas|canceladas|todas]/`.
5.  📝 **Generación de Nombres de Archivo:** Los nombres de los archivos de salida (tablas, figuras) incorporan los filtros CLI aplicados para facilitar la identificación (ej. `asset_stats_fiat_UYU_asset_USDT_status_Completed.csv`).

## 📁 Estructura del Proyecto

```plaintext
p2p/
├── data/                     # Carpeta para el archivo CSV de entrada
│   └── p2p.csv               # (Debe colocarse aquí manualmente)
├── output/                   # Carpeta base donde se guardan todos los resultados
│   ├── total/                # Resultados para el conjunto de datos completo (filtrado por CLI)
│   │   ├── canceladas/
│   │   │   ├── figures/
│   │   │   ├── reports/
│   │   │   └── tables/       # Tablas CSV generadas por Polars
│   │   ├── completadas/
│   │   │   ├── figures/
│   │   │   ├── reports/
│   │   │   └── tables/       # Tablas CSV generadas por Polars
│   │   └── todas/
│   │       ├── figures/
│   │       ├── reports/
│   │       └── tables/       # Tablas CSV generadas por Polars
│   ├── 2022/                 # Resultados filtrados para el año 2022
│   │   ├── canceladas/
│   │   │   └── ... (misma estructura que total/)
│   │   ├── completadas/
│   │   │   └── ...
│   │   └── todas/
│   │       └── ...
│   ├── 2023/                 # Resultados filtrados para el año 2023
│   │   └── ... (misma estructura)
│   └── ...                   # (Más carpetas de años si existen en los datos)
├── src/                      # Código fuente
│   └── analisis_profesional_p2p.py # Script principal de análisis (usa Polars)
├── templates/                # Plantillas HTML
│   └── report_template.html  # Plantilla para el reporte HTML
├── README.md                 # Este archivo
└── requirements.txt          # Dependencias del proyecto
```

## 🛠️ Requisitos

*   Python 3.8 o superior
*   Las librerías listadas en `requirements.txt`.

## ⚙️ Instalación

1.  **Clonar el repositorio (si aplica) o descargar los archivos.**
2.  **Crear un entorno virtual (recomendado):**
    ```bash
    python -m venv venv
    # En Linux/macOS
    source venv/bin/activate
    # En Windows
    # venv\Scripts\activate
    ```
3.  **Instalar las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Preparar los datos:**
    *   Coloca tu archivo CSV de operaciones P2P en la carpeta `data/` (ej. `data/p2p.csv`).

## 🚀 Uso

El script principal es `src/analisis_profesional_p2p.py`. Se ejecuta desde la línea de comandos.

**Comando Básico (Análisis Total y por Año, segmentado por estado):**

Procesa `data/p2p.csv` y guarda los resultados en la estructura de carpetas dentro de `output/`. Por defecto, considera las órdenes `"Completed"` para ciertos cálculos base si ` --status_filter ` no se usa, pero la segmentación `completadas/canceladas/todas` siempre se realiza.

```bash
python src/analisis_profesional_p2p.py --csv data/p2p.csv
```

**Solo Análisis Total (sin desglose anual):**

Utiliza el flag ` --no_annual_breakdown `. La segmentación por estado (`completadas/canceladas/todas`) se mantiene para el directorio `total/`.

```bash
python src/analisis_profesional_p2p.py --csv data/p2p.csv --no_annual_breakdown
```

**Especificar Carpeta de Salida Principal:**

```bash
python src/analisis_profesional_p2p.py --csv data/p2p.csv --out mis_resultados
```

**Ejemplos de Filtrado (se aplican al conjunto de datos *antes* del desglose anual y la segmentación por estado):**

*   **Filtrar por Fiat UYU y Activo USDT:**
    ```bash
    python src/analisis_profesional_p2p.py --csv data/p2p.csv --fiat_filter UYU --asset_filter USDT
    ```
    > *(Los nombres de los archivos CSV/PNG dentro de las carpetas `output/[periodo]/[estado]/tables/` y `output/[periodo]/[estado]/figures/` reflejarán estos filtros CLI en sus nombres.)*

*   **Filtrar por estado de orden "Cancelled" (CLI):**
    ```bash
    python src/analisis_profesional_p2p.py --csv data/p2p.csv --status_filter Cancelled
    ```
    > *(En este caso, dentro de `output/[periodo]/`, la subcarpeta `completadas/` estará vacía o no se creará. La carpeta `canceladas/` y `todas/` contendrán los datos de las órdenes canceladas. Los nombres de archivo reflejarán `status_Cancelled`.)*

**Argumentos Disponibles:**

*   `--csv RUTA_CSV` (**Requerido**): Ruta al archivo CSV de operaciones P2P.
*   `--out CARPETA_SALIDA`: Carpeta base para guardar los resultados (Default: `output`).
*   `--fiat_filter [FIAT1 FIAT2 ...]`: Filtrar por una o más monedas Fiat.
*   `--asset_filter [ASSET1 ASSET2 ...]`: Filtrar por uno o más tipos de Activos.
*   `--status_filter [STATUS1 STATUS2 ...]`: Filtrar por uno o más Estados de orden a nivel global *antes* de la segmentación. Si no se usa, el script podría tener un comportamiento por defecto (ej. `'Completed'`) para ciertos análisis base, pero la segmentación `completadas/canceladas/todas` siempre ocurrirá sobre el conjunto de datos resultante. Para analizar todos los estados sin filtro previo, no usar este argumento.
*   `--payment_method_filter [METODO1 METODO2 ...]`: Filtrar por uno o más Métodos de Pago.
*   `--no_annual_breakdown`: Si se establece, no se generan resultados desglosados por año; solo se procesa el conjunto total (con su respectiva segmentación por estado).

## 🤝 Contribuciones y Mejoras

Sugerencias y contribuciones son bienvenidas. Posibles áreas de mejora futura podrían incluir:

*   📈 Análisis de rentabilidad por operación (si se dispone de datos de coste).
*   🔍 Detección de patrones o anomalías más sofisticada.
*   🖥️ Interfaz gráfica de usuario (GUI).
*   🔄 Soporte para diferentes formatos de entrada de exchange.
*   🧪 Tests unitarios y de integración para la lógica de **Polars**.
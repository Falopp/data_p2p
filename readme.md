# Proyecto de Análisis de Datos P2P (Versión Profesional)

Este proyecto realiza un análisis exhaustivo de datos de operaciones Peer-to-Peer (P2P) exportados desde plataformas como Binance. El script principal procesa un archivo CSV, calcula diversas métricas financieras y de actividad, genera tablas de resumen, visualizaciones detalladas y un reporte HTML, organizando los resultados por año y en un consolidado total.

## Características Principales

*   **Análisis Detallado:** Calcula estadísticas sobre activos, monedas fiat, precios, comisiones, y actividad horaria/mensual.
*   **Desglose Anual y Total:** Genera un conjunto completo de resultados (tablas, gráficos y reportes HTML) para el período total de los datos y para cada año individual presente en el dataset.
*   **Filtrado Avanzado:** Permite filtrar los datos por múltiples criterios directamente desde la línea de comandos. Estos filtros se aplican antes del desglose anual.
    *   Moneda Fiat (ej. UYU, USD)
    *   Tipo de Activo (ej. USDT, BTC)
    *   Estado de la Orden (ej. Completed, Cancelled)
    *   Método de Pago
*   **Visualizaciones Claras:** Genera una amplia gama de gráficos utilizando `matplotlib` y `seaborn`.
*   **Reportes HTML:** Genera un reporte HTML por cada periodo (total y anual) que resume los filtros aplicados, métricas clave y las figuras generadas.
*   **Salida Organizada:** Todos los resultados se guardan en una carpeta principal (por defecto `output/`). Dentro de ella, se crean subcarpetas para el análisis `total/` y para cada año (ej. `2022/`, `2023/`). Cada una de estas carpetas contiene subdirectorios `tables/` (para archivos CSV), `figures/` (para gráficos PNG) y `reports/` (para archivos HTML).
*   **Robustez:** Manejo mejorado de formatos numéricos, columnas de datos faltantes y errores en la generación de gráficos individuales.

## Estructura del Proyecto

```
p2p/
├── data/                     # Carpeta para el archivo CSV de entrada
│   └── p2p.csv               # (Debe colocarse aquí manualmente)
├── output/                   # Carpeta base donde se guardan todos los resultados
│   ├── total/                # Resultados para el conjunto de datos completo (filtrado por CLI)
│   │   ├── tables/
│   │   │   ├── asset_stats_general_status_completed.csv
│   │   │   └── ...
│   │   ├── figures/
│   │   │   ├── hourly_operations_general_status_completed.png
│   │   │   └── ...
│   │   └── reports/
│   │       └── p2p_sales_report_general_status_completed.html
│   ├── 2022/                 # Resultados filtrados para el año 2022
│   │   ├── tables/
│   │   │   └── ... 
│   │   ├── figures/
│   │   │   └── ...
│   │   └── reports/
│   │       └── ...
│   ├── 2023/                 # Resultados filtrados para el año 2023
│   │   └── ...
│   └── ...                   # (Más carpetas de años si existen en los datos)
├── src/                      # Código fuente
│   └── analisis_profesional_p2p.py # Script principal de análisis
├── templates/                # Plantillas HTML
│   └── report_template.html  # Plantilla para el reporte HTML
├── config.yaml               # Archivo de configuración opcional
├── README.md                 # Este archivo
└── requirements.txt          # Dependencias del proyecto
```

## Requisitos

*   Python 3.8 o superior
*   Las librerías listadas en `requirements.txt`.

## Instalación

1.  **Clonar el repositorio (si aplica) o descargar los archivos.**
2.  **Crear un entorno virtual (recomendado).**
3.  **Instalar las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Preparar los datos:**
    *   Coloca tu archivo CSV de operaciones P2P en la carpeta `data/` (ej. `data/p2p.csv`).

## Uso

El script principal es `src/analisis_profesional_p2p.py`. Se ejecuta desde la línea de comandos.

**Comando Básico (Análisis Total y por Año):**
Procesa `data/p2p.csv` y guarda los resultados en la estructura de carpetas dentro de `output/`.

```bash
python src/analisis_profesional_p2p.py --csv data/p2p.csv
```

**Solo Análisis Total (sin desglose anual):**
Utiliza el flag `--no_annual_breakdown`.

```bash
python src/analisis_profesional_p2p.py --csv data/p2p.csv --no_annual_breakdown
```

**Especificar Carpeta de Salida Principal:**

```bash
python src/analisis_profesional_p2p.py --csv data/p2p.csv --out mis_resultados
```

**Ejemplos de Filtrado (se aplican al conjunto de datos antes del desglose anual):**

*   **Filtrar por Fiat UYU y Activo USDT:**
    ```bash
    python src/analisis_profesional_p2p.py --csv data/p2p.csv --fiat_filter UYU --asset_filter USDT
    ```
    *(Los nombres de los archivos CSV/PNG dentro de las carpetas `total/tables/`, `2022/tables/`, etc., reflejarán estos filtros CLI.)*

**Argumentos Disponibles:**

*   `--csv RUTA_CSV` (Requerido): Ruta al archivo CSV de operaciones P2P.
*   `--out CARPETA_SALIDA`: Carpeta base para guardar los resultados (Default: `output`).
*   `--fiat_filter [FIAT1 FIAT2 ...]`: Filtrar por una o más monedas Fiat.
*   `--asset_filter [ASSET1 ASSET2 ...]`: Filtrar por uno o más tipos de Activos.
*   `--status_filter [STATUS1 STATUS2 ...]`: Filtrar por uno o más Estados de orden (Default: `Completed`).
*   `--payment_method_filter [METODO1 METODO2 ...]`: Filtrar por uno o más Métodos de Pago.
*   `--no_annual_breakdown`: Si se establece, no se generan resultados desglosados por año; solo se procesa el conjunto total.

## Contribuciones y Mejoras

Sugerencias y contribuciones son bienvenidas. Posibles áreas de mejora futura podrían incluir:
*   Análisis de rentabilidad por operación (si se dispone de datos de coste).
*   Detección de patrones o anomalías más sofisticada.
*   Interfaz gráfica de usuario (GUI).
*   Soporte para diferentes formatos de entrada de exchange.
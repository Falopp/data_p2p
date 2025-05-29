#!/usr/bin/env python3
"""Análisis integral de operaciones P2P (Versión Profesional Avanzada).

Ejemplo:
    python src/analisis_profesional_p2p.py --csv data/p2p.csv --out output_profesional
"""
from __future__ import annotations
import argparse
import os
import textwrap
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns # Importado seaborn
import pytz
import yaml # <--- Añadido
import logging # <--- Añadido
import datetime # <--- Añadido para timestamp
from jinja2 import Environment, FileSystemLoader # <--- Añadido para Jinja2

# --- Configuración de Logging Básico ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuración por Defecto ---
DEFAULT_CONFIG = {
    'column_mapping': {
        'order_number': "Order Number",
        'order_type': "Order Type",
        'asset_type': "Asset Type",
        'fiat_type': "Fiat Type",
        'total_price': "Total Price",
        'price': "Price",
        'quantity': "Quantity",
        'status': "Status",
        'match_time_utc': "Match time(UTC)",
        'payment_method': "Payment Method",
        'maker_fee': "Maker Fee",
        'taker_fee': "Taker Fee",
        'sale_value_reference_fiat': None # Ejemplo: "Value in USD"
    },
    'sell_operation': {
        'indicator_column': "order_type", # <--- CORREGIDO a nombre interno
        'indicator_value': "SELL"
    },
    'reference_fiat_for_sales_summary': "USD", # Moneda para intentar convertir/mostrar como referencia
    'html_report': {
        'include_tables_default': ["asset_stats", "fiat_stats"],
        'include_figures_default': ["hourly_operations"]
    }
}

# --- Funciones de Configuración ---
def load_config(config_path: str | None) -> dict:
    """Carga la configuración desde un archivo YAML, usando defaults si el archivo o claves faltan."""
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
            if user_config:
                # Fusionar user_config con DEFAULT_CONFIG de forma profunda (para claves anidadas)
                config = DEFAULT_CONFIG.copy() # Empezar con una copia de los defaults
                for key, value in user_config.items():
                    if isinstance(value, dict) and isinstance(config.get(key), dict):
                        config[key] = {**config.get(key, {}), **value} # Fusionar diccionarios internos
                    else:
                        config[key] = value # Sobrescribir o añadir
                logger.info(f"Configuración cargada desde: {config_path}")
                return config
        except Exception as e:
            logger.error(f"Error al cargar o parsear el archivo de configuración '{config_path}': {e}. Se usarán los valores por defecto.")
    else:
        if config_path: # Si se especificó una ruta pero no existe
            logger.warning(f"Archivo de configuración no encontrado en '{config_path}'. Se usarán los valores por defecto.")
        else: # Si no se especificó ninguna ruta
            logger.info("No se especificó archivo de configuración. Se usarán los valores por defecto.")
    return DEFAULT_CONFIG.copy() # Devolver una copia para evitar modificaciones globales

# Establecer un tema visual agradable para seaborn
sns.set_theme(style="whitegrid")

# --- Funciones Auxiliares (Helpers) ---

def parse_amount(val: str | float | int) -> float:
    """Convierte strings con puntos de miles ("53.550.640,279" o "53.550.640.279") -> float."""
    if pd.isna(val):
        return 0.0
    
    original_val = val

    if not isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            return 0.0
    
    # Lógica de parseo robusta (adaptada de la original del README y mejorada)
    val = val.strip()
    # Caso: "1.234,56" (punto para miles, coma para decimal) -> "1234.56"
    if '.' in val and ',' in val and val.rfind('.') < val.rfind(','):
        val = val.replace('.', '').replace(',', '.')
    # Caso: "1,234.56" (coma para miles, punto para decimal) -> "1234.56"
    elif ',' in val and '.' in val and val.rfind(',') < val.rfind('.'):
        val = val.replace(',', '')
    # Caso: "1.234" o "1,234" (solo separador de miles, sin decimales explícitos)
    # O "123,45" (coma como decimal)
    elif ',' in val and '.' not in val:
        if val.count(',') == 1 and len(val.split(',')[-1]) <=2: # Probable decimal como "123,45"
             val = val.replace(',', '.')
        else: # Comas son separadores de miles
             val = val.replace(',', '') 
    # Caso: "1.234.567" (puntos como separadores de miles) o "1234.56" (punto como decimal)
    #       o "53.550.640.279" (este es el formato original problemático)
    elif '.' in val and ',' not in val:
        parts = val.split('.')
        if len(parts) > 2: # Múltiples puntos, asumir que todos menos el último son miles
            integer_part = "".join(parts[:-1])
            decimal_part = parts[-1]
            val = f"{integer_part}.{decimal_part}"
        # Si len(parts) == 2 (ej. "1234.56") o 1 (ej. "1234"), float() lo maneja.
    
    try:
        return float(val)
    except ValueError:
        # print(f"Advertencia parse_amount: No se pudo convertir '{original_val}' (procesado como '{val}') a float. Se usará 0.0.")
        return 0.0

# --- Funciones de Análisis Principal (sin cambios por ahora, se adaptarán luego) ---

def analyze(df: pd.DataFrame, col_map: dict, sell_config: dict) -> tuple[pd.DataFrame, dict[str, pd.DataFrame | pd.Series]]:
    """Devuelve un DataFrame procesado y un dict de DataFrames/Series con todas las métricas.
       La función es ahora más idempotente: si las columnas procesadas ya existen, las usa.
       Utiliza col_map para los nombres de columna y sell_config para identificar ventas.
    """
    logger.info("Iniciando análisis...")
    df_processed = df.copy()

    # --- Nombres de columna INTERNOS que el script usará --- 
    # Estos son los nombres definidos como CLAVES en DEFAULT_CONFIG['column_mapping']
    # y son los nombres que el DataFrame df_processed tendrá DESPUÉS del renombrado inicial.
    order_type_col = 'order_type'
    asset_type_col = 'asset_type'
    fiat_type_col = 'fiat_type'
    total_price_col = 'total_price'
    price_col = 'price'
    quantity_col = 'quantity'
    status_col = 'status'
    match_time_utc_col = 'match_time_utc' # Nombre INTERNO esperado
    maker_fee_col = 'maker_fee'
    taker_fee_col = 'taker_fee'
    order_number_col = 'order_number'
    payment_method_col = 'payment_method' # Aunque no se use directamente aquí, para consistencia
    # sale_value_reference_fiat_col = 'sale_value_reference_fiat' # Si se usara

    # --- Transformaciones Numéricas --- 
    logger.info("Transformando columnas numéricas (si es necesario)...")
    # Nombres de columnas originales (del CSV) vs nombres de columnas numéricas nuevas (internas)
    # Las claves aquí son los nombres INTERNOS después del mapeo inicial.
    # Los valores son los nombres de las NUEVAS columnas numéricas que se crearán.
    cols_to_process_numeric = {
        quantity_col: 'Quantity_num',
        maker_fee_col: 'MakerFee_num',
        taker_fee_col: 'TakerFee_num',
        price_col: 'Price_num',
        total_price_col: 'TotalPrice_num'
    }

    for original_col_internal_name, new_num_col in cols_to_process_numeric.items():
        if new_num_col not in df_processed.columns: # Solo procesar si la columna numérica no existe
            if original_col_internal_name in df_processed.columns:
                logger.info(f"Procesando columna: {original_col_internal_name} -> {new_num_col}")
                df_processed[new_num_col] = df_processed[original_col_internal_name].apply(parse_amount)
            else:
                logger.warning(f"Columna original mapeada a '{original_col_internal_name}' no encontrada para crear '{new_num_col}'. Se creará '{new_num_col}' con ceros.")
                df_processed[new_num_col] = 0.0
        else:
            logger.info(f"Columna numérica '{new_num_col}' ya existe, se usará directamente.")

    # Asegurar que las columnas de fees existan para calcular TotalFee (usando los nombres NUEVOS)
    if 'MakerFee_num' not in df_processed.columns: df_processed['MakerFee_num'] = 0.0
    if 'TakerFee_num' not in df_processed.columns: df_processed['TakerFee_num'] = 0.0
    df_processed['TotalFee'] = df_processed['MakerFee_num'] + df_processed['TakerFee_num']

    # --- Procesamiento de Tiempo --- 
    logger.info("Procesando columnas de tiempo (si es necesario)...")
    # Match_time_local es la columna clave que indica si el procesamiento de tiempo ya se hizo.
    if 'Match_time_local' not in df_processed.columns or not pd.api.types.is_datetime64_any_dtype(df_processed['Match_time_local']):
        # <<< LOGGING ADICIONAL AQUÍ >>>
        logger.info(f"Intentando encontrar la columna de tiempo UTC. Nombre esperado de col_map: '{match_time_utc_col}'.")
        logger.info(f"Columnas disponibles en df_processed: {df_processed.columns.tolist()}")
        # <<< FIN LOGGING ADICIONAL >>>
        if match_time_utc_col in df_processed.columns:
            logger.info(f"Creando columnas de tiempo a partir de '{match_time_utc_col}': Match_time_utc_dt, Match_time_local, hour_local, YearMonth, Year")
            
            rows_before_conversion = len(df_processed)
            logger.info(f"Filas antes de conversión de '{match_time_utc_col}': {rows_before_conversion}")

            df_processed['Match_time_utc_dt'] = pd.to_datetime(df_processed[match_time_utc_col], utc=True, errors='coerce')
            
            nat_count = df_processed['Match_time_utc_dt'].isna().sum()
            logger.info(f"Número de valores NaT generados después de convertir '{match_time_utc_col}': {nat_count} de {rows_before_conversion} filas.")
            
            rows_before_dropna = len(df_processed)
            df_processed.dropna(subset=['Match_time_utc_dt'], inplace=True) 
            rows_after_dropna = len(df_processed)
            logger.info(f"Filas eliminadas por NaT en 'Match_time_utc_dt': {rows_before_dropna - rows_after_dropna}")
            logger.info(f"Filas restantes después de dropna: {rows_after_dropna}")
            
            if not df_processed.empty and pd.api.types.is_datetime64_any_dtype(df_processed['Match_time_utc_dt']):
                uy_tz = pytz.timezone('America/Montevideo') # Considerar hacerlo configurable
                df_processed['Match_time_local'] = df_processed['Match_time_utc_dt'].dt.tz_convert(uy_tz)
                df_processed['hour_local']       = df_processed['Match_time_local'].dt.hour
                df_processed['YearMonth']        = df_processed['Match_time_local'].dt.to_period('M')
                df_processed['Year']             = df_processed['Match_time_local'].dt.year
            else:
                logger.warning(f"'{match_time_utc_col}' no pudo ser convertida a datetime o resultó en df vacío después de dropna. Columnas de tiempo no creadas/actualizadas.")
                # Asegurar que estas columnas existan como NA/NaT si no se pueden crear correctamente
                for col_to_add_na in ['Match_time_local', 'hour_local', 'YearMonth', 'Year']:
                    if col_to_add_na not in df_processed.columns:
                         df_processed[col_to_add_na] = pd.NA if col_to_add_na != 'Match_time_local' else pd.NaT
                    else: # Si ya existe pero el flujo falló, forzar a NA/NaT para consistencia
                         df_processed[col_to_add_na] = pd.NA if col_to_add_na != 'Match_time_local' else pd.NaT

            logger.info(f"dtypes después de procesamiento de tiempo inicial:\n{df_processed.dtypes[['Match_time_utc_dt', 'Match_time_local', 'hour_local', 'YearMonth', 'Year']].to_string() if not df_processed.empty and all(c in df_processed.columns for c in ['Match_time_utc_dt', 'Match_time_local', 'hour_local', 'YearMonth', 'Year']) else 'Columnas de tiempo no disponibles para dtypes.'}")

        else:
            logger.warning(f"Columna de tiempo original mapeada a '{match_time_utc_col}' no encontrada. Columnas de tiempo no creadas.")
            df_processed['Match_time_local'] = pd.NaT # Asegurar que estas columnas existan como NA/NaT si no se pueden crear
            df_processed['hour_local'] = pd.NA
            df_processed['YearMonth'] = pd.NA
            df_processed['Year'] = pd.NA
    elif 'Match_time_local' in df_processed.columns and pd.api.types.is_datetime64_any_dtype(df_processed['Match_time_local']):
        logger.info("Columnas de tiempo base (Match_time_local) ya existen y son válidas.")
        # Asegurar que las columnas derivadas existan si Match_time_local existe
        if 'hour_local' not in df_processed.columns: df_processed['hour_local'] = df_processed['Match_time_local'].dt.hour
        if 'YearMonth' not in df_processed.columns: df_processed['YearMonth'] = df_processed['Match_time_local'].dt.to_period('M')
        if 'Year' not in df_processed.columns: df_processed['Year'] = df_processed['Match_time_local'].dt.year
    else:
        logger.warning(f"'Match_time_local' existe pero no es datetime. Forzando a NaT y derivadas a NA.")
        df_processed['Match_time_local'] = pd.NaT
        df_processed['hour_local'] = pd.NA
        df_processed['YearMonth'] = pd.NA
        df_processed['Year'] = pd.NA

    metrics: dict[str, pd.DataFrame | pd.Series] = {}
    logger.info("Calculando métricas existentes...")

    # --- DataFrame para métricas específicas de ventas (que suelen requerir 'Completed') ---
    # Este df_completed_for_sales_summary se usará solo para el resumen de ventas.
    df_completed_for_sales_summary = pd.DataFrame() # Inicializar vacío
    if status_col in df_processed.columns:
        df_completed_for_sales_summary = df_processed[df_processed[status_col] == 'Completed'].copy()
        if df_completed_for_sales_summary.empty:
            logger.info(f"No hay operaciones con estado 'Completed' en el DataFrame actual (base para resumen de ventas). El resumen de ventas podría estar vacío.")
    else:
        logger.warning(f"Columna de estado '{status_col}' no encontrada. El resumen de ventas (que busca 'Completed') no se podrá calcular.")

    # --- Métricas Financieras y Estadísticas Clave (calculadas sobre df_processed) ---
    # df_processed ya está filtrado por la categoría de estado deseada (todas, completadas, canceladas)
    # desde el bucle principal antes de llamar a analyze.

    # Verificar si las columnas necesarias para las métricas financieras existen en df_processed
    required_financial_cols_internal = [order_number_col, 'Quantity_num', 'TotalPrice_num', 'TotalFee', 'Price_num', asset_type_col, fiat_type_col]
    
    missing_cols_check = []
    for col_key in [order_number_col, asset_type_col, fiat_type_col]:
        if col_key not in df_processed.columns:
            missing_cols_check.append(f"'{col_key}' (mapeada desde config)")
    for num_col_suffix in ['Quantity_num', 'TotalPrice_num', 'TotalFee', 'Price_num']:
        if num_col_suffix not in df_processed.columns:
            missing_cols_check.append(f"'{num_col_suffix}' (generada numéricamente)")

    if missing_cols_check:
        logger.warning(f"Faltan columnas esenciales en el DataFrame para calcular métricas: {', '.join(missing_cols_check)}. Algunas métricas estarán vacías o darán error.")
        # Inicializar métricas como vacías si faltan columnas clave
        metrics['asset_stats'] = pd.DataFrame()
        metrics['fiat_stats'] = pd.DataFrame()
        metrics['price_stats'] = pd.DataFrame()
        metrics['fees_stats'] = pd.DataFrame()
        metrics['monthly_fiat'] = pd.DataFrame()
    else:
        logger.info("Calculando asset_stats (sobre df_processed)...")
        metrics['asset_stats'] = (df_processed.groupby([asset_type_col, order_type_col])
                                    .agg(operations=(order_number_col,'count'),
                                         quantity=('Quantity_num','sum'),
                                         total_fiat=('TotalPrice_num','sum'),
                                         total_fees=('TotalFee','sum'))
                                    .sort_values('total_fiat', ascending=False))

        logger.info("Calculando fiat_stats (sobre df_processed)...")
        metrics['fiat_stats']  = (df_processed.groupby([fiat_type_col, order_type_col])
                                    .agg(operations=(order_number_col,'count'),
                                         total_fiat=('TotalPrice_num','sum'),
                                         avg_price=('Price_num','mean'),
                                         total_fees=('TotalFee','sum'))
                                    .sort_values('total_fiat', ascending=False))

        logger.info("Calculando price_stats (sobre df_processed)...")
        if not df_processed.empty and fiat_type_col in df_processed.columns and 'Price_num' in df_processed.columns:
            metrics['price_stats'] = (df_processed.groupby(fiat_type_col)['Price_num']
                                      .agg(avg_price='mean', median_price='median', min_price='min', max_price='max',
                                           std_price='std',
                                           q1_price=lambda x: x.quantile(0.25),
                                           q3_price=lambda x: x.quantile(0.75),
                                           iqr_price=lambda x: x.quantile(0.75) - x.quantile(0.25),
                                           p1_price=lambda x: x.quantile(0.01),
                                           p99_price=lambda x: x.quantile(0.99)
                                          )
                                      .reset_index())
        else:
            logger.warning(f"No se pueden calcular price_stats (sobre df_processed). DataFrame vacío, o faltan '{fiat_type_col}' o 'Price_num'.")
            metrics['price_stats'] = pd.DataFrame()

        logger.info("Calculando fees_stats (sobre df_processed)...")
        if not df_processed.empty and asset_type_col in df_processed.columns and 'TotalFee' in df_processed.columns:
             metrics['fees_stats'] = (df_processed.groupby(asset_type_col)
                                     .agg(total_fees_collected=('TotalFee', 'sum'),
                                          avg_fee_per_op=('TotalFee', 'mean'),
                                          num_ops_with_fees=('TotalFee', lambda x: (x > 0).sum()), 
                                          max_fee=('TotalFee', 'max'))
                                     .sort_values('total_fees_collected', ascending=False))
        else:
            logger.warning(f"No se pueden calcular fees_stats (sobre df_processed). DataFrame vacío, o faltan '{asset_type_col}' o 'TotalFee'.")
            metrics['fees_stats'] = pd.DataFrame()

        logger.info("Calculando monthly_fiat (sobre df_processed)...")
        if not df_processed.empty and 'YearMonth' in df_processed.columns and \
           fiat_type_col in df_processed.columns and 'TotalPrice_num' in df_processed.columns and \
           order_type_col in df_processed.columns:
            metrics['monthly_fiat'] = (df_processed.groupby(['YearMonth', fiat_type_col, order_type_col])
                                     ['TotalPrice_num'].sum().unstack(fill_value=0)
                                     .reset_index())
        else:
            logger.warning(f"No se pueden calcular monthly_fiat (sobre df_processed). DataFrame vacío o faltan columnas requeridas (YearMonth, {fiat_type_col}, TotalPrice_num, {order_type_col}).")
            metrics['monthly_fiat'] = pd.DataFrame()

    # --- Métricas Generales (sobre todo el df_processed, no solo 'Completed') ---
    # Estas usan el df_processed que ya tiene filtros CLI aplicados.
    
    # Contadores de estado (usando la columna de estado INTERNA)
    if status_col in df_processed.columns:
        metrics['status_counts'] = df_processed[status_col].value_counts()
    else:
        logger.warning(f"Columna de estado mapeada a '{status_col}' no encontrada. No se calculará 'status_counts'.")
        metrics['status_counts'] = pd.Series(dtype='int64')

    # Contadores de tipo de orden (BUY/SELL) (usando la columna de tipo de orden INTERNA)
    if order_type_col in df_processed.columns:
        metrics['side_counts'] = df_processed[order_type_col].value_counts()
    else:
        logger.warning(f"Columna de tipo de orden mapeada a '{order_type_col}' no encontrada. No se calculará 'side_counts'.")
        metrics['side_counts'] = pd.Series(dtype='int64')

    # Operaciones por hora local (si la columna 'hour_local' fue creada)
    if 'hour_local' in df_processed.columns and not df_processed['hour_local'].isna().all():
        metrics['hourly_counts'] = df_processed['hour_local'].value_counts().sort_index()
    else:
        logger.warning("Columna 'hour_local' no disponible o vacía. No se calculará 'hourly_counts'.")
        metrics['hourly_counts'] = pd.Series(dtype='int64')

    # --- NUEVAS MÉTRICAS DE RESUMEN DE VENTAS ---
    logger.info("Calculando nuevas métricas de resumen de ventas...")
    sell_indicator_col_mapped = sell_config.get('indicator_column') 
    sell_indicator_value = sell_config.get('indicator_value')
    
    sales_summary_metrics = {} 

    if not (sell_indicator_col_mapped and sell_indicator_value and sell_indicator_col_mapped in df_processed.columns):
        logger.warning(f"Configuración de ventas incompleta o columna '{sell_indicator_col_mapped}' no encontrada. No se calcularán las métricas de resumen de ventas.")
    # Usar df_completed_for_sales_summary para el resumen de ventas, ya que este se basa en 'Completed'
    elif df_completed_for_sales_summary.empty:
         logger.warning(f"No hay operaciones completadas (df_completed_for_sales_summary) para calcular el resumen de ventas.")
    else:
        # Filtrar solo operaciones de venta completadas desde df_completed_for_sales_summary
        df_sales_completed = df_completed_for_sales_summary[df_completed_for_sales_summary[sell_indicator_col_mapped] == sell_indicator_value]

        if df_sales_completed.empty:
            logger.info(f"No se encontraron operaciones de venta (columna '{sell_indicator_col_mapped}' == '{sell_indicator_value}') entre las completadas.")
        else:
            logger.info(f"Procesando {len(df_sales_completed)} operaciones de venta completadas.")
            # Agrupar por activo vendido
            # Columnas necesarias: asset_type_col, quantity_col (numérico), total_price_col (numérico), fiat_type_col
            # Nombres numéricos: 'Quantity_num', 'TotalPrice_num'
            
            required_cols_for_sales = [asset_type_col, 'Quantity_num', 'TotalPrice_num', fiat_type_col]
            if not all(col in df_sales_completed.columns for col in required_cols_for_sales):
                logger.warning(f"Faltan columnas para el resumen de ventas ({', '.join(required_cols_for_sales)}). No se calculará.")
            else:
                # Calcular métricas por cada activo vendido y por cada fiat en la que se recibió el pago
                # Un activo puede venderse contra diferentes fiats.
                
                sales_summary_list = []
                for (asset, fiat), group_data in df_sales_completed.groupby([asset_type_col, fiat_type_col]):
                    total_asset_sold = group['Quantity_num'].sum()
                    total_fiat_received = group['TotalPrice_num'].sum()
                    
                    if total_asset_sold > 0: # Evitar división por cero
                        avg_sell_price = total_fiat_received / total_asset_sold
                    else:
                        avg_sell_price = 0.0 # O pd.NA

                    sales_summary_list.append({
                        'Asset Sold': asset,
                        'Fiat Received': fiat,
                        'Total Asset Sold': total_asset_sold,
                        'Total Fiat Received': total_fiat_received,
                        'Average Sell Price (in Fiat Received)': avg_sell_price
                    })
                
                if sales_summary_list:
                    df_sales_summary_all_assets = pd.DataFrame(sales_summary_list)
                    
                    # Guardar este DataFrame general en las métricas
                    metrics['sales_summary_all_assets_fiat_detailed'] = df_sales_summary_all_assets
                    logger.info(f"Resumen de ventas detallado por activo/fiat calculado con {len(df_sales_summary_all_assets)} filas.")

                    # Adicionalmente, podríamos querer un resumen por ACTIVO solamente,
                    # si un activo se vende contra múltiples fiats, podríamos agregarlo.
                    # Por ahora, el detalle por fiat es más informativo.
                    # Si se necesita agregar, considerar cómo manejar múltiples fiats para "Average Sell Price".
                    
                    # Ejemplo de cómo se podría agregar por Asset si solo hay una fiat principal o si se quiere un total general
                    # (esto requiere una lógica más compleja si hay muchas fiats por activo)
                    # simple_sales_summary = df_sales_summary_all_assets.groupby('Asset Sold').agg(
                    #    Total_Asset_Sold_Agg=('Total Asset Sold', 'sum'),
                    #    # No se puede sumar directamente Total_Fiat_Received si son diferentes monedas
                    #    # No se puede promediar directamente Average_Sell_Price si son diferentes monedas
                    # ).reset_index()
                    # metrics['sales_summary_by_asset_simple'] = simple_sales_summary


    logger.info("Análisis completado.")
    return df_processed, metrics

# --- Funciones de Visualización ---
def plot_hourly(hourly_counts: pd.Series, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    if hourly_counts.empty:
        logger.info(f"No hay datos para el gráfico horario{title_suffix}.")
        return None
    hourly_counts_reindexed = hourly_counts.reindex(range(24), fill_value=0)
    plt.figure(figsize=(12, 6))
    sns.barplot(x=hourly_counts_reindexed.index, y=hourly_counts_reindexed.values, color="skyblue")
    plt.title(f'Operaciones por Hora del Día (Local){title_suffix}')
    plt.xlabel('Hora del Día (0-23)')
    plt.ylabel('Cantidad de Operaciones')
    plt.xticks(range(0, 24, 1))
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    file_path = os.path.join(out_dir, f'hourly_counts{file_identifier}.png')
    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico horario guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el gráfico horario {file_path}: {e}")
        plt.close()
        return None

def plot_monthly(monthly_fiat: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if monthly_fiat.empty:
        logger.info(f"No hay datos para el gráfico mensual{title_suffix}.")
        return saved_paths

    fiat_type_col_internal = 'fiat_type'
    year_month_col_internal = 'YearMonth'

    if year_month_col_internal not in monthly_fiat.columns:
        logger.warning(f"Columna '{year_month_col_internal}' no encontrada para plot_monthly{title_suffix}.")
        return saved_paths
        
    unique_fiats = [None]
    if fiat_type_col_internal in monthly_fiat.columns and monthly_fiat[fiat_type_col_internal].nunique() > 0:
        unique_fiats = monthly_fiat[fiat_type_col_internal].unique()

    for current_fiat in unique_fiats:
        df_plot_full = monthly_fiat.copy()
        plot_title_fiat_part = ""
        current_fiat_label = "general"

        if current_fiat is not None:
            df_plot_full = monthly_fiat[monthly_fiat[fiat_type_col_internal] == current_fiat]
            plot_title_fiat_part = f" para {current_fiat}"
            current_fiat_label = str(current_fiat)
        
        if df_plot_full.empty:
            continue

        potential_value_cols = [col for col in df_plot_full.columns if col not in [year_month_col_internal, fiat_type_col_internal]]
        
        if not potential_value_cols:
            logger.warning(f"No hay columnas de valor para graficar en plot_monthly para {current_fiat_label}{title_suffix}.")
            continue

        plt.figure(figsize=(14, 7))
        
        if isinstance(df_plot_full[year_month_col_internal].dtype, pd.PeriodDtype):
            x_values = df_plot_full[year_month_col_internal].astype(str)
        elif pd.api.types.is_datetime64_any_dtype(df_plot_full[year_month_col_internal]):
            x_values = df_plot_full[year_month_col_internal].dt.strftime('%Y-%m')
        else:
            x_values = df_plot_full[year_month_col_internal]

        for value_col in potential_value_cols:
            if value_col in df_plot_full and pd.api.types.is_numeric_dtype(df_plot_full[value_col]):
                plt.plot(x_values, df_plot_full[value_col], label=str(value_col), marker='o', linestyle='-')

        plt.title(f'Volumen Mensual de Fiat{plot_title_fiat_part}{title_suffix}')
        plt.xlabel('Mes (Año-Mes)')
        plt.ylabel('Volumen Total en Fiat')
        plt.xticks(rotation=45, ha="right")
        plt.legend(title='Tipo de Operación')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        fiat_file_part = f"_{current_fiat_label.lower()}" if current_fiat is not None else "_general"
        file_path = os.path.join(out_dir, f'monthly_fiat_volume{fiat_file_part}{file_identifier}.png')
        try:
            plt.savefig(file_path)
            logger.info(f"Gráfico de volumen mensual ({current_fiat_label}) guardado en: {file_path}")
            saved_paths.append(file_path)
        except Exception as e:
            logger.error(f"Error al guardar el gráfico {file_path}: {e}")
        plt.close()
    return saved_paths

def plot_pie(df_counts: pd.DataFrame, column_name: str, title: str, fname_prefix: str, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    if df_counts.empty or column_name not in df_counts.columns or df_counts[column_name].sum() == 0:
        logger.info(f"No hay datos para el gráfico de torta '{title}'{title_suffix}.")
        return None
    plt.figure(figsize=(10, 7))
    plt.pie(df_counts[column_name], labels=df_counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette('pastel', n_colors=len(df_counts.index)))
    plt.title(f'{title}{title_suffix}')
    plt.axis('equal')
    plt.tight_layout()
    file_path = os.path.join(out_dir, f'{fname_prefix}{file_identifier}.png')
    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico de torta '{title}' guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el gráfico de torta {file_path}: {e}")
        plt.close()
        return None

def plot_price_distribution(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if df_completed.empty:
        logger.info(f"No hay datos completados para graficar distribución de precios{title_suffix}.")
        return saved_paths

    price_num_col = 'Price_num'
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'
    order_type_col_internal = 'order_type'

    required_cols = [price_num_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_completed.columns]
        logger.warning(f"Faltan columnas para graficar distribución de precios ({', '.join(missing)}){title_suffix}.")
        return saved_paths

    for (asset, fiat), group_data in df_completed.groupby([asset_type_col_internal, fiat_type_col_internal]):
        # ELIMINAR DESDE AQUÍ HASTA ANTES DE fig = None
        fig = None  # Inicializar fig para el bloque finally
        file_name_plot = f'price_distribution_{str(asset).lower().replace(" ", "_")}_{str(fiat).lower().replace(" ", "_")}{file_identifier}.png'
        file_path = os.path.join(out_dir, file_name_plot)

        try:
            if group_data.empty or group_data[price_num_col].isna().all():
                logger.info(f"Omitiendo gráfico de distribución de precios para {asset}/{fiat} (archivo: {file_name_plot}) debido a datos vacíos o todos los precios son NaN{title_suffix}.")
                continue

            logger.info(f"Attempting to generate plot: {file_path} (Data rows: {len(group_data)}){title_suffix}")

            fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
            fig.suptitle(f'Distribución de Precios para {asset}/{fiat}{title_suffix}', fontsize=16)

            sns.histplot(data=group_data, x=price_num_col, hue=order_type_col_internal, multiple="stack", kde=False, ax=axes[0], palette="muted", linewidth=0.5, bins=30)
            axes[0].set_title('Histograma de Precios')
            axes[0].set_xlabel('')
            axes[0].set_ylabel('Frecuencia')
            
            handles, labels = axes[0].get_legend_handles_labels()
            if handles: 
                axes[0].legend(handles=handles, labels=labels, title=order_type_col_internal)

            sns.boxplot(data=group_data, x=price_num_col, y=order_type_col_internal, hue=order_type_col_internal, legend=False, ax=axes[1], palette="muted", orient='h')
            axes[1].set_title('Boxplot de Precios')
            axes[1].set_xlabel(f'Precio de {asset} en {fiat}')
            axes[1].set_ylabel(order_type_col_internal)
            
            mean_price = group_data[price_num_col].mean()
            median_price = group_data[price_num_col].median()
            
            current_handles, current_labels = axes[0].get_legend_handles_labels()
            
            if pd.notna(mean_price):
                line_mean = axes[0].axvline(mean_price, color='r', linestyle='--', linewidth=1.5, label=f'Media: {mean_price:.2f}')
                if not any(label.startswith('Media:') for label in current_labels): 
                     current_handles.append(line_mean)
                     current_labels.append(f'Media: {mean_price:.2f}')

            if pd.notna(median_price):
                line_median = axes[0].axvline(median_price, color='g', linestyle=':', linewidth=1.5, label=f'Mediana: {median_price:.2f}')
                if not any(label.startswith('Mediana:') for label in current_labels):
                     current_handles.append(line_median)
                     current_labels.append(f'Mediana: {median_price:.2f}')
            
            if current_handles: 
                axes[0].legend(handles=current_handles, labels=current_labels, title=order_type_col_internal)
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Ajustado para dar espacio al suptitle
            
            plt.savefig(file_path)
            logger.info(f"Successfully generated and saved: {file_path}")
            saved_paths.append(file_path)
        
        except (Exception, KeyboardInterrupt) as e: # MODIFICADO para incluir KeyboardInterrupt
            print(f"DEBUG: Entered except block for {file_path} due to {type(e).__name__}") # <-- DEBUG PRINT ADDED
            logger.error(f"Failed to generate/save plot {file_path} for {asset}/{fiat}{title_suffix} due to {type(e).__name__}: {e}. Creating placeholder image.")
            if isinstance(e, KeyboardInterrupt):
                logger.warning(f"Plot generation for {file_path} was manually interrupted by the user.")
            try:
                if fig is not None and plt.fignum_exists(fig.number):
                    plt.close(fig) # Cerrar la figura original si existe y está abierta
                
                error_fig, error_ax = plt.subplots(figsize=(10, 3)) # Figura simple para el mensaje de error
                error_text = f"Error al generar gráfico para:\n{asset}/{fiat}{title_suffix}\nConsulte los logs para más detalles."
                error_ax.text(0.5, 0.5, error_text, ha='center', va='center', fontsize=10, color='red', wrap=True)
                error_ax.axis('off')
                plt.tight_layout()
                error_fig.savefig(file_path) # Guardar el placeholder en la ruta original
                logger.info(f"Placeholder error chart saved to: {file_path}")
                if file_path not in saved_paths: # Asegurar que se añada si no estaba
                    saved_paths.append(file_path)
            except Exception as e_placeholder:
                logger.error(f"CRITICAL: Failed to create placeholder chart for {file_path}: {e_placeholder}")
            finally:
                 if 'error_fig' in locals() and plt.fignum_exists(error_fig.number):
                    plt.close(error_fig) # Asegurar que la figura de error se cierre
        finally:
            if fig is not None and plt.fignum_exists(fig.number):
                plt.close(fig) # Asegurar que la figura principal (original o parcialmente creada) se cierre
    return saved_paths

def plot_volume_vs_price_scatter(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    """
    Genera scatter plots de Volumen vs. Precio.
    Usa nombres de columna internos.
    Devuelve una lista de rutas de los archivos guardados.
    """
    saved_paths = []
    if df_completed.empty:
        logger.info(f"No hay datos completados para graficar volumen vs. precio{title_suffix}.")
        return saved_paths

    # Nombres numéricos generados internamente
    quantity_num_col = 'Quantity_num'
    price_num_col = 'Price_num'
    total_price_num_col = 'TotalPrice_num' 
    # Nombres internos (claves de col_map)
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'
    order_type_col_internal = 'order_type'

    required_cols = [quantity_num_col, price_num_col, total_price_num_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_completed.columns]
        logger.warning(f"Faltan columnas para scatter plot volumen vs. precio ({', '.join(missing)}){title_suffix}.")
        return saved_paths

    for (asset_val, fiat_val), group_data in df_completed.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data.empty or group_data[[quantity_num_col, price_num_col]].isna().all().all():
            continue
        
        size_data = group_data[total_price_num_col].copy()
        sizes_for_plot = pd.Series([30] * len(group_data), index=group_data.index) # Default size
        
        if not size_data.isna().all() and not (size_data == 0).all():
            min_val_sd = size_data.min()
            max_val_sd = size_data.max()
            if pd.notna(min_val_sd) and pd.notna(max_val_sd) and max_val_sd > min_val_sd:
                 sizes_norm = (size_data.fillna(0) - min_val_sd) / (max_val_sd - min_val_sd)
                 sizes_for_plot = sizes_norm * 490 + 10
            elif pd.notna(min_val_sd): # Todos los valores son iguales (min_val_sd) o algunos NaN
                 sizes_for_plot = pd.Series([50] * len(group_data), index=group_data.index)
        
        sizes_for_plot = sizes_for_plot.fillna(30).clip(lower=10, upper=500) # Asegurar que los tamaños estén en un rango razonable

        plt.figure(figsize=(14, 8))
        scatter_plot = sns.scatterplot(
            data=group_data, x=quantity_num_col, y=price_num_col,
            hue=order_type_col_internal,
            size=sizes_for_plot, 
            sizes=(20, 500), 
            alpha=0.7,
            palette="viridis",
            legend="auto"
        )
        plt.title(f"""Volumen vs. Precio para {asset_val}/{fiat_val}{title_suffix}
(Tamaño del punto proporcional al Monto Total Fiat)""")
        plt.xlabel(f'Volumen del Activo ({asset_val})')
        plt.ylabel(f'Precio en {fiat_val}')
        
        handles, labels = scatter_plot.get_legend_handles_labels()
        if handles:
            legend_params = {'title': f'{order_type_col_internal} / Monto'}
            if len(handles) > 5:
                legend_params['loc'] = 'upper left'
                legend_params['bbox_to_anchor'] = (1.05, 1)
            else:
                legend_params['loc'] = 'best'
            scatter_plot.legend(**legend_params)

        plt.grid(True, linestyle='--', alpha=0.7)
        # plt.tight_layout() # Eliminado ya que savefig con bbox_inches='tight' se encarga del ajuste.
        file_path = os.path.join(out_dir, f'volume_vs_price_scatter_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
        try:
            plt.savefig(file_path, bbox_inches='tight')
            logger.info(f"Gráfico de volumen vs. precio ({asset_val}/{fiat_val}) guardado en: {file_path}")
            saved_paths.append(file_path)
            plt.close()
        except Exception as e:
            logger.error(f"Error al guardar el gráfico {file_path}: {e}")
            plt.close()
    return saved_paths

def plot_price_over_time(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    """
    Genera gráficos de línea del Precio a lo largo del tiempo.
    Usa nombres de columna internos.
    Devuelve lista de rutas.
    """
    saved_paths = []
    if df_completed.empty:
        logger.info(f"No hay datos completados para graficar precio sobre tiempo{title_suffix}.")
        return saved_paths

    price_num_col = 'Price_num' # Generada internamente
    match_time_local_col = 'Match_time_local' # Generada internamente
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'
    order_type_col_internal = 'order_type'

    required_cols = [price_num_col, match_time_local_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_completed.columns]
        logger.warning(f"Faltan columnas para graficar precio sobre tiempo ({', '.join(missing)}){title_suffix}.")
        return saved_paths
    
    if not pd.api.types.is_datetime64_any_dtype(df_completed[match_time_local_col]):
        logger.warning(f"Columna '{match_time_local_col}' no es de tipo datetime para graficar precio sobre tiempo{title_suffix}.")
        return saved_paths

    for (asset_val, fiat_val), group_data in df_completed.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data.empty or group_data[price_num_col].isna().all():
            continue
        
        group_data_sorted = group_data.sort_values(by=match_time_local_col)
        plt.figure(figsize=(15, 8))
        
        for order_val, order_group in group_data_sorted.groupby(order_type_col_internal):
            if order_group.empty or order_group[price_num_col].isna().all():
                continue
            plt.plot(order_group[match_time_local_col], order_group[price_num_col], marker='.', linestyle='-', alpha=0.5, label=f'Precio {order_val}')
            if len(order_group) >= 7:
                plt.plot(order_group[match_time_local_col], order_group[price_num_col].rolling(window=7, center=True, min_periods=1).mean(), linestyle='--', label=f'Media Móvil 7P {order_val}')
            if len(order_group) >= 30:
                plt.plot(order_group[match_time_local_col], order_group[price_num_col].rolling(window=30, center=True, min_periods=1).mean(), linestyle=':', label=f'Media Móvil 30P {order_val}')

        plt.title(f'Evolución del Precio para {asset_val}/{fiat_val}{title_suffix}')
        plt.xlabel('Fecha y Hora (Local)')
        plt.ylabel(f'Precio en {fiat_val}')
        plt.xticks(rotation=45, ha='right')
        plt.legend(title='Serie de Precio / Media Móvil')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        file_path = os.path.join(out_dir, f'price_over_time_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
        try:
            plt.savefig(file_path)
            logger.info(f"Gráfico de precio sobre tiempo ({asset_val}/{fiat_val}) guardado en: {file_path}")
            saved_paths.append(file_path)
            plt.close()
        except Exception as e:
            logger.error(f"Error al guardar el gráfico {file_path}: {e}")
            plt.close()
    return saved_paths

def plot_volume_over_time(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    """
    Genera gráficos de línea del Volumen a lo largo del tiempo.
    Usa nombres de columna internos.
    Devuelve lista de rutas.
    """
    saved_paths = []
    if df_completed.empty:
        logger.info(f"No hay datos completados para graficar volumen sobre tiempo{title_suffix}.")
        return saved_paths

    # Nombres numéricos generados internamente en analyze()
    quantity_num_col = 'Quantity_num'
    total_price_num_col = 'TotalPrice_num' 
    # Nombres internos
    match_time_local_col = 'Match_time_local' # Esta se genera internamente
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'

    required_cols_base = [match_time_local_col, asset_type_col_internal, fiat_type_col_internal]
    if not (quantity_num_col in df_completed.columns or total_price_num_col in df_completed.columns):
        logger.warning(f"Faltan columnas de volumen ('{quantity_num_col}' o '{total_price_num_col}') para graficar{title_suffix}.")
        return saved_paths
    if not all(col in df_completed.columns for col in required_cols_base):
        missing = [col for col in required_cols_base if col not in df_completed.columns]
        logger.warning(f"Faltan columnas base para volumen sobre tiempo ({', '.join(missing)}){title_suffix}.")
        return saved_paths
    if not pd.api.types.is_datetime64_any_dtype(df_completed[match_time_local_col]):
        logger.warning(f"Columna '{match_time_local_col}' no es datetime para volumen sobre tiempo{title_suffix}.")
        return saved_paths

    volume_cols_to_plot = {}
    if quantity_num_col in df_completed.columns: volume_cols_to_plot[quantity_num_col] = ('Volumen de Activo', asset_type_col_internal)
    if total_price_num_col in df_completed.columns: volume_cols_to_plot[total_price_num_col] = ('Volumen en Fiat', fiat_type_col_internal)

    for (asset_val, fiat_val), group_data in df_completed.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data.empty:
            continue
        group_data_sorted = group_data.sort_values(by=match_time_local_col)

        for vol_col, (vol_label_base, unit_col_name_from_map) in volume_cols_to_plot.items():
            if group_data_sorted[vol_col].isna().all() or (group_data_sorted[vol_col] == 0).all():
                logger.info(f"No hay datos de '{vol_col}' (>0) para {asset_val}/{fiat_val} en plot_volume_over_time{title_suffix}.")
                continue
            plt.figure(figsize=(15, 8))
            
            # La unidad de la etiqueta será el asset_val o fiat_val según corresponda
            label_unit = asset_val if unit_col_name_from_map == asset_type_col_internal else fiat_val
            plt.plot(group_data_sorted[match_time_local_col], group_data_sorted[vol_col], marker='.', linestyle='-', alpha=0.7, label=f'{vol_label_base} ({label_unit})')
            
            if len(group_data_sorted) >= 7:
                plt.plot(group_data_sorted[match_time_local_col], group_data_sorted[vol_col].rolling(window=7, center=True, min_periods=1).mean(), linestyle='--', label='Media Móvil 7P')
            if len(group_data_sorted) >= 30:
                plt.plot(group_data_sorted[match_time_local_col], group_data_sorted[vol_col].rolling(window=30, center=True, min_periods=1).mean(), linestyle=':', label='Media Móvil 30P')

            y_label = f'{vol_label_base} ({label_unit})'
            plt.title(f'Evolución del {vol_label_base} para {asset_val}/{fiat_val}{title_suffix}')
            plt.xlabel('Fecha y Hora (Local)')
            plt.ylabel(y_label)
            plt.xticks(rotation=45, ha='right')
            plt.legend(title='Serie de Volumen / Media Móvil')
            plt.grid(True, linestyle='--', alpha=0.7)
            plt.tight_layout()
            
            vol_type_suffix = "fiat_value" if vol_col == total_price_num_col else "asset_quantity"
            file_path = os.path.join(out_dir, f'volume_over_time_{vol_type_suffix}_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
            try:
                plt.savefig(file_path)
                logger.info(f"Gráfico de {vol_label_base.lower()} sobre tiempo ({asset_val}/{fiat_val}) guardado en: {file_path}")
                saved_paths.append(file_path)
                plt.close()
            except Exception as e:
                logger.error(f"Error al guardar el gráfico {file_path}: {e}")
                plt.close()
    return saved_paths

def plot_price_vs_payment_method(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    """
    Genera boxplots del Precio vs. Método de Pago.
    Devuelve lista de rutas.
    Usa nombres de columna internos.
    """
    saved_paths = []
    if df_completed.empty:
        logger.info(f"No hay datos completados para graficar precio vs. método de pago{title_suffix}.")
        return saved_paths

    # Nombres de columna internos
    price_num_col = 'Price_num' 
    payment_method_col_internal = 'payment_method' 
    order_type_col_internal = 'order_type'
    fiat_type_col_internal = 'fiat_type'
    asset_type_col_internal = 'asset_type'

    required_cols_in_df = [price_num_col, payment_method_col_internal, order_type_col_internal, fiat_type_col_internal, asset_type_col_internal]
    
    if not all(col in df_completed.columns for col in required_cols_in_df):
        missing = [col for col in required_cols_in_df if col not in df_completed.columns]
        logger.warning(f"Faltan columnas para graficar precio vs. método de pago ({', '.join(missing)}) en df_completed{title_suffix}.")
        return saved_paths

    df_plot_base = df_completed.copy()
    df_plot_base[payment_method_col_internal] = df_plot_base[payment_method_col_internal].fillna('Desconocido')
    
    # Agrupar por Asset y Fiat para generar un gráfico por cada combinación
    for (asset_val, fiat_val), group_data_asset_fiat in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_asset_fiat.empty or group_data_asset_fiat[payment_method_col_internal].nunique() == 0 or group_data_asset_fiat[price_num_col].isna().all():
            logger.info(f"No hay datos o precios válidos para {asset_val}/{fiat_val} en plot_price_vs_payment_method{title_suffix}.")
            continue
        
        payment_methods_count = group_data_asset_fiat[payment_method_col_internal].nunique()
        plot_data_final = group_data_asset_fiat
        effective_pm_count = payment_methods_count

        top_n_methods = 15 
        if payment_methods_count > top_n_methods:
            logger.info(f"Mostrando los {top_n_methods} métodos de pago más frecuentes para {asset_val}/{fiat_val} de {payment_methods_count} totales.")
            main_methods = group_data_asset_fiat[payment_method_col_internal].value_counts().nlargest(top_n_methods).index
            plot_data_final = group_data_asset_fiat[group_data_asset_fiat[payment_method_col_internal].isin(main_methods)]
            effective_pm_count = len(main_methods)

        if plot_data_final.empty: continue

        plt.figure(figsize=(max(12, effective_pm_count * 1.1), 9))
        sns.boxplot(x=payment_method_col_internal, y=price_num_col, hue=order_type_col_internal, data=plot_data_final, palette="Set3")
        plt.title(f'Precio de {asset_val} vs. Método de Pago en {fiat_val}{title_suffix}')
        plt.xlabel('Método de Pago') 
        plt.ylabel(f'Precio de {asset_val} en {fiat_val}')
        plt.xticks(rotation=45, ha='right')
        plt.legend(title=order_type_col_internal) 
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        file_path = os.path.join(out_dir, f'price_vs_payment_method_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
        try:
            plt.savefig(file_path)
            logger.info(f"Gráfico de precio vs. método de pago ({asset_val}/{fiat_val}) guardado en: {file_path}")
            saved_paths.append(file_path)
            plt.close()
        except Exception as e:
            logger.error(f"Error al guardar el gráfico {file_path}: {e}")
            plt.close()
    return saved_paths

def plot_activity_heatmap(df_all_statuses: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None: # col_map eliminado
    """
    Genera un heatmap de la actividad de operaciones y devuelve la ruta del archivo.
    Usa nombres de columna internos directamente.
    """
    if df_all_statuses.empty:
        logger.info(f"No hay datos para generar el heatmap de actividad{title_suffix}.")
        return None

    # Nombres de columna internos directamente
    match_time_local_col = 'Match_time_local' 
    order_number_col_internal = 'order_number' 
    hour_local_col_internal = 'hour_local' 

    required_cols = [match_time_local_col, order_number_col_internal, hour_local_col_internal]
    if not all(col in df_all_statuses.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_all_statuses.columns]
        logger.warning(f"Faltan columnas para el heatmap de actividad ({', '.join(missing)}){title_suffix}.")
        return None
    
    if not pd.api.types.is_datetime64_any_dtype(df_all_statuses[match_time_local_col]):
        logger.warning(f"Columna '{match_time_local_col}' no es datetime para heatmap{title_suffix}.")
        return None

    df_plot = df_all_statuses.copy()
    
    if 'day_of_week' not in df_plot.columns or df_plot['day_of_week'].isna().all():
        if pd.api.types.is_datetime64_any_dtype(df_plot[match_time_local_col]):
            df_plot['day_of_week'] = df_plot[match_time_local_col].dt.day_name()
        else: 
            logger.warning(f"No se pudo generar 'day_of_week' para heatmap, '{match_time_local_col}' no es procesable.")
            return None

    days_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    # Asegurar que la columna exista y no sea todo NaNs antes de convertir a categórica
    if 'day_of_week' in df_plot.columns and not df_plot['day_of_week'].isna().all():
        df_plot['day_of_week'] = pd.Categorical(df_plot['day_of_week'], categories=days_ordered, ordered=True)
    else:
        logger.warning(f"Columna 'day_of_week' ausente o vacía antes de categorizar para heatmap{title_suffix}.")
        return None # No se puede proceder sin días de la semana válidos

    # Chequeo de NaNs en columnas para pivot_table
    cols_for_pivot = [order_number_col_internal, 'day_of_week', hour_local_col_internal]
    if df_plot[cols_for_pivot].isna().any().any():
        logger.warning(f"Datos con NaNs en columnas clave para pivot_table en heatmap. NaNs por columna: {df_plot[cols_for_pivot].isna().sum().to_dict()}. Se intentará eliminar filas con NaNs en estas columnas.")
        df_plot.dropna(subset=cols_for_pivot, inplace=True)
        if df_plot.empty:
            logger.info(f"DataFrame vacío después de quitar NaNs para heatmap{title_suffix}.")
            return None

    activity_matrix = df_plot.pivot_table(
        values=order_number_col_internal, 
        index='day_of_week', 
        columns=hour_local_col_internal, 
        aggfunc='count', 
        fill_value=0,
        observed=False 
    )
    
    for hour in range(24):
        if hour not in activity_matrix.columns:
            activity_matrix[hour] = 0
    activity_matrix = activity_matrix.reindex(columns=sorted(activity_matrix.columns)) 
    activity_matrix = activity_matrix.reindex(index=days_ordered, fill_value=0) # Rellenar días faltantes con 0

    if activity_matrix.empty:
        logger.info(f"Matriz de actividad vacía, no se generará heatmap{title_suffix}.")
        return None

    plt.figure(figsize=(18, 8))
    sns.heatmap(activity_matrix, annot=True, fmt="d", cmap="YlGnBu", linewidths=.5, cbar_kws={'label': 'Cantidad de Operaciones'})
    plt.title(f'Heatmap de Actividad de Operaciones por Hora y Día{title_suffix}')
    plt.xlabel('Hora del Día (Local)')
    plt.ylabel('Día de la Semana')
    plt.xticks(rotation=0) 
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    file_path = os.path.join(out_dir, f'activity_heatmap{file_identifier}.png')
    try:
        plt.savefig(file_path)
        logger.info(f"Heatmap de actividad guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el heatmap de actividad {file_path}: {e}")
        plt.close()
        return None

def plot_fees_analysis(fees_stats_df: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None: # col_map eliminado
    """
    Genera un gráfico de barras para el análisis de comisiones (total_fees_collected por Asset Type).
    Devuelve la ruta del archivo o None.
    """
    if fees_stats_df.empty:
        logger.info(f"No hay datos de comisiones para graficar{title_suffix}.")
        return None

    plot_col = 'total_fees_collected' 
    
    if plot_col not in fees_stats_df.columns:
        logger.warning(f"Columna '{plot_col}' no encontrada en fees_stats_df para graficar{title_suffix}.")
        return None
        
    df_plot = fees_stats_df[[plot_col]].copy() 
    
    # El índice de fees_stats_df es 'asset_type' (nombre interno)
    # Usar el nombre del índice si está disponible y no es el default numérico
    x_label_text = "Tipo de Activo"
    if fees_stats_df.index.name is not None and isinstance(fees_stats_df.index, pd.Index) and fees_stats_df.index.name != 'asset_type':
         # Si el índice tiene un nombre y no es el default que ya usamos internamente
         # Esto es más por si la estructura de fees_stats_df cambiara. Normalmente será 'asset_type'.
         x_label_text = fees_stats_df.index.name.replace('_',' ').title()
    elif fees_stats_df.index.name == 'asset_type':
        x_label_text = "Tipo de Activo" # Específicamente para 'asset_type'

    df_plot = fees_stats_df[[plot_col]].copy() # Seleccionar solo la columna a graficar
    # El índice de fees_stats_df debería ser 'Asset Type'
    if df_plot.index.name is None or df_plot.index.name == '': # Si el índice no tiene nombre, o es anónimo
        df_plot.index.name = "Asset Type" # Darle un nombre para el xlabel

    if df_plot.empty or df_plot[plot_col].sum() == 0:
        logger.info(f"No hay comisiones significativas (>0) en '{plot_col}' para graficar{title_suffix}.")
        return None

    df_plot.sort_values(by=plot_col, ascending=False).plot(kind='bar', figsize=(12, 7), width=0.8, colormap='viridis', legend=None)
    
    plt.title(f'Total de Comisiones Recaudadas por Tipo de Activo{title_suffix}')
    plt.xlabel(df_plot.index.name) # Usar el nombre del índice (debería ser 'Asset Type')
    plt.ylabel('Monto Total de Comisión')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    file_path = os.path.join(out_dir, f'fees_total_by_asset{file_identifier}.png')
    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico de análisis de comisiones por activo guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el gráfico de comisiones {file_path}: {e}")
        plt.close()
        return None

# --- Nueva Función para Guardar Resultados ---
def save_outputs(
    df_to_plot_from: pd.DataFrame, 
    metrics_to_save: dict[str, pd.DataFrame | pd.Series],
    output_label: str, # "total" o el año
    status_subdir: str, # "completadas", "canceladas", o "todas"
    base_output_dir: str, 
    file_name_suffix_from_cli: str, 
    title_suffix_from_cli: str, 
    col_map: dict,
    cli_args: argparse.Namespace, # <--- Añadido para obtener filtros y config de HTML
    config: dict # <--- Añadido para obtener preferencias del reporte HTML
):
    """Guarda tablas de métricas, genera gráficos y un reporte HTML para un subconjunto de datos.\n"""
    
    logger.info(f"\n--- Procesando y guardando resultados para: {output_label.upper()} - {status_subdir.upper()} ---")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_path = os.path.join(script_dir, '..', 'templates') # Asume que templates está al nivel de src/
    if not os.path.exists(templates_path):
        # Fallback si la estructura es diferente (ej. templates en la raíz del proyecto)
        templates_path = os.path.join(os.getcwd(), 'templates') 

    try:
        env = Environment(loader=FileSystemLoader(templates_path), autoescape=True)
        template = env.get_template("report_template.html")
    except Exception as e:
        logger.error(f"Error al cargar la plantilla Jinja2 'report_template.html' desde '{templates_path}': {e}. No se generará el reporte HTML.")
        template = None # Para evitar errores más adelante si la plantilla no se carga

    # Modificación para incluir status_subdir en la ruta
    period_and_status_path = os.path.join(base_output_dir, output_label, status_subdir)
    os.makedirs(period_and_status_path, exist_ok=True) # Asegurar que la carpeta base del status exista

    tables_dir = os.path.join(period_and_status_path, "tables")
    figures_dir = os.path.join(period_and_status_path, "figures")
    reports_dir = os.path.join(period_and_status_path, "reports")
    os.makedirs(tables_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    final_title_suffix = title_suffix_from_cli
    report_main_title = f"Reporte de Operaciones P2P"
    if output_label.lower() != "total":
        final_title_suffix = f"{title_suffix_from_cli} (Año: {output_label} - {status_subdir.capitalize()})"
        report_main_title += f" - Año {output_label} ({status_subdir.capitalize()})"
    else:
        final_title_suffix = f"{title_suffix_from_cli} (Total - {status_subdir.capitalize()})" # Añadido para el caso total
        report_main_title += f" - Consolidado Total ({status_subdir.capitalize()})"
    if title_suffix_from_cli:
        report_main_title += f" {title_suffix_from_cli}"

    logger.info(f"Guardando tablas de métricas para '{output_label}' en: {tables_dir}")
    saved_csv_paths = {}
    for name, table_data in metrics_to_save.items():
        if isinstance(table_data, (pd.DataFrame, pd.Series)):
            if not table_data.empty:
                clean_metric_name = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in name)
                file_path = os.path.join(tables_dir, f"{clean_metric_name}{file_name_suffix_from_cli}.csv")
                try:
                    table_data.to_csv(file_path)
                    logger.info(f"  Tabla '{name}' guardada en: {file_path}")
                    saved_csv_paths[name] = file_path
                except Exception as e:
                    logger.error(f"  Error al guardar la tabla '{name}' en '{file_path}': {e}")
            else:
                logger.info(f"  Tabla '{name}' para '{output_label} - {status_subdir}'{final_title_suffix} está vacía, no se guardará.")
        else:
            logger.warning(f"  El resultado '{name}' para '{output_label} - {status_subdir}' no es un DataFrame o Series, es {type(table_data)}. No se guardará como CSV.")

    logger.info(f"\nGenerando y guardando gráficos para '{output_label} - {status_subdir}' en: {figures_dir}")
    
    # --- Preparar df_completed_for_plots --- 
    # Este df se usa como base para muchos gráficos que requieren transacciones 'Completed'
    df_completed_for_plots = df_to_plot_from.copy()
    status_col = 'status' # Usar directamente el nombre interno esperado
    if status_col in df_to_plot_from.columns:
        # Usar el valor de estado de completado que se usó en analyze() o uno genérico
        # Aquí asumimos 'Completed' como el estado principal para estos gráficos generales.
        # Si se quisiera configurar, se necesitaría pasar ese valor.
        # Esta lógica de filtrado para df_completed_for_plots se mantiene,
        # ya que algunos gráficos específicos (como distribución de precios de ventas)
        # pueden seguir necesitando solo las 'Completed' independientemente del status_subdir.
        # El df_to_plot_from que llega ya está filtrado para el status_subdir si es necesario.
        df_completed_for_plots = df_to_plot_from[df_to_plot_from[status_col] == 'Completed'].copy()
        if df_completed_for_plots.empty:
            logger.warning(f"No hay operaciones 'Completed' en el subset '{output_label} - {status_subdir}' para generar algunos gráficos detallados (df_completed_for_plots está vacío).")
    else:
        logger.warning(f"Columna Status ('{status_col}') no encontrada en '{output_label} - {status_subdir}'. Algunos gráficos pueden no generarse o usar todos los datos.")

    # --- Lista para recolectar información de figuras para el HTML --- 
    figures_for_html = []

    # Función auxiliar para añadir figura al contexto HTML si se generó
    def add_figure_to_html_list(fig_path: str | list[str] | None, title_prefix: str):
        if isinstance(fig_path, str) and os.path.exists(fig_path):
            relative_fig_path = os.path.join('..', 'figures', os.path.basename(fig_path)).replace('\\', '/')
            # Generar un título más descriptivo para figuras individuales
            base_name = os.path.basename(fig_path).replace(file_name_suffix_from_cli, '').replace('.png', '')
            name_parts = [p.capitalize() for p in base_name.split('_') if p not in ['general']]
            descriptive_title = f"{title_prefix} ({' '.join(name_parts)})" if name_parts and not title_prefix.endswith(tuple(name_parts)) else title_prefix
            figures_for_html.append({'title': descriptive_title, 'path': relative_fig_path})
            logger.info(f"Figura '{descriptive_title}' preparada para HTML: {relative_fig_path}")
        elif isinstance(fig_path, list):
            for idx, single_path in enumerate(fig_path):
                if isinstance(single_path, str) and os.path.exists(single_path):
                    relative_single_path = os.path.join('..', 'figures', os.path.basename(single_path)).replace('\\', '/')
                    # Generar título descriptivo también para partes de una lista de figuras
                    base_name = os.path.basename(single_path).replace(file_name_suffix_from_cli, '').replace('.png', '')
                    # Eliminar prefijos comunes de las funciones de ploteo para un título más limpio
                    prefixes_to_remove = [
                        'price_distribution', 'volume_vs_price_scatter', 'price_over_time', 
                        'volume_over_time_asset_quantity', 'volume_over_time_fiat_value', 
                        'price_vs_payment_method', 'monthly_fiat_volume', 'hourly_counts',
                        'buy_sell_distribution', 'order_status_distribution', 'activity_heatmap',
                        'fees_total_by_asset'
                    ]
                    cleaned_name_part = base_name
                    for pfx in prefixes_to_remove:
                        if cleaned_name_part.startswith(pfx + '_'):
                            cleaned_name_part = cleaned_name_part[len(pfx)+1:]
                        elif cleaned_name_part.startswith(pfx):
                             cleaned_name_part = cleaned_name_part[len(pfx):]
                    
                    name_parts = [p.capitalize() for p in cleaned_name_part.split('_') if p and p not in ['general']]
                    specific_addon = ' '.join(name_parts) if name_parts else f"Parte {idx + 1}"
                    specific_title = f"{title_prefix} - {specific_addon}"
                    
                    figures_for_html.append({'title': specific_title, 'path': relative_single_path})
                    logger.info(f"Figura '{specific_title}' preparada para HTML: {relative_single_path}")

    # --- Llamadas a las funciones de ploteo y recolección de rutas --- 
    # logger.info("Generación de gráficos comentada temporalmente para depuración.") # Se descomenta ahora
    if 'hourly_counts' in metrics_to_save and isinstance(metrics_to_save['hourly_counts'], pd.Series) and not metrics_to_save['hourly_counts'].empty:
        path = plot_hourly(metrics_to_save['hourly_counts'], figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(path, "Operaciones por Hora")

    if 'monthly_fiat' in metrics_to_save and isinstance(metrics_to_save['monthly_fiat'], pd.DataFrame) and not metrics_to_save['monthly_fiat'].empty:
        paths = plot_monthly(metrics_to_save['monthly_fiat'], figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(paths, "Volumen Mensual de Fiat")

    # Gráficos de torta para distribuciones (side_counts, status_counts)
    if 'side_counts' in metrics_to_save and isinstance(metrics_to_save['side_counts'], pd.Series) and not metrics_to_save['side_counts'].empty:
        df_pie_side = metrics_to_save['side_counts'].reset_index()
        df_pie_side.columns = ['Tipo de Orden', 'Cantidad'] 
        path = plot_pie(df_pie_side, 'Cantidad', f'Distribución Tipos de Orden', 'buy_sell_distribution', figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(path, "Distribución Tipos de Orden")

    if 'status_counts' in metrics_to_save and isinstance(metrics_to_save['status_counts'], pd.Series) and not metrics_to_save['status_counts'].empty:
        df_pie_status = metrics_to_save['status_counts'].reset_index()
        df_pie_status.columns = ['Estado', 'Cantidad']
        path = plot_pie(df_pie_status, 'Cantidad', f'Distribución Estados de Orden', 'order_status_distribution', figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(path, "Distribución Estados de Orden")

    # Gráficos que usan df_completed_for_plots
    if not df_completed_for_plots.empty:
        paths = plot_price_distribution(df_completed_for_plots, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(paths, "Distribución de Precios")

        paths = plot_volume_vs_price_scatter(df_completed_for_plots, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(paths, "Volumen vs. Precio")
        
        paths = plot_price_over_time(df_completed_for_plots, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(paths, "Evolución del Precio")

        paths = plot_volume_over_time(df_completed_for_plots, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(paths, "Evolución del Volumen")

        paths = plot_price_vs_payment_method(df_completed_for_plots, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(paths, "Precio vs. Método de Pago")
    else:
        logger.info(f"Skipping plots based on completed data for '{output_label} - {status_subdir}' as df_completed_for_plots is empty.")

    # Heatmap de actividad (usa df_to_plot_from, que es el df general para el periodo y status_subdir)
    if not df_to_plot_from.empty:
        path = plot_activity_heatmap(df_to_plot_from, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(path, "Heatmap de Actividad")
    else:
        logger.info(f"Skipping heatmap for '{output_label} - {status_subdir}' as df_to_plot_from is empty.")

    # Análisis de comisiones (usa métrica fees_stats)
    if 'fees_stats' in metrics_to_save and isinstance(metrics_to_save['fees_stats'], pd.DataFrame) and not metrics_to_save['fees_stats'].empty:
        path = plot_fees_analysis(metrics_to_save['fees_stats'], figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli)
        add_figure_to_html_list(path, "Análisis de Comisiones")

    # --- Preparación del Contexto para el Reporte HTML --- 
    if template: # Solo proceder si la plantilla se cargó
        logger.info(f"Preparando datos para el reporte HTML de '{output_label} - {status_subdir}'...")
        html_context = {
            'title': report_main_title,
            'generation_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (UTC" + datetime.datetime.now(datetime.timezone.utc).astimezone().strftime('%z') + ")",
            'applied_filters': {},
            'sales_summary_data': {},
            'included_tables': [],
            'included_figures': figures_for_html # Usar las figuras recolectadas (estará vacío si se comenta arriba)
        }

        # 1. Filtros Aplicados
        if cli_args.fiat_filter: html_context['applied_filters']['Monedas Fiat'] = cli_args.fiat_filter
        if cli_args.asset_filter: html_context['applied_filters']['Activos'] = cli_args.asset_filter
        if cli_args.status_filter: html_context['applied_filters']['Estados'] = cli_args.status_filter
        if cli_args.payment_method_filter: html_context['applied_filters']['Métodos de Pago'] = cli_args.payment_method_filter
        if output_label.lower() != "total": 
            html_context['applied_filters']['Periodo'] = f"Año {output_label}"
        html_context['applied_filters']['Categoría de Estado'] = status_subdir.capitalize()

        # 2. Resumen de Ventas
        sales_summary_df_key = 'sales_summary_all_assets_fiat_detailed'
        if sales_summary_df_key in metrics_to_save and isinstance(metrics_to_save[sales_summary_df_key], pd.DataFrame) and not metrics_to_save[sales_summary_df_key].empty:
            html_context['sales_summary_data']['sales_summary_all_assets_fiat_detailed'] = True
            html_context['sales_summary_data']['sales_summary_all_assets_fiat_detailed_html'] = metrics_to_save[sales_summary_df_key].to_html(classes='table table-striped table-hover', border=0, index=False)
        
        # 3. Tablas Incluidas
        html_report_prefs = config.get('html_report', {})
        tables_to_include_keys = html_report_prefs.get('include_tables_default', ['asset_stats', 'fiat_stats'])
        
        for table_key in tables_to_include_keys:
            if table_key in metrics_to_save and isinstance(metrics_to_save[table_key], (pd.DataFrame, pd.Series)) and not metrics_to_save[table_key].empty:
                table_df = metrics_to_save[table_key]
                if isinstance(table_df, pd.Series):
                    table_df = table_df.to_frame()
                html_context['included_tables'].append({
                    'title': table_key.replace('_', ' ').title(),
                    'html': table_df.to_html(classes='table table-striped table-hover', border=0, index=isinstance(table_df.index, pd.MultiIndex) or table_df.index.name is not None)
                })
        
        # 4. Figuras Incluidas (ya asignado a html_context['included_figures'])
        # La lógica de filtrado basada en config['html_report']['include_figures_default'] se omite por ahora
        # ya que estamos incluyendo todas las generadas (o ninguna si están comentadas).

        # logger.info("Generación de HTML comentada temporalmente para depuración.") # Se descomenta ahora
        try:
            html_output = template.render(html_context)
            report_filename = f"p2p_sales_report{file_name_suffix_from_cli}.html"
            report_path = os.path.join(reports_dir, report_filename)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_output)
            logger.info(f"Reporte HTML guardado en: {report_path}")
        except Exception as e:
            logger.error(f"Error al renderizar o guardar el reporte HTML: {e}")

    logger.info(f"--- Fin de procesamiento para: {output_label.upper()} - {status_subdir.upper()} ---")

# --- Lógica Principal (CLI) ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analiza un CSV de operaciones P2P, genera tablas de métricas y gráficos, opcionalmente por año.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=textwrap.dedent("""
        Ejemplos de uso:
        ----------------
        1. Análisis general y por año (salida en output/total/, output/YYYY/tables/, output/YYYY/figures/):
           python src/analisis_profesional_p2p.py --csv data/p2p.csv

        2. Solo análisis total (sin desglose anual):
           python src/analisis_profesional_p2p.py --csv data/p2p.csv --no_annual_breakdown
        """)
    )
    parser.add_argument(
        '--csv', 
        required=True, 
        help='Ruta al archivo CSV de operaciones P2P. (Ej: data/p2p.csv)'
    )
    parser.add_argument(
        '--config', 
        help='Ruta al archivo de configuración YAML. (Opcional, ej: config.yaml)'
    )
    parser.add_argument(
        '--out', 
        default='output', 
        help='Carpeta base para guardar los resultados. (Default: output)'
    )
    parser.add_argument('--fiat_filter', nargs='*', help='Filtrar por una o más monedas Fiat (ej. UYU USD).')
    parser.add_argument('--asset_filter', nargs='*', help='Filtrar por uno o más tipos de Activos (ej. USDT BTC).')
    parser.add_argument('--status_filter', nargs='*', default=None, help='Filtrar por uno o más Estados de orden (ej. Completed Cancelled). Si no se especifica, se procesan todos los estados relevantes para las categorías todas/completadas/canceladas.')
    parser.add_argument('--payment_method_filter', nargs='*', help='Filtrar por uno o más Métodos de Pago.')
    parser.add_argument('--no_annual_breakdown', action='store_true', help='Si se establece, no se generan resultados desglosados por año.')

    args = parser.parse_args()

    # Cargar configuración
    config = load_config(args.config)
    logger.debug(f"Configuración en uso: {config}")

    # Obtener mapeo de columnas y definición de venta desde la config
    col_map = config.get('column_mapping', DEFAULT_CONFIG['column_mapping'])
    sell_config = config.get('sell_operation', DEFAULT_CONFIG['sell_operation'])

    # --- Generación de Sufijos para Nombres de Archivo y Títulos (basado en filtros CLI) ---
    file_suffix_parts_cli = []
    title_suffix_parts_cli = [] 
    if args.fiat_filter:
        processed_fiats = [f.strip().upper() for f in args.fiat_filter]
        file_suffix_parts_cli.append(f"fiat_({'_'.join(processed_fiats)})")
        title_suffix_parts_cli.append(f"Fiat {', '.join(processed_fiats)}")
    if args.asset_filter:
        processed_assets = [a.strip().upper() for a in args.asset_filter]
        file_suffix_parts_cli.append(f"asset_({'_'.join(processed_assets)})")
        title_suffix_parts_cli.append(f"Asset {', '.join(processed_assets)}")
    # Solo añadir filtro de estado al sufijo si el usuario lo especificó explícitamente
    if args.status_filter: # Ya no hay default ['Completed'], así que esto es si el usuario lo pone
        processed_status = [s.strip().capitalize() for s in args.status_filter]
        file_suffix_parts_cli.append(f"status_({'_'.join(processed_status)})")
        title_suffix_parts_cli.append(f"Status {', '.join(processed_status)}")
    if args.payment_method_filter:
        safe_payment_methods = [pm.strip().replace(' ', '_') for pm in args.payment_method_filter]
        file_suffix_parts_cli.append(f"payment_({'_'.join(safe_payment_methods)})")
        title_suffix_parts_cli.append(f"Payment {', '.join(args.payment_method_filter)}")

    if file_suffix_parts_cli:
        base_filename_suffix_cli = "_" + "_".join(file_suffix_parts_cli)
        analysis_title_suffix_cli = " (" + "; ".join(title_suffix_parts_cli) + ")"
    else:
        # Si no hay filtros CLI, el sufijo es general
        base_filename_suffix_cli = "_general"
        analysis_title_suffix_cli = " (General)"
    
    clean_filename_suffix_cli = base_filename_suffix_cli.replace("(", "").replace(")", "").replace(",", "").replace(";", "").replace(":", "").lower()

    # --- Carga y Filtrado Inicial de Datos (según CLI) ---
    logger.info(f"Cargando datos desde: {args.csv}")
    try:
        # Usar col_map['order_number'] y col_map['adv_order_number'] (si existiera) para dtype_spec
        # Por ahora, asumimos que 'Order Number' es el nombre clave para str, si el mapeo lo cambia, esto necesitará ajuste
        # o una forma más genérica de especificar dtypes via config.
        raw_col_order_number = col_map.get('order_number', "Order Number")
        # raw_col_adv_order_number = col_map.get('adv_order_number', "Advertisement Order Number") # Ejemplo si tuvieras esta columna
        dtype_spec = {raw_col_order_number: str}
        # dtype_spec[raw_col_adv_order_number] = str # Ejemplo
        
        df_raw = pd.read_csv(args.csv, dtype=dtype_spec) # Dtype spec se aplica a columnas originales
        logger.info(f"Datos cargados: {len(df_raw)} filas desde CSV.")

        # Renombrar columnas según el mapeo ANTES de cualquier otro procesamiento
        # Crear un diccionario de renombrado solo con las columnas presentes en df_raw
        rename_dict = {csv_col_name: script_col_name 
                       for script_col_name, csv_col_name in col_map.items() 
                       if csv_col_name in df_raw.columns and csv_col_name != script_col_name}
        if rename_dict:
            df_raw.rename(columns=rename_dict, inplace=True)
            logger.info(f"Columnas renombradas según config: {rename_dict}")
        
        # Ahora df_raw tiene los nombres de columna internos del script (las claves de col_map)

    except FileNotFoundError:
        logger.error(f"Error: El archivo CSV no se encontró en la ruta especificada: {args.csv}")
        exit(1)
    except Exception as e:
        logger.error(f"Error al leer o procesar inicialmente el archivo CSV: {e}")
        exit(1)
    
    # --- Filtrado basado en nombres de columna INTERNOS del script ---
    df_cli_filtered = df_raw.copy()
    # Ahora los filtros usan los nombres de columna INTERNOS (claves de col_map)
    # por ejemplo, en lugar de 'Fiat Type', usar col_map['fiat_type'] si se quiere ser robusto
    # pero como ya renombramos, podemos usar directamente las claves de col_map como nombres de columna.

    # Ejemplo de cómo se haría el filtrado usando los nombres internos del script (claves de col_map)
    # if args.fiat_filter and 'fiat_type' in df_cli_filtered.columns: # 'fiat_type' es la clave interna
    #     df_cli_filtered = df_cli_filtered[df_cli_filtered['fiat_type'].str.upper().str.strip().isin(processed_fiats)]
    #     logger.info(f"Filtrado CLI por Fiat Type: {processed_fiats}. Filas restantes: {len(df_cli_filtered)}")
    # Esta sección necesita ser adaptada para usar los nombres de columna INTERNOS DEL SCRIPT (las claves de col_map)
    # después del renombrado.

    # CORRECCIÓN: El filtrado debe usar los nombres de columna INTERNOS (las claves de col_map)
    # ya que df_raw (y por ende df_cli_filtered) ha sido renombrado.

    if args.fiat_filter and 'fiat_type' in df_cli_filtered.columns:
        df_cli_filtered = df_cli_filtered[df_cli_filtered['fiat_type'].str.upper().str.strip().isin(processed_fiats)]
        logger.info(f"Filtrado CLI por Fiat: {processed_fiats}. Filas restantes: {len(df_cli_filtered)}")
    if args.asset_filter and 'asset_type' in df_cli_filtered.columns:
        df_cli_filtered = df_cli_filtered[df_cli_filtered['asset_type'].str.upper().str.strip().isin(processed_assets)]
        logger.info(f"Filtrado CLI por Asset: {processed_assets}. Filas restantes: {len(df_cli_filtered)}")
    if args.status_filter and 'status' in df_cli_filtered.columns:
        processed_status_cli = [s.strip().capitalize() for s in args.status_filter]
        df_cli_filtered = df_cli_filtered[df_cli_filtered['status'].str.capitalize().str.strip().isin(processed_status_cli)]
        logger.info(f"Filtrado CLI explícito por Status: {processed_status_cli}. Filas restantes: {len(df_cli_filtered)}")
    if args.payment_method_filter and 'payment_method' in df_cli_filtered.columns:
        df_cli_filtered = df_cli_filtered[df_cli_filtered['payment_method'].isin(args.payment_method_filter)]
        logger.info(f"Filtrado CLI por Payment Method: {args.payment_method_filter}. Filas restantes: {len(df_cli_filtered)}")

    if df_cli_filtered.empty:
        print(f"El DataFrame está vacío después de aplicar los filtros CLI. No se generarán resultados.")
        exit(0)

    # --- Procesamiento y Análisis Principal ---
    # 1. Ejecutar 'analyze' una vez sobre el df filtrado por CLI para obtener todas las columnas procesadas (ej. 'Year')
    # Este df_master_processed será la base para los desgloses por estado y año.
    logger.info("\n=== Pre-procesando DataFrame base con todos los filtros CLI aplicados ===")
    df_master_processed, _ = analyze(df_cli_filtered.copy(), col_map, sell_config) # Las métricas aquí no se usan directamente para guardar por estado

    if df_master_processed.empty:
        print("El DataFrame está vacío después del pre-procesamiento inicial (función analyze). No se generarán resultados.")
        exit(0)

    # Definir la columna de estado interna
    status_col_internal = 'status' # Asumiendo que el renombrado de columnas ya ocurrió y 'status' es el nombre interno

    # Lista de categorías de estado para iterar
    status_categories = ["todas", "completadas", "canceladas"]

    # --- Análisis por Período (Total y Anual) y por Categoría de Estado ---
    
    periods_to_process = {"total": df_master_processed.copy()}
    
    if not args.no_annual_breakdown:
        if 'Year' in df_master_processed.columns and not df_master_processed['Year'].isna().all():
            unique_years = sorted(df_master_processed['Year'].dropna().unique().astype(int))
            logger.info(f"\n=== Años identificados para desglose: {unique_years} ===")
            for year_val in unique_years:
                df_year_subset = df_master_processed[df_master_processed['Year'] == year_val].copy()
                if not df_year_subset.empty:
                    periods_to_process[str(year_val)] = df_year_subset
                else:
                    logger.info(f"No hay datos para el año {year_val} en el df_master_processed. Se omite para este año.")
        else:
            logger.warning("La columna 'Year' no está disponible o está vacía en el DataFrame pre-procesado. No se realizará el desglose anual.")

    for period_label, df_period_base in periods_to_process.items():
        logger.info(f"\n=== Iniciando Análisis para el PERÍODO: {period_label.upper()} ===")
        
        for status_category in status_categories:
            logger.info(f"--- Procesando categoría de estado: {status_category.upper()} para el período: {period_label.upper()} ---")
            
            df_subset_for_status = pd.DataFrame() # Inicializar df vacío

            if status_category == "todas":
                df_subset_for_status = df_period_base.copy()
            elif status_category == "completadas":
                if status_col_internal in df_period_base.columns:
                    df_subset_for_status = df_period_base[df_period_base[status_col_internal] == 'Completed'].copy()
                else:
                    logger.warning(f"Columna '{status_col_internal}' no encontrada para filtrar por 'Completadas' en período {period_label}. Omitiendo.")
                    continue
            elif status_category == "canceladas":
                if status_col_internal in df_period_base.columns:
                    df_subset_for_status = df_period_base[df_period_base[status_col_internal] != 'Completed'].copy()
                else:
                    logger.warning(f"Columna '{status_col_internal}' no encontrada para filtrar por 'Canceladas' en período {period_label}. Omitiendo.")
                    continue
            
            if df_subset_for_status.empty:
                logger.info(f"No hay datos para la categoría '{status_category}' en el período '{period_label}'. Se omite esta combinación.")
                continue

            logger.info(f"Analizando {len(df_subset_for_status)} filas para {period_label.upper()} - {status_category.upper()}")
            # El df_subset_for_status ya tiene las columnas procesadas de df_master_processed,
            # pero es mejor volver a llamar a analyze para que las métricas se calculen correctamente
            # sobre el subconjunto específico (ej. status_counts, etc.).
            # Si `analyze` es idempotente y no modifica el df innecesariamente, esto es seguro.
            # La función `analyze` ha sido diseñada para ser más idempotente, así que debería estar bien.
            processed_df_for_save, current_metrics = analyze(df_subset_for_status.copy(), col_map, sell_config)
            
            save_outputs(
                df_to_plot_from=processed_df_for_save, # Usar el df procesado específico para este status y período
                metrics_to_save=current_metrics, 
                output_label=period_label, 
                status_subdir=status_category,
                base_output_dir=args.out, 
                file_name_suffix_from_cli=clean_filename_suffix_cli, 
                title_suffix_from_cli=analysis_title_suffix_cli, 
                col_map=col_map, 
                cli_args=args, 
                config=config
            )

    print(f"\n\u2705 Todos los análisis completados. Resultados generales en: {os.path.abspath(args.out)}")
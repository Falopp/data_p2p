import polars as pl
import logging
from .utils import parse_amount # Importar parse_amount de utils
from . import finance_utils # Usar import relativo si está en el mismo paquete src
import numpy as np # Añadir numpy para FFT
# DONE: 1.6 Importar IsolationForest
from sklearn.ensemble import IsolationForest
# DONE: 3.2 Importar datetime y timedelta
from datetime import datetime, timedelta, timezone 

logger = logging.getLogger(__name__)

def analyze(df: pl.DataFrame, col_map: dict, sell_config: dict, cli_args: dict | None = None) -> tuple[pl.DataFrame, dict[str, pl.DataFrame | pl.Series]]:
    logger.info("Iniciando análisis con Polars...")
    df_processed = df.clone()

    order_type_col = 'order_type'
    asset_type_col = 'asset_type'
    fiat_type_col = 'fiat_type'
    total_price_col = 'total_price'
    price_col = 'price'
    quantity_col = 'quantity'
    status_col = 'status'
    match_time_utc_col = 'match_time_utc'
    maker_fee_col = 'maker_fee'
    taker_fee_col = 'taker_fee'
    order_number_col = 'order_number'
    payment_method_col = 'payment_method'

    logger.info("Iniciando transformación de columnas numéricas con Polars...")
    cols_to_process_numeric = {
        quantity_col: 'Quantity_num',
        maker_fee_col: 'MakerFee_num',
        taker_fee_col: 'TakerFee_num',
        price_col: 'Price_num',
        total_price_col: 'TotalPrice_num'
    }

    processed_numerics = []
    warnings_numerics = []

    for original_col_internal_name, new_num_col in cols_to_process_numeric.items():
        if new_num_col not in df_processed.columns:
            if original_col_internal_name in df_processed.columns:
                df_processed = df_processed.with_columns(
                    pl.col(original_col_internal_name).map_elements(parse_amount, return_dtype=pl.Float64).alias(new_num_col)
                )
                processed_numerics.append(f"{original_col_internal_name} -> {new_num_col}")
            else:
                logger.warning(f"Columna original mapeada a '{original_col_internal_name}' no encontrada para crear '{new_num_col}'. Se creará '{new_num_col}' con nulos.")
                df_processed = df_processed.with_columns(pl.lit(None, dtype=pl.Float64).alias(new_num_col))
                warnings_numerics.append(f"'{original_col_internal_name}' no encontrada, '{new_num_col}' creada con nulos.")
        else:
            processed_numerics.append(f"{new_num_col} (existente)")

    if processed_numerics:
        logger.info(f"Columnas numéricas procesadas/verificadas: {'; '.join(processed_numerics)}.")
    if warnings_numerics:
        for warning_msg in warnings_numerics:
            logger.warning(warning_msg)
    logger.info("Transformación de columnas numéricas completada.")

    # --- INICIO: Parche para corregir Price_num en USDT/USD BUY ---
    if (asset_type_col in df_processed.columns and
        fiat_type_col in df_processed.columns and
        order_type_col in df_processed.columns and
        'Price_num' in df_processed.columns):

        price_correction_condition = (
            (pl.col(asset_type_col) == "USDT") &
            (pl.col(fiat_type_col) == "USD") &
            (pl.col(order_type_col) == "BUY") &
            (pl.col('Price_num').is_not_null()) &
            (pl.col('Price_num') > 10) # Umbral para precios probablemente mal interpretados
        )

        # Contar cuántas filas se van a afectar antes de la corrección
        rows_to_correct_count = df_processed.filter(price_correction_condition).height
        if rows_to_correct_count > 0:
            logger.info(f"Detectadas {rows_to_correct_count} filas de USDT/USD BUY con Price_num > 10. Se intentará corregir dividiendo por 1000.")
            
            df_processed = df_processed.with_columns(
                pl.when(price_correction_condition)
                .then(pl.col('Price_num') / 1000)
                .otherwise(pl.col('Price_num'))
                .alias('Price_num') # Sobrescribe la columna Price_num
            )
            logger.info(f"Corrección de Price_num para USDT/USD BUY aplicada.")
        else:
            logger.info("No se encontraron filas USDT/USD BUY que necesiten corrección de Price_num (Price_num > 10).")
    else:
        logger.info("No se aplicó el parche de corrección de Price_num para USDT/USD BUY porque faltan una o más columnas requeridas (asset_type, fiat_type, order_type, Price_num).")
    # --- FIN: Parche para corregir Price_num en USDT/USD BUY ---

    if 'MakerFee_num' not in df_processed.columns:
        df_processed = df_processed.with_columns(pl.lit(0.0, dtype=pl.Float64).alias('MakerFee_num'))
    if 'TakerFee_num' not in df_processed.columns:
        df_processed = df_processed.with_columns(pl.lit(0.0, dtype=pl.Float64).alias('TakerFee_num'))
    
    df_processed = df_processed.with_columns(
        (pl.col('MakerFee_num').fill_null(0.0) + pl.col('TakerFee_num').fill_null(0.0)).alias('TotalFee')
    )

    logger.info("Iniciando procesamiento de columnas de tiempo con Polars...")
    time_cols_created_or_verified = []
    
    if 'Match_time_local' not in df_processed.columns or not isinstance(df_processed.schema['Match_time_local'], pl.Datetime):
        if match_time_utc_col in df_processed.columns:
            logger.info(f"Generando columnas de tiempo a partir de '{match_time_utc_col}'.")
            
            df_processed = df_processed.with_columns([
                pl.col(match_time_utc_col).str.to_datetime(time_unit='us').alias('Match_time_utc_dt_naive')
            ])

            df_processed = df_processed.with_columns([
                pl.col('Match_time_utc_dt_naive').dt.replace_time_zone("UTC").alias('Match_time_utc_dt')
            ])

            uy_tz = 'America/Montevideo'
            df_processed = df_processed.with_columns([
                pl.col('Match_time_utc_dt').dt.convert_time_zone(uy_tz).alias('Match_time_local')
            ])

            df_processed = df_processed.with_columns([
                pl.col('Match_time_local').dt.hour().alias('hour_local'),
                pl.col('Match_time_local').dt.strftime('%Y-%m').alias('YearMonthStr'), 
                pl.col('Match_time_local').dt.year().alias('Year')
            ]).drop('Match_time_utc_dt_naive')
            
            initial_rows = df_processed.height
            df_processed = df_processed.drop_nulls(subset=['Match_time_utc_dt']) 
            rows_dropped = initial_rows - df_processed.height
            if rows_dropped > 0:
                logger.info(f"Filas eliminadas debido a valores nulos/inválidos en 'Match_time_utc_dt': {rows_dropped}")

            if df_processed.height > 0 and isinstance(df_processed.schema['Match_time_utc_dt'], pl.Datetime):
                time_cols_created_or_verified.extend(['Match_time_utc_dt', 'Match_time_local', 'hour_local', 'YearMonthStr', 'Year'])
            else:
                logger.warning(f"'{match_time_utc_col}' no pudo ser convertida a datetime válida o resultó en DataFrame vacío. Columnas de tiempo no creadas/actualizadas.")
        else:
            logger.warning(f"Columna de tiempo original mapeada a '{match_time_utc_col}' no encontrada. Columnas de tiempo no creadas.")
            df_processed = df_processed.with_columns([
                pl.lit(None, dtype=pl.Datetime(time_unit='us', time_zone=None)).alias('Match_time_local'),
                pl.lit(None, dtype=pl.Int64).alias('hour_local'),
                pl.lit(None, dtype=pl.String).alias('YearMonthStr'),
                pl.lit(None, dtype=pl.Int64).alias('Year')
            ])
    elif 'Match_time_local' in df_processed.columns and isinstance(df_processed.schema['Match_time_local'], pl.Datetime):
        logger.info("Columnas de tiempo base (Match_time_local, hour_local, YearMonthStr, Year) ya existen o se crearán si faltan.")
        if 'hour_local' not in df_processed.columns: 
            df_processed = df_processed.with_columns(pl.col('Match_time_local').dt.hour().alias('hour_local'))
            time_cols_created_or_verified.append('hour_local (derivada)')
        else: 
            time_cols_created_or_verified.append('hour_local (existente)')
            
        if 'YearMonthStr' not in df_processed.columns: 
            df_processed = df_processed.with_columns(pl.col('Match_time_local').dt.strftime('%Y-%m').alias('YearMonthStr'))
            time_cols_created_or_verified.append('YearMonthStr (derivada)')
        else:
            time_cols_created_or_verified.append('YearMonthStr (existente)')

        if 'Year' not in df_processed.columns: 
            df_processed = df_processed.with_columns(pl.col('Match_time_local').dt.year().alias('Year'))
            time_cols_created_or_verified.append('Year (derivada)')
        else:
            time_cols_created_or_verified.append('Year (existente)')
    else: 
        logger.warning(f"'Match_time_local' existe pero no es Datetime. Forzando columnas de tiempo relacionadas a nulos.")
        df_processed = df_processed.with_columns([
                pl.lit(None, dtype=pl.Datetime(time_unit='us', time_zone=None)).alias('Match_time_local'),
                pl.lit(None, dtype=pl.Int64).alias('hour_local'),
                pl.lit(None, dtype=pl.String).alias('YearMonthStr'),
                pl.lit(None, dtype=pl.Int64).alias('Year')
            ])

    if time_cols_created_or_verified:
        logger.info(f"Columnas de tiempo procesadas/verificadas: {'; '.join(time_cols_created_or_verified)}.")
    logger.info("Procesamiento de columnas de tiempo completado.")

    metrics: dict[str, pl.DataFrame | pl.Series] = {}
    logger.info("Calculando métricas con Polars...")

    df_completed_for_sales_summary = pl.DataFrame() 
    if status_col in df_processed.columns:
        df_completed_for_sales_summary = df_processed.filter(pl.col(status_col) == 'Completed').clone()
        if df_completed_for_sales_summary.is_empty():
            logger.info("No hay operaciones 'Completed' para resumen de ventas.")
    else:
        logger.warning(f"Columna '{status_col}' no encontrada para resumen de ventas.")

    required_financial_cols_internal = [order_number_col, 'Quantity_num', 'TotalPrice_num', 'TotalFee', 'Price_num', asset_type_col, fiat_type_col]
    missing_cols_check = [col for col in required_financial_cols_internal if col not in df_processed.columns]

    if missing_cols_check:
        logger.warning(f"Faltan columnas para métricas financieras: {missing_cols_check}. Algunas métricas estarán vacías.")
        metrics['asset_stats'] = pl.DataFrame()
        metrics['fiat_stats'] = pl.DataFrame()
        metrics['price_stats'] = pl.DataFrame()
        metrics['fees_stats'] = pl.DataFrame()
        metrics['monthly_fiat'] = pl.DataFrame()
    else:
        logger.info("Calculando asset_stats...")
        metrics['asset_stats'] = (df_processed.group_by([asset_type_col, order_type_col])
                                    .agg([
                                        pl.col(order_number_col).count().alias('operations'),
                                        pl.col('Quantity_num').sum().alias('quantity'),
                                        pl.col('TotalPrice_num').sum().alias('total_fiat'),
                                        pl.col('TotalFee').sum().alias('total_fees')
                                    ])
                                    .sort('total_fiat', descending=True))

        logger.info("Calculando fiat_stats...")
        metrics['fiat_stats']  = (df_processed.group_by([fiat_type_col, order_type_col])
                                    .agg([
                                        pl.col(order_number_col).count().alias('operations'),
                                        pl.col('TotalPrice_num').sum().alias('total_fiat'),
                                        pl.col('Price_num').mean().alias('avg_price'),
                                        pl.col('TotalFee').sum().alias('total_fees')
                                    ])
                                    .sort('total_fiat', descending=True))

        logger.info("Calculando price_stats...")
        if not df_processed.is_empty() and fiat_type_col in df_processed.columns and 'Price_num' in df_processed.columns:
            metrics['price_stats'] = (df_processed.group_by(fiat_type_col)
                                      .agg([
                                          pl.col('Price_num').mean().alias('avg_price'),
                                          pl.col('Price_num').median().alias('median_price'),
                                          pl.col('Price_num').min().alias('min_price'),
                                          pl.col('Price_num').max().alias('max_price'),
                                          pl.col('Price_num').std().alias('std_price'),
                                          pl.col('Price_num').quantile(0.25).alias('q1_price'),
                                          pl.col('Price_num').quantile(0.75).alias('q3_price'),
                                          (pl.col('Price_num').quantile(0.75) - pl.col('Price_num').quantile(0.25)).alias('iqr_price'),
                                          pl.col('Price_num').quantile(0.01).alias('p1_price'),
                                          pl.col('Price_num').quantile(0.99).alias('p99_price')
                                      ]))
        else:
            logger.warning(f"No se pueden calcular price_stats. DataFrame vacío o faltan columnas.")
            metrics['price_stats'] = pl.DataFrame()

        logger.info("Calculando fees_stats...")
        if not df_processed.is_empty() and asset_type_col in df_processed.columns and 'TotalFee' in df_processed.columns:
             metrics['fees_stats'] = (df_processed.group_by(asset_type_col)
                                     .agg([
                                         pl.col('TotalFee').sum().alias('total_fees_collected'),
                                         pl.col('TotalFee').mean().alias('avg_fee_per_op'),
                                         pl.col('TotalFee').filter(pl.col('TotalFee') > 0).count().alias('num_ops_with_fees'), 
                                         pl.col('TotalFee').max().alias('max_fee')
                                     ])
                                     .sort('total_fees_collected', descending=True))
        else:
            logger.warning(f"No se pueden calcular fees_stats. DataFrame vacío o faltan columnas.")
            metrics['fees_stats'] = pl.DataFrame()

        logger.info("Calculando monthly_fiat...")
        if not df_processed.is_empty() and 'YearMonthStr' in df_processed.columns and \
           fiat_type_col in df_processed.columns and 'TotalPrice_num' in df_processed.columns and \
           order_type_col in df_processed.columns:
            
            monthly_summary = (df_processed.group_by(['YearMonthStr', fiat_type_col, order_type_col])
                                .agg(pl.sum('TotalPrice_num').alias('sum_total_price'))
                                .sort(['YearMonthStr', fiat_type_col, order_type_col]))
            
            try:
                metrics['monthly_fiat'] = monthly_summary.pivot(
                    values='sum_total_price',
                    index=['YearMonthStr', fiat_type_col],
                    on=order_type_col,  
                    aggregate_function=None 
                ).fill_null(0) 
            except Exception as e: 
                logger.error(f"Error al pivotar monthly_fiat: {e}. La tabla podría estar en formato largo.")
                metrics['monthly_fiat'] = monthly_summary 
        else:
            logger.warning(f"No se pueden calcular monthly_fiat. DataFrame vacío o faltan columnas.")
            metrics['monthly_fiat'] = pl.DataFrame()

    if status_col in df_processed.columns:
        metrics['status_counts'] = df_processed[status_col].value_counts() 
    else:
        metrics['status_counts'] = pl.Series(dtype=pl.datatypes.UInt32).to_frame() 

    if order_type_col in df_processed.columns:
        metrics['side_counts'] = df_processed[order_type_col].value_counts()
    else:
        metrics['side_counts'] = pl.Series(dtype=pl.datatypes.UInt32).to_frame()

    # DONE: 1. VWAP diario
    logger.info("Calculando VWAP diario...")
    if not df_processed.is_empty() and \
       'Match_time_local' in df_processed.columns and \
       'Price_num' in df_processed.columns and \
       'Quantity_num' in df_processed.columns and \
       df_processed['Match_time_local'].null_count() == 0 and \
       df_processed['Price_num'].null_count() == 0 and \
       df_processed['Quantity_num'].null_count() == 0:
        
        df_vwap = df_processed.group_by(pl.col('Match_time_local').dt.date().alias('date')) \
                              .agg(
                                  (pl.col('Price_num') * pl.col('Quantity_num')).sum().alias('total_price_volume'),
                                  pl.col('Quantity_num').sum().alias('total_volume')
                              ) \
                              .filter(pl.col('total_volume') != 0) \
                              .with_columns(
                                  (pl.col('total_price_volume') / pl.col('total_volume')).alias('vwap')
                              ) \
                              .select(['date', 'vwap', 'total_volume']) \
                              .sort('date')
        
        metrics['vwap_daily'] = df_vwap
        logger.info("VWAP diario calculado y añadido a las métricas.")
    else:
        logger.warning("No se puede calcular VWAP diario. Faltan columnas requeridas (Match_time_local, Price_num, Quantity_num) o contienen nulos.")
        metrics['vwap_daily'] = pl.DataFrame()

    # DONE: 1.2 High / Low intradía
    logger.info("Calculando High/Low intradía...")
    if not df_processed.is_empty() and \
       'Match_time_local' in df_processed.columns and \
       'Price_num' in df_processed.columns and \
       df_processed['Match_time_local'].dtype == pl.Datetime(time_unit='us', time_zone='America/Montevideo') and \
       df_processed['Price_num'].null_count() == 0:

        # DONE: Asegurar que el DataFrame esté ordenado por la columna de índice dinámico
        df_processed_sorted_for_dynamic = df_processed.sort("Match_time_local")

        df_intraday_hl = df_processed_sorted_for_dynamic.group_by_dynamic(
            index_column="Match_time_local",
            every="1d",
            by='asset_type', # Agrupamos también por asset_type para tener High/Low por cada activo
            closed='left'
        ).agg([
            pl.col('Price_num').max().alias('high_price'),
            pl.col('Price_num').min().alias('low_price'),
            pl.col('Price_num').mean().alias('avg_price_day'), # Añadimos precio promedio diario como extra
            pl.count().alias('trades_count_day')
        ]).sort("Match_time_local")

        metrics['intraday_high_low'] = df_intraday_hl
        logger.info("High/Low intradía calculado y añadido a las métricas.")
    else:
        logger.warning("No se puede calcular High/Low intradía. Faltan columnas (Match_time_local, Price_num) o Match_time_local no es Datetime con timezone o Price_num tiene nulos.")
        metrics['intraday_high_low'] = pl.DataFrame()

    # DONE: 1.3 Time-Between-Trades (TBT)
    logger.info("Calculando Time-Between-Trades (TBT)...")
    if not df_processed.is_empty() and \
       'Match_time_utc_dt' in df_processed.columns and \
       df_processed['Match_time_utc_dt'].dtype == pl.Datetime(time_unit='us', time_zone='UTC') and \
       df_processed.height > 1: # Necesitamos al menos 2 trades para calcular TBT

        # Aseguramos que el DataFrame esté ordenado por tiempo para el cálculo de diff
        df_tbt_calc = df_processed.sort('Match_time_utc_dt')

        # Calculamos la diferencia entre timestamps consecutivos
        # El resultado de diff() es Duration, lo convertimos a segundos totales.
        tbt_series = df_tbt_calc['Match_time_utc_dt'].diff().dt.total_seconds().drop_nulls()

        if not tbt_series.is_empty():
            tbt_stats_dict = {
                'tbt_mean_seconds': [tbt_series.mean()],
                'tbt_median_seconds': [tbt_series.median()],
                'tbt_min_seconds': [tbt_series.min()],
                'tbt_max_seconds': [tbt_series.max()],
                'tbt_std_seconds': [tbt_series.std()],
                'tbt_p05_seconds': [tbt_series.quantile(0.05)],
                'tbt_p95_seconds': [tbt_series.quantile(0.95)],
                'tbt_count': [tbt_series.len()]
            }
            metrics['tbt_stats'] = pl.DataFrame(tbt_stats_dict)
            logger.info("Estadísticas TBT calculadas y añadidas a las métricas.")
        else:
            logger.warning("Series TBT resultó vacía después del cálculo. No se añadirán estadísticas TBT.")
            metrics['tbt_stats'] = pl.DataFrame({
                'tbt_mean_seconds': [None],
                'tbt_median_seconds': [None],
                'tbt_min_seconds': [None],
                'tbt_max_seconds': [None],
                'tbt_std_seconds': [None],
                'tbt_p05_seconds': [None],
                'tbt_p95_seconds': [None],
                'tbt_count': [0]
            })

    else:
        logger.warning("No se puede calcular TBT. Se requiere la columna 'Match_time_utc_dt' (Datetime UTC) y al menos 2 trades.")
        # Crear un DataFrame vacío con la estructura esperada si no se puede calcular
        metrics['tbt_stats'] = pl.DataFrame({
            'tbt_mean_seconds': [None],
            'tbt_median_seconds': [None],
            'tbt_min_seconds': [None],
            'tbt_max_seconds': [None],
            'tbt_std_seconds': [None],
            'tbt_p05_seconds': [None],
            'tbt_p95_seconds': [None],
            'tbt_count': [0]
        })

    # DONE: 1.4 Rolling P&L + Sharpe (7 días)
    logger.info("Calculando Rolling P&L (7 días) y Sharpe Ratio...")
    if 'vwap_daily' in metrics and not metrics['vwap_daily'].is_empty() and 'vwap' in metrics['vwap_daily'].columns:
        df_vwap_daily = metrics['vwap_daily']
        
        # Asegurarse que la columna vwap es Float64 para el cálculo de retornos
        if df_vwap_daily['vwap'].dtype != pl.Float64:
            df_vwap_daily = df_vwap_daily.with_columns(pl.col('vwap').cast(pl.Float64))

        daily_returns = finance_utils.calculate_daily_returns(df_vwap_daily['vwap'])
        
        # Añadir retornos al df_vwap_daily para referencia si es necesario
        # Necesitamos alinear los retornos con las fechas. daily_returns tendrá un nulo al principio.
        if not daily_returns.is_empty():
            # La serie daily_returns ya tiene la longitud correcta (misma que df_vwap_daily)
            # y tiene un nulo al principio debido a .shift(1) en su cálculo.
            df_vwap_daily = df_vwap_daily.with_columns(daily_returns.alias('daily_returns'))
            
            # Calcular P&L rodante de 7 días
            # Usar daily_returns.drop_nulls() para el cálculo de P&L, ya que no puede manejar el nulo inicial.
            rolling_pnl_7d = finance_utils.calculate_rolling_pnl(daily_returns.drop_nulls(), window_size=7)
            
            # El P&L rodante también tendrá nulos al principio, alinear con fechas
            if not rolling_pnl_7d.is_empty():
                # El P&L rodante con ventana 7 sobre N retornos, tendrá N-(7-1) = N-6 valores.
                # Y los retornos tienen M-1 valores respecto a M precios.
                # Entonces, P&L tiene (M-1) - 6 = M-7 valores.
                # Necesitamos M-7 valores alineados con las últimas M-7 fechas.
                
                # Longitud esperada de rolling_pnl_7d es daily_returns.drop_nulls().len() - (7 -1)
                # Si df_vwap_daily tiene N filas, daily_returns tiene N-1 filas (sin nulos).
                # rolling_pnl_7d tiene (N-1) - (7-1) = N-7 filas.
                # Se alinea con las últimas N-7 fechas de df_vwap_daily.
                
                num_pnl_values = rolling_pnl_7d.len()
                num_total_dates = df_vwap_daily.height
                
                if num_pnl_values > 0 and num_total_dates > num_pnl_values:
                    padding_pnl = [None] * (num_total_dates - num_pnl_values)
                    aligned_pnl_series = pl.Series(padding_pnl + list(rolling_pnl_7d), dtype=pl.Float64)
                    df_vwap_daily = df_vwap_daily.with_columns(aligned_pnl_series.alias('rolling_pnl_7d'))
                elif num_pnl_values > 0 and num_pnl_values == num_total_dates: # Caso menos probable pero posible si hay pocos datos
                     df_vwap_daily = df_vwap_daily.with_columns(rolling_pnl_7d.alias('rolling_pnl_7d'))


            metrics['rolling_pnl_7d'] = df_vwap_daily.select(['date', 'vwap', 'daily_returns', 'rolling_pnl_7d']).drop_nulls(subset=['rolling_pnl_7d'])
            
            # Calcular Sharpe Ratio (general, no rodante)
            sharpe_ratio_overall = finance_utils.calculate_sharpe_ratio(daily_returns.drop_nulls())
            metrics['sharpe_ratio_overall'] = pl.DataFrame({'sharpe_ratio': [sharpe_ratio_overall]})
            logger.info(f"Rolling P&L (7d) y Sharpe Ratio calculados. Sharpe: {sharpe_ratio_overall}")
            
        else:
            logger.warning("No se pudieron calcular retornos diarios a partir de vwap_daily. P&L y Sharpe no calculados.")
            metrics['rolling_pnl_7d'] = pl.DataFrame({'date': [], 'vwap': [], 'daily_returns': [], 'rolling_pnl_7d': []}, schema={'date': pl.Date, 'vwap': pl.Float64, 'daily_returns': pl.Float64, 'rolling_pnl_7d': pl.Float64})
            metrics['sharpe_ratio_overall'] = pl.DataFrame({'sharpe_ratio': [None]}, schema={'sharpe_ratio': pl.Float64})
    else:
        logger.warning("No se puede calcular Rolling P&L y Sharpe Ratio: 'vwap_daily' no disponible o no contiene columna 'vwap'.")
        metrics['rolling_pnl_7d'] = pl.DataFrame({'date': [], 'vwap': [], 'daily_returns': [], 'rolling_pnl_7d': []}, schema={'date': pl.Date, 'vwap': pl.Float64, 'daily_returns': pl.Float64, 'rolling_pnl_7d': pl.Float64})
        metrics['sharpe_ratio_overall'] = pl.DataFrame({'sharpe_ratio': [None]}, schema={'sharpe_ratio': pl.Float64})

    # DONE: 1.5 Estacionalidad (STL / FFT) en volumen
    logger.info("Analizando estacionalidad en volumen (FFT)...")
    if 'vwap_daily' in metrics and not metrics['vwap_daily'].is_empty() and 'total_volume' in metrics['vwap_daily'].columns:
        df_vwap_info = metrics['vwap_daily']
        daily_volumes = df_vwap_info['total_volume'].drop_nulls()

        if daily_volumes.len() > 1: # Necesitamos al menos 2 puntos para FFT
            try:
                # Aplicar FFT
                volume_fft = np.fft.fft(daily_volumes.to_numpy()) # type: ignore
                fft_freq = np.fft.fftfreq(daily_volumes.len())
                
                # Obtener magnitudes y excluir el componente DC (frecuencia cero)
                magnitudes = np.abs(volume_fft)[1:]
                frequencies = fft_freq[1:]
                
                # Filtrar solo frecuencias positivas (la FFT es simétrica para entradas reales)
                positive_freq_mask = frequencies > 0
                magnitudes = magnitudes[positive_freq_mask]
                frequencies = frequencies[positive_freq_mask]

                if magnitudes.size > 0:
                    # Encontrar las N frecuencias más dominantes (ej. N=3)
                    top_n = 3
                    dominant_indices = np.argsort(magnitudes)[-top_n:][::-1]
                    
                    dominant_frequencies = frequencies[dominant_indices]
                    dominant_magnitudes = magnitudes[dominant_indices]
                    # Periodos en días (asumiendo que los datos son diarios)
                    dominant_periods = 1 / dominant_frequencies 

                    fft_results_list = []
                    for i in range(len(dominant_frequencies)):
                        fft_results_list.append({
                            'rank': i + 1,
                            'frequency': dominant_frequencies[i],
                            'magnitude': dominant_magnitudes[i],
                            'period_days': dominant_periods[i]
                        })
                    metrics['volume_seasonality_fft'] = pl.DataFrame(fft_results_list)
                    logger.info(f"Análisis FFT de estacionalidad de volumen completado. Principales periodos (días): {dominant_periods}")
                else:
                    logger.warning("No se encontraron frecuencias positivas en FFT de volumen.")
                    metrics['volume_seasonality_fft'] = pl.DataFrame()
            except Exception as e:
                logger.error(f"Error durante el cálculo de FFT para estacionalidad de volumen: {e}")
                metrics['volume_seasonality_fft'] = pl.DataFrame()
        else:
            logger.warning("No hay suficientes datos de volumen diario (después de quitar nulos) para análisis FFT.")
            metrics['volume_seasonality_fft'] = pl.DataFrame()
    else:
        logger.warning("No se puede analizar estacionalidad de volumen: 'vwap_daily' o 'total_volume' no disponibles.")
        metrics['volume_seasonality_fft'] = pl.DataFrame()

    if 'hour_local' in df_processed.columns and df_processed['hour_local'].null_count() < df_processed.height:
        metrics['hourly_counts'] = df_processed['hour_local'].value_counts().sort(by='hour_local')
    else:
        metrics['hourly_counts'] = pl.DataFrame({'hour_local': pl.Series([], dtype=pl.Int64), 'counts': pl.Series([], dtype=pl.UInt32)})

    logger.info("Calculando nuevas métricas de resumen de ventas con Polars...")
    sell_indicator_col_mapped = sell_config.get('indicator_column') 
    sell_indicator_value = sell_config.get('indicator_value')
    
    if not (sell_indicator_col_mapped and sell_indicator_value and sell_indicator_col_mapped in df_completed_for_sales_summary.columns):
        logger.warning(f"Configuración de ventas incompleta o columna '{sell_indicator_col_mapped}' no encontrada en df_completed_for_sales_summary.")
    elif df_completed_for_sales_summary.is_empty():
         logger.warning(f"No hay operaciones completadas (df_completed_for_sales_summary) para resumen de ventas.")
    else:
        df_sales_completed = df_completed_for_sales_summary.filter(pl.col(sell_indicator_col_mapped) == sell_indicator_value)

        if df_sales_completed.is_empty():
            logger.info(f"No se encontraron operaciones de venta (col '{sell_indicator_col_mapped}' == '{sell_indicator_value}') entre las completadas.")
        else:
            logger.info(f"Procesando {df_sales_completed.height} operaciones de venta completadas.")
            required_cols_for_sales = [asset_type_col, 'Quantity_num', 'TotalPrice_num', fiat_type_col]
            if not all(col in df_sales_completed.columns for col in required_cols_for_sales):
                logger.warning(f"Faltan columnas para el resumen de ventas ({required_cols_for_sales}). No se calculará.")
            else:
                df_sales_summary_all_assets = (
                    df_sales_completed.group_by([asset_type_col, fiat_type_col])
                    .agg([
                        pl.col('Quantity_num').sum().alias('Total Asset Sold'),
                        pl.col('TotalPrice_num').sum().alias('Total Fiat Received')
                    ])
                    .with_columns([
                        (pl.col('Total Fiat Received') / pl.col('Total Asset Sold')).alias('Average Sell Price (in Fiat Received)')
                    ])
                    .rename({
                        asset_type_col: 'Asset Sold',
                        fiat_type_col: 'Fiat Received'
                    })
                )
                if not df_sales_summary_all_assets.is_empty():
                    metrics['sales_summary_all_assets_fiat_detailed'] = df_sales_summary_all_assets
                    logger.info(f"Resumen de ventas detallado calculado con {df_sales_summary_all_assets.height} filas.")
                else:
                    metrics['sales_summary_all_assets_fiat_detailed'] = pl.DataFrame()

    # DONE: 1.6 Detección de Outliers con IsolationForest
    logger.info("Iniciando detección de outliers con IsolationForest...")
    # El argumento cli_args debe pasarse a la función analyze.
    # Se asume que args de app.py (o main_logic.py) se pasa como cli_args.
    detect_outliers_active = cli_args.get('detect_outliers', False) if cli_args else False

    if detect_outliers_active:
        if 'TotalPrice_num' in df_processed.columns and not df_processed.filter(pl.col('TotalPrice_num').is_not_null()).is_empty():
            df_for_outliers = df_processed.select(['TotalPrice_num']).drop_nulls()
            if not df_for_outliers.is_empty():
                try:
                    model = IsolationForest(n_estimators=100, contamination='auto', random_state=42)
                    # IsolationForest espera un array de Numpy 2D
                    df_for_outliers_np = df_for_outliers.to_numpy()
                    model.fit(df_for_outliers_np)
                    
                    # Predecir outliers (-1 para outlier, 1 para inlier)
                    # Para alinear con el df original, primero creamos una columna de predicciones nulas
                    # outlier_predictions = pl.Series([None] * df_processed.height, dtype=pl.Int8) # No se usa directamente
                    
                    # Obtenemos los índices de las filas no nulas usadas para el entrenamiento
                    # Corregido el acceso a la columna y conversión a Series
                    non_null_indices_df = df_processed.with_row_count().filter(pl.col('TotalPrice_num').is_not_null()).select(pl.col("row_nr"))
                    non_null_indices = non_null_indices_df.to_series()

                    # Hacemos predicciones sobre los datos no nulos
                    predictions_on_non_null = model.predict(df_for_outliers_np)
                    
                    # Creamos una serie temporal para actualizar las posiciones correctas
                    # Convertimos las predicciones a una serie de Polars
                    predictions_series = pl.Series("outlier_pred_temp", predictions_on_non_null, dtype=pl.Int8)
                    
                    # Actualizamos la columna de predicciones de outliers en el df_processed
                    df_temp_predictions = pl.DataFrame({
                        "row_nr": non_null_indices, # Usar la serie de índices aquí
                        "outlier_TotalPrice_num": predictions_series
                    })
                    
                    df_processed = df_processed.with_row_count().join(
                        df_temp_predictions, on="row_nr", how="left"
                    ).drop("row_nr")

                    num_outliers = df_processed.filter(pl.col('outlier_TotalPrice_num') == -1).height
                    # Seleccionar columnas relevantes, incluyendo el identificador de orden si está mapeado
                    order_id_col_for_outliers = order_number_col if order_number_col in df_processed.columns else None
                    cols_to_select_for_outliers = [col for col in [order_id_col_for_outliers, 'TotalPrice_num', 'outlier_TotalPrice_num'] if col is not None and col in df_processed.columns]
                    
                    if cols_to_select_for_outliers:
                        metrics['outliers_totalprice_num'] = df_processed.filter(pl.col('outlier_TotalPrice_num') == -1).select(cols_to_select_for_outliers)
                    else:
                        metrics['outliers_totalprice_num'] = pl.DataFrame() # Vacío si no hay columnas para seleccionar

                    logger.info(f"Detección de outliers completada. {num_outliers} outliers encontrados en TotalPrice_num.")
                except Exception as e:
                    logger.error(f"Error durante la detección de outliers con IsolationForest: {e}")
                    df_processed = df_processed.with_columns(pl.lit(None, dtype=pl.Int8).alias('outlier_TotalPrice_num'))
                    metrics['outliers_totalprice_num'] = pl.DataFrame()
            else:
                logger.warning("No hay datos no nulos en 'TotalPrice_num' para la detección de outliers.")
                df_processed = df_processed.with_columns(pl.lit(None, dtype=pl.Int8).alias('outlier_TotalPrice_num'))
                metrics['outliers_totalprice_num'] = pl.DataFrame()
        else:
            logger.warning("Columna 'TotalPrice_num' no encontrada o vacía, no se realizará detección de outliers.")
            # Asegurar que la columna exista aunque no se procese para consistencia del esquema
            if 'outlier_TotalPrice_num' not in df_processed.columns:
                 df_processed = df_processed.with_columns(pl.lit(None, dtype=pl.Int8).alias('outlier_TotalPrice_num'))
            metrics['outliers_totalprice_num'] = pl.DataFrame()
    else:
        logger.info("Detección de outliers no activada.")
        if 'outlier_TotalPrice_num' not in df_processed.columns:
            df_processed = df_processed.with_columns(pl.lit(None, dtype=pl.Int8).alias('outlier_TotalPrice_num'))
        metrics['outliers_totalprice_num'] = pl.DataFrame() # DataFrame vacío si no está activo

    # DONE: 1.7 Índice de liquidez efectiva (mean_qty/median_qty)
    logger.info("Calculando Índice de Liquidez Efectiva (mean_qty/median_qty)...")
    if 'Quantity_num' in df_processed.columns and df_processed['Quantity_num'].null_count() < df_processed.height:
        quantity_series = df_processed['Quantity_num'].drop_nulls()
        if not quantity_series.is_empty():
            mean_qty = quantity_series.mean()
            median_qty = quantity_series.median()

            if median_qty is not None and median_qty != 0 and mean_qty is not None:
                effective_liquidity_index = mean_qty / median_qty
                metrics['effective_liquidity_index'] = pl.DataFrame({'index_value': [effective_liquidity_index], 'mean_quantity': [mean_qty], 'median_quantity': [median_qty]})
                logger.info(f"Índice de Liquidez Efectiva calculado: {effective_liquidity_index:.4f} (Media: {mean_qty:.4f}, Mediana: {median_qty:.4f})")
            else:
                logger.warning("No se puede calcular el Índice de Liquidez Efectiva: mediana es cero, nula o media es nula.")
                metrics['effective_liquidity_index'] = pl.DataFrame({'index_value': [None], 'mean_quantity': [mean_qty], 'median_quantity': [median_qty]})
        else:
            logger.warning("Columna 'Quantity_num' no tiene valores no nulos para calcular el índice de liquidez.")
            metrics['effective_liquidity_index'] = pl.DataFrame({'index_value': [None], 'mean_quantity': [mean_qty], 'median_quantity': [median_qty]})
    else:
        logger.warning("Columna 'Quantity_num' no encontrada o completamente nula. No se calculará el Índice de Liquidez Efectiva.")
        metrics['effective_liquidity_index'] = pl.DataFrame({'index_value': [None], 'mean_quantity': [mean_qty], 'median_quantity': [median_qty]})

    # DONE: 3.1 Whale trades (> mean + 3σ)
    logger.info("Detectando Whale Trades (TotalPrice_num > mean + 3*std)...")
    if 'TotalPrice_num' in df_processed.columns and not df_processed.filter(pl.col('TotalPrice_num').is_not_null()).is_empty():
        total_price_series = df_processed['TotalPrice_num'].drop_nulls()
        if not total_price_series.is_empty():
            mean_total_price = total_price_series.mean()
            std_total_price = total_price_series.std()

            if mean_total_price is not None and std_total_price is not None:
                whale_threshold = mean_total_price + (3 * std_total_price)
                df_whale_trades = df_processed.filter(pl.col('TotalPrice_num') > whale_threshold)
                
                cols_for_whale_report = [ # Columnas que podrían ser interesantes para el reporte de whale trades
                    order_number_col, asset_type_col, fiat_type_col, 'Price_num', 'Quantity_num', 'TotalPrice_num', 'Match_time_local'
                ]
                # Filtrar solo las columnas que existen en df_whale_trades
                actual_cols_for_whale_report = [col for col in cols_for_whale_report if col in df_whale_trades.columns]

                if not df_whale_trades.is_empty() and actual_cols_for_whale_report:
                    metrics['whale_trades'] = df_whale_trades.select(actual_cols_for_whale_report).sort('TotalPrice_num', descending=True)
                    logger.info(f"Se detectaron {df_whale_trades.height} whale trades con umbral {whale_threshold:.2f}.")
                else:
                    logger.info(f"No se detectaron whale trades con umbral {whale_threshold:.2f} o faltan columnas para el reporte.")
                    metrics['whale_trades'] = pl.DataFrame()
            else:
                logger.warning("No se pudo calcular la media o desviación estándar de TotalPrice_num para detectar whale trades.")
                metrics['whale_trades'] = pl.DataFrame()
        else:
            logger.warning("La serie TotalPrice_num está vacía después de quitar nulos. No se detectarán whale trades.")
            metrics['whale_trades'] = pl.DataFrame()
    else:
        logger.warning("Columna 'TotalPrice_num' no disponible para detectar whale trades.")
        metrics['whale_trades'] = pl.DataFrame()

    # DONE: 3.2 Before/After --event_date comparativo 24h
    logger.info("Analizando comparación Antes/Después de --event-date...")
    event_date_str = cli_args.get('event_date') if cli_args else None
    if event_date_str:
        try:
            # Asumir que event_date_str es YYYY-MM-DD. Convertir a datetime UTC al inicio del día.
            event_dt_utc = datetime.strptime(event_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            logger.info(f"Fecha de evento para comparación: {event_dt_utc}")

            if 'Match_time_utc_dt' in df_processed.columns and df_processed['Match_time_utc_dt'].dtype == pl.Datetime(time_unit='us', time_zone='UTC'):
                # Definir ventanas de 24h antes y después
                before_window_start = event_dt_utc - timedelta(hours=24)
                before_window_end = event_dt_utc 
                after_window_start = event_dt_utc
                after_window_end = event_dt_utc + timedelta(hours=24)

                df_before_event = df_processed.filter(
                    (pl.col('Match_time_utc_dt') >= before_window_start) & 
                    (pl.col('Match_time_utc_dt') < before_window_end)
                )
                df_after_event = df_processed.filter(
                    (pl.col('Match_time_utc_dt') >= after_window_start) & 
                    (pl.col('Match_time_utc_dt') < after_window_end) 
                )

                event_comparison_stats = {}
                for period_label, df_period in [("24h_before_event", df_before_event), ("24h_after_event", df_after_event)]:
                    if not df_period.is_empty():
                        stats = {
                            'num_trades': df_period.height,
                            'total_volume_asset': df_period['Quantity_num'].sum() if 'Quantity_num' in df_period.columns else None,
                            'total_volume_fiat': df_period['TotalPrice_num'].sum() if 'TotalPrice_num' in df_period.columns else None,
                            'avg_price': df_period['Price_num'].mean() if 'Price_num' in df_period.columns else None,
                            'median_price': df_period['Price_num'].median() if 'Price_num' in df_period.columns else None
                        }
                        event_comparison_stats[period_label] = stats
                    else:
                        event_comparison_stats[period_label] = {'num_trades': 0, 'total_volume_asset': 0, 'total_volume_fiat': 0, 'avg_price': None, 'median_price': None}
                
                if event_comparison_stats:
                    metrics['event_comparison_stats'] = pl.from_dicts([ # Convertir a DataFrame para consistencia
                        dict(period=k, **v) for k,v in event_comparison_stats.items()
                    ])
                    logger.info(f"Estadísticas comparativas Antes/Después del evento calculadas: {event_comparison_stats}")
                else:
                    metrics['event_comparison_stats'] = pl.DataFrame()
            else:
                logger.warning("Columna 'Match_time_utc_dt' (Datetime UTC) no disponible o tipo incorrecto. No se puede hacer comparación Antes/Después.")
                metrics['event_comparison_stats'] = pl.DataFrame()
        except ValueError:
            logger.error(f"Formato de --event-date incorrecto: '{event_date_str}'. Debe ser YYYY-MM-DD.")
            metrics['event_comparison_stats'] = pl.DataFrame()
        except Exception as e_event:
            logger.error(f"Error durante análisis comparativo Antes/Después: {e_event}")
            metrics['event_comparison_stats'] = pl.DataFrame()
    else:
        logger.info("--event-date no proporcionado. Se omite análisis comparativo Antes/Después.")
        metrics['event_comparison_stats'] = pl.DataFrame() # Vacío si no se activa

    logger.info("Análisis (cálculo de métricas con Polars) completado.")
    return df_processed, metrics
import polars as pl
import logging
from .utils import parse_amount # Importar parse_amount de utils
from . import finance_utils # Usar import relativo si está en el mismo paquete src
import numpy as np # Añadir numpy para FFT
from sklearn.ensemble import IsolationForest
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

    # --- INICIO: Parche para corregir Price_num en USDT/USD ---
    if (asset_type_col in df_processed.columns and
        fiat_type_col in df_processed.columns and
        order_type_col in df_processed.columns and
        'Price_num' in df_processed.columns):

        price_correction_condition = (
            (pl.col(asset_type_col) == "USDT") &
            (pl.col(fiat_type_col) == "USD") &
            (pl.col('Price_num').is_not_null()) &
            (pl.col('Price_num') > 10) # Umbral para precios probablemente mal interpretados
        )

        # Contar cuántas filas se van a afectar antes de la corrección
        rows_to_correct_count = df_processed.filter(price_correction_condition).height
        if rows_to_correct_count > 0:
            logger.info(f"Detectadas {rows_to_correct_count} filas de USDT/USD con Price_num > 10. Se intentará corregir dividiendo por 1000.")
            
            df_processed = df_processed.with_columns(
                pl.when(price_correction_condition)
                .then(pl.col('Price_num') / 1000)
                .otherwise(pl.col('Price_num'))
                .alias('Price_num')
            )
            logger.info(f"Corrección de Price_num para USDT/USD aplicada.")
        else:
            logger.info("No se encontraron filas USDT/USD que necesiten corrección de Price_num (Price_num > 10).")
    else:
        logger.info("No se aplicó el parche de corrección de Price_num para USDT/USD porque faltan una o más columnas requeridas (asset_type, fiat_type, Price_num).")
    # --- FIN: Parche para corregir Price_num en USDT/USD ---

    # --- INICIO: Crear TotalPrice_USD_equivalent ---
    logger.info("Creando columna 'TotalPrice_USD_equivalent' para volúmenes combinados...")
    if ('TotalPrice_num' in df_processed.columns and
        fiat_type_col in df_processed.columns and
        asset_type_col in df_processed.columns and
        'Price_num' in df_processed.columns):

        df_processed = df_processed.with_columns(
            pl.when(pl.col(fiat_type_col).is_in(["USD", "USDT"]))
            .then(pl.col('TotalPrice_num'))
            .when(
                (pl.col(fiat_type_col) == "UYU") &
                (pl.col(asset_type_col) == "USDT") &
                (pl.col('Price_num').is_not_null()) &
                (pl.col('Price_num') != 0) # Evitar división por cero
            )
            .then(pl.col('TotalPrice_num') / pl.col('Price_num'))
            .otherwise(None) # Para otras combinaciones (ej. UYU con BTC) o UYU/USDT con Price_num cero/nulo
            .alias('TotalPrice_USD_equivalent')
        )
        logger.info("Columna 'TotalPrice_USD_equivalent' creada.")
        
        null_equivalent_count = df_processed.filter(pl.col('TotalPrice_USD_equivalent').is_null()).height
        if null_equivalent_count > 0:
            logger.info(f"  {null_equivalent_count} filas tienen 'TotalPrice_USD_equivalent' nulo (posibles casos UYU no USDT, o Price_num cero/nulo).")
        
        uyu_not_converted_df = df_processed.filter(
            (pl.col(fiat_type_col) == "UYU") &
            (pl.col('TotalPrice_USD_equivalent').is_null())
        )
        if not uyu_not_converted_df.is_empty():
            logger.info(f"  Se encontraron {uyu_not_converted_df.height} filas UYU no convertidas a USD equivalente. Ejemplos de asset_type: {uyu_not_converted_df.group_by(asset_type_col).agg(pl.count()).sort('count', descending=True).head(3)}")

    else:
        logger.warning("No se pudo crear 'TotalPrice_USD_equivalent' porque faltan una o más columnas requeridas (TotalPrice_num, fiat_type, asset_type, Price_num). Se creará con nulos.")
        df_processed = df_processed.with_columns(pl.lit(None, dtype=pl.Float64).alias('TotalPrice_USD_equivalent'))
    # --- FIN: Crear TotalPrice_USD_equivalent ---

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

    logger.info("Iniciando Detección de Outliers (Isolation Forest) en Price_num...")
    if cli_args and getattr(cli_args, 'detect_outliers', False):
        if 'Price_num' in df_processed.columns and not df_processed.filter(pl.col('Price_num').is_not_null()).is_empty():
            df_for_outliers = df_processed.select(['Price_num', order_number_col, 'Match_time_local']).drop_nulls(subset=['Price_num'])
            
            if df_for_outliers.height > 1: # IsolationForest necesita al menos 2 muestras
                prices_for_model = df_for_outliers.select('Price_num').to_numpy()
                
                try:
                    iso_forest = IsolationForest(
                        n_estimators=cli_args.get('outliers_n_estimators', 100),
                        contamination=float(cli_args.get('outliers_contamination', 'auto')), # 'auto' o un float
                        random_state=cli_args.get('outliers_random_state', 42),
                        n_jobs=-1 # Usar todos los procesadores disponibles
                    )
                    iso_forest.fit(prices_for_model)
                    
                    # Predecir outliers (-1 para outliers, 1 para inliers)
                    outlier_predictions = iso_forest.predict(prices_for_model)
                    
                    # Añadir predicciones al DataFrame temporal
                    df_for_outliers = df_for_outliers.with_columns(
                        pl.Series(name="is_outlier", values=(outlier_predictions == -1))
                    )
                    
                    # Contar outliers
                    num_outliers = df_for_outliers.filter(pl.col("is_outlier")).height
                    logger.info(f"Detección de Outliers completada. Se encontraron {num_outliers} outliers en 'Price_num'.")

                    # Preparar DataFrame de información de outliers para métricas
                    # Seleccionar columnas relevantes para el reporte de outliers
                    outlier_report_cols = [order_number_col, 'Match_time_local', 'Price_num']
                    # Verificar que las columnas existan en df_for_outliers
                    actual_outlier_report_cols = [col for col in outlier_report_cols if col in df_for_outliers.columns]
                    
                    if actual_outlier_report_cols:
                         metrics['outlier_info'] = df_for_outliers.filter(pl.col("is_outlier")).select(actual_outlier_report_cols).sort('Match_time_local')
                    else:
                        logger.warning("No se pudieron seleccionar columnas para el reporte de outliers, puede que falten.")
                        metrics['outlier_info'] = pl.DataFrame()

                except Exception as e_iso:
                    logger.error(f"Error durante la detección de outliers con IsolationForest: {e_iso}")
                    metrics['outlier_info'] = pl.DataFrame() # Devolver DataFrame vacío en caso de error
            else:
                logger.info("No hay suficientes datos (después de quitar nulos en Price_num) para ejecutar IsolationForest. Se requieren al menos 2 muestras.")
                metrics['outlier_info'] = pl.DataFrame()
        else:
            logger.info("Columna 'Price_num' no disponible o vacía después de quitar nulos. No se ejecutará la detección de outliers.")
            metrics['outlier_info'] = pl.DataFrame()
    else:
        logger.info("Detección de outliers no activada mediante argumento CLI (--detect_outliers).")
        metrics['outlier_info'] = pl.DataFrame() # DataFrame vacío si no está activada

    logger.info("Análisis finalizado.")
    return df_processed, metrics
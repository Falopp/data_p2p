import polars as pl
import logging
from utils import parse_amount # Importar parse_amount de utils

logger = logging.getLogger(__name__)

def analyze(df: pl.DataFrame, col_map: dict, sell_config: dict) -> tuple[pl.DataFrame, dict[str, pl.DataFrame | pl.Series]]:
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

    logger.info("Análisis (cálculo de métricas con Polars) completado.")
    return df_processed, metrics 
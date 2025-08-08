import polars as pl
import logging
from .utils import parse_amount  # Importar parse_amount de utils
from . import finance_utils  # Usar import relativo si está en el mismo paquete src
from . import counterparty_analyzer  # Importar el módulo de análisis de contrapartes
from . import session_analyzer  # Importar el nuevo módulo de análisis de sesiones
import numpy as np  # Añadir numpy para FFT
from sklearn.ensemble import IsolationForest
from datetime import datetime, timedelta, timezone
from .transformations.numeric import process_numeric_columns
from .transformations.patches import (
    patch_usdt_usd_price,
    create_total_price_usd_equivalent,
)
from .finance_utils import (
    calculate_daily_returns,
    calculate_rolling_pnl,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    compute_drawdown_series,
    calculate_max_drawdown,
)

logger = logging.getLogger(__name__)


def analyze(
    df: pl.DataFrame, col_map: dict, sell_config: dict, cli_args: dict | None = None
) -> tuple[pl.DataFrame, dict[str, pl.DataFrame | pl.Series]]:
    logger.info("Iniciando análisis con Polars...")
    df_processed = df.clone()

    order_type_col = "order_type"
    asset_type_col = "asset_type"
    fiat_type_col = "fiat_type"
    total_price_col = "total_price"
    price_col = "price"
    quantity_col = "quantity"
    status_col = "status"
    match_time_utc_col = "match_time_utc"
    maker_fee_col = "maker_fee"
    taker_fee_col = "taker_fee"
    order_number_col = "order_number"
    payment_method_col = "payment_method"

    # Procesamiento de columnas numéricas
    df_processed = process_numeric_columns(df_processed)

    # Aplicar parche de corrección de precios USDT/USD
    if (
        asset_type_col in df_processed.columns
        and fiat_type_col in df_processed.columns
        and order_type_col in df_processed.columns
        and "Price_num" in df_processed.columns
    ):
        price_correction_condition = (
            (pl.col(asset_type_col) == "USDT")
            & (pl.col(fiat_type_col) == "USD")
            & (pl.col("Price_num").is_not_null())
            & (
                pl.col("Price_num") > 10
            )  # Umbral para precios probablemente mal interpretados
        )

        # Contar cuántas filas se van a afectar antes de la corrección
        rows_to_correct_count = df_processed.filter(price_correction_condition).height
        if rows_to_correct_count > 0:
            logger.info(
                f"Detectadas {rows_to_correct_count} filas de USDT/USD con Price_num > 10. Se intentará corregir dividiendo por 1000."
            )

            df_processed = df_processed.with_columns(
                pl.when(price_correction_condition)
                .then(pl.col("Price_num") / 1000)
                .otherwise(pl.col("Price_num"))
                .alias("Price_num")
            )
            logger.info(f"Corrección de Price_num para USDT/USD aplicada.")
        else:
            logger.info(
                "No se encontraron filas USDT/USD que necesiten corrección de Price_num (Price_num > 10)."
            )
    else:
        logger.info(
            "No se aplicó el parche de corrección de Price_num para USDT/USD porque faltan una o más columnas requeridas (asset_type, fiat_type, Price_num)."
        )

    # Crear columna de TotalPrice_USD_equivalent
    logger.info(
        "Creando columna 'TotalPrice_USD_equivalent' para volúmenes combinados..."
    )
    if (
        "TotalPrice_num" in df_processed.columns
        and fiat_type_col in df_processed.columns
        and asset_type_col in df_processed.columns
        and "Price_num" in df_processed.columns
    ):
        df_processed = df_processed.with_columns(
            pl.when(pl.col(fiat_type_col).is_in(["USD", "USDT"]))
            .then(pl.col("TotalPrice_num"))
            .when(
                (pl.col(fiat_type_col) == "UYU")
                & (pl.col(asset_type_col) == "USDT")
                & (pl.col("Price_num").is_not_null())
                & (pl.col("Price_num") != 0)  # Evitar división por cero
            )
            .then(pl.col("TotalPrice_num") / pl.col("Price_num"))
            .otherwise(
                None
            )  # Para otras combinaciones (ej. UYU con BTC) o UYU/USDT con Price_num cero/nulo
            .alias("TotalPrice_USD_equivalent")
        )
        logger.info("Columna 'TotalPrice_USD_equivalent' creada.")

        null_equivalent_count = df_processed.filter(
            pl.col("TotalPrice_USD_equivalent").is_null()
        ).height
        if null_equivalent_count > 0:
            logger.info(
                f"  {null_equivalent_count} filas tienen 'TotalPrice_USD_equivalent' nulo (posibles casos UYU no USDT, o Price_num cero/nulo)."
            )

        uyu_not_converted_df = df_processed.filter(
            (pl.col(fiat_type_col) == "UYU")
            & (pl.col("TotalPrice_USD_equivalent").is_null())
        )
        if not uyu_not_converted_df.is_empty():
            logger.info(
                f"  Se encontraron {uyu_not_converted_df.height} filas UYU no convertidas a USD equivalente. Ejemplos de asset_type: {uyu_not_converted_df.group_by(asset_type_col).agg(pl.count()).sort('count', descending=True).head(3)}"
            )

    else:
        logger.warning(
            "No se pudo crear 'TotalPrice_USD_equivalent' porque faltan una o más columnas requeridas (TotalPrice_num, fiat_type, asset_type, Price_num). Se creará con nulos."
        )
        df_processed = df_processed.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("TotalPrice_USD_equivalent")
        )

    df_processed = create_total_price_usd_equivalent(df_processed)

    if "MakerFee_num" not in df_processed.columns:
        df_processed = df_processed.with_columns(
            pl.lit(0.0, dtype=pl.Float64).alias("MakerFee_num")
        )
    if "TakerFee_num" not in df_processed.columns:
        df_processed = df_processed.with_columns(
            pl.lit(0.0, dtype=pl.Float64).alias("TakerFee_num")
        )

    df_processed = df_processed.with_columns(
        (
            pl.col("MakerFee_num").fill_null(0.0)
            + pl.col("TakerFee_num").fill_null(0.0)
        ).alias("TotalFee")
    )

    logger.info(
        "Verificando columnas de tiempo pre-procesadas (esperadas desde app.py)..."
    )
    required_time_cols = {
        "Match_time_local": pl.Datetime,
        "hour_local": pl.Int64,  # Polars usa Int32 para hour, pero Int64 es seguro para la comprobación de tipo base.
        "YearMonthStr": pl.String,
        "Year": pl.Int64,  # Polars usa Int32 para year.
    }
    missing_or_wrong_type_time_cols = []
    for col_name, expected_type_class in required_time_cols.items():
        if col_name not in df_processed.columns:
            missing_or_wrong_type_time_cols.append(f"'{col_name}' (faltante)")
        else:
            actual_type = df_processed.schema.get(col_name)
            # Comprobación genérica de tipo
            if expected_type_class == pl.Datetime and not isinstance(
                actual_type, pl.Datetime
            ):
                missing_or_wrong_type_time_cols.append(
                    f"'{col_name}' (tipo incorrecto: {actual_type}, esperado: Datetime)"
                )
            elif expected_type_class == pl.String and not isinstance(
                actual_type, pl.String
            ):
                missing_or_wrong_type_time_cols.append(
                    f"'{col_name}' (tipo incorrecto: {actual_type}, esperado: String)"
                )
            elif expected_type_class == pl.Int64 and not isinstance(
                actual_type,
                (
                    pl.Int8,
                    pl.Int16,
                    pl.Int32,
                    pl.Int64,
                    pl.UInt8,
                    pl.UInt16,
                    pl.UInt32,
                    pl.UInt64,
                ),
            ):  # Comprobar si es algún tipo entero de Polars
                missing_or_wrong_type_time_cols.append(
                    f"'{col_name}' (tipo incorrecto: {actual_type}, esperado: Integer)"
                )

    if missing_or_wrong_type_time_cols:
        logger.warning(
            "Una o más columnas de tiempo pre-procesadas faltan o tienen tipo incorrecto. "
            f"Detalles: {', '.join(missing_or_wrong_type_time_cols)}. "
            "Esto puede afectar análisis posteriores. "
            "Asegúrese que app.py está generando estas columnas correctamente."
        )
    else:
        logger.info(
            "Columnas de tiempo pre-procesadas verificadas y parecen correctas."
        )

    metrics: dict[str, pl.DataFrame | pl.Series] = {}
    logger.info("Calculando métricas con Polars...")

    # --- NUEVO: Análisis de Contrapartes ---
    logger.info("Iniciando análisis avanzado de contrapartes...")
    try:
        # Llamada a la función principal de análisis de contrapartes del módulo
        # Esta función ahora encapsula toda la lógica, incluyendo los joins internos.
        # ESTO AHORA DEVUELVE UN DICCIONARIO
        all_counterparty_metrics_dict = counterparty_analyzer.analyze_counterparties(
            df_processed
        )

        if all_counterparty_metrics_dict:  # Si el diccionario no está vacío
            logger.info(
                f"[analyzer.py:analyze] Diccionario de métricas de contrapartes RECIBIDO. Claves: {list(all_counterparty_metrics_dict.keys())}"
            )
            expected_cp_keys_for_plotting = [
                "general_stats",
                "temporal_evolution",
                "payment_preferences",
                "trading_patterns",
                "vip_counterparties",
                "efficiency_stats",
            ]
            for metric_key, metric_df in all_counterparty_metrics_dict.items():
                if metric_df is not None and not metric_df.is_empty():
                    # Usar el prefijo 'counterparty_' para que src/reporter.py lo encuentre
                    metrics[f"counterparty_{metric_key}"] = metric_df
                    logger.info(
                        f"  Métrica de contraparte '{metric_key}' (DataFrame Polars) añadida a 'metrics' con clave 'counterparty_{metric_key}'. Altura: {metric_df.height}"
                    )
                else:
                    logger.warning(
                        f"  Métrica de contraparte '{metric_key}' devuelta por el analizador está vacía o es None. Se añadirá como DataFrame vacío con clave 'counterparty_{metric_key}'."
                    )
                    metrics[
                        f"counterparty_{metric_key}"
                    ] = pl.DataFrame()  # Asegurar que la clave exista

            # Asegurar que todas las claves esperadas por el plotter existan en metrics, incluso si no vinieron del analizador
            for key in expected_cp_keys_for_plotting:
                if f"counterparty_{key}" not in metrics:
                    logger.warning(
                        f"  Métrica de contraparte esperada '{key}' no fue devuelta por el analizador. Se crea entrada vacía 'counterparty_{key}'."
                    )
                    metrics[f"counterparty_{key}"] = pl.DataFrame()
        else:
            logger.warning(
                f"[analyzer.py:analyze] No se generaron métricas de contrapartes (el diccionario devuelto está vacío o es None)."
            )
            # Crear entradas vacías para todas las claves esperadas
            expected_cp_keys_for_plotting = [
                "general_stats",
                "temporal_evolution",
                "payment_preferences",
                "trading_patterns",
                "vip_counterparties",
                "efficiency_stats",
            ]
            for key in expected_cp_keys_for_plotting:
                logger.warning(
                    f"  Creando entrada vacía para métrica de contraparte esperada: 'counterparty_{key}'."
                )
                metrics[f"counterparty_{key}"] = pl.DataFrame()

        logger.info(
            f"[analyzer.py:analyze] Claves en 'metrics' DESPUÉS del procesamiento de contrapartes: {list(metrics.keys())}"
        )

    except Exception as e:
        logger.error(
            f"[analyzer.py:analyze] Error principal en el bloque de análisis de contrapartes: {e}"
        )
        logger.error(f"Tipo de error: {type(e)}")
        # Asegurar que las claves esperadas existan como DFs vacíos en caso de error grave
        expected_cp_keys_for_plotting = [
            "general_stats",
            "temporal_evolution",
            "payment_preferences",
            "trading_patterns",
            "vip_counterparties",
            "efficiency_stats",
        ]
        for key in expected_cp_keys_for_plotting:
            if f"counterparty_{key}" not in metrics:  # Solo añadir si no existe ya
                logger.error(
                    f"  Creando entrada vacía de emergencia para métrica de contraparte: 'counterparty_{key}'."
                )
                metrics[f"counterparty_{key}"] = pl.DataFrame()

    # --- NUEVO: Análisis de Sesiones de Trading ---
    logger.info("Iniciando análisis avanzado de sesiones de trading...")
    try:
        session_data = session_analyzer.analyze_trading_sessions(
            df_processed, session_gap_minutes=30
        )
        if session_data:
            # Agregar todas las métricas de sesiones al diccionario principal
            for key, value in session_data.items():
                metrics[f"session_{key}"] = value

            # Generar insights automáticos
            insights = session_analyzer.get_session_insights(session_data)
            metrics["session_insights"] = (
                pl.from_dicts([insights]) if insights else pl.DataFrame()
            )

            logger.info(
                f"Análisis de sesiones completado exitosamente. {len(session_data)} métricas generadas."
            )
        else:
            logger.warning("No se generaron métricas de sesiones")
    except Exception as e:
        logger.error(f"Error en análisis de sesiones: {e}")
        # Continuar con el análisis normal aunque falle el análisis de sesiones

    df_completed_for_sales_summary = pl.DataFrame()
    if status_col in df_processed.columns:
        df_completed_for_sales_summary = df_processed.filter(
            pl.col(status_col) == "Completed"
        ).clone()
        if df_completed_for_sales_summary.is_empty():
            logger.info("No hay operaciones 'Completed' para resumen de ventas.")
    else:
        logger.warning(f"Columna '{status_col}' no encontrada para resumen de ventas.")

    required_financial_cols_internal = [
        order_number_col,
        "Quantity_num",
        "TotalPrice_num",
        "TotalFee",
        "Price_num",
        asset_type_col,
        fiat_type_col,
    ]
    missing_cols_check = [
        col
        for col in required_financial_cols_internal
        if col not in df_processed.columns
    ]

    if missing_cols_check:
        logger.warning(
            f"Faltan columnas para métricas financieras: {missing_cols_check}. Algunas métricas estarán vacías."
        )
        metrics["asset_stats"] = pl.DataFrame()
        metrics["fiat_stats"] = pl.DataFrame()
        metrics["price_stats"] = pl.DataFrame()
        metrics["fees_stats"] = pl.DataFrame()
        metrics["monthly_fiat"] = pl.DataFrame()
    else:
        logger.info("Calculando asset_stats...")
        metrics["asset_stats"] = (
            df_processed.group_by([asset_type_col, order_type_col])
            .agg(
                [
                    pl.col(order_number_col).count().alias("operations"),
                    pl.col("Quantity_num").sum().alias("quantity"),
                    pl.col("TotalPrice_num").sum().alias("total_fiat"),
                    pl.col("TotalFee").sum().alias("total_fees"),
                ]
            )
            .sort("total_fiat", descending=True)
        )

        logger.info("Calculando fiat_stats...")
        metrics["fiat_stats"] = (
            df_processed.group_by([fiat_type_col, order_type_col])
            .agg(
                [
                    pl.col(order_number_col).count().alias("operations"),
                    pl.col("TotalPrice_num").sum().alias("total_fiat"),
                    pl.col("Price_num").mean().alias("avg_price"),
                    pl.col("TotalFee").sum().alias("total_fees"),
                ]
            )
            .sort("total_fiat", descending=True)
        )

        logger.info("Calculando price_stats...")
        if (
            not df_processed.is_empty()
            and fiat_type_col in df_processed.columns
            and "Price_num" in df_processed.columns
        ):
            metrics["price_stats"] = df_processed.group_by(fiat_type_col).agg(
                [
                    pl.col("Price_num").mean().alias("avg_price"),
                    pl.col("Price_num").median().alias("median_price"),
                    pl.col("Price_num").min().alias("min_price"),
                    pl.col("Price_num").max().alias("max_price"),
                    pl.col("Price_num").std().alias("std_price"),
                    pl.col("Price_num").quantile(0.25).alias("q1_price"),
                    pl.col("Price_num").quantile(0.75).alias("q3_price"),
                    (
                        pl.col("Price_num").quantile(0.75)
                        - pl.col("Price_num").quantile(0.25)
                    ).alias("iqr_price"),
                    pl.col("Price_num").quantile(0.01).alias("p1_price"),
                    pl.col("Price_num").quantile(0.99).alias("p99_price"),
                ]
            )
        else:
            logger.warning(
                f"No se pueden calcular price_stats. DataFrame vacío o faltan columnas."
            )
            metrics["price_stats"] = pl.DataFrame()

        logger.info("Calculando fees_stats...")
        if (
            not df_processed.is_empty()
            and asset_type_col in df_processed.columns
            and "TotalFee" in df_processed.columns
        ):
            metrics["fees_stats"] = (
                df_processed.group_by(asset_type_col)
                .agg(
                    [
                        pl.col("TotalFee").sum().alias("total_fees_collected"),
                        pl.col("TotalFee").mean().alias("avg_fee_per_op"),
                        pl.col("TotalFee")
                        .filter(pl.col("TotalFee") > 0)
                        .count()
                        .alias("num_ops_with_fees"),
                        pl.col("TotalFee").max().alias("max_fee"),
                    ]
                )
                .sort("total_fees_collected", descending=True)
            )
        else:
            logger.warning(
                f"No se pueden calcular fees_stats. DataFrame vacío o faltan columnas."
            )
            metrics["fees_stats"] = pl.DataFrame()

        logger.info("Calculando monthly_fiat...")
        if (
            not df_processed.is_empty()
            and "YearMonthStr" in df_processed.columns
            and fiat_type_col in df_processed.columns
            and "TotalPrice_num" in df_processed.columns
            and order_type_col in df_processed.columns
        ):
            monthly_summary = (
                df_processed.group_by(["YearMonthStr", fiat_type_col, order_type_col])
                .agg(pl.sum("TotalPrice_num").alias("sum_total_price"))
                .sort(["YearMonthStr", fiat_type_col, order_type_col])
            )

            try:
                metrics["monthly_fiat"] = monthly_summary.pivot(
                    values="sum_total_price",
                    index=["YearMonthStr", fiat_type_col],
                    on=order_type_col,
                    aggregate_function=None,
                ).fill_null(0)
            except Exception as e:
                logger.error(
                    f"Error al pivotar monthly_fiat: {e}. La tabla podría estar en formato largo."
                )
                metrics["monthly_fiat"] = monthly_summary
        else:
            logger.warning(
                f"No se pueden calcular monthly_fiat. DataFrame vacío o faltan columnas."
            )
            metrics["monthly_fiat"] = pl.DataFrame()

        # --- NUEVO: Cálculo de serie mensual de operaciones y volumen para serie acumulada ---
        logger.info("Calculando monthly_ops y monthly_volume para serie acumulada...")
        if (
            "YearMonthStr" in df_processed.columns
            and order_number_col in df_processed.columns
            and "TotalPrice_num" in df_processed.columns
        ):
            monthly_ops = (
                df_processed.group_by("YearMonthStr")
                .agg(pl.count(order_number_col).alias("monthly_ops"))
                .sort("YearMonthStr")
            )
            metrics["monthly_ops"] = monthly_ops
            monthly_volume = (
                df_processed.group_by("YearMonthStr")
                .agg(pl.sum("TotalPrice_num").alias("monthly_volume"))
                .sort("YearMonthStr")
            )
            metrics["monthly_volume"] = monthly_volume
        else:
            logger.warning(
                "No se pudo calcular monthly_ops/monthly_volume para serie acumulada; faltan columnas."
            )
            metrics["monthly_ops"] = pl.DataFrame()
            metrics["monthly_volume"] = pl.DataFrame()
        # --- FIN: Cálculo de serie mensual de operaciones y volumen para serie acumulada ---

    if status_col in df_processed.columns:
        metrics["status_counts"] = df_processed[status_col].value_counts()
    else:
        metrics["status_counts"] = pl.Series(dtype=pl.datatypes.UInt32).to_frame()

    if order_type_col in df_processed.columns:
        metrics["side_counts"] = df_processed[order_type_col].value_counts()
    else:
        metrics["side_counts"] = pl.Series(dtype=pl.datatypes.UInt32).to_frame()

    logger.info("Calculando Índice de Liquidez Efectiva (mean_qty/median_qty)...")
    if (
        "Quantity_num" in df_processed.columns
        and df_processed["Quantity_num"].null_count() < df_processed.height
    ):
        quantity_series = df_processed["Quantity_num"].drop_nulls()
        if not quantity_series.is_empty():
            mean_qty = quantity_series.mean()
            median_qty = quantity_series.median()

            if median_qty is not None and median_qty != 0 and mean_qty is not None:
                effective_liquidity_index = mean_qty / median_qty
                metrics["effective_liquidity_index"] = pl.DataFrame(
                    {
                        "index_value": [effective_liquidity_index],
                        "mean_quantity": [mean_qty],
                        "median_quantity": [median_qty],
                    }
                )
                logger.info(
                    f"Índice de Liquidez Efectiva calculado: {effective_liquidity_index:.4f} (Media: {mean_qty:.4f}, Mediana: {median_qty:.4f})"
                )
            else:
                logger.warning(
                    "No se puede calcular el Índice de Liquidez Efectiva: mediana es cero, nula o media es nula."
                )
                metrics["effective_liquidity_index"] = pl.DataFrame(
                    {
                        "index_value": [None],
                        "mean_quantity": [mean_qty],
                        "median_quantity": [median_qty],
                    }
                )
        else:
            logger.warning(
                "Columna 'Quantity_num' no tiene valores no nulos para calcular el índice de liquidez."
            )
            metrics["effective_liquidity_index"] = pl.DataFrame(
                {
                    "index_value": [None],
                    "mean_quantity": [mean_qty],
                    "median_quantity": [median_qty],
                }
            )
    else:
        logger.warning(
            "Columna 'Quantity_num' no encontrada o completamente nula. No se calculará el Índice de Liquidez Efectiva."
        )
        metrics["effective_liquidity_index"] = pl.DataFrame(
            {
                "index_value": [None],
                "mean_quantity": [mean_qty],
                "median_quantity": [median_qty],
            }
        )

    logger.info("Detectando Whale Trades (TotalPrice_num > mean + 3*std)...")
    if (
        "TotalPrice_num" in df_processed.columns
        and df_processed["TotalPrice_num"].is_not_null().any()
    ):
        mean_total_price = df_processed["TotalPrice_num"].mean()
        std_total_price = df_processed["TotalPrice_num"].std()
        if mean_total_price is not None and std_total_price is not None:
            whale_trade_threshold = mean_total_price + 3 * std_total_price
            df_processed = df_processed.with_columns(
                (pl.col("TotalPrice_num") > whale_trade_threshold).alias(
                    "is_whale_trade"
                )
            )
            whale_trades_count = df_processed.filter(pl.col("is_whale_trade")).height
            logger.info(
                f"Se detectaron {whale_trades_count} whale trades con umbral {whale_trade_threshold:.2f}."
            )
        else:
            logger.warning(
                "No se pudo calcular el umbral de whale trades (mean o std es nulo). Saltando detección."
            )
            df_processed = df_processed.with_columns(
                pl.lit(False).alias("is_whale_trade")
            )
    else:
        logger.warning(
            "Columna 'TotalPrice_num' no disponible o vacía para detección de Whale Trades. Saltando detección."
        )
        df_processed = df_processed.with_columns(pl.lit(False).alias("is_whale_trade"))

    logger.info("Analizando comparación Antes/Después de --event-date...")
    event_date_str = getattr(cli_args, "event_date", None) if cli_args else None
    if (
        event_date_str
        and "Match_time_local" in df_processed.columns
        and isinstance(df_processed.schema["Match_time_local"], pl.Datetime)
    ):
        try:
            event_date = datetime.strptime(event_date_str, "%Y-%m-%d").replace(
                tzinfo=df_processed["Match_time_local"].dtype.time_zone
            )
            df_before_event = df_processed.filter(
                pl.col("Match_time_local") < event_date
            )
            df_after_event = df_processed.filter(
                pl.col("Match_time_local") >= event_date
            )
            metrics["before_event_stats"] = df_before_event.select(
                pl.mean("TotalPrice_num").alias("avg_volume_before"),
                pl.count().alias("ops_before"),
            )
            metrics["after_event_stats"] = df_after_event.select(
                pl.mean("TotalPrice_num").alias("avg_volume_after"),
                pl.count().alias("ops_after"),
            )
            logger.info(
                f"Análisis Antes/Después de evento {event_date_str} completado."
            )
        except ValueError:
            logger.warning(
                f"Formato de --event-date '{event_date_str}' inválido. Use YYYY-MM-DD. Se omite análisis comparativo."
            )
        except Exception as e:
            logger.error(f"Error en análisis comparativo Antes/Después: {e}")
    else:
        if event_date_str:
            logger.info(
                f"--event-date '{event_date_str}' proporcionado, pero falta Match_time_local o no es Datetime. Se omite análisis comparativo."
            )
        else:
            logger.info(
                "--event-date no proporcionado. Se omite análisis comparativo Antes/Después."
            )

    logger.info("Iniciando Detección de Outliers (Isolation Forest) en Price_num...")
    detect_outliers_flag = (
        getattr(cli_args, "detect_outliers", False) if cli_args else False
    )
    if (
        detect_outliers_flag
        and "Price_num" in df_processed.columns
        and df_processed["Price_num"].is_not_null().any()
    ):
        contamination_param = (
            getattr(cli_args, "outliers_contamination", "auto") if cli_args else "auto"
        )
        n_estimators_param = (
            getattr(cli_args, "outliers_n_estimators", 100) if cli_args else 100
        )
        random_state_param = (
            getattr(cli_args, "outliers_random_state", 42) if cli_args else 42
        )

        logger.info(
            f"Parámetros de Isolation Forest: contamination={contamination_param}, n_estimators={n_estimators_param}, random_state={random_state_param}"
        )

        # Eliminar nulos y convertir a NumPy array para IsolationForest
        price_data_no_nulls = (
            df_processed.select(
                pl.col("Price_num").filter(pl.col("Price_num").is_not_null())
            )
            .to_numpy()
            .reshape(-1, 1)
        )

        if price_data_no_nulls.shape[0] > 0:
            try:
                iso_forest = IsolationForest(
                    contamination=contamination_param
                    if contamination_param != "auto"
                    else "auto",
                    n_estimators=n_estimators_param,
                    random_state=random_state_param,
                )
                outlier_preds = iso_forest.fit_predict(price_data_no_nulls)

                # Añadir predicciones al DataFrame original. Esto es un poco más complejo
                # porque necesitamos alinear las predicciones (que son solo para no nulos)
                # con el DataFrame original que puede tener nulos en Price_num.

                # 1. Crear un df temporal con los índices originales de los no nulos
                df_with_indices = df_processed.with_row_count("original_index")
                price_data_indices = df_with_indices.filter(
                    pl.col("Price_num").is_not_null()
                ).select(["original_index"])

                # 2. Crear df de predicciones con esos índices
                predictions_df = pl.DataFrame(
                    {
                        "original_index": price_data_indices["original_index"],
                        "is_outlier_price": (
                            outlier_preds == -1
                        ),  # -1 significa outlier
                    }
                )

                # 3. Unir de vuelta al df_processed
                df_processed = (
                    df_processed.with_row_count("original_index")
                    .join(predictions_df, on="original_index", how="left")
                    .with_columns(pl.col("is_outlier_price").fill_null(False))
                )  # Llenar nulos (donde Price_num era nulo) con False

                outliers_found = df_processed.filter(pl.col("is_outlier_price")).height
                logger.info(
                    f"Detección de Outliers completada. {outliers_found} outliers de precio identificados."
                )
            except Exception as e_iso:
                logger.error(
                    f"Error durante la detección de outliers con Isolation Forest: {e_iso}"
                )
                df_processed = df_processed.with_columns(
                    pl.lit(False).alias("is_outlier_price")
                )
        else:
            logger.info(
                "No hay datos de precio válidos (no nulos) para la detección de outliers."
            )
            df_processed = df_processed.with_columns(
                pl.lit(False).alias("is_outlier_price")
            )
    else:
        if not detect_outliers_flag:
            logger.info(
                "Detección de outliers no activada mediante argumento CLI (--detect_outliers)."
            )
        else:
            logger.info(
                "Columna 'Price_num' no disponible o todos sus valores son nulos. No se ejecutó la detección de outliers."
            )
        df_processed = df_processed.with_columns(
            pl.lit(False).alias("is_outlier_price")
        )

    logger.info("Análisis finalizado.")
    # --- Métricas de riesgo básicas a nivel de precio por fiat (si disponible) ---
    try:
        if "Match_time_local" in df_processed.columns and "Price_num" in df_processed.columns:
            # Serie diaria de precios agregada por fiat
            for fiat in ["USD", "UYU"]:
                df_fiat = df_processed.filter(pl.col("fiat_type") == fiat)
                if df_fiat.is_empty():
                    continue
                daily_prices = (
                    df_fiat
                    .with_columns(pl.col("Match_time_local").dt.date().alias("date"))
                    .group_by("date")
                    .agg(pl.mean("Price_num").alias("price"))
                    .sort("date")
                )
                if daily_prices.height < 3:
                    continue
                returns = calculate_daily_returns(daily_prices.get_column("price"))
                sharpe = calculate_sharpe_ratio(returns)
                sortino = calculate_sortino_ratio(returns)
                # Equity simple como producto de (1+r)
                one_plus = (1 + returns).cast(pl.Float64)
                equity = one_plus.cum_prod()
                max_dd = calculate_max_drawdown(equity)
                dd_series = compute_drawdown_series(equity)

                metrics[f"risk_{fiat.lower()}_daily_returns"] = pl.DataFrame({"date": daily_prices["date"], "return": returns})
                metrics[f"risk_{fiat.lower()}_drawdown_series"] = pl.DataFrame({"date": daily_prices["date"], "drawdown": dd_series})
                metrics[f"risk_{fiat.lower()}_summary"] = pl.DataFrame(
                    {
                        "metric": ["sharpe", "sortino", "max_drawdown"],
                        "value": [sharpe, sortino, max_dd],
                    }
                )
    except Exception as _e:
        logger.warning(f"No se pudieron calcular métricas de riesgo básicas: {_e}")

    return df_processed, metrics

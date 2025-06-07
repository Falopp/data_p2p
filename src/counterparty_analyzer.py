import polars as pl
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Union

logger = logging.getLogger(__name__)


def analyze_counterparties(df: pl.DataFrame) -> Dict[str, Union[pl.DataFrame, Any]]:
    """
    Análisis completo de comportamiento de contrapartes.

    Args:
        df: DataFrame con operaciones P2P procesadas

    Returns:
        Un diccionario donde las claves son nombres de métricas (ej. 'general_stats')
        y los valores son los DataFrames de Polars correspondientes.
    """
    logger.info("Iniciando análisis de contrapartes...")

    # Verificar columnas requeridas (actualizado para usar la columna correcta del CSV)
    required_cols = [
        "Counterparty",
        "TotalPrice_num",
        "Price_num",
        "Quantity_num",
        "Match_time_local",
        "payment_method",
        "status",
        "order_type",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]

    if missing_cols:
        logger.warning(f"Faltan columnas para análisis de contrapartes: {missing_cols}")
        return {}

    if df.is_empty():
        logger.warning("DataFrame vacío para análisis de contrapartes")
        return {}

    # Filtrar solo contrapartes válidas (no vacías)
    df_filtered = df.filter(
        (pl.col("Counterparty").is_not_null())
        & (pl.col("Counterparty") != "")
        & (pl.col("Counterparty").str.strip_chars() != "")
    )

    if df_filtered.is_empty():
        logger.warning("No hay contrapartes válidas para analizar")
        return {}

    logger.info(
        f"Analizando {df_filtered.height} operaciones con contrapartes válidas de {df.height} operaciones totales"
    )

    counterparty_metrics = {}

    # 1. Análisis general de contrapartes
    logger.info("Calculando métricas generales de contrapartes...")
    counterparty_metrics["general_stats"] = _calculate_general_counterparty_stats(
        df_filtered
    )

    # 2. Evolución temporal de contrapartes
    logger.info("Analizando evolución temporal de contrapartes...")
    counterparty_metrics["temporal_evolution"] = _analyze_temporal_evolution(
        df_filtered
    )

    # 3. Métodos de pago preferidos por contraparte
    logger.info("Analizando métodos de pago por contraparte...")
    counterparty_metrics["payment_preferences"] = _analyze_payment_preferences(
        df_filtered
    )

    # 4. Análisis de horarios de trading
    logger.info("Analizando patrones horarios de contrapartes...")
    counterparty_metrics["trading_patterns"] = _analyze_trading_patterns(df_filtered)

    # 5. Detección de contrapartes VIP
    logger.info("Identificando contrapartes VIP...")
    counterparty_metrics["vip_counterparties"] = _identify_vip_counterparties(
        df_filtered
    )

    # 6. Análisis de eficiencia por contraparte
    logger.info("Calculando eficiencia de contrapartes...")
    counterparty_metrics["efficiency_stats"] = _calculate_efficiency_stats(df_filtered)

    # 7. Matriz de actividad de contrapartes (NOTA: esta es series temporales, puede no unirse bien directamente)
    logger.info("Generando matriz de actividad...")
    # counterparty_metrics['activity_matrix'] = _generate_activity_matrix(df_filtered)
    # Comentado temporalmente ya que su estructura (Counterparty, year_month, ...) es diferente
    # y podría complicar el join directo. Considerar cómo integrarla o si debe permanecer separada.
    # Por ahora, la excluiremos del join automático.

    # logger.info("Análisis de sub-métricas de contrapartes completado. Iniciando consolidación final...") # Comentado

    # Consolidar todas las métricas en un único DataFrame
    # final_consolidated_df = None # Comentado

    # Lista de DataFrames a unir. Empezamos con el primero que no sea None y no esté vacío.
    # El orden puede importar si hay colisiones de nombres (aunque se deberían renombrar antes si es necesario).
    # Orden preferido: general_stats, trading_patterns, vip_counterparties, efficiency_stats

    # metric_keys_for_join = [ # Comentado
    #     'general_stats', # Comentado
    #     'trading_patterns', # trading_patterns ya debería tener 'Counterparty' # Comentado
    #     'vip_counterparties', # vip_counterparties se basa en general_stats, debería tener 'Counterparty' # Comentado
    #     'efficiency_stats' # efficiency_stats agrupa por 'Counterparty' # Comentado
    # ] # Comentado

    # # La métrica 'temporal_evolution' y 'payment_preferences' tienen granularidad diferente
    # # (Counterparty, year_month) y (Counterparty, payment_method) respectivamente.
    # # Estas no se unirán directamente en el DataFrame consolidado principal de contrapartes,
    # # sino que se devolverán por separado o se manejarán de otra forma.
    # # Por ahora, las mantendremos en el diccionario y no las uniremos.

    # # Devolveremos un diccionario: el DF consolidado principal y las métricas no unidas.
    # output_data = {}

    # for i, key in enumerate(metric_keys_for_join): # Comentado
    #     df_to_join = counterparty_metrics.get(key) # Comentado

    #     if df_to_join is None or df_to_join.is_empty(): # Comentado
    #         logger.warning(f"Métrica '{key}' está vacía o es None. Se omitirá del join consolidado.") # Comentado
    #         continue # Comentado

    #     if 'Counterparty' not in df_to_join.columns: # Comentado
    #         logger.error(f"Métrica '{key}' no tiene la columna 'Counterparty'. No se puede unir. Schema: {df_to_join.schema}") # Comentado
    #         continue # Comentado

    #     logger.info(f"Procesando para join: '{key}'. Schema: {df_to_join.schema}") # Comentado

    #     if final_consolidated_df is None: # Comentado
    #         final_consolidated_df = df_to_join # Comentado
    #         logger.info(f"DataFrame inicial para consolidación: '{key}'. Schema: {final_consolidated_df.schema}") # Comentado
    #     else: # Comentado
    #         try: # Comentado
    #             logger.info(f"Intentando unir con '{key}'. Schema de final_consolidated_df ANTES: {final_consolidated_df.schema}. Schema de df_to_join ('{key}'): {df_to_join.schema}") # Comentado

    #             # Renombrar columnas duplicadas (excepto 'Counterparty') antes del join # Comentado
    #             cols_in_final = set(final_consolidated_df.columns) # Comentado
    #             cols_in_current = set(df_to_join.columns) # Comentado
    #             duplicate_cols = (cols_in_final & cols_in_current) - {'Counterparty'} # Comentado

    #             if duplicate_cols: # Comentado
    #                 logger.warning(f"Columnas duplicadas encontradas al intentar unir '{key}': {duplicate_cols}. Se renombrarán en '{key}'.") # Comentado
    #                 rename_mapping = {col: f"{col}_{key[:3]}" for col in duplicate_cols} # Comentado
    #                 df_to_join = df_to_join.rename(rename_mapping) # Comentado
    #                 logger.info(f"'{key}' renombrado. Nuevo schema: {df_to_join.schema}") # Comentado

    #             final_consolidated_df = final_consolidated_df.join( # Comentado
    #                 df_to_join, # Comentado
    #                 on='Counterparty', # Comentado
    #                 how='outer' # Usar outer join para no perder contrapartes que puedan no estar en todas las métricas # Comentado
    #             ) # Comentado
    #             logger.info(f"Unión con '{key}' exitosa. Schema de final_consolidated_df DESPUÉS: {final_consolidated_df.schema}") # Comentado

    #             # >>> INICIO: Nueva lógica para manejar 'Counterparty_right' # Comentado
    #             if 'Counterparty_right' in final_consolidated_df.columns: # Comentado
    #                 logger.warning("Columna 'Counterparty_right' detectada después del join. Se eliminará, manteniendo la original 'Counterparty'.") # Comentado
    #                 # Primero, verificar si la columna original 'Counterparty' sigue siendo válida y no todos nulos si es posible # Comentado
    #                 # Esta verificación puede ser compleja, por ahora asumimos que 'Counterparty' es la correcta. # Comentado
    #                 final_consolidated_df = final_consolidated_df.drop('Counterparty_right') # Comentado
    #                 logger.info(f"Columna 'Counterparty_right' eliminada. Schema actual: {final_consolidated_df.schema}") # Comentado
    #             # <<< FIN: Nueva lógica para manejar 'Counterparty_right' # Comentado

    #         except Exception as e_join: # Comentado
    #             logger.error(f"Error al unir la métrica '{key}' al DataFrame consolidado: {e_join}") # Comentado
    #             logger.error(f"Schema de final_consolidated_df: {final_consolidated_df.schema}") # Comentado
    #             logger.error(f"Schema de df_to_join ('{key}'): {df_to_join.schema}") # Comentado
    #             # Podríamos decidir continuar sin esta métrica o detenernos. Por ahora, continuamos. # Comentado
    #             pass # Comentado

    # if final_consolidated_df is not None: # Comentado
    #     logger.info(f"Consolidación final de métricas de contrapartes completada. Schema final: {final_consolidated_df.schema}. Altura: {final_consolidated_df.height}") # Comentado
    # else: # Comentado
    #     logger.warning("El DataFrame consolidado final de contrapartes está vacío o es None.") # Comentado
    #     final_consolidated_df = pl.DataFrame() # Devolver un DF vacío si nada se pudo consolidar # Comentado

    # output_data['consolidated_metrics'] = final_consolidated_df

    # # Añadir métricas no unidas directamente al output
    # if counterparty_metrics.get('temporal_evolution') is not None:
    #     output_data['temporal_evolution'] = counterparty_metrics['temporal_evolution']
    # if counterparty_metrics.get('payment_preferences') is not None:
    #     output_data['payment_preferences'] = counterparty_metrics['payment_preferences']
    # if counterparty_metrics.get('activity_matrix') is not None: # Si se reactiva
    #    output_data['activity_matrix'] = counterparty_metrics['activity_matrix']

    # return output_data # Devolver el diccionario con el DF consolidado y otros separados
    # return final_consolidated_df # Devolver solo el DataFrame consolidado # Comentado

    logger.info(
        f"Análisis de contrapartes completado. Devolviendo diccionario de métricas: {list(counterparty_metrics.keys())}"
    )
    return counterparty_metrics  # Devolver el diccionario


def _calculate_general_counterparty_stats(df: pl.DataFrame) -> pl.DataFrame:
    """Estadísticas generales por contraparte."""
    return (
        df.group_by("Counterparty")
        .agg(
            [
                pl.count("Counterparty").alias("total_operations"),
                pl.sum("TotalPrice_num").alias("total_volume"),
                pl.mean("TotalPrice_num").alias("avg_volume_per_op"),
                pl.median("TotalPrice_num").alias("median_volume_per_op"),
                pl.sum("Quantity_num").alias("total_quantity"),
                pl.mean("Price_num").alias("avg_price"),
                pl.std("Price_num").alias("std_price"),
                pl.min("Match_time_local").alias("first_operation"),
                pl.max("Match_time_local").alias("last_operation"),
                pl.n_unique("payment_method").alias("payment_methods_used"),
                pl.n_unique("order_type").alias("operation_types"),
                # Calcular días activos
                (pl.max("Match_time_local") - pl.min("Match_time_local"))
                .dt.total_days()
                .alias("days_active"),
            ]
        )
        .with_columns(
            [
                # Calcular frecuencia de trading (operaciones por día)
                (pl.col("total_operations") / (pl.col("days_active") + 1)).alias(
                    "operations_per_day"
                ),
                # Calcular volumen por día
                (pl.col("total_volume") / (pl.col("days_active") + 1)).alias(
                    "volume_per_day"
                ),
                # Calcular coeficiente de variación del precio
                (pl.col("std_price") / pl.col("avg_price")).alias("price_cv"),
            ]
        )
        .sort("total_volume", descending=True)
    )


def _analyze_temporal_evolution(df: pl.DataFrame) -> pl.DataFrame:
    """Evolución temporal de actividad por contraparte."""
    return (
        df.with_columns(
            [pl.col("Match_time_local").dt.strftime("%Y-%m").alias("year_month")]
        )
        .group_by(["Counterparty", "year_month"])
        .agg(
            [
                pl.count("Counterparty").alias("monthly_operations"),
                pl.sum("TotalPrice_num").alias("monthly_volume"),
                pl.mean("TotalPrice_num").alias("avg_monthly_volume"),
                pl.n_unique("payment_method").alias("payment_methods_monthly"),
            ]
        )
        .sort(["Counterparty", "year_month"])
    )


def _analyze_payment_preferences(df: pl.DataFrame) -> pl.DataFrame:
    """Análisis de preferencias de métodos de pago por contraparte."""
    # Calcular estadísticas por contraparte y método de pago
    payment_stats = df.group_by(["Counterparty", "payment_method"]).agg(
        [
            pl.count("Counterparty").alias("operations_with_method"),
            pl.sum("TotalPrice_num").alias("volume_with_method"),
            pl.mean("TotalPrice_num").alias("avg_volume_with_method"),
        ]
    )

    # Calcular totales por contraparte para percentages
    counterparty_totals = df.group_by("Counterparty").agg(
        [
            pl.count("Counterparty").alias("total_operations_cp"),
            pl.sum("TotalPrice_num").alias("total_volume_cp"),
        ]
    )

    # Combinar y calcular porcentajes
    return (
        payment_stats.join(counterparty_totals, on="Counterparty")
        .with_columns(
            [
                (
                    pl.col("operations_with_method")
                    / pl.col("total_operations_cp")
                    * 100
                ).alias("pct_operations"),
                (pl.col("volume_with_method") / pl.col("total_volume_cp") * 100).alias(
                    "pct_volume"
                ),
            ]
        )
        .sort(["Counterparty", "pct_operations"], descending=[False, True])
    )


def _analyze_trading_patterns(df: pl.DataFrame) -> pl.DataFrame:
    """Análisis de patrones horarios y diarios de trading."""
    df_with_time_parts = df.with_columns(
        [
            pl.col("Match_time_local").dt.hour().alias("hour"),
            pl.col("Match_time_local")
            .dt.weekday()
            .alias("weekday"),  # Lunes=1, Domingo=7
        ]
    )

    # Log de diagnóstico para la columna 'weekday' cruda
    try:
        weekday_stats_raw = df_with_time_parts.group_by("Counterparty").agg(
            [
                pl.col("weekday").min().alias("min_weekday"),
                pl.col("weekday").max().alias("max_weekday"),
                pl.col("weekday").null_count().alias("null_weekday_count"),
                pl.col("weekday").is_not_null().sum().alias("valid_weekday_count"),
                pl.col("weekday")
                .value_counts(sort=True)
                .alias(
                    "weekday_value_counts_struct"
                ),  # Mantener como struct para inspección
            ]
        )
        # Para el log, convertir el struct a algo más simple si es necesario o loguear con cuidado.
        # Intentaremos loguear directamente; si causa problemas, se simplificará más.
        logger.info(
            f"Estadísticas de 'weekday' cruda por Counterparty (value_counts es un struct):\n{weekday_stats_raw}"
        )

        problematic_weekdays = weekday_stats_raw.filter(
            (pl.col("min_weekday") < 1)
            | (pl.col("max_weekday") > 7)
            | (
                (pl.col("null_weekday_count") > 0)
                & (pl.col("valid_weekday_count") == 0)
            )
        )
        if not problematic_weekdays.is_empty():
            logger.warning(
                f"ALERTA: Se encontraron valores de 'weekday' problemáticos (fuera de 1-7 o todos nulos) para algunas contrapartes:\n{problematic_weekdays}"
            )
    except Exception as e_log_wk:
        logger.error(f"Error al loguear estadísticas de 'weekday': {e_log_wk}")

    aggregated_patterns = df_with_time_parts.group_by(
        "Counterparty"
    ).agg(  # Agrupación directa por Counterparty
        [
            pl.col("hour")
            .filter(pl.col("hour").is_not_null())
            .mode()
            .first()
            .alias("most_active_hour"),
            # Dejar most_active_weekday como Int8 (0-7)
            pl.col("weekday")
            .filter(pl.col("weekday").is_not_null())
            .mode()
            .first()
            .fill_null(0)
            .cast(pl.Int8)
            .alias("most_active_weekday_int"),
            (
                pl.col("hour").filter(pl.col("hour").is_not_null()).max()
                - pl.col("hour").filter(pl.col("hour").is_not_null()).min()
            ).alias("hour_spread"),
            pl.struct(
                [
                    pl.col("hour").filter(pl.col("hour").is_not_null()),
                    pl.col("weekday").filter(pl.col("weekday").is_not_null()),
                ]
            )
            .alias("hour_weekday_struct")
            .drop_nulls()
            .n_unique()
            .alias("unique_hour_day_combinations"),
        ]
    )

    # Log de diagnóstico para 'most_active_weekday_int' antes del mapeo
    try:
        most_active_weekday_int_values = aggregated_patterns.select(
            ["Counterparty", "most_active_weekday_int"]
        ).drop_nulls("most_active_weekday_int")
        logger.info(
            f"Valores de 'most_active_weekday_int' (resultado del mode(), tipo Int8) antes del mapeo a nombres:\\n{most_active_weekday_int_values}"
        )

        problematic_int_modes = most_active_weekday_int_values.filter(
            (pl.col("most_active_weekday_int") < 0)
            | (pl.col("most_active_weekday_int") > 7)
        )
        if not problematic_int_modes.is_empty():
            logger.warning(
                f"ALERTA: Se encontraron valores de 'most_active_weekday_int' problemáticos (fuera de 0-7) DESPUÉS del mode():\\n{problematic_int_modes}"
            )

    except Exception as e_log_maw:
        logger.error(
            f"Error al loguear valores de 'most_active_weekday_int': {e_log_maw}"
        )

    # Asegurar que las columnas en aggregated_patterns tengan tipos simples antes del 'replace'
    try:
        logger.info(
            f"Schema de aggregated_patterns ANTES de casteo explícito: {aggregated_patterns.schema}"
        )
        aggregated_patterns = aggregated_patterns.select(
            [
                pl.col("Counterparty"),  # Debe ser String
                pl.col("most_active_hour")
                .cast(pl.Int32, strict=False)
                .alias("most_active_hour"),
                pl.col("most_active_weekday_int"),  # Ya es Int8
                pl.col("hour_spread").cast(pl.Int32, strict=False).alias("hour_spread"),
                pl.col("unique_hour_day_combinations")
                .cast(pl.UInt32, strict=False)
                .alias("unique_hour_day_combinations"),
            ]
        )
        logger.info(
            f"Schema de aggregated_patterns DESPUÉS de casteo explícito y re-select: {aggregated_patterns.schema}"
        )
    except Exception as e_cast:
        logger.error(
            f"Error durante el casteo explícito de aggregated_patterns: {e_cast}"
        )
        # Si el casteo falla, es probable que aquí esté el problema original.
        # Devolvemos el DataFrame original para que el error principal siga ocurriendo donde estaba.
        pass  # Continuar con el aggregated_patterns original si el casteo falla, para no ocultar el error principal.

    # Mapear 'most_active_weekday_int' (entero 0-7) a nombres de días
    # int_weekday_map = {
    #     1: pl.lit('Lunes'),
    #     2: pl.lit('Martes'),
    #     3: pl.lit('Miércoles'),
    #     4: pl.lit('Jueves'),
    #     5: pl.lit('Viernes'),
    #     6: pl.lit('Sábado'),
    #     7: pl.lit('Domingo'),
    #     0: pl.lit('Desconocido (sin moda)') # Corresponde al fill_null(0)
    # }

    try:
        unique_values_in_problem_col = (
            aggregated_patterns.select(
                pl.col("most_active_weekday_int").unique().sort()
            )
            .to_series()
            .to_list()
        )
        logger.info(
            f"Valores únicos en 'most_active_weekday_int' justo antes de mapeo when/then: {unique_values_in_problem_col}"
        )
        logger.info(
            f"Tipo de la columna 'most_active_weekday_int': {aggregated_patterns.get_column('most_active_weekday_int').dtype}"
        )

        # Mapeo usando when/then/otherwise
        weekday_name_expr = (
            pl.when(pl.col("most_active_weekday_int") == 1)
            .then(pl.lit("Lunes"))
            .when(pl.col("most_active_weekday_int") == 2)
            .then(pl.lit("Martes"))
            .when(pl.col("most_active_weekday_int") == 3)
            .then(pl.lit("Miércoles"))
            .when(pl.col("most_active_weekday_int") == 4)
            .then(pl.lit("Jueves"))
            .when(pl.col("most_active_weekday_int") == 5)
            .then(pl.lit("Viernes"))
            .when(pl.col("most_active_weekday_int") == 6)
            .then(pl.lit("Sábado"))
            .when(pl.col("most_active_weekday_int") == 7)
            .then(pl.lit("Domingo"))
            .when(pl.col("most_active_weekday_int") == 0)
            .then(pl.lit("Desconocido (sin moda)"))
            .otherwise(
                pl.lit("FALLO_MAPEO_OTHERWISE")
            )  # Default para valores inesperados
            .cast(pl.String)  # Asegurar que la columna final sea String
            .alias("most_active_weekday_name")
        )

        logger.info(
            "Expresión para 'most_active_weekday_name' (con when/then) creada. Intentando aplicarla con with_columns..."
        )

        result_df = aggregated_patterns.with_columns(weekday_name_expr)
        logger.info(
            f"Columna 'most_active_weekday_name' (con when/then) añadida exitosamente. Schema resultante: {result_df.schema}"
        )
        return result_df

    except Exception as e_whenthen_detailed:
        logger.error(
            f"ERROR DETALLADO durante when/then o al añadir columna 'most_active_weekday_name': {e_whenthen_detailed}"
        )
        logger.error(
            f"Tipo de error detallado (when/then): {type(e_whenthen_detailed)}"
        )
        logger.warning(
            "Devolviendo aggregated_patterns SIN 'most_active_weekday_name' debido a error en su creación (when/then)."
        )
        return aggregated_patterns


def _identify_vip_counterparties(df: pl.DataFrame) -> pl.DataFrame:
    """Identificación de contrapartes VIP basada en múltiples criterios."""
    # Calcular estadísticas base
    base_stats = _calculate_general_counterparty_stats(df)

    if base_stats.is_empty():
        return pl.DataFrame()

    # Calcular percentiles para clasificación
    volume_p75 = base_stats["total_volume"].quantile(0.75)
    volume_p90 = base_stats["total_volume"].quantile(0.90)
    operations_p75 = base_stats["total_operations"].quantile(0.75)
    operations_p90 = base_stats["total_operations"].quantile(0.90)

    return (
        base_stats.with_columns(
            [
                # Criterios VIP
                (pl.col("total_volume") >= volume_p90).alias("high_volume_vip"),
                (pl.col("total_operations") >= operations_p90).alias(
                    "high_frequency_vip"
                ),
                (pl.col("operations_per_day") >= 2.0).alias("daily_trader"),
                (pl.col("days_active") >= 30).alias("long_term_trader"),
                # Scoring VIP (0-100)
                (
                    # 40% peso en volumen
                    (pl.col("total_volume") / volume_p90 * 40).clip(0, 40)
                    +
                    # 30% peso en frecuencia
                    (pl.col("total_operations") / operations_p90 * 30).clip(0, 30)
                    +
                    # 20% peso en consistencia (días activos)
                    (pl.col("days_active") / 365 * 20).clip(0, 20)
                    +
                    # 10% peso en diversidad de métodos de pago
                    (pl.col("payment_methods_used") / 5 * 10).clip(0, 10)
                ).alias("vip_score"),
            ]
        )
        .with_columns(
            [
                # Clasificación VIP
                pl.when(pl.col("vip_score") >= 80)
                .then(pl.lit("Diamond"))
                .when(pl.col("vip_score") >= 60)
                .then(pl.lit("Gold"))
                .when(pl.col("vip_score") >= 40)
                .then(pl.lit("Silver"))
                .when(pl.col("vip_score") >= 20)
                .then(pl.lit("Bronze"))
                .otherwise(pl.lit("Standard"))
                .alias("vip_tier")
            ]
        )
        .sort("vip_score", descending=True)
    )


def _calculate_efficiency_stats(df: pl.DataFrame) -> pl.DataFrame:
    """Métricas de eficiencia por contraparte."""
    return (
        df.group_by("Counterparty")
        .agg(
            [
                pl.count("Counterparty").alias("total_ops"),
                # Tasa de completitud
                (
                    pl.col("status").filter(pl.col("status") == "Completed").count()
                    / pl.count("Counterparty")
                    * 100
                ).alias("completion_rate"),
                # Tasa de cancelación
                (
                    pl.col("status")
                    .filter(pl.col("status").str.contains("Cancel"))
                    .count()
                    / pl.count("Counterparty")
                    * 100
                ).alias("cancellation_rate"),
                # Variabilidad en tiempos (si tienes timestamps)
                pl.col("Match_time_local")
                .diff()
                .dt.total_hours()
                .std()
                .alias("timing_variability_hours"),
                # Consistencia en volúmenes
                (pl.std("TotalPrice_num") / pl.mean("TotalPrice_num")).alias(
                    "volume_consistency"
                ),
            ]
        )
        .with_columns(
            [
                # Score de eficiencia (0-100)
                (
                    pl.col("completion_rate") * 0.5
                    + (100 - pl.col("cancellation_rate"))  # 50% peso en completitud
                    * 0.3
                    + (  # 30% peso en no cancelación
                        100 - pl.col("volume_consistency").clip(0, 100)
                    )
                    * 0.2  # 20% peso en consistencia
                ).alias("efficiency_score")
            ]
        )
        .sort("efficiency_score", descending=True)
    )


def _generate_activity_matrix(df: pl.DataFrame) -> pl.DataFrame:
    """Matriz de actividad mensual por contraparte."""
    return (
        df.with_columns(
            [pl.col("Match_time_local").dt.strftime("%Y-%m").alias("year_month")]
        )
        .group_by(["Counterparty", "year_month"])
        .agg(
            [
                pl.count("Counterparty").alias("activity_count"),
                pl.sum("TotalPrice_num").alias("activity_volume"),
            ]
        )
        .sort(["Counterparty", "year_month"])
    )


def get_counterparty_insights(counterparty_df: pl.DataFrame) -> Dict[str, Any]:
    """
    Genera insights automáticos basados en el análisis de contrapartes consolidado.

    Args:
        counterparty_df: DataFrame consolidado del análisis de contrapartes

    Returns:
        Diccionario con insights textuales y numéricos
    """
    insights = {}

    if counterparty_df is None or counterparty_df.is_empty():
        return {
            "error": "No hay datos consolidados de contrapartes para generar insights"
        }

    # Asumiendo que 'total_volume' y 'total_operations' están en el DF consolidado
    # y que 'vip_tier' también (si vip_counterparties se unió correctamente)

    insights["total_counterparties"] = counterparty_df.height

    # Para top_counterparty, necesitamos ordenar por una métrica clave, ej. 'total_volume'
    # Asegurarse que la columna existe antes de usarla
    if "total_volume" in counterparty_df.columns:
        insights["top_counterparty_by_volume"] = counterparty_df.sort(
            "total_volume", descending=True
        ).row(0, named=True)
        total_volume_sum = counterparty_df["total_volume"].sum()
        if total_volume_sum is not None and total_volume_sum > 0:
            top_10_df = counterparty_df.sort("total_volume", descending=True).head(10)
            top_10_volume_sum = top_10_df["total_volume"].sum()
            insights["top_10_volume_concentration_pct"] = (
                (top_10_volume_sum / total_volume_sum * 100)
                if total_volume_sum > 0
                else 0
            )
        else:
            insights["top_10_volume_concentration_pct"] = 0
    else:
        insights["top_counterparty_by_volume"] = "N/A (total_volume no encontrado)"
        insights["top_10_volume_concentration_pct"] = "N/A (total_volume no encontrado)"

    if "vip_tier" in counterparty_df.columns:
        insights["vip_breakdown"] = (
            counterparty_df.group_by("vip_tier")
            .agg(pl.count().alias("count"))
            .to_dict(as_series=False)
        )

    if "total_operations" in counterparty_df.columns:
        insights["avg_operations_per_counterparty"] = counterparty_df[
            "total_operations"
        ].mean()

    return insights

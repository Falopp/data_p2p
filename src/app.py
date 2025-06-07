#!/usr/bin/env python3
"""Punto de entrada CLI y orquestador principal para el análisis de operaciones P2P.

Este script maneja la carga de datos desde un archivo CSV, aplica filtros iniciales
basados en argumentos de línea de comandos, realiza un pre-procesamiento básico
(como la generación de columnas de fecha) y luego invoca el pipeline de análisis
detallado.

Ejemplo de uso:
    python src/app.py --csv data/p2p.csv --out output_directorio

Módulos requeridos:
    - analyzer: Funciones de análisis principal
    - config_loader: Carga de configuración
    - main_logic: Pipeline de análisis y inicialización
    - unified_reporter: Reporte unificado
"""
from __future__ import annotations

import argparse
import logging
import os
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

import polars as pl
import polars.exceptions

from .analyzer import analyze
from .config_loader import load_config
from .main_logic import initialize_analysis, execute_analysis
from .unified_reporter import UnifiedReporter

import datetime

# Configuración de logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constantes de nombres de columnas internas
INTERNAL_FIAT_COLUMN = "fiat_type"
INTERNAL_ASSET_COLUMN = "asset_type"
INTERNAL_STATUS_COLUMN = "status"
INTERNAL_PAYMENT_METHOD_COLUMN = "payment_method"

# Definición de las categorías principales de análisis
MAIN_CATEGORIES = {
    "General": {
        "filters": {},  # No aplica filtros adicionales
        "output_folder": "",  # Sin subcarpeta para categoría General
    }
    # Se podrían añadir más categorías aquí en el futuro si es necesario, por ejemplo:
    # "Solo_USD": {
    # "filters": {"fiat_type": ["USD"]},
    # "output_folder": "Solo_USD_Analysis"
    # },
}


def _load_csv_with_schema_override(
    csv_path: str, column_map_config: Dict[str, str]
) -> pl.DataFrame:
    """Carga el archivo CSV con override de esquema para columnas específicas.

    Args:
        csv_path: Ruta al archivo CSV
        column_map_config: Mapeo de columnas de configuración

    Returns:
        DataFrame de Polars con los datos cargados

    Raises:
        FileNotFoundError: Si el archivo CSV no existe
        polars.exceptions.NoDataError: Si el CSV está vacío
        polars.exceptions.SchemaError: Si hay problemas de esquema
        polars.exceptions.ComputeError: Si hay errores de cómputo de Polars
    """
    csv_order_number_col = column_map_config.get("order_number", "Order Number")
    csv_adv_order_number_col = column_map_config.get(
        "adv_order_number", "Advertisement Order Number"
    )

    csv_column_types_override: Dict[str, Any] = {
        csv_order_number_col: pl.String,
        csv_adv_order_number_col: pl.String,
    }

    raw_df = pl.read_csv(
        source=csv_path,
        infer_schema_length=10000,
        null_values=["", "NA", "N/A", "NaN", "null"],
        schema_overrides=csv_column_types_override,
    )

    logger.info(
        f"Datos cargados exitosamente: {raw_df.shape[0]} filas, "
        f"{raw_df.shape[1]} columnas."
    )
    return raw_df


def _rename_columns_from_config(
    df: pl.DataFrame, column_map_config: Dict[str, str]
) -> pl.DataFrame:
    """Renombra las columnas del DataFrame según la configuración.

    Args:
        df: DataFrame a procesar
        column_map_config: Mapeo de nombres de columnas

    Returns:
        DataFrame con columnas renombradas
    """
    column_rename_map: Dict[str, str] = {
        csv_col_name: script_col_name
        for script_col_name, csv_col_name in column_map_config.items()
        if (
            csv_col_name
            and csv_col_name in df.columns
            and csv_col_name != script_col_name
        )
    }

    if column_rename_map:
        df = df.rename(column_rename_map)
        logger.info(f"Columnas renombradas: {column_rename_map}")

    return df


def _apply_fiat_filter(df: pl.DataFrame, fiat_filters: List[str]) -> pl.DataFrame:
    """Aplica filtros de tipo FIAT al DataFrame.

    Args:
        df: DataFrame a filtrar
        fiat_filters: Lista de tipos FIAT a incluir

    Returns:
        DataFrame filtrado
    """
    if not fiat_filters or INTERNAL_FIAT_COLUMN not in df.columns:
        return df

    processed_filters = [f.strip().upper() for f in fiat_filters]
    filtered_df = df.filter(
        pl.col(INTERNAL_FIAT_COLUMN)
        .str.to_uppercase()
        .str.strip_chars()
        .is_in(processed_filters)
    )
    logger.info(f"Filtro por FIAT aplicado: {processed_filters}")
    return filtered_df


def _apply_asset_filter(df: pl.DataFrame, asset_filters: List[str]) -> pl.DataFrame:
    """Aplica filtros de tipo Asset al DataFrame.

    Args:
        df: DataFrame a filtrar
        asset_filters: Lista de tipos de asset a incluir

    Returns:
        DataFrame filtrado
    """
    if not asset_filters or INTERNAL_ASSET_COLUMN not in df.columns:
        return df

    processed_filters = [a.strip().upper() for a in asset_filters]
    filtered_df = df.filter(
        pl.col(INTERNAL_ASSET_COLUMN)
        .str.to_uppercase()
        .str.strip_chars()
        .is_in(processed_filters)
    )
    logger.info(f"Filtro por Asset aplicado: {processed_filters}")
    return filtered_df


def _apply_status_filter(df: pl.DataFrame, status_filters: List[str]) -> pl.DataFrame:
    """Aplica filtros de estado al DataFrame.

    Args:
        df: DataFrame a filtrar
        status_filters: Lista de estados a incluir

    Returns:
        DataFrame filtrado
    """
    if not status_filters or INTERNAL_STATUS_COLUMN not in df.columns:
        return df

    processed_filters = [s.strip().capitalize() for s in status_filters]
    filtered_df = df.filter(
        pl.col(INTERNAL_STATUS_COLUMN)
        .str.to_titlecase()
        .str.strip_chars()
        .is_in(processed_filters)
    )
    logger.info(f"Filtro por Status aplicado: {processed_filters}")
    return filtered_df


def _apply_payment_method_filter(
    df: pl.DataFrame, payment_method_filters: List[str]
) -> pl.DataFrame:
    """Aplica filtros de método de pago al DataFrame.

    Args:
        df: DataFrame a filtrar
        payment_method_filters: Lista de métodos de pago a incluir

    Returns:
        DataFrame filtrado
    """
    if not payment_method_filters or INTERNAL_PAYMENT_METHOD_COLUMN not in df.columns:
        return df

    filtered_df = df.filter(
        pl.col(INTERNAL_PAYMENT_METHOD_COLUMN).is_in(payment_method_filters)
    )
    logger.info(f"Filtro por Payment Method aplicado: {payment_method_filters}")
    return filtered_df


def _apply_month_filter(
    df: pl.DataFrame, month_number: int, month_name: str
) -> pl.DataFrame:
    """Aplica filtro de mes específico al DataFrame.

    Args:
        df: DataFrame a filtrar
        month_number: Número del mes (1-12)
        month_name: Nombre del mes para logging

    Returns:
        DataFrame filtrado por el mes especificado
    """
    if "Match_time_local" not in df.columns:
        logger.warning(
            f"Columna 'Match_time_local' no encontrada. "
            f"No se puede aplicar filtro de mes {month_name}."
        )
        return df

    try:
        # Asegurarse que la columna de fecha es de tipo Datetime
        if not isinstance(df["Match_time_local"].dtype, pl.Datetime):
            logger.warning(
                f"Columna 'Match_time_local' no es de tipo Datetime. "
                f"Intentando conversión para filtro de mes {month_name}."
            )
            # Intentar convertirla, asumiendo un formato común si es string.
            # Esta es una solución temporal. Idealmente, el preprocesamiento asegura el tipo correcto.
            try:
                df = df.with_columns(
                    pl.col("Match_time_local").str.to_datetime(
                        format="%Y-%m-%d %H:%M:%S%.f",
                        strict=False,  # Ajusta el formato si es necesario
                    )
                )
            except polars.exceptions.ComputeError as e:
                logger.error(
                    f"Error convirtiendo 'Match_time_local' a Datetime: {e}. "
                    f"No se aplicará filtro de mes."
                )
                return df

        filtered_df = df.filter(pl.col("Match_time_local").dt.month() == month_number)
        logger.info(f"Filtro por mes aplicado: {month_name} ({month_number})")
        return filtered_df

    except Exception as e:  # Captura errores más generales durante el filtrado
        logger.error(
            f"Error inesperado aplicando filtro de mes {month_name}: {e}. "
            f"No se aplicará el filtro."
        )
        return df


def _load_and_preprocess_input_data(
    cli_args: argparse.Namespace,
    column_map_config: Dict[str, str],
    current_category_filters: Dict[str, Any],
    config: Dict[str, Any],
) -> Optional[pl.DataFrame]:
    """Carga, renombra y filtra inicialmente el DataFrame basado en argumentos CLI.

    También realiza un pre-procesamiento básico como la conversión de la columna
    de fecha/hora a un tipo de dato temporal local.

    Args:
        cli_args: Argumentos parseados de la línea de comandos.
        column_map_config: Mapeo de nombres de columnas desde la config.
        current_category_filters: Filtros específicos para la categoría actual
        config: Configuración general del análisis

    Returns:
        Un DataFrame de Polars procesado o None si ocurre un error crítico.
    """
    logger.info(f"Iniciando carga de datos desde CSV: {cli_args.csv}")
    try:
        raw_df = _load_csv_with_schema_override(cli_args.csv, column_map_config)
    except FileNotFoundError:
        logger.error(f"Archivo CSV no encontrado en la ruta: {cli_args.csv}")
        return None
    except polars.exceptions.NoDataError:
        logger.error(f"El archivo CSV está vacío: {cli_args.csv}")
        return None
    except (polars.exceptions.SchemaError, polars.exceptions.ComputeError) as e:
        logger.error(f"Error de Polars al cargar o procesar el CSV: {e}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al cargar el CSV: {e}")
        return None

    if raw_df.is_empty():
        logger.warning(
            "El DataFrame está vacío después de la carga. No hay datos para analizar."
        )
        return raw_df

    df_renamed = _rename_columns_from_config(raw_df, column_map_config)

    # Aplicar filtros básicos existentes
    if cli_args.fiat_filter:
        df_renamed = _apply_fiat_filter(df_renamed, cli_args.fiat_filter)
    if cli_args.asset_filter:
        df_renamed = _apply_asset_filter(df_renamed, cli_args.asset_filter)
    if cli_args.status_filter:
        df_renamed = _apply_status_filter(df_renamed, cli_args.status_filter)
    if cli_args.payment_method_filter:
        df_renamed = _apply_payment_method_filter(
            df_renamed, cli_args.payment_method_filter
        )

    # --- Procesamiento de Columnas de Tiempo ---
    logger.info("Iniciando procesamiento de columnas de tiempo con Polars...")
    time_cols_created_or_verified = []
    match_time_utc_col_internal = "match_time_utc"  # Nombre interno post-renombrado

    if match_time_utc_col_internal in df_renamed.columns:
        logger.info(
            f"Generando columnas de tiempo a partir de '{match_time_utc_col_internal}'."
        )
        try:
            # Primero, intentar la conversión directa si ya es datetime o un formato reconocido
            if not isinstance(
                df_renamed[match_time_utc_col_internal].dtype, pl.Datetime
            ):
                df_renamed = df_renamed.with_columns(
                    pl.col(match_time_utc_col_internal)
                    .str.to_datetime(
                        format="%Y-%m-%d %H:%M:%S",
                        strict=True,  # Formato esperado del CSV
                    )
                    .alias("Match_time_utc_dt_naive")
                )
            else:  # Si ya es datetime, solo clonarla para mantener consistencia
                df_renamed = df_renamed.with_columns(
                    pl.col(match_time_utc_col_internal).alias("Match_time_utc_dt_naive")
                )

            # Proceder con la zona horaria y otras derivaciones
            df_renamed = df_renamed.with_columns(
                [
                    pl.col("Match_time_utc_dt_naive")
                    .dt.replace_time_zone("UTC")
                    .alias("Match_time_utc_dt")
                ]
            )

            uy_tz = "America/Montevideo"
            df_renamed = df_renamed.with_columns(
                [
                    pl.col("Match_time_utc_dt")
                    .dt.convert_time_zone(uy_tz)
                    .alias("Match_time_local"),
                ]
            )

            df_renamed = df_renamed.with_columns(
                [
                    pl.col("Match_time_local").dt.hour().alias("hour_local"),
                    pl.col("Match_time_local")
                    .dt.strftime("%Y-%m")
                    .alias("YearMonthStr"),
                    pl.col("Match_time_local").dt.year().alias("Year"),
                    pl.col("Match_time_local")
                    .dt.weekday()
                    .alias("weekday_local"),  # Lunes=1, Domingo=7
                    pl.col("Match_time_local").dt.date().alias("date_local"),
                ]
            ).drop("Match_time_utc_dt_naive")

            initial_rows = df_renamed.height
            # Es crucial dropear nulos DESPUÉS de la conversión a Match_time_local y no antes
            # o sobre una columna intermedia que podría fallar para todas las filas.
            df_renamed = df_renamed.drop_nulls(subset=["Match_time_local"])
            rows_dropped = initial_rows - df_renamed.height
            if rows_dropped > 0:
                logger.warning(
                    f"Filas eliminadas debido a valores nulos/inválidos en fechas después de la conversión: {rows_dropped}"
                )

            if df_renamed.height > 0:
                time_cols_created_or_verified.extend(
                    [
                        "Match_time_utc_dt",
                        "Match_time_local",
                        "hour_local",
                        "YearMonthStr",
                        "Year",
                        "weekday_local",
                        "date_local",
                    ]
                )
            else:
                logger.error(
                    "El DataFrame quedó vacío después del procesamiento de fechas y drop_nulls. Verifica la calidad de los datos de fecha en el CSV."
                )
                return None  # DataFrame vacío, no se puede continuar

        except (
            Exception
        ) as e_time_proc:  # Captura más genérica para errores de conversión
            logger.error(
                f"Error crítico durante el procesamiento de la columna '{match_time_utc_col_internal}': {e_time_proc}. No se pueden generar columnas de tiempo."
            )
            # Si falla la conversión de tiempo, es mejor devolver None para que el script se detenga controladamente.
            return None
    else:
        logger.warning(
            f"Columna de tiempo original '{match_time_utc_col_internal}' no encontrada. "
            f"No se crearán columnas de tiempo derivadas. El análisis puede ser limitado."
        )
        # Considerar si devolver None o df aquí. Si las fechas son cruciales, mejor None.
        return None

    if time_cols_created_or_verified:
        logger.info(
            f"Columnas de tiempo procesadas/verificadas: {', '.join(time_cols_created_or_verified)}."
        )
    logger.info("Procesamiento de columnas de tiempo completado.")
    # --- Fin Procesamiento de Columnas de Tiempo ---

    # Filtro de mes (después de que Match_time_local se haya creado)
    if cli_args.mes:
        month_name_or_num = cli_args.mes.lower()
        month_number = initialize_analysis.MONTH_NAMES_MAP.get(month_name_or_num)
        if not month_number:
            try:
                month_number = int(month_name_or_num)
                if not 1 <= month_number <= 12:
                    logger.warning(
                        f"Número de mes '{month_name_or_num}' inválido. Se ignora filtro de mes."
                    )
                    month_number = None
            except ValueError:
                logger.warning(
                    f"Nombre de mes '{month_name_or_num}' no reconocido. Se ignora filtro de mes."
                )
                month_number = None

        if month_number:
            df_renamed = _apply_month_filter(df_renamed, month_number, cli_args.mes)

    # Se eliminan las llamadas a los nuevos filtros avanzados

    logger.info(
        f"Carga y filtrado completados. DataFrame resultante: {df_renamed.shape[0]} filas."
    )
    return df_renamed


def main() -> None:
    """Punto de entrada principal del script."""
    args, clean_filename_suffix_cli, analysis_title_suffix_cli = initialize_analysis()
    logger.error(f"CRITICAL_APP_DEBUG_MAIN_START: Args parseados: {args}")
    logger.info(
        f"CRITICAL_APP_DEBUG_MAIN_START: clean_filename_suffix_cli: {clean_filename_suffix_cli}"
    )
    logger.info(
        f"CRITICAL_APP_DEBUG_MAIN_START: analysis_title_suffix_cli: {analysis_title_suffix_cli}"
    )

    output_dir_base = Path(args.out)
    try:
        output_dir_base.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directorio de salida base verificado/creado: {output_dir_base}")
    except Exception as e:
        logger.error(
            f"No se pudo crear el directorio de salida base {output_dir_base}: {e}"
        )
        return

    logger.info(f"Directorio de salida principal: {args.out}")
    logger.info(f"Archivo CSV de entrada: {args.csv}")

    config_path = args.config if hasattr(args, "config") else None
    config = load_config(config_path)
    column_map_config = config.get("column_mapping", {})

    if args.unified_only:
        logger.info("Ejecutando en modo --unified-only.")
        logger.info(
            "Cargando y preprocesando datos para el reporte unificado global..."
        )
        df_full_processed = _load_and_preprocess_input_data(
            args, column_map_config, {}, config
        )
        if df_full_processed is not None and not df_full_processed.is_empty():
            logger.info(
                f"Datos cargados para unificado global. Shape: {df_full_processed.shape}"
            )
            # Para unified_only, el output_dir es directamente la base.
            # Necesitamos construir all_period_data para generate_unified_report
            # Esto es un placeholder, la lógica real de _execute_unified_only_analysis se movió/integró.
            # Esta rama de unified_only necesita ser revisada si se va a usar extensivamente.
            # Por ahora, asumimos que si unified_only=True, main_logic.execute_analysis no se llama,
            # y alguna otra función debería manejar la generación del reporte unificado.
            # O, que execute_analysis se llame con flags especiales.
            # La implementación actual de UnifiedReporter espera "all_period_data"
            # que es un dict complejo que execute_analysis construye.
            # TEMPORALMENTE: Para evitar error, si es unified_only, creamos el reporte unificado
            # de forma simplificada o indicamos que se necesita implementar.
            logger.warning(
                "La lógica completa para --unified-only y la recolección de datos para generate_unified_report necesita revisión."
            )
            logger.warning(
                "Intentando generar reporte unificado solo con datos totales..."
            )

            # Simulación de all_period_data para el reporte unificado en modo --unified-only
            # Se asume que el df_full_processed contiene todos los datos sin filtrar por categoría.
            # Y que el reporte unificado procesará los años internamente si es necesario.
            all_period_data_for_unified_only = {
                "total": {
                    "todas": df_full_processed.clone(),
                    "completadas": df_full_processed.filter(
                        pl.col(INTERNAL_STATUS_COLUMN) == "Completed"
                    ).clone()
                    if INTERNAL_STATUS_COLUMN in df_full_processed.columns
                    else pl.DataFrame(),
                    "canceladas": df_full_processed.filter(
                        pl.col(INTERNAL_STATUS_COLUMN) == "Cancelled"
                    ).clone()
                    if INTERNAL_STATUS_COLUMN in df_full_processed.columns
                    else pl.DataFrame(),
                }
            }
            if (
                hasattr(args, "no_annual_breakdown")
                and not args.no_annual_breakdown
                and "Year" in df_full_processed.columns
            ):
                # Si hay desglose anual y la columna Year existe, popular también por años
                available_years_unified = sorted(
                    [
                        str(y)
                        for y in df_full_processed.select(pl.col("Year").unique())
                        .drop_nulls()
                        .to_series()
                        .to_list()
                        if isinstance(y, int) and not isinstance(y, bool)
                    ]
                )
                for year_str in available_years_unified:
                    df_year_specific = df_full_processed.filter(
                        pl.col("Year") == int(year_str)
                    )
                    all_period_data_for_unified_only[year_str] = {
                        "todas": df_year_specific.clone(),
                        "completadas": df_year_specific.filter(
                            pl.col(INTERNAL_STATUS_COLUMN) == "Completed"
                        ).clone()
                        if INTERNAL_STATUS_COLUMN in df_year_specific.columns
                        else pl.DataFrame(),
                        "canceladas": df_year_specific.filter(
                            pl.col(INTERNAL_STATUS_COLUMN) == "Cancelled"
                        ).clone()
                        if INTERNAL_STATUS_COLUMN in df_year_specific.columns
                        else pl.DataFrame(),
                    }

            reporter_unificado = UnifiedReporter(str(output_dir_base), config, args)
            reporter_unificado.generate_unified_report(all_period_data_for_unified_only)
            logger.info(
                f"Reporte unificado (modo --unified-only) generado en: {output_dir_base}"
            )
        else:
            logger.error("No se pudieron cargar datos para el modo --unified-only.")
        logger.info("🎉 Análisis (modo --unified-only) completado.")
        return  # Terminar aquí si es unified_only

    # Bucle principal para procesar categorías (ej. "General")
    for category_name, category_config_map in MAIN_CATEGORIES.items():
        logger.info(f"\n--- Procesando categoría principal: {category_name} ---")
        logger.error(  # CRITICAL LOG
            f"CRITICAL_APP_DEBUG: Procesando categoría '{category_name}'. Args: {args}, CatFilters: {category_config_map}"
        )

        current_category_filters = category_config_map.get("filters", {}).copy()
        category_output_folder_name = category_config_map.get(
            "output_folder", f" {category_name}"
        ).strip()
        output_dir_for_analysis = output_dir_base / category_output_folder_name

        try:
            output_dir_for_analysis.mkdir(parents=True, exist_ok=True)
            logger.info(
                f"Directorio de categoría creado/verificado: {output_dir_for_analysis}"
            )
        except Exception as e:
            logger.error(
                f"No se pudo crear el directorio de salida para la categoría {category_name}: {output_dir_for_analysis}. Error: {e}"
            )
            continue  # Saltar a la siguiente categoría

        logger.error(
            f"CRITICAL_APP_DEBUG: Antes de _load_and_preprocess_input_data para '{category_name}'"
        )
        df_processed_for_category = _load_and_preprocess_input_data(
            args, column_map_config, current_category_filters, config
        )

        if df_processed_for_category is None or df_processed_for_category.is_empty():
            logger.warning(
                f"No hay datos para procesar en la categoría '{category_name}' después de la carga y preprocesamiento. Saltando execute_analysis."
            )
            continue

        logger.error(
            f"CRITICAL_APP_DEBUG: Para '{category_name}', ANTES de execute_analysis: df.shape: {df_processed_for_category.shape}, df.cols: {df_processed_for_category.columns}, output_dir_for_analysis: {output_dir_for_analysis}"
        )
        if "Year" in df_processed_for_category.columns:
            unique_years_app = (
                df_processed_for_category.select(
                    pl.col("Year").unique().sort(nulls_last=True)
                )
                .to_series()
                .to_list()
            )
            logger.error(
                f"CRITICAL_APP_DEBUG: 'Year' en df_processed. Únicos: {unique_years_app}"
            )
        else:
            logger.error(
                "CRITICAL_APP_DEBUG: 'Year' column NOT in df_processed antes de execute_analysis."
            )

        execute_analysis(
            df=df_processed_for_category.clone(),
            col_map=column_map_config,
            config=config,
            cli_args=args,
            output_dir=str(output_dir_for_analysis),
            clean_filename_suffix_cli=clean_filename_suffix_cli,  # NUEVO
            analysis_title_suffix_cli=analysis_title_suffix_cli,  # NUEVO
        )

    logger.info("🎉 Análisis completado para todas las categorías.")
    logger.info("El pipeline de análisis ha finalizado.")


if __name__ == "__main__":
    main()

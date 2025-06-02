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
"""
from __future__ import annotations

import argparse
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import polars as pl
import polars.exceptions

from .analyzer import analyze
from .config_loader import load_config
from .main_logic import initialize_analysis, run_analysis_pipeline

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

    # Filtrar por mes usando la columna de fecha local
    filtered_df = df.filter(pl.col("Match_time_local").dt.month() == month_number)

    if filtered_df.is_empty():
        logger.warning(
            f"No se encontraron datos para el mes {month_name} ({month_number}). "
            "El DataFrame resultante está vacío."
        )
    else:
        logger.info(
            f"Filtro de mes aplicado: {month_name}. "
            f"Datos filtrados: {filtered_df.shape[0]} filas "
            f"(de {df.shape[0]} originales)."
        )

    return filtered_df


def _load_and_preprocess_input_data(
    cli_args: argparse.Namespace, column_map_config: Dict[str, str]
) -> Optional[pl.DataFrame]:
    """Carga datos CSV, renombra columnas y aplica filtros CLI.

    Esta función encapsula toda la lógica de carga, mapeo de columnas y filtrado
    inicial basado en los argumentos de línea de comandos.

    Args:
        cli_args: Argumentos parseados de CLI con path CSV y filtros
        column_map_config: Mapeo de nombres de columnas del CSV a nombres internos

    Returns:
        DataFrame procesado y filtrado, o None si hay errores críticos o
        el DataFrame resultante está vacío tras aplicar filtros

    Raises:
        Los errores específicos se capturan y se registran, retornando None
        en caso de fallos críticos
    """
    logger.info(f"Iniciando carga de datos desde CSV: {cli_args.csv}")

    try:
        # Carga del CSV con esquema personalizado
        raw_df = _load_csv_with_schema_override(cli_args.csv, column_map_config)

        # Renombrado de columnas según configuración
        raw_df = _rename_columns_from_config(raw_df, column_map_config)

    except FileNotFoundError:
        logger.error(
            f"Error crítico: Archivo CSV no encontrado en ruta: {cli_args.csv}"
        )
        return None
    except polars.exceptions.NoDataError:
        logger.error(
            f"Error crítico: El archivo CSV '{cli_args.csv}' está vacío "
            "o no contiene datos legibles."
        )
        return None
    except polars.exceptions.SchemaError as e_schema:
        logger.error(
            f"Error crítico de esquema en CSV '{cli_args.csv}'. "
            f"Verifique columnas y tipos: {e_schema}"
        )
        return None
    except polars.exceptions.ComputeError as e_compute:
        logger.error(
            f"Error crítico de Polars durante carga/renombrado "
            f"del CSV '{cli_args.csv}': {e_compute}"
        )
        return None
    except Exception as e_general:
        logger.exception(
            f"Error inesperado al procesar CSV '{cli_args.csv}': {e_general}"
        )
        return None

    # Aplicación de filtros CLI sin modificar el DataFrame original
    filtered_df = raw_df.clone()

    # Aplicar cada filtro en secuencia
    filtered_df = _apply_fiat_filter(filtered_df, cli_args.fiat_filter or [])
    filtered_df = _apply_asset_filter(filtered_df, cli_args.asset_filter or [])
    filtered_df = _apply_status_filter(filtered_df, cli_args.status_filter or [])
    filtered_df = _apply_payment_method_filter(
        filtered_df, cli_args.payment_method_filter or []
    )

    if filtered_df.is_empty():
        logger.warning(
            "El DataFrame está vacío después de aplicar filtros CLI. "
            "No se generarán resultados."
        )
        return None

    logger.info(
        f"Carga y filtrado completados. DataFrame resultante: "
        f"{filtered_df.shape[0]} filas."
    )
    return filtered_df


def main() -> None:
    """Punto de entrada principal para la aplicación CLI de análisis P2P.

    Orquesta el flujo completo de la aplicación:
    1. Inicialización y parseo de argumentos CLI
    2. Carga de configuración
    3. Carga y pre-procesamiento de datos CSV
    4. Aplicación de filtros CLI (excepto mes)
    5. Ejecución del análisis base con analyze()
    6. Aplicación del filtro de mes (si se especifica)
    7. Ejecución del pipeline de análisis completo
    8. Reporte de finalización con ruta de resultados

    Raises:
        SystemExit: Con código 1 si hay errores críticos de carga/filtrado,
                   con código 0 si el DataFrame queda vacío post-análisis
    """
    # Inicialización y parseo de argumentos
    args, cli_filename_suffix, cli_report_title_suffix = initialize_analysis()

    # Carga de configuración centralizada
    config = load_config()
    column_map_config = config.get("column_mapping", {})
    sell_operation_config = config.get("sell_operation", {})

    # Carga y pre-procesamiento de datos con filtros CLI (excepto mes)
    cli_filtered_df = _load_and_preprocess_input_data(args, column_map_config)

    if cli_filtered_df is None:
        logger.error(
            "Proceso terminado: errores en carga o DataFrame vacío post-filtros."
        )
        exit(1)

    logger.info("Iniciando pre-procesamiento con analyze() para generar columnas base.")

    # Pre-procesamiento base mediante analyze() para generar columnas de tiempo
    analyze_output: Tuple[pl.DataFrame, Optional[Any]] = analyze(
        cli_filtered_df.clone(),
        column_map_config,
        sell_operation_config,
        cli_args=vars(args),
    )
    base_processed_df = analyze_output[0]

    if base_processed_df.is_empty():
        logger.warning(
            "DataFrame vacío después de pre-procesamiento con analyze(). "
            "No se generarán resultados."
        )
        exit(0)

    # Aplicar filtro de mes DESPUÉS de que analyze() genere las columnas de tiempo
    if hasattr(args, "month_number") and args.month_number is not None:
        logger.info(f"Aplicando filtro de mes: {args.month_name_display}")
        base_processed_df = _apply_month_filter(
            base_processed_df, args.month_number, args.month_name_display
        )

        if base_processed_df.is_empty():
            logger.warning(
                f"DataFrame vacío después de filtrar por mes {args.month_name_display}. "
                "No se generarán resultados."
            )
            exit(0)

        logger.info(
            f"Filtro de mes aplicado exitosamente. Filas resultantes: {base_processed_df.shape[0]}"
        )

    logger.info("Pre-procesamiento completado. Iniciando pipeline principal...")

    # Ejecución del pipeline de análisis completo
    run_analysis_pipeline(
        df_master_processed=base_processed_df,
        args=args,
        config=config,
        base_file_suffix=cli_filename_suffix,
        base_title_suffix=cli_report_title_suffix,
    )

    # Reporte de finalización exitosa
    output_path = os.path.abspath(args.out)
    logger.info(
        f"✅ Análisis completado exitosamente. " f"Resultados en: {output_path}"
    )


if __name__ == "__main__":
    main()

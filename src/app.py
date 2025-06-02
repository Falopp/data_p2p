#!/usr/bin/env python3
"""Punto de entrada CLI y orquestador principal para el análisis de operaciones P2P.

Este script maneja la carga de datos desde un archivo CSV, aplica filtros iniciales
basados en argumentos de línea de comandos, realiza un pre-procesamiento básico
(como la generación de columnas de fecha) y luego invoca el pipeline de análisis detallado.

Ejemplo de uso:
    python src/app.py --csv data/p2p.csv --out output_directorio
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

# --- Configuración de Logging ---
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Constantes de Nombres de Columnas Internas ---
# Estos nombres se usan después del mapeo inicial desde el CSV y para filtros.
INTERNAL_FIAT_COLUMN = "fiat_type"
INTERNAL_ASSET_COLUMN = "asset_type"
INTERNAL_STATUS_COLUMN = "status"
INTERNAL_PAYMENT_METHOD_COLUMN = "payment_method"


def _load_and_filter_data(
    cli_args: argparse.Namespace, column_map_config: Dict[str, str]
) -> Optional[pl.DataFrame]:
    """
    Carga los datos desde el archivo CSV especificado, renombra columnas según la configuración,
    y aplica filtros basados en los argumentos CLI.

    Args:
        cli_args: Argumentos parseados de la línea de comandos, incluyendo la ruta al CSV.
        column_map_config: Mapeo de nombres de columnas del CSV a nombres internos.

    Returns:
        Un DataFrame de Polars con los datos cargados y filtrados, o None si ocurre un error
        o si el DataFrame resultante de los filtros está vacío.
    """
    logger.info(f"Iniciando carga de datos desde el archivo CSV: {cli_args.csv}")
    try:
        csv_order_number_col: str = column_map_config.get("order_number", "Order Number")
        csv_adv_order_number_col: str = column_map_config.get(
            "adv_order_number", "Advertisement Order Number"
        )

        csv_column_types_override: Dict[str, pl.DataType] = {
            csv_order_number_col: pl.String,
            csv_adv_order_number_col: pl.String,
        }

        raw_df: pl.DataFrame = pl.read_csv(
            source=cli_args.csv,
            infer_schema_length=10000,
            null_values=["", "NA", "N/A", "NaN", "null"],
            schema_overrides=csv_column_types_override,
        )
        logger.info(
            f"Datos cargados exitosamente: {raw_df.shape[0]} filas, {raw_df.shape[1]} columnas."
        )

        column_rename_map: Dict[str, str] = {
            csv_col_name: script_col_name
            for script_col_name, csv_col_name in column_map_config.items()
            if csv_col_name
            and csv_col_name in raw_df.columns
            and csv_col_name != script_col_name
        }
        if column_rename_map:
            raw_df = raw_df.rename(column_rename_map)
            logger.info(f"Columnas renombradas según configuración: {column_rename_map}")

    except FileNotFoundError:
        logger.error(f"Error crítico: El archivo CSV no se encontró en la ruta especificada: {cli_args.csv}")
        return None
    except polars.exceptions.NoDataError:
        logger.error(f"Error crítico: El archivo CSV '{cli_args.csv}' está vacío o no contiene datos legibles.")
        return None
    except polars.exceptions.SchemaError as e_schema:
        logger.error(f"Error crítico de esquema al leer el CSV '{cli_args.csv}'. Verifique las columnas y tipos: {e_schema}")
        return None
    except polars.exceptions.ComputeError as e_compute:
        logger.error(f"Error crítico de Polars durante la carga o renombrado inicial del CSV '{cli_args.csv}': {e_compute}")
        return None
    except Exception as e_general: # Captura más genérica para problemas inesperados durante carga/renombrado
        logger.exception(f"Error inesperado y crítico al procesar el archivo CSV '{cli_args.csv}': {e_general}")
        return None

    # Clonar para aplicar filtros sin modificar el DataFrame original cargado (raw_df)
    filtered_df: pl.DataFrame = raw_df.clone()

    # Aplicación de filtros basados en argumentos CLI
    if cli_args.fiat_filter and INTERNAL_FIAT_COLUMN in filtered_df.columns:
        processed_fiat_filters: List[str] = [f.strip().upper() for f in cli_args.fiat_filter]
        filtered_df = filtered_df.filter(
            pl.col(INTERNAL_FIAT_COLUMN).str.to_uppercase().str.strip_chars().is_in(processed_fiat_filters)
        )
        logger.info(f"Filtro por FIAT aplicado: {processed_fiat_filters}")

    if cli_args.asset_filter and INTERNAL_ASSET_COLUMN in filtered_df.columns:
        processed_asset_filters: List[str] = [a.strip().upper() for a in cli_args.asset_filter]
        filtered_df = filtered_df.filter(
            pl.col(INTERNAL_ASSET_COLUMN).str.to_uppercase().str.strip_chars().is_in(processed_asset_filters)
        )
        logger.info(f"Filtro por Asset aplicado: {processed_asset_filters}")

    if cli_args.status_filter and INTERNAL_STATUS_COLUMN in filtered_df.columns:
        processed_status_filters: List[str] = [
            s.strip().capitalize() for s in cli_args.status_filter
        ]
        filtered_df = filtered_df.filter(
            pl.col(INTERNAL_STATUS_COLUMN)
            .str.to_titlecase()
            .str.strip_chars()
            .is_in(processed_status_filters)
        )
        logger.info(f"Filtro por Status aplicado: {processed_status_filters}")

    if cli_args.payment_method_filter and INTERNAL_PAYMENT_METHOD_COLUMN in filtered_df.columns:
        filtered_df = filtered_df.filter(
            pl.col(INTERNAL_PAYMENT_METHOD_COLUMN).is_in(cli_args.payment_method_filter)
        )
        logger.info(f"Filtro por Payment Method aplicado: {cli_args.payment_method_filter}")

    if filtered_df.is_empty():
        logger.warning(
            "El DataFrame está vacío después de aplicar los filtros CLI. No se generarán resultados."
        )
        return None # DataFrame vacío después de filtros, no continuar.

    logger.info(f"Carga y filtrado inicial completados. DataFrame resultante con {filtered_df.shape[0]} filas.")
    return filtered_df


def main() -> None:
    """
    Punto de entrada principal para la aplicación CLI de análisis P2P.

    Orquesta la carga de datos, pre-procesamiento, aplicación de filtros CLI,
    y la ejecución del pipeline de análisis.
    """
    args: argparse.Namespace
    cli_filename_suffix: str
    cli_report_title_suffix: str
    (args, cli_filename_suffix, cli_report_title_suffix) = initialize_analysis()

    config: Dict[str, Any] = load_config()
    column_map_config: Dict[str, str] = config.get("column_mapping", {})
    sell_operation_config: Dict[str, Any] = config.get("sell_operation", {})

    # Carga, renombrado y filtrado inicial de datos
    cli_filtered_df: Optional[pl.DataFrame] = _load_and_filter_data(args, column_map_config)

    if cli_filtered_df is None:
        logger.error("Proceso terminado debido a errores en la carga o DataFrame vacío post-filtros CLI.")
        exit(1) # Usar exit(1) si la carga/filtrado falla y es crítico

    logger.info(
        "Iniciando pre-procesamiento del DataFrame (post-filtros CLI) para generar columnas base (ej. 'Year')."
    )

    base_processed_df: pl.DataFrame
    analyze_output: Tuple[pl.DataFrame, Optional[Any]] = analyze(
        cli_filtered_df.clone(), # .clone() aquí es importante si analyze modifica el DF y necesitamos el original filtrado después
        column_map_config, # Pasar column_map_config en lugar de column_map (que ya no existe en este scope)
        sell_operation_config,
        cli_args=vars(args),
    )
    base_processed_df = analyze_output[0]

    if base_processed_df.is_empty():
        logger.warning(
            "El DataFrame está vacío después del pre-procesamiento inicial con 'analyze' (post-filtros CLI)."
            " No se generarán resultados."
        )
        exit(0) # Salida controlada, DataFrame vacío post-analyze puede no ser un error crítico.

    logger.info("Pre-procesamiento base completado. Iniciando pipeline de análisis principal...")
    run_analysis_pipeline(
        df_master_processed=base_processed_df,
        args=args,
        config=config,
        base_file_suffix=cli_filename_suffix,
        base_title_suffix=cli_report_title_suffix,
    )

    output_path: str = os.path.abspath(args.out)
    logger.info(f"✅ Todos los análisis completados. Resultados generados en: {output_path}")

if __name__ == "__main__":
    main()
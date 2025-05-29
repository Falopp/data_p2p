#!/usr/bin/env python3
"""Análisis integral de operaciones P2P (Versión Profesional Avanzada).

Ejemplo:
    python src/analisis_profesional_p2p.py --csv data/p2p.csv --out output_profesional
"""
from __future__ import annotations
import argparse
import os
import textwrap
import polars as pl
import pytz
import logging
import datetime
from jinja2 import Environment, FileSystemLoader
import pandas as pd
import sys

from .config_loader import load_config, setup_logging
from .main_logic import initialize_analysis, run_analysis_pipeline
from .utils import parse_amount # Asegurarse que utils.py está en src/
from .analyzer import analyze # analyze se llama desde main_logic Y TAMBIÉN AQUÍ para pre-procesar
from . import plotting # plotting.py está en src/

# --- Configuración de Logging Básico ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Funciones Auxiliares (Helpers) ---

# --- Funciones de Análisis Principal (A REFACATORIZAR) ---

# --- Lógica Principal (CLI) ---
def main():
    args, clean_filename_suffix_cli, analysis_title_suffix_cli = initialize_analysis()

    config = load_config()
    col_map = config.get('column_mapping', {})
    sell_config = config.get('sell_operation', {})

    logger.info(f"Cargando datos desde: {args.csv}")
    try:
        order_number_csv_col = col_map.get('order_number', "Order Number")
        adv_order_number_csv_col = col_map.get('adv_order_number', "Advertisement Order Number")
            
        column_types_to_override = {
            order_number_csv_col: pl.String,
            adv_order_number_csv_col: pl.String 
        }
        
        df_raw = pl.read_csv(
            args.csv, 
            infer_schema_length=10000, 
            null_values=["", "NA", "N/A", "NaN", "null"],
            schema_overrides=column_types_to_override
        )
        logger.info(f"Datos cargados: {df_raw.shape[0]} filas, {df_raw.shape[1]} columnas desde CSV.")

        rename_dict = {csv_col_name: script_col_name 
                       for script_col_name, csv_col_name in col_map.items() 
                       if csv_col_name and csv_col_name in df_raw.columns and csv_col_name != script_col_name}
        if rename_dict:
            df_raw = df_raw.rename(rename_dict)
            logger.info(f"Columnas renombradas según config: {rename_dict}")
        
    except Exception as e:
        logger.error(f"Error al leer o renombrar inicialmente el archivo CSV con Polars: {e}")
        exit(1)
    
    df_cli_filtered = df_raw.clone()
    fiat_type_internal_col = 'fiat_type' 
    asset_type_internal_col = 'asset_type' 
    status_internal_col = 'status'
    payment_method_internal_col = 'payment_method'

    if args.fiat_filter and fiat_type_internal_col in df_cli_filtered.columns:
        processed_fiats = [f.strip().upper() for f in args.fiat_filter]
        df_cli_filtered = df_cli_filtered.filter(pl.col(fiat_type_internal_col).str.to_uppercase().str.strip().is_in(processed_fiats))
    if args.asset_filter and asset_type_internal_col in df_cli_filtered.columns:
        processed_assets = [a.strip().upper() for a in args.asset_filter]
        df_cli_filtered = df_cli_filtered.filter(pl.col(asset_type_internal_col).str.to_uppercase().str.strip().is_in(processed_assets))
    if args.status_filter and status_internal_col in df_cli_filtered.columns:
        processed_status_cli_arg = [s.strip().capitalize() for s in args.status_filter]
        df_cli_filtered = df_cli_filtered.filter(pl.col(status_internal_col).str.to_capitalized().str.strip().is_in(processed_status_cli_arg))
    if args.payment_method_filter and payment_method_internal_col in df_cli_filtered.columns:
        df_cli_filtered = df_cli_filtered.filter(pl.col(payment_method_internal_col).is_in(args.payment_method_filter))

    if df_cli_filtered.is_empty():
        print("El DataFrame está vacío después de aplicar los filtros CLI. No se generarán resultados.")
        exit(0)

    logger.info("\n=== Pre-procesando DataFrame base con Polars (después de filtros CLI) para generar columnas base ===")
    # Esta llamada es crucial para que df_master_processed tenga columnas como 'Year'
    # generadas por analyze, antes de pasarlo a run_analysis_pipeline.
    df_master_processed, _ = analyze(
        df_cli_filtered.clone(), # Usar una copia para no modificar df_cli_filtered si se usa después
        col_map, 
        sell_config, 
        cli_args=vars(args) # analyze espera cli_args como un dict
    )

    if df_master_processed.is_empty():
        print("DataFrame vacío después del pre-procesamiento inicial con 'analyze' (post-CLI filters). No se generarán resultados.")
        exit(0)

    # Llamar a run_analysis_pipeline con el df_master_processed
    run_analysis_pipeline(
        df_master_processed=df_master_processed, # DataFrame ya pre-procesado con columnas como 'Year'
        args=args,
        config=config,
        base_file_suffix=clean_filename_suffix_cli, # Nombre de argumento actualizado
        base_title_suffix=analysis_title_suffix_cli  # Nombre de argumento actualizado
    )

    print(f"\n\u2705 Todos los análisis completados. Resultados en: {os.path.abspath(args.out)}")

if __name__ == "__main__":
    main()
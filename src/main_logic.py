import argparse
import polars as pl
import logging

logger = logging.getLogger(__name__)

def initialize_analysis(cli_args_list: list[str] | None = None) -> tuple[argparse.Namespace, str, str]:
    parser = argparse.ArgumentParser(
        description="Analiza datos de operaciones P2P desde un CSV y genera reportes y gráficos.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""Ejemplos de uso:\n{'-'*17}\n1. Análisis básico:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv\n\n2. Solo total, sin desglose anual:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv --no_annual_breakdown\n\n3. Especificar salida:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv --out mis_resultados_p2p\n\n4. Filtrar por fiat y asset:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv --fiat_filter UYU ARS --asset_filter USDT BTC"""
    )
    parser.add_argument("--csv", required=True, help="Ruta al archivo CSV de operaciones P2P.")
    parser.add_argument("--out", default="output", help="Carpeta base para guardar los resultados (Default: output).")
    parser.add_argument("--fiat_filter", nargs='+', default=None, help="Filtrar por una o más monedas Fiat.")
    parser.add_argument("--asset_filter", nargs='+', default=None, help="Filtrar por uno o más tipos de Activos.")
    parser.add_argument("--status_filter", nargs='+', default=None, help="Filtrar por uno o más Estados de orden.")
    parser.add_argument("--payment_method_filter", nargs='+', default=None, help="Filtrar por uno o más Métodos de Pago.")
    parser.add_argument("--no_annual_breakdown",action="store_true",help="Si se establece, no se generan resultados desglosados por año.")
    
    args = parser.parse_args(cli_args_list)

    logger.info(f"Directorio de salida principal: {args.out}")
    logger.info(f"Archivo CSV de entrada: {args.csv}")
    
    processed_fiats = []
    processed_assets = []
    processed_status_cli_arg = []
    safe_payment_methods = []

    if args.fiat_filter: processed_fiats = [f.strip().upper() for f in args.fiat_filter]
    if args.asset_filter: processed_assets = [a.strip().upper() for a in args.asset_filter]
    if args.status_filter: processed_status_cli_arg = [s.strip().capitalize() for s in args.status_filter]
    if args.payment_method_filter: safe_payment_methods = [pm.strip().replace(' ', '_') for pm in args.payment_method_filter]

    file_suffix_parts_cli = []
    title_suffix_parts_cli = [] 
    if args.fiat_filter:
        file_suffix_parts_cli.append(f"fiat_({'_'.join(processed_fiats)})" )
        title_suffix_parts_cli.append(f"Fiat {', '.join(processed_fiats)}")
    if args.asset_filter:
        file_suffix_parts_cli.append(f"asset_({'_'.join(processed_assets)})" )
        title_suffix_parts_cli.append(f"Asset {', '.join(processed_assets)}")
    if args.status_filter:
        file_suffix_parts_cli.append(f"status_({'_'.join(processed_status_cli_arg)})" )
        title_suffix_parts_cli.append(f"Status {', '.join(processed_status_cli_arg)}")
    if args.payment_method_filter:
        file_suffix_parts_cli.append(f"payment_({'_'.join(safe_payment_methods)})" )
        title_suffix_parts_cli.append(f"Payment {', '.join(args.payment_method_filter)}")

    if file_suffix_parts_cli:
        base_filename_suffix_cli = "_" + "_".join(file_suffix_parts_cli)
        analysis_title_suffix_cli = " (" + "; ".join(title_suffix_parts_cli) + ")"
    else:
        base_filename_suffix_cli = "_general"
        analysis_title_suffix_cli = " (General)"
    clean_filename_suffix_cli = base_filename_suffix_cli.replace("(", "").replace(")", "").replace(",", "").replace(";", "").replace(":", "").lower()
    
    return args, clean_filename_suffix_cli, analysis_title_suffix_cli


def run_analysis_pipeline(df_master_processed: pl.DataFrame, args: argparse.Namespace, config: dict, col_map: dict, sell_config: dict, clean_filename_suffix_cli: str, analysis_title_suffix_cli: str):
    from analyzer import analyze
    from reporter import save_outputs

    status_col_internal = 'status' # Asumir que este es el nombre INTERNO después del mapeo
    status_categories = ["todas", "completadas", "canceladas"]
    periods_to_process = {"total": df_master_processed.clone()}
    
    if not args.no_annual_breakdown:
        year_internal_col = 'Year' # Asumir que este es el nombre INTERNO después del procesamiento en analyze
        if year_internal_col in df_master_processed.columns and df_master_processed[year_internal_col].null_count() < df_master_processed.height:
            unique_years = sorted(df_master_processed.select(pl.col(year_internal_col).drop_nulls().unique()).to_series().to_list())
            logger.info(f"\n=== Años identificados para desglose: {unique_years} ===")
            for year_val in unique_years:
                df_year_subset = df_master_processed.filter(pl.col(year_internal_col) == year_val)
                if not df_year_subset.is_empty():
                    periods_to_process[str(year_val)] = df_year_subset
        else:
            logger.warning(f"Columna '{year_internal_col}' no disponible o vacía. No se realizará desglose anual.")

    for period_label, df_period_base in periods_to_process.items():
        logger.info(f"\n=== Iniciando Análisis (Polars) para PERÍODO: {period_label.upper()} ===")
        for status_category in status_categories:
            logger.info(f"--- Procesando categoría de estado (Polars): {status_category.upper()} para período: {period_label.upper()} ---")
            df_subset_for_status = pl.DataFrame() 
            if status_category == "todas":
                df_subset_for_status = df_period_base.clone()
            elif status_category == "completadas":
                if status_col_internal in df_period_base.columns:
                    df_subset_for_status = df_period_base.filter(pl.col(status_col_internal) == 'Completed')
            elif status_category == "canceladas":
                if status_col_internal in df_period_base.columns:
                     df_subset_for_status = df_period_base.filter(pl.col(status_col_internal).is_in(['Cancelled', 'System cancelled'])) 
            
            if df_subset_for_status.is_empty():
                logger.info(f"No hay datos para '{status_category}' en período '{period_label}'. Se omite.")
                continue
            else:
                logger.info(f"DataFrame para '{status_category}' en período '{period_label}' tiene {df_subset_for_status.height} filas ANTES de llamar a analyze.")

            logger.info(f"Analizando {df_subset_for_status.height} filas para {period_label.upper()} - {status_category.upper()} con Polars")
            # La función analyze ya está definida en src.analyzer, la importamos arriba.
            processed_df_for_save, current_metrics = analyze(df_subset_for_status.clone(), col_map, sell_config)
            
            # La función save_outputs ya está definida en src.reporter, la importamos arriba.
            save_outputs(
                df_to_plot_from=processed_df_for_save, 
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
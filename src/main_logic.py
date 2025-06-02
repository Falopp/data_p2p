import argparse
import polars as pl
import logging
from pathlib import Path
from typing import Tuple, Dict, Any, List

from .analyzer import analyze
from .reporter import save_outputs

logger = logging.getLogger(__name__)

# Mapeo de nombres de meses a números para facilitar búsqueda
MONTH_NAMES_MAP = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def initialize_analysis(
    cli_args_list: List[str] = None,
) -> Tuple[argparse.Namespace, str, str]:
    parser = argparse.ArgumentParser(
        description="Analiza datos de operaciones P2P desde un CSV y genera reportes y gráficos.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""Ejemplos de uso:\n{'-'*17}\n1. Análisis básico:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv\n\n2. Solo total, sin desglose anual:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv --no_annual_breakdown\n\n3. Especificar salida:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv --out mis_resultados_p2p\n\n4. Filtrar por fiat y asset:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv --fiat_filter UYU ARS --asset_filter USDT BTC\n\n5. Análisis de mayo solamente:\n   python src/analisis_profesional_p2p.py --csv data/p2p.csv --mes mayo""",
    )
    parser.add_argument(
        "--csv", required=True, help="Ruta al archivo CSV de operaciones P2P."
    )
    parser.add_argument(
        "--out",
        default="output",
        help="Carpeta base para guardar los resultados (Default: output).",
    )
    parser.add_argument(
        "--fiat_filter",
        nargs="+",
        default=None,
        help="Filtrar por una o más monedas Fiat.",
    )
    parser.add_argument(
        "--asset_filter",
        nargs="+",
        default=None,
        help="Filtrar por uno o más tipos de Activos.",
    )
    parser.add_argument(
        "--status_filter",
        nargs="+",
        default=None,
        help="Filtrar por uno o más Estados de orden.",
    )
    parser.add_argument(
        "--payment_method_filter",
        nargs="+",
        default=None,
        help="Filtrar por uno o más Métodos de Pago.",
    )
    parser.add_argument(
        "--year",
        nargs="?",
        const="all",
        default=None,
        help="Specify a year to process (e.g., 2023). If provided without a value or as '--year all', all available years will be processed. If omitted, all years will also be processed. The 'total' dataset is always processed.",
    )
    parser.add_argument(
        "--mes",
        type=str,
        default=None,
        help="Filtrar por un mes específico (ej. mayo, december, 5). Acepta nombres en español/inglés o números (1-12).",
    )
    parser.add_argument(
        "--detect-outliers",
        action="store_true",
        help="Activar detección de outliers con IsolationForest.",
    )
    parser.add_argument(
        "--event-date",
        type=str,
        default=None,
        help="Fecha del evento (YYYY-MM-DD) para análisis comparativo Antes/Después (24h).",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Activar modo interactivo (ej. gráficos Plotly incrustados o enlazados).",
    )

    if cli_args_list is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(cli_args_list)  # Para testing

    logger.info(f"Directorio de salida principal: {args.out}")
    logger.info(f"Archivo CSV de entrada: {args.csv}")

    processed_fiats = []
    processed_assets = []
    processed_status_cli_arg = []
    safe_payment_methods = []

    if args.fiat_filter:
        processed_fiats = [f.strip().upper() for f in args.fiat_filter]
    if args.asset_filter:
        processed_assets = [a.strip().upper() for a in args.asset_filter]
    if args.status_filter:
        processed_status_cli_arg = [s.strip().capitalize() for s in args.status_filter]
    if args.payment_method_filter:
        safe_payment_methods = [
            pm.strip().replace(" ", "_") for pm in args.payment_method_filter
        ]

    # Procesar filtro de mes
    month_number = None
    month_name_display = None
    if args.mes:
        month_input = args.mes.strip().lower()

        # Intentar parsear como número
        try:
            month_number = int(month_input)
            if not (1 <= month_number <= 12):
                logger.error(
                    f"Número de mes inválido: {month_number}. Debe estar entre 1 y 12."
                )
                exit(1)
            # Convertir número a nombre para display
            month_names = [
                "enero",
                "febrero",
                "marzo",
                "abril",
                "mayo",
                "junio",
                "julio",
                "agosto",
                "septiembre",
                "octubre",
                "noviembre",
                "diciembre",
            ]
            month_name_display = month_names[month_number - 1].capitalize()
        except ValueError:
            # No es un número, buscar en el mapeo de nombres
            if month_input in MONTH_NAMES_MAP:
                month_number = MONTH_NAMES_MAP[month_input]
                month_name_display = month_input.capitalize()
            else:
                logger.error(
                    f"Mes no reconocido: '{args.mes}'. Use nombres en español/inglés o números 1-12."
                )
                exit(1)

        # Agregar el mes procesado a args para uso posterior
        args.month_number = month_number
        args.month_name_display = month_name_display
        logger.info(
            f"Filtro de mes activado: {month_name_display} (mes {month_number})"
        )
    else:
        args.month_number = None
        args.month_name_display = None

    file_suffix_parts_cli = []
    title_suffix_parts_cli = []
    if args.fiat_filter:
        file_suffix_parts_cli.append(f"fiat_({'_'.join(processed_fiats)})")
        title_suffix_parts_cli.append(f"Fiat {', '.join(processed_fiats)}")
    if args.asset_filter:
        file_suffix_parts_cli.append(f"asset_({'_'.join(processed_assets)})")
        title_suffix_parts_cli.append(f"Asset {', '.join(processed_assets)}")
    if args.status_filter:
        file_suffix_parts_cli.append(f"status_({'_'.join(processed_status_cli_arg)})")
        title_suffix_parts_cli.append(f"Status {', '.join(processed_status_cli_arg)}")
    if args.payment_method_filter:
        file_suffix_parts_cli.append(f"payment_({'_'.join(safe_payment_methods)})")
        title_suffix_parts_cli.append(
            f"Payment {', '.join(args.payment_method_filter)}"
        )
    if args.mes:
        file_suffix_parts_cli.append(f"mes_{month_name_display.lower()}")
        title_suffix_parts_cli.append(f"Mes {month_name_display}")

    if file_suffix_parts_cli:
        base_filename_suffix_cli = "_" + "_".join(file_suffix_parts_cli)
        analysis_title_suffix_cli = " (" + "; ".join(title_suffix_parts_cli) + ")"
    else:
        base_filename_suffix_cli = "_general"
        analysis_title_suffix_cli = " (General)"
    clean_filename_suffix_cli = (
        base_filename_suffix_cli.replace("(", "")
        .replace(")", "")
        .replace(",", "")
        .replace(";", "")
        .replace(":", "")
        .lower()
    )

    return args, clean_filename_suffix_cli, analysis_title_suffix_cli


def run_analysis_pipeline(
    df_master_processed: pl.DataFrame,
    args: argparse.Namespace,
    config: Dict[str, Any],
    base_file_suffix: str,  # Renombrado de clean_file_suffix para claridad
    base_title_suffix: str,  # Renombrado de title_suffix_str para claridad
    # logger es global o pasado si es necesario
):
    """
    Runs the main analysis pipeline, processing data for "total" and specified/all years.
    Generates outputs for "todas", "completadas", and "canceladas" statuses for each period.
    """
    output_root_path = Path(args.out)
    status_categories_map = {
        "todas": None,  # Usar None para indicar que no se filtra por estado específico aquí
        "completadas": "Completed",
        "canceladas": [
            "Cancelled",
            "System cancelled",
        ],  # Como lista para el filtro is_in
    }

    # --- 1. Procesar el conjunto de datos "total" ---
    logger.info("Starting processing for 'total' dataset.")
    period_label_for_total = "total"
    df_for_total_period = (
        df_master_processed.clone()
    )  # Trabajar con una copia para el periodo total

    # Generar sufijos específicos para el periodo "total" si es necesario (generalmente no)
    # El base_file_suffix y base_title_suffix ya reflejan filtros globales CLI

    for status_key, status_filter_values in status_categories_map.items():
        status_category_cleaned_name = status_key  # ej. "todas", "completadas"
        logger.info(
            f"Processing 'total' dataset, status: {status_category_cleaned_name}"
        )

        df_subset = df_for_total_period.clone()
        status_internal_col_name = "status"  # Nombre interno de la columna de estado

        if (
            status_filter_values
        ):  # Solo filtrar si hay valores de estado definidos (no para "todas")
            if status_internal_col_name in df_subset.columns:
                if isinstance(status_filter_values, list):
                    df_subset = df_subset.filter(
                        pl.col(status_internal_col_name).is_in(status_filter_values)
                    )
                else:
                    df_subset = df_subset.filter(
                        pl.col(status_internal_col_name) == status_filter_values
                    )
            else:
                logger.warning(
                    f"Skipping status filter for '{status_category_cleaned_name}' in 'total': Column '{status_internal_col_name}' not found."
                )

        if df_subset.is_empty():
            logger.warning(
                f"No data for 'total' with status '{status_category_cleaned_name}' after filtering. Skipping."
            )
            continue

        # El título y sufijo de archivo para el reporte de este subconjunto específico
        # Podrían añadir el estado, ej. " (Total - Completadas)"
        # O dejarlo como está y el nombre de la carpeta ya indica el estado.
        # El README sugiere que el sufijo CLI ya está bien.
        # El título del reporte HTML sí debería reflejar el periodo y estado.
        # final_title = f"{period_label_for_total.capitalize()} Data{base_title_suffix} - {status_category_cleaned_name.capitalize()}"
        # El reporter.py ya maneja el título del reporte, pasándole el `period_label_for_path` y `status_category_cleaned_name`

        processed_df_subset, current_metrics = analyze(
            df_subset,
            config["column_mapping"],
            config["sell_operation"],
            # Pasar más args si analyze los necesita, ej. para outliers, event_date
        )

        if (
            processed_df_subset.is_empty() and not current_metrics
        ):  # O una comprobación más robusta
            logger.warning(
                f"Analysis of 'total' with status '{status_category_cleaned_name}' yielded no data or metrics. Skipping report."
            )
            continue

        save_outputs(
            df_to_plot_from=processed_df_subset,
            metrics_to_save=current_metrics,
            output_label=period_label_for_total,
            status_subdir=status_category_cleaned_name,
            base_output_dir=args.out,
            file_name_suffix_from_cli=base_file_suffix,
            title_suffix_from_cli=base_title_suffix,
            col_map=config["column_mapping"],
            cli_args=args,
            config=config,
        )
    logger.info("Finished processing for 'total' dataset.")

    # --- 2. Determinar y procesar años individuales ---
    years_to_process_individually = []
    process_all_available_years = args.year is None or args.year == "all"

    if (
        "Year" not in df_master_processed.columns
        or df_master_processed["Year"].is_null().all()
    ):
        logger.warning(
            "'Year' column not found or contains all nulls. Skipping annual breakdown."
        )
    else:
        if process_all_available_years:
            unique_years = (
                df_master_processed["Year"].unique().drop_nulls().sort().to_list()
            )
            years_to_process_individually.extend(unique_years)
            logger.info(f"Processing all available years: {unique_years}")
        elif args.year:  # Un año específico fue dado
            try:
                specific_year = int(args.year)
                # Verificar si ese año existe en los datos para evitar crear carpetas vacías innecesariamente
                if df_master_processed.filter(
                    pl.col("Year") == specific_year
                ).is_empty():
                    logger.warning(
                        f"Year {specific_year} provided via --year, but no data found for this year after initial filters. Skipping this year."
                    )
                else:
                    years_to_process_individually.append(specific_year)
                    logger.info(f"Processing specific year: {specific_year}")
            except ValueError:
                logger.error(
                    f"Invalid year format '{args.year}' provided with --year. Skipping annual processing."
                )

    if not years_to_process_individually:
        logger.info("No specific years to process individually.")

    for year_val in years_to_process_individually:
        period_label_for_year = str(year_val)
        logger.info(f"Starting processing for year: {period_label_for_year}")

        df_year_specific_period = df_master_processed.filter(pl.col("Year") == year_val)

        if (
            df_year_specific_period.is_empty()
        ):  # Doble chequeo, aunque uno arriba ya lo hizo para --year YYYY
            logger.warning(
                f"No data for year {year_val} after filtering from master. Skipping this year."
            )
            continue

        # Los sufijos base_file_suffix y base_title_suffix de los filtros CLI siguen aplicando.
        # El año se refleja en la estructura de carpetas (period_label_for_year).

        for status_key, status_filter_values in status_categories_map.items():
            status_category_cleaned_name = status_key
            logger.info(
                f"Processing year {period_label_for_year}, status: {status_category_cleaned_name}"
            )

            df_subset_year = df_year_specific_period.clone()
            status_internal_col_name = (
                "status"  # Nombre interno de la columna de estado
            )

            if status_filter_values:  # Solo filtrar si hay valores de estado definidos
                if status_internal_col_name in df_subset_year.columns:
                    if isinstance(status_filter_values, list):
                        df_subset_year = df_subset_year.filter(
                            pl.col(status_internal_col_name).is_in(status_filter_values)
                        )
                    else:
                        df_subset_year = df_subset_year.filter(
                            pl.col(status_internal_col_name) == status_filter_values
                        )
                else:
                    logger.warning(
                        f"Skipping status filter for '{status_category_cleaned_name}' in year '{period_label_for_year}': Column '{status_internal_col_name}' not found."
                    )

            if df_subset_year.is_empty():
                logger.warning(
                    f"No data for year {period_label_for_year} with status '{status_category_cleaned_name}'. Skipping."
                )
                continue

            processed_df_subset_year, current_metrics_year = analyze(
                df_subset_year,
                config["column_mapping"],
                config["sell_operation"],
                # ... más args para analyze
            )

            if processed_df_subset_year.is_empty() and not current_metrics_year:
                logger.warning(
                    f"Analysis of year {period_label_for_year} with status '{status_category_cleaned_name}' yielded no data or metrics. Skipping report."
                )
                continue

            save_outputs(
                df_to_plot_from=processed_df_subset_year,
                metrics_to_save=current_metrics_year,
                output_label=period_label_for_year,  # Será "2023", "2024", etc.
                status_subdir=status_category_cleaned_name,
                base_output_dir=args.out,
                file_name_suffix_from_cli=base_file_suffix,
                title_suffix_from_cli=base_title_suffix,
                col_map=config["column_mapping"],
                cli_args=args,
                config=config,
            )
        logger.info(f"Finished processing for year: {period_label_for_year}.")

    logger.info("Analysis pipeline finished.")

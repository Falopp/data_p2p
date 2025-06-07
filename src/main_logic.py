#!/usr/bin/env python3
"""
Módulo para la lógica principal de análisis y configuración inicial.
"""

import argparse
import logging
import os  # Necesario para algunas operaciones de Path, aunque Path maneja mucho
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import polars as pl

# Asegurarse de que DEFAULT_CONFIG esté disponible
from .config_loader import DEFAULT_CONFIG
from .analyzer import analyze

# from .plotting import get_plot_config # Eliminada esta importación
from .reporter import (
    save_outputs,
)  # Contiene generate_html_report, generate_summary_excel, save_metric_tables
from .unified_reporter import UnifiedReporter

logger = logging.getLogger(__name__)

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
    cli_args_list: Optional[List[str]] = None,
) -> Tuple[argparse.Namespace, str, str]:
    """Inicializa el análisis: parsea argumentos y configura el logging."""
    logger.error("CRITICAL_DEBUG_INIT_ANALYSIS_START: Entrando a initialize_analysis")
    parser = argparse.ArgumentParser(
        description="Analizador de datos P2P.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "--csv", type=str, required=True, help="Ruta al archivo CSV de datos P2P."
    )
    parser.add_argument(
        "--out",
        type=str,
        default="output",
        help="Directorio de salida para los reportes y gráficos (Default: output).",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Ruta a un archivo de configuración YAML personalizado.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Nivel de logging.",
    )
    # Filtros CLI (ejemplos, app.py podría manejarlos antes)
    parser.add_argument(
        "--fiat_filter",
        nargs="+",
        default=None,
        help="Filtrar por monedas Fiat (no implementado centralmente aquí aún).",
    )
    parser.add_argument(
        "--asset_filter",
        nargs="+",
        default=None,
        help="Filtrar por tipos de Activos (no implementado centralmente aquí aún).",
    )
    parser.add_argument(
        "--status_filter",
        nargs="+",
        default=None,
        help="Filtrar por Estados de orden (CLI, para sufijo global o si app.py no filtra).",
    )
    parser.add_argument(
        "--payment_method_filter",
        nargs="+",
        default=None,
        help="Filtrar por Métodos de Pago (no implementado centralmente aquí aún).",
    )
    parser.add_argument(
        "--mes",
        help="Analizar solo un mes específico (nombre o número). Ej: --mes mayo",
    )
    parser.add_argument(
        "--event_date",
        help="Fecha de evento para análisis comparativo Antes/Después (YYYY-MM-DD) (no implementado centralmente aquí aún).",
    )

    parser.add_argument(
        "--no-annual-breakdown",
        action="store_true",
        help="No generar análisis anuales individuales, solo el total.",
    )
    parser.add_argument(
        "--year",
        type=str,
        default=None,  # Default None, execute_analysis lo interpreta como 'all'
        help="Año para analizar (ej: 2023) o 'all'. Si no se da, todos los años y total.",
    )
    parser.add_argument(
        "--unified-only",
        action="store_true",
        help="Generar solo el reporte unificado global y salir (lógica en app.py).",
    )
    parser.add_argument(
        "--no-unified-report",
        action="store_true",
        help="Omitir la generación del reporte unificado global.",
    )
    parser.add_argument(
        "--detect_outliers", action="store_true", help="Activar detección de outliers."
    )
    parser.add_argument(
        "--outliers_contamination",
        default="auto",
        help="Parámetro 'contamination' para Isolation Forest.",
    )
    parser.add_argument(
        "--outliers_n_estimators",
        type=int,
        default=100,
        help="Número de estimadores para Isolation Forest.",
    )
    parser.add_argument(
        "--outliers_random_state",
        type=int,
        default=42,
        help="Random state para Isolation Forest.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Modo interactivo (actualmente sin efecto específico global).",
    )

    args = parser.parse_args(cli_args_list if cli_args_list is not None else None)

    try:
        log_level_int = getattr(logging, args.log_level.upper(), logging.INFO)

        # Configuración básica para la consola
        logging.basicConfig(
            level=log_level_int,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            force=True,
        )

        # Añadir FileHandler para errores
        error_log_file = Path(args.out) / "log_error.txt"
        # Asegurarse de que el directorio de salida exista para el log de errores
        error_log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(error_log_file, mode="a")  # 'a' para append
        file_handler.setLevel(logging.ERROR)  # Solo errores y niveles superiores
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)

        # Añadir el handler al logger raíz (o a un logger específico si se prefiere)
        logging.getLogger("").addHandler(file_handler)  # Logger raíz

        logging.getLogger("matplotlib").setLevel(logging.WARNING)
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logger.info(f"Nivel de logging configurado a: {args.log_level}")
    except AttributeError:
        logger.error(
            f"Nivel de logging inválido: {args.log_level}. Usando INFO por defecto."
        )

    logger.error(
        f"CRITICAL_DEBUG_INIT_ANALYSIS_END: Args parseados en initialize_analysis: {args}"
    )

    clean_filename_suffix = ""
    analysis_title_suffix = ""

    if args.mes:
        month_input = args.mes.strip().lower()
        month_number = None
        month_name_display = None
        try:
            month_number = int(month_input)
            if not (1 <= month_number <= 12):
                logger.error(
                    f"Número de mes inválido: {month_number}. No se aplicará filtro de mes."
                )
                args.mes = None
            else:
                month_names_list = [
                    "Enero",
                    "Febrero",
                    "Marzo",
                    "Abril",
                    "Mayo",
                    "Junio",
                    "Julio",
                    "Agosto",
                    "Septiembre",
                    "Octubre",
                    "Noviembre",
                    "Diciembre",
                ]
                month_name_display = month_names_list[month_number - 1]
        except ValueError:
            month_number = MONTH_NAMES_MAP.get(month_input)
            if not month_number:
                logger.error(
                    f"Nombre de mes inválido: '{args.mes}'. No se aplicará filtro de mes."
                )
                args.mes = None
            else:
                month_name_display = month_input.capitalize()

        if args.mes and month_number:
            args.month_number = month_number  # Guardar en args para uso en app.py
            args.month_name_display = month_name_display
            logger.info(
                f"Filtro de mes activado para: {month_name_display} (mes {month_number})"
            )
            clean_filename_suffix += (
                f"_mes_{month_name_display.lower().replace(' ', '_')}"
            )
            analysis_title_suffix += f" (Mes: {month_name_display})"
    else:
        args.month_number = None
        args.month_name_display = None

    if args.status_filter:  # Para el sufijo global si se usa este filtro desde CLI
        suffix_text = "_" + "_".join(args.status_filter).lower().replace(" ", "_")
        clean_filename_suffix += suffix_text
        analysis_title_suffix += f" (CLI Filtrado: {', '.join(args.status_filter)})"

    return args, clean_filename_suffix, analysis_title_suffix


def _apply_status_filters_for_period(
    df: pl.DataFrame, period_name: str, config: Dict
) -> Dict[str, pl.DataFrame]:
    """
    Aplica los filtros de estado (todas, completadas, canceladas) para un periodo dado.
    Devuelve un diccionario con los dataframes filtrados.
    """
    datasets = {}
    status_column = (
        "status"  # Usar 'status' directamente, ya que app.py lo estandariza.
    )

    datasets["todas"] = df.clone()
    logger.info(
        f"Dataset para '{period_name} - todas' preparado con {df.height} filas."
    )

    df_schema = df.schema  # Usar para crear DFs vacíos si es necesario

    if status_column in df.columns:
        completed_df = df.filter(
            pl.col(status_column).str.to_titlecase().str.strip_chars() == "Completed"
        )
        datasets["completadas"] = completed_df.clone()
        logger.info(
            f"Dataset para '{period_name} - completadas' preparado con {completed_df.height} filas."
        )

        cancelled_df = df.filter(
            pl.col(status_column).str.to_titlecase().str.strip_chars() == "Cancelled"
        )
        datasets["canceladas"] = cancelled_df.clone()
        logger.info(
            f"Dataset para '{period_name} - canceladas' preparado con {cancelled_df.height} filas."
        )
    else:
        logger.warning(
            f"Columna de estado '{status_column}' no encontrada. No se puede filtrar por 'Completed' o 'Cancelled' para '{period_name}'. Se crearán DataFrames vacíos."
        )
        datasets["completadas"] = pl.DataFrame(schema=df_schema)
        datasets["canceladas"] = pl.DataFrame(schema=df_schema)

    return datasets


def execute_analysis(
    df: pl.DataFrame,
    col_map: dict,  # Este es el col_map de la config
    config: dict,
    cli_args: argparse.Namespace,
    output_dir: str,
    clean_filename_suffix_cli: str,
    analysis_title_suffix_cli: str,
) -> None:
    """
    Ejecuta el pipeline de análisis principal, iterando por años y estados.
    """
    logger.error(
        f"CRITICAL_DEBUG_EXEC_ANALYSIS_START: ENTERING execute_analysis. cli_args.out (base global): {getattr(cli_args, 'out', 'N/A')}, output_dir (categoría): {output_dir}"
    )
    logger.error(
        f"CRITICAL_DEBUG_EXEC_ANALYSIS_START: df shape: {df.shape}, df columns: {df.columns}"
    )
    if "Year" in df.columns:
        try:
            unique_years_df = (
                df.select(pl.col("Year").unique().sort(nulls_last=True))
                .to_series()
                .to_list()
            )
            logger.error(
                f"CRITICAL_DEBUG_EXEC_ANALYSIS_START: Initial 'Year' unique values in df for this category: {unique_years_df}"
            )
        except Exception as e_year_exc:
            logger.error(
                f"CRITICAL_DEBUG_EXEC_ANALYSIS_START: Error getting unique years from df: {e_year_exc}"
            )
    else:
        logger.error(
            "CRITICAL_DEBUG_EXEC_ANALYSIS_START: 'Year' column NOT in df.columns at start of execute_analysis for this category."
        )

    years_to_analyze: List[str]
    if cli_args.no_annual_breakdown:
        logger.error(
            "CRITICAL_DEBUG_YEARS: Análisis SIN desglose anual (solo total) debido a --no-annual-breakdown."
        )
        years_to_analyze = ["total"]
    elif cli_args.year and cli_args.year.lower() != "all":
        try:
            year_int = int(cli_args.year)
            logger.error(
                f"CRITICAL_DEBUG_YEARS: Análisis para el año específico {year_int} y 'total' debido a --year={cli_args.year}."
            )
            years_to_analyze = [str(year_int), "total"]
        except ValueError:
            logger.error(
                f"CRITICAL_DEBUG_YEARS: --year inválido ('{cli_args.year}'). Comportamiento por defecto: todos los años disponibles y 'total'."
            )
            if "Year" in df.columns and df["Year"].dtype in [
                pl.Int64,
                pl.Int32,
                pl.Int16,
                pl.Int8,
                pl.UInt64,
                pl.UInt32,
                pl.UInt16,
                pl.UInt8,
            ]:
                years_available = sorted(
                    [
                        str(y)
                        for y in df.select(pl.col("Year").unique())
                        .drop_nulls()
                        .to_series()
                        .to_list()
                        if isinstance(y, int) and not isinstance(y, bool)
                    ]
                )
                years_to_analyze = (
                    years_available + ["total"] if years_available else ["total"]
                )
                logger.error(
                    f"CRITICAL_DEBUG_YEARS: Años disponibles (fallback de ValueError en --year): {years_available}. Analizando: {years_to_analyze}"
                )
            else:
                logger.error(
                    "CRITICAL_DEBUG_YEARS: Columna 'Year' no disponible/no numérica para fallback de --year. Analizando solo 'total'."
                )
                years_to_analyze = ["total"]
    else:
        logger.error(
            "CRITICAL_DEBUG_YEARS: Análisis para todos los años disponibles y 'total' (default o --year=all o --year no especificado)."
        )
    # --- CORRECCIÓN: Solo usar todos los años disponibles si no se especificó --year y no se omitió desglose anual ---
    if (
        not cli_args.year or cli_args.year.lower() == "all"
    ) and not cli_args.no_annual_breakdown:
        if "Year" in df.columns and df["Year"].dtype in [
            pl.Int64,
            pl.Int32,
            pl.Int16,
            pl.Int8,
            pl.UInt64,
            pl.UInt32,
            pl.UInt16,
            pl.UInt8,
        ]:
            years_available = sorted(
                [
                    str(y)
                    for y in df.select(pl.col("Year").unique())
                    .drop_nulls()
                    .to_series()
                    .to_list()
                    if isinstance(y, int) and not isinstance(y, bool)
                ]
            )
            if years_available:
                years_to_analyze = years_available + ["total"]
                logger.error(
                    f"CRITICAL_DEBUG_YEARS: Años disponibles encontrados: {years_available}. Analizando: {years_to_analyze}"
                )
            else:
                logger.error(
                    "CRITICAL_DEBUG_YEARS: No se encontraron años válidos en 'Year'. Analizando solo 'total'."
                )
                years_to_analyze = ["total"]
        else:
            logger.error(
                "CRITICAL_DEBUG_YEARS: Columna 'Year' no disponible/no numérica para desglose. Analizando solo 'total'."
            )
            years_to_analyze = ["total"]

    logger.error(
        f"CRITICAL_DEBUG_YEARS: Final decision - Years to analyze: {years_to_analyze}"
    )

    all_period_data_for_unified_report: Dict[str, Dict[str, Dict[str, Any]]] = {}

    for year_period in years_to_analyze:
        logger.error(
            f"CRITICAL_DEBUG_LOOP: Iniciando ciclo para el periodo: {year_period}"
        )

        period_specific_output_path = Path(output_dir) / year_period
        # No crear aquí, save_outputs creará subdirectorios "reports", "tables", "figures" dentro de status_specific_output_path

        df_for_this_period: pl.DataFrame
        if year_period == "total":
            df_for_this_period = df.clone()
            logger.error(
                f"CRITICAL_DEBUG_FILTER: Para periodo '{year_period}', usando df de categoría original. Shape: {df_for_this_period.shape}"
            )
        else:
            if "Year" in df.columns and df["Year"].dtype in [
                pl.Int64,
                pl.Int32,
                pl.Int16,
                pl.Int8,
                pl.UInt64,
                pl.UInt32,
                pl.UInt16,
                pl.UInt8,
            ]:
                try:
                    current_year_int = int(year_period)
                    df_for_this_period = df.filter(
                        pl.col("Year") == current_year_int
                    ).clone()
                    logger.error(
                        f"CRITICAL_DEBUG_FILTER: Para periodo '{year_period}', df filtrado por año. Shape: {df_for_this_period.shape}"
                    )
                    if df_for_this_period.is_empty():
                        logger.warning(
                            f"No hay datos para el año {year_period} después de filtrar. Se omitirá el análisis detallado."
                        )
                        all_period_data_for_unified_report[year_period] = {}
                        continue
                except ValueError:
                    logger.error(
                        f"CRITICAL_DEBUG_FILTER: Error convirtiendo '{year_period}' a int. Saltando."
                    )
                    all_period_data_for_unified_report[year_period] = {}
                    continue
            else:
                logger.error(
                    f"CRITICAL_DEBUG_FILTER: Columna 'Year' no disponible/tipo incorrecto para filtrar '{year_period}'. Saltando."
                )
                all_period_data_for_unified_report[year_period] = {}
                continue

        logger.error(
            f"CRITICAL_DEBUG_PRE_STATUS_FILTER: Llegando al punto de llamar a _apply_status_filters_for_period para el periodo: {year_period}. Shape de df_for_this_period: {df_for_this_period.shape if 'df_for_this_period' in locals() else 'df_for_this_period no definido'}"
        )
        datasets_for_period_and_statuses = _apply_status_filters_for_period(
            df_for_this_period, year_period, config
        )

        # Inicializar el diccionario para el periodo actual ANTES del bucle de status
        all_period_data_for_unified_report[year_period] = {}

        for (
            status_name,
            df_to_analyze_for_status,
        ) in datasets_for_period_and_statuses.items():
            if df_to_analyze_for_status.is_empty():
                logger.info(
                    f"No hay datos para '{year_period} - {status_name}'. Se omite análisis detallado."
                )
                # Aún así, podríamos querer una entrada vacía o con un df vacío para el reporte unificado
                all_period_data_for_unified_report[year_period][status_name] = {
                    "df": df_to_analyze_for_status.clone(),  # DataFrame vacío
                    "metrics": {},  # Métricas vacías
                }
                continue

            logger.info(
                f"\n--- INICIO: Procesamiento Detallado para: {year_period.upper()} - {status_name.upper()} ---"
            )
            logger.info(
                f"  Analizando: {year_period} - {status_name} ({df_to_analyze_for_status.height} filas)"
            )

            status_specific_output_path = period_specific_output_path / status_name

            analysis_results_tuple = analyze(
                df=df_to_analyze_for_status.clone(),
                col_map=col_map,
                sell_config=config,
                cli_args=cli_args,
            )
            (
                processed_df_from_analyze,
                metrics_dict_from_analyze,
            ) = analysis_results_tuple

            # Guardar en la estructura correcta para el reporte unificado
            all_period_data_for_unified_report[year_period][status_name] = {
                "df": processed_df_from_analyze.clone(),
                "metrics": metrics_dict_from_analyze,
            }

            save_outputs(
                metrics_to_save=metrics_dict_from_analyze,
                df_to_plot_from=processed_df_from_analyze.clone(),
                config=config,
                base_output_dir=output_dir,
                output_label=year_period,
                status_subdir=status_name,
                cli_args=cli_args,
                col_map=col_map,
                file_name_suffix_from_cli=clean_filename_suffix_cli,
                title_suffix_from_cli=analysis_title_suffix_cli,
            )
            logger.info(
                f"  \u2705 Guardado y finalizado: {year_period} - {status_name}"
            )

    if not cli_args.no_unified_report:
        logger.info(
            "\n\U0001f680 Generando reporte unificado global con gráficos consolidados..."
        )

        reporter_unificado = UnifiedReporter(
            base_output_dir=output_dir, config=config, cli_args=cli_args
        )
        unified_html_path = reporter_unificado.generate_unified_report(
            all_period_data=all_period_data_for_unified_report
        )
        logger.info(
            f"  \u2705 Reporte unificado global completado. Verificar en: {unified_html_path}"
        )
    else:
        logger.info(
            "Generación de reporte unificado global omitida (--no-unified-report)."
        )


# No es necesario _execute_unified_only_analysis aquí si app.py lo maneja.

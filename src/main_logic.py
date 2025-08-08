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
import warnings

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
    logger.debug("CRITICAL_DEBUG_INIT_ANALYSIS_START: Entrando a initialize_analysis")
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

    # La configuración de logging se realiza centralizadamente en app.py
    logger.debug(
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


class AnalysisRunner:
    """
    Clase que encapsula la orquestación de análisis por años y estados.
    """

    def __init__(
        self,
        df: pl.DataFrame,
        col_map: dict,
        config: dict,
        cli_args: argparse.Namespace,
        output_dir: str,
        clean_filename_suffix_cli: str,
        analysis_title_suffix_cli: str,
    ):
        self.df = df
        self.col_map = col_map
        self.config = config
        self.cli_args = cli_args
        self.output_dir = output_dir
        self.clean_filename_suffix_cli = clean_filename_suffix_cli
        self.analysis_title_suffix_cli = analysis_title_suffix_cli

    def run(self) -> None:
        """
        Lanza el análisis principal para el DataFrame configurado.
        """
        execute_analysis(
            df=self.df,
            col_map=self.col_map,
            config=self.config,
            cli_args=self.cli_args,
            output_dir=self.output_dir,
            clean_filename_suffix_cli=self.clean_filename_suffix_cli,
            analysis_title_suffix_cli=self.analysis_title_suffix_cli,
        )

    def _determine_years(self) -> list[str]:
        """
        Determina la lista de años a analizar según los argumentos CLI.
        """
        cli = self.cli_args
        df = self.df
        years_to_analyze: list[str]
        # Si no se desea desglose anual
        if cli.no_annual_breakdown:
            years_to_analyze = ["total"]
        # Año específico indicado
        elif cli.year and cli.year.lower() != "all":
            try:
                year_int = int(cli.year)
                years_to_analyze = [str(year_int), "total"]
            except ValueError:
                years_to_analyze = [
                    str(y)
                    for y in df.select(pl.col("Year")).to_series().to_list()
                    if isinstance(y, int)
                ] + ["total"]
        # Default: todos los años + total
        else:
            unique_years = []
            if "Year" in df.columns:
                unique_years = [
                    str(y)
                    for y in df.select(pl.col("Year").unique()).to_series().to_list()
                    if isinstance(y, int)
                ]
            years_to_analyze = unique_years + ["total"]
        return years_to_analyze


def execute_analysis(
    *,
    df: pl.DataFrame,
    col_map: Dict,
    config: Dict,
    cli_args: argparse.Namespace,
    output_dir: str,
    clean_filename_suffix_cli: str,
    analysis_title_suffix_cli: str,
) -> None:
    """
    Orquesta el análisis por año y estado y genera salidas y reporte unificado.

    Esta función existe para compatibilidad con tests y para facilitar su reuse.
    """
    all_period_data: Dict[str, Dict[str, Any]] = {}

    # Determinar años a analizar (reutiliza la lógica de AnalysisRunner)
    def _determine_years_local() -> list[str]:
        if cli_args.no_annual_breakdown:
            return ["total"]
        elif cli_args.year and str(cli_args.year).lower() != "all":
            try:
                year_int = int(cli_args.year)
                return [str(year_int), "total"]
            except ValueError:
                years = [
                    str(y)
                    for y in df.select(pl.col("Year")).to_series().to_list()
                    if isinstance(y, int)
                ]
                return years + ["total"]
        else:
            unique_years = []
            if "Year" in df.columns:
                unique_years = [
                    str(y)
                    for y in df.select(pl.col("Year").unique()).to_series().to_list()
                    if isinstance(y, int)
                ]
            return unique_years + ["total"]

    years = _determine_years_local()

    for year in years:
        period_output = Path(output_dir) / year
        # Preparar DataFrame para este periodo
        if year == "total":
            df_period = df.clone()
        else:
            df_period = (
                df.filter(pl.col("Year") == int(year)).clone()
                if "Year" in df.columns
                else df.clone()
            )

        # Aplicar filtros de estado
        status_datasets = _apply_status_filters_for_period(df_period, year, config)
        all_period_data[year] = {}

        for status, df_status in status_datasets.items():
            if df_status.is_empty():
                all_period_data[year][status] = {
                    "df": df_status.clone(),
                    "metrics": {},
                }
                continue

            processed_df, metrics = analyze(
                df=df_status.clone(),
                col_map=col_map,
                sell_config=config,
                cli_args=cli_args,
            )

            all_period_data[year][status] = {
                "df": processed_df.clone(),
                "metrics": metrics,
            }

            save_outputs(
                metrics_to_save=metrics,
                df_to_plot_from=processed_df.clone(),
                config=config,
                base_output_dir=str(period_output),
                output_label=year,
                status_subdir=status,
                cli_args=cli_args,
                col_map=col_map,
                file_name_suffix_from_cli=clean_filename_suffix_cli,
                title_suffix_from_cli=analysis_title_suffix_cli,
            )

    # Generar reporte unificado global
    if not getattr(cli_args, "no_unified_report", False):
        reporter = UnifiedReporter(str(output_dir), config, cli_args)
        reporter.generate_unified_report(all_period_data)

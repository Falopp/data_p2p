import os
import logging
import datetime
import polars as pl
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import argparse 
import pathlib
from typing import Dict, List, Any, Tuple, Union
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from . import plotting 
from . import counterparty_plotting
from . import utils

logger = logging.getLogger(__name__)

class UnifiedReporter:
    """
    Generador de reportes unificados que consolida análisis por periodo y estado
    en una estructura más limpia manteniendo separación USD/UYU.
    """
    
    def __init__(self, base_output_dir: str, config: dict, cli_args: argparse.Namespace):
        self.base_output_dir = base_output_dir
        self.config = config
        self.cli_args = cli_args
        
        # Estructura unificada más simple
        self.structure = {
            'consolidated': os.path.join(base_output_dir, 'consolidated'),
            'figures': {
                'usd_analysis': os.path.join(base_output_dir, 'figures', 'usd_analysis'),
                'uyu_analysis': os.path.join(base_output_dir, 'figures', 'uyu_analysis'),
                'comparative': os.path.join(base_output_dir, 'figures', 'comparative'),
                'general': os.path.join(base_output_dir, 'figures', 'general'),
                'counterparty': os.path.join(base_output_dir, 'figures', 'counterparty'),
                'sessions': os.path.join(base_output_dir, 'figures', 'sessions')
            },
            'reports': os.path.join(base_output_dir, 'reports'),
            'data_exports': os.path.join(base_output_dir, 'data_exports')
        }
        
        # Crear estructura de directorios
        self._create_directory_structure()
        
    def _create_directory_structure(self):
        """Crea la estructura de directorios unificada."""
        for path in [self.structure['consolidated'], self.structure['reports'], self.structure['data_exports']]:
            os.makedirs(path, exist_ok=True)
        
        for fig_dir in self.structure['figures'].values():
            os.makedirs(fig_dir, exist_ok=True)
            
    def generate_unified_report(self, all_period_data: Dict[str, Dict[str, Any]]) -> str:
        """
        Genera un reporte HTML unificado con todas las temporalidades y estados.
        
        Args:
            all_period_data: {
                'period_name': {
                    'status_name': {
                        'df': pl.DataFrame,
                        'metrics': Dict[str, pl.DataFrame]
                    }
                }
            }
        """
        logger.info("Iniciando generación de reporte unificado...")
        
        # 1. Generar gráficos consolidados por categoría
        figure_paths = self._generate_consolidated_figures(all_period_data)
        
        # 2. Crear Excel multi-periodo consolidado
        excel_path = self._generate_consolidated_excel(all_period_data)
        
        # 3. Generar HTML unificado con navegación
        html_path = self._generate_unified_html(all_period_data, figure_paths, excel_path)
        
        logger.info(f"Reporte unificado completado: {html_path}")
        return html_path
        
    def _generate_consolidated_figures(self, all_period_data: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """Genera gráficos consolidados organizados por categoría temática."""
        logger.info("Generando figuras consolidadas por categoría...")
        
        figure_paths = {
            'usd_analysis': [],
            'uyu_analysis': [],
            'comparative': [],
            'general': [],
            'counterparty': [],
            'sessions': []
        }
        
        # 1. ANÁLISIS USD: Consolidar todos los periodos en gráficos USD
        usd_data_consolidated = self._consolidate_currency_data(all_period_data, 'USD')
        if not usd_data_consolidated.is_empty():
            usd_figures = self._generate_currency_specific_plots(
                usd_data_consolidated, 
                self.structure['figures']['usd_analysis'],
                'USD',
                'Análisis Consolidado USD/USDT'
            )
            figure_paths['usd_analysis'].extend(usd_figures)
            
        # 2. ANÁLISIS UYU: Consolidar todos los periodos en gráficos UYU  
        uyu_data_consolidated = self._consolidate_currency_data(all_period_data, 'UYU')
        if not uyu_data_consolidated.is_empty():
            uyu_figures = self._generate_currency_specific_plots(
                uyu_data_consolidated,
                self.structure['figures']['uyu_analysis'], 
                'UYU',
                'Análisis Consolidado UYU'
            )
            figure_paths['uyu_analysis'].extend(uyu_figures)
            
        # 3. ANÁLISIS COMPARATIVO: USD vs UYU lado a lado
        comparative_figures = self._generate_comparative_plots(
            usd_data_consolidated, 
            uyu_data_consolidated,
            self.structure['figures']['comparative']
        )
        figure_paths['comparative'].extend(comparative_figures)
        
        # 4. ANÁLISIS GENERAL: Métricas que no dependen de moneda
        general_figures = self._generate_general_plots(
            all_period_data,
            self.structure['figures']['general']
        )
        figure_paths['general'].extend(general_figures)
        
        # 5. ANÁLISIS DE CONTRAPARTES: Consolidado
        logger.info("Iniciando generación de gráficos consolidados de contrapartes...")
        counterparty_figures = self._generate_consolidated_counterparty_plots(
            all_period_data,
            self.structure['figures']['counterparty']
        )
        figure_paths['counterparty'].extend(counterparty_figures)
        
        # 6. ANÁLISIS DE SESIONES: Consolidado
        session_figures = self._generate_consolidated_session_plots(
            all_period_data,
            self.structure['figures']['sessions']
        )
        figure_paths['sessions'].extend(session_figures)
        
        return figure_paths
        
    def _consolidate_currency_data(self, all_period_data: Dict, currency: str) -> pl.DataFrame:
        """Consolida datos de una moneda específica de todos los periodos."""
        logger.info(f"Consolidando datos para {currency}...")
        
        all_dfs = []
        for period_name, period_data in all_period_data.items():
            for status_name, status_data in period_data.items():
                current_df = pl.DataFrame() # Inicializar como DataFrame vacío
                if isinstance(status_data, dict):
                    current_df = status_data.get('df', pl.DataFrame())
                elif isinstance(status_data, pl.DataFrame): # Asumiendo que pl es polars
                    current_df = status_data
                else:
                    logger.warning(
                        f"En _consolidate_currency_data para periodo '{period_name}', status '{status_name}': "
                        f"status_data es de tipo inesperado {type(status_data)}. Se usará DataFrame vacío."
                    )

                if not current_df.is_empty() and 'fiat_type' in current_df.columns:
                    # Filtrar por moneda y añadir metadatos
                    currency_df = current_df.filter(pl.col('fiat_type') == currency).with_columns([
                        pl.lit(period_name).alias('period_source'),
                        pl.lit(status_name).alias('status_source')
                    ])
                    if not currency_df.is_empty():
                        all_dfs.append(currency_df)
                        
        if all_dfs:
            consolidated = pl.concat(all_dfs, how='vertical')
            logger.info(f"Consolidados {consolidated.height} registros para {currency}")
            return consolidated
        else:
            logger.warning(f"No se encontraron datos para {currency}")
            return pl.DataFrame()
            
    def _generate_currency_specific_plots(self, df: pl.DataFrame, out_dir: str, 
                                        currency: str, title_suffix: str) -> List[str]:
        """Genera gráficos específicos para una moneda consolidando todos los periodos."""
        saved_paths = []
        
        if df.is_empty():
            return saved_paths
            
        df_pandas = df.to_pandas()
        
        # 1. Evolución temporal por periodo y estado
        if 'Match_time_local' in df_pandas.columns and 'TotalPrice_num' in df_pandas.columns:
            fig, axes = plt.subplots(2, 2, figsize=(16, 12))
            fig.suptitle(f'Evolución Temporal - {title_suffix}', fontsize=16, fontweight='bold')
            
            # Por periodo
            axes[0,0].set_title('Volumen por Periodo')
            period_volume = df_pandas.groupby(['period_source', df_pandas['Match_time_local'].dt.to_period('M')])['TotalPrice_num'].sum().unstack(level=0, fill_value=0)
            if not period_volume.empty:
                period_volume.plot(ax=axes[0,0], marker='o')
                axes[0,0].legend(title='Periodo')
                
            # Por estado
            axes[0,1].set_title('Volumen por Estado')
            status_volume = df_pandas.groupby(['status_source', df_pandas['Match_time_local'].dt.to_period('M')])['TotalPrice_num'].sum().unstack(level=0, fill_value=0)
            if not status_volume.empty:
                status_volume.plot(ax=axes[0,1], marker='s')
                axes[0,1].legend(title='Estado')
                
            # Distribución de precios
            axes[1,0].set_title('Distribución de Precios')
            if 'Price_num' in df_pandas.columns:
                df_pandas['Price_num'].hist(bins=50, ax=axes[1,0], alpha=0.7)
                
            # Volumen vs Precio
            axes[1,1].set_title('Volumen vs Precio')
            if 'Price_num' in df_pandas.columns:
                axes[1,1].scatter(df_pandas['Price_num'], df_pandas['TotalPrice_num'], alpha=0.5)
                axes[1,1].set_xlabel('Precio')
                axes[1,1].set_ylabel('Volumen Total')
                
            plt.tight_layout()
            path = os.path.join(out_dir, f'temporal_evolution_{currency.lower()}.png')
            plt.savefig(path, dpi=300, bbox_inches='tight')
            plt.close()
            saved_paths.append(path)
            
        # 2. Heatmap consolidado de actividad
        if 'Match_time_local' in df_pandas.columns:
            path_heatmap = self._generate_consolidated_heatmap(df_pandas, out_dir, currency, title_suffix)
            if path_heatmap:
                saved_paths.append(path_heatmap)
                
        # 3. Análisis de métodos de pago
        if 'payment_method' in df_pandas.columns:
            path_payment = self._generate_payment_analysis(df_pandas, out_dir, currency, title_suffix)
            if path_payment:
                saved_paths.append(path_payment)
                
        return saved_paths
        
    def _generate_comparative_plots(self, usd_df: pl.DataFrame, uyu_df: pl.DataFrame, out_dir: str) -> List[str]:
        """Genera gráficos comparativos USD vs UYU."""
        saved_paths = []
        
        if usd_df.is_empty() or uyu_df.is_empty():
            logger.warning("Datos insuficientes para análisis comparativo USD vs UYU")
            return saved_paths
            
        # Convertir a pandas para manipulación
        usd_pandas = usd_df.to_pandas()
        uyu_pandas = uyu_df.to_pandas()
        
        # 1. Comparación de volúmenes mensuales
        if all(col in usd_pandas.columns for col in ['Match_time_local', 'TotalPrice_num']):
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
            fig.suptitle('Comparación USD vs UYU - Volúmenes Mensuales', fontsize=16, fontweight='bold')
            
            # Volumen USD
            usd_monthly = usd_pandas.groupby(usd_pandas['Match_time_local'].dt.to_period('M'))['TotalPrice_num'].sum()
            usd_monthly.plot(ax=ax1, color='green', marker='o', title='Volumen USD/USDT')
            ax1.set_ylabel('Volumen USD')
            
            # Volumen UYU  
            uyu_monthly = uyu_pandas.groupby(uyu_pandas['Match_time_local'].dt.to_period('M'))['TotalPrice_num'].sum()
            uyu_monthly.plot(ax=ax2, color='blue', marker='s', title='Volumen UYU')
            ax2.set_ylabel('Volumen UYU')
            
            plt.tight_layout()
            path = os.path.join(out_dir, 'usd_vs_uyu_volumes.png')
            plt.savefig(path, dpi=300, bbox_inches='tight')
            plt.close()
            saved_paths.append(path)
            
        # 2. Comparación de número de operaciones
        fig, ax = plt.subplots(figsize=(12, 6))
        
        usd_ops = usd_pandas.groupby(usd_pandas['Match_time_local'].dt.to_period('M')).size()
        uyu_ops = uyu_pandas.groupby(uyu_pandas['Match_time_local'].dt.to_period('M')).size()
        
        ax.plot(usd_ops.index.astype(str), usd_ops.values, marker='o', label='Operaciones USD/USDT', color='green')
        ax.plot(uyu_ops.index.astype(str), uyu_ops.values, marker='s', label='Operaciones UYU', color='blue')
        
        ax.set_title('Comparación USD vs UYU - Número de Operaciones', fontsize=14, fontweight='bold')
        ax.set_ylabel('Número de Operaciones')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        path = os.path.join(out_dir, 'usd_vs_uyu_operations.png')
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        saved_paths.append(path)
        
        return saved_paths
        
    def _generate_general_plots(self, all_period_data: Dict, out_dir: str) -> List[str]:
        """Genera gráficos generales consolidados (ej: todos los periodos, todos los status)."""
        figures = []
        dfs_to_concat = []

        # Recolectar todos los DataFrames relevantes
        for period_name, period_item in all_period_data.items():
            for status_name, status_data in period_item.items():
                current_df = pl.DataFrame() # Inicializar como DataFrame vacío
                if isinstance(status_data, dict):
                    current_df = status_data.get('df', pl.DataFrame())
                elif isinstance(status_data, pl.DataFrame): # Asumiendo que pl es polars
                    current_df = status_data
                else:
                    logger.warning(
                        f"En _generate_general_plots para periodo '{period_name}', status '{status_name}': "
                        f"status_data es de tipo inesperado {type(status_data)}. Se usará DataFrame vacío."
                    )

                if not current_df.is_empty():
                    dfs_to_concat.append(current_df.clone().with_columns([
                        pl.lit(period_name).alias("period_source"),
                        pl.lit(status_name).alias("status_source")
                    ]))

        if not dfs_to_concat:
            return figures

        consolidated_df = pl.concat(dfs_to_concat, how='vertical')
        consolidated_pandas = consolidated_df.to_pandas()
        
        # 1. Resumen de estados por periodo
        if 'status' in consolidated_pandas.columns:
            fig, ax = plt.subplots(figsize=(12, 8))
            
            status_period = consolidated_pandas.groupby(['period_source', 'status']).size().unstack(fill_value=0)
            status_period.plot(kind='bar', ax=ax, stacked=True)
            
            ax.set_title('Distribución de Estados por Periodo', fontsize=14, fontweight='bold')
            ax.set_ylabel('Número de Operaciones')
            ax.legend(title='Estado')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            path = os.path.join(out_dir, 'status_distribution_by_period.png')
            plt.savefig(path, dpi=300, bbox_inches='tight')
            plt.close()
            figures.append(path)
            
        # 2. Evolución de activos
        if 'asset_type' in consolidated_pandas.columns and 'Match_time_local' in consolidated_pandas.columns:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            asset_monthly = consolidated_pandas.groupby([
                consolidated_pandas['Match_time_local'].dt.to_period('M'),
                'asset_type'
            ]).size().unstack(fill_value=0)
            
            asset_monthly.plot(ax=ax, marker='o')
            ax.set_title('Evolución de Operaciones por Tipo de Activo', fontsize=14, fontweight='bold')
            ax.set_ylabel('Número de Operaciones')
            ax.legend(title='Activo')
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            path = os.path.join(out_dir, 'asset_evolution.png')
            plt.savefig(path, dpi=300, bbox_inches='tight')
            plt.close()
            figures.append(path)
            
        return figures
        
    def _generate_consolidated_counterparty_plots(self, all_period_data: Dict, out_dir: str) -> List[str]:
        """Genera análisis consolidado de contrapartes."""
        logger.info("Consolidando datos de contrapartes para gráficos...")
        
        # Claves esperadas del diccionario de datos de contrapartes
        # (basado en lo que devuelve counterparty_analyzer.analyze_counterparties y usa counterparty_plotting)
        counterparty_metric_keys = [
            'general_stats', 'temporal_evolution', 'payment_preferences', 
            'trading_patterns', 'vip_counterparties', 'efficiency_stats', 
            'activity_matrix' # Aunque no todas se grafican directamente por generate_all_counterparty_plots
        ]
        
        consolidated_cp_data_pl = {key: [] for key in counterparty_metric_keys}
        
        has_any_cp_data = False
        for period_name, period_data in all_period_data.items():
            for status_name, status_data in period_data.items():
                metrics = {}  # Inicializar metrics como un diccionario vacío
                if isinstance(status_data, dict):
                    metrics = status_data.get('metrics', {})
                elif isinstance(status_data, pl.DataFrame): # Asumiendo que pl es polars
                    logger.warning(
                        f"En _generate_consolidated_counterparty_plots para periodo '{period_name}', status '{status_name}': "
                        f"status_data es un DataFrame y se esperaba un dict. No se pueden extraer métricas de contraparte."
                    )
                    # metrics permanece como un diccionario vacío, el bucle interno no encontrará claves.
                else:
                    logger.warning(
                        f"En _generate_consolidated_counterparty_plots para periodo '{period_name}', status '{status_name}': "
                        f"status_data es de tipo inesperado ({type(status_data)}). No se pueden extraer métricas."
                    )

                # Las métricas de contrapartes están prefijadas con 'counterparty_'
                for key in counterparty_metric_keys:
                    metric_df_pl = metrics.get(f'counterparty_{key}') # Usará 'metrics' de forma segura
                    if metric_df_pl is not None and isinstance(metric_df_pl, pl.DataFrame) and not metric_df_pl.is_empty():
                        # Añadir metadatos de origen si es útil y no rompe el esquema esperado por plotting
                        # Por ahora, asumimos que los esquemas son compatibles para concatenar.
                        # Si las funciones de plotting no esperan 'period_source' o 'status_source', esto podría ser un problema.
                        # metric_df_pl_with_meta = metric_df_pl.with_columns([
                        #     pl.lit(period_name).alias('period_source'),
                        #     pl.lit(status_name).alias('status_source')
                        # ])
                        consolidated_cp_data_pl[key].append(metric_df_pl)
                        has_any_cp_data = True

        if not has_any_cp_data:
            logger.warning("No se encontraron datos de métricas de contrapartes en ningún periodo/estado.")
            return []

        final_cp_data_pd = {}
        for key, df_list in consolidated_cp_data_pl.items():
            if df_list:
                # Concatenar todos los DataFrames de Polars para esta métrica
                # Es crucial que los esquemas sean idénticos o compatibles.
                try:
                    combined_df_pl = pl.concat(df_list, how='vertical_relaxed') # relaxed para manejar pequeñas diferencias de esquema
                    # Algunas métricas pueden necesitar una re-agrupación si la concatenación crea duplicados o cambia la granularidad deseada.
                    # Por ejemplo, 'general_stats' debería ser por 'Counterparty' único globalmente.
                    if key == 'general_stats' and 'Counterparty' in combined_df_pl.columns:
                         # Re-agregar general_stats para tener una visión global única por contraparte
                         # Esto es una simplificación; la lógica de agregación real puede ser más compleja
                         # y debería replicar la que está en _calculate_general_counterparty_stats pero sobre el DF combinado.
                         # Por ahora, si se duplican contrapartes, los gráficos podrían mostrar datos inflados.
                         # Una solución más robusta sería tomar el df_processed completo, consolidarlo, y RECALCULAR las métricas de CP.
                         # Esto es complejo de hacer aquí. Optamos por un simple distinct por ahora.
                         # combined_df_pl = combined_df_pl.unique(subset=['Counterparty'], keep='first', maintain_order=False)
                         # Mejor aún, recalcular algunas métricas clave si es posible, o al menos loguear.
                         logger.warning(f"Métrica '{key}' concatenada. Si hay IDs de contraparte duplicados entre periodos/estados, "
                                        f"las estadísticas podrían no ser representativas de un 'global'. Se necesitaría re-agregación.")

                    final_cp_data_pd[key] = combined_df_pl.to_pandas()
                except Exception as e:
                    logger.error(f"Error al concatenar o convertir a Pandas la métrica de contraparte '{key}': {e}")
                    final_cp_data_pd[key] = pd.DataFrame() # DataFrame vacío si falla
            else:
                final_cp_data_pd[key] = pd.DataFrame()

        if not any(not df.empty for df in final_cp_data_pd.values()):
            logger.warning("Todos los DataFrames de métricas de contrapartes consolidados están vacíos después del procesamiento.")
            return []
            
        # Llamar a la función de plotting de contrapartes
        # El directorio de salida ya es específico para contrapartes (self.structure['figures']['counterparty'])
        # title_suffix y file_identifier pueden ser genéricos para la consolidación
        try:
            return counterparty_plotting.generate_all_counterparty_plots(
                counterparty_data=final_cp_data_pd,
                base_figures_dir=out_dir, # out_dir ya es el subdirectorio de contrapartes
                title_suffix=" (Consolidado)",
                file_identifier="_consolidated"
            )
        except Exception as e:
            logger.error(f"Error al llamar a generate_all_counterparty_plots: {e}")
            return []
        
    def _generate_consolidated_session_plots(self, all_period_data: Dict, out_dir: str) -> List[str]:
        """Genera análisis consolidado de sesiones."""
        # Reutilizar la lógica existente pero consolidando datos  
        logger.info("Consolidando datos de sesiones para gráficos...")

        session_metric_keys = [
            'session_stats', 'session_patterns', 'session_efficiency',
            'counterparty_sessions', 'temporal_distribution', 'raw_sessions'
        ]
        consolidated_session_data_pl = {key: [] for key in session_metric_keys}
        has_any_session_data = False

        for period_name, period_data in all_period_data.items():
            for status_name, status_data in period_data.items():
                metrics = {} # Inicializar metrics como un diccionario vacío
                if isinstance(status_data, dict):
                    metrics = status_data.get('metrics', {})
                elif isinstance(status_data, pl.DataFrame): # Asumiendo que pl es polars
                    logger.warning(
                        f"En _generate_consolidated_session_plots para periodo '{period_name}', status '{status_name}': "
                        f"status_data es un DataFrame y se esperaba un dict. No se pueden extraer métricas de sesión."
                    )
                else:
                    logger.warning(
                        f"En _generate_consolidated_session_plots para periodo '{period_name}', status '{status_name}': "
                        f"status_data no es ni un dict ni un DataFrame Polars (tipo: {type(status_data)}). No se pueden extraer métricas de sesión."
                    )

                session_stats_df = metrics.get('session_session_stats')
                for key in session_metric_keys:
                    metric_df_pl = metrics.get(f'session_{key}')
                    if metric_df_pl is not None and isinstance(metric_df_pl, pl.DataFrame) and not metric_df_pl.is_empty():
                        consolidated_session_data_pl[key].append(metric_df_pl)
                        has_any_session_data = True
        
        if not has_any_session_data:
            logger.warning("No se encontraron datos de métricas de sesiones en ningún periodo/estado.")
            return []

        final_session_data_pd = {}
        for key, df_list in consolidated_session_data_pl.items():
            if df_list:
                try:
                    combined_df_pl = pl.concat(df_list, how='vertical_relaxed')
                    # Similar a contrapartes, 'session_stats' o 'raw_sessions' podrían necesitar un manejo especial
                    # si los IDs de sesión no son globalmente únicos (lo cual es probable si se recalculan por periodo).
                    # Para un análisis consolidado real de sesiones, lo ideal sería tomar el df_processed global
                    # y re-ejecutar session_analyzer.analyze_trading_sessions sobre él.
                    # Aquí, simplemente concatenamos y los gráficos mostrarán la unión de todas las sesiones identificadas.
                    if key == 'raw_sessions' and 'session_id' in combined_df_pl.columns:
                         # Si los session_id no son únicos globalmente, podríamos re-numerarlos.
                         # combined_df_pl = combined_df_pl.with_row_count(name='global_row_num_for_session_id_regen')
                         # Esto es solo un ejemplo, la lógica de regeneración de IDs de sesión sería más compleja.
                         pass
                    final_session_data_pd[key] = combined_df_pl.to_pandas()
                except Exception as e:
                    logger.error(f"Error al concatenar o convertir a Pandas la métrica de sesión '{key}': {e}")
                    final_session_data_pd[key] = pd.DataFrame()
            else:
                final_session_data_pd[key] = pd.DataFrame()

        if not any(not df.empty for df in final_session_data_pd.values()):
            logger.warning("Todos los DataFrames de métricas de sesiones consolidados están vacíos.")
            return []

        saved_paths = []
        
        # --- Gráficos específicos para Sesiones ---
        # Usaremos funciones de plotting.py adaptándolas o crearemos stubs aquí.
        
        # 1. Distribución de Duración de Sesiones (Histograma)
        if 'session_stats' in final_session_data_pd and not final_session_data_pd['session_stats'].empty:
            df_plot = final_session_data_pd['session_stats']
            if 'duration_minutes' in df_plot.columns:
                try:
                    plt.figure(figsize=(10, 6))
                    sns.histplot(df_plot['duration_minutes'].dropna(), bins=30, kde=True)
                    plt.title('Distribución de Duración de Sesiones (Consolidado)')
                    plt.xlabel('Duración (minutos)')
                    plt.ylabel('Frecuencia')
                    path = os.path.join(out_dir, 'session_duration_distribution_consolidated.png')
                    plt.savefig(path, dpi=300, bbox_inches='tight')
                    plt.close()
                    saved_paths.append(path)
                    logger.info(f"Gráfico de duración de sesiones guardado: {path}")
                except Exception as e_plot:
                    logger.error(f"Error generando gráfico de duración de sesiones: {e_plot}")

        # 2. Número de Operaciones por Sesión (Histograma)
        if 'session_stats' in final_session_data_pd and not final_session_data_pd['session_stats'].empty:
            df_plot = final_session_data_pd['session_stats']
            if 'num_operations' in df_plot.columns:
                try:
                    plt.figure(figsize=(10, 6))
                    sns.histplot(df_plot['num_operations'].dropna(), bins=30, kde=True)
                    plt.title('Distribución de Operaciones por Sesión (Consolidado)')
                    plt.xlabel('Número de Operaciones')
                    plt.ylabel('Frecuencia de Sesiones')
                    path = os.path.join(out_dir, 'session_operations_distribution_consolidated.png')
                    plt.savefig(path, dpi=300, bbox_inches='tight')
                    plt.close()
                    saved_paths.append(path)
                    logger.info(f"Gráfico de operaciones por sesión guardado: {path}")
                except Exception as e_plot:
                    logger.error(f"Error generando gráfico de operaciones por sesión: {e_plot}")

        # 3. Distribución de Inicio de Sesiones por Hora del Día
        if 'temporal_distribution' in final_session_data_pd and not final_session_data_pd['temporal_distribution'].empty:
            df_plot_raw = final_session_data_pd['temporal_distribution'] # Este ya está agregado por start_hour EN EL ANALIZADOR ORIGINAL
            if 'start_hour' in df_plot_raw.columns and 'num_sessions' in df_plot_raw.columns:
                try:
                    # CONSOLIDACIÓN: Agrupar por 'start_hour' y sumar 'num_sessions' porque df_plot_raw es una concatenación
                    # de múltiples análisis 'temporal_distribution', cada uno ya agrupado por hora.
                    df_plot_grouped = df_plot_raw.groupby('start_hour', as_index=False)['num_sessions'].sum()
                    
                    hourly_series = df_plot_grouped.set_index('start_hour')['num_sessions'].sort_index()
                    hourly_series_reindexed = hourly_series.reindex(range(24), fill_value=0)

                    plt.figure(figsize=(12, 7))
                    sns.barplot(x=hourly_series_reindexed.index, y=hourly_series_reindexed.values, color=sns.color_palette()[2])
                    plt.title('Distribución de Inicio de Sesiones por Hora (Consolidado)')
                    plt.xlabel('Hora de Inicio de Sesión')
                    plt.ylabel('Número de Sesiones')
                    plt.xticks(ticks=range(0,24,2))
                    path = os.path.join(out_dir, 'session_start_hour_distribution_consolidated.png')
                    plt.savefig(path, dpi=300, bbox_inches='tight')
                    plt.close()
                    saved_paths.append(path)
                    logger.info(f"Gráfico de inicio de sesiones por hora guardado: {path}")
                except Exception as e_plot:
                    logger.error(f"Error generando gráfico de inicio de sesiones por hora: {e_plot}")
        
        # Podríamos añadir más gráficos aquí basados en 'session_patterns', 'session_efficiency', etc.
        # Por ejemplo, un scatter plot de duración vs volumen de sesión.
        if 'session_stats' in final_session_data_pd and not final_session_data_pd['session_stats'].empty:
            df_plot = final_session_data_pd['session_stats']
            if 'duration_minutes' in df_plot.columns and 'total_volume' in df_plot.columns:
                try:
                    plt.figure(figsize=(10,6))
                    sns.scatterplot(data=df_plot, x='duration_minutes', y='total_volume', 
                                    size='num_operations', hue='dominant_fiat', alpha=0.7, sizes=(20, 200))
                    plt.title('Volumen vs Duración de Sesión (Consolidado)')
                    plt.xlabel('Duración (minutos)')
                    plt.ylabel('Volumen Total en Sesión')
                    plt.xscale('log') # A menudo útil para duraciones
                    plt.yscale('log') # A menudo útil para volúmenes
                    plt.legend(title='Moneda Dominante / Ops', bbox_to_anchor=(1.05, 1), loc='upper left')
                    path = os.path.join(out_dir, 'session_volume_vs_duration_consolidated.png')
                    plt.savefig(path, dpi=300, bbox_inches='tight')
                    plt.close()
                    saved_paths.append(path)
                    logger.info(f"Gráfico de volumen vs duración de sesión guardado: {path}")
                except Exception as e_plot:
                    logger.error(f"Error generando scatter de volumen vs duración de sesión: {e_plot}")

        logger.info(f"Generados {len(saved_paths)} gráficos de sesiones consolidados.")
        return saved_paths

    def _generate_consolidated_heatmap(self, df_pandas: pd.DataFrame, out_dir: str, 
                                     currency: str, title_suffix: str) -> Union[str, None]:
        """Genera heatmap consolidado de actividad."""
        if 'Match_time_local' not in df_pandas.columns:
            return None
            
        # Crear columnas de hora y día de la semana
        df_pandas['hour'] = df_pandas['Match_time_local'].dt.hour
        df_pandas['weekday'] = df_pandas['Match_time_local'].dt.day_name()
        
        # Crear matriz para heatmap
        heatmap_data = df_pandas.groupby(['weekday', 'hour']).size().unstack(fill_value=0)
        
        # Reordenar días de la semana
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = heatmap_data.reindex(day_order, fill_value=0)
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        sns.heatmap(heatmap_data, annot=True, fmt='d', cmap='YlOrRd', ax=ax)
        
        ax.set_title(f'Actividad por Hora y Día - {title_suffix}', fontsize=14, fontweight='bold')
        ax.set_xlabel('Hora del Día')
        ax.set_ylabel('Día de la Semana')
        
        plt.tight_layout()
        path = os.path.join(out_dir, f'activity_heatmap_{currency.lower()}.png')
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return path
        
    def _generate_payment_analysis(self, df_pandas: pd.DataFrame, out_dir: str,
                                 currency: str, title_suffix: str) -> str:
        """Genera análisis de métodos de pago."""
        if 'payment_method' not in df_pandas.columns or 'TotalPrice_num' not in df_pandas.columns:
            return None
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
        fig.suptitle(f'Análisis de Métodos de Pago - {title_suffix}', fontsize=16, fontweight='bold')
        
        # Distribución por número de operaciones
        payment_counts = df_pandas['payment_method'].value_counts()
        payment_counts.head(10).plot(kind='bar', ax=ax1)
        ax1.set_title('Top 10 Métodos por Número de Operaciones')
        ax1.set_ylabel('Número de Operaciones')
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Distribución por volumen
        payment_volume = df_pandas.groupby('payment_method')['TotalPrice_num'].sum().sort_values(ascending=False)
        payment_volume.head(10).plot(kind='bar', ax=ax2, color='orange')
        ax2.set_title('Top 10 Métodos por Volumen')
        ax2.set_ylabel(f'Volumen Total ({currency})')
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        path = os.path.join(out_dir, f'payment_methods_{currency.lower()}.png')
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return path
        
    def _generate_consolidated_excel(self, all_period_data: Dict) -> str:
        """Genera un Excel consolidado con múltiples hojas organizadas."""
        logger.info("Generando Excel consolidado...")
        
        excel_path = os.path.join(self.structure['data_exports'], 'P2P_Analysis_Consolidated.xlsx')
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # 1. Hoja resumen ejecutivo
            self._create_executive_summary_sheet(writer, all_period_data)
            
            # 2. Datos consolidados por moneda
            self._create_currency_sheets(writer, all_period_data)
            
            # 3. Métricas por periodo
            self._create_period_metrics_sheets(writer, all_period_data)
            
            # 4. Análisis comparativo
            self._create_comparative_sheet(writer, all_period_data)
            
        logger.info(f"Excel consolidado guardado: {excel_path}")
        return excel_path
        
    def _create_executive_summary_sheet(self, writer: pd.ExcelWriter, all_period_data: Dict):
        """Crea hoja de resumen ejecutivo."""
        summary_data = []
        
        for period_name, period_data in all_period_data.items():
            for status_name, status_data in period_data.items():
                current_df = pl.DataFrame() # Inicializar como DataFrame vacío
                if isinstance(status_data, dict):
                    current_df = status_data.get('df', pl.DataFrame())
                elif isinstance(status_data, pl.DataFrame): # Asumiendo que pl es polars
                    current_df = status_data
                else:
                    logger.warning(
                        f"En _create_executive_summary_sheet para periodo '{period_name}', status '{status_name}': "
                        f"status_data es de tipo inesperado {type(status_data)}. Se usará DataFrame vacío."
                    )

                if not current_df.is_empty():
                    df_pandas = current_df.to_pandas()
                    
                    # Calcular métricas resumidas
                    total_ops = len(df_pandas)
                    total_volume_usd = 0 # Inicializar
                    if 'fiat_type' in df_pandas.columns and 'TotalPrice_num' in df_pandas.columns:
                        total_volume_usd = df_pandas[df_pandas['fiat_type'] == 'USD']['TotalPrice_num'].sum()
                    
                    total_volume_uyu = 0 # Inicializar
                    if 'fiat_type' in df_pandas.columns and 'TotalPrice_num' in df_pandas.columns:
                        total_volume_uyu = df_pandas[df_pandas['fiat_type'] == 'UYU']['TotalPrice_num'].sum()
                        
                    unique_counterparties = df_pandas['Counterparty'].nunique() if 'Counterparty' in df_pandas.columns else 0
                    
                    summary_data.append({
                        'Periodo': period_name,
                        'Estado': status_name,
                        'Total_Operaciones': total_ops,
                        'Volumen_USD': total_volume_usd,
                        'Volumen_UYU': total_volume_uyu,
                        'Contrapartes_Unicas': unique_counterparties
                    })
                    
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Resumen_Ejecutivo', index=False)
        
    def _create_currency_sheets(self, writer: pd.ExcelWriter, all_period_data: Dict):
        """Crea hojas separadas para USD y UYU con todos los datos consolidados."""
        logger.info("Creando hojas de datos por moneda...")
        for currency in ["USD", "UYU"]:
            logger.info(f"Consolidando datos para hoja Excel de {currency}...")
            currency_dfs = []
            for period_name, period_data in all_period_data.items():
                for status_name, status_data in period_data.items():
                    current_df = pl.DataFrame() # Inicializar como DataFrame vacío
                    if isinstance(status_data, dict):
                        current_df = status_data.get('df')
                    elif isinstance(status_data, pl.DataFrame): # Asumiendo que pl es polars
                        current_df = status_data
                    else:
                        logger.warning(
                            f"En _create_currency_sheets para periodo '{period_name}', status '{status_name}', moneda '{currency}': "
                            f"status_data es de tipo inesperado {type(status_data)}. Se omitirá."
                        )
                    
                    if current_df is not None and not current_df.is_empty() and 'fiat_type' in current_df.columns:
                        filtered_df = current_df.filter(pl.col('fiat_type') == currency)
                        if not filtered_df.is_empty():
                            currency_dfs.append(filtered_df.with_columns([
                                pl.lit(period_name).alias('_period_source'),
                                pl.lit(status_name).alias('_status_source')
                            ]))
            
            if not currency_dfs:
                logger.info(f"No hay datos para la hoja de {currency}.")
                continue

            df_for_excel_pl = pl.concat(currency_dfs, how='vertical')
            df_for_excel_pd = df_for_excel_pl.to_pandas() # Convertir a Pandas DataFrame

            # Convertir datetimes timezone-aware a timezone-naive
            for col in df_for_excel_pd.columns:
                if pd.api.types.is_datetime64_any_dtype(df_for_excel_pd[col]):
                    if df_for_excel_pd[col].dt.tz is not None:
                        logger.info(f"Convirtiendo columna datetime '{col}' a timezone-naive para Excel en hoja {currency}.")
                        df_for_excel_pd[col] = df_for_excel_pd[col].dt.tz_localize(None)
            
            try:
                df_for_excel_pd.to_excel(writer, sheet_name=f'Datos_{currency}', index=False)
                logger.info(f"Hoja 'Datos_{currency}' creada en Excel con {df_for_excel_pd.shape[0]} filas.")
            except Exception as e_excel:
                logger.error(f"Error al escribir la hoja 'Datos_{currency}' en Excel: {e_excel}")
                
    def _create_period_metrics_sheets(self, writer: pd.ExcelWriter, all_period_data: Dict):
        """Crea hojas de métricas por periodo."""
        # Placeholder - implementar métricas específicas por periodo
        pass
        
    def _create_comparative_sheet(self, writer: pd.ExcelWriter, all_period_data: Dict):
        """Crea hoja de análisis comparativo."""
        # Placeholder - implementar análisis comparativo
        pass
        
    def _generate_unified_html(self, all_period_data: Dict, figure_paths: Dict, excel_path: str) -> str:
        """Genera HTML unificado con navegación."""
        logger.info("Generando HTML unificado...")
        
        # Cargar template
        templates_path = pathlib.Path(__file__).parent.parent / 'templates'
        env = Environment(loader=FileSystemLoader(str(templates_path)), autoescape=True)
        
        try:
            template = env.get_template("unified_report_template.html")
        except:
            # Fallback a template básico si el unificado no existe
            template = env.get_template("report_template.html")
            
        # Preparar contexto
        html_context = {
            'title': 'Reporte P2P Consolidado',
            'generation_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'current_year': datetime.datetime.now().year,
            'figure_paths': figure_paths,
            'excel_path': os.path.basename(excel_path),
            'summary_stats': self._calculate_summary_stats(all_period_data),
            'periods_analyzed': list(all_period_data.keys()),
            'interactive_mode': self.cli_args.interactive
        }
        
        # Renderizar y guardar
        html_output = template.render(html_context)
        html_path = os.path.join(self.structure['reports'], 'P2P_Unified_Report.html')
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
            
        logger.info(f"HTML unificado guardado: {html_path}")
        return html_path
        
    def _calculate_summary_stats(self, all_period_data: Dict) -> Dict:
        """Calcula estadísticas resumen para el reporte."""
        total_operations = 0
        total_volume_usd = 0
        total_volume_uyu = 0
        unique_counterparties = set()
        periods_count = len(all_period_data)
        
        for period_data in all_period_data.values():
            for status_data in period_data.values():
                current_df = pl.DataFrame() # Inicializar como DataFrame vacío
                if isinstance(status_data, dict):
                    current_df = status_data.get('df', pl.DataFrame())
                elif isinstance(status_data, pl.DataFrame): # Asumiendo que pl es polars
                    current_df = status_data
                else:
                    logger.warning(
                        f"En _calculate_summary_stats: status_data es de tipo inesperado {type(status_data)}. "
                        f"Se usará DataFrame vacío."
                    )

                if not current_df.is_empty():
                    total_operations += current_df.height
                    
                    if 'fiat_type' in current_df.columns and 'TotalPrice_num' in current_df.columns:
                        usd_data = current_df.filter(pl.col('fiat_type') == 'USD')
                        uyu_data = current_df.filter(pl.col('fiat_type') == 'UYU')
                        
                        total_volume_usd += usd_data['TotalPrice_num'].sum() or 0
                        total_volume_uyu += uyu_data['TotalPrice_num'].sum() or 0
                        
                    if 'Counterparty' in current_df.columns:
                        counterparties = current_df['Counterparty'].unique().to_list()
                        unique_counterparties.update([cp for cp in counterparties if cp is not None])
                        
        return {
            'total_operations': total_operations,
            'total_volume_usd': total_volume_usd,
            'total_volume_uyu': total_volume_uyu, 
            'unique_counterparties': len(unique_counterparties),
            'periods_analyzed': periods_count
        } 
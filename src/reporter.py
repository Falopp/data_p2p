import os
import logging
import datetime
import polars as pl
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import argparse 
import pathlib

import plotting 

logger = logging.getLogger(__name__)

def save_outputs(
    df_to_plot_from: pl.DataFrame, 
    metrics_to_save: dict[str, pl.DataFrame | pl.Series], 
    output_label: str,
    status_subdir: str,
    base_output_dir: str, 
    file_name_suffix_from_cli: str, 
    title_suffix_from_cli: str, 
    col_map: dict, # col_map ya no se usa directamente en save_outputs, pero se mantiene por si acaso o futuras necesidades.
    cli_args: argparse.Namespace,
    config: dict
):
    section_id = f"{output_label.upper()} - {status_subdir.upper()}"
    logger.info(f"\n--- INICIO: Procesamiento y Guardado para: {section_id} ---")
    
    # Construcción robusta de la ruta a la carpeta de plantillas usando pathlib
    try:
        script_path = pathlib.Path(__file__).resolve()
        project_root = script_path.parent.parent # Sube dos niveles: src -> p2p
        templates_path = project_root / 'templates'
        templates_path_str = str(templates_path)
        logger.info(f"[REPORTER_DEBUG] Ruta de templates construida con pathlib: {templates_path_str}")
    except Exception as e_path:
        logger.error(f"[REPORTER_DEBUG] Error al construir ruta de templates con pathlib: {e_path}")
        # Fallback a la lógica anterior si pathlib falla (aunque es improbable)
        script_dir_fallback = os.path.dirname(os.path.abspath(__file__))
        templates_path_str = os.path.join(script_dir_fallback, '..', 'templates')
        logger.warning(f"[REPORTER_DEBUG] Usando ruta de fallback para templates: {templates_path_str}")


    env = None
    template = None
    try:
        logger.info(f"[REPORTER_DEBUG] Intentando cargar templates desde: {templates_path_str}")
        if not os.path.isdir(templates_path_str): # Usar os.path.isdir con la cadena
            logger.error(f"[REPORTER_DEBUG] La ruta de templates NO es un directorio: {templates_path_str}")
        else:
            logger.info(f"[REPORTER_DEBUG] La ruta de templates SÍ es un directorio.")
            env = Environment(loader=FileSystemLoader(templates_path_str), autoescape=True)
            logger.info(f"[REPORTER_DEBUG] Jinja Environment creado: {env is not None}")
            if env:
                template = env.get_template("report_template.html")
                logger.info(f"[REPORTER_DEBUG] Plantilla 'report_template.html' cargada: {template is not None}")
            else:
                logger.error("[REPORTER_DEBUG] Jinja Environment no se pudo crear.")
                template = None

    except Exception as e:
        logger.error(f"[REPORTER_DEBUG] Error al cargar plantilla Jinja2: {e}"); 
        template = None # Asegurar que template es None si hay error

    period_and_status_path = os.path.join(base_output_dir, output_label, status_subdir)
    os.makedirs(period_and_status_path, exist_ok=True)
    tables_dir = os.path.join(period_and_status_path, "tables")
    figures_dir = os.path.join(period_and_status_path, "figures")
    reports_dir = os.path.join(period_and_status_path, "reports")
    os.makedirs(tables_dir, exist_ok=True); os.makedirs(figures_dir, exist_ok=True); os.makedirs(reports_dir, exist_ok=True)

    final_title_suffix = title_suffix_from_cli
    report_main_title = f"Reporte de Operaciones P2P"
    if output_label.lower() != "total":
        final_title_suffix = f"{title_suffix_from_cli} (Año: {output_label} - {status_subdir.capitalize()})"
        report_main_title += f" - Año {output_label} ({status_subdir.capitalize()})"
    else:
        final_title_suffix = f"{title_suffix_from_cli} (Total - {status_subdir.capitalize()})"
        report_main_title += f" - Consolidado Total ({status_subdir.capitalize()})"
    if title_suffix_from_cli and title_suffix_from_cli not in report_main_title:
        report_main_title += f" {title_suffix_from_cli}"

    logger.info(f"Guardando tablas de métricas para '{output_label} - {status_subdir}' en: {tables_dir}")
    metrics_to_save_pandas = {} 

    for name, table_data_pl in metrics_to_save.items():
        clean_metric_name = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in name)
        file_path = os.path.join(tables_dir, f"{clean_metric_name}{file_name_suffix_from_cli}.csv")
        
        if isinstance(table_data_pl, pl.DataFrame):
            metrics_to_save_pandas[name] = table_data_pl.to_pandas(use_pyarrow_extension_array=True) if not table_data_pl.is_empty() else pd.DataFrame()
            if not table_data_pl.is_empty():
                try:
                    table_data_pl.write_csv(file_path)
                    logger.info(f"  Tabla Polars '{name}' guardada: {file_path}")
                except Exception as e:
                    logger.error(f"  Error guardando tabla Polars '{name}': {e}")
            else:
                logger.info(f"  Tabla Polars '{name}' vacía, no se guarda CSV.")
        elif isinstance(table_data_pl, pl.Series):
            pandas_equivalent = table_data_pl.to_pandas(use_pyarrow_extension_array=True) if not table_data_pl.is_empty() else pd.Series(dtype='object')
            metrics_to_save_pandas[name] = pandas_equivalent
            if not table_data_pl.is_empty():
                try:
                    if isinstance(pandas_equivalent, pd.DataFrame): 
                        pandas_equivalent.to_csv(file_path, index=False)
                        logger.info(f"  Serie Polars (convertida a DF Pandas) '{name}' guardada como CSV: {file_path}")
                    else:
                        # Para Series, index=True es usualmente lo deseado para mantener las etiquetas
                        pandas_equivalent.to_csv(file_path, index=True, header=True) 
                        logger.info(f"  Serie Polars (convertida a Serie Pandas) '{name}' guardada como CSV: {file_path}")
                except Exception as e: 
                    logger.error(f"  Error guardando serie Polars '{name}' como CSV: {e}")
            else: 
                logger.info(f"  Serie Polars '{name}' vacía, no se guarda CSV.")
        else:
            metrics_to_save_pandas[name] = table_data_pl 
            logger.warning(f"  Resultado '{name}' no es Polars DataFrame/Series. Tipo: {type(table_data_pl)}. Se usa como está para el reporte.")

    logger.info(f"\nGenerando y guardando gráficos para '{output_label} - {status_subdir}' en: {figures_dir}")
    df_to_plot_from_pandas = df_to_plot_from.to_pandas(use_pyarrow_extension_array=True) 

    figures_for_html = []
    def add_figure_to_html_list(fig_path: str | list[str] | None, title_prefix: str):
        if fig_path: # Solo procesar si fig_path no es None
            if isinstance(fig_path, str) and os.path.exists(fig_path):
                relative_fig_path = os.path.join('..', 'figures', os.path.basename(fig_path)).replace('\\', '/')
                descriptive_title = title_prefix 
                figures_for_html.append({'title': descriptive_title, 'path': relative_fig_path})
            elif isinstance(fig_path, list):
                for idx, single_path in enumerate(fig_path):
                    if isinstance(single_path, str) and os.path.exists(single_path):
                        relative_single_path = os.path.join('..', 'figures', os.path.basename(single_path)).replace('\\', '/')
                        base_name = os.path.basename(single_path).replace(file_name_suffix_from_cli, '').replace('.png', '')
                        prefixes_to_remove = ['price_distribution', 'volume_vs_price_scatter', 'price_over_time', 'volume_over_time_asset_quantity', 'volume_over_time_fiat_value', 'price_vs_payment_method', 'monthly_fiat_volume', 'hourly_counts','buy_sell_distribution', 'order_status_distribution', 'activity_heatmap','fees_total_by_asset']
                        cleaned_name_part = base_name
                        for pfx in prefixes_to_remove:
                            if cleaned_name_part.startswith(pfx + '_'): cleaned_name_part = cleaned_name_part[len(pfx)+1:]
                            elif cleaned_name_part.startswith(pfx): cleaned_name_part = cleaned_name_part[len(pfx):]
                        name_parts = [p.capitalize() for p in cleaned_name_part.split('_') if p and p not in ['general']]
                        specific_addon = ' '.join(name_parts) if name_parts else f"Parte {idx + 1}"
                        specific_title = f"{title_prefix} - {specific_addon}"
                        figures_for_html.append({'title': specific_title, 'path': relative_single_path})
    
    logger.info(f"Generando y adaptando datos para gráficos de '{output_label} - {status_subdir}'...")

    # --- Hourly Counts Plot --- 
    hourly_counts_pd = metrics_to_save_pandas.get('hourly_counts')
    path_hourly = None 
    if hourly_counts_pd is not None and not hourly_counts_pd.empty:
        if isinstance(hourly_counts_pd, pd.DataFrame) and hourly_counts_pd.shape[0] > 0:
            label_col_name = hourly_counts_pd.columns[0]
            counts_col_name = hourly_counts_pd.columns[1] if hourly_counts_pd.shape[1] >= 2 else 'counts' 
            if counts_col_name not in hourly_counts_pd.columns and hourly_counts_pd.shape[1] >=2 : 
                 counts_col_name = hourly_counts_pd.columns[1]
            elif counts_col_name not in hourly_counts_pd.columns and hourly_counts_pd.shape[1] == 1: 
                 counts_col_name = hourly_counts_pd.columns[0]
                 logger.warning(f"hourly_counts_pd para '{output_label} - {status_subdir}' solo tiene una columna '{counts_col_name}', se usará como counts y se intentará inferir/usar índice como etiquetas.")

            try:
                current_labels = pd.to_numeric(hourly_counts_pd[label_col_name], errors='coerce')
                valid_indices = ~current_labels.isna()
                hourly_counts_series = pd.Series(
                    hourly_counts_pd.loc[valid_indices, counts_col_name].values, 
                    index=current_labels[valid_indices]
                ).sort_index()
                path_hourly = plotting.plot_hourly(hourly_counts_series, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
            except Exception as e_hc: 
                logger.error(f"Error al procesar/plotear hourly_counts para '{output_label} - {status_subdir}': {e_hc}. DataFrame: \n{hourly_counts_pd.head()}")
                path_hourly = None # Asegurar que path_hourly es None si hay error
        elif isinstance(hourly_counts_pd, pd.Series): 
             logger.info(f"hourly_counts_pd para '{output_label} - {status_subdir}' ya es una Serie, ploteando directamente.")
             try:
                 path_hourly = plotting.plot_hourly(hourly_counts_pd.sort_index(), figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
             except Exception as e_hc_series:
                 logger.error(f"Error al plotear hourly_counts (Series) para '{output_label} - {status_subdir}': {e_hc_series}.")
                 path_hourly = None # Asegurar que path_hourly es None si hay error
        add_figure_to_html_list(path_hourly, "Operaciones por Hora")
    else:
        logger.info(f"No hay datos de hourly_counts para graficar en '{output_label} - {status_subdir}'.")

    # --- Monthly Fiat Plot --- 
    monthly_fiat_pd = metrics_to_save_pandas.get('monthly_fiat')
    paths_monthly = None
    if monthly_fiat_pd is not None and not monthly_fiat_pd.empty and isinstance(monthly_fiat_pd, pd.DataFrame):
        df_to_plot_monthly = monthly_fiat_pd.copy()
        if isinstance(df_to_plot_monthly.index, pd.MultiIndex):
            logger.info(f"monthly_fiat_pd para '{output_label} - {status_subdir}' tiene MultiIndex, reseteando para ploteo.")
            df_to_plot_monthly = df_to_plot_monthly.reset_index()
        
        year_month_col_internal = 'YearMonthStr' 
        if year_month_col_internal not in df_to_plot_monthly.columns and year_month_col_internal not in (df_to_plot_monthly.index.name or [] if not isinstance(df_to_plot_monthly.index, pd.MultiIndex) else df_to_plot_monthly.index.names) :
             logger.warning(f"Columna/Índice '{year_month_col_internal}' no encontrada en monthly_fiat_pd para '{output_label} - {status_subdir}'. No se puede graficar.")
        else:
            try:
                paths_monthly = plotting.plot_monthly(df_to_plot_monthly, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
            except Exception as e_mf:
                logger.error(f"Error al plotear monthly_fiat para '{output_label} - {status_subdir}': {e_mf}.")
                paths_monthly = None # Asegurar que paths_monthly es None si hay error
        add_figure_to_html_list(paths_monthly, "Volumen Mensual de Fiat")
    else:
        logger.info(f"No hay datos de monthly_fiat para graficar en '{output_label} - {status_subdir}'.")

    # --- Pie Charts --- 
    for pie_metric_key, pie_title, pie_fname in [
        ('side_counts', 'Distribución Tipos de Orden', 'buy_sell_distribution'),
        ('status_counts', 'Distribución Estados de Orden', 'order_status_distribution')
    ]:
        counts_pd = metrics_to_save_pandas.get(pie_metric_key)
        path_pie = None
        if counts_pd is not None and not counts_pd.empty:
            df_for_pie = None
            if isinstance(counts_pd, pd.DataFrame) and counts_pd.shape[0] > 0:
                label_col_name = counts_pd.columns[0] 
                values_col_name = counts_pd.columns[1] if counts_pd.shape[1] >= 2 else 'counts' 
                if values_col_name not in counts_pd.columns and counts_pd.shape[1] >=2: values_col_name = counts_pd.columns[1]
                elif values_col_name not in counts_pd.columns and counts_pd.shape[1] == 1: values_col_name = counts_pd.columns[0]
                
                try:
                    df_for_pie = counts_pd.set_index(label_col_name)[[values_col_name]].rename(columns={values_col_name: 'Cantidad'})
                except KeyError as e_pie_prep:
                    logger.error(f"Error preparando datos para pie chart '{pie_metric_key}' ('{output_label} - {status_subdir}'): {e_pie_prep}. DF Head:\n{counts_pd.head()}")
                    # df_for_pie se mantiene como None
            elif isinstance(counts_pd, pd.Series):
                df_for_pie = counts_pd.to_frame(name='Cantidad')
            
            if df_for_pie is not None and not df_for_pie.empty:
                try:
                    path_pie = plotting.plot_pie(df_for_pie, 'Cantidad', pie_title, pie_fname, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
                except Exception as e_pie_plot:
                    logger.error(f"Error al plotear pie chart '{pie_metric_key}' ('{output_label} - {status_subdir}'): {e_pie_plot}.")
                    path_pie = None
            add_figure_to_html_list(path_pie, pie_title)
        else:
            logger.info(f"No hay datos de '{pie_metric_key}' para graficar en '{output_label} - {status_subdir}'.")

    # --- Completed Data Plots --- 
    status_col_name_in_pandas = 'status' 
    df_completed_for_plots_pandas = pd.DataFrame() 
    if status_col_name_in_pandas in df_to_plot_from_pandas.columns:
        if not df_to_plot_from_pandas.empty:
            df_completed_for_plots_pandas = df_to_plot_from_pandas[df_to_plot_from_pandas[status_col_name_in_pandas] == 'Completed'].copy()
            if df_completed_for_plots_pandas.empty:
                 logger.info(f"No hay operaciones 'Completed' en df_to_plot_from_pandas para '{output_label} - {status_subdir}'. Gráficos dependientes estarán vacíos.")
        else:
            logger.info(f"df_to_plot_from_pandas está vacío para '{output_label} - {status_subdir}'. Gráficos dependientes estarán vacíos.")
    else:
        logger.warning(f"Columna '{status_col_name_in_pandas}' no encontrada en df_to_plot_from_pandas para '{output_label} - {status_subdir}'. Gráficos basados en 'Completed' podrían estar vacíos.")

    if not df_completed_for_plots_pandas.empty:
        logger.info(f"Generando gráficos basados en datos 'Completed' para '{output_label} - {status_subdir}' ({len(df_completed_for_plots_pandas)} filas).")
        logger.info(f"[REPORTER_DEBUG] Columnas en df_completed_for_plots_pandas: {df_completed_for_plots_pandas.columns.tolist()}") # LOG DE COLUMNAS
        
        asset_col_name = 'asset_type'
        fiat_col_name = 'fiat_type'

        target_pairs_for_dist_scatter = [
            {'asset': 'USDT', 'fiat': 'USD', 'title_suffix': 'USDT USD'},
            {'asset': 'USDT', 'fiat': 'UYU', 'title_suffix': 'USDT UYU'}
        ]

        # --- plot_price_distribution ---
        for pair_info in target_pairs_for_dist_scatter:
            df_filtered = df_completed_for_plots_pandas[
                (df_completed_for_plots_pandas[asset_col_name] == pair_info['asset']) &
                (df_completed_for_plots_pandas[fiat_col_name] == pair_info['fiat'])
            ]
            if not df_filtered.empty:
                specific_file_id = f"{file_name_suffix_from_cli}_{pair_info['asset']}_{pair_info['fiat']}"
                try:
                    # Asumiendo que la función de ploteo devuelve una lista de paths.
                    # Si df_filtered es para un solo par, la lista podría tener un solo path.
                    paths_dist_pair = plotting.plot_price_distribution(df_filtered, figures_dir, title_suffix=final_title_suffix, file_identifier=specific_file_id)
                    if paths_dist_pair:
                        # Si devuelve una lista, tomamos el primer (y esperado único) elemento.
                        # Si devuelve una cadena, add_figure_to_html_list también lo maneja.
                        path_to_add = paths_dist_pair[0] if isinstance(paths_dist_pair, list) and paths_dist_pair else paths_dist_pair
                        if path_to_add: # Asegurarse de que no esté vacío
                             add_figure_to_html_list(path_to_add, f"Distribución de Precios - {pair_info['title_suffix']}")
                except Exception as e:
                    logger.error(f"Error en plot_price_distribution para {pair_info['asset']}/{pair_info['fiat']}: {e}")
            else:
                logger.info(f"No hay datos 'Completed' para {pair_info['asset']}/{pair_info['fiat']} para Distribución de Precios.")

        # --- plot_volume_vs_price_scatter ---
        for pair_info in target_pairs_for_dist_scatter:
            df_filtered = df_completed_for_plots_pandas[
                (df_completed_for_plots_pandas[asset_col_name] == pair_info['asset']) &
                (df_completed_for_plots_pandas[fiat_col_name] == pair_info['fiat'])
            ]
            if not df_filtered.empty:
                specific_file_id = f"{file_name_suffix_from_cli}_{pair_info['asset']}_{pair_info['fiat']}"
                try:
                    paths_scatter_pair = plotting.plot_volume_vs_price_scatter(df_filtered, figures_dir, title_suffix=final_title_suffix, file_identifier=specific_file_id)
                    if paths_scatter_pair:
                        path_to_add = paths_scatter_pair[0] if isinstance(paths_scatter_pair, list) and paths_scatter_pair else paths_scatter_pair
                        if path_to_add:
                            add_figure_to_html_list(path_to_add, f"Volumen vs. Precio - {pair_info['title_suffix']}")
                except Exception as e:
                    logger.error(f"Error en plot_volume_vs_price_scatter para {pair_info['asset']}/{pair_info['fiat']}: {e}")
            else:
                logger.info(f"No hay datos 'Completed' para {pair_info['asset']}/{pair_info['fiat']} para Volumen vs. Precio.")
        
        # Las siguientes gráficas se eliminan según solicitud:
        # try: paths_price_time = plotting.plot_price_over_time(df_completed_for_plots_pandas, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
        # except Exception as e: logger.error(f"Error en plot_price_over_time: {e}")
        # add_figure_to_html_list(paths_price_time, "Evolución del Precio")
        
        # try: paths_vol_time = plotting.plot_volume_over_time(df_completed_for_plots_pandas, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
        # except Exception as e: logger.error(f"Error en plot_volume_over_time: {e}")
        # add_figure_to_html_list(paths_vol_time, "Evolución del Volumen")
        
        # try: paths_pm = plotting.plot_price_vs_payment_method(df_completed_for_plots_pandas, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
        # except Exception as e: logger.error(f"Error en plot_price_vs_payment_method: {e}")
        # add_figure_to_html_list(paths_pm, "Precio vs. Método de Pago")
    else:
        logger.info(f"Omitiendo gráficos basados en datos 'Completed' para '{output_label} - {status_subdir}' ya que no hay datos 'Completed' o el DataFrame base está vacío.")

    # --- Activity Heatmap --- 
    path_heatmap = None
    if not df_to_plot_from_pandas.empty:
        logger.info(f"Generando heatmap de actividad para '{output_label} - {status_subdir}' ({len(df_to_plot_from_pandas)} filas).")
        try:
            path_heatmap = plotting.plot_activity_heatmap(df_to_plot_from_pandas, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
        except Exception as e: 
            logger.error(f"Error en plot_activity_heatmap: {e}")
        add_figure_to_html_list(path_heatmap, "Heatmap de Actividad")
    else:
        logger.info(f"Omitiendo heatmap de actividad para '{output_label} - {status_subdir}' ya que df_to_plot_from_pandas está vacío.")

    # --- Fees Analysis Plot --- 
    # fees_stats_pd = metrics_to_save_pandas.get('fees_stats') # Ya no se necesita el gráfico
    # path_fees = None
    # if fees_stats_pd is not None and not fees_stats_pd.empty and isinstance(fees_stats_pd, pd.DataFrame):
    #     asset_type_col_name_fees = 'asset_type' 
    #     if asset_type_col_name_fees in fees_stats_pd.columns:
    #         logger.info(f"Generando gráfico de análisis de comisiones para '{output_label} - {status_subdir}'.")
    #         fees_stats_pd_for_plot = fees_stats_pd.set_index(asset_type_col_name_fees)
    #         try:
    #             path_fees = plotting.plot_fees_analysis(fees_stats_pd_for_plot, figures_dir, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
    #         except Exception as e: 
    #             logger.error(f"Error en plot_fees_analysis: {e}")
    #         add_figure_to_html_list(path_fees, "Análisis de Comisiones")
    #     else:
    #         logger.warning(f"Columna '{asset_type_col_name_fees}' no encontrada en fees_stats_pd para ploteo en '{output_label} - {status_subdir}'. DF columns: {fees_stats_pd.columns}")
    # else:
    #     logger.info(f"No hay datos de fees_stats para graficar en '{output_label} - {status_subdir}'.")

    # --- HTML Report Generation --- 
    if template:
        logger.info(f"Preparando datos para el reporte HTML de '{output_label} - {status_subdir}'...")
        current_year = datetime.datetime.now().year
        html_context = {
            'title': report_main_title,
            'generation_timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (UTC" + datetime.datetime.now(datetime.timezone.utc).astimezone().strftime('%z') + ")",
            'current_year': current_year,
            'applied_filters': {},
            'sales_summary_data': {},
            'included_tables': [],
            'included_figures': figures_for_html 
        }
        
        if cli_args.fiat_filter: html_context['applied_filters']['Monedas Fiat (CLI)'] = ", ".join(cli_args.fiat_filter)
        if cli_args.asset_filter: html_context['applied_filters']['Activos (CLI)'] = ", ".join(cli_args.asset_filter)
        if cli_args.status_filter: html_context['applied_filters']['Estados (CLI)'] = ", ".join(cli_args.status_filter)
        if cli_args.payment_method_filter: html_context['applied_filters']['Métodos de Pago (CLI)'] = ", ".join(cli_args.payment_method_filter)
        if output_label.lower() != "total": 
            html_context['applied_filters']['Periodo Analizado'] = f"Año {output_label}"
        else:
            html_context['applied_filters']['Periodo Analizado'] = "Total Consolidado"
        html_context['applied_filters']['Categoría de Estado Procesada'] = status_subdir.capitalize()

        sales_summary_df_key = 'sales_summary_all_assets_fiat_detailed'
        sales_summary_pd = metrics_to_save_pandas.get(sales_summary_df_key)
        if sales_summary_pd is not None and isinstance(sales_summary_pd, pd.DataFrame) and not sales_summary_pd.empty:
            logger.info(f"Añadiendo '{sales_summary_df_key}' al reporte HTML para '{output_label} - {status_subdir}'.")
            html_context['sales_summary_data']['sales_summary_all_assets_fiat_detailed'] = True
            try:
                html_context['sales_summary_data']['sales_summary_all_assets_fiat_detailed_html'] = sales_summary_pd.to_html(classes='table table-striped table-hover table-sm', border=0, index=False)
            except Exception as e_html_sales:
                logger.error(f"Error generando HTML para sales_summary: {e_html_sales}")
                html_context['sales_summary_data']['sales_summary_all_assets_fiat_detailed_html'] = "<p>Error al generar tabla de resumen de ventas.</p>"
        else:
            logger.info(f"No hay datos de '{sales_summary_df_key}' para el reporte HTML en '{output_label} - {status_subdir}'.")
        
        html_report_prefs = config.get('html_report', {})
        tables_to_include_keys = html_report_prefs.get('include_tables_default', [])
        logger.info(f"Tablas configuradas para incluir en HTML ({output_label} - {status_subdir}): {tables_to_include_keys}")
        
        for table_key in tables_to_include_keys:
            table_df_pandas = metrics_to_save_pandas.get(table_key)
            if table_df_pandas is not None and not table_df_pandas.empty:
                logger.info(f"Procesando tabla '{table_key}' para HTML en '{output_label} - {status_subdir}'. Tipo: {type(table_df_pandas)}")
                current_table_html = "<p>Error desconocido al generar esta tabla.</p>"
                try:
                    if isinstance(table_df_pandas, pd.Series):
                        series_name = table_df_pandas.name if table_df_pandas.name else table_key.replace('_', ' ').title()
                        table_df_pandas_for_html = table_df_pandas.to_frame(name=series_name) 
                        should_show_index_for_series = True 
                        current_table_html = table_df_pandas_for_html.to_html(classes='table table-striped table-hover table-sm', border=0, index=should_show_index_for_series)
                    elif isinstance(table_df_pandas, pd.DataFrame):
                        should_show_index = True 
                        if table_key in ['status_counts', 'side_counts', 'hourly_counts']:
                            should_show_index = False 
                        elif isinstance(table_df_pandas.index, pd.RangeIndex) and table_df_pandas.index.name is None:
                            should_show_index = False
                        elif isinstance(table_df_pandas.index, pd.MultiIndex):
                            should_show_index = True 

                        current_table_html = table_df_pandas.to_html(classes='table table-striped table-hover table-sm', border=0, index=should_show_index)
                    else:
                        logger.warning(f"El objeto para la tabla '{table_key}' no es ni Serie ni DataFrame de Pandas. Tipo: {type(table_df_pandas)}. Se omite del HTML.")
                        continue 

                    html_context['included_tables'].append({
                        'title': table_key.replace('_', ' ').title(),
                        'html': current_table_html
                    })
                except Exception as e_html_table:
                    logger.error(f"Error generando HTML para tabla '{table_key}' ({output_label} - {status_subdir}): {e_html_table}")
                    html_context['included_tables'].append({
                        'title': table_key.replace('_', ' ').title(),
                        'html': f"<p>Error al generar tabla: {table_key}</p>"
                    })
            else:
                logger.info(f"Tabla '{table_key}' vacía o no encontrada en metrics_to_save_pandas para '{output_label} - {status_subdir}'. No se incluirá en HTML.")
        
        try:
            logger.info(f"Renderizando reporte HTML para '{output_label} - {status_subdir}'...")
            html_output = template.render(html_context)
            report_filename = f"p2p_sales_report{file_name_suffix_from_cli}.html"
            report_path = os.path.join(reports_dir, report_filename)
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_output)
            logger.info(f"Reporte HTML guardado en: {report_path}")
        except Exception as e_render:
            logger.error(f"Error al renderizar o guardar el reporte HTML para '{output_label} - {status_subdir}': {e_render}")
    else:
        logger.warning(f"No se encontró la plantilla HTML. No se generará el reporte HTML para '{section_id}'.")

    logger.info(f"--- FIN: Procesamiento y Guardado para: {section_id} ---") 
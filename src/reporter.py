import os
import logging
import datetime
import polars as pl
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import argparse 
import pathlib

from . import plotting 

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
        template = None

    period_and_status_path = os.path.join(base_output_dir, output_label, status_subdir)
    os.makedirs(period_and_status_path, exist_ok=True)
    tables_dir = os.path.join(period_and_status_path, "tables")
    figures_dir = os.path.join(period_and_status_path, "figures")
    reports_dir = os.path.join(period_and_status_path, "reports")
    os.makedirs(tables_dir, exist_ok=True); os.makedirs(figures_dir, exist_ok=True); os.makedirs(reports_dir, exist_ok=True)

    # Crear subdirectorios para figuras por moneda
    figures_dir_usd = os.path.join(figures_dir, "usd_usdt") # Nombrado usd_usdt para claridad
    figures_dir_uyu = os.path.join(figures_dir, "uyu")
    figures_dir_general = os.path.join(figures_dir, "general")
    figures_dir_combined = os.path.join(figures_dir, "combined")
    os.makedirs(figures_dir_usd, exist_ok=True)
    os.makedirs(figures_dir_uyu, exist_ok=True)
    os.makedirs(figures_dir_general, exist_ok=True)
    os.makedirs(figures_dir_combined, exist_ok=True)

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
    def add_figure_to_html_list(fig_path: str | list[str] | None, title_prefix: str, subfolder: str | None = None):
        if fig_path: # Solo procesar si fig_path no es None
            if isinstance(fig_path, str) and os.path.exists(fig_path):
                file_name = os.path.basename(fig_path)
                # Construir la ruta relativa incluyendo el subdirectorio si se proporciona
                if subfolder:
                    relative_fig_path = os.path.join('..', 'figures', subfolder, file_name).replace('\\\\', '/')
                else:
                    relative_fig_path = os.path.join('..', 'figures', file_name).replace('\\\\', '/')
                
                descriptive_title = title_prefix 
                file_type = 'html' if file_name.lower().endswith('.html') else 'image'
                figures_for_html.append({'title': descriptive_title, 'path': relative_fig_path, 'type': file_type})
            elif isinstance(fig_path, list):
                for idx, single_path in enumerate(fig_path):
                    if isinstance(single_path, str) and os.path.exists(single_path):
                        single_file_name = os.path.basename(single_path)
                        # Asumimos que el subfolder se aplica a todos los paths en la lista si se proporciona
                        if subfolder:
                            relative_single_path = os.path.join('..', 'figures', subfolder, single_file_name).replace('\\\\', '/')
                        else:
                            relative_single_path = os.path.join('..', 'figures', single_file_name).replace('\\\\', '/')
                        
                        base_name = single_file_name.replace(file_name_suffix_from_cli, '').replace('.png', '').replace('.html', '')
                        prefixes_to_remove = ['price_distribution', 'volume_vs_price_scatter', 'price_over_time', 'volume_over_time_asset_quantity', 'volume_over_time_fiat_value', 'price_vs_payment_method', 'monthly_fiat_volume', 'hourly_counts','buy_sell_distribution', 'order_status_distribution', 'activity_heatmap','fees_total_by_asset', 'sankey_fiat_to_asset', 'scatter_animated_price_qty']
                        cleaned_name_part = base_name
                        for pfx in prefixes_to_remove:
                            if cleaned_name_part.startswith(pfx + '_'): cleaned_name_part = cleaned_name_part[len(pfx)+1:]
                            elif cleaned_name_part.startswith(pfx): cleaned_name_part = cleaned_name_part[len(pfx):]
                        name_parts = [p.capitalize() for p in cleaned_name_part.split('_') if p and p not in ['general']]
                        specific_addon = ' '.join(name_parts) if name_parts else f"Parte {idx + 1}"
                        specific_title = f"{title_prefix} - {specific_addon}"
                        single_file_type = 'html' if single_file_name.lower().endswith('.html') else 'image'
                        figures_for_html.append({'title': specific_title, 'path': relative_single_path, 'type': single_file_type})
    
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
                path_hourly = plotting.plot_hourly(hourly_counts_series, figures_dir_general, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
            except Exception as e_hc: 
                logger.error(f"Error al procesar/plotear hourly_counts para '{output_label} - {status_subdir}': {e_hc}. DataFrame: \n{hourly_counts_pd.head()}")
                path_hourly = None
        elif isinstance(hourly_counts_pd, pd.Series): 
             logger.info(f"hourly_counts_pd para '{output_label} - {status_subdir}' ya es una Serie, ploteando directamente.")
             try:
                 path_hourly = plotting.plot_hourly(hourly_counts_pd.sort_index(), figures_dir_general, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
             except Exception as e_hc_series:
                 logger.error(f"Error al plotear hourly_counts (Series) para '{output_label} - {status_subdir}': {e_hc_series}.")
                 path_hourly = None
        add_figure_to_html_list(path_hourly, "Operaciones por Hora", subfolder="general")
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
                paths_monthly = plotting.plot_monthly(df_to_plot_monthly, figures_dir_general, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
            except Exception as e_mf:
                logger.error(f"Error al plotear monthly_fiat para '{output_label} - {status_subdir}': {e_mf}.")
                paths_monthly = None
        add_figure_to_html_list(paths_monthly, "Volumen Mensual de Fiat", subfolder="general")
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
                    
            elif isinstance(counts_pd, pd.Series):
                df_for_pie = counts_pd.to_frame(name='Cantidad')
            
            if df_for_pie is not None and not df_for_pie.empty:
                try:
                    path_pie = plotting.plot_pie(df_for_pie, 'Cantidad', pie_title, pie_fname, figures_dir_general, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
                except Exception as e_pie_plot:
                    logger.error(f"Error al plotear pie chart '{pie_metric_key}' ('{output_label} - {status_subdir}'): {e_pie_plot}.")
                    path_pie = None
            add_figure_to_html_list(path_pie, pie_title, subfolder="general")
        else:
            logger.info(f"No hay datos de '{pie_metric_key}' para graficar en '{output_label} - {status_subdir}'.")

    # DONE: 2.1 Llamar a plot_sankey_fiat_asset
    path_sankey = None
    if config.get('plotting', {}).get('generate_sankey_fiat_asset', True):
        logger.info(f"Intentando generar gráfico Sankey para '{output_label} - {status_subdir}'...")
        # Primero, la versión que usa df_to_plot_from (DataFrame de Polars original)
        if df_to_plot_from is not None and not df_to_plot_from.is_empty():
            try:
                path_sankey_general = plotting.plot_sankey_fiat_asset(
                    df_to_plot_from, 
                    figures_dir_general, # Guardar en figures/general/
                    title_suffix=final_title_suffix, 
                    file_identifier=file_name_suffix_from_cli
                )
                add_figure_to_html_list(path_sankey_general, "Flujo Fiat a Activo (Sankey General)", subfolder="general")
            except Exception as e_sankey_plot:
                logger.error(f"Error al generar gráfico Sankey general para '{output_label} - {status_subdir}': {e_sankey_plot}.")
        else:
            logger.info(f"DataFrame principal (df_to_plot_from) vacío para '{output_label} - {status_subdir}', no se genera Sankey general.")

        # Adicionalmente, si existe la columna 'TotalPrice_USD_equivalent', generar un Sankey combinado
        if 'TotalPrice_USD_equivalent' in df_to_plot_from_pandas.columns:
            df_for_sankey_combined = df_to_plot_from_pandas.dropna(subset=['TotalPrice_USD_equivalent'])
            if not df_for_sankey_combined.empty:
                
                try:
                    # Convertimos el df de pandas a polars para la función de ploteo
                    df_polars_for_sankey_combined = pl.from_pandas(df_for_sankey_combined)
                    path_sankey_combined = plotting.plot_sankey_fiat_asset(
                        df_polars_for_sankey_combined, 
                        figures_dir_combined, # Guardar en figures/combined/
                        value_col_name='TotalPrice_USD_equivalent', # PASAR LA COLUMNA CORRECTA
                        title_suffix=f"{final_title_suffix} (Combinado USD Eq.)", 
                        file_identifier=f"{file_name_suffix_from_cli}_combined_usd_eq"
                    )
                    add_figure_to_html_list(path_sankey_combined, "Flujo Fiat a Activo (Sankey Combinado USD Eq.)", subfolder="combined")
                except TypeError as te:
                    if "unexpected keyword argument 'value_col_name'" in str(te):
                        logger.error(f"Error al generar Sankey combinado: la función plot_sankey_fiat_asset no acepta 'value_col_name'. Se necesita actualizar plotting.py. {te}")
                    else:
                        logger.error(f"Error (TypeError) al generar gráfico Sankey combinado para '{output_label} - {status_subdir}': {te}.")
                except Exception as e_sankey_combined:
                    logger.error(f"Error al generar gráfico Sankey combinado para '{output_label} - {status_subdir}': {e_sankey_combined}.")
            else:
                logger.info(f"No hay datos con 'TotalPrice_USD_equivalent' válido para Sankey combinado en '{output_label} - {status_subdir}'.")
        else:
            logger.warning(f"Columna 'TotalPrice_USD_equivalent' no encontrada para Sankey combinado en '{output_label} - {status_subdir}'.")

    # --- Nuevo Gráfico: Completitud de Órdenes a lo largo del Tiempo ---
    logger.info(f"Intentando generar gráfico de Completitud de Órdenes a lo largo del Tiempo para '{output_label} - {status_subdir}'...")
    time_col_name = config.get('column_names', {}).get('match_time_local_internal', 'Match_time_local')
    status_col_name = config.get('column_names', {}).get('status_internal', 'status') # Usar el nombre de columna de estado mapeado/configurado
    
    if not df_to_plot_from_pandas.empty and time_col_name in df_to_plot_from_pandas.columns and status_col_name in df_to_plot_from_pandas.columns:
        try:
            path_status_over_time = plotting.plot_order_status_over_time(
                df_all_statuses_pd=df_to_plot_from_pandas, # Este DF ya contiene todos los estados para el periodo/status actual del reporte
                time_col=time_col_name,
                status_col=status_col_name,
                out_dir=figures_dir_general, # Guardar en figures/general/
                title_suffix=final_title_suffix,
                file_identifier=file_name_suffix_from_cli
            )
            add_figure_to_html_list(path_status_over_time, "Distribución Porcentual de Estados de Órdenes por Mes", subfolder="general")
        except Exception as e_status_ot_plot:
            logger.error(f"Error al generar gráfico de Completitud de Órdenes para '{output_label} - {status_subdir}': {e_status_ot_plot}.")
    elif df_to_plot_from_pandas.empty:
        logger.info(f"DataFrame principal (df_to_plot_from_pandas) vacío para '{output_label} - {status_subdir}', no se genera gráfico de completitud de órdenes.")
    else:
        missing_cols_status_ot = []
        if time_col_name not in df_to_plot_from_pandas.columns: missing_cols_status_ot.append(time_col_name)
        if status_col_name not in df_to_plot_from_pandas.columns: missing_cols_status_ot.append(status_col_name)
        logger.warning(f"Faltan columnas requeridas ({', '.join(missing_cols_status_ot)}) para gráfico de completitud de órdenes en '{output_label} - {status_subdir}'.")

    # --- Heatmaps Hora x Día (plot_heatmap_hour_day) --- 
    # df_to_plot_from_pandas ya está disponible y es un DataFrame de Pandas
    # con Match_time_local procesado.
    
    # Heatmap para el conteo de operaciones
    if config.get('plotting', {}).get('generate_heatmaps_hour_day', True): # Usar la misma flag de config
        logger.info(f"Intentando generar Heatmap Hora x Día (Conteo) para '{output_label} - {status_subdir}'...")
        col_order_number = config.get('column_names', {}).get('order_number_internal', 'order_number')
        path_heatmap_count = plotting.plot_heatmap_hour_day(
            df_pd=df_to_plot_from_pandas, # PASAR EL DF PANDAS
            out_dir=figures_dir_general, # Guardar en figures/general/
            value_col_name=col_order_number, 
            agg_func='count', 
            title_suffix=f" ({final_title_suffix})",
            file_identifier=file_name_suffix_from_cli
        )
        add_figure_to_html_list(path_heatmap_count, "Heatmap Actividad (Conteo por Hora/Día)", subfolder="general")

        # Heatmap para la suma de TotalPrice_num
        logger.info(f"Intentando generar Heatmap Hora x Día (Suma TotalPrice) para '{output_label} - {status_subdir}'...")
        col_total_price = config.get('column_names', {}).get('total_price_num_internal', 'TotalPrice_num')
        path_heatmap_sum = plotting.plot_heatmap_hour_day(
            df_pd=df_to_plot_from_pandas, # PASAR EL DF PANDAS
            out_dir=figures_dir_general, # CORREGIDO: Usar figures_dir_general
            value_col_name=col_total_price, 
            agg_func='sum', 
            title_suffix=f" ({final_title_suffix})",
            file_identifier=file_name_suffix_from_cli
        )
    # df_to_plot_from es el DataFrame de Polars original para el período/estado actual
    if df_to_plot_from is not None and not df_to_plot_from.is_empty():
        try:
            path_sankey = plotting.plot_sankey_fiat_asset(
                df_to_plot_from, 
                figures_dir, 
                title_suffix=final_title_suffix, 
                file_identifier=file_name_suffix_from_cli
            )
        except Exception as e_sankey_plot:
            logger.error(f"Error al generar gráfico Sankey para '{output_label} - {status_subdir}': {e_sankey_plot}.")
        add_figure_to_html_list(path_sankey, "Flujo Fiat a Activo (Sankey)")
    else:
        logger.info(f"DataFrame principal (df_to_plot_from) vacío para '{output_label} - {status_subdir}', no se genera Sankey.")

    logger.info(f"Intentando generar Heatmaps Hora x Día para '{output_label} - {status_subdir}'...")
    path_heatmap_count = None
    path_heatmap_volume = None
    if df_to_plot_from is not None and not df_to_plot_from.is_empty():
        # Para el heatmap de conteo:
        try:
            # Intentar usar 'order_number' si existe, ya que es un buen candidato para contar operaciones únicas o filas.
            # La función de ploteo plot_heatmap_hour_day usará esta columna con agg_func='count'.
            # Si 'order_number' no está, la función de ploteo podría tener un fallback o podríamos pasar otra columna.
            col_for_counting = 'order_number' # Nombre estándar después del mapeo
            if col_for_counting not in df_to_plot_from.columns:
                # Si 'order_number' no está, intentamos con la primera columna del df como placeholder para 'count'.
                # La función de ploteo debería usar aggfunc='size' o 'count' sobre cualquier columna no nula.
                if not df_to_plot_from.is_empty() and len(df_to_plot_from.columns) > 0:
                    col_for_counting = df_to_plot_from.columns[0]
                    logger.info(f"Columna '{col_for_counting}' (primera disponible) se usará como base para heatmap de conteo en '{output_label} - {status_subdir}'.")
                else:
                    col_for_counting = None # No hay columnas disponibles
            
            if col_for_counting:
                path_heatmap_count = plotting.plot_heatmap_hour_day(
                    df_pd=df_to_plot_from_pandas, # PASAR EL DF PANDAS
                    out_dir=figures_dir_general, # Guardar en figures/general/
                    value_col_name=col_for_counting, 
                    agg_func='count', 
                    title_suffix=final_title_suffix, 
                    file_identifier=file_name_suffix_from_cli
                )
                add_figure_to_html_list(path_heatmap_count, "Heatmap de Actividad (Conteo de Operaciones)", subfolder="general")
            else:
                logger.warning(f"No se pudo determinar una columna para el heatmap de conteo en '{output_label} - {status_subdir}'. El DataFrame está vacío o no tiene columnas.")

        except Exception as e_heatmap_count:
            logger.error(f"Error al generar Heatmap (conteo) para '{output_label} - {status_subdir}': {e_heatmap_count}.")

        # Para el heatmap de volumen (TotalPrice_num):
        # if 'TotalPrice_num' in df_to_plot_from.columns: 
        #     try:
        #         path_heatmap_volume = plotting.plot_heatmap_hour_day(
        #             df_pd=df_to_plot_from_pandas, # PASAR EL DF PANDAS
        #             out_dir=figures_dir, 
        #             value_col_name='TotalPrice_num', 
        #             agg_func='sum', 
        #             title_suffix=final_title_suffix, 
        #             file_identifier=file_name_suffix_from_cli
        #         )
        #         add_figure_to_html_list(path_heatmap_volume, "Heatmap de Actividad (Volumen TotalPrice_num)")
        #     except Exception as e_heatmap_vol:
        #         logger.error(f"Error al generar Heatmap (volumen) para '{output_label} - {status_subdir}': {e_heatmap_vol}.")
        # else:
        #     logger.warning(f"Columna 'TotalPrice_num' no encontrada para heatmap de volumen en '{output_label} - {status_subdir}'.")

        # --- Heatmaps de Volumen por Moneda Fiat Específica ---
        if 'TotalPrice_num' in df_to_plot_from_pandas.columns and 'fiat_type' in df_to_plot_from_pandas.columns:
            # Heatmap para USD y USDT (usando TotalPrice_num filtrado)
            df_usd_usdt = df_to_plot_from_pandas[df_to_plot_from_pandas['fiat_type'].isin(['USD', 'USDT'])]
            if not df_usd_usdt.empty:
                try:
                    path_heatmap_volume_usd = plotting.plot_heatmap_hour_day(
                        df_pd=df_usd_usdt,
                        out_dir=figures_dir_usd, # Guardar en figures/usd_usdt/
                        value_col_name='TotalPrice_num',
                        agg_func='sum',
                        title_suffix=f"{final_title_suffix} (USD/USDT)",
                        file_identifier=f"{file_name_suffix_from_cli}_vol_usd_usdt"
                    )
                    add_figure_to_html_list(path_heatmap_volume_usd, "Heatmap de Actividad (Volumen USD/USDT)", subfolder="usd_usdt")
                except Exception as e_heatmap_vol_usd:
                    logger.error(f"Error al generar Heatmap de volumen USD/USDT para '{output_label} - {status_subdir}': {e_heatmap_vol_usd}.")
            else:
                logger.info(f"No hay datos con fiat_type USD o USDT para heatmap de volumen en '{output_label} - {status_subdir}'.")

            # Heatmap para UYU
            df_uyu = df_to_plot_from_pandas[df_to_plot_from_pandas['fiat_type'] == 'UYU']
            if not df_uyu.empty:
                try:
                    path_heatmap_volume_uyu = plotting.plot_heatmap_hour_day(
                        df_pd=df_uyu,
                        out_dir=figures_dir_uyu, # Guardar en figures/uyu/
                        value_col_name='TotalPrice_num',
                        agg_func='sum',
                        title_suffix=f"{final_title_suffix} (UYU)",
                        file_identifier=f"{file_name_suffix_from_cli}_vol_uyu"
                    )
                    add_figure_to_html_list(path_heatmap_volume_uyu, "Heatmap de Actividad (Volumen UYU)", subfolder="uyu")
                except Exception as e_heatmap_vol_uyu:
                    logger.error(f"Error al generar Heatmap de volumen UYU para '{output_label} - {status_subdir}': {e_heatmap_vol_uyu}.")
            else:
                logger.info(f"No hay datos con fiat_type UYU para heatmap de volumen en '{output_label} - {status_subdir}'.")
        else:
            logger.warning(f"Columnas 'TotalPrice_num' o 'fiat_type' no encontradas para heatmaps de volumen por moneda en '{output_label} - {status_subdir}'.")

        # --- Heatmap de Volumen Combinado (equivalente en USD) ---
        if 'TotalPrice_USD_equivalent' in df_to_plot_from_pandas.columns:
            df_with_usd_equivalent = df_to_plot_from_pandas.dropna(subset=['TotalPrice_USD_equivalent'])
            if not df_with_usd_equivalent.empty:
                try:
                    path_heatmap_volume_combined = plotting.plot_heatmap_hour_day(
                        df_pd=df_with_usd_equivalent,
                        out_dir=figures_dir_combined, # Guardar en figures/combined/
                        value_col_name='TotalPrice_USD_equivalent',
                        agg_func='sum',
                        title_suffix=f"{final_title_suffix} (Volumen Combinado USD Eq.)",
                        file_identifier=f"{file_name_suffix_from_cli}_vol_combined_usd_eq"
                    )
                    add_figure_to_html_list(path_heatmap_volume_combined, "Heatmap de Actividad (Volumen Combinado USD Eq.)", subfolder="combined")
                except Exception as e_heatmap_vol_combined:
                    logger.error(f"Error al generar Heatmap de volumen combinado para '{output_label} - {status_subdir}': {e_heatmap_vol_combined}.")
            else:
                logger.info(f"No hay datos con 'TotalPrice_USD_equivalent' válido para heatmap de volumen combinado en '{output_label} - {status_subdir}'.")
        else:
            logger.warning(f"Columna 'TotalPrice_USD_equivalent' no encontrada para heatmap de volumen combinado en '{output_label} - {status_subdir}'.")

        # --- Nuevo Gráfico: Volumen por Día de la Semana ---
        time_col_for_dow = config.get('column_names', {}).get('match_time_local_internal', 'Match_time_local')
        total_price_col_for_dow = config.get('column_names', {}).get('total_price_num_internal', 'TotalPrice_num')
        total_price_usd_eq_col_for_dow = 'TotalPrice_USD_equivalent' # Asumimos que este nombre es estable

        if time_col_for_dow in df_to_plot_from_pandas.columns:
            # 1. Volumen General (TotalPrice_num) por Día de la Semana
            if total_price_col_for_dow in df_to_plot_from_pandas.columns:
                logger.info(f"Generando Volumen General ({total_price_col_for_dow}) por Día de la Semana para '{output_label} - {status_subdir}'...")
                path_vol_dow_general = plotting.plot_volume_by_day_of_week(
                    df_data_pd=df_to_plot_from_pandas,
                    time_col=time_col_for_dow,
                    volume_col=total_price_col_for_dow,
                    volume_col_label=f"Volumen Total ({total_price_col_for_dow})",
                    out_dir=figures_dir_general,
                    title_suffix=final_title_suffix,
                    file_identifier=f"{file_name_suffix_from_cli}_general"
                )
                add_figure_to_html_list(path_vol_dow_general, f"Volumen General ({total_price_col_for_dow}) por Día de la Semana", subfolder="general")
            else:
                logger.warning(f"Columna '{total_price_col_for_dow}' no encontrada. No se generará gráfico de Volumen General por Día de la Semana.")

            # 2. Volumen USD/USDT (TotalPrice_num) por Día de la Semana
            if not df_usd_usdt.empty and total_price_col_for_dow in df_usd_usdt.columns: # df_usd_usdt se define antes para los heatmaps
                logger.info(f"Generando Volumen USD/USDT ({total_price_col_for_dow}) por Día de la Semana para '{output_label} - {status_subdir}'...")
                path_vol_dow_usd = plotting.plot_volume_by_day_of_week(
                    df_data_pd=df_usd_usdt,
                    time_col=time_col_for_dow,
                    volume_col=total_price_col_for_dow,
                    volume_col_label="Volumen Total (USD/USDT)",
                    out_dir=figures_dir_usd,
                    title_suffix=f"{final_title_suffix} (USD/USDT)",
                    file_identifier=f"{file_name_suffix_from_cli}_usd_usdt",
                    specific_plot_title=f"Volumen Total (USD/USDT) por Día de la Semana{final_title_suffix}"
                )
                add_figure_to_html_list(path_vol_dow_usd, "Volumen (USD/USDT) por Día de la Semana", subfolder="usd_usdt")
            else:
                logger.info(f"No hay datos USD/USDT o falta columna '{total_price_col_for_dow}' para Volumen por Día de la Semana.")

            # 3. Volumen UYU (TotalPrice_num) por Día de la Semana
            if not df_uyu.empty and total_price_col_for_dow in df_uyu.columns: # df_uyu se define antes para los heatmaps
                logger.info(f"Generando Volumen UYU ({total_price_col_for_dow}) por Día de la Semana para '{output_label} - {status_subdir}'...")
                path_vol_dow_uyu = plotting.plot_volume_by_day_of_week(
                    df_data_pd=df_uyu,
                    time_col=time_col_for_dow,
                    volume_col=total_price_col_for_dow,
                    volume_col_label="Volumen Total (UYU)",
                    out_dir=figures_dir_uyu,
                    title_suffix=f"{final_title_suffix} (UYU)",
                    file_identifier=f"{file_name_suffix_from_cli}_uyu",
                    specific_plot_title=f"Volumen Total (UYU) por Día de la Semana{final_title_suffix}"
                )
                add_figure_to_html_list(path_vol_dow_uyu, "Volumen (UYU) por Día de la Semana", subfolder="uyu")
            else:
                logger.info(f"No hay datos UYU o falta columna '{total_price_col_for_dow}' para Volumen por Día de la Semana.")

            # 4. Volumen Combinado (TotalPrice_USD_equivalent) por Día de la Semana
            if total_price_usd_eq_col_for_dow in df_to_plot_from_pandas.columns:
                logger.info(f"Generando Volumen Combinado ({total_price_usd_eq_col_for_dow}) por Día de la Semana para '{output_label} - {status_subdir}'...")
                path_vol_dow_combined = plotting.plot_volume_by_day_of_week(
                    df_data_pd=df_to_plot_from_pandas,
                    time_col=time_col_for_dow,
                    volume_col=total_price_usd_eq_col_for_dow,
                    volume_col_label="Volumen Total (USD Equivalente)",
                    out_dir=figures_dir_combined,
                    title_suffix=final_title_suffix,
                    file_identifier=f"{file_name_suffix_from_cli}_combined_usd_eq",
                    specific_plot_title=f"Volumen Total (USD Equivalente) por Día de la Semana{final_title_suffix}"
                )
                add_figure_to_html_list(path_vol_dow_combined, "Volumen Combinado (USD Eq.) por Día de la Semana", subfolder="combined")
            else:
                logger.warning(f"Columna '{total_price_usd_eq_col_for_dow}' no encontrada. No se generará gráfico de Volumen Combinado por Día de la Semana.")
        else:
            logger.warning(f"Columna de tiempo '{time_col_for_dow}' no encontrada. No se generarán gráficos de Volumen por Día de la Semana.")

    else:
        logger.info(f"DataFrame principal (df_to_plot_from) vacío para '{output_label} - {status_subdir}', no se generan Heatmaps Hora x Día.")

    # DONE: 2.3 Llamar a plot_violin_price_vs_payment_method
    logger.info(f"Intentando generar Gráficos de Violín (Precio vs Método Pago) para '{output_label} - {status_subdir}'...")
    paths_violin_price_payment = None
    # if df_to_plot_from is not None and not df_to_plot_from.is_empty():
    #     try:
    #         paths_violin_price_payment = plotting.plot_violin_price_vs_payment_method(
    #             df_to_plot_from, 
    #             figures_dir, 
    #             title_suffix=final_title_suffix, 
    #             file_identifier=file_name_suffix_from_cli
    #         )
    #     except Exception as e_violin_plot:
    #         logger.error(f"Error al generar gráficos de violín (Precio vs Método Pago) para '{output_label} - {status_subdir}': {e_violin_plot}.")
    #     add_figure_to_html_list(paths_violin_price_payment, "Distribución de Precio por Método de Pago (Violín)")
    # else:
    #     logger.info(f"DataFrame principal (df_to_plot_from) vacío para '{output_label} - {status_subdir}', no se generan gráficos de violín.")

    # DONE: 2.4 Llamar a plot_yoy_monthly_comparison
    logger.info(f"Intentando generar Gráficos YoY Mensuales para '{output_label} - {status_subdir}'...")
    paths_yoy_total_price = None
    paths_yoy_quantity = None
    # if df_to_plot_from is not None and not df_to_plot_from.is_empty():
    #     # YoY para TotalPrice_num
    #     if 'TotalPrice_num' in df_to_plot_from.columns:
    #         try:
    #             paths_yoy_total_price = plotting.plot_yoy_monthly_comparison(
    #                 df_to_plot_from, 
    #                 figures_dir, 
    #                 value_col='TotalPrice_num',
    #                 agg_func='sum',
    #                 title_suffix=final_title_suffix, 
    #                 file_identifier=file_name_suffix_from_cli
    #             )
    #             add_figure_to_html_list(paths_yoy_total_price, "Comparación Mensual YoY (Suma de TotalPrice_num)")
    #         except Exception as e_yoy_tp:
    #             logger.error(f"Error al generar gráficos YoY (TotalPrice_num) para '{output_label} - {status_subdir}': {e_yoy_tp}.")
    #     else:
    #         logger.warning(f"Columna 'TotalPrice_num' no encontrada para YoY en '{output_label} - {status_subdir}'.")

    #     # YoY para Quantity_num
    #     if 'Quantity_num' in df_to_plot_from.columns:
    #         try:
    #             paths_yoy_quantity = plotting.plot_yoy_monthly_comparison(
    #                 df_to_plot_from, 
    #                 figures_dir, 
    #                 value_col='Quantity_num',
    #                 agg_func='sum',
    #                 title_suffix=final_title_suffix, 
    #                 file_identifier=file_name_suffix_from_cli
    #             )
    #             add_figure_to_html_list(paths_yoy_quantity, "Comparación Mensual YoY (Suma de Quantity_num)")
    #         except Exception as e_yoy_qty:
    #             logger.error(f"Error al generar gráficos YoY (Quantity_num) para '{output_label} - {status_subdir}': {e_yoy_qty}.")
    #     else:
    #         logger.warning(f"Columna 'Quantity_num' no encontrada para YoY en '{output_label} - {status_subdir}'.")
    # else:
    #     logger.info(f"DataFrame principal (df_to_plot_from) vacío para '{output_label} - {status_subdir}', no se generan gráficos YoY.")

    # DONE: 2.5 Llamar a plot_animated_scatter_price_volume
    logger.info(f"Intentando generar Scatter Animado (Precio/Volumen) para '{output_label} - {status_subdir}'...")
    path_animated_scatter = None
    # if df_to_plot_from is not None and not df_to_plot_from.is_empty():
    #     # Usaremos el df_to_plot_from que corresponde al período y estado actual.
    #     # La función de ploteo ya está diseñada para manejar Polars y convertir a Pandas.
    #     try:
    #         path_animated_scatter = plotting.plot_animated_scatter_price_volume(
    #             df_to_plot_from, 
    #             figures_dir, 
    #             title_suffix=final_title_suffix, 
    #             file_identifier=file_name_suffix_from_cli
    #         )
    #     except Exception as e_anim_scatter:
    #         logger.error(f"Error al generar scatter animado para '{output_label} - {status_subdir}': {e_anim_scatter}.")
    #     add_figure_to_html_list(path_animated_scatter, "Scatter Animado Precio vs. Volumen por Día")
    # else:
    #     logger.info(f"DataFrame principal (df_to_plot_from) vacío para '{output_label} - {status_subdir}', no se genera scatter animado.")

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
                current_subfolder = "usd_usdt" if pair_info['fiat'] == "USD" else "uyu" # Determinar subfolder
                output_directory = figures_dir_usd if pair_info['fiat'] == "USD" else figures_dir_uyu

                try:
                    paths_dist_pair = plotting.plot_price_distribution(df_filtered, output_directory, title_suffix=final_title_suffix, file_identifier=specific_file_id)
                    if paths_dist_pair:
                        path_to_add = paths_dist_pair[0] if isinstance(paths_dist_pair, list) and paths_dist_pair else paths_dist_pair
                        if path_to_add:
                             add_figure_to_html_list(path_to_add, f"Distribución de Precios - {pair_info['title_suffix']}", subfolder=current_subfolder)
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
                current_subfolder = "usd_usdt" if pair_info['fiat'] == "USD" else "uyu" # Determinar subfolder
                output_directory = figures_dir_usd if pair_info['fiat'] == "USD" else figures_dir_uyu

                try:
                    paths_scatter_pair = plotting.plot_volume_vs_price_scatter(df_filtered, output_directory, title_suffix=final_title_suffix, file_identifier=specific_file_id)
                    if paths_scatter_pair:
                        path_to_add = paths_scatter_pair[0] if isinstance(paths_scatter_pair, list) and paths_scatter_pair else paths_scatter_pair
                        if path_to_add:
                            add_figure_to_html_list(path_to_add, f"Volumen vs. Precio - {pair_info['title_suffix']}", subfolder=current_subfolder)
                except Exception as e:
                    logger.error(f"Error en plot_volume_vs_price_scatter para {pair_info['asset']}/{pair_info['fiat']}: {e}")
            else:
                logger.info(f"No hay datos 'Completed' para {pair_info['asset']}/{pair_info['fiat']} para Volumen vs. Precio.")
        
        # --- Nuevos Boxplots por Método de Pago ---
        payment_method_col_name = config.get('column_names', {}).get('payment_method_cleaned_internal', 'Payment_method_cleaned') # Usar el nombre de columna configurado o un default

        if payment_method_col_name in df_completed_for_plots_pandas.columns:
            # 1. Boxplot de Price_num vs Payment_method (USD/USDT)
            logger.info(f"Generando Boxplot Precio vs Método de Pago para USD/USDT en '{output_label} - {status_subdir}'...")
            df_usd_pair = df_completed_for_plots_pandas[
                (df_completed_for_plots_pandas[asset_col_name] == 'USDT') &
                (df_completed_for_plots_pandas[fiat_col_name] == 'USD')
            ]
            if not df_usd_pair.empty:
                paths_boxplot_price_usd = plotting.plot_boxplot_by_payment_method(
                    df_data_pd=df_usd_pair,
                    value_col_name='Price_num',
                    value_col_label="Precio",
                    payment_method_col=payment_method_col_name,
                    asset_col=asset_col_name,
                    fiat_col=fiat_col_name,
                    out_dir=figures_dir_usd,
                    title_suffix=final_title_suffix,
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_USD"
                )
                add_figure_to_html_list(paths_boxplot_price_usd, "Distribución de Precio por Método de Pago (USDT/USD)", subfolder="usd_usdt")
            else:
                logger.info(f"No hay datos USDT/USD para Boxplot Precio vs Método de Pago en '{output_label} - {status_subdir}'.")

            # 2. Boxplot de TotalPrice_num vs Payment_method (USD/USDT)
            logger.info(f"Generando Boxplot Volumen Fiat vs Método de Pago para USD/USDT en '{output_label} - {status_subdir}'...")
            if not df_usd_pair.empty: # Reusamos df_usd_pair
                paths_boxplot_volume_usd = plotting.plot_boxplot_by_payment_method(
                    df_data_pd=df_usd_pair,
                    value_col_name='TotalPrice_num',
                    value_col_label="Volumen Fiat",
                    payment_method_col=payment_method_col_name,
                    asset_col=asset_col_name,
                    fiat_col=fiat_col_name,
                    out_dir=figures_dir_usd,
                    title_suffix=final_title_suffix,
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_USD"
                )
                add_figure_to_html_list(paths_boxplot_volume_usd, "Distribución de Volumen Fiat por Método de Pago (USDT/USD)", subfolder="usd_usdt")
            # No es necesario un else aquí

            # 3. Boxplot de Price_num vs Payment_method (UYU)
            logger.info(f"Generando Boxplot Precio vs Método de Pago para UYU en '{output_label} - {status_subdir}'...")
            df_uyu_pair = df_completed_for_plots_pandas[
                (df_completed_for_plots_pandas[asset_col_name] == 'USDT') &
                (df_completed_for_plots_pandas[fiat_col_name] == 'UYU')
            ]
            if not df_uyu_pair.empty:
                paths_boxplot_price_uyu = plotting.plot_boxplot_by_payment_method(
                    df_data_pd=df_uyu_pair,
                    value_col_name='Price_num',
                    value_col_label="Precio",
                    payment_method_col=payment_method_col_name,
                    asset_col=asset_col_name,
                    fiat_col=fiat_col_name,
                    out_dir=figures_dir_uyu,
                    title_suffix=final_title_suffix,
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_UYU"
                )
                add_figure_to_html_list(paths_boxplot_price_uyu, "Distribución de Precio por Método de Pago (USDT/UYU)", subfolder="uyu")
            else:
                logger.info(f"No hay datos USDT/UYU para Boxplot Precio vs Método de Pago en '{output_label} - {status_subdir}'.")

            # 4. Boxplot de TotalPrice_num vs Payment_method (UYU)
            logger.info(f"Generando Boxplot Volumen Fiat vs Método de Pago para UYU en '{output_label} - {status_subdir}'...")
            if not df_uyu_pair.empty: # Reusamos df_uyu_pair
                paths_boxplot_volume_uyu = plotting.plot_boxplot_by_payment_method(
                    df_data_pd=df_uyu_pair,
                    value_col_name='TotalPrice_num',
                    value_col_label="Volumen Fiat",
                    payment_method_col=payment_method_col_name,
                    asset_col=asset_col_name,
                    fiat_col=fiat_col_name,
                    out_dir=figures_dir_uyu,
                    title_suffix=final_title_suffix,
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_UYU"
                )
                add_figure_to_html_list(paths_boxplot_volume_uyu, "Distribución de Volumen Fiat por Método de Pago (USDT/UYU)", subfolder="uyu")
            # No es necesario un else aquí

            # 5. Boxplot de TotalPrice_USD_equivalent vs Payment_method (Combinado)
            if 'TotalPrice_USD_equivalent' in df_completed_for_plots_pandas.columns:
                logger.info(f"Generando Boxplot Volumen Combinado (USD Eq.) vs Método de Pago en '{output_label} - {status_subdir}'...")
                paths_boxplot_vol_combined = plotting.plot_boxplot_by_payment_method(
                    df_data_pd=df_completed_for_plots_pandas, # Usar todos los datos completados
                    value_col_name='TotalPrice_USD_equivalent',
                    value_col_label="Volumen Combinado (USD Eq.)",
                    payment_method_col=payment_method_col_name,
                    asset_col=None, # Indicar que no es por par asset/fiat específico
                    fiat_col=None,  # Indicar que no es por par asset/fiat específico
                    out_dir=figures_dir_combined,
                    title_suffix=final_title_suffix,
                    file_identifier=f"{file_name_suffix_from_cli}_Combined_USD_Eq"
                )
                add_figure_to_html_list(paths_boxplot_vol_combined, "Distribución de Volumen Combinado (USD Eq.) por Método de Pago", subfolder="combined")
            else:
                logger.warning(f"Columna 'TotalPrice_USD_equivalent' no encontrada. No se generará Boxplot de Volumen Combinado por Método de Pago en '{output_label} - {status_subdir}'.")
        else:
            logger.warning(f"Columna de método de pago '{payment_method_col_name}' no encontrada. No se generarán Boxplots por Método de Pago en '{output_label} - {status_subdir}'.")

        # Asegurarse de que df_uyu_pair y df_usd_pair estén definidos, incluso si los boxplots no se generaron.
        # Se inicializan a DataFrames vacíos si no existen en este punto.
        if 'df_uyu_pair' not in locals():
            df_uyu_pair = pd.DataFrame()
            logger.info(f"df_uyu_pair inicializado a DataFrame vacío porque no se definió previamente (posiblemente por falta de columna de método de pago).")
        
        if 'df_usd_pair' not in locals(): # Hacemos lo mismo para df_usd_pair por consistencia, aunque el error no fue por este.
            df_usd_pair = pd.DataFrame()
            logger.info(f"df_usd_pair inicializado a DataFrame vacío porque no se definió previamente.")

        # --- Nuevo Gráfico: Volumen de Compra vs. Venta Mensual ---
        logger.info(f"Generando gráficos de Volumen Compra vs. Venta Mensual para '{output_label} - {status_subdir}'...")
        time_col_buysell = config.get('column_names', {}).get('match_time_local_internal', 'Match_time_local')
        volume_col_buysell_fiat = config.get('column_names', {}).get('total_price_num_internal', 'TotalPrice_num')
        volume_col_buysell_usd_eq = 'TotalPrice_USD_equivalent'
        order_type_col_buysell = config.get('column_names', {}).get('order_type_internal', 'order_type') # o 'side_internal' dependiendo de la config

        required_cols_for_buysell = [time_col_buysell, order_type_col_buysell]
        # Verificar columnas base requeridas
        if all(col in df_completed_for_plots_pandas.columns for col in required_cols_for_buysell):
            # 1. Compra vs. Venta para USD/USDT (usando TotalPrice_num)
            if volume_col_buysell_fiat in df_usd_pair.columns: # df_usd_pair ya está filtrado por asset y fiat USD
                path_bs_vol_usd = plotting.plot_buy_sell_volume_over_time(
                    df_data_pd=df_usd_pair, 
                    time_col=time_col_buysell,
                    volume_col=volume_col_buysell_fiat,
                    order_type_col=order_type_col_buysell,
                    out_dir=figures_dir_usd,
                    volume_col_label="Volumen Fiat (USD/USDT)",
                    title_suffix=f"{final_title_suffix} (USDT/USD)",
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_USD",
                    specific_plot_title=f"Volumen Mensual Compra vs. Venta (USD/USDT){final_title_suffix}"
                )
                add_figure_to_html_list(path_bs_vol_usd, "Volumen Mensual Compra vs. Venta (USD/USDT)", subfolder="usd_usdt")
            else:
                logger.warning(f"Columna de volumen fiat '{volume_col_buysell_fiat}' no en df_usd_pair para Compra/Venta en '{output_label} - {status_subdir}'.")

            # 2. Compra vs. Venta para UYU (usando TotalPrice_num)
            if volume_col_buysell_fiat in df_uyu_pair.columns: # df_uyu_pair ya está filtrado por asset y fiat UYU
                path_bs_vol_uyu = plotting.plot_buy_sell_volume_over_time(
                    df_data_pd=df_uyu_pair,
                    time_col=time_col_buysell,
                    volume_col=volume_col_buysell_fiat,
                    order_type_col=order_type_col_buysell,
                    out_dir=figures_dir_uyu,
                    volume_col_label="Volumen Fiat (UYU)",
                    title_suffix=f"{final_title_suffix} (USDT/UYU)",
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_UYU",
                    specific_plot_title=f"Volumen Mensual Compra vs. Venta (UYU){final_title_suffix}"
                )
                add_figure_to_html_list(path_bs_vol_uyu, "Volumen Mensual Compra vs. Venta (UYU)", subfolder="uyu")
            else:
                logger.warning(f"Columna de volumen fiat '{volume_col_buysell_fiat}' no en df_uyu_pair para Compra/Venta en '{output_label} - {status_subdir}'.")

            # 3. Compra vs. Venta Combinado (usando TotalPrice_USD_equivalent)
            if volume_col_buysell_usd_eq in df_completed_for_plots_pandas.columns:
                path_bs_vol_combined = plotting.plot_buy_sell_volume_over_time(
                    df_data_pd=df_completed_for_plots_pandas, # Usar todos los datos completados
                    time_col=time_col_buysell,
                    volume_col=volume_col_buysell_usd_eq,
                    order_type_col=order_type_col_buysell,
                    out_dir=figures_dir_combined,
                    volume_col_label="Volumen (USD Equivalente)",
                    title_suffix=f"{final_title_suffix} (Combinado USD Eq.)",
                    file_identifier=f"{file_name_suffix_from_cli}_Combined_USD_Eq",
                    specific_plot_title=f"Volumen Mensual Compra vs. Venta (Combinado USD Eq.){final_title_suffix}"
                )
                add_figure_to_html_list(path_bs_vol_combined, "Volumen Mensual Compra vs. Venta (Combinado USD Eq.)", subfolder="combined")
            else:
                logger.warning(f"Columna de volumen '{volume_col_buysell_usd_eq}' no encontrada para Compra/Venta Combinado en '{output_label} - {status_subdir}'.")
        else:
            missing_cols_bs_str = ", ".join([col for col in required_cols_for_buysell if col not in df_completed_for_plots_pandas.columns])
            logger.warning(f"Faltan columnas base ({missing_cols_bs_str}) para gráficos de Volumen Compra vs. Venta en '{output_label} - {status_subdir}'.")

        # --- Nuevo Gráfico: Scatter de Correlación Precio vs. Volumen Total Fiat ---
        logger.info(f"Generando gráficos de Scatter Precio vs. Volumen Total Fiat para '{output_label} - {status_subdir}'...")
        price_col_scatter = config.get('column_names', {}).get('price_num_internal', 'Price_num')
        total_fiat_col_scatter = config.get('column_names', {}).get('total_price_num_internal', 'TotalPrice_num')
        total_fiat_usd_eq_col_scatter = 'TotalPrice_USD_equivalent'
        order_type_col_scatter = config.get('column_names', {}).get('order_type_internal', 'order_type')
        # asset_col_name y fiat_col_name ya están definidos

        required_cols_for_scatter = [price_col_scatter, order_type_col_scatter, asset_col_name, fiat_col_name]

        if all(col in df_completed_for_plots_pandas.columns for col in required_cols_for_scatter):
            # 1. Scatter para USDT/USD (usando TotalPrice_num)
            if total_fiat_col_scatter in df_usd_pair.columns:
                path_scatter_usd = plotting.plot_price_vs_total_fiat_scatter(
                    df_data_pd=df_usd_pair, 
                    price_col=price_col_scatter,
                    total_fiat_col=total_fiat_col_scatter,
                    order_type_col=order_type_col_scatter,
                    asset_col_for_grouping=asset_col_name, # Usado para el título y file_identifier en la función
                    fiat_col_for_grouping=fiat_col_name,
                    out_dir=figures_dir_usd,
                    x_axis_label=f"Precio USDT (en USD)",
                    y_axis_label=f"Volumen Total Transacción (USD)",
                    title_suffix=f"{final_title_suffix} (USDT/USD)",
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_USD",
                    specific_plot_title=f"Precio vs. Volumen Total (USDT/USD){final_title_suffix}"
                )
                add_figure_to_html_list(path_scatter_usd, "Scatter Precio vs. Volumen Total (USDT/USD)", subfolder="usd_usdt")
            else:
                logger.warning(f"Columna '{total_fiat_col_scatter}' no en df_usd_pair para Scatter en '{output_label} - {status_subdir}'.")

            # 2. Scatter para USDT/UYU (usando TotalPrice_num)
            if total_fiat_col_scatter in df_uyu_pair.columns:
                path_scatter_uyu = plotting.plot_price_vs_total_fiat_scatter(
                    df_data_pd=df_uyu_pair, 
                    price_col=price_col_scatter,
                    total_fiat_col=total_fiat_col_scatter,
                    order_type_col=order_type_col_scatter,
                    asset_col_for_grouping=asset_col_name,
                    fiat_col_for_grouping=fiat_col_name,
                    out_dir=figures_dir_uyu,
                    x_axis_label=f"Precio USDT (en UYU)",
                    y_axis_label=f"Volumen Total Transacción (UYU)",
                    title_suffix=f"{final_title_suffix} (USDT/UYU)",
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_UYU",
                    specific_plot_title=f"Precio vs. Volumen Total (USDT/UYU){final_title_suffix}"
                )
                add_figure_to_html_list(path_scatter_uyu, "Scatter Precio vs. Volumen Total (USDT/UYU)", subfolder="uyu")
            else:
                logger.warning(f"Columna '{total_fiat_col_scatter}' no en df_uyu_pair para Scatter en '{output_label} - {status_subdir}'.")

            # 3. Scatter Combinado (Precio USDT vs TotalPrice_USD_equivalent, coloreado por fiat_type original)
            if total_fiat_usd_eq_col_scatter in df_completed_for_plots_pandas.columns and price_col_scatter in df_completed_for_plots_pandas.columns:
                # Para el combinado, queremos Precio de USDT vs. el Volumen Total en USD Equivalente.
                # Filtramos donde el asset es USDT para que el price_col_scatter (Precio USDT) tenga sentido.
                df_usdt_completed = df_completed_for_plots_pandas[df_completed_for_plots_pandas[asset_col_name] == 'USDT']
                if not df_usdt_completed.empty:
                    path_scatter_combined = plotting.plot_price_vs_total_fiat_scatter(
                        df_data_pd=df_usdt_completed,
                        price_col=price_col_scatter, # Precio del USDT
                        total_fiat_col=total_fiat_usd_eq_col_scatter, # Volumen en USD eq.
                        order_type_col=order_type_col_scatter, # Usar order_type para el hue primario si hue_col_for_combined no se especifica o no es útil.
                                                                # Opcionalmente, se podría pasar fiat_col_name a hue_col_for_combined para ver de qué fiat original vino la transacción.
                        asset_col_for_grouping=None, # Es combinado, no agrupamos por asset/fiat aquí
                        fiat_col_for_grouping=None,
                        out_dir=figures_dir_combined,
                        x_axis_label=f"Precio USDT",
                        y_axis_label=f"Volumen Total Transacción (USD Equivalente)",
                        title_suffix=f"{final_title_suffix} (Combinado)",
                        file_identifier=f"{file_name_suffix_from_cli}_Combined_USD_Eq",
                        specific_plot_title=f"Precio USDT vs. Volumen Total (Combinado USD Eq.){final_title_suffix}",
                        hue_col_for_combined=fiat_col_name # Colorear por el fiat original (USD o UYU)
                    )
                    add_figure_to_html_list(path_scatter_combined, "Scatter Precio USDT vs. Volumen Total (Combinado USD Eq.)", subfolder="combined")
                else:
                    logger.info(f"No hay datos de USDT completados para Scatter Combinado en '{output_label} - {status_subdir}'.")
            else:
                logger.warning(f"Columnas '{total_fiat_usd_eq_col_scatter}' o '{price_col_scatter}' no encontradas para Scatter Combinado en '{output_label} - {status_subdir}'.")
        else:
            missing_cols_scatter_str = ", ".join([col for col in required_cols_for_scatter if col not in df_completed_for_plots_pandas.columns])
            logger.warning(f"Faltan columnas base ({missing_cols_scatter_str}) para gráficos Scatter Precio vs Volumen en '{output_label} - {status_subdir}'.")

        # --- Nuevo Gráfico: Profundidad de Mercado Simplificado ---
        logger.info(f"Generando gráficos de Profundidad de Mercado Simplificado para '{output_label} - {status_subdir}'...")
        price_col_md = config.get('column_names', {}).get('price_num_internal', 'Price_num')
        qty_col_md = config.get('column_names', {}).get('quantity_num_internal', 'Quantity_num')
        order_type_col_md = config.get('column_names', {}).get('order_type_internal', 'order_type')
        # asset_col_name y fiat_col_name ya están definidos

        required_cols_for_md = [price_col_md, qty_col_md, order_type_col_md, asset_col_name, fiat_col_name]
        if all(col in df_completed_for_plots_pandas.columns for col in required_cols_for_md):
            # La función plot_simplified_market_depth itera internamente por pares (asset, fiat)
            # por lo que una sola llamada con df_completed_for_plots_pandas generaría para todos los pares.
            # Sin embargo, para controlar el directorio de salida (figures_dir_usd, figures_dir_uyu),
            # es mejor pasar DataFrames ya filtrados por el par principal o que la función acepte un out_dir dinámico.
            # Dado que la función actual toma un solo out_dir, le pasaremos los DFs filtrados.

            # Profundidad para USDT/USD
            if not df_usd_pair.empty:
                paths_md_usd = plotting.plot_simplified_market_depth(
                    df_data_pd=df_usd_pair,
                    price_col=price_col_md,
                    quantity_col=qty_col_md,
                    order_type_col=order_type_col_md,
                    asset_col=asset_col_name,
                    fiat_col=fiat_col_name,
                    out_dir=figures_dir_usd,
                    title_suffix=f"{final_title_suffix} (USDT/USD)",
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_USD"
                )
                add_figure_to_html_list(paths_md_usd, "Profundidad de Mercado Simplificada (USDT/USD)", subfolder="usd_usdt")
            else:
                logger.info(f"No hay datos USDT/USD completados para gráfico de Profundidad de Mercado en '{output_label} - {status_subdir}'.")

            # Profundidad para USDT/UYU
            if not df_uyu_pair.empty:
                paths_md_uyu = plotting.plot_simplified_market_depth(
                    df_data_pd=df_uyu_pair,
                    price_col=price_col_md,
                    quantity_col=qty_col_md,
                    order_type_col=order_type_col_md,
                    asset_col=asset_col_name,
                    fiat_col=fiat_col_name,
                    out_dir=figures_dir_uyu,
                    title_suffix=f"{final_title_suffix} (USDT/UYU)",
                    file_identifier=f"{file_name_suffix_from_cli}_USDT_UYU"
                )
                add_figure_to_html_list(paths_md_uyu, "Profundidad de Mercado Simplificada (USDT/UYU)", subfolder="uyu")
            else:
                logger.info(f"No hay datos USDT/UYU completados para gráfico de Profundidad de Mercado en '{output_label} - {status_subdir}'.")
        else:
            missing_cols_md_str = ", ".join([col for col in required_cols_for_md if col not in df_completed_for_plots_pandas.columns])
            logger.warning(f"Faltan columnas ({missing_cols_md_str}) para gráficos de Profundidad de Mercado en '{output_label} - {status_subdir}'.")

        # --- Activity Heatmap --- 
        path_heatmap = None
        logger.info(f"[HEATMAP_DEBUG] Verificando para heatmap en '{output_label} - {status_subdir}'.")
        logger.info(f"[HEATMAP_DEBUG] df_to_plot_from_pandas.empty: {df_to_plot_from_pandas.empty}")
        if not df_to_plot_from_pandas.empty:
            logger.info(f"[HEATMAP_DEBUG] Columnas en df_to_plot_from_pandas: {df_to_plot_from_pandas.columns.tolist()}")
            required_cols_heatmap = ['Match_time_local', 'order_number', 'hour_local']
            missing_cols = [col for col in required_cols_heatmap if col not in df_to_plot_from_pandas.columns]
            if missing_cols:
                logger.warning(f"[HEATMAP_DEBUG] Faltan columnas requeridas para heatmap en '{output_label} - {status_subdir}': {missing_cols}. DataFrame head:\n{df_to_plot_from_pandas.head().to_string()}")
            else:
                # Verificar si las columnas requeridas tienen datos válidos (no todos NaN)
                all_nan_cols = []
                for col in required_cols_heatmap:
                    if df_to_plot_from_pandas[col].isna().all():
                        all_nan_cols.append(col)
                if all_nan_cols:
                    logger.warning(f"[HEATMAP_DEBUG] Columnas requeridas para heatmap son todos NaN en '{output_label} - {status_subdir}': {all_nan_cols}. DataFrame head:\n{df_to_plot_from_pandas.head().to_string()}")
                else:
                    logger.info(f"Generando heatmap de actividad para '{output_label} - {status_subdir}' ({len(df_to_plot_from_pandas)} filas).")
                    try:
                        path_heatmap = plotting.plot_activity_heatmap(df_to_plot_from_pandas, figures_dir_general, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
                    except Exception as e: 
                        logger.error(f"Error en plot_activity_heatmap para '{output_label} - {status_subdir}': {e}")
                    add_figure_to_html_list(path_heatmap, "Heatmap de Actividad", subfolder="general")
        else:
            logger.info(f"Omitiendo heatmap de actividad para '{output_label} - {status_subdir}' ya que df_to_plot_from_pandas está vacío.")
    else:
        logger.info(f"Omitiendo gráficos basados en datos 'Completed' para '{output_label} - {status_subdir}' ya que no hay datos 'Completed' o el DataFrame base está vacío.")

    # --- Fees Analysis Plot --- 
    # fees_stats_pd = metrics_to_save_pandas.get('fees_stats') # Ya no se necesita el gráfico
    # path_fees = None
    # if fees_stats_pd is not None and not fees_stats_pd.empty and isinstance(fees_stats_pd, pd.DataFrame):
    #     asset_type_col_name_fees = 'asset_type' 
    #     if asset_type_col_name_fees in fees_stats_pd.columns:
    #         logger.info(f"Generando gráfico de análisis de comisiones para '{output_label} - {status_subdir}'.")
    #         fees_stats_pd_for_plot = fees_stats_pd.set_index(asset_type_col_name_fees)
    #         try:
    #             path_fees = plotting.plot_fees_analysis(fees_stats_pd_for_plot, figures_dir_general, title_suffix=final_title_suffix, file_identifier=file_name_suffix_from_cli) 
    #         except Exception as e: 
    #             logger.error(f"Error en plot_fees_analysis: {e}")
    #         add_figure_to_html_list(path_fees, "Análisis de Comisiones", subfolder="general")
    #     else:
    #         logger.warning(f"Columna '{asset_type_col_name_fees}' no encontrada en fees_stats_pd para ploteo en '{output_label} - {status_subdir}'. DF columns: {fees_stats_pd.columns}")

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
            'included_figures': figures_for_html,
            'interactive_mode': cli_args.interactive,
            'whale_trades_data': False, # Inicializar por si acaso
            'event_comparison_data': False # Inicializar por si acaso
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

        # DONE: 3.1 Añadir Whale Trades al contexto HTML
        whale_trades_df = metrics_to_save_pandas.get('whale_trades')
        if whale_trades_df is not None and isinstance(whale_trades_df, pd.DataFrame) and not whale_trades_df.empty:
            logger.info(f"Añadiendo 'whale_trades' al reporte HTML para '{output_label} - {status_subdir}'.")
            html_context['whale_trades_data'] = True # Indicar que hay datos
            try:
                # Formatear columnas de fecha/hora si existen, antes de convertir a HTML
                if 'Match_time_local' in whale_trades_df.columns:
                    # Intentar convertir a datetime si no lo es, luego formatear
                    if not pd.api.types.is_datetime64_any_dtype(whale_trades_df['Match_time_local']):
                        whale_trades_df['Match_time_local'] = pd.to_datetime(whale_trades_df['Match_time_local'], errors='coerce')
                    # Formatear solo si la conversión fue exitosa y es datetime
                    if pd.api.types.is_datetime64_any_dtype(whale_trades_df['Match_time_local']):
                         whale_trades_df['Match_time_local'] = whale_trades_df['Match_time_local'].dt.strftime('%Y-%m-%d %H:%M:%S')
                
                # Formatear columnas numéricas para mejor lectura
                for col_num_format in ['Price_num', 'Quantity_num', 'TotalPrice_num']:
                    if col_num_format in whale_trades_df.columns:
                        whale_trades_df[col_num_format] = whale_trades_df[col_num_format].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else x)

                # DONE: 4.2 Añadir clase datatable-ready
                html_context['whale_trades_table_html'] = whale_trades_df.to_html(classes='table table-striped table-hover table-sm datatable-ready', border=0, index=False, na_rep='N/A')
            except Exception as e_html_whale:
                logger.error(f"Error generando HTML para whale_trades: {e_html_whale}")
                html_context['whale_trades_table_html'] = "<p>Error al generar tabla de whale trades.</p>"
                html_context['whale_trades_data'] = False # Indicar que hubo error
        else:
            logger.info(f"No hay datos de 'whale_trades' para el reporte HTML en '{output_label} - {status_subdir}'.")
            html_context['whale_trades_data'] = False # Indicar que no hay datos

        # DONE: 3.2 Añadir Event Comparison al contexto HTML
        event_comp_df = metrics_to_save_pandas.get('event_comparison_stats')
        if cli_args.event_date and event_comp_df is not None and isinstance(event_comp_df, pd.DataFrame) and not event_comp_df.empty:
            logger.info(f"Añadiendo 'event_comparison_stats' para fecha {cli_args.event_date} al reporte HTML para '{output_label} - {status_subdir}'.")
            html_context['event_comparison_data'] = True # Indicar que hay datos
            html_context['event_date_for_report'] = cli_args.event_date
            try:
                # Formatear columnas numéricas para mejor lectura
                cols_to_format_event = ['num_trades', 'total_volume_asset', 'total_volume_fiat', 'avg_price', 'median_price']
                event_comp_df_display = event_comp_df.copy()
                for col_num_format in cols_to_format_event:
                    if col_num_format in event_comp_df_display.columns:
                        if col_num_format == 'num_trades':
                             event_comp_df_display[col_num_format] = event_comp_df_display[col_num_format].apply(lambda x: f"{x:,}" if pd.notnull(x) else '0')
                        else:
                             event_comp_df_display[col_num_format] = event_comp_df_display[col_num_format].apply(lambda x: f"{x:,.2f}" if pd.notnull(x) else ('N/A' if x is None else x))
                
                # DONE: 4.2 Añadir clase datatable-ready
                html_context['event_comparison_table_html'] = event_comp_df_display.to_html(classes='table table-striped table-hover table-sm datatable-ready', border=0, index=False, na_rep='N/A')
            except Exception as e_html_event_comp:
                logger.error(f"Error generando HTML para event_comparison_stats: {e_html_event_comp}")
                html_context['event_comparison_table_html'] = "<p>Error al generar tabla de comparación de evento.</p>"
                html_context['event_comparison_data'] = False
        else:
            logger.info(f"No hay datos de 'event_comparison_stats' (o --event-date no usado/datos insuficientes) para el reporte HTML en '{output_label} - {status_subdir}'.")
            html_context['event_comparison_data'] = False

        sales_summary_df_key = 'sales_summary_all_assets_fiat_detailed'
        sales_summary_pd = metrics_to_save_pandas.get(sales_summary_df_key)
        if sales_summary_pd is not None and isinstance(sales_summary_pd, pd.DataFrame) and not sales_summary_pd.empty:
            logger.info(f"Añadiendo '{sales_summary_df_key}' al reporte HTML para '{output_label} - {status_subdir}'.")
            html_context['sales_summary_data']['sales_summary_all_assets_fiat_detailed'] = True
            try:
                # DONE: 4.2 Añadir clase datatable-ready
                html_context['sales_summary_data']['sales_summary_all_assets_fiat_detailed_html'] = sales_summary_pd.to_html(classes='table table-striped table-hover table-sm datatable-ready', border=0, index=False)
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
                        # DONE: 4.2 Añadir clase datatable-ready
                        current_table_html = table_df_pandas_for_html.to_html(classes='table table-striped table-hover table-sm datatable-ready', border=0, index=should_show_index_for_series)
                    elif isinstance(table_df_pandas, pd.DataFrame):
                        should_show_index = True 
                        if table_key in ['status_counts', 'side_counts', 'hourly_counts']:
                            should_show_index = False 
                        elif isinstance(table_df_pandas.index, pd.RangeIndex) and table_df_pandas.index.name is None:
                            should_show_index = False
                        elif isinstance(table_df_pandas.index, pd.MultiIndex):
                            should_show_index = True 

                        # DONE: 4.2 Añadir clase datatable-ready
                        current_table_html = table_df_pandas.to_html(classes='table table-striped table-hover table-sm datatable-ready', border=0, index=should_show_index)
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

    # DONE: 4.3 Export XLSX multi-hoja
    logger.info(f"Iniciando exportación XLSX multi-hoja para '{output_label} - {status_subdir}'...")
    xlsx_filename = f"p2p_analysis_summary{file_name_suffix_from_cli}.xlsx"
    xlsx_path = os.path.join(reports_dir, xlsx_filename) # Guardar en la subcarpeta de reports
    
    try:
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            # Hoja de resumen con el DataFrame principal procesado
            if not df_to_plot_from_pandas.empty:
                try:
                    df_summary_sheet = df_to_plot_from_pandas.copy()
                    # Manejar índice del DataFrame si es datetime con timezone
                    if pd.api.types.is_datetime64_any_dtype(df_summary_sheet.index) and getattr(df_summary_sheet.index, 'tz', None) is not None:
                        logger.info(f"  Convirtiendo índice de 'Operaciones_Procesadas' a timezone-naive para Excel.")
                        df_summary_sheet.index = df_summary_sheet.index.tz_convert(None)
                        
                    for col in df_summary_sheet.columns:
                        if pd.api.types.is_datetime64_any_dtype(df_summary_sheet[col]):
                            if getattr(df_summary_sheet[col].dt, 'tz', None) is not None:
                                logger.info(f"  Convirtiendo columna datetime '{col}' en 'Operaciones_Procesadas' a timezone-naive para Excel.")
                                df_summary_sheet[col] = df_summary_sheet[col].dt.tz_convert(None)
                        elif df_summary_sheet[col].dtype == object or pd.api.types.is_extension_array_dtype(df_summary_sheet[col]):
                            try: # Intentar convertir a string si no es numérico ni datetime ya manejado
                                if not pd.api.types.is_numeric_dtype(df_summary_sheet[col].infer_objects()):
                                    logger.info(f"  Convirtiendo columna objeto/extensión '{col}' en 'Operaciones_Procesadas' a string para Excel.")
                                    df_summary_sheet[col] = df_summary_sheet[col].astype(str)
                            except Exception as e_astype:
                                logger.warning(f"  No se pudo convertir columna '{col}' a string en 'Operaciones_Procesadas': {e_astype}. Se deja como está.")
                    
                    max_raw_data_rows_excel = config.get('excel_export_max_raw_rows', 10000)
                    if len(df_summary_sheet) > max_raw_data_rows_excel:
                        logger.warning(f"DataFrame principal para Excel es muy grande ({len(df_summary_sheet)} filas), se truncará a {max_raw_data_rows_excel} filas para la hoja 'Operaciones_Procesadas'.")
                        df_summary_sheet = df_summary_sheet.head(max_raw_data_rows_excel)
                    df_summary_sheet.to_excel(writer, sheet_name='Operaciones_Procesadas', index=False)
                    logger.info(f"  Hoja 'Operaciones_Procesadas' añadida al XLSX.")
                except Exception as e_sheet_raw:
                    logger.error(f"  Error al escribir la hoja 'Operaciones_Procesadas' en XLSX: {e_sheet_raw}")

            # Guardar cada métrica (que sea DataFrame o Serie) en una hoja separada
            for metric_name, metric_data_pd_original in metrics_to_save_pandas.items():
                if isinstance(metric_data_pd_original, (pd.DataFrame, pd.Series)) and not metric_data_pd_original.empty:
                    metric_data_pd_excel = metric_data_pd_original.copy()
                    
                    if isinstance(metric_data_pd_excel, pd.DataFrame):
                        if pd.api.types.is_datetime64_any_dtype(metric_data_pd_excel.index) and getattr(metric_data_pd_excel.index, 'tz', None) is not None:
                            logger.info(f"  Convirtiendo índice de DataFrame métrica '{metric_name[:31]}' a timezone-naive para Excel.")
                            metric_data_pd_excel.index = metric_data_pd_excel.index.tz_convert(None)
                        for col in metric_data_pd_excel.columns:
                            if pd.api.types.is_datetime64_any_dtype(metric_data_pd_excel[col]):
                                if getattr(metric_data_pd_excel[col].dt, 'tz', None) is not None:
                                    logger.info(f"  Convirtiendo columna datetime '{col}' en hoja '{metric_name[:31]}' a timezone-naive para Excel.")
                                    metric_data_pd_excel[col] = metric_data_pd_excel[col].dt.tz_convert(None)
                            elif metric_data_pd_excel[col].dtype == object or pd.api.types.is_extension_array_dtype(metric_data_pd_excel[col]):
                                try:
                                    if not pd.api.types.is_numeric_dtype(metric_data_pd_excel[col].infer_objects()):
                                        logger.info(f"  Convirtiendo columna objeto/extensión '{col}' en hoja '{metric_name[:31]}' a string para Excel.")
                                        metric_data_pd_excel[col] = metric_data_pd_excel[col].astype(str)
                                except Exception as e_astype_metric_col:
                                    logger.warning(f"  No se pudo convertir columna '{col}' a string en hoja '{metric_name[:31]}': {e_astype_metric_col}. Se deja como está.")

                    elif isinstance(metric_data_pd_excel, pd.Series):
                        if pd.api.types.is_datetime64_any_dtype(metric_data_pd_excel.index) and getattr(metric_data_pd_excel.index, 'tz', None) is not None:
                            logger.info(f"  Convirtiendo índice de Serie '{metric_name[:31]}' a timezone-naive para Excel.")
                            metric_data_pd_excel.index = metric_data_pd_excel.index.tz_convert(None)
                        if pd.api.types.is_datetime64_any_dtype(metric_data_pd_excel.dtype) and getattr(metric_data_pd_excel.dt, 'tz', None) is not None:
                            logger.info(f"  Convirtiendo valores datetime de Serie '{metric_name[:31]}' a timezone-naive para Excel.")
                            metric_data_pd_excel = metric_data_pd_excel.dt.tz_convert(None)
                        elif metric_data_pd_excel.dtype == object or pd.api.types.is_extension_array_dtype(metric_data_pd_excel.dtype):
                            try:
                                if not pd.api.types.is_numeric_dtype(metric_data_pd_excel.infer_objects()):
                                    logger.info(f"  Convirtiendo valores objeto/extensión de Serie '{metric_name[:31]}' a string para Excel.")
                                    metric_data_pd_excel = metric_data_pd_excel.astype(str)
                            except Exception as e_astype_metric_series:
                                logger.warning(f"  No se pudo convertir valores de Serie '{metric_name[:31]}' a string : {e_astype_metric_series}. Se deja como está.")
                    
                    sane_sheet_name = metric_name.replace('[', '(').replace(']', ')').replace('*', '').replace(':', '-').replace('/', '-').replace('\\', '-').replace('?', '')
                    sane_sheet_name = sane_sheet_name[:31]
                    try:
                        metric_data_pd_excel.to_excel(writer, sheet_name=sane_sheet_name, index=isinstance(metric_data_pd_excel, pd.Series))
                        logger.info(f"  Hoja '{sane_sheet_name}' (desde métrica '{metric_name}') añadida al XLSX.")
                    except Exception as e_sheet:
                        logger.error(f"  Error al escribir hoja '{sane_sheet_name}' (métrica '{metric_name}') en XLSX: {e_sheet}")
                elif not isinstance(metric_data_pd_original, (pd.DataFrame, pd.Series)):
                     logger.info(f"  Métrica '{metric_name}' no es DataFrame/Serie Pandas, se omite de XLSX. Tipo: {type(metric_data_pd_original)}.")
        logger.info(f"Archivo XLSX multi-hoja guardado en: {xlsx_path}")
    except Exception as e_xlsx:
        logger.error(f"Error al generar o guardar el archivo XLSX '{xlsx_path}': {e_xlsx}")

    logger.info(f"--- FIN: Procesamiento y Guardado para: {section_id} ---") 
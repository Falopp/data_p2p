import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure
import plotly.graph_objects as go
import polars as pl
import plotly.express as px
from . import utils # Para formatear números, etc.
import matplotlib.ticker as mticker
from typing import Union, List, Any, Optional

logger = logging.getLogger(__name__)
sns.set_theme(style="whitegrid")

# --- Funciones de Visualización ---

def plot_hourly(hourly_counts: pd.Series, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    if hourly_counts.empty:
        logger.info(f"No hay datos para el gráfico horario{title_suffix}.")
        return None
    # Asegurar un índice completo de 0-23 horas y ordenado
    hourly_counts_reindexed = hourly_counts.reindex(range(24), fill_value=0).sort_index()
    
    x_tick_positions = hourly_counts_reindexed.index # Posiciones numéricas (0-23)
    x_category_labels = x_tick_positions.astype(str) # Etiquetas de categoría como string ('0', '1', ..., '23')
    y_data = pd.to_numeric(hourly_counts_reindexed.values, errors='coerce').fillna(0)

    plt.figure(figsize=(12, 8))
    # Usar x_tick_positions (numérico) para el eje X de barplot
    ax = sns.barplot(x=x_tick_positions, y=y_data, color="skyblue", palette=["skyblue"] if len(x_category_labels) <=1 else None)
    ax.set_title(f'Operaciones por Hora del Día (Local){title_suffix}', fontsize=15)
    ax.set_xlabel('Hora del Día (0-23)', fontsize=12)
    ax.set_ylabel('Cantidad de Operaciones', fontsize=12)
    
    # Establecer los ticks en las posiciones numéricas y las etiquetas como strings
    ax.set_xticks(x_tick_positions)
    ax.set_xticklabels(x_category_labels)

    # Si hay muchas horas, ajustar los xticks para mejorar legibilidad
    if len(x_tick_positions) > 12:
        locator = mticker.MaxNLocator(nbins=12, integer=True)
        ax.xaxis.set_major_locator(locator)

    ax.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout()
    file_path = os.path.join(out_dir, f'hourly_counts{file_identifier}.png')
    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico horario guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el gráfico horario {file_path}: {e}")
        plt.close()
        return None

def plot_monthly(monthly_fiat: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if monthly_fiat.empty:
        logger.info(f"No hay datos para el gráfico mensual{title_suffix}.")
        return saved_paths

    fiat_type_col_internal = 'fiat_type' 
    year_month_col_internal = 'YearMonthStr'

    if year_month_col_internal not in monthly_fiat.columns:
        logger.warning(f"Columna '{year_month_col_internal}' no encontrada para plot_monthly{title_suffix}.")
        return saved_paths
        
    unique_fiats = [None]
    fiat_column_for_grouping = None
    if fiat_type_col_internal in monthly_fiat.columns:
        fiat_column_for_grouping = fiat_type_col_internal
    elif monthly_fiat.index.name == fiat_type_col_internal:
        pass 
    elif isinstance(monthly_fiat.index, pd.MultiIndex) and fiat_type_col_internal in monthly_fiat.index.names:
        pass 

    if fiat_column_for_grouping and monthly_fiat[fiat_column_for_grouping].nunique() > 0:
        unique_fiats = monthly_fiat[fiat_column_for_grouping].unique()

    for current_fiat in unique_fiats:
        df_plot_full = monthly_fiat.copy()
        plot_title_fiat_part = ""
        current_fiat_label = "general"

        if current_fiat is not None and fiat_column_for_grouping:
            df_plot_full = monthly_fiat[monthly_fiat[fiat_column_for_grouping] == current_fiat]
            plot_title_fiat_part = f" para {current_fiat}"
            current_fiat_label = str(current_fiat)
        elif current_fiat is not None and monthly_fiat.index.name == fiat_type_col_internal:
             df_plot_full = monthly_fiat[monthly_fiat.index == current_fiat]
             plot_title_fiat_part = f" para {current_fiat}" # Asegurar que esto se setea
             current_fiat_label = str(current_fiat)       # Asegurar que esto se setea
        elif current_fiat is not None and isinstance(monthly_fiat.index, pd.MultiIndex) and fiat_type_col_internal in monthly_fiat.index.names:
             df_plot_full = monthly_fiat[monthly_fiat.index.get_level_values(fiat_type_internal) == current_fiat]
             plot_title_fiat_part = f" para {current_fiat}" # Asegurar que esto se setea
             current_fiat_label = str(current_fiat)       # Asegurar que esto se setea
        
        if df_plot_full.empty:
            continue

        exclude_cols = {year_month_col_internal} 
        if fiat_column_for_grouping:
            exclude_cols.add(fiat_column_for_grouping)
        
        potential_value_cols = [col for col in df_plot_full.columns if col not in exclude_cols]

        if not potential_value_cols and isinstance(df_plot_full, pd.Series): 
            potential_value_cols = [df_plot_full.name if df_plot_full.name else 'value']
            df_plot_full = df_plot_full.to_frame(name=potential_value_cols[0])

        if not potential_value_cols:
            logger.warning(f"No hay columnas de valor para graficar en plot_monthly para {current_fiat_label}{title_suffix}.")
            continue

        plt.figure(figsize=(14, 7))
        
        x_values_source = df_plot_full.index if df_plot_full.index.name == year_month_col_internal else df_plot_full[year_month_col_internal]
        
        # DONE: Convertir x_values_plot a datetime para un eje X temporal correcto
        try:
            # Intentar convertir a datetime, asumiendo formato como "YYYY-MM" o similar que pd.to_datetime pueda inferir.
            # Si ya es datetime (p.ej. PeriodIndex convertido a timestamp), esto no debería dañarlo.
            # Si es string "YYYY-MM", se convertirá al primer día del mes.
            x_values_plot_dt = pd.to_datetime(x_values_source, errors='coerce')
            
            # Verificar si la conversión fue exitosa y no todos son NaT
            if x_values_plot_dt is not None and not x_values_plot_dt.isna().all():
                # Ordenar por fecha para asegurar que el gráfico de línea sea correcto
                # Esto requiere que df_plot_full se ordene según estas fechas también.
                # Creamos un DataFrame temporal para ordenar y usar.
                df_temp_plot = df_plot_full.assign(x_plot_dt_col=x_values_plot_dt).sort_values(by='x_plot_dt_col')
                x_axis_for_plot = df_temp_plot['x_plot_dt_col']
            else:
                logger.warning(f"Conversión de x_values_source a datetime resultó en todos NaT o None. Usando strings originales.")
                # Fallback a strings si la conversión a datetime no es útil
                if isinstance(x_values_source.dtype, pd.PeriodDtype):
                    x_values_plot_str = x_values_source.astype(str)
                elif pd.api.types.is_datetime64_any_dtype(x_values_source):
                    x_values_plot_str = x_values_source.dt.strftime('%Y-%m')
                else:
                    x_values_plot_str = x_values_source.astype(str)
                
                # Ordenar por estos strings
                df_temp_plot = df_plot_full.assign(x_plot_str_col=x_values_plot_str).sort_values(by='x_plot_str_col')
                
                # Usar índices numéricos para el ploteo si x_values_plot_str es el eje X
                x_axis_for_plot = range(len(df_temp_plot)) # Usar rango numérico
                x_tick_labels_for_plot = df_temp_plot['x_plot_str_col'].tolist() # Etiquetas string para los ticks
                # Guardar las etiquetas para usarlas después con plt.xticks()
                _use_numeric_x_with_str_labels = True

        except Exception as e_datetime_conv:
            logger.error(f"Error crítico convirtiendo eje X a datetime en plot_monthly: {e_datetime_conv}. Usando strings.")
            df_temp_plot = df_plot_full.assign(x_plot_str_col=x_values_source.astype(str)).sort_values(by='x_plot_str_col')
            # Usar índices numéricos para el ploteo si x_values_source.astype(str) es el eje X
            x_axis_for_plot = range(len(df_temp_plot)) # Usar rango numérico
            x_tick_labels_for_plot = df_temp_plot['x_plot_str_col'].tolist() # Etiquetas string para los ticks
            _use_numeric_x_with_str_labels = True

        # Inicializar _use_numeric_x_with_str_labels si no se definió en los bloques try/except
        if '_use_numeric_x_with_str_labels' not in locals():
            _use_numeric_x_with_str_labels = False
            x_tick_labels_for_plot = [] # Inicializar para que no falle plt.xticks después

        for value_col in potential_value_cols:
            if value_col in df_temp_plot and pd.api.types.is_numeric_dtype(df_temp_plot[value_col]):
                plt.plot(x_axis_for_plot, df_temp_plot[value_col], label=str(value_col), marker='o', linestyle='-')

        plt.title(f'Volumen Mensual de Fiat{plot_title_fiat_part}{title_suffix}')
        plt.xlabel('Mes (Año-Mes)')
        plt.ylabel('Volumen Total en Fiat')
        
        if _use_numeric_x_with_str_labels:
            # Si usamos un eje X numérico (0, 1, 2...), establecemos los ticks en esas posiciones
            # y las etiquetas correspondientes a los strings de 'Año-Mes'
            plt.xticks(ticks=x_axis_for_plot, labels=x_tick_labels_for_plot, rotation=45, ha="right")
        else:
            # Si el eje X ya es datetime, la rotación se aplica directamente
            plt.xticks(rotation=45, ha="right")
            
        # Ajustar la densidad de los ticks si hay muchas etiquetas (especialmente para el caso de strings)
        if _use_numeric_x_with_str_labels and len(x_tick_labels_for_plot) > 12:
            plt.gca().xaxis.set_major_locator(mticker.MaxNLocator(nbins=12, prune='both'))
        elif not _use_numeric_x_with_str_labels and isinstance(x_axis_for_plot, pd.Series) and len(x_axis_for_plot) > 12:
             # Para ejes datetime, MaxNLocator puede ayudar a seleccionar un número razonable de ticks
             plt.gca().xaxis.set_major_locator(mticker.MaxNLocator(nbins=12, prune='both'))

        plt.legend(title='Tipo de Operación')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        fiat_file_part = f"_{current_fiat_label.lower()}_" if current_fiat is not None else "_general_"
        file_path = os.path.join(out_dir, f'monthly_fiat_volume{fiat_file_part}{file_identifier}.png')
        try:
            plt.savefig(file_path)
            logger.info(f"Gráfico de volumen mensual ({current_fiat_label}) guardado en: {file_path}")
            saved_paths.append(file_path)
        except Exception as e:
            logger.error(f"Error al guardar el gráfico {file_path}: {e}")
        plt.close()
    return saved_paths

def plot_pie(df_counts: pd.DataFrame, column_name: str, title: str, fname_prefix: str, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    if df_counts.empty or column_name not in df_counts.columns or df_counts[column_name].sum() == 0:
        logger.info(f"No hay datos para el gráfico de torta '{title}'{title_suffix}.")
        return None
    plt.figure(figsize=(10, 7))
    plt.pie(df_counts[column_name], labels=df_counts.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette('pastel', n_colors=len(df_counts.index)))
    plt.title(f'{title}{title_suffix}')
    plt.axis('equal')
    plt.tight_layout()
    file_path = os.path.join(out_dir, f'{fname_prefix}{file_identifier}.png')
    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico de torta '{title}' guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el gráfico de torta {file_path}: {e}")
        plt.close()
        return None

def plot_price_distribution(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if df_completed.empty:
        logger.info(f"No hay datos completados para graficar distribución de precios{title_suffix}.")
        return saved_paths

    price_num_col = 'Price_num'
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'
    order_type_col_internal = 'order_type'

    required_cols = [price_num_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_completed.columns]
        logger.warning(f"Faltan columnas para graficar distribución de precios ({', '.join(missing)}){title_suffix}.")
        return saved_paths

    for (asset, fiat), group_data in df_completed.groupby([asset_type_col_internal, fiat_type_col_internal]):
        fig = None
        file_name_plot = f'price_distribution_{str(asset).lower().replace(" ", "_")}_{str(fiat).lower().replace(" ", "_")}{file_identifier}.png'
        file_path = os.path.join(out_dir, file_name_plot)
        try:
            if group_data.empty or group_data[price_num_col].isna().all():
                logger.info(f"Omitiendo gráfico de distribución de precios para {asset}/{fiat} (archivo: {file_name_plot}) debido a datos vacíos o todos los precios son NaN{title_suffix}.")
                continue
            fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
            fig.suptitle(f'Distribución de Precios para {asset}/{fiat}{title_suffix}', fontsize=16)
            sns.histplot(data=group_data, x=price_num_col, hue=order_type_col_internal, multiple="stack", kde=False, ax=axes[0], palette="muted", linewidth=0.5, bins=30)
            axes[0].set_title('Histograma de Precios')
            axes[0].set_xlabel('')
            axes[0].set_ylabel('Frecuencia')
            handles, labels = axes[0].get_legend_handles_labels()
            if handles: axes[0].legend(handles=handles, labels=labels, title=order_type_col_internal)
            sns.boxplot(data=group_data, x=price_num_col, y=order_type_col_internal, hue=order_type_col_internal, legend=False, ax=axes[1], palette="muted", orient='h')
            axes[1].set_title('Boxplot de Precios')
            axes[1].set_xlabel(f'Precio de {asset} en {fiat}')
            axes[1].set_ylabel(order_type_col_internal)
            mean_price = group_data[price_num_col].mean()
            median_price = group_data[price_num_col].median()
            current_handles, current_labels = axes[0].get_legend_handles_labels()
            if pd.notna(mean_price):
                line_mean = axes[0].axvline(mean_price, color='r', linestyle='--', linewidth=1.5, label=f'Media: {mean_price:.2f}')
                if not any(label.startswith('Media:') for label in current_labels): 
                     current_handles.append(line_mean); current_labels.append(f'Media: {mean_price:.2f}')
            if pd.notna(median_price):
                line_median = axes[0].axvline(median_price, color='g', linestyle=':', linewidth=1.5, label=f'Mediana: {median_price:.2f}')
                if not any(label.startswith('Mediana:') for label in current_labels):
                     current_handles.append(line_median); current_labels.append(f'Mediana: {median_price:.2f}')
            if current_handles: axes[0].legend(handles=current_handles, labels=current_labels, title=order_type_col_internal)
            plt.tight_layout(rect=[0, 0.03, 1, 0.95])
            plt.savefig(file_path)
            saved_paths.append(file_path)
        except (Exception, KeyboardInterrupt) as e:
            logger.error(f"Failed to generate/save plot {file_path} for {asset}/{fiat}{title_suffix} due to {type(e).__name__}: {e}. Creating placeholder image.")
            if isinstance(e, KeyboardInterrupt): logger.warning(f"Plot generation for {file_path} was manually interrupted.")
            try:
                if fig is not None and plt.fignum_exists(fig.number): plt.close(fig)
                error_fig, error_ax = plt.subplots(figsize=(10, 3))
                error_text = f"Error al generar gráfico para:\\n{asset}/{fiat}{title_suffix}\\nConsulte los logs."
                error_ax.text(0.5, 0.5, error_text, ha='center', va='center', fontsize=10, color='red', wrap=True)
                error_ax.axis('off'); plt.tight_layout(); error_fig.savefig(file_path)
                if file_path not in saved_paths: saved_paths.append(file_path)
            except Exception as e_placeholder: logger.error(f"CRITICAL: Failed to create placeholder for {file_path}: {e_placeholder}")
            finally: 
                if 'error_fig' in locals() and plt.fignum_exists(error_fig.number): plt.close(error_fig)
        finally:
            if fig is not None and plt.fignum_exists(fig.number): plt.close(fig)
    return saved_paths

def plot_volume_vs_price_scatter(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if df_completed.empty: return saved_paths
    quantity_num_col = 'Quantity_num'; price_num_col = 'Price_num'; total_price_num_col = 'TotalPrice_num' 
    asset_type_col_internal = 'asset_type'; fiat_type_col_internal = 'fiat_type'; order_type_col_internal = 'order_type'
    required_cols = [quantity_num_col, price_num_col, total_price_num_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols): return saved_paths

    df_plot_base = df_completed.copy()

    for (asset_val, fiat_val), group_data_original in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_original.empty or group_data_original[[quantity_num_col, price_num_col]].isna().all().all(): continue
        
        group_data = group_data_original.copy() 

        for col_to_convert in [quantity_num_col, price_num_col, total_price_num_col]:
            if col_to_convert in group_data.columns:
                group_data[col_to_convert] = pd.to_numeric(group_data[col_to_convert], errors='coerce')

        size_data = group_data[total_price_num_col]; 
        sizes_for_plot = pd.Series([30] * len(group_data), index=group_data.index)
        if not size_data.isna().all() and not (size_data == 0).all():
            min_val_sd = size_data.min(); max_val_sd = size_data.max()
            if pd.notna(min_val_sd) and pd.notna(max_val_sd) and max_val_sd > min_val_sd:
                 sizes_norm = (size_data.fillna(0) - min_val_sd) / (max_val_sd - min_val_sd); sizes_for_plot = sizes_norm * 490 + 10
            elif pd.notna(min_val_sd): sizes_for_plot = pd.Series([50] * len(group_data), index=group_data.index)
        
        sizes_for_plot = sizes_for_plot.fillna(30).clip(lower=10, upper=500).astype('float64') 

        plt.figure(figsize=(14, 8))
        scatter_plot = sns.scatterplot(data=group_data, x=quantity_num_col, y=price_num_col, hue=order_type_col_internal, size=sizes_for_plot, sizes=(20, 500), alpha=0.7, palette="viridis", legend="auto")
        plt.title(f"""Volumen vs. Precio para {asset_val}/{fiat_val}{title_suffix}\\n(Tamaño del punto proporcional al Monto Total Fiat)""")
        plt.xlabel(f'Volumen del Activo ({asset_val})'); plt.ylabel(f'Precio en {fiat_val}')
        handles, labels = scatter_plot.get_legend_handles_labels()
        if handles:
            legend_params = {'title': f'{order_type_col_internal} / Monto'}
            if len(handles) > 5: legend_params['loc'] = 'upper left'; legend_params['bbox_to_anchor'] = (1.05, 1)
            else: legend_params['loc'] = 'best'
            scatter_plot.legend(**legend_params)
        plt.grid(True, linestyle='--', alpha=0.7)
        file_path = os.path.join(out_dir, f'volume_vs_price_scatter_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
        try:
            plt.savefig(file_path, bbox_inches='tight'); saved_paths.append(file_path); plt.close()
        except Exception as e: logger.error(f"Error al guardar el gráfico {file_path}: {e}"); plt.close()
    return saved_paths

def plot_price_over_time(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if df_completed.empty: return saved_paths
    price_num_col = 'Price_num'; match_time_local_col = 'Match_time_local'; asset_type_col_internal = 'asset_type'; fiat_type_col_internal = 'fiat_type'; order_type_col_internal = 'order_type'
    required_cols = [price_num_col, match_time_local_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols) or not pd.api.types.is_datetime64_any_dtype(df_completed[match_time_local_col]): return saved_paths
    for (asset_val, fiat_val), group_data in df_completed.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data.empty or group_data[price_num_col].isna().all(): continue
        group_data_sorted = group_data.sort_values(by=match_time_local_col); plt.figure(figsize=(15, 8))
        for order_val, order_group in group_data_sorted.groupby(order_type_col_internal):
            if order_group.empty or order_group[price_num_col].isna().all(): continue
            plt.plot(order_group[match_time_local_col], order_group[price_num_col], marker='.', linestyle='-', alpha=0.5, label=f'Precio {order_val}')
            if len(order_group) >= 7: plt.plot(order_group[match_time_local_col], order_group[price_num_col].rolling(window=7, center=True, min_periods=1).mean(), linestyle='--', label=f'Media Móvil 7P {order_val}')
            if len(order_group) >= 30: plt.plot(order_group[match_time_local_col], order_group[price_num_col].rolling(window=30, center=True, min_periods=1).mean(), linestyle=':', label=f'Media Móvil 30P {order_val}')
        plt.title(f'Evolución del Precio para {asset_val}/{fiat_val}{title_suffix}'); plt.xlabel('Fecha y Hora (Local)'); plt.ylabel(f'Precio en {fiat_val}'); plt.xticks(rotation=45, ha='right')
        plt.legend(title='Serie de Precio / Media Móvil'); plt.grid(True, linestyle='--', alpha=0.7); plt.tight_layout()
        file_path = os.path.join(out_dir, f'price_over_time_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
        try: plt.savefig(file_path); saved_paths.append(file_path); plt.close()
        except Exception as e: logger.error(f"Error al guardar el gráfico {file_path}: {e}"); plt.close()
    return saved_paths

def plot_volume_over_time(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if df_completed.empty: return saved_paths
    quantity_num_col = 'Quantity_num'; total_price_num_col = 'TotalPrice_num'; match_time_local_col = 'Match_time_local'; asset_type_col_internal = 'asset_type'; fiat_type_col_internal = 'fiat_type'
    required_cols_base = [match_time_local_col, asset_type_col_internal, fiat_type_col_internal]
    if not (quantity_num_col in df_completed.columns or total_price_num_col in df_completed.columns) or not all(col in df_completed.columns for col in required_cols_base) or not pd.api.types.is_datetime64_any_dtype(df_completed[match_time_local_col]): return saved_paths
    volume_cols_to_plot = {}
    if quantity_num_col in df_completed.columns: volume_cols_to_plot[quantity_num_col] = ('Volumen de Activo', asset_type_col_internal)
    if total_price_num_col in df_completed.columns: volume_cols_to_plot[total_price_num_col] = ('Volumen en Fiat', fiat_type_col_internal)
    for (asset_val, fiat_val), group_data in df_completed.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data.empty: continue
        group_data_sorted = group_data.sort_values(by=match_time_local_col)
        for vol_col, (vol_label_base, unit_col_name_from_map) in volume_cols_to_plot.items():
            if group_data_sorted[vol_col].isna().all() or (group_data_sorted[vol_col] == 0).all(): continue
            plt.figure(figsize=(15, 8)); label_unit = asset_val if unit_col_name_from_map == asset_type_col_internal else fiat_val
            plt.plot(group_data_sorted[match_time_local_col], group_data_sorted[vol_col], marker='.', linestyle='-', alpha=0.7, label=f'{vol_label_base} ({label_unit})')
            if len(group_data_sorted) >= 7: plt.plot(group_data_sorted[match_time_local_col], group_data_sorted[vol_col].rolling(window=7, center=True, min_periods=1).mean(), linestyle='--', label='Media Móvil 7P')
            if len(group_data_sorted) >= 30: plt.plot(group_data_sorted[match_time_local_col], group_data_sorted[vol_col].rolling(window=30, center=True, min_periods=1).mean(), linestyle=':', label='Media Móvil 30P')
            y_label = f'{vol_label_base} ({label_unit})'; plt.title(f'Evolución del {vol_label_base} para {asset_val}/{fiat_val}{title_suffix}')
            plt.xlabel('Fecha y Hora (Local)'); plt.ylabel(y_label); plt.xticks(rotation=45, ha='right'); plt.legend(title='Serie de Volumen / Media Móvil'); plt.grid(True, linestyle='--', alpha=0.7); plt.tight_layout()
            vol_type_suffix = "fiat_value" if vol_col == total_price_num_col else "asset_quantity"
            file_path = os.path.join(out_dir, f'volume_over_time_{vol_type_suffix}_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
            try: plt.savefig(file_path); saved_paths.append(file_path); plt.close()
            except Exception as e: logger.error(f"Error al guardar el gráfico {file_path}: {e}"); plt.close()
    return saved_paths

def plot_price_vs_payment_method(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if df_completed.empty: return saved_paths
    price_num_col = 'Price_num'; payment_method_col_internal = 'payment_method'; order_type_col_internal = 'order_type'; fiat_type_col_internal = 'fiat_type'; asset_type_col_internal = 'asset_type'
    required_cols_in_df = [price_num_col, payment_method_col_internal, order_type_col_internal, fiat_type_col_internal, asset_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols_in_df): return saved_paths
    df_plot_base = df_completed.copy(); df_plot_base[payment_method_col_internal] = df_plot_base[payment_method_col_internal].fillna('Desconocido')
    for (asset_val, fiat_val), group_data_asset_fiat in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_asset_fiat.empty or group_data_asset_fiat[payment_method_col_internal].nunique() == 0 or group_data_asset_fiat[price_num_col].isna().all(): continue
        payment_methods_count = group_data_asset_fiat[payment_method_col_internal].nunique(); plot_data_final = group_data_asset_fiat; effective_pm_count = payment_methods_count; top_n_methods = 15 
        if payment_methods_count > top_n_methods:
            main_methods = group_data_asset_fiat[payment_method_col_internal].value_counts().nlargest(top_n_methods).index
            plot_data_final = group_data_asset_fiat[group_data_asset_fiat[payment_method_col_internal].isin(main_methods)]; effective_pm_count = len(main_methods)
        if plot_data_final.empty: continue
        plt.figure(figsize=(max(12, effective_pm_count * 1.1), 9)); sns.boxplot(x=payment_method_col_internal, y=price_num_col, hue=order_type_col_internal, data=plot_data_final, palette="Set3")
        plt.title(f'Precio de {asset_val} vs. Método de Pago en {fiat_val}{title_suffix}'); plt.xlabel('Método de Pago') 
        plt.ylabel(f'Precio de {asset_val} en {fiat_val}'); plt.xticks(rotation=45, ha='right'); plt.legend(title=order_type_col_internal); plt.grid(axis='y', linestyle='--', alpha=0.7); plt.tight_layout()
        file_path = os.path.join(out_dir, f'price_vs_payment_method_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
        try: plt.savefig(file_path); saved_paths.append(file_path); plt.close()
        except Exception as e: logger.error(f"Error al guardar el gráfico {file_path}: {e}"); plt.close()
    return saved_paths

def plot_activity_heatmap(df_all_statuses: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    logger.debug(f"plot_activity_heatmap_v2_debug: Recibido df_all_statuses con {df_all_statuses.shape[0]} filas y {df_all_statuses.shape[1]} columnas.")
    if df_all_statuses.empty:
        logger.warning(f"plot_activity_heatmap_v2_debug: df_all_statuses está vacío. No se generará heatmap.{title_suffix}")
        return None
        
    match_time_local_col = 'Match_time_local'
    order_number_col_internal = 'order_number' 
    hour_local_col_internal = 'hour_local' 
    required_cols = [match_time_local_col, order_number_col_internal, hour_local_col_internal]

    df_plot = df_all_statuses.copy() # Trabajar con una copia

    # Asegurar que Match_time_local sea datetime de Pandas
    if match_time_local_col in df_plot.columns:
        if not pd.api.types.is_datetime64_any_dtype(df_plot[match_time_local_col]):
            logger.debug(f"plot_activity_heatmap_v2_debug: Columna '{match_time_local_col}' no es datetime64 nativo de Pandas. Tipo actual: {df_plot[match_time_local_col].dtype}. Intentando conversión...")
            try:
                df_plot[match_time_local_col] = pd.to_datetime(df_plot[match_time_local_col])
                logger.debug(f"plot_activity_heatmap_v2_debug: Columna '{match_time_local_col}' convertida a {df_plot[match_time_local_col].dtype}.")
            except Exception as e_conv:
                logger.warning(f"plot_activity_heatmap_v2_debug: Falló la conversión de '{match_time_local_col}' a datetime de Pandas: {e_conv}. No se generará heatmap.{title_suffix}")
                return None
    else:
        logger.warning(f"plot_activity_heatmap_v2_debug: Columna requerida '{match_time_local_col}' no encontrada. No se generará heatmap.{title_suffix}")
        return None

    missing_cols = [col for col in required_cols if col not in df_plot.columns]
    if missing_cols:
        # Este cheque es un poco redundante ahora que verificamos Match_time_local arriba, pero lo mantenemos por si acaso para otras columnas
        logger.warning(f"plot_activity_heatmap_v2_debug: Faltan columnas requeridas (después de conversión de fecha): {missing_cols}. No se generará heatmap.{title_suffix}")
        return None

    # Esta comprobación ahora debería pasar si la conversión fue exitosa
    if not pd.api.types.is_datetime64_any_dtype(df_plot[match_time_local_col]):
        logger.warning(f"plot_activity_heatmap_v2_debug: Columna '{match_time_local_col}' aún no es de tipo datetime después del intento de conversión. No se generará heatmap.{title_suffix}")
        return None
        
    # df_plot = df_all_statuses.copy() # Movido arriba
    logger.debug(f"plot_activity_heatmap_v2_debug: Columnas en df_plot: {df_plot.columns.tolist()}")

    if 'day_of_week' not in df_plot.columns or df_plot['day_of_week'].isna().all():
        if pd.api.types.is_datetime64_any_dtype(df_plot[match_time_local_col]):
            df_plot['day_of_week'] = df_plot[match_time_local_col].dt.day_name()
            logger.debug(f"plot_activity_heatmap_v2_debug: Columna 'day_of_week' creada.")
        else:
            logger.warning(f"plot_activity_heatmap_v2_debug: '{match_time_local_col}' no es datetime, no se pudo crear 'day_of_week'. No se generará heatmap.{title_suffix}")
            return None
            
    days_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    if 'day_of_week' in df_plot.columns and not df_plot['day_of_week'].isna().all():
        df_plot['day_of_week'] = pd.Categorical(df_plot['day_of_week'], categories=days_ordered, ordered=True)
        logger.debug(f"plot_activity_heatmap_v2_debug: Columna 'day_of_week' convertida a categórica ordenada.")
    else:
        logger.warning(f"plot_activity_heatmap_v2_debug: Columna 'day_of_week' no es válida o contiene solo NaNs. No se generará heatmap.{title_suffix}")
        return None
        
    cols_for_pivot = [order_number_col_internal, 'day_of_week', hour_local_col_internal]
    if df_plot[cols_for_pivot].isna().any().any():
        rows_before_dropna = len(df_plot)
        df_plot.dropna(subset=cols_for_pivot, inplace=True)
        logger.debug(f"plot_activity_heatmap_v2_debug: Eliminadas {rows_before_dropna - len(df_plot)} filas con NaNs en cols_for_pivot. Filas restantes: {len(df_plot)}.")

    if df_plot.empty:
        logger.warning(f"plot_activity_heatmap_v2_debug: df_plot vacío después de dropna. No se generará heatmap.{title_suffix}")
        return None

    logger.debug(f"plot_activity_heatmap_v2_debug: Intentando pivotar con index='day_of_week', columns='{hour_local_col_internal}', values='{order_number_col_internal}'.")
    try:
        activity_matrix = df_plot.pivot_table(values=order_number_col_internal, index='day_of_week', columns=hour_local_col_internal, aggfunc='count', fill_value=0, observed=False)
    except Exception as e_pivot:
        logger.error(f"plot_activity_heatmap_v2_debug: Error durante pivot_table: {e_pivot}. Datos head:\n{df_plot.head()}")
        return None

    logger.debug(f"plot_activity_heatmap_v2_debug: activity_matrix creada con forma {activity_matrix.shape}. Columnas: {activity_matrix.columns.tolist()}")

    for hour in range(24):
        if hour not in activity_matrix.columns: activity_matrix[hour] = 0
    activity_matrix = activity_matrix.reindex(columns=sorted(activity_matrix.columns)); activity_matrix = activity_matrix.reindex(index=days_ordered, fill_value=0)
    logger.debug(f"plot_activity_heatmap_v2_debug: activity_matrix reindexada. Forma final: {activity_matrix.shape}. Suma total: {activity_matrix.sum().sum()}")

    if activity_matrix.empty or activity_matrix.sum().sum() == 0:
        logger.warning(f"plot_activity_heatmap_v2_debug: activity_matrix vacía o todas las sumas son cero después de reindexar. No se generará heatmap.{title_suffix}")
        return None
    
    # Asegurar que la matriz de actividad sea de tipo numérico antes de pasarla al heatmap
    try:
        activity_matrix = activity_matrix.astype(int)
        logger.debug(f"plot_activity_heatmap_v2_debug: activity_matrix convertida a tipo int. Dtypes ahora: {activity_matrix.dtypes.unique()}")
    except Exception as e_astype:
        logger.error(f"plot_activity_heatmap_v2_debug: Error al convertir activity_matrix a int: {e_astype}. No se generará heatmap.{title_suffix}")
        return None
        
    plt.figure(figsize=(18, 8)); sns.heatmap(activity_matrix, annot=True, fmt="d", cmap="YlGnBu", linewidths=.5, cbar_kws={'label': 'Cantidad de Operaciones'})
    plt.title(f'Heatmap de Actividad de Operaciones por Hora y Día{title_suffix}'); plt.xlabel('Hora del Día (Local)'); plt.ylabel('Día de la Semana'); plt.xticks(rotation=0); plt.yticks(rotation=0); plt.tight_layout()
    file_path = os.path.join(out_dir, f'activity_heatmap{file_identifier}.png')
    try: 
        plt.savefig(file_path); plt.close(); 
        logger.info(f"plot_activity_heatmap_v2_debug: Heatmap guardado en: {file_path}")
        return file_path
    except Exception as e: 
        logger.error(f"plot_activity_heatmap_v2_debug: Error al guardar el heatmap {file_path}: {e}"); plt.close(); 
        return None

def plot_fees_analysis(fees_stats_df: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    if fees_stats_df.empty:
        logger.info(f"No hay datos de comisiones para graficar{title_suffix}.")
        return None

    plot_col = 'total_fees_collected' 
    if plot_col not in fees_stats_df.columns:
        logger.warning(f"Columna '{plot_col}' no encontrada en fees_stats_df para graficar{title_suffix}.")
        return None
        
    df_plot = fees_stats_df[[plot_col]].copy() 
    x_label_text = fees_stats_df.index.name if fees_stats_df.index.name is not None else "Tipo de Activo"

    if df_plot.empty or df_plot[plot_col].sum() == 0:
        logger.info(f"No hay comisiones significativas (>0) en '{plot_col}' para graficar{title_suffix}.")
        return None

    df_plot.sort_values(by=plot_col, ascending=False).plot(kind='bar', figsize=(12, 7), width=0.8, colormap='viridis', legend=None)
    
    plt.title(f'Total de Comisiones Recaudadas por {x_label_text}{title_suffix}')
    plt.xlabel(x_label_text)
    plt.ylabel('Monto Total de Comisión')
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    
    file_path = os.path.join(out_dir, f'fees_total_by_asset{file_identifier}.png')
    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico de análisis de comisiones por activo guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el gráfico de comisiones {file_path}: {e}")
        plt.close()
        return None 

# DONE: 2.1 Sankey Fiat -> Activo
def plot_sankey_fiat_asset(df_data: pl.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    logger.info(f"Iniciando generación de gráfico Sankey Fiat -> Activo{title_suffix}.")
    
    fiat_col = 'fiat_type'; asset_col = 'asset_type'; value_col = 'TotalPrice_num'
    df_agg = df_data.group_by([fiat_col, asset_col]).agg(pl.sum(value_col).alias(value_col))
    if df_agg.is_empty():
        logger.info(f"No hay datos agregados para generar el gráfico Sankey{title_suffix}.")
        return None
    
    sankey_agg_pd = df_agg.to_pandas() 

    # DONE: Corregir pd.unique para evitar FutureWarning
    # Combinar las dos listas de nodos (origen y destino)
    combined_node_list = sankey_agg_pd[fiat_col].tolist() + sankey_agg_pd[asset_col].tolist()
    # Convertir la lista combinada a una Serie de Pandas antes de pd.unique()
    all_nodes = pd.unique(pd.Series(combined_node_list)).tolist()
    node_map = {name: i for i, name in enumerate(all_nodes)}

    # source_indices = sankey_agg_pd[fiat_col].map_elements(lambda x: node_map[x], return_dtype=pl.Int64).to_list()
    source_indices = sankey_agg_pd[fiat_col].map(node_map).tolist()
    target_indices = sankey_agg_pd[asset_col].map(node_map).tolist()
    values = sankey_agg_pd[value_col].tolist()

    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
            # TODO: Añadir colores a los nodos si es necesario
            # color = ["blue"] * len(all_nodes) # Ejemplo
        ),
        link=dict(
            source=source_indices,
            target=target_indices,
            value=values,
            # TODO: Añadir colores a los enlaces si es necesario
            # color = ["rgba(0,0,255,0.2)"]*len(source_indices) # Ejemplo
        ))])

    title_text = f'Diagrama Sankey: Flujo Fiat -> Activo (Volumen en Fiat){title_suffix}'
    fig.update_layout(title_text=title_text, font_size=10)
    
    file_path = os.path.join(out_dir, f'sankey_fiat_to_asset{file_identifier}.html') # Guardar como HTML para interactividad
    try:
        fig.write_html(file_path)
        logger.info(f"Gráfico Sankey guardado en: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el gráfico Sankey {file_path}: {e}")
        return None 

# DONE: 2.2 Heatmap Hora x Día
def plot_heatmap_hour_day(df_pd: pd.DataFrame, out_dir: str, value_col_name: str = 'TotalPrice_num', agg_func: str = 'sum', title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    if df_pd.empty:
        logger.info(f"No hay datos para el heatmap hora/día ({value_col_name} {agg_func}){title_suffix}.")
        return None

    logger.info(f"Generando heatmap hora/día para {value_col_name} (agg: {agg_func}){title_suffix}...")

    if 'Match_time_local' not in df_pd.columns:
        logger.warning(f"Columna 'Match_time_local' no encontrada en el DataFrame para heatmap. No se puede generar.{title_suffix}")
        return None
        
    df_pd_copy = df_pd.copy() # Crear una copia para evitar SettingWithCopyWarning

    # Asegurarse que Match_time_local sea datetime y manejar timezone
    if not pd.api.types.is_datetime64_any_dtype(df_pd_copy['Match_time_local']):
        try:
            df_pd_copy['Match_time_local'] = pd.to_datetime(df_pd_copy['Match_time_local'], errors='coerce')
        except Exception as e:
            logger.error(f"Error al convertir 'Match_time_local' a datetime: {e}. No se puede generar heatmap.{title_suffix}")
            return None

    if df_pd_copy['Match_time_local'].isna().all():
        logger.warning(f"'Match_time_local' contiene solo NaT después de la conversión. No se puede generar heatmap.{title_suffix}")
        return None

    # Si la columna tiene timezone, convertirla a naive (UTC o simplemente remover tz)
    # Esto es crucial para evitar errores con algunas operaciones de .dt o con librerías como PyArrow si tzdata no está bien configurado.
    if hasattr(df_pd_copy['Match_time_local'].dt, 'tz') and df_pd_copy['Match_time_local'].dt.tz is not None:
        try:
            logger.debug(f"Convirtiendo 'Match_time_local' a timezone-naive desde {df_pd_copy['Match_time_local'].dt.tz} para heatmap.")
            df_pd_copy['Match_time_local'] = df_pd_copy['Match_time_local'].dt.tz_convert(None) # Convertir a UTC y hacerlo naive
            # Alternativamente, si ya está en la hora local correcta conceptualmente:
            # df_pd_copy['Match_time_local'] = df_pd_copy['Match_time_local'].dt.tz_localize(None)
        except Exception as e_tz_convert:
            logger.error(f"Error al convertir 'Match_time_local' a timezone-naive: {e_tz_convert}. Usando datos como están si es posible.")
            # Podríamos optar por no continuar si la conversión de TZ es crítica y falla.
            # Por ahora, se intentará continuar, pero podría fallar más adelante en .dt.hour/.dt.dayofweek

    try:
        df_pd_copy['hour'] = df_pd_copy['Match_time_local'].dt.hour
        # Antes era .weekday, ahora .dayofweek (Lunes=0, Domingo=6) para consistencia y facilidad de mapeo.
        df_pd_copy['weekday'] = df_pd_copy['Match_time_local'].dt.dayofweek 
    except Exception as e_dt_extract:
        logger.error(f"Error extrayendo componentes de hora/día de 'Match_time_local': {e_dt_extract}. Tipo de dato actual: {df_pd_copy['Match_time_local'].dtype}. No se puede generar heatmap.")
        return None

    # Extraer día de la semana (como número 0-6) y hora del día
    df_pd_copy['day_of_week_num'] = df_pd_copy['Match_time_local'].dt.dayofweek # Lunes=0, Domingo=6
    df_pd_copy['day_of_week_label'] = df_pd_copy['day_of_week_num'].map({0: 'Monday', 1: 'Tuesday', 2: 'Wednesday', 3: 'Thursday', 4: 'Friday', 5: 'Saturday', 6: 'Sunday'})
    
    # Orden de los días para el heatmap
    days_ordered_spanish = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    # Validar la columna de valor y la función de agregación
    if value_col_name not in df_pd_copy.columns:
        logger.warning(f"Columna de valor '{value_col_name}' no encontrada para heatmap.{title_suffix}")
        return None

    final_agg_func: Union[str, callable]
    if agg_func == 'count':
        final_agg_func = 'size' 
        # Si es 'count', no importa mucho 'value_col_name' para pivot_table con 'size', 
        # pero debe existir. Usaremos la primera columna si order_number no está.
        if value_col_name == 'order_number' and value_col_name not in df_pd_copy.columns:
            if df_pd_copy.columns.empty: return None # No hay columnas
            value_col_name = df_pd_copy.columns[0] # Usar cualquier columna existente
            logger.info(f"Columna '{value_col_name}' no encontrada para conteo, usando '{df_pd_copy.columns[0]}' como fallback.")

    elif agg_func == 'sum':
        final_agg_func = 'sum'
        # Asegurar que la columna de valor sea numérica para la suma
        if not pd.api.types.is_numeric_dtype(df_pd_copy[value_col_name]):
            logger.warning(f"Columna de valor '{value_col_name}' no es numérica para agg_func='sum' en heatmap. Intentando convertir...")
            df_pd_copy[value_col_name] = pd.to_numeric(df_pd_copy[value_col_name], errors='coerce')
            df_pd_copy = df_pd_copy.dropna(subset=[value_col_name]) # Quitar filas donde la conversión falló
            if df_pd_copy.empty:
                logger.warning(f"Columna de valor '{value_col_name}' quedó vacía después de intentar convertir a numérico.{title_suffix}")
                return None
    else:
        logger.error(f"Función de agregación no soportada '{agg_func}' para heatmap.")
        return None

    try:
        pivot_table = df_pd_copy.pivot_table(
            values=value_col_name, 
            index='hour', 
            columns='day_of_week_label', # Usar las etiquetas en español
            aggfunc=final_agg_func,
            fill_value=0
        )
    except Exception as e_pivot:
        logger.error(f"Error al crear pivot_table para heatmap ({value_col_name} {agg_func}): {e_pivot}")
        return None
    
    # Reordenar columnas según days_ordered_spanish y rellenar días faltantes con 0
    # Asegurar que todas las horas (0-23) estén presentes como índice también
    pivot_table_ordered = pivot_table.reindex(columns=days_ordered_spanish, index=range(24)).fillna(0)
    
    # Si la agregación fue 'size' (conteo), convertir a int para el formato del heatmap
    if final_agg_func == 'size':
        pivot_table_ordered = pivot_table_ordered.astype(int)
    elif final_agg_func == 'sum': # Asegurar que para la suma, la tabla sea float
        try:
            pivot_table_ordered = pivot_table_ordered.astype(float)
        except ValueError as e_astype_float:
            logger.error(f"Error convirtiendo pivot_table_ordered a float para heatmap (sum): {e_astype_float}. Dtypes actuales:\n{pivot_table_ordered.dtypes}")
            # Opcionalmente, podrías intentar convertir columna por columna o manejar de otra forma
            return None # No se puede generar el heatmap si la conversión falla

    if pivot_table_ordered.empty:
        logger.info(f"Pivot table para heatmap resultó vacía ({value_col_name} {agg_func}).{title_suffix}")
        return None

    plt.figure(figsize=(12, 8))
    
    fmt_str = ".1f" if final_agg_func == 'sum' else "d" # "d" para enteros (conteo)

    sns.heatmap(pivot_table_ordered, cmap="viridis", linewidths=.5, annot=False, fmt=fmt_str, cbar_kws={'label': f'{agg_func.capitalize()} de {value_col_name}'})
    plt.title(f'Heatmap de Actividad: Hora del Día vs. Día de la Semana ({agg_func.capitalize()} de {value_col_name}){title_suffix}')
    plt.xlabel('Día de la Semana')
    plt.ylabel('Hora del Día (0-23)')
    plt.yticks(rotation=0) 
    plt.xticks(rotation=0) 

    # Guardar la figura
    clean_val_col_name = utils.sanitize_filename_component(value_col_name)
    clean_agg_func = utils.sanitize_filename_component(agg_func)
    file_path = os.path.join(out_dir, f'heatmap_hour_day_{clean_val_col_name}_{clean_agg_func}{file_identifier}.png')
    
    try:
        plt.savefig(file_path)
        logger.info(f"Heatmap guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el heatmap {file_path}: {e}")
        plt.close()
        return None

# DONE: 2.3 Violín Precio vs. Método de pago
def plot_violin_price_vs_payment_method(df_data: pl.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    logger.info(f"Iniciando generación de gráficos de Violín: Precio vs Método de Pago{title_suffix}.")

    price_col = 'Price_num'
    payment_method_col = 'payment_method'
    asset_col = 'asset_type' # Para generar un gráfico por cada tipo de activo
    fiat_col = 'fiat_type'   # Y por cada fiat

    required_cols = [price_col, payment_method_col, asset_col, fiat_col]
    if not all(col in df_data.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_data.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para gráfico Violín Precio vs Método Pago{title_suffix}. No se generará.")
        return saved_paths

    # Filtrar datos donde el precio o método de pago son nulos
    df_violin_base = df_data.filter(
        pl.col(price_col).is_not_null() & pl.col(payment_method_col).is_not_null() &
        pl.col(asset_col).is_not_null() & pl.col(fiat_col).is_not_null()
    )

    if df_violin_base.is_empty():
        logger.info(f"No hay datos válidos para gráfico Violín Precio vs Método de Pago{title_suffix}.")
        return saved_paths

    # Convertir a Pandas para Seaborn
    df_violin_pd = df_violin_base.select(required_cols).to_pandas(use_pyarrow_extension_array=True)

    # Agrupar por Asset y Fiat para generar gráficos separados
    for (current_asset, current_fiat), group_df in df_violin_pd.groupby([asset_col, fiat_col]):
        if group_df.empty or group_df[payment_method_col].nunique() < 1:
            logger.info(f"Omitiendo gráfico violín para {current_asset}/{current_fiat} (datos insuficientes o sin métodos de pago).{title_suffix}")
            continue

        # Limitar el número de métodos de pago a mostrar para evitar gráficos sobrecargados
        # Por ejemplo, los Top N métodos por ocurrencia
        top_n_methods = 10 
        common_methods = group_df[payment_method_col].value_counts().nlargest(top_n_methods).index
        df_plot = group_df[group_df[payment_method_col].isin(common_methods)]

        if df_plot.empty:
            logger.info(f"Omitiendo gráfico violín para {current_asset}/{current_fiat} (sin datos tras filtrar por Top N métodos).{title_suffix}")
            continue

        plt.figure(figsize=(15, 8))
        order = sorted(df_plot[payment_method_col].unique()) # Ordenar métodos de pago alfabéticamente
        
        sns.violinplot(
            data=df_plot, 
            x='payment_method', 
            y='Price_num', 
            hue='payment_method',
            palette="muted", 
            order=order,
            cut=0,
            inner="quartile",
            legend=False
        )
        # cut=0 evita que los violines se extiendan más allá del rango de los datos
        # inner="quartile" muestra los cuartiles dentro del violín

        plot_title = f'Distribución de Precios ({current_asset}/{current_fiat}) por Método de Pago (Top {top_n_methods}){title_suffix}'
        plt.title(plot_title)
        plt.xlabel('Método de Pago')
        plt.ylabel(f'Precio de {current_asset} en {current_fiat}')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()

        file_name_part = f"violin_price_payment_{str(current_asset).lower()}_{str(current_fiat).lower()}{file_identifier}.png"
        file_path = os.path.join(out_dir, file_name_part)
        try:
            plt.savefig(file_path)
            logger.info(f"Gráfico Violín ({current_asset}/{current_fiat}) guardado en: {file_path}")
            saved_paths.append(file_path)
            plt.close()
        except Exception as e:
            logger.error(f"Error al guardar Gráfico Violín ({current_asset}/{current_fiat}) {file_path}: {e}")
            plt.close()
            
    return saved_paths 

# DONE: 2.4 Línea YoY alineada por mes
def plot_yoy_monthly_comparison(df_data: pl.DataFrame, out_dir: str, value_col: str, agg_func: str = 'sum', title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    logger.info(f"Iniciando generación de gráfico YoY mensual ({value_col}, agg: {agg_func}){title_suffix}.")

    time_col = 'Match_time_local'
    asset_col = 'asset_type' # Graficar por cada activo por separado
    fiat_col = 'fiat_type'   # Y por cada fiat

    required_cols_plot = [time_col, value_col, asset_col, fiat_col]
    if not all(col in df_data.columns for col in required_cols_plot):
        missing = [col for col in required_cols_plot if col not in df_data.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para gráfico YoY mensual{title_suffix}. No se generará.")
        return saved_paths

    df_plot_base = df_data.filter(pl.col(time_col).is_not_null() & pl.col(value_col).is_not_null())
    if df_plot_base.is_empty():
        logger.info(f"No hay datos válidos para gráfico YoY mensual tras filtrar nulos{title_suffix}.")
        return saved_paths

    df_yoy = df_plot_base.select([
        pl.col(time_col).dt.year().alias('year'),
        pl.col(time_col).dt.month().alias('month'),
        pl.col(asset_col),
        pl.col(fiat_col),
        pl.col(value_col)
    ])

    # Convertir a Pandas para pivotar y graficar
    df_yoy_pd = df_yoy.to_pandas(use_pyarrow_extension_array=True)

    # Un gráfico por cada combinación Asset/Fiat
    for (current_asset, current_fiat), group_df_asset_fiat in df_yoy_pd.groupby([asset_col, fiat_col]):
        if group_df_asset_fiat.empty:
            continue

        try:
            pivot_yoy = group_df_asset_fiat.pivot_table(
                index='month',
                columns='year',
                values=value_col,
                aggfunc=agg_func,
                fill_value=0
            )
        except Exception as e_pivot_yoy:
            logger.error(f"Error al pivotar datos para YoY ({current_asset}/{current_fiat}): {e_pivot_yoy}")
            continue
            
        if pivot_yoy.empty:
            logger.info(f"Tabla pivote YoY vacía para {current_asset}/{current_fiat}{title_suffix}.")
            continue
        
        # Asegurar que todos los meses (1-12) estén presentes
        pivot_yoy = pivot_yoy.reindex(index=range(1, 13), fill_value=0)
        month_map = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun', 
                     7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
        pivot_yoy.index = pivot_yoy.index.map(month_map)

        if pivot_yoy.columns.empty: # No hay años para comparar
            logger.info(f"No hay suficientes años para comparación YoY para {current_asset}/{current_fiat}{title_suffix}.")
            continue

        plt.figure(figsize=(14, 7))
        
        # Usar un eje X numérico (0 a N-1) para el trazado
        x_numeric_axis = range(len(pivot_yoy.index))
        month_labels = pivot_yoy.index.tolist()

        for year_data in pivot_yoy.columns:
            # Usar x_numeric_axis para el trazado
            plt.plot(x_numeric_axis, pivot_yoy[year_data].values, marker='o', linestyle='-', label=str(year_data))
        
        agg_label = agg_func.capitalize()
        plt.title(f'Comparación Mensual YoY de {agg_label} de {value_col} ({current_asset}/{current_fiat}){title_suffix}')
        plt.xlabel('Mes')
        plt.ylabel(f'{agg_label} de {value_col}')
        
        # Establecer los ticks en las posiciones numéricas y usar los nombres de los meses como etiquetas
        plt.xticks(ticks=x_numeric_axis, labels=month_labels, rotation=45, ha="right")
        
        # Ajustar la densidad de los ticks si hay muchas etiquetas (generalmente 12 meses, pero por si acaso)
        if len(month_labels) > 12: # Aunque normalmente son 12 meses
            plt.gca().xaxis.set_major_locator(mticker.MaxNLocator(nbins=12, prune='both', integer=True))
        
        plt.legend(title='Año')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        file_name_part = f"yoy_monthly_{value_col}_{agg_func}_{str(current_asset).lower()}_{str(current_fiat).lower()}{file_identifier}.png"
        file_path = os.path.join(out_dir, file_name_part)
        try:
            plt.savefig(file_path)
            logger.info(f"Gráfico YoY ({current_asset}/{current_fiat}, {value_col}) guardado en: {file_path}")
            saved_paths.append(file_path)
            plt.close()
        except Exception as e:
            logger.error(f"Error al guardar gráfico YoY ({current_asset}/{current_fiat}, {value_col}) {file_path}: {e}")
            plt.close()
            
    return saved_paths 

# DONE: 2.5 Scatter animado precio/volumen
def plot_animated_scatter_price_volume(df_data: pl.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    logger.info(f"Iniciando generación de Scatter animado Precio/Volumen{title_suffix}.")

    price_col = 'Price_num'
    qty_col = 'Quantity_num'
    time_col = 'Match_time_local' # Para el frame de animación
    asset_col = 'asset_type'   # Para color/símbolo
    fiat_col = 'fiat_type'     # Para facet_col si se desea, o para título
    total_price_col = 'TotalPrice_num' # Para el tamaño del marcador

    required_cols_scatter = [price_col, qty_col, time_col, asset_col, fiat_col, total_price_col]
    if not all(col in df_data.columns for col in required_cols_scatter):
        missing = [col for col in required_cols_scatter if col not in df_data.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para Scatter animado{title_suffix}. No se generará.")
        return None

    df_scatter = df_data.filter(
        pl.col(price_col).is_not_null() & pl.col(qty_col).is_not_null() & 
        pl.col(time_col).is_not_null() & pl.col(asset_col).is_not_null() &
        pl.col(fiat_col).is_not_null() & pl.col(total_price_col).is_not_null()
    )

    if df_scatter.is_empty():
        logger.info(f"No hay datos válidos para Scatter animado tras filtrar nulos{title_suffix}.")
        return None

    # Convertir a Pandas para Plotly Express
    # Convertir la columna de tiempo a string para que Plotly la ordene correctamente como animación discreta
    # o asegurarse de que sea un tipo datetime que Plotly pueda manejar.
    # Usar Date para la animación (frame diario)
    df_scatter_pd = df_scatter.with_columns(
        pl.col(time_col).dt.date().cast(pl.Utf8).alias('animation_frame_date')
    ).to_pandas(use_pyarrow_extension_array=True)

    if df_scatter_pd.empty:
        logger.info(f"DataFrame Pandas vacío para Scatter animado{title_suffix}.")
        return None

    # Limitar el número de puntos para evitar archivos HTML muy grandes y lentos
    # Podríamos tomar una muestra o solo los datos más recientes si son demasiados
    max_points_for_animation = 2000 # Ajustable
    if len(df_scatter_pd) > max_points_for_animation:
        logger.warning(f"Demasiados puntos ({len(df_scatter_pd)}) para scatter animado. Se tomará una muestra de {max_points_for_animation} puntos.{title_suffix}")
        df_scatter_pd = df_scatter_pd.sample(n=max_points_for_animation, random_state=42)
    
    df_scatter_pd = df_scatter_pd.sort_values(by='animation_frame_date') # Importante para la animación

    try:
        fig = px.scatter(
            df_scatter_pd,
            x=price_col,
            y=qty_col,
            animation_frame='animation_frame_date',
            animation_group=asset_col, # Para que los puntos de un mismo asset se conecten/identifiquen a través de frames
            color=asset_col,
            size=total_price_col, # El tamaño del marcador representa el valor total de la operación
            hover_name=asset_col,
            log_x=False, # Podría ser True si el rango de precios es muy amplio
            log_y=False, # Podría ser True si el rango de cantidades es muy amplio
            facet_col=fiat_col, # Un gráfico por cada Fiat
            facet_col_wrap=2,   # Número de facetas por fila
            size_max=30,
            labels={price_col: "Precio", qty_col: "Cantidad", asset_col: "Activo", total_price_col: "Valor Total Fiat"}
        )

        title_text = f'Scatter Animado: Precio vs. Cantidad por Día{title_suffix}'
        fig.update_layout(
            title_text=title_text,
            xaxis_title="Precio",
            yaxis_title="Cantidad",
            legend_title_text='Activo'
        )
        # Mejorar la apariencia de la animación y los sliders
        fig.layout.updatemenus[0].buttons[0].args[1]['frame']['duration'] = 500 # Duración de cada frame en ms
        fig.layout.updatemenus[0].buttons[0].args[1]['transition']['duration'] = 100 # Duración de la transición

    except Exception as e_px_scatter:
        logger.error(f"Error al generar Scatter animado con Plotly Express: {e_px_scatter}")
        return None

    file_path = os.path.join(out_dir, f'scatter_animated_price_qty{file_identifier}.html')
    try:
        fig.write_html(file_path)
        logger.info(f"Scatter animado guardado en: {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar Scatter animado {file_path}: {e}")
        return None

def plot_volume_vs_price_scatter(df_completed: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if df_completed.empty: return saved_paths
    quantity_num_col = 'Quantity_num'; price_num_col = 'Price_num'; total_price_num_col = 'TotalPrice_num' 
    asset_type_col_internal = 'asset_type'; fiat_type_col_internal = 'fiat_type'; order_type_col_internal = 'order_type'
    required_cols = [quantity_num_col, price_num_col, total_price_num_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols): return saved_paths

    df_plot_base = df_completed.copy()

    for (asset_val, fiat_val), group_data_original in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_original.empty or group_data_original[[quantity_num_col, price_num_col]].isna().all().all(): continue
        
        group_data = group_data_original.copy() 

        for col_to_convert in [quantity_num_col, price_num_col, total_price_num_col]:
            if col_to_convert in group_data.columns:
                group_data[col_to_convert] = pd.to_numeric(group_data[col_to_convert], errors='coerce')

        size_data = group_data[total_price_num_col]; 
        sizes_for_plot = pd.Series([30] * len(group_data), index=group_data.index)
        if not size_data.isna().all() and not (size_data == 0).all():
            min_val_sd = size_data.min(); max_val_sd = size_data.max()
            if pd.notna(min_val_sd) and pd.notna(max_val_sd) and max_val_sd > min_val_sd:
                 sizes_norm = (size_data.fillna(0) - min_val_sd) / (max_val_sd - min_val_sd); sizes_for_plot = sizes_norm * 490 + 10
            elif pd.notna(min_val_sd): sizes_for_plot = pd.Series([50] * len(group_data), index=group_data.index)
        
        sizes_for_plot = sizes_for_plot.fillna(30).clip(lower=10, upper=500).astype('float64') 

        plt.figure(figsize=(14, 8))
        scatter_plot = sns.scatterplot(data=group_data, x=quantity_num_col, y=price_num_col, hue=order_type_col_internal, size=sizes_for_plot, sizes=(20, 500), alpha=0.7, palette="viridis", legend="auto")
        plt.title(f"""Volumen vs. Precio para {asset_val}/{fiat_val}{title_suffix}\\n(Tamaño del punto proporcional al Monto Total Fiat)""")
        plt.xlabel(f'Volumen del Activo ({asset_val})'); plt.ylabel(f'Precio en {fiat_val}')
        handles, labels = scatter_plot.get_legend_handles_labels()
        if handles:
            legend_params = {'title': f'{order_type_col_internal} / Monto'}
            if len(handles) > 5: legend_params['loc'] = 'upper left'; legend_params['bbox_to_anchor'] = (1.05, 1)
            else: legend_params['loc'] = 'best'
            scatter_plot.legend(**legend_params)
        plt.grid(True, linestyle='--', alpha=0.7)
        file_path = os.path.join(out_dir, f'volume_vs_price_scatter_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png')
        try:
            plt.savefig(file_path, bbox_inches='tight'); saved_paths.append(file_path); plt.close()
        except Exception as e: logger.error(f"Error al guardar el gráfico {file_path}: {e}"); plt.close()
    return saved_paths
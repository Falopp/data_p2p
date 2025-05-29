import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure

logger = logging.getLogger(__name__)
sns.set_theme(style="whitegrid")

# --- Funciones de Visualización ---

def plot_hourly(hourly_counts: pd.Series, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> str | None:
    if hourly_counts.empty:
        logger.info(f"No hay datos para el gráfico horario{title_suffix}.")
        return None
    hourly_counts_reindexed = hourly_counts.reindex(range(24), fill_value=0)
    plt.figure(figsize=(12, 6))

    # Asegurar que los datos para barplot sean explícitamente numéricos
    x_data = pd.to_numeric(hourly_counts_reindexed.index)
    y_data = pd.to_numeric(hourly_counts_reindexed.values)

    sns.barplot(x=x_data, y=y_data, color="skyblue")
    plt.title(f'Operaciones por Hora del Día (Local){title_suffix}')
    plt.xlabel('Hora del Día (0-23)')
    plt.ylabel('Cantidad de Operaciones')
    plt.xticks(range(0, 24, 1))
    plt.grid(axis='y', linestyle='--', alpha=0.7)
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
             df_plot_full = monthly_fiat[monthly_fiat.index.get_level_values(fiat_type_col_internal) == current_fiat]
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
        
        if isinstance(x_values_source.dtype, pd.PeriodDtype):
            x_values_plot = x_values_source.astype(str)
        elif pd.api.types.is_datetime64_any_dtype(x_values_source):
            x_values_plot = x_values_source.dt.strftime('%Y-%m')
        elif hasattr(x_values_source, 'dtype') and pd.api.types.is_string_dtype(x_values_source.dtype):
            x_values_plot = x_values_source 
        else:
            try:
                x_values_plot = x_values_source.astype(str)
            except Exception as e_conv:
                logger.warning(f"No se pudo convertir x_values_source a string en plot_monthly: {e_conv}. Usando como está.")
                x_values_plot = x_values_source

        for value_col in potential_value_cols:
            if value_col in df_plot_full and pd.api.types.is_numeric_dtype(df_plot_full[value_col]):
                plt.plot(x_values_plot, df_plot_full[value_col], label=str(value_col), marker='o', linestyle='-')

        plt.title(f'Volumen Mensual de Fiat{plot_title_fiat_part}{title_suffix}')
        plt.xlabel('Mes (Año-Mes)')
        plt.ylabel('Volumen Total en Fiat')
        plt.xticks(rotation=45, ha="right")
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
        logger.error(f"plot_activity_heatmap_v2_debug: Error durante pivot_table: {e_pivot}. No se generará heatmap.{title_suffix}")
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
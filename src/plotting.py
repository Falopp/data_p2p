import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure
import plotly.graph_objects as go
import polars as pl
import plotly.express as px
from . import utils
import matplotlib.ticker as mticker
from typing import Union, List, Any, Optional
import numpy as np

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

    plt.figure(figsize=(14, 8)) # Ligeramente más ancho para el título y subtítulo
    
    # Usar el primer color de la paleta activa de Seaborn
    bar_color = sns.color_palette()[0] 
    ax = sns.barplot(x=x_tick_positions, y=y_data, color=bar_color) # Quitamos palette para usar color uniforme
    
    main_title = f'Distribución de Operaciones P2P por Hora del Día{title_suffix}'
    fig_text_explanation = "Este gráfico muestra el número total de operaciones P2P realizadas en cada hora del día (zona horaria local).\\nPermite identificar los periodos de mayor y menor actividad."
    
    plt.suptitle(main_title, fontsize=16, y=1.02) # y=1.02 para dar espacio si el título es largo
    ax.set_title(fig_text_explanation, fontsize=10, pad=20) # Usar ax.set_title como subtítulo

    ax.set_xlabel('Hora del Día (Local, 0-23)', fontsize=12)
    ax.set_ylabel('Cantidad de Operaciones', fontsize=12)
    
    ax.set_xticks(x_tick_positions)
    ax.set_xticklabels(x_category_labels)

    if len(x_tick_positions) > 12:
        locator = mticker.MaxNLocator(nbins=12, integer=True)
        ax.xaxis.set_major_locator(locator)

    # Añadir línea de media
    mean_operations = y_data.mean()
    if pd.notna(mean_operations) and mean_operations > 0 : # Solo si la media es válida y positiva
        ax.axhline(mean_operations, color='red', linestyle='--', linewidth=1.5, label=f'Promedio: {mean_operations:.2f} ops/hr')
        ax.legend(fontsize=10)

    ax.grid(True, linestyle='--', alpha=0.7)
    plt.tight_layout(rect=[0, 0, 1, 0.96]) # Ajustar rect para dejar espacio para suptitle
    
    file_path = os.path.join(out_dir, f'hourly_counts{file_identifier}.png')
    try:
        plt.savefig(file_path, dpi=300) # Añadir DPI
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

    # Usar una paleta de colores más distintiva
    palette = sns.color_palette("tab10", n_colors=10) 

    if year_month_col_internal not in monthly_fiat.columns and not (isinstance(monthly_fiat.index, pd.MultiIndex) and year_month_col_internal in monthly_fiat.index.names) and monthly_fiat.index.name != year_month_col_internal:
        logger.warning(f"Columna o índice '{year_month_col_internal}' no encontrada para plot_monthly{title_suffix}.")
        return saved_paths
        
    unique_fiats = [None]
    fiat_column_for_grouping = None

    # Determinar cómo acceder a fiat_type (columna o nivel de índice)
    if fiat_type_col_internal in monthly_fiat.columns:
        fiat_column_for_grouping = fiat_type_col_internal
        if monthly_fiat[fiat_column_for_grouping].nunique() > 0:
            unique_fiats = monthly_fiat[fiat_column_for_grouping].unique()
    elif isinstance(monthly_fiat.index, pd.MultiIndex) and fiat_type_col_internal in monthly_fiat.index.names:
        # Si es un MultiIndex y fiat_type es uno de los niveles
        unique_fiats = monthly_fiat.index.get_level_values(fiat_type_col_internal).unique()
    elif monthly_fiat.index.name == fiat_type_col_internal:
        # Si fiat_type es el nombre del índice único
        unique_fiats = monthly_fiat.index.unique()
    # Si unique_fiats sigue siendo [None], significa que no se agrupará por fiat (ej. datos ya filtrados para un fiat)

    for i, current_fiat in enumerate(unique_fiats):
        df_plot_full_orig = monthly_fiat.copy()
        plot_title_fiat_part = ""
        current_fiat_label_for_file = "all_fiats"
        current_fiat_label_for_title = "General"

        if current_fiat is not None:
            current_fiat_label_for_file = str(current_fiat).lower()
            current_fiat_label_for_title = str(current_fiat)
            plot_title_fiat_part = f" para {current_fiat_label_for_title}"
            if fiat_column_for_grouping:
                df_plot_full_orig = monthly_fiat[monthly_fiat[fiat_column_for_grouping] == current_fiat]
            elif isinstance(monthly_fiat.index, pd.MultiIndex) and fiat_type_col_internal in monthly_fiat.index.names:
                 df_plot_full_orig = monthly_fiat[monthly_fiat.index.get_level_values(fiat_type_col_internal) == current_fiat]
            elif monthly_fiat.index.name == fiat_type_col_internal:
                 df_plot_full_orig = monthly_fiat[monthly_fiat.index == current_fiat]
        
        if df_plot_full_orig.empty:
            logger.info(f"Datos vacíos para Fiat: {current_fiat_label_for_title} en plot_monthly. Omitiendo.")
            continue

        # Asegurar que YearMonthStr sea una columna para facilitar el ploteo
        if isinstance(df_plot_full_orig.index, pd.MultiIndex) and year_month_col_internal in df_plot_full_orig.index.names:
            df_plot_full = df_plot_full_orig.reset_index()
        elif df_plot_full_orig.index.name == year_month_col_internal:
            df_plot_full = df_plot_full_orig.reset_index()
        else:
            df_plot_full = df_plot_full_orig

        # Identificar columnas de valor (ej. BUY, SELL)
        exclude_cols_from_values = {year_month_col_internal, fiat_type_col_internal, 'x_plot_dt_col', 'x_plot_str_col'} 
        potential_value_cols = [col for col in df_plot_full.columns if col not in exclude_cols_from_values and pd.api.types.is_numeric_dtype(df_plot_full[col])]
        
        if not potential_value_cols:
            logger.warning(f"No hay columnas de valor numéricas para graficar en plot_monthly para {current_fiat_label_for_title}{title_suffix}. Columnas disponibles: {df_plot_full.columns}")
            continue

        plt.figure(figsize=(15, 9)) # Ajustar tamaño para subtítulo
        ax = plt.gca()
        
        # Preparar el eje X (fechas)
        if year_month_col_internal not in df_plot_full.columns:
            logger.error(f"La columna '{year_month_col_internal}' no está en df_plot_full después de reset_index. No se puede graficar.")
            plt.close()
            continue
            
        try:
            # Convertir YearMonthStr a datetime objetos para el ploteo
            df_plot_full['plot_date'] = pd.to_datetime(df_plot_full[year_month_col_internal] + '-01', errors='coerce')
            df_plot_full = df_plot_full.dropna(subset=['plot_date']).sort_values(by='plot_date')
            if df_plot_full.empty:
                logger.warning(f"DataFrame vacío después de procesar fechas para {current_fiat_label_for_title}.")
                plt.close()
                continue
            x_axis_for_plot = df_plot_full['plot_date']
        except Exception as e_date_conv:
            logger.error(f"Error convirtiendo '{year_month_col_internal}' a fechas: {e_date_conv}. Usando strings.")
            # Fallback a usar strings si la conversión de fecha falla catastróficamente
            df_plot_full = df_plot_full.sort_values(by=year_month_col_internal)
            x_axis_for_plot = df_plot_full[year_month_col_internal]

        color_idx = 0
        for value_col in potential_value_cols:
            if value_col in df_plot_full and pd.api.types.is_numeric_dtype(df_plot_full[value_col]):
                series_to_plot = df_plot_full.set_index('plot_date')[value_col] if 'plot_date' in df_plot_full else df_plot_full.set_index(year_month_col_internal)[value_col]
                
                line_color = palette[color_idx % len(palette)]
                plt.plot(series_to_plot.index, series_to_plot.values, label=str(value_col), marker='o', linestyle='-', color=line_color)
                color_idx += 1

                # Media móvil de 3 meses
                if len(series_to_plot) >= 3:
                    rolling_mean_3m = series_to_plot.rolling(window=3, center=True, min_periods=1).mean()
                    plt.plot(rolling_mean_3m.index, rolling_mean_3m.values, linestyle='--', color=line_color, alpha=0.8, label=f'{value_col} (Media Móvil 3M)')
        
        main_chart_title = f'Evolución Mensual del Volumen P2P{plot_title_fiat_part}{title_suffix}'
        fig_text_explanation_monthly = (
            f"Este gráfico muestra la evolución mensual del volumen total transaccionado en {current_fiat_label_for_title}. "
            f"Las líneas de colores representan diferentes tipos de operación (ej. Compra, Venta).\\n"
            f"Las líneas discontinuas muestran una media móvil de 3 meses para suavizar las fluctuaciones y destacar tendencias."
        )
        plt.suptitle(main_chart_title, fontsize=16, y=1.03)
        ax.set_title(fig_text_explanation_monthly, fontsize=10, pad=20)
        
        plt.xlabel('Mes (Año-Mes)', fontsize=12)
        plt.ylabel(f'Volumen Total Transaccionado ({current_fiat_label_for_title})', fontsize=12)
        
        plt.xticks(rotation=45, ha="right")
        plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m'))
        if len(x_axis_for_plot) > 12:
             plt.gca().xaxis.set_major_locator(mticker.MaxNLocator(nbins=12, prune='both'))

        # Formatear eje Y para números grandes
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x) if x >= 1000 else f"{x:,.0f}"))

        plt.legend(title='Tipo de Operación / Tendencia', fontsize=9)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout(rect=[0, 0, 1, 0.95]) # Ajuste para suptitle
        
        fiat_file_part = f"_{current_fiat_label_for_file.lower()}_" 
        file_path = os.path.join(out_dir, f'monthly_fiat_volume{fiat_file_part}{file_identifier}.png')
        try:
            plt.savefig(file_path, dpi=300) # Añadir DPI
            logger.info(f"Gráfico de volumen mensual ({current_fiat_label_for_title}) guardado en: {file_path}")
            saved_paths.append(file_path)
        except Exception as e:
            logger.error(f"Error al guardar el gráfico {file_path}: {e}")
        finally:
            plt.close() # Asegurar que la figura se cierre
            
    return saved_paths

def plot_pie(
    df_counts: pd.DataFrame, 
    column_name: str, 
    title: str, 
    fname_prefix: str, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    min_percentage_for_slice: float = 1.0 # Porcentaje mínimo para tener su propio slice, el resto va a 'Otros'
) -> str | None:
    if df_counts.empty or column_name not in df_counts.columns or df_counts[column_name].sum() == 0:
        logger.info(f"No hay datos para el gráfico de torta '{title}'{title_suffix}.")
        return None

    # Preparar datos para el gráfico de torta
    pie_data = df_counts[column_name].copy()
    total_sum = pie_data.sum()
    
    # Agrupar slices pequeños en 'Otros'
    slices = []
    labels = []
    other_sum = 0
    exploded_slices = [] # Para destacar algún slice si es necesario

    # Ordenar datos para que 'Otros' (si se crea) sea consistente
    pie_data_sorted = pie_data.sort_values(ascending=False)

    for category, value in pie_data_sorted.items():
        percentage = (value / total_sum) * 100
        if percentage < min_percentage_for_slice:
            other_sum += value
        else:
            slices.append(value)
            labels.append(f"{category} ({percentage:.1f}%)")
            exploded_slices.append(0) # No explotar por defecto
    
    if other_sum > 0:
        slices.append(other_sum)
        other_percentage = (other_sum / total_sum) * 100
        labels.append(f"Otros ({other_percentage:.1f}%)")
        exploded_slices.append(0)

    if not slices: # Todos los slices eran demasiado pequeños
        logger.info(f"Todos los slices para '{title}' son menores que {min_percentage_for_slice}%. No se generará gráfico de torta.{title_suffix}")
        return None

    # Podríamos explotar el slice más grande si es útil
    # if exploded_slices: exploded_slices[0] = 0.05 # Ejemplo: explotar el primer slice (el más grande)

    plt.figure(figsize=(12, 8)) # Tamaño más grande para mejor legibilidad
    wedges, texts, autotexts = plt.pie(
        slices, 
        labels=None, # Las etiquetas se manejan en la leyenda para evitar superposición
        autopct=None, # El porcentaje ya está en las etiquetas de la leyenda
        startangle=90, 
        colors=sns.color_palette('pastel', n_colors=len(labels)),
        pctdistance=0.85, # Distancia del centro para autopct si se usara
        explode=exploded_slices
    )

    # Añadir un círculo en el centro para hacerlo un "donut chart" (opcional)
    # centre_circle = plt.Circle((0,0),0.70,fc='white')
    # fig = plt.gcf()
    # fig.gca().add_artist(centre_circle)

    main_title = f'{title}{title_suffix}'
    # El subtítulo podría explicar qué representa el gráfico o el umbral de 'Otros'
    sub_title_explanation = f"Distribución porcentual. Las categorías con menos del {min_percentage_for_slice}% se agrupan en 'Otros'."
    
    plt.suptitle(main_title, fontsize=16, y=0.98)
    plt.gca().set_title(sub_title_explanation, fontsize=10, pad=10)
    
    plt.axis('equal') # Asegura que el gráfico de torta sea circular.
    
    # Leyenda mejorada
    plt.legend(wedges, labels, title="Categorías", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize=9)

    plt.tight_layout(rect=[0, 0, 0.85, 0.95]) # Ajustar para dar espacio a la leyenda y suptitle

    file_path = os.path.join(out_dir, f'{fname_prefix}{file_identifier}.png')
    try:
        plt.savefig(file_path, dpi=300)
        logger.info(f"Gráfico de torta '{title}' guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar el gráfico de torta {file_path}: {e}")
        plt.close()
        return None

def plot_price_distribution(
    df_completed: pd.DataFrame, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    num_bins: int = 30 # Número de bins para el histograma
) -> list[str]:
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

    # Iterar por cada par de Asset/Fiat
    for (asset, fiat), group_data in df_completed.groupby([asset_type_col_internal, fiat_type_col_internal]):
        fig = None # Inicializar fig aquí para el manejo de errores
        main_plot_title = f'Distribución de Precios de {asset} en {fiat}{title_suffix}'
        file_name_plot = f'price_distribution_{str(asset).lower().replace(" ", "_")}_{str(fiat).lower().replace(" ", "_")}{file_identifier}.png'
        file_path = os.path.join(out_dir, file_name_plot)

        try:
            if group_data.empty or group_data[price_num_col].isna().all():
                logger.info(f"Omitiendo gráfico de distribución de precios para {asset}/{fiat} (datos vacíos o NaN){title_suffix}.")
                continue
            
            # Convertir a numérico por si acaso, y eliminar NaNs en la columna de precio
            group_data_cleaned = group_data.copy() # Trabajar con una copia
            group_data_cleaned[price_num_col] = pd.to_numeric(group_data_cleaned[price_num_col], errors='coerce')
            group_data_cleaned = group_data_cleaned.dropna(subset=[price_num_col])

            if group_data_cleaned.empty:
                logger.info(f"Omitiendo gráfico de distribución de precios para {asset}/{fiat} (datos vacíos después de limpiar NaNs en precio){title_suffix}.")
                continue

            # Crear figura con dos subplots: histograma y boxplot
            fig, axes = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
            plt.suptitle(main_plot_title, fontsize=18, y=0.98)

            # Subtítulo explicativo general
            sub_title_text = (
                f"Arriba: Histograma de frecuencias de precios de {asset} en {fiat}, diferenciado por tipo de orden (Compra/Venta). "
                f"Permite ver los rangos de precios más comunes.\n"
                f"Abajo: Boxplot que resume la distribución de precios (mediana, cuartiles, outliers) para cada tipo de orden."
            )
            axes[0].set_title(sub_title_text, fontsize=10, pad=10) # Título para el primer subplot (actúa como subtítulo general)

            # Histograma en el primer subplot (axes[0])
            sns.histplot(data=group_data_cleaned, x=price_num_col, hue=order_type_col_internal, 
                         multiple="layer", kde=True, ax=axes[0], palette="muted", 
                         linewidth=0.5, bins=num_bins, alpha=0.6)
            axes[0].set_ylabel('Frecuencia', fontsize=12)
            axes[0].legend(title=f'Tipo Orden ({order_type_col_internal})', fontsize=9)
            axes[0].grid(True, linestyle='--', alpha=0.7)

            # Añadir líneas de media y mediana al histograma para cada tipo de orden
            legend_handles_hist = axes[0].get_legend_handles_labels()[0]
            legend_labels_hist = axes[0].get_legend_handles_labels()[1]

            for order_t, color in zip(pd.unique(group_data_cleaned[order_type_col_internal]), sns.color_palette("muted", n_colors=group_data_cleaned[order_type_col_internal].nunique())):
                subset = group_data_cleaned[group_data_cleaned[order_type_col_internal] == order_t]
                if not subset.empty:
                    mean_price = subset[price_num_col].mean()
                    median_price = subset[price_num_col].median()
                    if pd.notna(mean_price):
                        line_mean = axes[0].axvline(mean_price, color=color, linestyle='--', linewidth=1.2, label=f'Media {order_t}: {mean_price:.2f}')
                        if f'Media {order_t}' not in legend_labels_hist:
                            legend_handles_hist.append(line_mean); legend_labels_hist.append(f'Media {order_t}: {utils.format_large_number(mean_price, precision=2)}')
                    if pd.notna(median_price):
                        line_median = axes[0].axvline(median_price, color=color, linestyle=':', linewidth=1.2, label=f'Mediana {order_t}: {median_price:.2f}')
                        if f'Mediana {order_t}' not in legend_labels_hist:
                             legend_handles_hist.append(line_median); legend_labels_hist.append(f'Mediana {order_t}: {utils.format_large_number(median_price, precision=2)}')
            
            axes[0].legend(handles=legend_handles_hist, labels=legend_labels_hist, title=f'Tipo Orden / Estadísticas', fontsize=9)

            # Boxplot en el segundo subplot (axes[1])
            sns.boxplot(data=group_data_cleaned, x=price_num_col, y=order_type_col_internal, 
                        hue=order_type_col_internal, legend=False, ax=axes[1], palette="muted", orient='h')
            axes[1].set_xlabel(f'Precio de {asset} en {fiat}', fontsize=12)
            axes[1].set_ylabel(f'Tipo Orden ({order_type_col_internal})', fontsize=12)
            axes[1].grid(True, linestyle='--', alpha=0.7)
            
            # Formatear eje X para números grandes
            axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x, precision=2)))
            axes[1].xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x, precision=2)))
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.93]) # Ajustar rect para suptitle y subtítulo
            plt.savefig(file_path, dpi=300)
            saved_paths.append(file_path)

        except (Exception, KeyboardInterrupt) as e:
            logger.error(f"Fallo al generar/guardar gráfico {file_path} para {asset}/{fiat}{title_suffix} debido a {type(e).__name__}: {e}. Creando imagen placeholder.")
            if isinstance(e, KeyboardInterrupt): logger.warning(f"Generación de gráfico para {file_path} interrumpida manualmente.")
            try:
                if fig is not None and plt.fignum_exists(fig.number): plt.close(fig)
                error_fig, error_ax = plt.subplots(figsize=(10, 3))
                error_text = f"Error al generar gráfico para:\n{main_plot_title}\nConsulte los logs."
                error_ax.text(0.5, 0.5, error_text, ha='center', va='center', fontsize=10, color='red', wrap=True)
                error_ax.axis('off'); plt.tight_layout(); error_fig.savefig(file_path, dpi=100)
                if file_path not in saved_paths: saved_paths.append(file_path)
            except Exception as e_placeholder:
                logger.error(f"CRÍTICO: Fallo al crear placeholder para {file_path}: {e_placeholder}")
            finally: 
                if 'error_fig' in locals() and plt.fignum_exists(error_fig.number): plt.close(error_fig)
        finally:
            if fig is not None and plt.fignum_exists(fig.number): plt.close(fig)
            
    return saved_paths

def plot_volume_vs_price_scatter(
    df_completed: pd.DataFrame, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    max_points_to_plot: int = 2000 # Limitar puntos para rendimiento
) -> list[str]:
    saved_paths = []
    if df_completed.empty: 
        logger.info(f"No hay datos completados para scatter Volumen vs Precio{title_suffix}.")
        return saved_paths
        
    quantity_num_col = 'Quantity_num' 
    price_num_col = 'Price_num'
    total_price_num_col = 'TotalPrice_num' # Usado para el tamaño de los puntos
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'
    order_type_col_internal = 'order_type' # Usado para el color (hue)
    
    required_cols = [quantity_num_col, price_num_col, total_price_num_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_completed.columns]
        logger.warning(f"Faltan columnas ({missing}) para scatter Volumen vs Precio{title_suffix}.")
        return saved_paths

    df_plot_base = df_completed.copy()

    # Convertir columnas relevantes a numérico y eliminar NaNs
    for col_to_convert in [quantity_num_col, price_num_col, total_price_num_col]:
        if col_to_convert in df_plot_base.columns:
            df_plot_base[col_to_convert] = pd.to_numeric(df_plot_base[col_to_convert], errors='coerce')
    df_plot_base.dropna(subset=[quantity_num_col, price_num_col, total_price_num_col], inplace=True)

    if df_plot_base.empty: 
        logger.info(f"Datos vacíos después de conversión a numérico/NaN drop para scatter Volumen vs Precio{title_suffix}.")
        return saved_paths

    # Iterar por cada par Asset/Fiat
    for (asset_val, fiat_val), group_data_original in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_original.empty:
            logger.info(f"Datos vacíos para el par {asset_val}/{fiat_val} en scatter Volumen vs Precio{title_suffix}.")
            continue
        
        group_data_to_plot = group_data_original.copy() 

        # Limitar el número de puntos si excede el máximo
        if len(group_data_to_plot) > max_points_to_plot:
            logger.info(f"Tomando muestra de {max_points_to_plot} puntos de {len(group_data_to_plot)} para scatter {asset_val}/{fiat_val}{title_suffix}.")
            group_data_to_plot = group_data_to_plot.sample(n=max_points_to_plot, random_state=42) # random_state para reproducibilidad

        # Normalizar TotalPrice_num para el tamaño de los puntos, asegurando que sea positivo
        size_data = group_data_to_plot[total_price_num_col]
        sizes_for_plot = pd.Series([30] * len(group_data_to_plot), index=group_data_to_plot.index) # Default size
        if not size_data.empty and size_data.min() >= 0: # Asegurar que todos los valores sean no negativos
            min_val_sd = size_data.min()
            max_val_sd = size_data.max()
            if pd.notna(min_val_sd) and pd.notna(max_val_sd) and max_val_sd > min_val_sd:
                 sizes_norm = (size_data - min_val_sd) / (max_val_sd - min_val_sd) 
                 sizes_for_plot = sizes_norm * 480 + 20 # Rango de tamaño de 20 a 500
            elif pd.notna(min_val_sd) and min_val_sd == max_val_sd: # Todos los valores son iguales (y no NaN)
                 sizes_for_plot = pd.Series([100] * len(group_data_to_plot), index=group_data_to_plot.index)
        
        sizes_for_plot = sizes_for_plot.fillna(30).clip(lower=10, upper=500).astype('float64')


        fig, ax = plt.subplots(figsize=(14, 9)) # Usar fig, ax
        
        scatter_plot = sns.scatterplot(
            data=group_data_to_plot, 
            x=quantity_num_col, 
            y=price_num_col, 
            hue=order_type_col_internal, 
            size=sizes_for_plot, 
            sizes=(20, 500), 
            alpha=0.6, 
            palette="viridis", 
            legend="auto",
            ax=ax # Especificar el ax
        )
        
        main_title = f'Volumen de Transacción vs. Precio para {asset_val}/{fiat_val}{title_suffix}'
        sub_title_text = f"Cada punto es una transacción. Color indica Compra/Venta. Tamaño del punto proporcional al Monto Total en {fiat_val}."
        fig.suptitle(main_title, fontsize=16, y=0.99) # Usar fig.suptitle
        ax.set_title(sub_title_text, fontsize=10, pad=10)
        
        ax.set_xlabel(f'Volumen del Activo ({asset_val})', fontsize=12)
        ax.set_ylabel(f'Precio Unitario en {fiat_val}', fontsize=12) # Corregido aquí
        
        handles, labels = scatter_plot.get_legend_handles_labels()
        legend_params = {} # Inicializar legend_params
        if handles:
            legend_params = {'title': f'{order_type_col_internal.replace("_", " ").title()} / Monto Total'}
            if len(handles) > 6: 
                legend_params['loc'] = 'center left'
                legend_params['bbox_to_anchor'] = (1.01, 0.5) 
            else:
                legend_params['loc'] = 'best'
            ax.legend(**legend_params, fontsize=9) # Usar ax.legend

        ax.grid(True, linestyle='--', alpha=0.7)
        
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x, precision=2)))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x, precision=2)))
        
        # Ajustar el layout para acomodar la leyenda si está fuera
        fig.tight_layout(rect=[0, 0, 0.88 if legend_params.get('bbox_to_anchor') else 1, 0.95])
        
        file_name_scatter = f'volume_vs_price_scatter_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png'
        file_path = os.path.join(out_dir, file_name_scatter)
        try:
            fig.savefig(file_path, dpi=300) # Usar fig.savefig
        except Exception as e: 
            logger.error(f"Error al guardar el gráfico scatter {file_path}: {e}")
        finally:
            plt.close(fig) # Usar plt.close(fig)
            
    return saved_paths

def plot_price_over_time(
    df_completed: pd.DataFrame, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    rolling_window_short: int = 7, # Corta media móvil (ej. 7 periodos)
    rolling_window_long: int = 30  # Larga media móvil (ej. 30 periodos)
) -> list[str]:
    saved_paths = []
    if df_completed.empty: 
        logger.info(f"No hay datos completados para graficar Precio a lo largo del Tiempo{title_suffix}.")
        return saved_paths
        
    price_num_col = 'Price_num'
    match_time_local_col = 'Match_time_local'
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'
    order_type_col_internal = 'order_type'
    
    required_cols = [price_num_col, match_time_local_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_completed.columns]
        logger.warning(f"Faltan columnas ({missing}) para Precio a lo largo del Tiempo{title_suffix}.")
        return saved_paths

    # Asegurar que la columna de tiempo sea datetime y la de precio sea numérica
    df_plot_base = df_completed.copy()
    try:
        if not pd.api.types.is_datetime64_any_dtype(df_plot_base[match_time_local_col]):
            df_plot_base[match_time_local_col] = pd.to_datetime(df_plot_base[match_time_local_col], errors='coerce')
        df_plot_base[price_num_col] = pd.to_numeric(df_plot_base[price_num_col], errors='coerce')
        df_plot_base.dropna(subset=[match_time_local_col, price_num_col], inplace=True)
    except Exception as e:
        logger.error(f"Error en la conversión de tipos para Precio a lo largo del Tiempo: {e}{title_suffix}.")
        return saved_paths

    if df_plot_base.empty: 
        logger.info(f"Datos vacíos después de conversión/NaN drop para Precio a lo largo del Tiempo{title_suffix}.")
        return saved_paths

    # Iterar por cada par Asset/Fiat
    for (asset_val, fiat_val), group_data_asset_fiat in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_asset_fiat.empty:
            logger.info(f"Datos vacíos para el par {asset_val}/{fiat_val} en Precio a lo largo del Tiempo{title_suffix}.")
            continue
        
        group_data_sorted = group_data_asset_fiat.sort_values(by=match_time_local_col)
        
        fig, ax = plt.subplots(figsize=(15, 8))
        palette = sns.color_palette("husl", n_colors=group_data_sorted[order_type_col_internal].nunique() * 3) # Colores para datos y medias
        color_idx = 0

        # Iterar por cada tipo de orden (BUY/SELL)
        for order_val, order_group in group_data_sorted.groupby(order_type_col_internal):
            if order_group.empty or order_group[price_num_col].isna().all():
                logger.info(f"Datos vacíos o todos NaN para {order_val} en {asset_val}/{fiat_val} en Precio a lo largo del Tiempo{title_suffix}.")
                continue
            
            # Color base para este tipo de orden
            base_color = palette[color_idx * 3]
            ax.plot(order_group[match_time_local_col], order_group[price_num_col], marker='.', linestyle='-', alpha=0.4, label=f'Precio {order_val}', color=base_color)
            
            # Media Móvil Corta
            if len(order_group) >= rolling_window_short:
                short_rolling_mean = order_group[price_num_col].rolling(window=rolling_window_short, center=True, min_periods=1).mean()
                ax.plot(order_group[match_time_local_col], short_rolling_mean, linestyle='--', label=f'Media Móvil {rolling_window_short}P {order_val}', color=palette[color_idx * 3 + 1], linewidth=1.5)
            
            # Media Móvil Larga
            if len(order_group) >= rolling_window_long:
                long_rolling_mean = order_group[price_num_col].rolling(window=rolling_window_long, center=True, min_periods=1).mean()
                ax.plot(order_group[match_time_local_col], long_rolling_mean, linestyle=':', label=f'Media Móvil {rolling_window_long}P {order_val}', color=palette[color_idx * 3 + 2], linewidth=1.8)
            color_idx += 1

        main_title = f'Evolución del Precio para {asset_val}/{fiat_val}{title_suffix}'
        sub_title_text = f"Muestra el precio de las transacciones ({asset_val} en {fiat_val}) a lo largo del tiempo, con medias móviles de {rolling_window_short} y {rolling_window_long} periodos."
        fig.suptitle(main_title, fontsize=16, y=0.98)
        ax.set_title(sub_title_text, fontsize=10, pad=10)
        
        ax.set_xlabel('Fecha y Hora (Local)', fontsize=12)
        ax.set_ylabel(f'Precio en {fiat_val}', fontsize=12)
        
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.xticks(rotation=45, ha='right')
        
        # Ajustar la densidad de los ticks del eje X si hay muchos datos
        num_data_points = len(group_data_sorted[match_time_local_col].unique()) # Estimación del número de ticks necesarios
        if num_data_points > 20: # Umbral ajustable
            ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=15, prune='both')) # Mostrar menos ticks
        
        ax.legend(title='Serie de Precio / Media Móvil', fontsize=9)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x, precision=2)))
        
        fig.tight_layout(rect=[0, 0, 1, 0.94]) # Ajustar para suptitle y título
        
        file_name_price_time = f'price_over_time_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png'
        file_path = os.path.join(out_dir, file_name_price_time)
        try: 
            fig.savefig(file_path, dpi=300)
            saved_paths.append(file_path)
        except Exception as e: 
            logger.error(f"Error al guardar el gráfico Precio a lo largo del Tiempo {file_path}: {e}")
        finally:
            plt.close(fig)
            
    return saved_paths

def plot_volume_over_time(
    df_completed: pd.DataFrame, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    rolling_window_short: int = 7,
    rolling_window_long: int = 30
) -> list[str]:
    saved_paths = []
    if df_completed.empty: 
        logger.info(f"No hay datos completados para graficar Volumen a lo largo del Tiempo{title_suffix}.")
        return saved_paths

    # Columnas internas esperadas y de valor
    quantity_num_col = 'Quantity_num'       # Volumen en términos del activo
    total_price_num_col = 'TotalPrice_num'  # Volumen en términos de fiat
    match_time_local_col = 'Match_time_local'
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'
    
    required_cols_base = [match_time_local_col, asset_type_col_internal, fiat_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols_base):
        missing = [col for col in required_cols_base if col not in df_completed.columns]
        logger.warning(f"Faltan columnas base ({missing}) para Volumen a lo largo del Tiempo{title_suffix}.")
        return saved_paths

    # Determinar qué columnas de volumen están disponibles para graficar
    volume_cols_to_plot_map = {}
    if quantity_num_col in df_completed.columns: 
        volume_cols_to_plot_map[quantity_num_col] = ('Volumen de Activo', asset_type_col_internal)
    if total_price_num_col in df_completed.columns: 
        volume_cols_to_plot_map[total_price_num_col] = ('Volumen en Fiat', fiat_type_col_internal)

    if not volume_cols_to_plot_map:
        logger.warning(f"No se encontraron columnas de volumen ({quantity_num_col} o {total_price_num_col}) para graficar{title_suffix}.")
        return saved_paths

    # Asegurar que la columna de tiempo sea datetime y las de volumen sean numéricas
    df_plot_base = df_completed.copy()
    try:
        if not pd.api.types.is_datetime64_any_dtype(df_plot_base[match_time_local_col]):
            df_plot_base[match_time_local_col] = pd.to_datetime(df_plot_base[match_time_local_col], errors='coerce')
        for vol_col_name in volume_cols_to_plot_map.keys():
            if vol_col_name in df_plot_base.columns:
                df_plot_base[vol_col_name] = pd.to_numeric(df_plot_base[vol_col_name], errors='coerce')
        df_plot_base.dropna(subset=[match_time_local_col] + list(volume_cols_to_plot_map.keys()), how='any', inplace=True)
    except Exception as e:
        logger.error(f"Error en la conversión de tipos para Volumen a lo largo del Tiempo: {e}{title_suffix}.")
        return saved_paths

    if df_plot_base.empty: 
        logger.info(f"Datos vacíos después de conversión/NaN drop para Volumen a lo largo del Tiempo{title_suffix}.")
        return saved_paths

    # Iterar por cada par Asset/Fiat
    for (asset_val, fiat_val), group_data_asset_fiat in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_asset_fiat.empty:
            logger.info(f"Datos vacíos para el par {asset_val}/{fiat_val} en Volumen a lo largo del Tiempo{title_suffix}.")
            continue
        
        group_data_sorted = group_data_asset_fiat.sort_values(by=match_time_local_col)

        # Iterar por cada tipo de volumen a graficar (activo y/o fiat)
        for vol_col, (vol_label_base, unit_col_name_for_label) in volume_cols_to_plot_map.items():
            if group_data_sorted[vol_col].isna().all() or (group_data_sorted[vol_col] == 0).all():
                logger.info(f"Volumen en '{vol_col}' es todo NaN o cero para {asset_val}/{fiat_val}. Omitiendo gráfico.{title_suffix}")
                continue

            fig, ax = plt.subplots(figsize=(15, 8))
            
            # Determinar la unidad para la etiqueta del eje Y y el título
            label_unit = asset_val if unit_col_name_for_label == asset_type_col_internal else fiat_val
            y_axis_label = f'{vol_label_base} ({label_unit})'
            current_plot_main_title = f'Evolución del {vol_label_base} para {asset_val}/{fiat_val}{title_suffix}'
            current_plot_subtitle = f"Muestra el {vol_label_base.lower()} transaccionado ({asset_val} en {fiat_val}) a lo largo del tiempo, con medias móviles."

            # Graficar la serie de volumen principal
            ax.plot(group_data_sorted[match_time_local_col], group_data_sorted[vol_col], marker='.', linestyle='-', alpha=0.5, label=f'{vol_label_base}', color=sns.color_palette("tab10")[0])
            
            # Media Móvil Corta
            if len(group_data_sorted) >= rolling_window_short:
                short_rolling_mean = group_data_sorted[vol_col].rolling(window=rolling_window_short, center=True, min_periods=1).mean()
                ax.plot(group_data_sorted[match_time_local_col], short_rolling_mean, linestyle='--', label=f'Media Móvil {rolling_window_short}P', color=sns.color_palette("tab10")[1], linewidth=1.5)
            
            # Media Móvil Larga
            if len(group_data_sorted) >= rolling_window_long:
                long_rolling_mean = group_data_sorted[vol_col].rolling(window=rolling_window_long, center=True, min_periods=1).mean()
                ax.plot(group_data_sorted[match_time_local_col], long_rolling_mean, linestyle=':', label=f'Media Móvil {rolling_window_long}P', color=sns.color_palette("tab10")[2], linewidth=1.8)

            fig.suptitle(current_plot_main_title, fontsize=16, y=0.98)
            ax.set_title(current_plot_subtitle, fontsize=10, pad=10)
            ax.set_xlabel('Fecha y Hora (Local)', fontsize=12)
            ax.set_ylabel(y_axis_label, fontsize=12)
            
            ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M'))
            plt.xticks(rotation=45, ha='right')

            num_data_points_vol = len(group_data_sorted[match_time_local_col].unique())
            if num_data_points_vol > 20: 
                ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=15, prune='both'))
            
            ax.legend(title='Serie de Volumen / Media Móvil', fontsize=9)
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x)))
            
            fig.tight_layout(rect=[0, 0, 1, 0.94])
            
            vol_type_suffix_filename = "fiat_value" if vol_col == total_price_num_col else "asset_quantity"
            file_name_volume_time = f'volume_over_time_{vol_type_suffix_filename}_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png'
            file_path = os.path.join(out_dir, file_name_volume_time)
            try: 
                fig.savefig(file_path, dpi=300)
                saved_paths.append(file_path)
            except Exception as e: 
                logger.error(f"Error al guardar el gráfico Volumen a lo largo del Tiempo {file_path}: {e}")
            finally:
                plt.close(fig)
                
    return saved_paths

def plot_price_vs_payment_method(
    df_completed: pd.DataFrame, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    top_n_methods: int = 10 # Mostrar los N métodos de pago más comunes
) -> list[str]:
    saved_paths = []
    if df_completed.empty: 
        logger.info(f"No hay datos completados para graficar Precio vs Método de Pago{title_suffix}.")
        return saved_paths

    # Columnas internas esperadas
    price_num_col = 'Price_num'
    payment_method_col_internal = 'payment_method'
    order_type_col_internal = 'order_type' # Para el hue (color)
    fiat_type_col_internal = 'fiat_type'
    asset_type_col_internal = 'asset_type'
    
    required_cols_in_df = [price_num_col, payment_method_col_internal, order_type_col_internal, fiat_type_col_internal, asset_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols_in_df):
        missing = [col for col in required_cols_in_df if col not in df_completed.columns]
        logger.warning(f"Faltan columnas ({missing}) para Precio vs Método de Pago{title_suffix}.")
        return saved_paths

    df_plot_base = df_completed.copy()
    df_plot_base[payment_method_col_internal] = df_plot_base[payment_method_col_internal].fillna('Desconocido')
    df_plot_base[price_num_col] = pd.to_numeric(df_plot_base[price_num_col], errors='coerce')
    df_plot_base.dropna(subset=[price_num_col, payment_method_col_internal], inplace=True)

    if df_plot_base.empty: 
        logger.info(f"Datos vacíos después de limpieza para Precio vs Método de Pago{title_suffix}.")
        return saved_paths

    # Iterar por cada par Asset/Fiat
    for (asset_val, fiat_val), group_data_asset_fiat in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_asset_fiat.empty or group_data_asset_fiat[payment_method_col_internal].nunique() == 0 or group_data_asset_fiat[price_num_col].isna().all():
            logger.info(f"Omitiendo {asset_val}/{fiat_val} por datos insuficientes para Precio vs Método de Pago{title_suffix}.")
            continue
        
        # Limitar al Top N métodos de pago por frecuencia para este par Asset/Fiat
        payment_methods_to_show = group_data_asset_fiat[payment_method_col_internal].value_counts().nlargest(top_n_methods).index
        plot_data_final = group_data_asset_fiat[group_data_asset_fiat[payment_method_col_internal].isin(payment_methods_to_show)]
        effective_pm_count = plot_data_final[payment_method_col_internal].nunique()

        if plot_data_final.empty or effective_pm_count == 0:
            logger.info(f"Omitiendo {asset_val}/{fiat_val} (después de Top N) por datos insuficientes para Precio vs Método de Pago{title_suffix}.")
            continue
            
        fig, ax = plt.subplots(figsize=(max(12, effective_pm_count * 1.1), 9))
        
        # Ordenar los métodos de pago en el eje X por su mediana de precio (opcional, o alfabético)
        # sorted_methods = plot_data_final.groupby(payment_method_col_internal)[price_num_col].median().sort_values().index
        sorted_methods = sorted(plot_data_final[payment_method_col_internal].unique())

        sns.boxplot(
            x=payment_method_col_internal, 
            y=price_num_col, 
            hue=order_type_col_internal, 
            data=plot_data_final, 
            palette="Set2", # Paleta diferente para distinguir de otros gráficos
            order=sorted_methods,
            ax=ax
        )
        
        main_title = f'Precio de {asset_val} vs. Método de Pago en {fiat_val} (Top {top_n_methods}){title_suffix}'
        sub_title_text = f"Distribución de precios de {asset_val} para los {effective_pm_count} métodos de pago más usados, diferenciado por Compra/Venta."
        fig.suptitle(main_title, fontsize=16, y=0.98)
        ax.set_title(sub_title_text, fontsize=10, pad=10)
        
        ax.set_xlabel('Método de Pago', fontsize=12) 
        ax.set_ylabel(f'Precio de {asset_val} en {fiat_val}', fontsize=12)
        plt.xticks(rotation=45, ha='right', fontsize=10)
        
        ax.legend(title=order_type_col_internal.replace('_',' ').title(), fontsize=9)
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x, precision=2)))
        
        fig.tight_layout(rect=[0, 0, 1, 0.94])
        
        file_name_pvpm = f'price_vs_payment_method_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png'
        file_path = os.path.join(out_dir, file_name_pvpm)
        try: 
            fig.savefig(file_path, dpi=300)
            saved_paths.append(file_path)
        except Exception as e: 
            logger.error(f"Error al guardar el gráfico Precio vs Método de Pago {file_path}: {e}")
        finally:
            plt.close(fig)
            
    return saved_paths

def plot_activity_heatmap(
    df_all_statuses: pd.DataFrame, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    value_col: str = 'order_number', # Columna para la agregación (ej. 'order_number' para conteo, 'TotalPrice_num' para suma de volumen)
    agg_func: str = 'count'       # Función de agregación ('count', 'sum')
) -> str | None:
    logger.info(f"Generando Heatmap de Actividad (valor: {value_col}, agg: {agg_func}){title_suffix}.")
    
    if df_all_statuses.empty:
        logger.warning(f"DataFrame de entrada vacío para Heatmap de Actividad.{title_suffix}")
        return None
        
    # Columnas requeridas y de trabajo
    match_time_local_col = 'Match_time_local'
    hour_col = 'hour_of_day' # Nueva columna para la hora extraída
    day_of_week_col = 'day_of_week' # Nueva columna para el día de la semana extraído

    df_plot = df_all_statuses.copy()

    # 1. Validar y preparar columna de tiempo
    if match_time_local_col not in df_plot.columns:
        logger.warning(f"Columna de tiempo '{match_time_local_col}' no encontrada para Heatmap.{title_suffix}")
        return None
    if not pd.api.types.is_datetime64_any_dtype(df_plot[match_time_local_col]):
        try:
            df_plot[match_time_local_col] = pd.to_datetime(df_plot[match_time_local_col], errors='coerce')
        except Exception as e_time_conv:
            logger.error(f"Error convirtiendo '{match_time_local_col}' a datetime: {e_time_conv}.{title_suffix}")
            return None
    df_plot.dropna(subset=[match_time_local_col], inplace=True) # Eliminar filas donde la conversión de tiempo falló
    if df_plot.empty:
        logger.warning(f"DataFrame vacío después de procesar columna de tiempo para Heatmap.{title_suffix}")
        return None

    # 2. Validar columna de valor y función de agregación
    actual_agg_func = agg_func.lower()
    if actual_agg_func == 'count':
        # Para 'count', value_col no se usa directamente en pivot_table si aggfunc es una función como 'size' o 'count'
        # pero sí debe existir una columna (puede ser cualquiera si el aggfunc interno la ignora)
        # Si value_col es 'order_number' (o similar para conteo), y no existe, no es crítico si aggfunc es 'size'
        pass # No se necesita validación estricta de value_col para 'count' si pivot_table usa 'size'
    elif actual_agg_func == 'sum':
        if value_col not in df_plot.columns:
            logger.warning(f"Columna de valor '{value_col}' para 'sum' no encontrada en Heatmap.{title_suffix}")
            return None
        if not pd.api.types.is_numeric_dtype(df_plot[value_col]):
            try:
                df_plot[value_col] = pd.to_numeric(df_plot[value_col], errors='coerce')
                df_plot.dropna(subset=[value_col], inplace=True) # Eliminar filas donde la conversión de valor falló
            except Exception as e_val_conv:
                logger.error(f"Error convirtiendo columna de valor '{value_col}' a numérico: {e_val_conv}.{title_suffix}")
                return None
        if df_plot.empty:
            logger.warning(f"DataFrame vacío después de procesar columna de valor '{value_col}' para Heatmap.{title_suffix}")
            return None
    else:
        logger.error(f"Función de agregación '{agg_func}' no soportada para Heatmap. Usar 'count' o 'sum'.")
        return None

    # 3. Extraer hora y día de la semana
    try:
        df_plot[hour_col] = df_plot[match_time_local_col].dt.hour
        df_plot[day_of_week_col] = df_plot[match_time_local_col].dt.day_name() # Nombres: 'Monday', 'Tuesday', etc.
    except Exception as e_dt_extract:
        logger.error(f"Error extrayendo hora/día de '{match_time_local_col}': {e_dt_extract}.{title_suffix}")
        return None

    # Ordenar días de la semana
    days_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_plot[day_of_week_col] = pd.Categorical(df_plot[day_of_week_col], categories=days_ordered, ordered=True)

    # 4. Crear la matriz de actividad (pivot table)
    try:
        if actual_agg_func == 'count':
            # Usar order_number o cualquier otra columna no nula solo para que pivot_table funcione con aggfunc='count'
            # Si value_col es, por ejemplo, 'order_number' y existe, se puede usar. Si no, pivot_table con aggfunc='size' no necesita values.
            # Para mantener la flexibilidad con value_col, si es count, y value_col existe, la usamos, sino usamos 'size'
            if value_col in df_plot.columns:
                 activity_matrix = df_plot.pivot_table(values=value_col, index=day_of_week_col, columns=hour_col, aggfunc='count', fill_value=0, observed=False)
            else: # Si la columna de valor especificada para count no existe, simplemente contamos las filas
                 activity_matrix = df_plot.pivot_table(index=day_of_week_col, columns=hour_col, aggfunc='size', fill_value=0, observed=False)
        elif actual_agg_func == 'sum':
            activity_matrix = df_plot.pivot_table(values=value_col, index=day_of_week_col, columns=hour_col, aggfunc='sum', fill_value=0, observed=False)
    except Exception as e_pivot:
        logger.error(f"Error durante pivot_table para Heatmap: {e_pivot}.{title_suffix}")
        return None

    # 5. Asegurar que todas las horas (0-23) y días estén presentes
    for hour_val in range(24):
        if hour_val not in activity_matrix.columns: activity_matrix[hour_val] = 0
    activity_matrix = activity_matrix.reindex(columns=sorted(activity_matrix.columns))
    activity_matrix = activity_matrix.reindex(index=days_ordered, fill_value=0) # Asegura el orden de los días y rellena faltantes

    if activity_matrix.empty or (actual_agg_func == 'sum' and activity_matrix.sum().sum() == 0 and df_plot[value_col].sum() == 0) or (actual_agg_func == 'count' and activity_matrix.sum().sum() == 0 and len(df_plot) ==0 ):
        logger.warning(f"Matriz de actividad vacía o con todos los valores cero para Heatmap.{title_suffix}")
        return None
    
    # 6. Graficar el heatmap
    fig, ax = plt.subplots(figsize=(18, 8))
    
    fmt_str = "d" if actual_agg_func == 'count' else ",.0f" # Formato para anotaciones (enteros para count, float para sum)
    cbar_label_val = value_col.replace("_", " ").title() if value_col else "Conteo"
    cbar_label = f'{agg_func.capitalize()} de {cbar_label_val}' if actual_agg_func == 'sum' else 'Cantidad de Operaciones'
    
    sns.heatmap(activity_matrix, annot=True, fmt=fmt_str, cmap="YlGnBu", linewidths=.5, 
                cbar_kws={'label': cbar_label}, ax=ax)
    
    main_title = f'Heatmap de Actividad de Operaciones por Hora y Día ({agg_func.capitalize()} de {cbar_label_val}){title_suffix}'
    sub_title_text = f"Muestra la concentración de actividad ({cbar_label.lower()}) basada en la hora local y el día de la semana."
    fig.suptitle(main_title, fontsize=16, y=0.98)
    ax.set_title(sub_title_text, fontsize=10, pad=10)
    
    ax.set_xlabel('Hora del Día (Local, 0-23)', fontsize=12)
    ax.set_ylabel('Día de la Semana', fontsize=12)
    plt.xticks(rotation=0, fontsize=10)
    plt.yticks(rotation=0, fontsize=10)
    
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    
    # Nombre de archivo más descriptivo
    clean_value_col_name = utils.sanitize_filename_component(value_col)
    clean_agg_func_name = utils.sanitize_filename_component(agg_func)
    file_path = os.path.join(out_dir, f'activity_heatmap_{clean_value_col_name}_{clean_agg_func_name}{file_identifier}.png')
    
    try: 
        fig.savefig(file_path, dpi=300)
        logger.info(f"Heatmap de Actividad guardado en: {file_path}")
        return file_path
    except Exception as e_save:
        logger.error(f"Error al guardar el Heatmap de Actividad {file_path}: {e_save}")
        return None
    finally:
        plt.close(fig)

def plot_fees_analysis(
    fees_stats_df: pd.DataFrame, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    value_col_name: str = 'total_fees_collected', # Columna que contiene el valor de las comisiones
    index_level_name: str | None = None # Nombre del nivel del índice a usar para el eje X si es un MultiIndex
) -> str | None:
    if fees_stats_df.empty:
        logger.info(f"No hay datos de comisiones para graficar{title_suffix}.")
        return None

    # Determinar la columna de valor y las etiquetas del eje X
    plot_col = value_col_name
    if plot_col not in fees_stats_df.columns:
        # Si no es una columna, podría ser el nombre de la serie (si fees_stats_df es una Serie convertida a DataFrame)
        if fees_stats_df.shape[1] == 1 and (plot_col == fees_stats_df.iloc[:, 0].name or plot_col == 'value'): # Caso común si era una Serie
            df_plot = fees_stats_df.copy()
            df_plot.rename(columns={df_plot.columns[0]: 'data_value'}, inplace=True)
            plot_col = 'data_value'
        else:
            logger.warning(f"Columna de valor de comisión '{plot_col}' no encontrada en fees_stats_df para graficar{title_suffix}.")
            return None
    else:
        # Seleccionar solo la columna de valor si es parte de un DataFrame más grande
        df_plot = fees_stats_df[[plot_col]].copy()
        
    # Determinar etiquetas del eje X
    if index_level_name and isinstance(fees_stats_df.index, pd.MultiIndex):
        if index_level_name in fees_stats_df.index.names:
            x_labels = fees_stats_df.index.get_level_values(index_level_name)
            x_label_text = index_level_name.replace("_", " ").title()
        else:
            logger.warning(f"Nivel de índice '{index_level_name}' no encontrado. Usando el primer nivel como fallback.{title_suffix}")
            x_labels = fees_stats_df.index.get_level_values(0)
            x_label_text = fees_stats_df.index.names[0].replace("_", " ").title() if fees_stats_df.index.names[0] else "Categoría"
    else:
        x_labels = df_plot.index
        x_label_text = df_plot.index.name if df_plot.index.name is not None else "Categoría"
        x_label_text = x_label_text.replace("_", " ").title()

    # Asegurar que la columna de ploteo sea numérica
    if not pd.api.types.is_numeric_dtype(df_plot[plot_col]):
        try:
            df_plot[plot_col] = pd.to_numeric(df_plot[plot_col], errors='coerce')
            df_plot.dropna(subset=[plot_col], inplace=True)
        except Exception as e_conv_fees:
            logger.error(f"Error convirtiendo columna de comisiones '{plot_col}' a numérica: {e_conv_fees}{title_suffix}.")
            return None

    if df_plot.empty or df_plot[plot_col].sum() == 0:
        logger.info(f"No hay comisiones significativas (>0) en '{plot_col}' para graficar{title_suffix}.")
        return None

    # Ordenar por valor para un mejor gráfico de barras
    df_plot_sorted = df_plot.sort_values(by=plot_col, ascending=False)
    x_labels_sorted = x_labels[df_plot_sorted.index] # Reordenar etiquetas del eje X según el sort de df_plot

    fig, ax = plt.subplots(figsize=(12, 8))
    
    bars = ax.bar(x_labels_sorted.astype(str), df_plot_sorted[plot_col], width=0.8, color=sns.color_palette("viridis", len(df_plot_sorted)))

    main_plot_title = f'Análisis de Comisiones por {x_label_text}{title_suffix}'
    sub_title_text = f"Muestra el total de comisiones ('{plot_col.replace('_', ' ').title()}') recaudadas, agrupadas por {x_label_text.lower()}."
    fig.suptitle(main_plot_title, fontsize=16, y=0.98)
    ax.set_title(sub_title_text, fontsize=10, pad=10)
    
    ax.set_xlabel(x_label_text, fontsize=12)
    ax.set_ylabel(f'Monto Total de Comisión ({plot_col.replace("_", " ").title()})', fontsize=12)
    plt.xticks(rotation=45, ha='right', fontsize=10)
    
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x)))
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    # Añadir etiquetas de valor encima de las barras (opcional, puede ser ruidoso si hay muchas barras)
    # for bar in bars:
    #     yval = bar.get_height()
    #     ax.text(bar.get_x() + bar.get_width()/2.0, yval + 0.01 * df_plot_sorted[plot_col].max(), utils.format_large_number(yval, precision=1), ha='center', va='bottom', fontsize=8)

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    
    file_path = os.path.join(out_dir, f'fees_analysis_by_{utils.sanitize_filename_component(x_label_text.lower())}_{utils.sanitize_filename_component(plot_col.lower())}{file_identifier}.png')
    try:
        fig.savefig(file_path, dpi=300)
        logger.info(f"Gráfico de análisis de comisiones ({x_label_text}) guardado en: {file_path}")
        return file_path
    except Exception as e_save_fees:
        logger.error(f"Error al guardar el gráfico de comisiones {file_path}: {e_save_fees}")
        return None
    finally:
        plt.close(fig)

# DONE: 2.1 Sankey Fiat -> Activo
def plot_sankey_fiat_asset(df_data: pl.DataFrame, 
                           out_dir: str, 
                           title_suffix: str = "", 
                           file_identifier: str = "_general",
                           value_col_name: str | None = None
                           ) -> str | None:
    logger.info(f"Iniciando generación de gráfico Sankey Fiat -> Activo{title_suffix}.")
    
    fiat_col = 'fiat_type'
    asset_col = 'asset_type'
    # Usar value_col_name si se proporciona, de lo contrario, usar 'TotalPrice_num' por defecto
    actual_value_col = value_col_name if value_col_name else 'TotalPrice_num'

    if actual_value_col not in df_data.columns:
        logger.error(f"Columna de valor '{actual_value_col}' no encontrada en los datos para Sankey. Columnas disponibles: {df_data.columns}")
        return None

    df_agg = df_data.group_by([fiat_col, asset_col]).agg(pl.sum(actual_value_col).alias(actual_value_col))
    if df_agg.is_empty():
        logger.info(f"No hay datos agregados para generar el gráfico Sankey con la columna '{actual_value_col}'{title_suffix}.")
        return None
    
    sankey_agg_pd = df_agg.to_pandas() 

    # Combinar las dos listas de nodos (origen y destino)
    combined_node_list = sankey_agg_pd[fiat_col].tolist() + sankey_agg_pd[asset_col].tolist()
    # Convertir la lista combinada a una Serie de Pandas antes de pd.unique()
    all_nodes = pd.unique(pd.Series(combined_node_list)).tolist()
    node_map = {name: i for i, name in enumerate(all_nodes)}

    # source_indices = sankey_agg_pd[fiat_col].map_elements(lambda x: node_map[x], return_dtype=pl.Int64).to_list()
    source_indices = sankey_agg_pd[fiat_col].map(node_map).tolist()
    target_indices = sankey_agg_pd[asset_col].map(node_map).tolist()
    values = sankey_agg_pd[actual_value_col].tolist()

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

def plot_volume_vs_price_scatter(
    df_completed: pd.DataFrame, 
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    max_points_to_plot: int = 2000 # Limitar puntos para rendimiento
) -> list[str]:
    saved_paths = []
    if df_completed.empty: 
        logger.info(f"No hay datos completados para scatter Volumen vs Precio{title_suffix}.")
        return saved_paths
        
    quantity_num_col = 'Quantity_num' 
    price_num_col = 'Price_num'
    total_price_num_col = 'TotalPrice_num' # Usado para el tamaño de los puntos
    asset_type_col_internal = 'asset_type'
    fiat_type_col_internal = 'fiat_type'
    order_type_col_internal = 'order_type' # Usado para el color (hue)
    
    required_cols = [quantity_num_col, price_num_col, total_price_num_col, asset_type_col_internal, fiat_type_col_internal, order_type_col_internal]
    if not all(col in df_completed.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_completed.columns]
        logger.warning(f"Faltan columnas ({missing}) para scatter Volumen vs Precio{title_suffix}.")
        return saved_paths

    df_plot_base = df_completed.copy()

    # Convertir columnas relevantes a numérico y eliminar NaNs
    for col_to_convert in [quantity_num_col, price_num_col, total_price_num_col]:
        if col_to_convert in df_plot_base.columns:
            df_plot_base[col_to_convert] = pd.to_numeric(df_plot_base[col_to_convert], errors='coerce')
    df_plot_base.dropna(subset=[quantity_num_col, price_num_col, total_price_num_col], inplace=True)

    if df_plot_base.empty: 
        logger.info(f"Datos vacíos después de conversión a numérico/NaN drop para scatter Volumen vs Precio{title_suffix}.")
        return saved_paths

    # Iterar por cada par Asset/Fiat
    for (asset_val, fiat_val), group_data_original in df_plot_base.groupby([asset_type_col_internal, fiat_type_col_internal]):
        if group_data_original.empty:
            logger.info(f"Datos vacíos para el par {asset_val}/{fiat_val} en scatter Volumen vs Precio{title_suffix}.")
            continue
        
        group_data_to_plot = group_data_original.copy() 

        # Limitar el número de puntos si excede el máximo
        if len(group_data_to_plot) > max_points_to_plot:
            logger.info(f"Tomando muestra de {max_points_to_plot} puntos de {len(group_data_to_plot)} para scatter {asset_val}/{fiat_val}{title_suffix}.")
            group_data_to_plot = group_data_to_plot.sample(n=max_points_to_plot, random_state=42) # random_state para reproducibilidad

        # Normalizar TotalPrice_num para el tamaño de los puntos, asegurando que sea positivo
        size_data = group_data_to_plot[total_price_num_col]
        sizes_for_plot = pd.Series([30] * len(group_data_to_plot), index=group_data_to_plot.index) # Default size
        if not size_data.empty and size_data.min() >= 0: # Asegurar que todos los valores sean no negativos
            min_val_sd = size_data.min()
            max_val_sd = size_data.max()
            if pd.notna(min_val_sd) and pd.notna(max_val_sd) and max_val_sd > min_val_sd:
                 sizes_norm = (size_data - min_val_sd) / (max_val_sd - min_val_sd) 
                 sizes_for_plot = sizes_norm * 480 + 20 # Rango de tamaño de 20 a 500
            elif pd.notna(min_val_sd) and min_val_sd == max_val_sd: # Todos los valores son iguales (y no NaN)
                 sizes_for_plot = pd.Series([100] * len(group_data_to_plot), index=group_data_to_plot.index)
        
        sizes_for_plot = sizes_for_plot.fillna(30).clip(lower=10, upper=500).astype('float64')


        fig, ax = plt.subplots(figsize=(14, 9)) # Usar fig, ax
        
        scatter_plot = sns.scatterplot(
            data=group_data_to_plot, 
            x=quantity_num_col, 
            y=price_num_col, 
            hue=order_type_col_internal, 
            size=sizes_for_plot, 
            sizes=(20, 500), 
            alpha=0.6, 
            palette="viridis", 
            legend="auto",
            ax=ax # Especificar el ax
        )
        
        main_title = f'Volumen de Transacción vs. Precio para {asset_val}/{fiat_val}{title_suffix}'
        sub_title_text = f"Cada punto es una transacción. Color indica Compra/Venta. Tamaño del punto proporcional al Monto Total en {fiat_val}."
        fig.suptitle(main_title, fontsize=16, y=0.99) # Usar fig.suptitle
        ax.set_title(sub_title_text, fontsize=10, pad=10)
        
        ax.set_xlabel(f'Volumen del Activo ({asset_val})', fontsize=12)
        ax.set_ylabel(f'Precio Unitario en {fiat_val}', fontsize=12) # Corregido aquí
        
        handles, labels = scatter_plot.get_legend_handles_labels()
        legend_params = {} # Inicializar legend_params
        if handles:
            legend_params = {'title': f'{order_type_col_internal.replace("_", " ").title()} / Monto Total'}
            if len(handles) > 6: 
                legend_params['loc'] = 'center left'
                legend_params['bbox_to_anchor'] = (1.01, 0.5) 
            else:
                legend_params['loc'] = 'best'
            ax.legend(**legend_params, fontsize=9) # Usar ax.legend

        ax.grid(True, linestyle='--', alpha=0.7)
        
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x, precision=2)))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x, precision=2)))
        
        # Ajustar el layout para acomodar la leyenda si está fuera
        fig.tight_layout(rect=[0, 0, 0.88 if legend_params.get('bbox_to_anchor') else 1, 0.95])
        
        file_name_scatter = f'volume_vs_price_scatter_{str(asset_val).lower().replace(" ", "_")}_{str(fiat_val).lower().replace(" ", "_")}{file_identifier}.png'
        file_path = os.path.join(out_dir, file_name_scatter)
        try:
            fig.savefig(file_path, dpi=300) # Usar fig.savefig
        except Exception as e: 
            logger.error(f"Error al guardar el gráfico scatter {file_path}: {e}")
        finally:
            plt.close(fig) # Usar plt.close(fig)
            
    return saved_paths

# --- Nueva función para Boxplots por Método de Pago ---
def plot_boxplot_by_payment_method(
    df_data_pd: pd.DataFrame, 
    value_col_name: str,
    value_col_label: str, # Etiqueta legible para el eje Y (ej: "Precio", "Volumen Total")
    payment_method_col: str,
    asset_col: str,
    fiat_col: str,
    out_dir: str, 
    title_suffix: str = "", 
    file_identifier: str = "_general",
    top_n_methods: int = 15 # Mostrar los N métodos de pago más comunes
) -> list[str]:
    saved_paths = []
    logger.info(f"Iniciando generación de Boxplots: '{value_col_label}' vs Método de Pago{title_suffix}.")

    required_cols = [value_col_name, payment_method_col, asset_col, fiat_col]
    if not all(col in df_data_pd.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_data_pd.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para Boxplot '{value_col_label}' vs Método de Pago{title_suffix}. No se generarán gráficos.")
        return saved_paths

    # Asegurar que la columna de valor sea numérica
    if not pd.api.types.is_numeric_dtype(df_data_pd[value_col_name]):
        logger.warning(f"La columna de valor '{value_col_name}' no es numérica. No se pueden generar boxplots.{title_suffix}")
        return saved_paths
        
    df_plot_base = df_data_pd.dropna(subset=[value_col_name, payment_method_col])
    if df_plot_base.empty:
        logger.info(f"No hay datos válidos (después de eliminar NaNs en valor y método de pago) para Boxplot '{value_col_label}' vs Método de Pago{title_suffix}.")
        return saved_paths

    # Determinar si estamos graficando para un par asset/fiat específico o para datos combinados (USD equivalent)
    # Si asset_col y fiat_col son None, asumimos que es un gráfico combinado con una columna como 'TotalPrice_USD_equivalent'
    # y no necesitamos agrupar por asset/fiat.

    if asset_col and fiat_col:
        grouped_by_pair = df_plot_base.groupby([asset_col, fiat_col])
        iterator = grouped_by_pair
        is_combined_plot = False
    else: # Es un gráfico combinado (ej. TotalPrice_USD_equivalent)
        iterator = [(("Combined", "USD Equivalent"), df_plot_base)] # Crear un iterador de un solo grupo
        is_combined_plot = True


    for (current_asset, current_fiat), group_df in iterator:
        if group_df.empty or group_df[payment_method_col].nunique() < 1:
            logger.info(f"Omitiendo boxplot para {current_asset}/{current_fiat} (datos insuficientes o sin métodos de pago válidos).{title_suffix}")
            continue

        # Limitar el número de métodos de pago a mostrar
        common_methods = group_df[payment_method_col].value_counts().nlargest(top_n_methods).index
        df_plot_final = group_df[group_df[payment_method_col].isin(common_methods)]

        if df_plot_final.empty:
            logger.info(f"Omitiendo boxplot para {current_asset}/{current_fiat} (sin datos tras filtrar por Top {top_n_methods} métodos).{title_suffix}")
            continue
        
        num_methods = df_plot_final[payment_method_col].nunique()
        fig_width = max(12, num_methods * 0.8) # Ajustar ancho de la figura según cantidad de métodos
        plt.figure(figsize=(fig_width, 8))
        
        order = sorted(df_plot_final[payment_method_col].unique())

        sns.boxplot(
            data=df_plot_final, 
            x=payment_method_col, 
            y=value_col_name,
            # hue=payment_method_col, # No es necesario el hue si ya estamos en el eje X
            palette="muted", 
            order=order,
            legend=False
        )
        
        if is_combined_plot:
            plot_title = f"Distribución de {value_col_label} por Método de Pago (Top {top_n_methods}){title_suffix}"
            y_axis_label = f"{value_col_label}"
            file_name_prefix = f"boxplot_{value_col_name}_payment_method_combined"
        else:
            plot_title = f"Distribución de {value_col_label} ({current_asset}/{current_fiat}) por Método de Pago (Top {top_n_methods}){title_suffix}"
            y_axis_label = f"{value_col_label} de {current_asset} en {current_fiat}"
            file_name_prefix = f"boxplot_{value_col_name}_payment_method_{str(current_asset).lower()}_{str(current_fiat).lower()}"

        plt.title(plot_title, fontsize=15)
        plt.xlabel("Método de Pago", fontsize=12)
        plt.ylabel(y_axis_label, fontsize=12)
        plt.xticks(rotation=45, ha="right", fontsize=10)
        plt.yticks(fontsize=10)
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        file_name = f"{file_name_prefix}{file_identifier}.png"
        file_path = os.path.join(out_dir, file_name)
        
        try:
            plt.savefig(file_path)
            logger.info(f"Boxplot ({current_asset}/{current_fiat} - {value_col_label}) guardado en: {file_path}")
            saved_paths.append(file_path)
            plt.close()
        except Exception as e:
            logger.error(f"Error al guardar Boxplot ({current_asset}/{current_fiat} - {value_col_label}) {file_path}: {e}")
            plt.close()
            
    return saved_paths

# --- Fin de la nueva función ---

# --- Nueva función para Análisis de Completitud de Órdenes a lo largo del Tiempo ---
def plot_order_status_over_time(
    df_all_statuses_pd: pd.DataFrame,
    time_col: str,
    status_col: str,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general"
) -> str | None:
    logger.info(f"Iniciando generación de gráfico de Completitud de Órdenes a lo largo del Tiempo{title_suffix}.")

    required_cols = [time_col, status_col]
    if not all(col in df_all_statuses_pd.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_all_statuses_pd.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para gráfico de Completitud de Órdenes{title_suffix}. No se generará.")
        return None

    if df_all_statuses_pd[required_cols].isna().any().any():
        logger.warning(f"Hay valores nulos en columnas '{time_col}' o '{status_col}'. Se intentará continuar filtrando esos nulos.")
        df_plot_data = df_all_statuses_pd.dropna(subset=required_cols).copy()
    else:
        df_plot_data = df_all_statuses_pd.copy()
        
    if not pd.api.types.is_datetime64_any_dtype(df_plot_data[time_col]):
        try:
            df_plot_data[time_col] = pd.to_datetime(df_plot_data[time_col])
        except Exception as e:
            logger.error(f"No se pudo convertir la columna de tiempo '{time_col}' a datetime: {e}. No se generará gráfico.")
            return None
            
    if df_plot_data.empty:
        logger.info(f"No hay datos válidos para gráfico de Completitud de Órdenes{title_suffix}.")
        return None

    # Crear una columna 'YearMonth' para agrupar
    df_plot_data['YearMonth'] = df_plot_data[time_col].dt.to_period('M')

    # Contar ocurrencias de cada estado por mes
    status_counts_monthly = df_plot_data.groupby(['YearMonth', status_col]).size().unstack(fill_value=0)

    if status_counts_monthly.empty:
        logger.info(f"No hay datos después de agrupar por mes y estado para Completitud de Órdenes{title_suffix}.")
        return None

    # Calcular porcentajes
    status_percentages_monthly = status_counts_monthly.apply(lambda x: x / x.sum() * 100, axis=1)
    
    # Asegurar que el índice sea de tipo string para evitar problemas con Matplotlib/Seaborn si es PeriodIndex
    status_percentages_monthly.index = status_percentages_monthly.index.astype(str)


    plt.figure(figsize=(15, 8))
    
    # Colores (puedes personalizar esto)
    # Tratar de usar una paleta consistente si es posible o definir colores específicos por estado
    status_order = ['Completed', 'Cancelled', 'Appealing'] # Definir un orden deseado para el stack
    # Filtrar columnas para que solo estén las presentes en el DF y en el orden deseado
    cols_to_plot = [s for s in status_order if s in status_percentages_monthly.columns]
    # Añadir otras columnas que no estén en status_order al final
    other_cols = [s for s in status_percentages_monthly.columns if s not in cols_to_plot]
    final_plot_order = cols_to_plot + other_cols
    
    # Crear el gráfico de áreas apiladas
    status_percentages_monthly[final_plot_order].plot(kind='area', stacked=True, colormap='viridis', alpha=0.8)

    plt.title(f"Distribución Porcentual de Estados de Órdenes por Mes{title_suffix}", fontsize=16)
    plt.xlabel("Mes (Año-Mes)", fontsize=12)
    plt.ylabel("Porcentaje de Órdenes (%)", fontsize=12)
    plt.ylim(0, 100) # Asegurar que el eje Y vaya de 0 a 100%
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.yticks(fontsize=10)
    
    # Mover la leyenda fuera del gráfico
    plt.legend(title="Estado de Orden", bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Ajustar layout para dar espacio a la leyenda

    file_name = f"order_status_over_time_percentage{file_identifier}.png"
    file_path = os.path.join(out_dir, file_name)

    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico de Completitud de Órdenes por Mes guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar gráfico de Completitud de Órdenes por Mes {file_path}: {e}")
        plt.close()
        return None

# --- Fin de la nueva función ---

# --- Nueva función para Volumen por Día de la Semana ---
def plot_volume_by_day_of_week(
    df_data_pd: pd.DataFrame,
    time_col: str,
    volume_col: str,
    volume_col_label: str, # Ej: "Volumen Total (USD)", "Volumen Total (USD Equivalent)"
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
    specific_plot_title: str | None = None # Título específico si se quiere sobreescribir el default
) -> str | None:
    logger.info(f"Iniciando generación de gráfico de Volumen por Día de la Semana ({volume_col_label}){title_suffix}.")

    required_cols = [time_col, volume_col]
    if not all(col in df_data_pd.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_data_pd.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para gráfico de Volumen por Día de la Semana{title_suffix}. No se generará.")
        return None

    df_plot_data = df_data_pd.dropna(subset=required_cols).copy()

    if not pd.api.types.is_datetime64_any_dtype(df_plot_data[time_col]):
        try:
            df_plot_data[time_col] = pd.to_datetime(df_plot_data[time_col])
        except Exception as e:
            logger.error(f"No se pudo convertir la columna de tiempo '{time_col}' a datetime: {e}. No se generará gráfico de volumen por día.")
            return None
            
    if not pd.api.types.is_numeric_dtype(df_plot_data[volume_col]):
        logger.error(f"La columna de volumen '{volume_col}' no es numérica. No se generará gráfico de volumen por día.")
        return None

    if df_plot_data.empty:
        logger.info(f"No hay datos válidos para gráfico de Volumen por Día de la Semana ({volume_col_label}){title_suffix}.")
        return None

    df_plot_data['day_of_week'] = df_plot_data[time_col].dt.day_name()
    days_ordered = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    df_plot_data['day_of_week'] = pd.Categorical(df_plot_data['day_of_week'], categories=days_ordered, ordered=True)

    volume_by_day = df_plot_data.groupby('day_of_week', observed=False)[volume_col].sum()
    
    if volume_by_day.empty or volume_by_day.sum() == 0:
        logger.info(f"No hay volumen agregado para graficar por día de la semana ({volume_col_label}){title_suffix}.")
        return None

    plt.figure(figsize=(12, 7))
    sns.barplot(x=volume_by_day.index, y=volume_by_day.values, palette="viridis")

    title = specific_plot_title if specific_plot_title else f"Volumen Total de {volume_col_label} por Día de la Semana{title_suffix}"
    plt.title(title, fontsize=15)
    plt.xlabel("Día de la Semana", fontsize=12)
    plt.ylabel(f"{volume_col_label}", fontsize=12)
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.yticks(fontsize=10)
    
    # Formatear el eje Y para mostrar números grandes de forma legible
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x)))

    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    file_name = f"volume_by_day_of_week_{volume_col.lower()}{file_identifier}.png"
    file_path = os.path.join(out_dir, file_name)

    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico de Volumen por Día de la Semana ({volume_col_label}) guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar gráfico de Volumen por Día de la Semana ({volume_col_label}) {file_path}: {e}")
        plt.close()
        return None

# --- Fin de la nueva función ---

# --- Nueva función para VWAP (Precio Promedio Ponderado por Volumen) a lo largo del Tiempo ---
def plot_vwap_over_time(
    df_data_pd: pd.DataFrame,
    time_col: str,
    price_col: str,
    quantity_col: str,
    asset_col: str,
    fiat_col: str,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general"
) -> list[str]:
    saved_paths = []
    logger.info(f"Iniciando generación de gráfico VWAP a lo largo del Tiempo{title_suffix}.")

    required_cols = [time_col, price_col, quantity_col, asset_col, fiat_col]
    if not all(col in df_data_pd.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_data_pd.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para gráfico VWAP{title_suffix}. No se generará.")
        return saved_paths

    df_plot_data = df_data_pd.dropna(subset=required_cols).copy()

    if not pd.api.types.is_datetime64_any_dtype(df_plot_data[time_col]):
        try:
            df_plot_data[time_col] = pd.to_datetime(df_plot_data[time_col])
        except Exception as e:
            logger.error(f"No se pudo convertir la columna de tiempo '{time_col}' a datetime: {e}. No se generará gráfico VWAP.")
            return saved_paths
            
    for col_num in [price_col, quantity_col]:
        if not pd.api.types.is_numeric_dtype(df_plot_data[col_num]):
            try:
                df_plot_data[col_num] = pd.to_numeric(df_plot_data[col_num], errors='coerce')
                df_plot_data.dropna(subset=[col_num], inplace=True)
            except Exception as e_conv_num:
                 logger.error(f"No se pudo convertir la columna '{col_num}' a numérica: {e_conv_num}. No se generará gráfico VWAP.")
                 return saved_paths


    if df_plot_data.empty:
        logger.info(f"No hay datos válidos para gráfico VWAP{title_suffix}.")
        return saved_paths

    # Agrupar por Asset y Fiat
    for (current_asset, current_fiat), group_df_asset_fiat in df_plot_data.groupby([asset_col, fiat_col]):
        if group_df_asset_fiat.empty:
            logger.info(f"No hay datos para el par {current_asset}/{current_fiat} para VWAP.")
            continue

        # Agrupar por día y calcular VWAP
        group_df_asset_fiat = group_df_asset_fiat.set_index(time_col)
        
        # Calcular Precio * Cantidad
        price_times_quantity = group_df_asset_fiat[price_col] * group_df_asset_fiat[quantity_col]
        
        # Agrupar por día (resample)
        daily_sum_price_x_qty = price_times_quantity.resample('D').sum()
        daily_sum_qty = group_df_asset_fiat[quantity_col].resample('D').sum()
        
        # Calcular VWAP diario
        vwap_daily = daily_sum_price_x_qty / daily_sum_qty
        vwap_daily = vwap_daily.dropna() # Eliminar días donde el volumen fue cero (resulta en NaN/inf)

        if vwap_daily.empty:
            logger.info(f"VWAP diario vacío para {current_asset}/{current_fiat}{title_suffix}.")
            continue

        plt.figure(figsize=(15, 7))
        vwap_daily.plot(marker='.', linestyle='-', color='dodgerblue')
        
        # Añadir media móvil simple de 7 días si hay suficientes datos
        if len(vwap_daily) >= 7:
            vwap_daily.rolling(window=7, center=False).mean().plot(linestyle='--', color='orangered', label='Media Móvil 7 Días VWAP')
        
        plt.title(f"Precio Promedio Ponderado por Volumen (VWAP) Diario para {current_asset}/{current_fiat}{title_suffix}", fontsize=15)
        plt.xlabel("Fecha", fontsize=12)
        plt.ylabel(f"VWAP en {current_fiat}", fontsize=12)
        plt.xticks(rotation=45, ha="right", fontsize=10)
        plt.yticks(fontsize=10)
        
        ax = plt.gca()
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x) if x > 100 else f"{x:.2f}")) # Formato condicional

        if len(vwap_daily) >= 7:
            plt.legend()
            
        plt.grid(axis='y', linestyle='--', alpha=0.7)
        plt.tight_layout()

        file_name_part = f"vwap_daily_{str(current_asset).lower()}_{str(current_fiat).lower()}{file_identifier}.png"
        file_path = os.path.join(out_dir, file_name_part)
        
        try:
            plt.savefig(file_path)
            logger.info(f"Gráfico VWAP ({current_asset}/{current_fiat}) guardado en: {file_path}")
            saved_paths.append(file_path)
            plt.close()
        except Exception as e:
            logger.error(f"Error al guardar gráfico VWAP ({current_asset}/{current_fiat}) {file_path}: {e}")
            plt.close()
            
    return saved_paths

# --- Fin de la nueva función ---

# --- Nueva función para Comparativa de Volumen Compra vs. Venta a lo largo del Tiempo ---
def plot_buy_sell_volume_over_time(
    df_data_pd: pd.DataFrame,
    time_col: str,
    volume_col: str, # Ej: 'TotalPrice_num' o 'TotalPrice_USD_equivalent'
    order_type_col: str,
    out_dir: str,
    volume_col_label: str, # Ej: "Volumen Fiat (USD)", "Volumen Fiat (UYU)", "Volumen (USD Equivalent)"
    title_suffix: str = "",
    file_identifier: str = "_general",
    specific_plot_title: str | None = None
) -> str | None:
    logger.info(f"Iniciando generación de gráfico de Volumen Compra vs. Venta ({volume_col_label}){title_suffix}.")

    required_cols = [time_col, volume_col, order_type_col]
    if not all(col in df_data_pd.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_data_pd.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para gráfico Volumen Compra vs. Venta{title_suffix}. No se generará.")
        return None

    df_plot = df_data_pd.dropna(subset=required_cols).copy()

    if not pd.api.types.is_datetime64_any_dtype(df_plot[time_col]):
        try:
            df_plot[time_col] = pd.to_datetime(df_plot[time_col])
        except Exception as e:
            logger.error(f"No se pudo convertir la columna de tiempo '{time_col}' a datetime: {e}. No se generará gráfico.")
            return None
            
    if not pd.api.types.is_numeric_dtype(df_plot[volume_col]):
        try:
            df_plot[volume_col] = pd.to_numeric(df_plot[volume_col], errors='coerce')
            df_plot.dropna(subset=[volume_col], inplace=True)
        except Exception as e_conv_num_vol:
            logger.error(f"No se pudo convertir la columna de volumen '{volume_col}' a numérica: {e_conv_num_vol}. No se generará gráfico.")
            return None

    if df_plot.empty:
        logger.info(f"No hay datos válidos para gráfico Volumen Compra vs. Venta ({volume_col_label}){title_suffix}.")
        return None

    df_plot['YearMonth'] = df_plot[time_col].dt.to_period('M')

    # Filtrar para asegurar que solo tenemos 'BUY' y 'SELL' (o los valores esperados en order_type_col)
    # Esto es importante si hay otros tipos de 'order_type' que no son relevantes aquí.
    # Asumimos que los valores relevantes son 'BUY' y 'SELL'.
    expected_order_types = ['BUY', 'SELL']
    df_plot = df_plot[df_plot[order_type_col].isin(expected_order_types)]

    if df_plot.empty:
        logger.info(f"No hay datos con tipos de orden 'BUY' o 'SELL' para gráfico Volumen Compra vs. Venta ({volume_col_label}){title_suffix}.")
        return None

    volume_by_month_type = df_plot.groupby(['YearMonth', order_type_col], observed=False)[volume_col].sum().unstack(fill_value=0)
    
    if volume_by_month_type.empty:
        logger.info(f"No hay volumen agregado para graficar Compra vs. Venta ({volume_col_label}){title_suffix}.")
        return None
        
    # Asegurar que las columnas BUY y SELL existan, incluso si no hubo operaciones de un tipo
    if 'BUY' not in volume_by_month_type.columns: volume_by_month_type['BUY'] = 0
    if 'SELL' not in volume_by_month_type.columns: volume_by_month_type['SELL'] = 0

    # Convertir PeriodIndex a string para graficar
    volume_by_month_type.index = volume_by_month_type.index.astype(str)

    plt.figure(figsize=(15, 8))
    volume_by_month_type[['BUY', 'SELL']].plot(kind='bar', stacked=False, colormap='coolwarm') # side-by-side
    # Para stacked: stacked=True

    title = specific_plot_title if specific_plot_title else f"Volumen Mensual de Compra vs. Venta ({volume_col_label}){title_suffix}"
    plt.title(title, fontsize=16)
    plt.xlabel("Mes (Año-Mes)", fontsize=12)
    plt.ylabel(f"{volume_col_label}", fontsize=12)
    plt.xticks(rotation=45, ha="right", fontsize=10)
    plt.yticks(fontsize=10)
    plt.legend(title="Tipo de Orden")
    
    ax = plt.gca()
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x)))
    
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()

    file_name = f"buy_sell_volume_monthly_{volume_col.lower()}{file_identifier}.png"
    file_path = os.path.join(out_dir, file_name)

    try:
        plt.savefig(file_path)
        logger.info(f"Gráfico de Volumen Compra vs. Venta ({volume_col_label}) guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar gráfico de Volumen Compra vs. Venta ({volume_col_label}) {file_path}: {e}")
        plt.close()
        return None

# --- Fin de la nueva función ---

# --- Nueva función para Scatter de Correlación Precio vs. Volumen Total Fiat ---
def plot_price_vs_total_fiat_scatter(
    df_data_pd: pd.DataFrame,
    price_col: str,
    total_fiat_col: str, # Ej: 'TotalPrice_num' o 'TotalPrice_USD_equivalent'
    order_type_col: str, # Para colorear los puntos
    asset_col_for_grouping: str | None, # Para agrupar si no es combinado (ej: 'asset_type')
    fiat_col_for_grouping: str | None,  # Para agrupar si no es combinado (ej: 'fiat_type')
    out_dir: str,
    x_axis_label: str, # Ej: "Precio (USD)", "Precio (UYU)"
    y_axis_label: str, # Ej: "Volumen Total Transacción (USD)", "Volumen Total Transacción (USD Equivalent)"
    title_suffix: str = "",
    file_identifier: str = "_general",
    specific_plot_title: str | None = None,
    hue_col_for_combined: str | None = None # Ej: 'asset_type' si es un gráfico combinado
) -> str | None:
    logger.info(f"Iniciando generación de Scatter Precio vs Volumen Fiat ({x_axis_label} vs {y_axis_label}){title_suffix}.")

    required_cols = [price_col, total_fiat_col, order_type_col]
    if asset_col_for_grouping: required_cols.append(asset_col_for_grouping)
    if fiat_col_for_grouping: required_cols.append(fiat_col_for_grouping)
    if hue_col_for_combined and hue_col_for_combined not in required_cols : required_cols.append(hue_col_for_combined)
        
    if not all(col in df_data_pd.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_data_pd.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para Scatter Precio vs Volumen Fiat{title_suffix}. No se generará.")
        return None

    df_plot = df_data_pd.dropna(subset=[price_col, total_fiat_col, order_type_col]).copy()

    for col_num in [price_col, total_fiat_col]:
        if not pd.api.types.is_numeric_dtype(df_plot[col_num]):
            try:
                df_plot[col_num] = pd.to_numeric(df_plot[col_num], errors='coerce')
                df_plot.dropna(subset=[col_num], inplace=True)
            except Exception as e_conv_scatter_num:
                logger.error(f"No se pudo convertir la columna '{col_num}' a numérica para scatter: {e_conv_scatter_num}.")
                return None

    if df_plot.empty:
        logger.info(f"No hay datos válidos para Scatter Precio vs Volumen Fiat ({x_axis_label} vs {y_axis_label}){title_suffix}.")
        return None

    # Limitar el número de puntos para evitar gráficos muy pesados, especialmente scatter plots
    max_points = 5000 
    if len(df_plot) > max_points:
        logger.info(f"Demasiados puntos ({len(df_plot)}) para scatter Precio vs Volumen Fiat. Tomando muestra de {max_points}.")
        df_plot = df_plot.sample(n=max_points, random_state=42)

    plt.figure(figsize=(12, 8))
    
    current_hue_col = order_type_col
    if hue_col_for_combined and hue_col_for_combined in df_plot.columns:
        current_hue_col = hue_col_for_combined

    sns.scatterplot(
        data=df_plot, 
        x=price_col, 
        y=total_fiat_col, 
        hue=current_hue_col, 
        alpha=0.6, 
        palette="viridis", 
        s=50 # Tamaño de los puntos
    )

    title = specific_plot_title if specific_plot_title else f"Correlación Precio vs. Volumen Total Fiat{title_suffix}"
    plt.title(title, fontsize=16)
    plt.xlabel(x_axis_label, fontsize=12)
    plt.ylabel(y_axis_label, fontsize=12)
    plt.xticks(fontsize=10)
    plt.yticks(fontsize=10)
    plt.legend(title=current_hue_col.replace('_',' ').title())

    # Formatear ejes para números grandes si es necesario y aplicar escala logarítmica si hay mucha dispersión
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x) if x > 1000 else f"{x:.2f}"))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x)))

    # Considerar escala logarítmica si los datos tienen un rango muy amplio
    # Ejemplo: si el máximo es > 100 veces el mínimo (y ambos positivos)
    price_min, price_max = df_plot[price_col].min(), df_plot[price_col].max()
    total_fiat_min, total_fiat_max = df_plot[total_fiat_col].min(), df_plot[total_fiat_col].max()

    if price_min > 0 and price_max / price_min > 100:
        logger.info(f"Aplicando escala logarítmica al eje X (Precio) para scatter ({x_axis_label} vs {y_axis_label}).")
        ax.set_xscale('log')
    if total_fiat_min > 0 and total_fiat_max / total_fiat_min > 100:
        logger.info(f"Aplicando escala logarítmica al eje Y (Volumen Fiat) para scatter ({x_axis_label} vs {y_axis_label}).")
        ax.set_yscale('log')

    plt.grid(True, linestyle='--', alpha=0.5)
    plt.tight_layout()

    file_name = f"scatter_price_vs_totalfiat{file_identifier}.png"
    file_path = os.path.join(out_dir, file_name)

    try:
        plt.savefig(file_path)
        logger.info(f"Scatter Precio vs Volumen Fiat ({x_axis_label} vs {y_axis_label}) guardado en: {file_path}")
        plt.close()
        return file_path
    except Exception as e:
        logger.error(f"Error al guardar Scatter Precio vs Volumen Fiat ({x_axis_label} vs {y_axis_label}) {file_path}: {e}")
        plt.close()
        return None

# --- Fin de la nueva función ---

# --- Nueva función para Análisis de Profundidad de Mercado Simplificado ---
def plot_simplified_market_depth(
    df_data_pd: pd.DataFrame,
    price_col: str,
    quantity_col: str,
    order_type_col: str,
    asset_col: str,
    fiat_col: str,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general"
) -> list[str]:
    saved_paths = []
    logger.info(f"Iniciando generación de gráfico de Profundidad de Mercado Simplificado{title_suffix}.")

    required_cols = [price_col, quantity_col, order_type_col, asset_col, fiat_col]
    if not all(col in df_data_pd.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_data_pd.columns]
        logger.warning(f"Faltan columnas ({', '.join(missing)}) para Profundidad de Mercado{title_suffix}. No se generará.")
        return saved_paths

    df_plot_data = df_data_pd.dropna(subset=required_cols).copy()

    for col_num in [price_col, quantity_col]:
        if not pd.api.types.is_numeric_dtype(df_plot_data[col_num]):
            try:
                df_plot_data[col_num] = pd.to_numeric(df_plot_data[col_num], errors='coerce')
                df_plot_data.dropna(subset=[col_num], inplace=True)
            except Exception as e_conv_md_num:
                logger.error(f"No se pudo convertir la columna '{col_num}' a numérica para Market Depth: {e_conv_md_num}.")
                return saved_paths

    if df_plot_data.empty:
        logger.info(f"No hay datos válidos para Profundidad de Mercado{title_suffix}.")
        return saved_paths

    # Agrupar por Asset y Fiat
    for (current_asset, current_fiat), group_df_pair in df_plot_data.groupby([asset_col, fiat_col]):
        if group_df_pair.empty:
            logger.info(f"No hay datos para el par {current_asset}/{current_fiat} para Profundidad de Mercado.")
            continue

        bids = group_df_pair[group_df_pair[order_type_col] == 'BUY']
        asks = group_df_pair[group_df_pair[order_type_col] == 'SELL']

        if bids.empty and asks.empty:
            logger.info(f"No hay órdenes BUY o SELL para {current_asset}/{current_fiat} para Profundidad de Mercado.")
            continue

        # Procesar Bids (Compras)
        bid_depth = pd.DataFrame()
        if not bids.empty:
            bid_depth = bids.groupby(price_col)[quantity_col].sum().sort_index(ascending=False).cumsum().reset_index()
            bid_depth.rename(columns={quantity_col: 'cumulative_bid_volume'}, inplace=True)

        # Procesar Asks (Ventas)
        ask_depth = pd.DataFrame()
        if not asks.empty:
            ask_depth = asks.groupby(price_col)[quantity_col].sum().sort_index(ascending=True).cumsum().reset_index()
            ask_depth.rename(columns={quantity_col: 'cumulative_ask_volume'}, inplace=True)

        if bid_depth.empty and ask_depth.empty:
            logger.info(f"No se pudo calcular profundidad para Bids ni Asks para {current_asset}/{current_fiat}.")
            continue
            
        plt.figure(figsize=(12, 7))
        
        if not bid_depth.empty:
            plt.plot(bid_depth['cumulative_bid_volume'], bid_depth[price_col], label='Demanda (Vol. Compras Acum.)', color='green', drawstyle='steps-pre')
        
        if not ask_depth.empty:
            plt.plot(ask_depth['cumulative_ask_volume'], ask_depth[price_col], label='Oferta (Vol. Ventas Acum.)', color='red', drawstyle='steps-pre')

        plt.title(f"Profundidad de Mercado Simplificada para {current_asset}/{current_fiat}{title_suffix}", fontsize=15)
        plt.xlabel(f"Volumen Acumulado de {current_asset}", fontsize=12)
        plt.ylabel(f"Precio en {current_fiat}", fontsize=12)
        plt.xticks(fontsize=10); plt.yticks(fontsize=10)
        plt.legend(); plt.grid(True, linestyle='--', alpha=0.7)
        
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x)))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x) if x > 1000 else f"{x:.3f}"))
        
        # Podríamos intentar encontrar y marcar el "precio de cruce" si existe visualmente.
        # Esto es más complejo y podría requerir interpolación.

        plt.tight_layout()
        file_name_part = f"market_depth_simplified_{str(current_asset).lower()}_{str(current_fiat).lower()}{file_identifier}.png"
        file_path = os.path.join(out_dir, file_name_part)
        
        try:
            plt.savefig(file_path)
            logger.info(f"Gráfico de Profundidad de Mercado ({current_asset}/{current_fiat}) guardado en: {file_path}")
            saved_paths.append(file_path)
            plt.close()
        except Exception as e:
            logger.error(f"Error al guardar Profundidad de Mercado ({current_asset}/{current_fiat}) {file_path}: {e}")
            plt.close()
            
    return saved_paths

# --- Fin de la nueva función ---

def plot_daily_average(daily_avg_fiat: pd.DataFrame, out_dir: str, title_suffix: str = "", file_identifier: str = "_general") -> list[str]:
    saved_paths = []
    if daily_avg_fiat.empty:
        logger.info(f"No hay datos para el gráfico de promedio diario{title_suffix}.")
        return saved_paths

    # Columnas internas esperadas
    day_of_week_col_internal = 'DayOfWeek' # 0-6 (Lunes-Domingo) o nombres
    fiat_type_col_internal = 'fiat_type'
    
    # Usar una paleta de colores consistente
    palette = sns.color_palette("viridis", n_colors=7) # Paleta para días de la semana

    # Determinar cómo acceder a fiat_type (columna o nivel de índice)
    unique_fiats = [None]
    fiat_column_for_grouping = None
    if fiat_type_col_internal in daily_avg_fiat.columns:
        fiat_column_for_grouping = fiat_type_col_internal
        if daily_avg_fiat[fiat_column_for_grouping].nunique() > 0:
            unique_fiats = daily_avg_fiat[fiat_column_for_grouping].unique()
    elif isinstance(daily_avg_fiat.index, pd.MultiIndex) and fiat_type_col_internal in daily_avg_fiat.index.names:
        unique_fiats = daily_avg_fiat.index.get_level_values(fiat_type_col_internal).unique()
    elif daily_avg_fiat.index.name == fiat_type_col_internal:
        unique_fiats = daily_avg_fiat.index.unique()

    # Orden de los días de la semana para el gráfico
    days_order_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    days_order_num = list(range(7)) # 0 para Lunes, ..., 6 para Domingo

    for i, current_fiat in enumerate(unique_fiats):
        df_plot_full_orig = daily_avg_fiat.copy()
        plot_title_fiat_part = ""
        current_fiat_label_for_file = "all_fiats"
        current_fiat_label_for_title = "General"

        if current_fiat is not None:
            current_fiat_label_for_file = str(current_fiat).lower()
            current_fiat_label_for_title = str(current_fiat)
            plot_title_fiat_part = f" para {current_fiat_label_for_title}"
            if fiat_column_for_grouping:
                df_plot_full_orig = daily_avg_fiat[daily_avg_fiat[fiat_column_for_grouping] == current_fiat]
            elif isinstance(daily_avg_fiat.index, pd.MultiIndex) and fiat_type_col_internal in daily_avg_fiat.index.names:
                df_plot_full_orig = daily_avg_fiat[daily_avg_fiat.index.get_level_values(fiat_type_col_internal) == current_fiat]
            elif daily_avg_fiat.index.name == fiat_type_col_internal:
                df_plot_full_orig = daily_avg_fiat[daily_avg_fiat.index == current_fiat]
        
        if df_plot_full_orig.empty:
            logger.info(f"Datos vacíos para Fiat: {current_fiat_label_for_title} en plot_daily_average. Omitiendo.")
            continue

        # Asegurar que DayOfWeek sea una columna para facilitar el ploteo
        if isinstance(df_plot_full_orig.index, pd.MultiIndex) and day_of_week_col_internal in df_plot_full_orig.index.names:
            df_plot_full = df_plot_full_orig.reset_index()
        elif df_plot_full_orig.index.name == day_of_week_col_internal:
            df_plot_full = df_plot_full_orig.reset_index()
        else:
            df_plot_full = df_plot_full_orig

        if day_of_week_col_internal not in df_plot_full.columns:
            logger.warning(f"La columna '{day_of_week_col_internal}' no fue encontrada en los datos para plot_daily_average para {current_fiat_label_for_title}{title_suffix}.")
            continue

        # Convertir DayOfWeek a categórico con el orden correcto
        # Asumimos que DayOfWeek puede ser numérico (0-6) o string ("Lunes", "Martes", etc.)
        if pd.api.types.is_numeric_dtype(df_plot_full[day_of_week_col_internal]):
            # Mapear números a nombres para etiquetas y orden
            day_map_num_to_name = dict(zip(days_order_num, days_order_es))
            df_plot_full['DayName'] = df_plot_full[day_of_week_col_internal].map(day_map_num_to_name)
            plot_x_col = 'DayName'
            category_order = days_order_es
        else:
            # Si ya son nombres, usar directamente, pero asegurar el orden
            plot_x_col = day_of_week_col_internal
            category_order = pd.Categorical(df_plot_full[day_of_week_col_internal], categories=days_order_es, ordered=True)
            df_plot_full[plot_x_col] = category_order # Re-asignar para asegurar el tipo categórico ordenado
        
        df_plot_full = df_plot_full.sort_values(by=plot_x_col, key=lambda x: x.map({day: i for i, day in enumerate(days_order_es)}) if pd.api.types.is_string_dtype(x) else x) 

        exclude_cols_from_values = {day_of_week_col_internal, fiat_type_col_internal, 'DayName'} 
        potential_value_cols = [col for col in df_plot_full.columns if col not in exclude_cols_from_values and pd.api.types.is_numeric_dtype(df_plot_full[col])]

        if not potential_value_cols:
            logger.warning(f"No hay columnas de valor numéricas para graficar en plot_daily_average para {current_fiat_label_for_title}{title_suffix}. Columnas: {df_plot_full.columns}")
            continue

        plt.figure(figsize=(15, 9))
        ax = plt.gca()

        # Usaremos barplot para esto, agrupando si hay múltiples value_cols (ej. BUY, SELL)
        num_value_cols = len(potential_value_cols)
        bar_width = 0.8 / num_value_cols if num_value_cols > 0 else 0.8
        x_indices = np.arange(len(df_plot_full[plot_x_col].unique())) # Un índice numérico para las posiciones de las barras

        for idx, value_col in enumerate(potential_value_cols):
            series_to_plot = df_plot_full.groupby(plot_x_col, observed=False)[value_col].mean().reindex(category_order, fill_value=0)
            bar_positions = x_indices - (0.8 - bar_width) / 2 + idx * bar_width
            plt.bar(bar_positions, series_to_plot.values, width=bar_width, label=str(value_col), color=palette[idx % len(palette)], alpha=0.8)

            # Línea de media general para esta columna de valor
            overall_mean = df_plot_full[value_col].mean()
            plt.axhline(overall_mean, color=palette[idx % len(palette)], linestyle='--', alpha=0.7, label=f'{value_col} (Media Gral: {utils.format_large_number(overall_mean)})')

        main_chart_title = f'Promedio de Volumen P2P por Día de la Semana{plot_title_fiat_part}{title_suffix}'
        fig_text_explanation_daily = (
            f"Este gráfico muestra el volumen promedio transaccionado para cada día de la semana en {current_fiat_label_for_title}. "
            f"Las barras de colores representan diferentes tipos de operación (ej. Compra, Venta).\\n"
            f"Las líneas discontinuas indican el promedio general de volumen para cada tipo de operación a lo largo de todos los días."
        )
        plt.suptitle(main_chart_title, fontsize=16, y=1.03)
        ax.set_title(fig_text_explanation_daily, fontsize=10, pad=20)
        
        plt.xlabel('Día de la Semana', fontsize=12)
        plt.ylabel(f'Volumen Promedio Transaccionado ({current_fiat_label_for_title})', fontsize=12)
        plt.xticks(ticks=x_indices, labels=category_order, rotation=45, ha="right")
        
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: utils.format_large_number(x) if x >= 1000 else f"{x:,.0f}"))
        
        plt.legend(title='Tipo de Operación / Promedio Gral.', fontsize=9)
        plt.grid(True, linestyle='--', alpha=0.7, axis='y') # Grid solo en el eje Y para barplot
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        fiat_file_part = f"_{current_fiat_label_for_file.lower()}_"
        file_path = os.path.join(out_dir, f'daily_average_volume{fiat_file_part}{file_identifier}.png')
        try:
            plt.savefig(file_path, dpi=300)
            logger.info(f"Gráfico de volumen promedio diario ({current_fiat_label_for_title}) guardado en: {file_path}")
            saved_paths.append(file_path)
        except Exception as e:
            logger.error(f"Error al guardar el gráfico {file_path}: {e}")
        finally:
            plt.close()

    return saved_paths
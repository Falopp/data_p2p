import os
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
import polars as pl
from . import utils
import numpy as np
from typing import Dict, List, Union, Optional
from .plot_utils import set_default_style, save_figure

logger = logging.getLogger(__name__)
sns.set_theme(style="whitegrid")


def generate_all_counterparty_plots(
    counterparty_data: Dict[str, pd.DataFrame],
    base_figures_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
) -> List[str]:
    """
    Función principal que genera todos los gráficos de contrapartes.

    Args:
        counterparty_data: Diccionario con DataFrames de análisis de contrapartes
        base_figures_dir: Directorio base para guardar figuras
        title_suffix: Sufijo para títulos
        file_identifier: Identificador para nombres de archivos

    Returns:
        Lista de rutas de archivos generados
    """
    # Crear subdirectorio específico para contrapartes
    counterparty_dir = os.path.join(base_figures_dir, "counterparty_analysis")
    os.makedirs(counterparty_dir, exist_ok=True)

    all_figure_paths = []

    try:
        # 1. Ranking de volumen de contrapartes
        if (
            "general_stats" in counterparty_data
            and not counterparty_data["general_stats"].empty
        ):
            logger.info("Generando gráfico de ranking de volumen...")
            paths = plot_counterparty_volume_ranking(
                counterparty_data["general_stats"],
                counterparty_dir,
                title_suffix,
                file_identifier,
            )
            all_figure_paths.extend(paths)

        # 2. Scatter volumen vs frecuencia
        if (
            "general_stats" in counterparty_data
            and not counterparty_data["general_stats"].empty
        ):
            logger.info("Generando scatter volumen vs frecuencia...")
            paths = plot_volume_vs_frequency_scatter(
                counterparty_data["general_stats"],
                counterparty_dir,
                title_suffix,
                file_identifier,
            )
            all_figure_paths.extend(paths)

        # 3. Distribución de tiers VIP
        if (
            "vip_counterparties" in counterparty_data
            and not counterparty_data["vip_counterparties"].empty
        ):
            logger.info("Generando distribución de tiers VIP...")
            paths = plot_vip_tier_distribution(
                counterparty_data["vip_counterparties"],
                counterparty_dir,
                title_suffix,
                file_identifier,
            )
            all_figure_paths.extend(paths)

        # 4. Heatmap de métodos de pago
        if (
            "payment_preferences" in counterparty_data
            and not counterparty_data["payment_preferences"].empty
        ):
            logger.info("Generando heatmap de métodos de pago...")
            paths = plot_payment_preferences_heatmap(
                counterparty_data["payment_preferences"],
                counterparty_dir,
                title_suffix,
                file_identifier,
            )
            all_figure_paths.extend(paths)

        # 5. Timeline de evolución temporal
        if (
            "temporal_evolution" in counterparty_data
            and not counterparty_data["temporal_evolution"].empty
        ):
            logger.info("Generando timeline temporal...")
            paths = plot_temporal_timeline(
                counterparty_data["temporal_evolution"],
                counterparty_dir,
                title_suffix,
                file_identifier,
            )
            all_figure_paths.extend(paths)

        # 6. Scatter eficiencia vs volumen
        if (
            "efficiency_stats" in counterparty_data
            and "general_stats" in counterparty_data
        ):
            if (
                not counterparty_data["efficiency_stats"].empty
                and not counterparty_data["general_stats"].empty
            ):
                logger.info("Generando scatter eficiencia vs volumen...")
                paths = plot_efficiency_vs_volume(
                    counterparty_data["efficiency_stats"],
                    counterparty_data["general_stats"],
                    counterparty_dir,
                    title_suffix,
                    file_identifier,
                )
                all_figure_paths.extend(paths)

        # 7. Radar de patrones de trading
        if (
            "trading_patterns" in counterparty_data
            and not counterparty_data["trading_patterns"].empty
        ):
            logger.info("Generando radar de patrones...")
            paths = plot_trading_patterns_radar(
                counterparty_data["trading_patterns"],
                counterparty_dir,
                title_suffix,
                file_identifier,
            )
            all_figure_paths.extend(paths)

        logger.info(f"Generados {len(all_figure_paths)} gráficos de contrapartes")
        return all_figure_paths

    except Exception as e:
        logger.error(f"Error generando gráficos de contrapartes: {e}")
        return all_figure_paths


def plot_counterparty_volume_ranking(
    general_stats_df: pd.DataFrame,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
    top_n: int = 20,
) -> List[str]:
    """Genera gráfico de ranking de contrapartes por volumen."""
    saved_paths = []

    if general_stats_df.empty:
        logger.warning("No hay datos de contrapartes para ranking de volumen")
        return saved_paths

    try:
        # Preparar datos
        top_counterparties = general_stats_df.head(top_n).copy()

        # Gráfico de barras horizontales
        fig, ax = plt.subplots(figsize=(12, 8))

        bars = ax.barh(
            range(len(top_counterparties)),
            top_counterparties["total_volume"],
            color=plt.cm.viridis(np.linspace(0, 1, len(top_counterparties))),
        )

        ax.set_yticks(range(len(top_counterparties)))
        ax.set_yticklabels(top_counterparties["Counterparty"], fontsize=10)
        ax.set_xlabel("Volumen Total (USD)", fontsize=12)
        ax.set_title(
            f"Top {top_n} Contrapartes por Volumen{title_suffix}",
            fontsize=14,
            fontweight="bold",
        )

        # Añadir valores en las barras
        for i, (bar, value) in enumerate(zip(bars, top_counterparties["total_volume"])):
            ax.text(
                value + max(top_counterparties["total_volume"]) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"${value:,.0f}",
                va="center",
                fontsize=9,
            )

        plt.tight_layout()

        # Guardar
        filename = f"counterparty_volume_ranking{file_identifier}.png"
        file_path = os.path.join(out_dir, filename)
        plt.savefig(file_path, dpi=300, bbox_inches="tight")
        plt.close()
        saved_paths.append(file_path)

        logger.info(f"Gráfico de ranking de volumen guardado: {file_path}")

    except Exception as e:
        logger.error(f"Error generando ranking de volumen: {e}")

    return saved_paths


def plot_volume_vs_frequency_scatter(
    general_stats_df: pd.DataFrame,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
) -> List[str]:
    """Genera scatter plot de volumen vs frecuencia de operaciones."""
    saved_paths = []

    if general_stats_df.empty:
        return saved_paths

    try:
        fig, ax = plt.subplots(figsize=(12, 8))

        # Crear scatter con tamaños variables
        scatter = ax.scatter(
            general_stats_df["total_operations"],
            general_stats_df["total_volume"],
            s=general_stats_df["operations_per_day"] * 20,  # Tamaño basado en ops/día
            alpha=0.6,
            c=general_stats_df["avg_volume_per_op"],
            cmap="viridis",
        )

        # Añadir colorbar
        cbar = plt.colorbar(scatter)
        cbar.set_label("Volumen Promedio por Operación (USD)", fontsize=11)

        ax.set_xlabel("Número Total de Operaciones", fontsize=12)
        ax.set_ylabel("Volumen Total (USD)", fontsize=12)
        ax.set_title(
            f"Volumen vs Frecuencia de Trading{title_suffix}",
            fontsize=14,
            fontweight="bold",
        )

        # Escala logarítmica si es necesario
        if (
            general_stats_df["total_volume"].max()
            / general_stats_df["total_volume"].min()
            > 100
        ):
            ax.set_yscale("log")
        if (
            general_stats_df["total_operations"].max()
            / general_stats_df["total_operations"].min()
            > 50
        ):
            ax.set_xscale("log")

        # Añadir etiquetas para top contrapartes
        top_5 = general_stats_df.head(5)
        for _, row in top_5.iterrows():
            ax.annotate(
                row["Counterparty"],
                (row["total_operations"], row["total_volume"]),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=9,
                alpha=0.8,
            )

        plt.tight_layout()

        # Guardar
        filename = f"counterparty_volume_vs_frequency{file_identifier}.png"
        file_path = os.path.join(out_dir, filename)
        plt.savefig(file_path, dpi=300, bbox_inches="tight")
        plt.close()
        saved_paths.append(file_path)

        logger.info(f"Scatter volumen vs frecuencia guardado: {file_path}")

    except Exception as e:
        logger.error(f"Error generando scatter volumen vs frecuencia: {e}")

    return saved_paths


def plot_vip_tier_distribution(
    vip_df: pd.DataFrame,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
) -> List[str]:
    """Genera distribución de tiers VIP."""
    saved_paths = []

    if vip_df.empty or "vip_tier" not in vip_df.columns:
        return saved_paths

    try:
        set_default_style()
        # Contar por tier
        tier_counts = vip_df["vip_tier"].value_counts()

        # Colores por tier
        tier_colors = {
            "Diamond": "#E8E8E8",  # Plateado brillante
            "Gold": "#FFD700",  # Dorado
            "Silver": "#C0C0C0",  # Plateado
            "Bronze": "#CD7F32",  # Bronce
            "Standard": "#808080",  # Gris
        }

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Gráfico de barras
        colors = [tier_colors.get(tier, "#808080") for tier in tier_counts.index]
        bars = ax1.bar(tier_counts.index, tier_counts.values, color=colors, alpha=0.8)
        ax1.set_ylabel("Número de Contrapartes", fontsize=12)
        ax1.set_title(
            f"Distribución de Tiers VIP{title_suffix}", fontsize=14, fontweight="bold"
        )
        ax1.tick_params(axis="x", rotation=45)

        # Añadir valores en barras
        for bar, value in zip(bars, tier_counts.values):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.1,
                str(value),
                ha="center",
                va="bottom",
                fontsize=11,
            )

        # Gráfico circular
        wedges, texts, autotexts = ax2.pie(
            tier_counts.values,
            labels=tier_counts.index,
            colors=[tier_colors.get(tier, "#808080") for tier in tier_counts.index],
            autopct="%1.1f%%",
            startangle=90,
        )
        ax2.set_title(
            f"Proporción de Tiers VIP{title_suffix}", fontsize=14, fontweight="bold"
        )

        # Guardar utilizando utilidades
        filename = f"counterparty_vip_tier_distribution{file_identifier}.png"
        file_path = save_figure(fig, out_dir, filename, dpi=300)
        saved_paths.append(file_path)

        logger.info(f"Distribución VIP guardada: {file_path}")

    except Exception as e:
        logger.error(f"Error generando distribución VIP: {e}")

    return saved_paths


def plot_payment_preferences_heatmap(
    payment_df: pd.DataFrame,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
) -> List[str]:
    """Genera heatmap de preferencias de métodos de pago."""
    saved_paths = []

    if payment_df.empty:
        return saved_paths

    try:
        # Crear matriz pivotada
        pivot_data = payment_df.pivot_table(
            values="pct_volume",
            index="Counterparty",
            columns="payment_method",
            fill_value=0,
        )

        # Filtrar solo contrapartes con volumen significativo
        top_counterparties = (
            payment_df.groupby("Counterparty")["volume_with_method"]
            .sum()
            .nlargest(15)
            .index
        )
        pivot_filtered = pivot_data.loc[
            pivot_data.index.intersection(top_counterparties)
        ]
        # Convertir datos a numéricos y asegurar dtype float para el heatmap
        pivot_filtered = (
            pivot_filtered.apply(pd.to_numeric, errors="coerce").fillna(0).astype(float)
        )

        if pivot_filtered.empty:
            return saved_paths

        fig, ax = plt.subplots(figsize=(12, 8))

        # Crear heatmap
        sns.heatmap(
            pivot_filtered,
            annot=True,
            fmt=".1f",
            cmap="YlOrRd",
            ax=ax,
            cbar_kws={"label": "Porcentaje de Volumen (%)"},
        )

        ax.set_title(
            f"Preferencias de Métodos de Pago por Contraparte{title_suffix}",
            fontsize=14,
            fontweight="bold",
        )
        ax.set_xlabel("Método de Pago", fontsize=12)
        ax.set_ylabel("Contraparte", fontsize=12)

        plt.tight_layout()

        # Guardar
        filename = f"counterparty_payment_preferences_heatmap{file_identifier}.png"
        file_path = os.path.join(out_dir, filename)
        plt.savefig(file_path, dpi=300, bbox_inches="tight")
        plt.close()
        saved_paths.append(file_path)

        logger.info(f"Heatmap de métodos de pago guardado: {file_path}")

    except Exception as e:
        logger.error(f"Error generando heatmap de métodos de pago: {e}")

    return saved_paths


def plot_temporal_timeline(
    temporal_df: pd.DataFrame,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
) -> List[str]:
    """Genera timeline de evolución temporal."""
    saved_paths = []

    if temporal_df.empty:
        return saved_paths

    try:
        # Seleccionar top contrapartes por volumen total
        total_volume_by_cp = (
            temporal_df.groupby("Counterparty")["monthly_volume"].sum().nlargest(8)
        )
        top_counterparties = total_volume_by_cp.index

        filtered_df = temporal_df[temporal_df["Counterparty"].isin(top_counterparties)]

        if filtered_df.empty:
            return saved_paths

        fig, ax = plt.subplots(figsize=(15, 8))

        # Crear líneas para cada contraparte
        colors = plt.cm.Set3(np.linspace(0, 1, len(top_counterparties)))

        for i, cp in enumerate(top_counterparties):
            cp_data = filtered_df[filtered_df["Counterparty"] == cp].sort_values(
                "year_month"
            )

            ax.plot(
                cp_data["year_month"],
                cp_data["monthly_volume"],
                marker="o",
                label=cp,
                color=colors[i],
                linewidth=2,
                markersize=4,
            )

        ax.set_xlabel("Mes", fontsize=12)
        ax.set_ylabel("Volumen Mensual (USD)", fontsize=12)
        ax.set_title(
            f"Evolución Temporal de Contrapartes Top{title_suffix}",
            fontsize=14,
            fontweight="bold",
        )
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

        # Rotar etiquetas del eje x
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Guardar
        filename = f"counterparty_temporal_timeline{file_identifier}.png"
        file_path = os.path.join(out_dir, filename)
        plt.savefig(file_path, dpi=300, bbox_inches="tight")
        plt.close()
        saved_paths.append(file_path)

        logger.info(f"Timeline temporal guardado: {file_path}")

    except Exception as e:
        logger.error(f"Error generando timeline temporal: {e}")

    return saved_paths


def plot_efficiency_vs_volume(
    efficiency_df: pd.DataFrame,
    general_stats_df: pd.DataFrame,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
) -> List[str]:
    """Genera scatter de eficiencia vs volumen."""
    saved_paths = []

    if efficiency_df.empty or general_stats_df.empty:
        return saved_paths

    try:
        # Combinar datos
        combined_df = efficiency_df.merge(
            general_stats_df[["Counterparty", "total_volume", "total_operations"]],
            on="Counterparty",
            how="inner",
        )

        if combined_df.empty:
            return saved_paths

        fig, ax = plt.subplots(figsize=(12, 8))

        # Scatter con tamaño basado en número de operaciones
        scatter = ax.scatter(
            combined_df["total_volume"],
            combined_df["efficiency_score"],
            s=combined_df["total_operations"] * 3,  # Tamaño proporcional
            alpha=0.6,
            c=combined_df["completion_rate"],
            cmap="RdYlGn",
        )

        # Colorbar
        cbar = plt.colorbar(scatter)
        cbar.set_label("Tasa de Completitud (%)", fontsize=11)

        ax.set_xlabel("Volumen Total (USD)", fontsize=12)
        ax.set_ylabel("Score de Eficiencia", fontsize=12)
        ax.set_title(
            f"Eficiencia vs Volumen por Contraparte{title_suffix}",
            fontsize=14,
            fontweight="bold",
        )

        # Escala logarítmica en X si es necesario
        if combined_df["total_volume"].max() / combined_df["total_volume"].min() > 100:
            ax.set_xscale("log")

        # Añadir líneas de referencia
        ax.axhline(
            y=combined_df["efficiency_score"].median(),
            color="red",
            linestyle="--",
            alpha=0.5,
            label="Mediana Eficiencia",
        )
        ax.axvline(
            x=combined_df["total_volume"].median(),
            color="blue",
            linestyle="--",
            alpha=0.5,
            label="Mediana Volumen",
        )
        ax.legend()

        plt.tight_layout()

        # Guardar
        filename = f"counterparty_efficiency_vs_volume{file_identifier}.png"
        file_path = os.path.join(out_dir, filename)
        plt.savefig(file_path, dpi=300, bbox_inches="tight")
        plt.close()
        saved_paths.append(file_path)

        logger.info(f"Scatter eficiencia vs volumen guardado: {file_path}")

    except Exception as e:
        logger.error(f"Error generando eficiencia vs volumen: {e}")

    return saved_paths


def plot_trading_patterns_radar(
    patterns_df: pd.DataFrame,
    out_dir: str,
    title_suffix: str = "",
    file_identifier: str = "_general",
    top_n: int = 5,  # Mostrar radar para las top N contrapartes por alguna métrica
) -> List[str]:
    """Genera un gráfico de radar para visualizar patrones de trading."""
    saved_paths = []
    if patterns_df.empty:
        logger.warning("DataFrame de patrones de trading vacío, no se generará radar.")
        return saved_paths

    try:
        # Asegurar que las columnas que deben ser numéricas lo sean.
        # 'most_active_weekday' es un string '0'-'7', convertirlo a int.
        # 'most_active_hour' podría ser int o float.
        # 'hour_spread' y 'unique_hour_day_combinations' deberían ser numéricas.

        df_processed = patterns_df.copy()

        # Columnas a convertir a numérico (si no lo son ya)
        numeric_cols = [
            "most_active_hour",
            "hour_spread",
            "unique_hour_day_combinations",
        ]
        for col in numeric_cols:
            if col in df_processed.columns:
                df_processed[col] = pd.to_numeric(df_processed[col], errors="coerce")
            else:
                logger.warning(
                    f"Columna '{col}' no encontrada en patterns_df para gráfico radar. Se omitirá."
                )
                # Podríamos añadir una columna de ceros o manejarlo de otra forma si es crucial
                df_processed[col] = 0

        # Convertir 'most_active_weekday' (string '0'-'7') a int
        if "most_active_weekday" in df_processed.columns:
            df_processed["most_active_weekday_numeric"] = (
                pd.to_numeric(df_processed["most_active_weekday"], errors="coerce")
                .fillna(0)
                .astype(int)
            )
        else:
            logger.warning(
                "Columna 'most_active_weekday' no encontrada en patterns_df para gráfico radar. Se usará 0."
            )
            df_processed["most_active_weekday_numeric"] = 0

        # Seleccionar las top N contrapartes (ej. por 'unique_hour_day_combinations' o alguna métrica de general_stats si se pasara)
        # Por ahora, tomamos las primeras N filas del df procesado, asumiendo que ya tiene algún orden.
        # Una mejor aproximación sería unir con general_stats y ordenar por volumen o n_operaciones.
        # Para este ejemplo, usaremos 'unique_hour_day_combinations' si existe y es numérico.
        sort_col = "unique_hour_day_combinations"
        if sort_col not in df_processed.columns or not pd.api.types.is_numeric_dtype(
            df_processed[sort_col]
        ):
            logger.warning(
                f"Columna de ordenamiento '{sort_col}' no es numérica o no existe para radar. Se tomarán las primeras {top_n} filas."
            )
            top_n_df = df_processed.head(top_n)
        else:
            top_n_df = df_processed.sort_values(by=sort_col, ascending=False).head(
                top_n
            )

        if top_n_df.empty:
            logger.warning(
                "No hay datos suficientes en patterns_df después del preprocesamiento para generar radar."
            )
            return saved_paths

        # Definir las categorías para el radar.
        # Usaremos las columnas numéricas que hemos preparado.
        # Normalizaremos estos valores para que estén en una escala comparable (ej. 0-1)

        categories = [
            "Hora Más Activa (0-23)",
            "Día Más Activo (1-7, L-D)",  # Usaremos most_active_weekday_numeric
            "Dispersión Horaria (horas)",
            "Combinaciones Hora/Día Únicas",
        ]

        # Preparar datos para Plotly
        fig = go.Figure()

        for index, row in top_n_df.iterrows():
            values = []
            # 1. Hora Más Activa (normalizada, por ejemplo, sobre 24h)
            values.append(
                row["most_active_hour"] / 24.0
                if pd.notnull(row["most_active_hour"])
                else 0
            )
            # 2. Día Más Activo (normalizado, sobre 7 días)
            values.append(
                row["most_active_weekday_numeric"] / 7.0
                if pd.notnull(row["most_active_weekday_numeric"])
                else 0
            )
            # 3. Dispersión Horaria (normalizada, ej. si max spread es 23h)
            #    Para una mejor normalización, se podría calcular el max_spread del dataset
            max_hour_spread_observed = df_processed["hour_spread"].max()
            values.append(
                row["hour_spread"] / max_hour_spread_observed
                if pd.notnull(row["hour_spread"]) and max_hour_spread_observed > 0
                else 0
            )
            # 4. Combinaciones Hora/Día Únicas (normalizada, ej. sobre max combinaciones observadas)
            max_combinations_observed = df_processed[
                "unique_hour_day_combinations"
            ].max()
            values.append(
                row["unique_hour_day_combinations"] / max_combinations_observed
                if pd.notnull(row["unique_hour_day_combinations"])
                and max_combinations_observed > 0
                else 0
            )

            fig.add_trace(
                go.Scatterpolar(
                    r=values,
                    theta=categories,
                    fill="toself",
                    name=str(
                        row.get("Counterparty", f"CP_{index}")
                    ),  # Usar 'Counterparty' si existe
                )
            )

        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1])  # Rango normalizado
            ),
            showlegend=True,
            title=f"Patrones de Trading (Top {top_n}){title_suffix}",
        )

        filename = f"counterparty_trading_patterns_radar{file_identifier}.png"
        file_path = os.path.join(out_dir, filename)
        fig.write_image(file_path, width=1000, height=700)  # Guardar con Plotly
        saved_paths.append(file_path)
        logger.info(f"Radar de patrones guardado: {file_path}")

    except Exception as e:
        logger.error(f"Error generando radar de patrones: {e}")

    return saved_paths

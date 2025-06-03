import polars as pl
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)

def analyze_trading_sessions(df: pl.DataFrame, session_gap_minutes: int = 30) -> Dict[str, pl.DataFrame]:
    """
    Análisis completo de sesiones de trading basado en proximidad temporal.
    
    Args:
        df: DataFrame con operaciones P2P procesadas
        session_gap_minutes: Minutos de inactividad para considerar nueva sesión
        
    Returns:
        Diccionario con diferentes análisis de sesiones
    """
    logger.info(f"Iniciando análisis de sesiones de trading (gap: {session_gap_minutes} min)...")
    
    # Verificar columnas requeridas
    required_cols = ['Match_time_utc_dt', 'TotalPrice_num', 'Quantity_num', 'Counterparty']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        logger.warning(f"Faltan columnas para análisis de sesiones: {missing_cols}")
        return {}
    
    # Filtrar datos válidos y ordenar por tiempo
    df_sessions = df.filter(
        (pl.col('Match_time_utc_dt').is_not_null()) &
        (pl.col('TotalPrice_num').is_not_null()) &
        (pl.col('TotalPrice_num') > 0)
    ).sort('Match_time_utc_dt')
    
    if df_sessions.is_empty():
        logger.warning("No hay datos válidos para análisis de sesiones")
        return {}
    
    logger.info(f"Analizando {df_sessions.height} operaciones para identificar sesiones...")
    
    # 1. Identificar sesiones basadas en gaps temporales
    sessions_data = _identify_sessions(df_sessions, session_gap_minutes)
    
    # 2. Analizar características de sesiones
    session_stats = _analyze_session_characteristics(sessions_data)
    
    # 3. Análisis de patrones temporales de sesiones
    session_patterns = _analyze_session_patterns(sessions_data)
    
    # 4. Análisis de eficiencia de sesiones
    session_efficiency = _analyze_session_efficiency(sessions_data)
    
    # 5. Análisis de comportamiento por contraparte en sesiones
    counterparty_sessions = _analyze_counterparty_sessions(sessions_data)
    
    # 6. Análisis de distribución temporal de sesiones
    temporal_distribution = _analyze_temporal_distribution(sessions_data)
    
    logger.info("Análisis de sesiones de trading completado")
    
    return {
        'session_stats': session_stats,
        'session_patterns': session_patterns, 
        'session_efficiency': session_efficiency,
        'counterparty_sessions': counterparty_sessions,
        'temporal_distribution': temporal_distribution,
        'raw_sessions': sessions_data
    }


def _identify_sessions(df: pl.DataFrame, gap_minutes: int) -> pl.DataFrame:
    """Identifica sesiones basadas en gaps temporales."""
    logger.info("Identificando sesiones basadas en gaps temporales...")
    
    # Convertir a pandas para procesamiento temporal más fácil
    df_pandas = df.to_pandas()
    df_pandas = df_pandas.sort_values('Match_time_utc_dt').reset_index(drop=True)
    
    # Calcular diferencias temporales entre operaciones consecutivas
    df_pandas['time_diff_minutes'] = df_pandas['Match_time_utc_dt'].diff().dt.total_seconds() / 60
    
    # Identificar inicio de nueva sesión cuando gap > threshold
    df_pandas['new_session'] = (df_pandas['time_diff_minutes'] > gap_minutes) | (df_pandas['time_diff_minutes'].isna())
    
    # Asignar ID de sesión
    df_pandas['session_id'] = df_pandas['new_session'].cumsum()
    
    # Volver a polars
    df_with_sessions = pl.from_pandas(df_pandas)
    
    logger.info(f"Identificadas {df_pandas['session_id'].nunique()} sesiones de trading")
    
    return df_with_sessions


def _analyze_session_characteristics(df: pl.DataFrame) -> pl.DataFrame:
    """Analiza características generales de cada sesión."""
    logger.info("Analizando características de sesiones...")
    
    session_stats = df.group_by('session_id').agg([
        pl.count('session_id').alias('num_operations'),
        pl.sum('TotalPrice_num').alias('total_volume'),
        pl.mean('TotalPrice_num').alias('avg_volume_per_op'),
        pl.sum('Quantity_num').alias('total_quantity'),
        pl.min('Match_time_utc_dt').alias('session_start'),
        pl.max('Match_time_utc_dt').alias('session_end'),
        pl.col('Counterparty').n_unique().alias('unique_counterparties'),
        pl.col('fiat_type').mode().first().alias('dominant_fiat'),
        pl.col('asset_type').mode().first().alias('dominant_asset')
    ]).with_columns([
        # Duración de sesión en minutos
        ((pl.col('session_end') - pl.col('session_start')).dt.total_seconds() / 60).alias('duration_minutes'),
    ]).with_columns([
        # Velocidad de trading (operaciones por hora)
        (pl.col('num_operations') / (pl.col('duration_minutes') / 60).clip(lower_bound=0.01)).alias('operations_per_hour'),
        # Volumen por minuto
        (pl.col('total_volume') / pl.col('duration_minutes').clip(lower_bound=0.01)).alias('volume_per_minute')
    ]).sort('session_start')
    
    return session_stats


def _analyze_session_patterns(df: pl.DataFrame) -> pl.DataFrame:
    """Analiza patrones temporales de las sesiones."""
    logger.info("Analizando patrones temporales de sesiones...")
    
    # Añadir información temporal
    df_with_time = df.with_columns([
        pl.col('Match_time_utc_dt').dt.hour().alias('hour'),
        pl.col('Match_time_utc_dt').dt.weekday().alias('weekday'),
        pl.col('Match_time_utc_dt').dt.strftime('%Y-%m').alias('year_month')
    ])
    
    # Análisis por hora del día
    hourly_patterns = df_with_time.group_by(['session_id', 'hour']).agg([
        pl.count('session_id').alias('ops_in_hour'),
        pl.sum('TotalPrice_num').alias('volume_in_hour')
    ]).group_by('session_id').agg([
        pl.col('hour').first().alias('session_start_hour'),
        pl.col('hour').last().alias('session_end_hour'),
        pl.col('ops_in_hour').sum().alias('total_ops'),
        pl.col('volume_in_hour').sum().alias('total_volume'),
        (pl.col('hour').max() - pl.col('hour').min()).alias('hour_span')
    ])
    
    return hourly_patterns


def _analyze_session_efficiency(df: pl.DataFrame) -> pl.DataFrame:
    """Analiza la eficiencia de las sesiones."""
    logger.info("Analizando eficiencia de sesiones...")
    
    # Calcular métricas de eficiencia por sesión
    efficiency_stats = df.group_by('session_id').agg([
        pl.count('session_id').alias('num_operations'),
        pl.sum('TotalPrice_num').alias('total_volume'),
        pl.std('TotalPrice_num').alias('volume_volatility'),
        pl.col('TotalPrice_num').quantile(0.75).alias('q75_volume'),
        pl.col('TotalPrice_num').quantile(0.25).alias('q25_volume'),
        pl.min('Match_time_utc_dt').alias('session_start'),
        pl.max('Match_time_utc_dt').alias('session_end')
    ]).with_columns([
        # Duración en minutos
        ((pl.col('session_end') - pl.col('session_start')).dt.total_seconds() / 60).alias('duration_minutes'),
        # Rango intercuartílico de volúmenes
        (pl.col('q75_volume') - pl.col('q25_volume')).alias('volume_iqr')
    ]).with_columns([
        # Eficiencia: volumen por minuto de sesión
        (pl.col('total_volume') / pl.col('duration_minutes').clip(lower_bound=0.01)).alias('volume_efficiency'),
        # Consistencia: menor volatilidad = mayor consistencia
        (1 / (pl.col('volume_volatility') / pl.col('total_volume')).clip(lower_bound=0.01)).alias('consistency_score'),
        # Intensidad: operaciones por minuto
        (pl.col('num_operations') / pl.col('duration_minutes').clip(lower_bound=0.01)).alias('intensity_score')
    ])
    
    return efficiency_stats


def _analyze_counterparty_sessions(df: pl.DataFrame) -> pl.DataFrame:
    """Analiza comportamiento de contrapartes en sesiones."""
    logger.info("Analizando contrapartes en sesiones...")
    
    counterparty_session_stats = df.group_by(['Counterparty', 'session_id']).agg([
        pl.count('session_id').alias('ops_in_session'),
        pl.sum('TotalPrice_num').alias('volume_in_session'),
        pl.min('Match_time_utc_dt').alias('first_op_in_session'),
        pl.max('Match_time_utc_dt').alias('last_op_in_session')
    ]).group_by('Counterparty').agg([
        pl.count('session_id').alias('total_sessions'),
        pl.col('ops_in_session').mean().alias('avg_ops_per_session'),
        pl.col('volume_in_session').mean().alias('avg_volume_per_session'),
        pl.col('ops_in_session').max().alias('max_ops_in_session'),
        pl.col('volume_in_session').max().alias('max_volume_in_session'),
        ((pl.col('last_op_in_session') - pl.col('first_op_in_session')).dt.total_seconds() / 60).mean().alias('avg_session_duration_minutes')
    ]).sort('total_sessions', descending=True)
    
    return counterparty_session_stats


def _analyze_temporal_distribution(df: pl.DataFrame) -> pl.DataFrame:
    """Analiza la distribución temporal de sesiones."""
    logger.info("Analizando distribución temporal de sesiones...")
    
    # Información temporal por sesión
    temporal_stats = df.group_by('session_id').agg([
        pl.min('Match_time_utc_dt').alias('session_start'),
        pl.max('Match_time_utc_dt').alias('session_end'),
        pl.count('session_id').alias('num_operations'),
        pl.sum('TotalPrice_num').alias('total_volume')
    ]).with_columns([
        pl.col('session_start').dt.hour().alias('start_hour'),
        pl.col('session_start').dt.weekday().alias('start_weekday'),
        pl.col('session_start').dt.strftime('%Y-%m').alias('year_month'),
        ((pl.col('session_end') - pl.col('session_start')).dt.total_seconds() / 60).alias('duration_minutes')
    ])
    
    # Distribución por hora del día
    hourly_distribution = temporal_stats.group_by('start_hour').agg([
        pl.count('session_id').alias('num_sessions'),
        pl.sum('total_volume').alias('total_volume'),
        pl.mean('duration_minutes').alias('avg_duration'),
        pl.mean('num_operations').alias('avg_operations')
    ]).sort('start_hour')
    
    return hourly_distribution


def get_session_insights(session_data: Dict[str, pl.DataFrame]) -> Dict[str, Any]:
    """Genera insights automáticos basados en el análisis de sesiones."""
    if not session_data:
        return {}
    
    insights = {}
    
    # Insights de sesiones generales
    if 'session_stats' in session_data:
        stats = session_data['session_stats']
        if not stats.is_empty():
            insights.update({
                'total_sessions': stats.height,
                'avg_operations_per_session': stats['num_operations'].mean(),
                'avg_session_duration_minutes': stats['duration_minutes'].mean(),
                'most_productive_session_volume': stats['total_volume'].max(),
                'fastest_session_ops_per_hour': stats['operations_per_hour'].max()
            })
    
    # Insights de contrapartes
    if 'counterparty_sessions' in session_data:
        cp_stats = session_data['counterparty_sessions']
        if not cp_stats.is_empty():
            insights.update({
                'most_active_counterparty_sessions': cp_stats['total_sessions'].max(),
                'avg_sessions_per_counterparty': cp_stats['total_sessions'].mean()
            })
    
    return insights 
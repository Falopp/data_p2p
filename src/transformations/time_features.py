import polars as pl
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def process_time_features(
    df: pl.DataFrame, datetime_col: str, local_tz: str = "America/Montevideo"
) -> Optional[pl.DataFrame]:
    """
    Genera columnas de tiempo a partir de una columna UTC: convierte a datetime,
    ajusta zona horaria, y crea columnas auxiliares como hora, año, mes, día, etc.

    Args:
        df: DataFrame de entrada.
        datetime_col: Nombre de la columna UTC original.
        local_tz: Zona horaria local para conversión.

    Returns:
        DataFrame con nuevas columnas de tiempo o None si hay error.
    """
    if datetime_col not in df.columns:
        logger.warning(
            f"Columna de tiempo original '{datetime_col}' no encontrada. "
            f"No se crearán columnas de tiempo derivadas."
        )
        return None

    try:
        # Converter a datetime naive
        if not isinstance(df[datetime_col].dtype, pl.Datetime):
            df = df.with_columns(
                pl.col(datetime_col)
                .str.to_datetime(format="%Y-%m-%d %H:%M:%S", strict=True)
                .alias("_dt_naive")
            )
        else:
            df = df.with_columns(pl.col(datetime_col).alias("_dt_naive"))

        # Convertir UTC a datetime con zona y luego a zona local
        df = df.with_columns(
            pl.col("_dt_naive").dt.replace_time_zone("UTC").alias("_dt_utc")
        )
        df = df.with_columns(
            pl.col("_dt_utc").dt.convert_time_zone(local_tz).alias("Match_time_local")
        )

        # Crear columnas auxiliares
        df = df.with_columns(
            [
                pl.col("Match_time_local").dt.hour().alias("hour_local"),
                pl.col("Match_time_local").dt.strftime("%Y-%m").alias("YearMonthStr"),
                pl.col("Match_time_local").dt.year().alias("Year"),
                pl.col("Match_time_local").dt.weekday().alias("weekday_local"),
                pl.col("Match_time_local").dt.date().alias("date_local"),
            ]
        )

        # Limpiar columna intermedia y nulos
        df = df.drop("_dt_naive").drop("_dt_utc")
        initial = df.height
        df = df.drop_nulls(subset=["Match_time_local"])
        dropped = initial - df.height
        if dropped > 0:
            logger.warning(
                f"Filas eliminadas tras conversión de fecha por nulos: {dropped}"
            )

        logger.info("Procesamiento de columnas de tiempo completado.")
        return df

    except Exception as e:
        logger.error(f"Error crítico al procesar columna '{datetime_col}': {e}.")
        return None

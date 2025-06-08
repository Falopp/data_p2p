import polars as pl
import logging
from ..utils import parse_amount

logger = logging.getLogger(__name__)


def process_numeric_columns(df: pl.DataFrame) -> pl.DataFrame:
    """
    Procesa columnas numéricas: convierte cantidad, comisiones, precio y total a Float64.

    Args:
        df: DataFrame de entrada.

    Returns:
        DataFrame con nuevas columnas numéricas.
    """
    cols_map = {
        "quantity": "Quantity_num",
        "maker_fee": "MakerFee_num",
        "taker_fee": "TakerFee_num",
        "price": "Price_num",
        "total_price": "TotalPrice_num",
    }

    processed = []
    warnings = []
    for orig, new_col in cols_map.items():
        if new_col not in df.columns:
            if orig in df.columns:
                df = df.with_columns(
                    pl.col(orig)
                    .map_elements(parse_amount, return_dtype=pl.Float64)
                    .alias(new_col)
                )
                processed.append(f"{orig} -> {new_col}")
            else:
                logger.warning(
                    f"'{orig}' no encontrada al procesar numéricos. Se crea '{new_col}' con nulos."
                )
                df = df.with_columns(pl.lit(None, dtype=pl.Float64).alias(new_col))
                warnings.append(f"'{orig}' ausente, '{new_col}' con nulos.")
        else:
            processed.append(f"{new_col} (existente)")

    if processed:
        logger.info(f"Columnas numéricas procesadas: {processed}")
    if warnings:
        for w in warnings:
            logger.warning(w)
    return df

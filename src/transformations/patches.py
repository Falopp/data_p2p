import polars as pl
import logging

logger = logging.getLogger(__name__)


def patch_usdt_usd_price(df: pl.DataFrame) -> pl.DataFrame:
    """
    Corrige Price_num en casos USDT/USD dividiendo por 1000 si es mayor a 10.
    """
    cond = (
        (pl.col("asset_type") == "USDT")
        & (pl.col("fiat_type") == "USD")
        & pl.col("Price_num").is_not_null()
        & (pl.col("Price_num") > 10)
    )
    count = df.filter(cond).height
    if count > 0:
        logger.info(f"Aplicando parche USDT/USD a {count} filas de Price_num.")
        df = df.with_columns(
            pl.when(cond)
            .then(pl.col("Price_num") / 1000)
            .otherwise(pl.col("Price_num"))
            .alias("Price_num")
        )
    else:
        logger.info("No se necesitan correcciones de Price_num para USDT/USD.")
    return df


def create_total_price_usd_equivalent(df: pl.DataFrame) -> pl.DataFrame:
    """
    Crea la columna 'TotalPrice_USD_equivalent' a partir de TotalPrice_num y Price_num.
    """
    required = ["TotalPrice_num", "fiat_type", "asset_type", "Price_num"]
    if all(col in df.columns for col in required):
        df = df.with_columns(
            pl.when(pl.col("fiat_type").is_in(["USD", "USDT"]))
            .then(pl.col("TotalPrice_num"))
            .when(
                (pl.col("fiat_type") == "UYU")
                & (pl.col("asset_type") == "USDT")
                & pl.col("Price_num").is_not_null()
                & (pl.col("Price_num") != 0)
            )
            .then(pl.col("TotalPrice_num") / pl.col("Price_num"))
            .otherwise(None)
            .alias("TotalPrice_USD_equivalent")
        )
        logger.info("TotalPrice_USD_equivalent creada.")
    else:
        logger.warning(
            "Columnas para TotalPrice_USD_equivalent ausentes. Se crea con nulos."
        )
        df = df.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("TotalPrice_USD_equivalent")
        )
    return df

import polars as pl
import logging
import numpy as np

logger = logging.getLogger(__name__)


def calculate_daily_returns(prices: pl.Series) -> pl.Series:
    """Calcula los retornos diarios a partir de una serie de precios."""
    if prices.len() < 2:
        return pl.Series([], dtype=pl.Float64)
    # Retorno = (Precio_hoy / Precio_ayer) - 1
    return (prices / prices.shift(1)) - 1


def calculate_rolling_pnl(
    daily_returns: pl.Series, window_size: int, initial_investment: float = 1000.0
) -> pl.Series:
    """Calcula el P&L acumulado rodante sobre una ventana dada."""
    if daily_returns.is_empty() or daily_returns.len() < window_size:
        logger.warning(
            f"No hay suficientes datos para calcular P&L rodante con ventana {window_size}"
        )
        return pl.Series([], dtype=pl.Float64)

    # Asegurar que daily_returns es Float64
    daily_returns = daily_returns.cast(pl.Float64)

    # P&L simple basado en retornos: (1 + r1) * (1 + r2) * ... * (1 + rN)
    # Aquí calculamos el valor de la cartera rodante
    one_plus_returns = 1 + daily_returns

    # Evitar log(0) o log(negativo) reemplazando temporalmente 0 o negativos en one_plus_returns
    # con un valor muy pequeño y positivo si es necesario, aunque product() también tendría problemas.
    # Polars log() maneja 0 como -inf y negativos como NaN.
    log_one_plus_returns = one_plus_returns.log()

    sum_log_rolling = log_one_plus_returns.rolling_sum(
        window_size=window_size, min_periods=window_size
    )

    cumulative_returns_rolling = sum_log_rolling.exp()

    portfolio_value_rolling = initial_investment * cumulative_returns_rolling
    # El P&L sería el cambio en el valor de la cartera. Para simplificar, devolvemos el valor de la cartera.
    # Si se quisiera el P&L exacto, sería portfolio_value_rolling - initial_investment_at_start_of_window
    return portfolio_value_rolling.fill_null(
        strategy="forward"
    )  # Llenar nulos iniciales


def calculate_sharpe_ratio(
    daily_returns: pl.Series,
    risk_free_rate_annual: float = 0.0,
    periods_per_year: int = 252,
) -> float | None:
    """Calcula el Ratio de Sharpe anualizado a partir de retornos diarios."""
    if (
        daily_returns.is_empty()
        or daily_returns.std() == 0
        or daily_returns.std() is None
    ):
        logger.warning(
            "No se puede calcular el Ratio de Sharpe: retornos vacíos o desviación estándar cero/nula."
        )
        return None

    # Tasa libre de riesgo diaria
    risk_free_rate_daily = (1 + risk_free_rate_annual) ** (1 / periods_per_year) - 1

    excess_returns = daily_returns - risk_free_rate_daily
    mean_excess_return = excess_returns.mean()
    std_dev_excess_return = excess_returns.std()

    if std_dev_excess_return == 0 or std_dev_excess_return is None:
        logger.warning(
            "No se puede calcular el Ratio de Sharpe: desviación estándar de retornos excedentes es cero/nula."
        )
        return None

    sharpe_ratio_daily = mean_excess_return / std_dev_excess_return
    sharpe_ratio_annualized = sharpe_ratio_daily * np.sqrt(periods_per_year)

    return sharpe_ratio_annualized


# Ejemplo de uso (se puede eliminar o comentar)
if __name__ == "__main__":
    # Simular una serie de precios diarios (ej. VWAP diario)
    price_data = pl.Series("prices", [100, 102, 101, 105, 107, 103, 108, 110, 112, 109])
    dates = pl.date_range(
        pl.Date(2023, 1, 1), pl.Date(2023, 1, 10), "1d", eager=True
    ).alias("date")
    df_prices = pl.DataFrame({"date": dates, "price": price_data})

    logger.info(f"Precios de ejemplo:\n{df_prices}")

    # 1. Calcular retornos diarios
    df_prices = df_prices.with_columns(
        calculate_daily_returns(pl.col("price")).alias("daily_returns")
    )
    logger.info(f"Retornos diarios:\n{df_prices}")

    # 2. Calcular P&L rodante (ej. 3 días)
    window = 3
    df_prices = df_prices.with_columns(
        calculate_rolling_pnl(pl.col("daily_returns"), window_size=window).alias(
            f"rolling_pnl_{window}d"
        )
    )
    logger.info(f"P&L rodante ({window} días):\n{df_prices}")

    # 3. Calcular Ratio de Sharpe
    # Usaremos todos los retornos diarios disponibles para el Sharpe general
    all_daily_returns = df_prices["daily_returns"].drop_nulls()
    sharpe = calculate_sharpe_ratio(all_daily_returns, risk_free_rate_annual=0.02)
    logger.info(f"Ratio de Sharpe Anualizado: {sharpe:.4f}")

    # Para un Sharpe rodante, se aplicaría calculate_sharpe_ratio sobre ventanas rodantes de retornos.
    # Polars no tiene un rolling_apply directo tan flexible como pandas para esto con funciones custom complejas
    # que devuelven un escalar. Se podría hacer con un bucle o una expresión más compleja,
    # o calcularlo sobre la serie completa como arriba.
    # Por simplicidad, calculamos un Sharpe general y el P&L rodante.

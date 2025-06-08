import polars as pl


def apply_generic_filter(
    df: pl.DataFrame, column: str, values: list[str]
) -> pl.DataFrame:
    """
    Aplica un filtro genérico a una columna de tipo cadena.

    Args:
        df: DataFrame a filtrar.
        column: Nombre de la columna.
        values: Lista de valores a incluir.

    Returns:
        DataFrame filtrado.
    """
    if not values or column not in df.columns:
        return df
    processed = [v.strip().upper() for v in values]
    return df.filter(
        pl.col(column).str.to_uppercase().str.strip_chars().is_in(processed)
    )


def apply_filters(df: pl.DataFrame, filters: dict[str, list[str]]) -> pl.DataFrame:
    """
    Aplica múltiples filtros genéricos a un DataFrame.

    Args:
        df: DataFrame a filtrar.
        filters: Mapeo de nombre de columna a lista de valores.

    Returns:
        DataFrame filtrado.
    """
    for column, values in filters.items():
        df = apply_generic_filter(df, column, values)
    return df

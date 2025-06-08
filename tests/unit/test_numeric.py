import polars as pl
import pytest
from src.transformations.numeric import process_numeric_columns


def test_process_numeric_columns_all_present_and_missing():
    df = pl.DataFrame(
        {
            "quantity": ["10", "20.5"],
            "price": ["5", None],
        }
    )
    result = process_numeric_columns(df)
    # Columnas numéricas creadas
    assert "Quantity_num" in result.columns
    assert "Price_num" in result.columns
    assert "TotalPrice_num" in result.columns
    assert "MakerFee_num" in result.columns
    assert "TakerFee_num" in result.columns
    # Valores correctamente parseados
    assert result["Quantity_num"].to_list() == [10.0, 20.5]
    # Nulos respetados
    assert result["Price_num"][1] is None


def test_process_numeric_columns_empty_df():
    df = pl.DataFrame({})
    result = process_numeric_columns(df)
    # Solo deben crearse columnas con nulos
    for col in [
        "Quantity_num",
        "MakerFee_num",
        "TakerFee_num",
        "Price_num",
        "TotalPrice_num",
    ]:
        assert col in result.columns
        assert result[col].to_list() == [None] * result.height

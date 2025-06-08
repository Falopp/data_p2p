import polars as pl
import pytest
from src.transformations.patches import (
    patch_usdt_usd_price,
    create_total_price_usd_equivalent,
)


def test_patch_usdt_usd_price():
    df = pl.DataFrame(
        {
            "asset_type": ["USDT", "USDT"],
            "fiat_type": ["USD", "USD"],
            "Price_num": [15000.0, 5.0],
        }
    )
    result = patch_usdt_usd_price(df)
    assert result["Price_num"].to_list() == [15.0, 5.0]


def test_create_total_price_usd_equivalent():
    df = pl.DataFrame(
        {
            "TotalPrice_num": [100.0, 200.0, 300.0],
            "fiat_type": ["USD", "UYU", "UYU"],
            "asset_type": ["BTC", "USDT", "USDT"],
            "Price_num": [1.0, 2.0, 0.0],
        }
    )
    result = create_total_price_usd_equivalent(df)
    # Caso USD
    assert result["TotalPrice_USD_equivalent"][0] == 100.0
    # Caso UYU/USDT con Price_num !=0 -> 200/2
    assert result["TotalPrice_USD_equivalent"][1] == 100.0
    # Caso UYU/USDT con Price_num 0 -> None
    assert result["TotalPrice_USD_equivalent"][2] is None

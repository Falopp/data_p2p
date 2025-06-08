import polars as pl
import pytest
from src.filters import apply_generic_filter, apply_filters


def test_apply_generic_filter_no_values():
    df = pl.DataFrame({"col1": ["a", "b"]})
    result = apply_generic_filter(df, "col1", [])
    assert result.frame_equal(df)


def test_apply_generic_filter_missing_column():
    df = pl.DataFrame({"col": ["x", "y"]})
    result = apply_generic_filter(df, "col1", ["x"])
    assert result.frame_equal(df)


def test_apply_generic_filter_values():
    df = pl.DataFrame({"col": ["A", "b", "C"]})
    filtered = apply_generic_filter(df, "col", ["a", "c"])
    assert filtered.shape[0] == 2
    assert filtered.to_series("col").to_list() == ["A", "C"]


def test_apply_filters_multiple():
    df = pl.DataFrame({"f": ["usd", "eur", "usd"], "a": ["btc", "eth", "btc"]})
    filters = {"fiat_type": ["usd"], "asset_type": ["btc"]}
    # Rename df columns for test compatibility
    df = df.rename({"f": "fiat_type", "a": "asset_type"})
    result = apply_filters(df, filters)
    assert result.shape[0] == 2
    assert all(x == "usd" for x in result["fiat_type"].to_list())
    assert all(x == "btc" for x in result["asset_type"].to_list())

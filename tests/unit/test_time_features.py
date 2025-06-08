import polars as pl
from src.transformations.time_features import process_time_features


def test_process_time_features_success():
    # UTC a UTC local (sin cambio de zona)
    df = pl.DataFrame({"match_time_utc": ["2023-05-01 12:30:00"]})
    result = process_time_features(df, "match_time_utc", local_tz="UTC")
    assert result is not None
    assert "Match_time_local" in result.columns
    assert result["hour_local"][0] == 12
    assert result["Year"][0] == 2023


def test_process_time_features_missing_column():
    df = pl.DataFrame({"other": ["2023-05-01 12:30:00"]})
    result = process_time_features(df, "match_time_utc")
    assert result is None

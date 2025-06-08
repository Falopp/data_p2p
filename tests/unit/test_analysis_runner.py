import polars as pl
import argparse
import pytest
from src.main_logic import AnalysisRunner, execute_analysis as real_execute_analysis


def test_analysis_runner_calls_execute_analysis(monkeypatch):
    # Preparar un DataFrame de prueba y argumentos CLI mínimos
    df = pl.DataFrame({"col": [1, 2, 3]})
    col_map = {"col": "col"}
    config = {"some": "config"}
    cli_args = argparse.Namespace(
        out="output_path",
        log_level="INFO",
        no_annual_breakdown=False,
        year=None,
        unified_only=False,
    )
    output_dir = "output_dir"
    suffix1 = "suf1"
    suffix2 = "suf2"

    # Interceptar llamadas a execute_analysis
    called = {}

    def fake_execute_analysis(**kwargs):
        called.update(kwargs)

    # Monkeypatch del execute_analysis en el módulo
    import src.main_logic as ml

    monkeypatch.setattr(ml, "execute_analysis", fake_execute_analysis)

    # Crear y ejecutar runner
    runner = AnalysisRunner(df, col_map, config, cli_args, output_dir, suffix1, suffix2)
    runner.run()

    # Verificar que execute_analysis fue llamado con los mismos parámetros
    assert "df" in called and isinstance(called["df"], pl.DataFrame)
    assert called["col_map"] == col_map
    assert called["config"] == config
    assert called["cli_args"] == cli_args
    assert called["output_dir"] == output_dir
    assert called["clean_filename_suffix_cli"] == suffix1
    assert called["analysis_title_suffix_cli"] == suffix2

    # Restaurar execute_analysis original
    monkeypatch.setattr(ml, "execute_analysis", real_execute_analysis)

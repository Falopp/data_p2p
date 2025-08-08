#!/usr/bin/env python3
import argparse
import json
import os
from typing import Dict, Any, Tuple

import numpy as np
import polars as pl


def read_csv_if_exists(path: str) -> pl.DataFrame | None:
    return pl.read_csv(path) if os.path.exists(path) else None


def var_cvar(returns: pl.Series | None, q: float) -> Tuple[float | None, float | None]:
    if returns is None:
        return None, None
    r = returns.drop_nulls().to_numpy()
    if r.size == 0:
        return None, None
    var_val = float(np.quantile(r, 1 - q))
    tail = r[r <= var_val]
    cvar_val = float(tail.mean()) if tail.size > 0 else var_val
    return var_val, cvar_val


def compute_stats(base_tables_dir: str) -> Dict[str, Any]:
    # Core tables
    asset = read_csv_if_exists(os.path.join(base_tables_dir, "asset_stats.csv"))
    fiat = read_csv_if_exists(os.path.join(base_tables_dir, "fiat_stats.csv"))
    fees = read_csv_if_exists(os.path.join(base_tables_dir, "fees_stats.csv"))

    cp_gen = read_csv_if_exists(os.path.join(base_tables_dir, "counterparty_general_stats.csv"))
    cp_eff = read_csv_if_exists(os.path.join(base_tables_dir, "counterparty_efficiency_stats.csv"))

    sess_stats = read_csv_if_exists(os.path.join(base_tables_dir, "session_session_stats.csv"))
    sess_time = read_csv_if_exists(os.path.join(base_tables_dir, "session_temporal_distribution.csv"))

    # Risk
    risk_usd_returns = read_csv_if_exists(os.path.join(base_tables_dir, "risk_usd_daily_returns.csv"))
    risk_uyu_returns = read_csv_if_exists(os.path.join(base_tables_dir, "risk_uyu_daily_returns.csv"))
    risk_usd_summary = read_csv_if_exists(os.path.join(base_tables_dir, "risk_usd_summary.csv"))
    risk_uyu_summary = read_csv_if_exists(os.path.join(base_tables_dir, "risk_uyu_summary.csv"))

    # KPIs
    kpis: Dict[str, Any] = {}
    if fiat is not None and fiat.height > 0:
        kpis["vol_total"] = float(fiat["total_fiat"].sum())
        kpis["vol_usd"] = float(
            (fiat.filter(pl.col("fiat_type") == "USD")["total_fiat"].sum() or 0)
        )
        kpis["vol_uyu"] = float(
            (fiat.filter(pl.col("fiat_type") == "UYU")["total_fiat"].sum() or 0)
        )
    if asset is not None and "operations" in asset.columns:
        kpis["ops_total"] = int(asset["operations"].sum())
    if fees is not None and fees.height > 0:
        kpis["fees_total"] = float(fees["total_fees_collected"].sum())

    # Risk: VaR/CVaR and Sharpe/Sortino/MaxDD
    risk: Dict[str, Any] = {"USD": {}, "UYU": {}}
    if risk_usd_returns is not None and "return" in risk_usd_returns.columns:
        v95, c95 = var_cvar(risk_usd_returns["return"], 0.95)
        v99, c99 = var_cvar(risk_usd_returns["return"], 0.99)
        risk["USD"].update({"VaR95": v95, "CVaR95": c95, "VaR99": v99, "CVaR99": c99})
    if risk_uyu_returns is not None and "return" in risk_uyu_returns.columns:
        v95, c95 = var_cvar(risk_uyu_returns["return"], 0.95)
        v99, c99 = var_cvar(risk_uyu_returns["return"], 0.99)
        risk["UYU"].update({"VaR95": v95, "CVaR95": c95, "VaR99": v99, "CVaR99": c99})

    def summary_to_dict(df: pl.DataFrame | None) -> Dict[str, float | None]:
        if df is None or df.is_empty() or df.width < 2:
            return {}
        return {str(row[0]): (None if row[1] is None else float(row[1])) for row in df.iter_rows()}

    risk["USD"].update(summary_to_dict(risk_usd_summary))
    risk["UYU"].update(summary_to_dict(risk_uyu_summary))

    # Concentration and HHI (by total_volume)
    concentration: Dict[str, Any] = {"top10_volume_pct": None, "HHI": None, "top1": None}
    if cp_gen is not None and cp_gen.height > 0 and "total_volume" in cp_gen.columns:
        total = float(cp_gen["total_volume"].sum())
        if total > 0:
            top10 = cp_gen.sort("total_volume", descending=True).head(10)
            top10_sum = float(top10["total_volume"].sum())
            concentration["top10_volume_pct"] = top10_sum / total * 100.0
            # HHI on share^2
            shares = (cp_gen["total_volume"] / total).fill_null(0).to_numpy()
            concentration["HHI"] = float((shares ** 2).sum())
            # Top1
            r0 = top10.row(0, named=True)
            concentration["top1"] = {
                "Counterparty": r0["Counterparty"],
                "total_volume": float(r0["total_volume"]),
                "operations": int(r0["total_operations"]),
            }

    # Efficiency: top 5 and delta vs median
    efficiency: Dict[str, Any] = {}
    if cp_eff is not None and cp_eff.height > 0 and "efficiency_score" in cp_eff.columns:
        top5 = (
            cp_eff.sort("efficiency_score", descending=True)
            .head(5)
            .select(["Counterparty", "efficiency_score", "completion_rate", "cancellation_rate"])
        )
        efficiency["top5"] = top5.to_dict(as_series=False)
        med = cp_eff["efficiency_score"].median()
        efficiency["median_efficiency"] = None if med is None else float(med)

    # Sessions: summary and peak start hour by num_sessions
    sessions: Dict[str, Any] = {}
    if sess_stats is not None and sess_stats.height > 0:
        summary = (
            sess_stats.select(
                [
                    pl.col("num_operations").mean().alias("avg_ops_per_session"),
                    pl.col("duration_minutes").mean().alias("avg_duration_min"),
                    pl.col("operations_per_hour").mean().alias("avg_ops_per_hour"),
                    pl.col("volume_per_minute").mean().alias("avg_vol_per_min"),
                ]
            )
        )
        sessions["summary"] = summary.to_dict(as_series=False)
    if sess_time is not None and sess_time.height > 0 and "start_hour" in sess_time.columns:
        peak = sess_time.sort("num_sessions", descending=True).row(0, named=True)
        sessions["peak_hour"] = {"start_hour": int(peak["start_hour"]), "num_sessions": int(peak["num_sessions"]) }

    return {
        "kpis": kpis,
        "risk": risk,
        "concentration": concentration,
        "efficiency": efficiency,
        "sessions": sessions,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, help="Directorio base de tablas (e.g., output/total/total/completadas/tables)")
    parser.add_argument("--out", required=True, help="Ruta de salida JSON con estadísticas")
    args = parser.parse_args()

    stats = compute_stats(args.base)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"Estadísticas avanzadas guardadas en: {args.out}")


if __name__ == "__main__":
    main()



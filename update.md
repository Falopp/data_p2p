# 📈 P2P-Analysis — Roadmap de Actualización 2025-Q2

Este documento sirve como **bitácora y checklist** para implementar las mejoras propuestas (métricas avanzadas, nuevas visualizaciones, detección de patrones y reporting interactivo).
Está pensado para que **[Cursor](https://www.cursor.sh/)** pueda automatizar/seguir el progreso: basta con marcar cada casilla `- [x]` o añadir el comentario `// DONE:` (o `# DONE:`) junto al bloque de código correspondiente.

> **Cómo usar este README**
>
> 1. **Lee** cada sección y decide si la tarea aplica a tu caso.
> 2. **Implementa** el código / template requerido.
> 3. **Marca** la casilla `[x]` cuando lo hayas probado y pasado los tests.
> 4. Agrega un *commit message* del estilo `feat(metrics): add VWAP daily` o `docs(readme_update): mark TBT completed`.
>
> Cursor detectará los cambios y actualizará automáticamente la lista de pendientes.

---

## 🗂️ Estructura rápida

```
p2p-analysis/
├─ data/
├─ src/
│   ├─ analyzer.py
│   ├─ plotting.py
│   ├─ reporter.py
│   └─ …
├─ tests/
└─ README_UPDATE.md  ← (este archivo)
```

---

## 1. Métricas avanzadas

| Tarea                                                                       | Estado |
| --------------------------------------------------------------------------- | ------ |
| **1.1 VWAP diario** — calcular `vwap` con Polars y añadir al resumen anual. | - [x] |
| **1.2 High / Low intradía** con `groupby_dynamic("1d")`.                    | - [x] |
| **1.3 Time-Between-Trades (TBT)** y percentiles 5–95 %.                     | - [x] |
| **1.4 Rolling P&L + Sharpe (7 días)** — nuevo módulo `finance_utils.py`.   | - [x] |
| **1.5 Estacionalidad (STL / FFT)** en volumen.                              | - [x] |
| **1.6 Outliers con IsolationForest** — flag `--detect-outliers`.            | - [x] |
| **1.7 Índice de liquidez efectiva** (`mean_qty/median_qty`).                | - [x] |

### 💡 Tips de implementación

* Añade funciones en **`analyzer.py` → `class MetricsEngine`**.
* Expón resultados como un DataFrame adicional en `summary_dict`.
* Documenta cada métrica en el *docstring* y actualiza el report template.

---

## 2. Visualizaciones

| Tarea                                                              | Estado |
| ------------------------------------------------------------------ | ------ |
| **2.1 Sankey Fiat → Activo** con Plotly (`plot_sankey`).           | - [x] |
| **2.2 Heatmap Hora × Día** (`sns.heatmap`, `pivot_table`).         | - [x] |
| **2.3 Violín Precio vs. Método de pago**.                          | - [x] |
| **2.4 Línea YoY alineada por mes**.                                | - [x] |
| **2.5 Scatter animado precio/volumen** (`plotly.express.scatter`). | - [x] |

> **Nota:** agrega cada figura a **`plotting.py`** y usa la config `include_figures_default` para activarlas.

---

## 3. Detección de patrones & alertas

| Tarea                                                                 | Estado |
| --------------------------------------------------------------------- | ------ |
| **3.1 Whale trades (> mean + 3σ)** — lista en HTML.                   | - [x] |
| **3.2 Before/After `--event_date`** comparativo 24 h.                 | - [x] |
| **3.3 Métrica de eficiencia temporal** (si existen timestamps extra). | - [ ] <!-- PENDIENTE: Aclarar timestamps extra o definición de métrica --> |

---

## 4. Reporting interactivo

| Tarea                                                      | Estado |
| ---------------------------------------------------------- | ------ |
| **4.1 Modo `--interactive` → Plotly/Bokeh incrustado**.    | - [x] |
| **4.2 Tablas HTML DataTables.js** (`table.datatable`).     | - [x] |
| **4.3 Export XLSX multi-hoja** en carpeta `output/`.       | - [x] |
| **4.4 Dashboard opcional Streamlit** (`streamlit_app.py`). | - [x] |

---

## 5. Guía rápida de marcado (Cursor-friendly)

* **Casillas:** Mantén la sintaxis exacta `- [ ]` ➜ pendiente  **|** `- [x]` ➜ hecho.
* **Código:** Usa comentarios `# TODO:` o `# DONE:` arriba de bloques modificados.
* **Commits atómicos:** un feature ↔ un commit.
* **Tests:** añade tests unitarios mínimos en `tests/test_metrics.py`, `tests/test_plots.py`, etc.

---

## 6. Ejecución y pruebas

```bash
# Instalar deps (añade las nuevas en requirements.txt)
$ pip install -r requirements.txt

# Análisis clásico
$ python src/app.py data/p2p.csv --year 2024

# Activar métricas nuevas + interactive
$ python src/app.py data/p2p.csv --all-years --detect-outliers --interactive

# Dashboard
$ streamlit run streamlit_app.py
```

---

## 7. Changelog

Cada vez que completes una tarea, añade una entrada breve:

```
### [yyyy-mm-dd] Nombre o PR
- ✅ 1.3 TBT metrics added
- ✅ 2.2 Heatmap day×hour implemented
```
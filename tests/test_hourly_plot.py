import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import pandas as pd
from src.plotting import plot_hourly

# Crear datos sintéticos: operaciones aumenta a las horas punta
data = [i % 24 for i in range(100)]
counts = pd.Series(pd.value_counts(pd.Series(data)))

output_dir = 'output_test/figures'
# Ejecutar plot_hourly
path = plot_hourly(counts, output_dir, title_suffix=' (Test)', file_identifier='_test')
print('Hourly plot generado:', path)
assert path is not None and os.path.exists(path), f"Hourly plot no generado o no existe: {path}" 
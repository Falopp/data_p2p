import os
import sys
# Permitir importar el paquete src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

import pandas as pd
from src.counterparty_plotting import plot_vip_tier_distribution

# Crear directorio de test
output_dir = 'output_test/figures'
# Datos sintéticos de vip_tier
tiers = ['Standard'] * 50 + ['Bronze'] * 45 + ['Silver'] * 30 + ['Gold'] * 10
vip_df = pd.DataFrame({'vip_tier': tiers})

# Ejecutar la función de plot
paths = plot_vip_tier_distribution(vip_df, output_dir, title_suffix=' (Test)', file_identifier='_test')

print('Archivos generados:', paths)
# Verificación manual: el archivo debe existir en el sistema de ficheros
for path in paths:
    assert os.path.exists(path), f"No se encontró el archivo generado: {path}" 
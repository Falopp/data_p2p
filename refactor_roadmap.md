# Hoja de Ruta para la Refactorización de `src/app.py`

Este documento detalla los pasos planificados para refactorizar y optimizar el script `src/app.py`.

## ✅ I. Alcance General de la Refactorización
- [X] Confirmado: `src/app.py` actuará como punto de entrada CLI y orquestador principal.
- [X] Tarea: Asegurar que la lógica de negocio compleja permanezca delegada a módulos como `analyzer.py`, `main_logic.py`.

## 📜 II. Legibilidad y Estilo del Código (PEP 8)
- [X] **Formato Homogéneo:**
    - [X] Aplicar `black` para formato automático.
    - [X] Revisar manualmente indentación (4 espacios), espaciado y saltos de línea.
    - [X] Verificar longitud de líneas (79-99 caracteres).
- [X] **Nomenclatura Clara y Consistente:**
    - [X] Revisar y renombrar variables a `snake_case` (ej. `column_map`, `cli_filtered_df`).
    - [X] Identificar y renombrar constantes a nivel de módulo a `UPPER_SNAKE_CASE`.
- [X] **Organización de Importaciones:**
    - [X] Aplicar `isort` para organizar importaciones.
    - [X] Agrupar en: 1. Librerías estándar, 2. Librerías de terceros, 3. Módulos locales.
    - [X] Eliminar importaciones no utilizadas directamente en `src/app.py`.

## 🧱 III. Modularidad y Organización del Código
- [X] **Extracción de Lógica de `main()`:**
    - [X] Encapsular lectura de CSV, renombrado de columnas y filtros CLI en una función auxiliar privada (ej. `_load_and_preprocess_input_data`).
- [X] **Jerarquía y Estructura del Archivo:**
    - [X] Asegurar el orden: shebang, docstring módulo, imports, logger, constantes, funciones aux, `main()`, `if __name__ == "__main__":`.
- [X] **Principios SOLID:**
    - [X] Asegurar Responsabilidad Única (SRP) para funciones extraídas.

## 🚀 IV. Eficiencia y Uso Idiomático de Polars
- [X] **Operaciones con Polars en `app.py`:**
    - [X] Confirmar adecuación de `infer_schema_length=10000` en `pl.read_csv`.
    - [X] Mantener uso idiomático de `.filter()` y `.rename()`.
    - [X] Revisar el uso de `.clone()` para evitar efectos secundarios.
- [X] **Evitar Bucles Explícitos:**
    - [X] Confirmar que no se usan bucles de Python para iterar sobre filas del DataFrame.

## 🛡️ V. Manejo de Errores y Validaciones
- [X] **Bloques `try-except` Específicos para Lectura de CSV:**
    - [X] Capturar `FileNotFoundError`.
    - [X] Capturar `polars.exceptions.NoDataError`.
    - [X] Capturar `polars.exceptions.SchemaError`.
    - [X] Capturar `polars.exceptions.ComputeError`.
    - [X] Mantener `except Exception as e:` con `logger.exception(e)`.
- [X] **Mensajes de Error Claros:**
    - [X] Revisar y mejorar mensajes de log y error para incluir contexto.
- [X] **Validaciones Adicionales:**
    - [X] Considerar `type=argparse.FileType('r')` para el CSV de entrada.
    - [X] Asegurar consistencia en la verificación de disponibilidad de columnas post-mapeo.
- [X] **Manejo de DataFrames Vacíos:**
    - [X] Confirmar que `exit(0)` es el comportamiento deseado para DataFrames vacíos post-filtros.

## 📚 VI. Documentación y Comentarios
- [X] **Docstrings (Formato Google o NumPy):**
    - [X] Actualizar docstring del módulo `src/app.py`.
    - [X] Asegurar docstrings claros para `main()` y nuevas funciones públicas (descripción, Args, Returns, Raises).
- [X] **Comentarios Internos:**
    - [X] Eliminar comentarios obvios o redundantes.
    - [X] Añadir comentarios para lógica compleja o decisiones no evidentes (ej. propósito de la llamada inicial a `analyze()`).
    - [X] Eliminar comentarios de sección si el código es claro.

## 🧹 VII. Limpieza General del Código
- [X] **Código Muerto o Comentado:**
    - [X] Eliminar fragmentos de código comentados innecesarios.
    - [X] Eliminar comentarios placeholder (ej. `--- Funciones Auxiliares (Helpers) ---`).
- [X] **Variables No Utilizadas:**
    - [X] Usar linter para identificar y eliminar variables no utilizadas.
- [X] **Simplificación:**
    - [X] Buscar oportunidades para simplificar expresiones o bloques sin perder claridad.

## ⚙️ VIII. Configuración y Logging
- [X] **Uso del Logger:**
    - [X] Mantener `logger = logging.getLogger(__name__)`.
- [X] **Niveles de Logging:**
    - [X] Asegurar uso apropiado de `DEBUG`, `INFO`, `WARNING`, `ERROR`/`CRITICAL`.
- [X] **Carga de Configuración:**
    - [X] Confirmado: Carga centralizada en `config_loader.py` es correcta.

## 🚀 IX. Función `main()` y Flujo de Ejecución
- [X] **Orquestación Clara en `main()`:**
    - [X] Asegurar flujo lógico: parseo args -> carga config -> carga/pre-proceso datos -> llamada `analyze` base -> llamada `run_analysis_pipeline` -> mensaje final.
- [X] **Delegación de Lógica de Negocio:**
    - [X] Confirmar que `main()` delega análisis intensivo.
- [X] **Bloque de Guardia:**
    - [X] Mantener `if __name__ == "__main__":`.

## ✨ X. Consideraciones para Tipado Estático (Type Hinting)
- [X] Añadir type hints a todas las signaturas de funciones en `src/app.py`.
- [X] Usar `from typing import ...` si es necesario.
- [~] Ejecutar `mypy` para verificar consistencia. (Errores menores de importaciones relativas resueltos)

## 📝 XI. Guía para un Refactor Exitoso (Criterios y Herramientas)
- [X] **Formato y Estilo (PEP 8):**
    - [X] Usar `black`, `isort`, `flake8`. Meta: sin errores.
- [~] **Tipado Estático:**
    - [~] Usar `mypy`. Meta: sin advertencias relevantes. (Errores menores de módulos relativos)
- [X] **Rendimiento:**
    - [X] Monitorear tiempo de ejecución. Meta: comparable o mejor.
- [X] **Control de Versiones:**
    - [X] Realizar commits atómicos y descriptivos.

## 🎯 Resultados de la Refactorización

### ✅ Mejoras Implementadas:
1. **Modularización Completa**: Se extrajo la lógica de carga y filtrado de `main()` a funciones específicas con responsabilidad única
2. **Funciones Auxiliares Especializadas**: 
   - `_load_csv_with_schema_override()`: Carga de CSV con esquema personalizado
   - `_rename_columns_from_config()`: Renombrado de columnas
   - `_apply_*_filter()`: Funciones específicas para cada tipo de filtro
   - `_load_and_preprocess_input_data()`: Orquestador de carga y pre-procesamiento
3. **Docstrings Mejorados**: Formato Google Style con Args, Returns, Raises detallados
4. **Manejo de Errores Robusto**: Captura específica de excepciones de Polars con mensajes contextuales
5. **Type Hints Completos**: Todas las funciones tienen anotaciones de tipo
6. **Cumplimiento PEP 8**: Código formateado con black, isort y validado con flake8
7. **Mensajes de Log Mejorados**: Contexto claro y conciso en todos los mensajes
8. **Estructura Limpia**: Orden lógico de imports, constantes, funciones y main()

### 📊 Métricas de Calidad:
- ✅ **Black**: Formateo automático aplicado
- ✅ **Flake8**: Sin errores de estilo PEP 8
- ✅ **Isort**: Importaciones organizadas correctamente
- 🟡 **MyPy**: Errores menores de importaciones relativas (esperado en módulos)

### 🔄 Beneficios Obtenidos:
- **Mantenibilidad**: Funciones pequeñas y especializadas facilitan modificaciones
- **Testabilidad**: Cada función puede ser testeada independientemente
- **Legibilidad**: Código autodocumentado con docstrings claros
- **Robustez**: Manejo de errores específico para cada caso
- **Escalabilidad**: Estructura modular permite extensiones futuras 
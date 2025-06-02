# Hoja de Ruta para la Refactorización de `src/app.py`

Este documento detalla los pasos planificados para refactorizar y optimizar el script `src/app.py`.

## ✅ I. Alcance General de la Refactorización
- [X] Confirmado: `src/app.py` actuará como punto de entrada CLI y orquestador principal.
- [ ] Tarea: Asegurar que la lógica de negocio compleja permanezca delegada a módulos como `analyzer.py`, `main_logic.py`.

## 📜 II. Legibilidad y Estilo del Código (PEP 8)
- [ ] **Formato Homogéneo:**
    - [ ] Aplicar `black` para formato automático.
    - [ ] Revisar manualmente indentación (4 espacios), espaciado y saltos de línea.
    - [ ] Verificar longitud de líneas (79-99 caracteres).
- [ ] **Nomenclatura Clara y Consistente:**
    - [ ] Revisar y renombrar variables a `snake_case` (ej. `column_map`, `cli_filtered_df`).
    - [ ] Identificar y renombrar constantes a nivel de módulo a `UPPER_SNAKE_CASE`.
- [ ] **Organización de Importaciones:**
    - [ ] Aplicar `isort` para organizar importaciones.
    - [ ] Agrupar en: 1. Librerías estándar, 2. Librerías de terceros, 3. Módulos locales.
    - [ ] Eliminar importaciones no utilizadas directamente en `src/app.py`.

## 🧱 III. Modularidad y Organización del Código
- [ ] **Extracción de Lógica de `main()`:**
    - [ ] Encapsular lectura de CSV, renombrado de columnas y filtros CLI en una función auxiliar privada (ej. `_load_and_preprocess_input_data`).
- [ ] **Jerarquía y Estructura del Archivo:**
    - [ ] Asegurar el orden: shebang, docstring módulo, imports, logger, constantes, funciones aux, `main()`, `if __name__ == "__main__":`.
- [ ] **Principios SOLID:**
    - [ ] Asegurar Responsabilidad Única (SRP) para funciones extraídas.

## 🚀 IV. Eficiencia y Uso Idiomático de Polars
- [ ] **Operaciones con Polars en `app.py`:**
    - [ ] Confirmar adecuación de `infer_schema_length=10000` en `pl.read_csv`.
    - [ ] Mantener uso idiomático de `.filter()` y `.rename()`.
    - [ ] Revisar el uso de `.clone()` para evitar efectos secundarios.
- [ ] **Evitar Bucles Explícitos:**
    - [ ] Confirmar que no se usan bucles de Python para iterar sobre filas del DataFrame.

## 🛡️ V. Manejo de Errores y Validaciones
- [ ] **Bloques `try-except` Específicos para Lectura de CSV:**
    - [ ] Capturar `FileNotFoundError`.
    - [ ] Capturar `polars.exceptions.NoDataError`.
    - [ ] Capturar `polars.exceptions.SchemaError`.
    - [ ] Capturar `polars.exceptions.ComputeError`.
    - [ ] Mantener `except Exception as e:` con `logger.exception(e)`.
- [ ] **Mensajes de Error Claros:**
    - [ ] Revisar y mejorar mensajes de log y error para incluir contexto.
- [ ] **Validaciones Adicionales:**
    - [ ] Considerar `type=argparse.FileType('r')` para el CSV de entrada.
    - [ ] Asegurar consistencia en la verificación de disponibilidad de columnas post-mapeo.
- [ ] **Manejo de DataFrames Vacíos:**
    - [ ] Confirmar que `exit(0)` es el comportamiento deseado para DataFrames vacíos post-filtros.

## 📚 VI. Documentación y Comentarios
- [ ] **Docstrings (Formato Google o NumPy):**
    - [ ] Actualizar docstring del módulo `src/app.py`.
    - [ ] Asegurar docstrings claros para `main()` y nuevas funciones públicas (descripción, Args, Returns, Raises).
- [ ] **Comentarios Internos:**
    - [ ] Eliminar comentarios obvios o redundantes.
    - [ ] Añadir comentarios para lógica compleja o decisiones no evidentes (ej. propósito de la llamada inicial a `analyze()`).
    - [ ] Eliminar comentarios de sección si el código es claro.

## 🧹 VII. Limpieza General del Código
- [ ] **Código Muerto o Comentado:**
    - [ ] Eliminar fragmentos de código comentados innecesarios.
    - [ ] Eliminar comentarios placeholder (ej. `--- Funciones Auxiliares (Helpers) ---`).
- [ ] **Variables No Utilizadas:**
    - [ ] Usar linter para identificar y eliminar variables no utilizadas.
- [ ] **Simplificación:**
    - [ ] Buscar oportunidades para simplificar expresiones o bloques sin perder claridad.

## ⚙️ VIII. Configuración y Logging
- [ ] **Uso del Logger:**
    - [ ] Mantener `logger = logging.getLogger(__name__)`.
- [ ] **Niveles de Logging:**
    - [ ] Asegurar uso apropiado de `DEBUG`, `INFO`, `WARNING`, `ERROR`/`CRITICAL`.
- [ ] **Carga de Configuración:**
    - [ ] Confirmado: Carga centralizada en `config_loader.py` es correcta.

## 🚀 IX. Función `main()` y Flujo de Ejecución
- [ ] **Orquestación Clara en `main()`:**
    - [ ] Asegurar flujo lógico: parseo args -> carga config -> carga/pre-proceso datos -> llamada `analyze` base -> llamada `run_analysis_pipeline` -> mensaje final.
- [ ] **Delegación de Lógica de Negocio:**
    - [ ] Confirmar que `main()` delega análisis intensivo.
- [ ] **Bloque de Guardia:**
    - [ ] Mantener `if __name__ == "__main__":`.

## ✨ X. Consideraciones para Tipado Estático (Type Hinting)
- [ ] Añadir type hints a todas las signaturas de funciones en `src/app.py`.
- [ ] Usar `from typing import ...` si es necesario.
- [ ] Ejecutar `mypy` para verificar consistencia.

## 📝 XI. Guía para un Refactor Exitoso (Criterios y Herramientas)
- [ ] **Formato y Estilo (PEP 8):**
    - [ ] Usar `black`, `isort`, `flake8`. Meta: sin errores.
- [ ] **Tipado Estático:**
    - [ ] Usar `mypy`. Meta: sin advertencias relevantes.
- [ ] **Rendimiento:**
    - [ ] Monitorear tiempo de ejecución. Meta: comparable o mejor.
- [ ] **Control de Versiones:**
    - [ ] Realizar commits atómicos y descriptivos. 
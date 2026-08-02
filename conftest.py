"""Configuração de teste.

Os módulos de `src/` importam `pyspark` no topo, mas os testes de unidade cobrem
apenas FÓRMULAS PURAS (parser de tags, limiares, derivação de metadados, mapa de
custo por job, constantes) — nada que precise de Spark. Para importar esses
módulos sem uma instalação de PySpark/Java, instalamos um STUB mínimo de pyspark.
Se o PySpark real estiver instalado, o stub não é aplicado.
"""
import os
import sys
import types

# Garante que `import src...` funcione a partir da raiz do repo.
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def _install_pyspark_stub() -> None:
    try:
        import pyspark  # noqa: F401  (PySpark real disponível — não faz stub)
        return
    except Exception:
        pass

    pyspark = types.ModuleType("pyspark")
    sql = types.ModuleType("pyspark.sql")
    functions = types.ModuleType("pyspark.sql.functions")

    class _Column:
        pass

    class SparkSession:
        pass

    class DataFrame:
        pass

    sql.SparkSession = SparkSession
    sql.DataFrame = DataFrame
    sql.Column = _Column

    def _factory(name):
        def _f(*args, **kwargs):
            return _Column()
        _f.__name__ = name
        return _f

    def _module_getattr(name):
        # Qualquer função Spark importada (col, when, sum, current_timestamp, ...)
        # vira um callable inócuo — os testes não a exercitam.
        return _factory(name)

    functions.__getattr__ = _module_getattr

    pyspark.sql = sql
    sys.modules["pyspark"] = pyspark
    sys.modules["pyspark.sql"] = sql
    sys.modules["pyspark.sql.functions"] = functions


_install_pyspark_stub()

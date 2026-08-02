"""Testes dos limiares de benchmark (heurística interna) — sem Spark."""
from src.utils.benchmark_calculator import (
    get_benchmark_level,
    BENCHMARK_METRICS,
    BENCHMARK_SOURCE,
)


def test_niveis_metrica_maior_e_melhor():
    # cluster_utilization: quanto MAIOR, melhor (reverse=False)
    assert get_benchmark_level(0.85, "cluster_utilization") == "excellent"
    assert get_benchmark_level(0.65, "cluster_utilization") == "good"
    assert get_benchmark_level(0.45, "cluster_utilization") == "average"
    assert get_benchmark_level(0.10, "cluster_utilization") == "poor"


def test_niveis_metrica_menor_e_melhor_reverse():
    # cost_per_tb: quanto MENOR, melhor (reverse=True)
    assert get_benchmark_level(40.0, "cost_per_tb", reverse=True) == "excellent"
    assert get_benchmark_level(90.0, "cost_per_tb", reverse=True) == "good"
    assert get_benchmark_level(150.0, "cost_per_tb", reverse=True) == "average"
    assert get_benchmark_level(999.0, "cost_per_tb", reverse=True) == "poor"


def test_limiares_de_fronteira_sao_inclusivos():
    th = BENCHMARK_METRICS["job_success_rate"]
    assert get_benchmark_level(th["excellent"], "job_success_rate") == "excellent"
    assert get_benchmark_level(th["good"], "job_success_rate") == "good"


def test_estrutura_dos_limiares():
    for metric, faixas in BENCHMARK_METRICS.items():
        assert set(faixas) == {"excellent", "good", "average", "poor"}


def test_fonte_nao_alega_industria():
    # Honestidade: o rótulo deve se declarar heurística interna e negar
    # explicitamente ser benchmark de indústria.
    fonte = BENCHMARK_SOURCE.lower()
    assert "heurística interna" in fonte
    assert "não é benchmark de indústria" in fonte

"""Testes das constantes de custo (cost_estimator e roi_estimator) — sem Spark."""
from src.analyzers.cost_estimator import DBU_RATES
from src.auditors import roi_estimator as roi


def test_dbu_rates_cobre_as_tres_clouds():
    assert set(DBU_RATES) == {"azure", "aws", "gcp"}


def test_dbu_rates_tem_todos_os_skus_positivos():
    esperado = {"compute", "all_purpose", "jobs", "sql_compute", "sql_serverless"}
    for cloud, cfg in DBU_RATES.items():
        rates = cfg["standard"]
        assert set(rates) == esperado, cloud
        for sku, valor in rates.items():
            assert isinstance(valor, (int, float)) and valor > 0, (cloud, sku)


def test_roi_constantes_de_custo():
    assert roi.HOURLY_COST_PER_WORKER_USD > 0
    assert roi.STORAGE_COST_PER_GB_MONTH_USD > 0
    assert roi.HOURLY_COST_PER_JOB_RUN_USD > 0
    assert roi.MONTHS_PER_YEAR == 12

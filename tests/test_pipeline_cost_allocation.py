"""Testes da derivação heurística de pipeline/produto/SLA — sem Spark."""
from src.utils.pipeline_cost_allocation import _derive_pipeline_meta


def test_deriva_pipeline_e_produto_dos_separadores():
    meta = _derive_pipeline_meta("vendas_diario", 1.0)
    assert meta["pipeline_name"] == "vendas"
    meta2 = _derive_pipeline_meta("produtoA-etl", 1.0)
    assert meta2["product_name"] == "produtoA"


def test_sem_separador_cai_para_indefinido_nao_repete_o_nome():
    meta = _derive_pipeline_meta("jobsemseparador", 1.0)
    assert meta["pipeline_name"] == "(indefinido)"
    assert meta["product_name"] == "(indefinido)"


def test_nome_none_ou_vazio_nao_quebra():
    # Antes: job_name.split(...) estourava AttributeError com nome None.
    for nome in (None, "", "   "):
        meta = _derive_pipeline_meta(nome, 1.0)
        assert meta["pipeline_name"] == "(sem_nome)"
        assert meta["product_name"] == "(sem_nome)"


def test_sla_tier_por_duracao():
    assert _derive_pipeline_meta("x_y", 0.2)["sla_tier"] == "fast"
    assert _derive_pipeline_meta("x_y", 2.0)["sla_tier"] == "standard"
    assert _derive_pipeline_meta("x_y", 6.0)["sla_tier"] == "slow"
    assert _derive_pipeline_meta("x_y", None)["sla_tier"] == "fast"  # 0.0 -> fast

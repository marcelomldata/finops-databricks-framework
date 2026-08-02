"""Testes das fórmulas puras de alocação de custo (sem Spark)."""
from types import SimpleNamespace

from src.utils.cost_allocation import (
    parse_tags,
    _build_cluster_cost_map,
    _map_job_costs,
)


def test_parse_tags_json_puro():
    tags = parse_tags('{"cost_center": "CC1", "business_unit": "BU"}')
    assert tags["cost_center"] == "CC1"
    assert tags["business_unit"] == "BU"


def test_parse_tags_repr_python_com_aspas_simples_true_none():
    # Repr de dict Python NÃO é JSON válido — o parser antigo (.replace) e um
    # json.loads simples quebrariam aqui.
    tags = parse_tags("{'cost_center': 'CC2', 'owner': None, 'project': 'P'}")
    assert tags["cost_center"] == "CC2"
    assert tags["project"] == "P"
    assert tags["owner"] == ""  # None normaliza para vazio


def test_parse_tags_valor_com_apostrofo():
    # O .replace("'", '"') antigo corrompia este valor; robusto agora.
    tags = parse_tags("{'owner': \"O'Brien\", 'cost_center': 'CC'}")
    assert tags["owner"] == "O'Brien"
    assert tags["cost_center"] == "CC"


def test_parse_tags_aliases_camelcase():
    tags = parse_tags('{"CostCenter": "X", "BusinessUnit": "Y", "DataDomain": "Z"}')
    assert tags["cost_center"] == "X"
    assert tags["business_unit"] == "Y"
    assert tags["data_domain"] == "Z"


def test_parse_tags_dict_ja_desserializado():
    tags = parse_tags({"Project": "Zeta"})
    assert tags["project"] == "Zeta"


def test_parse_tags_entradas_vazias_ou_invalidas():
    for entrada in (None, "", "null", "{}", "not a dict", "[1,2,3]", 42):
        tags = parse_tags(entrada)
        assert tags == {
            "cost_center": "", "business_unit": "", "data_domain": "",
            "project": "", "owner": "",
        }


def test_build_cluster_cost_map():
    rows = [
        SimpleNamespace(cluster_id="c-1", estimated_monthly_cost=100.0, estimated_dbu_cost=10.0),
        SimpleNamespace(cluster_id="c-2", estimated_monthly_cost=None, estimated_dbu_cost=None),
        SimpleNamespace(cluster_id=None, estimated_monthly_cost=5.0, estimated_dbu_cost=1.0),
    ]
    cmap = _build_cluster_cost_map(rows)
    assert cmap["c-1"] == {"monthly": 100.0, "dbu": 10.0}
    assert cmap["c-2"] == {"monthly": 0.0, "dbu": 0.0}  # None -> 0.0
    assert None not in cmap and "None" not in cmap  # cluster sem id é ignorado


def test_map_job_costs_bug_nao_e_mais_sempre_zero():
    cmap = {"c-1": {"monthly": 100.0, "dbu": 10.0}, "c-2": {"monthly": 40.0, "dbu": 4.0}}
    runs = [
        SimpleNamespace(job_id=1, cluster_instance="{'cluster_id': 'c-1'}"),
        SimpleNamespace(job_id=1, cluster_instance="{'cluster_id': 'c-1'}"),  # 2ª run, mesmo cluster
        SimpleNamespace(job_id=1, cluster_instance="{'cluster_id': 'c-2'}"),  # outro cluster
        SimpleNamespace(job_id=2, cluster_instance="{'cluster_id': 'c-2'}"),
    ]
    jc = _map_job_costs(runs, cmap)
    # c-1 é só do job 1 (custo cheio); c-2 é compartilhado job 1+2 => RATEADO 50/50.
    # job 1: c-1 (100/10) + metade de c-2 (20/2) = 120 / 12
    assert jc["1"] == {"monthly": 120.0, "dbu": 12.0}
    # job 2: metade de c-2 (rateio, não o custo cheio de 40) = 20 / 2
    assert jc["2"] == {"monthly": 20.0, "dbu": 2.0}


def test_map_job_costs_rateio_nao_estoura_o_custo_do_cluster():
    # Regressão apontada em revisão: cluster compartilhado por 2 jobs não pode
    # somar 2× o próprio custo. A soma das parcelas = custo do cluster.
    cmap = {"c-1": {"monthly": 100.0, "dbu": 10.0}}
    runs = [
        SimpleNamespace(job_id=1, cluster_instance="{'cluster_id': 'c-1'}"),
        SimpleNamespace(job_id=2, cluster_instance="{'cluster_id': 'c-1'}"),
    ]
    jc = _map_job_costs(runs, cmap)
    assert jc["1"] == {"monthly": 50.0, "dbu": 5.0}
    assert jc["2"] == {"monthly": 50.0, "dbu": 5.0}
    assert jc["1"]["monthly"] + jc["2"]["monthly"] == 100.0  # não 200


def test_map_job_costs_casa_por_igualdade_nao_substring():
    # Bug antigo: 'c-1' casava DENTRO de 'c-12' (substring). Agora é igualdade.
    cmap = {"c-12": {"monthly": 80.0, "dbu": 8.0}}
    runs = [SimpleNamespace(job_id=5, cluster_instance="{'cluster_id': 'c-1'}")]
    jc = _map_job_costs(runs, cmap)
    assert jc == {}  # 'c-1' != 'c-12'


def test_map_job_costs_cluster_instance_id_puro():
    # cluster_instance pode vir como o id puro (não só como repr de dict).
    cmap = {"c-1": {"monthly": 60.0, "dbu": 6.0}}
    runs = [SimpleNamespace(job_id=9, cluster_instance="c-1")]
    jc = _map_job_costs(runs, cmap)
    assert jc["9"] == {"monthly": 60.0, "dbu": 6.0}


def test_map_job_costs_sem_cluster_casado():
    cmap = {"c-9": {"monthly": 10.0, "dbu": 1.0}}
    runs = [
        SimpleNamespace(job_id=7, cluster_instance="{'cluster_id': 'inexistente'}"),
        SimpleNamespace(job_id=8, cluster_instance=None),
    ]
    jc = _map_job_costs(runs, cmap)
    assert jc == {}  # nada casou -> dict vazio (chamador usa 0.0 como fallback)

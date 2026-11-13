"""
test_zabbix_upsert.py — Testes da lógica de upsert do configurar_zabbix.py.
"""

import pytest

from configurar_zabbix import (
    VT_FLOAT,
    VT_TEXT,
    VT_UNSIGNED,
    upsert_group,
    upsert_host,
    upsert_master_item,
    upsert_dependent_item,
)


# ---------- GRUPO ----------
def test_upsert_group_cria_se_nao_existe(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [],
        {"groupids": ["42"]},
    ]
    gid = upsert_group(zabbix_mock, "CPD")
    assert gid == "42"
    assert zabbix_mock.call.call_count == 2
    args, _ = zabbix_mock.call.call_args_list[1]
    assert args[0] == "hostgroup.create"


def test_upsert_group_nao_duplica(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [{"groupid": "42"}],
    ]
    gid = upsert_group(zabbix_mock, "CPD")
    assert gid == "42"
    assert zabbix_mock.call.call_count == 1
    args, _ = zabbix_mock.call.call_args_list[0]
    assert args[0] == "hostgroup.get"


# ---------- HOST ----------
def test_upsert_host_cria_se_nao_existe(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [],
        {"hostids": ["10683"]},
    ]
    hid = upsert_host(zabbix_mock, "esp32-cpd", "Rack CPD", "42")
    assert hid == "10683"
    args, _ = zabbix_mock.call.call_args_list[1]
    assert args[0] == "host.create"


def test_upsert_host_atualiza_se_existe(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [{"hostid": "10683"}],
        {},
    ]
    hid = upsert_host(zabbix_mock, "esp32-cpd", "Rack CPD", "42")
    assert hid == "10683"
    args, _ = zabbix_mock.call.call_args_list[1]
    assert args[0] == "host.update"


# ---------- ITEM MESTRE ----------
def test_upsert_master_item_cria(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [],
        {"itemids": ["50740"]},
    ]
    iid = upsert_master_item(zabbix_mock, "10683")
    assert iid == "50740"
    args, _ = zabbix_mock.call.call_args_list[1]
    assert args[0] == "item.create"


def test_upsert_master_item_nao_envia_preprocessing(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [{"itemid": "50740"}],
        {},
    ]
    upsert_master_item(zabbix_mock, "10683")
    args, _ = zabbix_mock.call.call_args_list[1]
    params = args[1]
    assert "preprocessing" not in params


# ---------- ITENS DEPENDENTES ----------
@pytest.mark.parametrize(
    "value_type,trends_esperado",
    [
        (VT_FLOAT, "365d"),
        (VT_TEXT, "0"),
        (VT_UNSIGNED, "0"),
    ],
)
def test_trends_por_tipo(zabbix_mock, value_type, trends_esperado):
    zabbix_mock.call.side_effect = [
        [],
        {"itemids": ["1"]},
    ]
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", value_type, "", "$.campo"
    )
    args, _ = zabbix_mock.call.call_args_list[1]
    params = args[1]
    assert params["trends"] == trends_esperado


def test_upsert_item_nao_envia_hostid_no_update(zabbix_mock):
    zabbix_mock.call.side_effect = [
        [{"itemid": "1"}],
        {},
    ]
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", VT_FLOAT, "C", "$.campo"
    )
    args, _ = zabbix_mock.call.call_args_list[1]
    params = args[1]
    assert "hostid" not in params
    assert "master_itemid" not in params


def test_upsert_item_nao_duplica(zabbix_mock):
    """Rodar 2x o mesmo item não cria duplicado.

    A segunda chamada deve usar item.update (não item.create).
    Como a função faz item.get + item.update, a ÚLTIMA chamada é o update.
    """
    # Primeira chamada: não existe -> item.get + item.create
    zabbix_mock.call.side_effect = [
        [],  # item.get (vazio)
        {"itemids": ["1"]},  # item.create
    ]
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", VT_FLOAT, "C", "$.campo"
    )

    # Limpa o mock para a segunda chamada
    zabbix_mock.call.reset_mock()
    zabbix_mock.call.side_effect = [
        [{"itemid": "1"}],  # item.get (encontrou)
        {},  # item.update
    ]
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", VT_FLOAT, "C", "$.campo"
    )

    # Verifica que a ÚLTIMA chamada foi item.update
    args, _ = zabbix_mock.call.call_args_list[-1]
    assert args[0] == "item.update", f"Esperado item.update, mas foi {args[0]}"

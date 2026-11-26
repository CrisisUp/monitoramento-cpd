#!/usr/bin/env python3
"""Cria os arquivos de teste do projeto."""

import os

BASE = "/Users/cristiano/Desktop/monitoramento-cpd"
TESTS = os.path.join(BASE, "tests")
os.makedirs(TESTS, exist_ok=True)

# ============================================================
# conftest.py
# ============================================================
conftest = '''"""
conftest.py — Configuração do pytest e fixtures compartilhadas.
"""

import json
import os
import sys

import pytest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


@pytest.fixture
def schema_status():
    caminho = os.path.join(BASE_DIR, "firmware", "status-schema.json")
    with open(caminho) as f:
        return json.load(f)


@pytest.fixture
def payload_status_valido():
    return {
        "estado": "NORMAL",
        "modo": "ARMADO",
        "ts": "2026-11-12T13:46:47",
        "time_source": "RTC",
        "nonce": 0,
        "porta": False,
        "luz": True,
        "dist_cm": 335.9,
        "ativo": False,
        "ip": "10.10.0.2",
        "uid": "-",
        "acessos": 0,
        "invasoes": 0,
        "rearmes": 0,
        "alerta_temp": False,
        "critico_temp": False,
        "alerta_umid": False,
        "critico_umid": False,
        "taxa_temp_alerta": False,
        "ambiente": "OK",
        "temp_c": 24.0,
        "umid_pct": 40.0,
    }


@pytest.fixture
def zabbix_mock(mocker):
    mock = mocker.patch("configurar_zabbix.ZabbixAPI")
    instance = mock.return_value
    instance.call = mocker.MagicMock()
    instance.login = mocker.MagicMock()
    instance.logout = mocker.MagicMock()
    return instance
'''

# ============================================================
# test_schema.py
# ============================================================
test_schema = '''"""
test_schema.py — Testes do JSON Schema do status do firmware.
"""

import jsonschema
import pytest


def test_schema_valido(schema_status):
    jsonschema.Draft7Validator.check_schema(schema_status)


def test_payload_valido(schema_status, payload_status_valido):
    jsonschema.validate(payload_status_valido, schema_status)


def test_payload_sem_campo_obrigatorio(schema_status, payload_status_valido):
    del payload_status_valido["temp_c"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload_status_valido, schema_status)


def test_payload_tipo_errado(schema_status, payload_status_valido):
    payload_status_valido["temp_c"] = "24.0"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload_status_valido, schema_status)


def test_payload_estado_invalido(schema_status, payload_status_valido):
    payload_status_valido["estado"] = "ESTADO_QUE_NAO_EXISTE"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload_status_valido, schema_status)


def test_payload_campo_extra(schema_status, payload_status_valido):
    payload_status_valido["campo_novo"] = 42
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload_status_valido, schema_status)


def test_payload_temp_fora_da_faixa(schema_status, payload_status_valido):
    payload_status_valido["temp_c"] = 150
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload_status_valido, schema_status)


def test_payload_umid_fora_da_faixa(schema_status, payload_status_valido):
    payload_status_valido["umid_pct"] = 150
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(payload_status_valido, schema_status)


def test_payload_ip_invalido(schema_status, payload_status_valido):
    from jsonschema import FormatChecker
    payload_status_valido["ip"] = "999.999.999.999"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            payload_status_valido, schema_status, format_checker=FormatChecker()
        )
'''

# ============================================================
# test_zabbix_upsert.py
# ============================================================
test_zabbix = '''"""
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
    zabbix_mock.call.side_effect = [
        [],
        {"itemids": ["1"]},
        [{"itemid": "1"}],
        {"itemids": ["1"]},
    ]
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", VT_FLOAT, "C", "$.campo"
    )
    upsert_dependent_item(
        zabbix_mock, "10683", "50740",
        "Teste", "esp32.teste", VT_FLOAT, "C", "$.campo"
    )
    args, _ = zabbix_mock.call.call_args_list[3]
    assert args[0] == "item.update"
    assert args[1]["itemid"] == "1"

# ============================================================
# pytest.ini
# ============================================================
pytest_ini = '''[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
'''

# Escrever arquivos
arquivos = {
    os.path.join(TESTS, "conftest.py"): conftest,
    os.path.join(TESTS, "test_schema.py"): test_schema,
    os.path.join(TESTS, "test_zabbix_upsert.py"): test_zabbix,
    os.path.join(BASE, "pytest.ini"): pytest_ini,
}

for caminho, conteudo in arquivos.items():
    with open(caminho, "w") as f:
        f.write(conteudo)
    print(f"OK: {caminho}")

print()
print(f"Total: {len(arquivos)} arquivos criados.")

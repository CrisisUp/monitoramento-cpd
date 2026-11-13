"""
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

"""
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

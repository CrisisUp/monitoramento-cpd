# ADR-005: Provisionar o Grafana via JSON em vez de cliques

- **Status:** Aceito
- **Data:** 2026-11-12
- **Autores:** Cristiano

## Contexto

O Grafana precisa de datasource e dashboards. Configurar manualmente é
demorado e sujeito a erros.

## Decisão

Usar provisionamento via arquivos (grafana/provisioning/ + JSON).

## Consequências

### Positivas
- Reprodutibilidade: docker compose up -d provisiona tudo.
- Versionamento: os JSONs estão no Git.

### Negativas
- allowUiUpdates: false ignora edições na UI.
- Erros de JSON são silenciosos.

## Alternativas descartadas

### A) Configurar tudo na interface
- Não é reproduzível.

### B) API do Grafana via Python
- Redundante com o provisionamento nativo.

## Referências

- grafana/provisioning/
- grafana/dashboards/
- docs/06.txt, 07.txt

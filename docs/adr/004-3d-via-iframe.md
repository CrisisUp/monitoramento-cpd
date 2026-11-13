# ADR-004: Carregar o NOC 3D via iframe em vez de plugin nativo

- **Status:** Aceito
- **Data:** 2026-11-12
- **Autores:** Cristiano

## Contexto

O NOC 3D usa Three.js. O Grafana tem CSP que bloqueia scripts inline e
iframes de fontes externas.

## Decisão

Usar iframe apontando para noc3d.html, servido pelo Grafana. O grafana.ini
precisa de:
- [security] disable_sanitize_html = true
- [security] allow_embedding = true
- [security] cookie_samesite = disabled
- [panels] disable_sanitize_html = true

## Consequências

### Positivas
- Isolamento: o Three.js roda no seu sandbox.
- Testável fora do Grafana (URL direta funciona).

### Negativas
- Configuração extra no grafana.ini.
- Iframe precisa de altura explícita.

## Alternativas descartadas

### A) Painel Text nativo
- O Grafana 13 escapa HTML por padrão.

### B) Business Text
- Também bloqueou scripts com type module.

### C) Plugin customizado
- Complexidade desnecessária.

## Referências

- grafana/noc/noc3d.html
- grafana/config/grafana.ini
- docs/12.txt

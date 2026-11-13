# ADR-003: Configurar o Zabbix via API (IaC) em vez de cliques

- **Status:** Aceito
- **Data:** 2026-11-12
- **Autores:** Cristiano

## Contexto

O Zabbix precisa de host, itens, macros e triggers. Configurar manualmente
leva 15+ minutos e é sujeito a erros.

## Decisão

Usar a API do Zabbix via script Python idempotente (configurar_zabbix.py).

## Consequências

### Positivas
- Reprodutibilidade: rodar o script cria tudo em 2s.
- Idempotência: rodar N vezes não duplica.
- Versionamento: o script está no Git.

### Negativas
- Curva de aprendizado da API.
- Debug menos amigável que a interface.

## Alternativas descartadas

### A) Configurar tudo na interface
- Não é reproduzível; erros de JSONPath são fáceis.

### B) Importar template YAML manualmente
- A criação inicial ainda seria manual.

## Referências

- configurar_zabbix.py
- docs/05.txt, 08.txt, 09.txt

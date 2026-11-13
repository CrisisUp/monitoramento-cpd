# ADR-006: Usar Makefile como porta de entrada do projeto

- **Status:** Aceito
- **Data:** 2026-11-12
- **Autores:** Cristiano

## Contexto

Reproduzir o projeto exigia entender 12 arquivos de documentação e
executar comandos na ordem certa. A porta de entrada era leia o README
e reze.

## Decisão

Adicionar um Makefile com comandos curtos (make setup, make up, make down,
make reset, make health, make backup, etc.).

## Consequências

### Positivas
- Porta de entrada óbvia.
- Padrão de mercado (universal em infraestrutura).
- make help documenta todos os comandos.

### Negativas
- Dependência do make (vem com Xcode CLT no macOS).

## Alternativas descartadas

### A) Manter só o README
- Não escala; erros na ordem dos comandos.

### B) install.sh monolítico
- Não permite operações separadas.

## Referências

- Makefile
- scripts/setup.sh, reset.sh, health.sh, backup.sh

# ADR-008: Usar Windows 11 como ambiente de produção (futuro)

- **Status:** Proposto
- **Data:** 2026-11-12
- **Autores:** Cristiano
- **Contexto do projeto:** Pós-Fatia 6 (migração para produção)

## Contexto

O projeto foi desenvolvido no macOS. Para produção, é necessário escolher
um sistema operacional.

As opções eram:

1. **Windows 10** — em fim de suporte (outubro de 2025).
2. **Windows 11** — sucessor, suporte até 2031.
3. **Linux** — mais próximo do Docker, mas exige conhecimento da equipe.

A equipe de TI está **avaliando a migração para Windows 11**, mas ainda
não homologou.

## Decisão

Usar **Windows 11** como ambiente de produção **assim que a equipe de TI
homologar** (previsto para 2026).

**Nota:** o Windows 10 é o ambiente **interino** (ver ADR-007).

## Consequências

### Positivas
- **Suporte de longo prazo:** atualizações de segurança até 2031.
- **Segurança:** TPM 2.0 obrigatório, Secure Boot, etc.
- **Compatibilidade:** Docker Desktop, IIS, URL Rewrite, ARR funcionam
  igual ao Windows 10.

### Negativas
- **Requisitos de hardware:** TPM 2.0, Secure Boot, 4 GB RAM, 64 GB disco.
- **Migração:** precisa ser planejada e testada pela equipe de TI.

### Neutras
- O IIS é o mesmo no Windows 10 e 11.
- O `web.config` é idêntico.
- O script `setup-producao.ps1` funciona nos dois.

## Alternativas descartadas

### A) Windows 10 (interino)
- **O que era:** usar o Windows 10 enquanto o Windows 11 não é homologado.
- **Por que foi descartada:** fim de suporte em outubro de 2025.

### B) Linux
- **O que era:** usar Ubuntu/Debian em produção.
- **Por que foi descartada:** a equipe de TI não tem familiaridade.

## Referências

- [ADR-007](007-windows-10-producao.md) — decisão paralela para Windows 10
- [README.configWindows.md](../README.configWindows.md) — guia de deploy
- `scripts/setup-producao.ps1` — automação do IIS
- [Requisitos do Windows 11](https://www.microsoft.com/windows/windows-11-specifications)

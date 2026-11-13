# ADR-007: Usar Windows 10 como ambiente de produção (legado)

- **Status:** Aceito
- **Data:** 2026-11-12
- **Autores:** Cristiano
- **Contexto do projeto:** Pós-Fatia 6 (migração para produção)

## Contexto

O projeto foi desenvolvido no macOS (Mac mini M4). Para produção, é
necessário escolher um sistema operacional.

As opções eram:

1. **Windows 10** — amplamente usado em empresas, mas em fim de suporte
   (outubro de 2025).
2. **Windows 11** — sucessor do Windows 10, suporte até 2031.
3. **Linux** (Ubuntu/Debian) — mais próximo do ambiente Docker, mas
   exige mais conhecimento da equipe.

A equipe de TI da empresa tem **mais familiaridade com Windows** (Active
Directory, GPO, IIS, etc.).

## Decisão

Usar **Windows 10** como ambiente de produção **enquanto o Windows 11 não
for homologado pela equipe de TI**.

**Nota:** o Windows 10 está em fim de suporte (outubro de 2025). A migração
para Windows 11 deve ser planejada.

## Consequências

### Positivas
- **Familiaridade da equipe:** IIS, Active Directory, GPO.
- **Compatibilidade:** Docker Desktop funciona no Windows 10 (via WSL2).
- **Custo:** máquinas já existentes podem ser reutilizadas.

### Negativas
- **Fim de suporte:** o Windows 10 não recebe mais atualizações de
  segurança após outubro de 2025.
- **Risco de segurança:** vulnerabilidades não corrigidas.
- **Necessidade de migração:** planejar a migração para Windows 11.

### Neutras
- O IIS é o mesmo no Windows 10 e 11 (mesmos módulos: URL Rewrite, ARR).
- O Docker Desktop é o mesmo.
- O `web.config` é idêntico.

## Alternativas descartadas

### A) Windows 11
- **O que era:** usar o sucessor do Windows 10.
- **Por que foi descartada:** a equipe de TI ainda não homologou o
  Windows 11 em produção (falta de testes de compatibilidade com
  softwares internos).

### B) Linux
- **O que era:** usar Ubuntu/Debian em produção.
- **Por que foi descartada:** a equipe de TI não tem familiaridade com
  Linux; o Active Directory e o GPO são baseados em Windows.

## Referências

- [ADR-008](008-windows-11-producao.md) — decisão paralela para Windows 11
- [README.configWindows.md](../README.configWindows.md) — guia de deploy
- `scripts/setup-producao.ps1` — automação do IIS

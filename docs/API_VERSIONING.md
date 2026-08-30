# Versionamento da API

- **Status:** Accepted
- **Data:** 2026-08-30

## Política

- Endpoints públicos começam em `/api/v1`.
- OpenAPI é o contrato canônico entre API e web.
- Mudança aditiva compatível não cria nova versão.
- Remoção, mudança semântica ou tipo incompatível exige nova versão ou período documentado de depreciação.
- Erros usam Problem Details e não vazam segredos.
- Campos financeiros mantêm semântica estável para fonte, timestamps, `data_level` e freshness.

## Compatibilidade

Schema OpenAPI será versionado junto ao código. O frontend deve gerar tipos a partir do contrato e não copiar payloads manualmente. Contract tests bloquearão drift após o Dia 5.

## Depreciação

Antes de remover um contrato: registrar ADR quando material, documentar alternativa, marcar depreciação, medir consumo e definir janela. Nenhuma janela é assumida no Dia 1.

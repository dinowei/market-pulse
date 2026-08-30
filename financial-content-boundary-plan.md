# Plano técnico da fronteira de conteúdo financeiro

- **Status:** Proposed; desenho do Dia 1, sem schema ou trigger implementado
- **Data:** 2026-08-30

## Modelo conceitual

```text
ContentBlock
- id
- version_id
- content_type
- body
- source
- source_timestamp
- data_level
- created_at

MorningCallVersion
- id
- version_number
- status
- content_hash
- previous_version_id
- correction_reason
- created_at
- published_at
```

`content_type` aceita `FACT`, `THIRD_PARTY_CONSENSUS`, `CONDITIONAL_SCENARIO`, `RISK` e `LIMITATION`.

`data_level` aceita `REAL_TIME`, `DELAYED`, `EOD` e `DEMO`.

## Pipeline futuro

1. **Checagem lexical:** lista versionada de imperativos, promessas e certezas proibidas.
2. **Checagem estrutural:** `content_type`, campos e status válidos.
3. **Checagem de atribuição:** `FACT` e `THIRD_PARTY_CONSENSUS` exigem fonte e timestamp.
4. **Checagem de nível:** números exigem `data_level`; `DEMO` exige limitação visível.

Qualquer falha impede avanço para revisão humana, mantém o conteúdo como rascunho e retorna lista estruturada de falhas. Validação automática não publica conteúdo e não substitui revisão humana.

## Publicação append-only

- Publicação insere versão imutável e nunca edita a anterior.
- Correção exige nova `MorningCallVersion`, `previous_version_id`, `correction_reason` e novo `published_at`.
- `content_hash` detecta divergência, mas não prova imutabilidade isoladamente.
- A garantia principal virá da regra de aplicação que proíbe `UPDATE`/`DELETE` publicado e, em etapa dedicada, de proteção no banco.
- Triggers, permissões de produção e schema não são implementados no Dia 1.

## Critérios de teste futuros

- Imperativo ou promessa bloqueia o rascunho.
- Tipo inválido falha estruturalmente.
- `FACT` sem fonte/timestamp é bloqueado.
- `THIRD_PARTY_CONSENSUS` sem fontes nomeadas é bloqueado.
- Número `DEMO` sem limitação visível é bloqueado.
- Revisor humano não consegue publicar conteúdo com falha pendente.
- Correção cria nova versão e preserva a anterior.
- Tentativa de alterar ou apagar publicação é rejeitada.
- Hash diferente sinaliza divergência, sem substituir controles append-only.

## Comando administrativo planejado

O Morning Call será importado por comando interno autenticado, não por editor visual e não por IA. O comando cria rascunho, executa validações e exige uma ação humana separada para publicar.

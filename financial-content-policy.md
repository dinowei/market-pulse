# Política de conteúdo financeiro

- **Status:** Accepted
- **Data:** 2026-08-30

> **Conteúdo informativo. Não constitui recomendação de investimento.**

O disclaimer deve ser visível junto às áreas financeiras; não pode ficar oculto em tooltip, página jurídica separada ou rodapé ilegível.

## Tipos permitidos

Todo bloco deve usar exatamente um tipo: `FACT`, `THIRD_PARTY_CONSENSUS`, `CONDITIONAL_SCENARIO`, `RISK` ou `LIMITATION`.

### `FACT`

- **Definição:** fato verificável em fonte identificada.
- **Pode:** descrever valor, evento ou divulgação.
- **Não pode:** extrapolar intenção, causalidade ou recomendação.
- **Metadados:** fonte, timestamp da fonte, `data_level` e limitação.
- **Seguro:** “O USD/BRL fechou em X segundo Fonte Y, às Z.”
- **Bloqueado:** “O dólar fechou em X, então compre agora.”

### `THIRD_PARTY_CONSENSUS`

- **Definição:** síntese atribuída de opiniões externas identificáveis.
- **Pode:** relatar consenso com amostra, fonte e data.
- **Não pode:** chamar opinião do produto de consenso.
- **Metadados:** fontes, data, metodologia/amostra e limitação.
- **Seguro:** “A mediana da pesquisa Y em data Z foi X.”
- **Bloqueado:** “O mercado sabe que o ativo vai subir.”

### `CONDITIONAL_SCENARIO`

- **Definição:** relação hipotética explícita entre condição e possível efeito.
- **Pode:** usar “se”, “pode” e condições observáveis.
- **Não pode:** converter hipótese em certeza ou instrução.
- **Metadados:** condição, horizonte, fonte dos dados e riscos.
- **Seguro:** “Se a taxa permanecer elevada, ativos sensíveis a juros podem oscilar.”
- **Bloqueado:** “A taxa ficará alta; venda ações.”

### `RISK`

- **Definição:** descrição de incerteza ou possibilidade adversa.
- **Pode:** explicar exposição, volatilidade e limitações.
- **Não pode:** usar medo para induzir operação.
- **Metadados:** contexto, horizonte, fonte e materialidade.
- **Seguro:** “Liquidez reduzida pode ampliar a oscilação intradiária.”
- **Bloqueado:** “O risco é enorme; saia agora.”

### `LIMITATION`

- **Definição:** restrição de cobertura, licença, atraso ou metodologia.
- **Pode:** explicar o que o dado não representa.
- **Não pode:** minimizar restrição material.
- **Metadados:** escopo afetado, `data_level`, início e fim quando conhecidos.
- **Seguro:** “Dados de demonstração; não refletem o mercado atual.”
- **Bloqueado:** “Cotação em tempo real” para dado `DEMO`.

## Proibições globais

- Imperativos como “compre”, “venda”, “entre agora” e “saia agora”.
- Promessas como “vai subir”, “lucro garantido” ou “retorno garantido”.
- Preço-alvo criado pelo produto.
- Cenário condicional apresentado como certeza.
- Consenso sem fonte nomeada e data.
- Dado `DELAYED`, `EOD` ou `DEMO` descrito como tempo real.
- Omissão de limitação material do dado.
- Opinião própria apresentada como consenso.

## Níveis de dados

- `REAL_TIME`: somente quando contrato e semântica estiverem confirmados.
- `DELAYED`: atraso conhecido e visível.
- `EOD`: fechamento, nunca descrito como intraday.
- `DEMO`: dado sintético ou de demonstração com limitação visível.

## Publicação

```text
Rascunho → Validador automático → Revisão humana → Publicação versionada
```

Qualquer falha automática mantém o conteúdo como rascunho com lista de erros. A revisão humana é obrigatória e não é substituída pelo validador.

Conteúdo publicado é append-only. Correção gera nova versão, referência à anterior, timestamp e motivo. Hash auxilia auditoria, mas não é garantia isolada de imutabilidade.

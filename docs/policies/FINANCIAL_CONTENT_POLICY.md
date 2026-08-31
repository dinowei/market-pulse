# Política Canônica de Conteúdo Financeiro

- **Status:** Canônica
- **Data:** 2026-08-30
- **Escopo:** conteúdo financeiro exibido, importado, revisado ou publicado pelo Market Pulse

> **Conteúdo informativo. Não constitui recomendação de investimento.**

Este documento é a única fonte canônica da política de conteúdo financeiro do Market Pulse. Documentos anteriores permanecem como registros históricos ou planos técnicos e não prevalecem sobre esta política. Este texto não afirma aprovação regulatória e não substitui revisão jurídica, regulatória ou profissional independente.

## Base documental e decisões de canonização

A política consolida decisões válidas de `docs/PROJECT_SPEC.md`, `financial-content-policy.md`, `financial-content-boundary-plan.md`, `docs/DATA_GOVERNANCE.md`, ADR-003 e ADR-004. Especificação, planos e ADRs continuam exercendo suas funções próprias; este arquivo é normativo apenas para conteúdo financeiro.

| Tema | Divergência ou lacuna anterior | Decisão canônica |
| --- | --- | --- |
| Local da política | A política anterior estava na raiz | Este arquivo passa a ser a única política canônica; o arquivo anterior é histórico |
| Tipos de conteúdo | Existiam valores, mas não um contrato completo de `ContentType` | São aceitos exatamente os cinco valores definidos nesta política |
| Atualização dos dados | Freshness aparecia em linguagem descritiva, sem enum completo | `DataLevel` e `Freshness` são conceitos separados, com valores normativos próprios |
| Fluxo editorial | O fluxo era descrito sem todos os estados | Os estados e transições desta política são normativos |
| Licenciamento | `DEMO` e controles internos poderiam ser confundidos com permissão | Modalidade do dado e controle de acesso não concedem direito de uso |
| Plano complementar | No início da canonização, `docs/superpowers/plans/financial-content-boundary.md` não existia | A lacuna foi registrada e depois resolvida no fechamento do Dia 1 pelo [plano técnico canônico](../superpowers/plans/financial-content-boundary.md) |

## 1. Natureza do produto

O Market Pulse é um terminal exclusivamente informativo e analítico. Ele apresenta fatos atribuídos, dados com proveniência, consensos de terceiros devidamente licenciados, cenários condicionais, riscos e limitações.

O Market Pulse não presta:

- consultoria financeira;
- análise personalizada;
- suitability ou avaliação de adequação;
- gestão de carteira;
- recomendação de compra, venda ou manutenção;
- sinal de negociação;
- orientação de timing ou alocação;
- promessa de resultado ou rentabilidade.

O conteúdo não deve ser adaptado para induzir uma pessoa específica a tomar uma ação financeira.

### Carteiras informativas

O beta pode registrar múltiplas carteiras próprias e eventos manuais informados pelo usuário, e calcular posição, custo, patrimônio, P&L, rentabilidade, proventos e performance histórica. Esses resultados são cálculos factuais baseados no ledger, snapshots, preços, FX e metodologias explicitamente identificados. Isso não constitui gestão de carteira, recomendação, suitability, ordem, alocação sugerida ou promessa de retorno.

Eventos sem preço, moeda, FX, timestamp ou fonte aplicável devem permanecer `PARTIAL` ou `UNAVAILABLE`; nenhum cálculo visual pode completar silenciosamente a lacuna.

## 2. Tipos permitidos de conteúdo

Todo bloco publicável deve ter exatamente um `ContentType`:

- `FACT`
- `THIRD_PARTY_CONSENSUS`
- `CONDITIONAL_SCENARIO`
- `RISK`
- `LIMITATION`

`CONSENSUS` não é um valor válido nem um alias de `THIRD_PARTY_CONSENSUS`.

### `FACT`

- **Definição:** afirmação verificável diretamente em fonte identificada.
- **Campos mínimos:** corpo; fonte; provider e dataset, quando aplicáveis; instrumento e mercado, quando aplicáveis; timestamp da fonte; timestamp da coleta para dados; `DataLevel` e `Freshness` para valores financeiros; limitações materiais.
- **Exemplo permitido:** “O indicador X foi publicado pela Fonte A em 2026-08-30 às 09:00 UTC.”
- **Exemplo inválido:** “O indicador X melhorou; portanto, compre o ativo.”
- **Atribuição:** a fonte deve estar nomeada e distinguida da autoria do Market Pulse.
- **Condição de publicação:** fonte, timestamp, evidência e classificações aplicáveis devem estar presentes e passar por validação e revisão humana.

### `THIRD_PARTY_CONSENSUS`

- **Definição:** síntese fiel e atribuída de estimativas ou opiniões de terceiros identificáveis.
- **Campos mínimos:** corpo; fontes nomeadas; data ou timestamp; amostra ou metodologia; evidência de licença para a finalidade; `DataLevel` e `Freshness` quando houver dados; limitações.
- **Exemplo permitido:** “A mediana da pesquisa P, publicada pela Fonte A na data D, foi X; a amostra e a metodologia estão identificadas na fonte.”
- **Exemplo inválido:** “O mercado sabe que o ativo vai subir.”
- **Atribuição:** o texto deve indicar explicitamente que o consenso pertence às fontes e não ao Market Pulse.
- **Condição de publicação:** licença, atribuição, data, amostra ou metodologia e limitações devem estar comprovadas; qualquer ausência bloqueia a publicação.

### `CONDITIONAL_SCENARIO`

- **Definição:** hipótese que relaciona condições observáveis a possíveis efeitos, sem converter incerteza em previsão certa.
- **Campos mínimos:** condição; horizonte; hipótese; fatos históricos separados da projeção; fontes; fatores de invalidação; riscos; limitações.
- **Exemplo permitido:** “Se a condição C persistir durante o período H, o indicador I pode oscilar; mudanças em F podem invalidar este cenário.”
- **Exemplo inválido:** “A condição C permanecerá; venda agora.”
- **Atribuição:** fatos e premissas de terceiros devem ter suas respectivas fontes; a relação condicional deve ser identificada como cenário.
- **Condição de publicação:** linguagem condicional, incerteza, horizonte, fontes, fatores de invalidação e revisão humana são obrigatórios.

### `RISK`

- **Definição:** descrição atribuída e contextualizada de incerteza, exposição ou possibilidade adversa.
- **Campos mínimos:** contexto; fator de risco; horizonte; fonte; materialidade quando conhecida; incerteza; limitações.
- **Exemplo permitido:** “Liquidez reduzida pode ampliar oscilações; o efeito e sua duração são incertos.”
- **Exemplo inválido:** “O risco é enorme; saia agora.”
- **Atribuição:** dados e avaliações de terceiros devem ser identificados; o Market Pulse não transforma risco em prescrição.
- **Condição de publicação:** contexto, incerteza, fonte e limitações devem estar explícitos, sem linguagem destinada a induzir negociação.

### `LIMITATION`

- **Definição:** restrição relevante de cobertura, licença, atraso, disponibilidade, metodologia ou interpretação.
- **Campos mínimos:** escopo afetado; natureza da limitação; provider e dataset quando aplicáveis; `DataLevel`; `Freshness`; início e fim quando conhecidos; impacto para interpretação.
- **Exemplo permitido:** “Dados sintéticos de demonstração; não representam o mercado atual.”
- **Exemplo inválido:** “Cotação em tempo real” para um valor classificado como `DEMO` ou `STALE`.
- **Atribuição:** a origem da limitação deve ser informada quando vier de contrato, provider, dataset ou metodologia de terceiro.
- **Condição de publicação:** a limitação deve permanecer visível junto ao conteúdo afetado e não pode ser minimizada ou ocultada.

## 3. Conteúdo proibido

É proibido publicar conteúdo que contenha, como afirmação, autoria ou orientação do Market Pulse:

- “compre”;
- “venda”;
- “mantenha” quando usado como recomendação;
- “entre agora”;
- “saia agora”;
- “vai subir”;
- “vai cair”;
- “lucro garantido”;
- “retorno garantido”;
- recomendação personalizada;
- carteira recomendada;
- sinal automático;
- promessa de rentabilidade;
- preço-alvo produzido pelo Market Pulse;
- classificação própria de “compra forte”;
- cenário hipotético apresentado como certeza;
- consenso sem atribuição;
- conteúdo de terceiro apresentado como autoria própria.

A linguagem deve ser avaliada em contexto. Uma futura validação automática poderá sinalizar ocorrências, mas não deverá bloquear mecanicamente toda palavra sem considerar fronteiras de palavra, negação, citação, exemplos editoriais, atribuição e falsos positivos. A análise contextual não autoriza conteúdo que, em substância, induza ação financeira.

## 4. Consenso de terceiros

`THIRD_PARTY_CONSENSUS` somente é publicável quando:

- provém de fonte terceira licenciada para a finalidade e modalidade de uso;
- possui fonte nomeada;
- possui data ou timestamp;
- está claramente atribuído;
- informa amostra ou metodologia aplicável;
- não é apresentado como opinião do Market Pulse;
- não é transformado em recomendação, sinal ou promessa.

Ausência de licença, atribuição, fonte, data ou contexto metodológico bloqueia a publicação.

## 5. Cenários condicionais

Todo `CONDITIONAL_SCENARIO` deve:

- usar linguagem condicional;
- declarar incerteza;
- separar observação histórica de hipótese ou previsão;
- declarar horizonte quando aplicável;
- apresentar fatores que podem invalidar o cenário;
- nomear as fontes dos fatos e premissas;
- nunca prescrever compra, venda, manutenção, timing ou alocação.

Um cenário não se torna fato por repetição, popularidade ou concordância aparente de terceiros.

## 6. Proveniência dos dados

Todo dado financeiro exibido deve informar, quando aplicável:

- provider;
- dataset;
- instrumento;
- mercado ou bolsa;
- moeda;
- timestamp da fonte;
- timestamp da coleta;
- `DataLevel`;
- `Freshness`;
- limitações conhecidas.

Fonte e timestamps devem permanecer associados ao item exibido. Transformação, agregação ou cache não podem apagar a proveniência original nem sugerir uma atualidade inexistente.

## 7. Separação entre DataLevel e Freshness

`DataLevel` descreve a modalidade ou latência contratual do dado. São aceitos exatamente:

- `REAL_TIME`
- `DELAYED`
- `EOD`
- `DEMO`

`Freshness` descreve a disponibilidade e a atualidade operacional do item. São aceitos exatamente:

- `FRESH`
- `STALE`
- `UNAVAILABLE`

Regras obrigatórias:

- `DataLevel` e `Freshness` são independentes e devem ser informados separadamente;
- `REAL_TIME` somente pode ser alegado com comprovação contratual e técnica;
- `DELAYED` deve exibir o atraso conhecido;
- `EOD` não pode ser descrito como intraday;
- `DEMO` identifica modalidade demonstrativa, não dado licenciado;
- `DEMO`, autenticação administrativa, feature flag ou acesso interno não concedem direitos de licença;
- `STALE` não pode ser apresentado como atual e deve informar o motivo e o timestamp do último valor válido;
- `UNAVAILABLE` não pode ser substituído silenciosamente por valor inventado, incompatível ou sem proveniência;
- fixtures sintéticas devem ser determinísticas e identificadas como demonstrativas.

## 8. Licenciamento

O Market Pulse adota **default deny**. Estado desconhecido, documentação incompleta ou interpretação duvidosa significam uso público não autorizado.

A aprovação deve ser específica por combinação de:

- provider;
- plano;
- endpoint;
- dataset;
- finalidade;
- modalidade de uso.

Antes de qualquer ativação pública, deve existir evidência documental vigente sobre:

- uso comercial;
- armazenamento;
- cache;
- transformação;
- exibição;
- redistribuição;
- atribuição;
- região;
- plano contratado.

Uma permissão para um endpoint, dataset, plano ou finalidade não se estende automaticamente aos demais. `DEMO`, autenticação administrativa, feature flag, allowlist, acesso interno ou classificação técnica não alteram direitos de licença.

Enquanto não houver aprovação documental aplicável, somente fixtures sintéticas, determinísticas e claramente identificadas podem ser utilizadas na apresentação. Elas não devem copiar dados reais protegidos nem ser confundidas com o mercado atual.

## 9. Fluxo editorial

O fluxo normativo é:

```text
DRAFT
→ VALIDATION_FAILED ou VALIDATED
→ IN_REVIEW
→ PUBLISHED
→ SUPERSEDED
```

- Conteúdo sem `ContentType` não é publicável.
- Validação automática é obrigatória, mas não publica conteúdo.
- `VALIDATION_FAILED` retorna o conteúdo para correção em estado não publicável.
- Somente conteúdo `VALIDATED` pode avançar para `IN_REVIEW`.
- Revisão humana é obrigatória.
- A aprovação humana deve registrar responsável e timestamp.
- Publicação deve ser versionada e append-only.
- Conteúdo publicado não é editado ou apagado silenciosamente.
- Correção cria nova versão com referência à anterior e motivo.
- A versão anterior permanece auditável e pode ser marcada `SUPERSEDED`.
- Hash ajuda a detectar alteração, mas não substitui controles de imutabilidade no armazenamento.

Este fluxo é uma regra de política. Sua implementação em código está fora desta tarefa.

## 10. Morning Call

Um Morning Call deve conter, nesta ordem:

1. horário de corte;
2. resumo factual;
3. mercados globais;
4. Brasil;
5. câmbio, juros e commodities;
6. agenda econômica;
7. empresas em destaque;
8. riscos e eventos a acompanhar;
9. fontes;
10. limitações dos dados;
11. aviso informativo.

Todo bloco deve ter exatamente um `ContentType`. Se uma seção não possuir evidência suficiente, ela deve ser omitida de forma explícita ou marcada como indisponível; nunca deve ser completada por inferência silenciosa. O Morning Call exige validação automática e revisão humana antes da publicação.

## 11. Disclaimer

Aviso mínimo visível junto a áreas financeiras:

> **Conteúdo informativo. Não constitui recomendação de investimento.**

Para Morning Call e conteúdo editorial completo:

> **Conteúdo exclusivamente informativo e educacional. Não constitui recomendação de investimento, oferta, análise personalizada ou promessa de rentabilidade. Verifique as fontes, os horários e a classificação de atualização dos dados antes de tomar decisões financeiras.**

O aviso deve ser legível e próximo do conteúdo. Não pode ficar restrito a tooltip, página separada ou rodapé ilegível, e não substitui atribuição, licenciamento, validação ou revisão humana.

## 12. Falha segura

Na ausência de qualquer item obrigatório — evidência, fonte, timestamp, licença, atribuição, `DataLevel`, `Freshness` ou revisão humana — o conteúdo deve permanecer não publicável ou o dado deve ser exibido como `UNAVAILABLE`, conforme o caso.

Nunca inventar, completar, interpolar ou inferir silenciosamente informação ausente. Um último valor validado somente pode ser exibido como `STALE`, com fonte, timestamp e limitação visíveis.

## 13. Exemplos editoriais

Os exemplos abaixo são redações ilustrativas; letras e valores simbólicos não representam dados atuais.

| Caso | Exemplo | Resultado e motivo |
| --- | --- | --- |
| `FACT` válido | “A Fonte A publicou o indicador X na data D, às T UTC.” | Permitido se fonte, timestamp, proveniência e classificações aplicáveis estiverem presentes |
| `THIRD_PARTY_CONSENSUS` válido | “A mediana da pesquisa P da Fonte A na data D foi X, segundo a metodologia M.” | Permitido se fonte, licença, amostra/metodologia, data e atribuição estiverem comprovadas |
| `CONDITIONAL_SCENARIO` válido | “Se C persistir durante H, I pode oscilar; F pode invalidar o cenário.” | Permitido por explicitar condição, incerteza e fator de invalidação |
| `RISK` válido | “A redução de liquidez pode ampliar oscilações; duração e magnitude são incertas.” | Permitido quando contextualizado, atribuído e não prescritivo |
| `LIMITATION` válida | “Dados sintéticos de demonstração; não representam o mercado atual.” | Permitido quando visível junto ao conteúdo afetado |
| Recomendação | “Compre o ativo agora.” | Bloqueado por prescrever ação financeira |
| Promessa | “Este ativo oferece retorno garantido.” | Bloqueado por promessa de rentabilidade |
| Falta de fonte | “O indicador X atingiu Y.” sem fonte ou timestamp | Bloqueado por ausência de evidência e proveniência |
| Licença desconhecida | “Consenso da Plataforma P” sem termos aplicáveis verificados | Bloqueado por default deny e falta de atribuição/licença suficiente |
| Atualização incorreta | “Cotação em tempo real” para dado `DEMO` ou `STALE` | Bloqueado por classificar incorretamente `DataLevel` ou `Freshness` |

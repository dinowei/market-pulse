// Plain-language explanation for each reason code the API returns instead of a value
// (ADR-025). The code itself stays visible next to the text, and an unknown code is shown
// as it came, never mapped to a friendlier one.
const REASONS: Record<string, string> = {
  UNAVAILABLE: "Indisponível no momento.",
  STALE: "Desatualizado: é o último valor validado.",
  LICENSE_BLOCKED: "Bloqueado por licença: a fonte não está aprovada para este uso.",
  PROVIDER_NOT_CONFIGURED: "A fonte deste dado não está configurada.",
  DATASET_NOT_APPROVED: "Nenhum dataset aprovado fornece este dado.",
  SCHEMA_UNSUPPORTED: "A resposta da fonte não seguiu o formato esperado e foi descartada.",
  RATE_LIMITED: "A fonte atingiu o limite de requisições; o dado volta depois da espera.",
  SOURCE_ERROR: "A fonte não respondeu.",
  SOURCE_UNAVAILABLE: "A fonte não respondeu.",
  QUOTE_NOT_LOADED: "A cotação não foi carregada.",
  PROVIDER_PAUSED: "A fonte está pausada.",
  SESSION_REQUIRED: "Dados reais só aparecem com a sessão do responsável (uso privado).",
};

export function explainReason(code: string | null | undefined): { code: string; text: string } | null {
  if (!code) return null;
  return { code, text: REASONS[code] ?? code };
}

/** "Explanation (CODE)", or the bare code when it has no explanation yet. */
export function formatReason(code: string | null | undefined): string | null {
  const reason = explainReason(code);
  if (!reason) return null;
  return reason.text === reason.code ? reason.code : `${reason.text} (${reason.code})`;
}

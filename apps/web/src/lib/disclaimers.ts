// Canonical disclaimers of docs/policies/FINANCIAL_CONTENT_POLICY.md section 11. The
// text is copied verbatim and a test compares it with the policy, so wording changes
// start in the policy, never here.

/** Minimum notice, visible next to every financial area. */
export const FINANCIAL_DISCLAIMER = "Conteúdo informativo. Não constitui recomendação de investimento.";

/** Morning Call and full editorial content. */
export const EDITORIAL_DISCLAIMER =
  "Conteúdo exclusivamente informativo e educacional. Não constitui recomendação de investimento, oferta, análise personalizada ou promessa de rentabilidade. Verifique as fontes, os horários e a classificação de atualização dos dados antes de tomar decisões financeiras.";

// H-13: the human compliance review (docs/editorial/MORNING_CALL_COMPLIANCE_REVIEW.md, §5)
// is unsigned. This states the pending review; it never claims an approval. Remove it in
// the same commit that records the signature (compliance-day35.test.ts enforces both ways).
export const MORNING_CALL_REVIEW_NOTE =
  "Revisão humana de compliance pendente: conteúdo restrito ao uso pessoal no staging privado.";

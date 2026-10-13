export type AuthMode = "login" | "register";

export const PASSWORD_RULE_HINT = "Mínimo de 12 caracteres, com letras e números.";

const LETTER = /\p{L}/u;
const DIGIT = /\p{Nd}/u;

/**
 * Mirrors the API contract (RegisterRequest / LoginRequest in apps/api/app/contracts.py)
 * so the user learns what is wrong before the request, instead of an opaque 422.
 * The API stays the authority: this only avoids sending payloads it will refuse.
 */
export function validateCredentials(mode: AuthMode, email: string, password: string): string | undefined {
  const normalized = email.trim();
  if (normalized.length < 3 || normalized.length > 320 || !normalized.includes("@") || normalized.startsWith("@") || normalized.endsWith("@")) {
    return "Informe um e-mail válido.";
  }
  if (password.length === 0) return "Informe a senha.";
  if (password.length > 128) return "A senha deve ter no máximo 128 caracteres.";
  if (mode === "register" && (password.length < 12 || !LETTER.test(password) || !DIGIT.test(password))) {
    return `Senha fora do padrão. ${PASSWORD_RULE_HINT}`;
  }
  return undefined;
}

/** User-facing message per API status; 409 stays generic so it never reveals whether an e-mail exists. */
export function authErrorMessage(mode: AuthMode, status: number): string {
  switch (status) {
    case 401:
      return "E-mail ou senha incorretos.";
    case 403:
      return "A requisição foi recusada pela proteção de segurança. Recarregue a página e tente novamente.";
    case 404:
      return mode === "register" ? "O cadastro não está aberto neste ambiente." : "Serviço de autenticação não encontrado.";
    case 422:
      return mode === "register" ? `Dados inválidos. Use um e-mail válido e uma senha com ${PASSWORD_RULE_HINT.toLowerCase()}` : "Dados inválidos. Verifique o e-mail e a senha.";
    case 429:
      return "Muitas tentativas. Aguarde um minuto e tente novamente.";
    case 503:
      return "Serviço de autenticação indisponível no momento. Tente novamente em instantes.";
    default:
      return "Não foi possível concluir a autenticação. Verifique os dados e tente novamente.";
  }
}

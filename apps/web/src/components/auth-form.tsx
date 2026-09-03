"use client";

import type { components } from "../generated/api";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

type AuthUserResponse = components["schemas"]["AuthUserResponse"];
type AuthPayload = components["schemas"]["LoginRequest"] | components["schemas"]["RegisterRequest"];

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const isRegister = mode === "register";
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(undefined);
    const payload: AuthPayload = { email, password };
    try {
      const response = await fetch(`${apiBase}/api/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error("AUTH_FAILED");
      const user = (await response.json()) as AuthUserResponse;
      if (!user.email) throw new Error("AUTH_FAILED");
      router.push("/");
    } catch {
      setError("Não foi possível concluir a autenticação. Verifique os dados e tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  return <main className="auth-page"><section className="auth-card" aria-labelledby="auth-title"><p className="eyebrow">MARKET PULSE / ACESSO</p><h1 id="auth-title">{isRegister ? "Criar cadastro" : "Entrar no terminal"}</h1><p className="muted">Acesso informativo. Dados financeiros continuam sujeitos a proveniência e disponibilidade.</p><form onSubmit={submit} noValidate><div className="form-field"><label htmlFor="email">E-mail</label><input id="email" name="email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></div><div className="form-field"><label htmlFor="password">Senha</label><input id="password" name="password" type="password" autoComplete={isRegister ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} required minLength={isRegister ? 12 : 1} /></div>{error && <p className="state-note" role="alert">{error}</p>}<button className="auth-submit" type="submit" disabled={loading}>{loading ? "Aguarde…" : isRegister ? "Cadastrar" : "Entrar"}</button></form><p className="auth-switch">{isRegister ? "Já possui cadastro?" : "Ainda não possui cadastro?"} <Link href={isRegister ? "/login" : "/register"}>{isRegister ? "Entrar" : "Criar conta"}</Link></p></section></main>;
}

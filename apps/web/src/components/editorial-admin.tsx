"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { components } from "../generated/api";

type AdminPost = components["schemas"]["EditorialAdminPostResponse"];
type AdminList = components["schemas"]["EditorialAdminPostListResponse"];
type CreatePayload = components["schemas"]["EditorialPostCreateRequest"];
type Block = components["schemas"]["EditorialBlock"];

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const blockTypes = ["FACT", "THIRD_PARTY_CONSENSUS", "CONDITIONAL_SCENARIO", "RISK", "LIMITATION"] as const;

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, {
    ...init,
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/json", ...init?.headers },
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.status === 204 ? (undefined as T) : response.json() as Promise<T>;
}

export function EditorialAdminPanel() {
  const [posts, setPosts] = useState<AdminPost[]>([]);
  const [slug, setSlug] = useState("");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [text, setText] = useState("");
  const [type, setType] = useState<(typeof blockTypes)[number]>("FACT");
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await requestJson<AdminList>("/api/v1/editorial/admin/posts");
      setPosts(result.items);
      setError(undefined);
    } catch { setError("Acesso editorial indisponível ou não autorizado."); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    let active = true;
    queueMicrotask(() => { if (active) void load(); });
    return () => { active = false; };
  }, [load]);

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const block: Block = { content_type: type, text: text.trim(), sources: [] };
    const payload: CreatePayload = { slug: slug.trim(), title: title.trim(), summary: summary.trim() || null, blocks: text.trim() ? [block] : [] };
    try {
      await requestJson<AdminPost>("/api/v1/editorial/admin/posts", { method: "POST", body: JSON.stringify(payload) });
      setSlug(""); setTitle(""); setSummary(""); setText(""); await load();
    } catch { setError("Não foi possível criar o rascunho. Revise os campos e permissões."); }
  }

  async function transition(id: string, action: "validate" | "submit-review" | "approve" | "publish" | "archive") {
    try { await requestJson(`/api/v1/editorial/admin/posts/${id}/${action}`, { method: "POST" }); await load(); }
    catch { setError("Transição recusada: valide o conteúdo e confirme seu papel editorial."); }
  }

  return <main className="editorial-admin-page terminal-root">
    <header className="editorial-admin-header"><div><p className="eyebrow">PARTICLE ATLAS / EDITORIAL</p><h1>Morning Call administrativo</h1></div><button type="button" onClick={() => void load}>Atualizar</button></header>
    <p className="editorial-admin-disclaimer">Área interna para conteúdo factual. Não constitui recomendação de investimento, oferta ou solicitação de ordem.</p>
    <form className="editorial-admin-form" onSubmit={create}>
      <label>Slug<input value={slug} onChange={(event) => setSlug(event.target.value)} required pattern="[a-z0-9][a-z0-9-]*" /></label>
      <label>Título<input value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
      <label>Resumo<input value={summary} onChange={(event) => setSummary(event.target.value)} /></label>
      <label>Tipo<select value={type} onChange={(event) => setType(event.target.value as (typeof blockTypes)[number])}>{blockTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
      <label className="editorial-admin-wide">Texto factual<textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Opcional; FACT exige fonte antes da publicação." /></label>
      <button type="submit">Criar rascunho</button>
    </form>
    {error && <p className="state-note" role="alert">{error}</p>}
    {loading ? <p className="muted">Carregando conteúdo editorial...</p> : <div className="editorial-admin-list">{posts.map((post) => <article className="editorial-admin-card" key={post.id}><div><p className="eyebrow">{post.status} · v{post.version}</p><h2>{post.title}</h2><p className="muted">{post.slug}</p></div><div className="editorial-admin-actions">{post.status === "DRAFT" && <button type="button" onClick={() => void transition(post.id, "validate")}>Validar</button>}{post.status === "DRAFT" && <button type="button" onClick={() => void transition(post.id, "submit-review")}>Enviar para revisão</button>}{post.status === "UNDER_REVIEW" && <button type="button" onClick={() => void transition(post.id, "approve")}>Aprovar</button>}{post.status === "APPROVED" && <button type="button" onClick={() => void transition(post.id, "publish")}>Publicar</button>}{post.status === "PUBLISHED" && <button type="button" onClick={() => void transition(post.id, "archive")}>Arquivar</button>}</div></article>)}</div>}
  </main>;
}

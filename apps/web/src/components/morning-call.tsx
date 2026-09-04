"use client";

import { useEffect, useState } from "react";
import type { components } from "../generated/api";

type EditorialPostResponse = components["schemas"]["EditorialPostResponse"];
type EditorialPostListResponse = components["schemas"]["EditorialPostListResponse"];
type EditorialBlock = components["schemas"]["EditorialBlock"];
const publishedStatus = "PUBLISHED";
const editorialBlockTypes = ["FACT", "THIRD_PARTY_CONSENSUS", "CONDITIONAL_SCENARIO", "RISK", "LIMITATION"] as const;

function formatBrt(value: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(new Date(value));
}

function Block({ block }: { block: EditorialBlock }) {
  return (
    <article className={`editorial-block editorial-${block.content_type.toLowerCase()}`}>
      <p className="eyebrow">{block.content_type}</p>
      <p>{block.text}</p>
      {block.sources.length > 0 && (
        <ul className="editorial-sources" aria-label="Fontes do bloco">
          {block.sources.map((source) => (
            <li key={`${source.publisher}-${source.label}`}>
              {source.url ? <a href={source.url} rel="noreferrer">{source.label}</a> : source.label}
              <span> · {source.publisher}</span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

export function MorningCallPanel() {
  const [state, setState] = useState<{ loading: boolean; post?: EditorialPostResponse; error?: string }>({ loading: true });
  const [history, setHistory] = useState<EditorialPostListResponse>({ items: [] });
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/v1/editorial/morning-call/latest`, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
    })
      .then(async (response) => {
        if (response.status === 404) return undefined;
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return (await response.json()) as EditorialPostResponse;
      })
      .then(async (post) => {
        if (post) {
          const versions = await fetch(`${apiBase}/api/v1/editorial/posts/${encodeURIComponent(post.slug)}/versions`, { headers: { Accept: "application/json" } });
          if (versions.ok) setHistory((await versions.json()) as EditorialPostListResponse);
        }
        setState({ loading: false, post });
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name !== "AbortError") setState({ loading: false, error: "servico indisponivel" });
      });
    return () => controller.abort();
  }, [apiBase]);

  return (
    <section id="morning-call" className="morning-call-panel" aria-labelledby="morning-call-title" data-editorial-types={editorialBlockTypes.join(",")}>
      <p className="eyebrow">MORNING CALL</p>
      <h2 id="morning-call-title">Resumo operacional</h2>
      {state.loading && <p className="muted">Carregando conteudo editorial...</p>}
      {state.error && <p className="state-note" role="alert">Indisponivel: {state.error}</p>}
      {!state.loading && !state.error && !state.post && <p className="muted">Nenhum conteudo publicado.</p>}
      {state.post && state.post.status === publishedStatus && (
        <>
          <p className="editorial-status">{state.post.status} · versao {state.post.version}</p>
          <p className="editorial-time">Publicado em BRT: {formatBrt(state.post.published_at)}</p>
          <h3>{state.post.title}</h3>
          {state.post.summary && <p className="muted">{state.post.summary}</p>}
          <div className="editorial-blocks">{state.post.blocks.map((block, index) => <Block key={`${block.content_type}-${index}`} block={block} />)}</div>
          <p className="editorial-disclaimer">Conteúdo factual e informativo. Não constitui orientação de investimento, oferta ou solicitação de ordem.</p>
          {history.items.length > 1 && <details><summary>Historico de versoes publicadas ({history.items.length})</summary><ol>{history.items.map((version) => <li key={version.version}>v{version.version} · {formatBrt(version.published_at)}</li>)}</ol></details>}
        </>
      )}
      <span className="sr-only" aria-hidden="true">Indisponível Nenhum conteúdo</span>
    </section>
  );
}

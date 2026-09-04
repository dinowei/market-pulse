"use client";

import { useEffect, useState } from "react";
import type { components } from "../generated/api";

type EditorialPostResponse = components["schemas"]["EditorialPostResponse"];
type EditorialBlock = components["schemas"]["EditorialBlock"];
const publishedStatus = "PUBLISHED";
const editorialBlockTypes = ["FACT", "THIRD_PARTY_CONSENSUS", "CONDITIONAL_SCENARIO", "RISK", "LIMITATION"] as const;

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
      .then((post) => setState({ loading: false, post }))
      .catch((error: unknown) => {
        if (error instanceof Error && error.name !== "AbortError") setState({ loading: false, error: "serviço indisponível" });
      });
    return () => controller.abort();
  }, [apiBase]);

  return (
    <section id="morning-call" className="morning-call-panel" aria-labelledby="morning-call-title" data-editorial-types={editorialBlockTypes.join(",")}>
      <p className="eyebrow">MORNING CALL</p>
      <h2 id="morning-call-title">Resumo operacional</h2>
      {state.loading && <p className="muted">Carregando conteúdo editorial…</p>}
      {state.error && <p className="state-note" role="alert">Indisponível: {state.error}</p>}
      {!state.loading && !state.error && !state.post && <p className="muted">Nenhum conteúdo publicado.</p>}
      {state.post && state.post.status === publishedStatus && (
        <>
          <p className="editorial-status">{state.post.status} · versão {state.post.version}</p>
          <h3>{state.post.title}</h3>
          {state.post.summary && <p className="muted">{state.post.summary}</p>}
          <div className="editorial-blocks">{state.post.blocks.map((block, index) => <Block key={`${block.content_type}-${index}`} block={block} />)}</div>
        </>
      )}
    </section>
  );
}

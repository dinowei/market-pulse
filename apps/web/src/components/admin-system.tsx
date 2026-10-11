"use client";

import { useEffect, useState } from "react";

import type { components } from "../generated/api";
import { formatReason } from "../lib/unavailable-reasons";

type AdminSystem = components["schemas"]["AdminSystemResponse"];
type RegistryItem = components["schemas"]["AdminProviderRegistryItem"];
type Section = {
  key: string;
  label: string;
  value: string;
  checkedAt: string;
  tone?: "ok" | "degraded" | "down";
};

function requestId(): string {
  return typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : "00000000-0000-4000-8000-000000000000";
}

function sections(payload: AdminSystem): Section[] {
  return [
    {
      key: "postgres",
      label: "PostgreSQL",
      value: payload.postgres.status,
      checkedAt: payload.postgres.checked_at,
      tone: payload.postgres.status as Section["tone"],
    },
    {
      key: "redis",
      label: "Redis",
      value: payload.redis.status,
      checkedAt: payload.redis.checked_at,
      tone: payload.redis.status as Section["tone"],
    },
    {
      key: "openapi",
      label: "Contrato OpenAPI",
      value: payload.openapi.version,
      checkedAt: payload.openapi.checked_at,
    },
    {
      key: "jobs",
      label: "Jobs / refresh",
      value: payload.background_jobs.last_refresh_at ?? "sem execução registrada",
      checkedAt: payload.background_jobs.checked_at,
    },
    {
      key: "providers",
      label: "Governança de providers",
      value: `${(payload.providers.items ?? []).filter((item) => item.access === "allowed").length}/${(payload.providers.items ?? []).length} permitidos`,
      checkedAt: payload.providers.checked_at,
    },
    {
      key: "quarantine",
      label: "Quarentena",
      value: `${payload.quarantine.price_anomalies + payload.quarantine.corporate_actions} registros`,
      checkedAt: payload.quarantine.checked_at,
      tone: payload.quarantine.price_anomalies + payload.quarantine.corporate_actions > 0 ? "degraded" : "ok",
    },
    {
      key: "locks",
      label: "Locks",
      value: `${(payload.locks.items ?? []).length} ativos`,
      checkedAt: payload.locks.checked_at,
    },
    {
      key: "editorial",
      label: "Editorial",
      value: `${payload.editorial.archived_versions} versões arquivadas`,
      checkedAt: payload.editorial.checked_at,
    },
    {
      key: "volumetrics",
      label: "Volumetria",
      value: `${payload.volumetrics.active_users} usuários · ${payload.volumetrics.active_portfolios} carteiras`,
      checkedAt: payload.volumetrics.checked_at,
    },
  ];
}

export function AdminSystemPanel() {
  const [payload, setPayload] = useState<AdminSystem | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = requestId();
    fetch("/api/v1/admin/system", {
      credentials: "include",
      headers: { "X-Request-ID": id },
    })
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 403 ? "Acesso restrito a administradores." : "Painel indisponível.");
        return (await response.json()) as AdminSystem;
      })
      .then(setPayload)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Painel indisponível."));
  }, []);

  return (
    <main id="main-content" className="admin-system-page">
      <header className="admin-system-header">
        <div>
          <p className="eyebrow">PARTICLE ATLAS / OPERAÇÕES</p>
          <h1>Painel do sistema</h1>
          <p className="muted">Visibilidade operacional interna. Sem dados sensíveis, recomendações ou credenciais.</p>
        </div>
        {payload && <span className="admin-system-request">request_id {payload.request_id}</span>}
      </header>
      {error && <p className="admin-system-error" role="alert">{error}</p>}
      {!payload && !error && <p className="loading-state">Consultando componentes internos…</p>}
      {payload && (
        <>
          <p className="admin-system-checked">Última verificação: {new Date(payload.checked_at).toLocaleString("pt-BR")}</p>
          <section className="admin-system-grid" aria-label="Status operacional">
            {sections(payload).map((section) => (
              <article className={`admin-system-card admin-system-card-${section.tone ?? "neutral"}`} key={section.key}>
                <p className="eyebrow">{section.label}</p>
                <strong>{section.value}</strong>
                <small>checado {new Date(section.checkedAt).toLocaleTimeString("pt-BR")}</small>
              </article>
            ))}
          </section>
          {(payload.providers.registry ?? []).length > 0 && <ProviderRegistry items={payload.providers.registry ?? []} />}
          <p className="admin-system-note">Diagnósticos são agregados e mascarados. Provider, dataset e licença permanecem default deny até aprovação documental.</p>
        </>
      )}
    </main>
  );
}

// ADR-025: the code registry, read-only. Credentials show only as present or absent, and
// "Uso agora" is the fail-closed decision: nothing is used before ACTIVE + license + key.
export function ProviderRegistry({ items }: { items: RegistryItem[] }) {
  return (
    <section className="admin-provider-registry" aria-labelledby="provider-registry-title">
      <h2 id="provider-registry-title">Registro de providers</h2>
      <p className="muted">Um provider só é usado com status ACTIVE, licença aprovada e credencial presente. Ter a chave não ativa nada.</p>
      <div className="table-wrap"><table>
        <caption>Providers preparados, status, credenciais e motivo de bloqueio</caption>
        <thead><tr><th scope="col">Provider</th><th scope="col">Status</th><th scope="col">Mercados e capacidades</th><th scope="col">Licença</th><th scope="col">Credenciais</th><th scope="col">Uso agora</th><th scope="col">Limites documentados</th><th scope="col">Verificado em</th></tr></thead>
        <tbody>{items.map((item) => <tr key={item.provider_id}>
          <th scope="row">{item.display_name}<br /><small>{item.provider_id}</small></th>
          <td>{item.status}</td>
          <td>{item.markets.join(", ")}<br /><small>{item.capabilities.join(", ") || "nenhuma"}</small></td>
          <td>{item.license_status}</td>
          <td>{Object.entries(item.credentials).map(([name, present]) => <span key={name} className="admin-credential">{name}: {present ? "presente" : "ausente"}</span>)}</td>
          <td>{item.activation === "ACTIVE" ? "Ativo" : formatReason(item.activation)}{item.blocked_reason && <><br /><small>{item.blocked_reason}</small></>}</td>
          <td><small>{item.rate_limits}</small></td>
          <td>{item.verified_on}</td>
        </tr>)}</tbody>
      </table></div>
    </section>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";

import type { components } from "../generated/api";
import { apiRequest, httpStatus, isAbort } from "../lib/api-client";

type AuthUser = components["schemas"]["AuthUserResponse"];

// Typed by the user before the irreversible deletion is enabled.
export const DELETE_CONFIRMATION = "EXCLUIR";

function errorMessage(error: unknown, action: string): string {
  const status = httpStatus(error);
  if (status === 401) return "Sua sessão expirou. Entre de novo para continuar.";
  if (status === 429) return "Muitas requisições; aguarde alguns segundos e tente de novo.";
  if (status === 503) return `Não foi possível ${action} agora: serviço indisponível. Nada foi alterado.`;
  return `Não foi possível ${action}. Nada foi alterado.`;
}

export function AccountPanel() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [signedOut, setSignedOut] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [exportMessage, setExportMessage] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<AuthUser>("/api/v1/auth/me", { signal: controller.signal })
      .then(setUser)
      .catch((error: unknown) => { if (!isAbort(error)) { if (httpStatus(error) === 401) setSignedOut(true); else setLoadError(errorMessage(error, "carregar sua conta")); } });
    return () => controller.abort();
  }, []);

  async function exportData() {
    setBusy(true);
    setExportMessage("");
    try {
      const data = await apiRequest<unknown>("/api/v1/account/data-export");
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = document.createElement("a");
      link.href = url;
      link.download = `market-pulse-meus-dados-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setExportMessage("Exportação gerada. O arquivo contém seus dados pessoais; guarde-o com cuidado.");
    } catch (error) {
      setExportMessage(errorMessage(error, "exportar seus dados"));
    } finally {
      setBusy(false);
    }
  }

  async function deleteAccount(event: FormEvent) {
    event.preventDefault();
    if (confirmation !== DELETE_CONFIRMATION || !acknowledged) return;
    setBusy(true);
    setDeleteError("");
    try {
      await apiRequest("/api/v1/account", { method: "DELETE" });
      router.push("/login");
    } catch (error) {
      setDeleteError(errorMessage(error, "excluir a conta"));
      setBusy(false);
    }
  }

  if (signedOut) return <section className="account-panel" aria-labelledby="account-title"><h1 id="account-title">Minha conta</h1><p className="muted"><Link href="/login">Entre</Link> para exportar seus dados ou excluir a conta.</p></section>;
  if (loadError) return <section className="account-panel" aria-labelledby="account-title"><h1 id="account-title">Minha conta</h1><p className="state-note" role="alert">{loadError}</p></section>;
  if (!user) return <section className="account-panel" aria-labelledby="account-title"><h1 id="account-title">Minha conta</h1><p className="loading-state">Carregando conta…</p></section>;

  const canDelete = confirmation === DELETE_CONFIRMATION && acknowledged && !busy;
  return (
    <section className="account-panel" aria-labelledby="account-title">
      <p className="eyebrow">CONTA / PRIVACIDADE</p>
      <h1 id="account-title">Minha conta</h1>
      <dl className="meta-grid compact"><div><dt>E-mail</dt><dd>{user.email}</dd></div><div><dt>Situação</dt><dd>{user.status}</dd></div></dl>

      <section aria-labelledby="export-title">
        <h2 id="export-title">Exportar meus dados</h2>
        <p className="muted">Gera um arquivo JSON com sua conta, watchlists, carteiras e eventos, com valores em texto decimal exato.</p>
        <button type="button" className="control" disabled={busy} onClick={() => void exportData()}>Exportar meus dados</button>
        <p role="status" aria-live="polite" className="muted">{exportMessage}</p>
      </section>

      <section aria-labelledby="delete-title" className="account-danger">
        <h2 id="delete-title">Excluir conta</h2>
        <p>A exclusão é <strong>irreversível</strong>. Ela:</p>
        <ul>
          <li>troca seu e-mail por um pseudônimo e encerra as sessões em todos os dispositivos;</li>
          <li>renomeia suas carteiras para &quot;Carteira removida&quot; e apaga as notas dos eventos;</li>
          <li>mantém os registros financeiros anonimizados e um registro de auditoria da exclusão.</li>
        </ul>
        <p className="muted">Se quiser uma cópia, exporte seus dados antes.</p>
        <form onSubmit={deleteAccount}>
          <label htmlFor="delete-confirmation">Digite {DELETE_CONFIRMATION} para confirmar</label>
          <input id="delete-confirmation" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="off" />
          <label className="account-ack"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} /> Entendo que a exclusão não pode ser desfeita.</label>
          <button type="submit" className="control" disabled={!canDelete}>Excluir minha conta</button>
        </form>
        {deleteError && <p className="state-note" role="alert">{deleteError}</p>}
      </section>
    </section>
  );
}

"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState, useSyncExternalStore } from "react";

import type { components } from "../generated/api";
import { apiRequest, httpStatus, isAbort } from "../lib/api-client";
import { applyPalette, applyTheme, currentPalette, currentTheme, subscribePalette, subscribeTheme } from "../lib/theme";
import styles from "./private-pages.module.css";

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
  const [lists, setLists] = useState<number | null>(null);
  const [portfolios, setPortfolios] = useState<number | null>(null);
  const theme = useSyncExternalStore(subscribeTheme, currentTheme, () => "dark" as const);
  const palette = useSyncExternalStore(subscribePalette, currentPalette, () => "default" as const);

  useEffect(() => {
    const controller = new AbortController();
    apiRequest<{ items: unknown[] }>("/api/v1/watchlists", { signal: controller.signal }).then((data) => setLists(data.items.length)).catch(() => undefined);
    apiRequest<{ items: unknown[] }>("/api/v1/portfolios", { signal: controller.signal }).then((data) => setPortfolios(data.items.length)).catch(() => undefined);
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
    <div className={styles.page}>
      <section className={styles.profile} aria-labelledby="account-title">
        <span className={styles.avatar} aria-hidden="true">{user.email.charAt(0).toUpperCase()}</span>
        <div>
          <h1 id="account-title">Minha conta</h1>
          <p>{user.email}</p>
          <p>Situação: {user.status}</p>
        </div>
      </section>

      <div className={styles.twoCols}>
        <section className={styles.glass} aria-labelledby="display-title">
          <h2 id="display-title">Exibição</h2>
          <p className="muted">Fica salvo neste navegador.</p>
          <h3>Tema</h3>
          <div className={styles.pills} role="group" aria-label="Tema">
            <button type="button" aria-pressed={theme === "light"} onClick={() => applyTheme("light")}>Claro</button>
            <button type="button" aria-pressed={theme === "dark"} onClick={() => applyTheme("dark")}>Escuro</button>
          </div>
          <h3>Cores de alta e queda</h3>
          <div className={styles.pills} role="group" aria-label="Paleta">
            <button type="button" aria-pressed={palette === "default"} onClick={() => applyPalette("default")}>Padrão</button>
            <button type="button" aria-pressed={palette === "cvd"} onClick={() => applyPalette("cvd")}>Para daltonismo</button>
          </div>
        </section>

        <section className={styles.glass} aria-labelledby="saved-title">
          <h2 id="saved-title">Suas listas e carteiras</h2>
          <ul className={styles.links}>
            <li><Link href="/watchlists"><small>Favoritos e listas</small><strong>{lists === null ? "—" : `${lists} ${lists === 1 ? "lista" : "listas"}`}</strong></Link></li>
            <li><Link href="/portfolios"><small>Carteiras informativas</small><strong>{portfolios === null ? "—" : `${portfolios} ${portfolios === 1 ? "carteira" : "carteiras"}`}</strong></Link></li>
          </ul>
        </section>
      </div>

      <section className={styles.glass} aria-labelledby="export-title">
        <h2 id="export-title">Exportar meus dados</h2>
        <p className="muted">Gera um arquivo JSON com sua conta, watchlists, carteiras e eventos, com valores em texto decimal exato.</p>
        <button type="button" className="control" disabled={busy} onClick={() => void exportData()}>Exportar meus dados</button>
        <p role="status" aria-live="polite" className="muted">{exportMessage}</p>
      </section>

      <section aria-labelledby="delete-title" className={`${styles.glass} account-danger`}>
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
    </div>
  );
}

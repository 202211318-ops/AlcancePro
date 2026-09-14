import { useEffect, useState } from "react";
import api, { getError } from "../api";
import { useAuth } from "../AuthContext";
import { ROLE_LABELS, isAdmin } from "../roles";

export default function Settings() {
  const { user } = useAuth();
  const [status, setStatus] = useState(null);
  const [form, setForm] = useState({
    llm_api_key: "",
    llm_base_url: "https://generativelanguage.googleapis.com/v1beta",
    llm_model: "gemini-flash-latest",
  });
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const { data } = await api.get("/system/status");
    setStatus(data.data);
    setForm((prev) => ({
      ...prev,
      llm_base_url: data.data.llm.base_url,
      llm_model: data.data.llm.model,
    }));
  }

  useEffect(() => {
    load().catch((err) => setError(getError(err)));
  }, []);

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setOk("");
    try {
      await api.put("/system/llm", form);
      setOk("Clave guardada.");
      setForm((prev) => ({ ...prev, llm_api_key: "" }));
      await load();
    } catch (err) {
      setError(getError(err, "No se pudo guardar"));
    } finally {
      setBusy(false);
    }
  }

  const mongo = status?.mongodb;
  const llm = status?.llm;

  return (
    <div className="stack">
      {error && <div className="alert">{error}</div>}
      {ok && <div className="notice">{ok}</div>}

      <article className="panel">
        <h3>Cuenta</h3>
        <p>
          {user.name} · {user.email} · {ROLE_LABELS[user.role] || user.role}
        </p>
      </article>

      <article className="panel">
        <h3>Base MongoDB</h3>
        <p className="muted">
          No hay que importar un archivo. MongoDB ya está en marcha y la aplicación crea sola la base
          <strong> {mongo?.database || "alcancepro"}</strong>. Conexión: <code>{mongo?.uri || "mongodb://127.0.0.1:27017"}</code>
        </p>
        <div className="table-wrap" style={{ marginTop: 12 }}>
          <table>
            <thead>
              <tr>
                <th>Colección</th>
                <th>Registros</th>
              </tr>
            </thead>
            <tbody>
              {(mongo?.collections || []).map((item) => (
                <tr key={item.name}>
                  <td className="mono">{item.name}</td>
                  <td>{item.count}</td>
                </tr>
              ))}
              {(!mongo?.collections || mongo.collections.length === 0) && (
                <tr>
                  <td colSpan={2} className="muted">
                    {mongo?.connected === false ? "MongoDB no está conectado. Ejecute scripts\\start-mongo.ps1" : "Cargando colecciones…"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </article>

      <article className="panel">
        <h3>Gemini (lectura de PDF)</h3>
        <p className="muted">
          El análisis envía los PDF a Gemini para extraer la matriz de alcance. La clave se guarda en el servidor, no en el navegador.
        </p>
        <p>
          Estado actual:{" "}
          {!status
            ? "Cargando…"
            : llm?.configured
              ? `Gemini ${llm.model} (${llm.masked_key})`
              : "Sin clave: extractor local"}
        </p>
        {isAdmin(user) && (
          <form className="stack" onSubmit={save} style={{ marginTop: 12 }}>
            <label>
              Clave de Gemini
              <input
                type="password"
                value={form.llm_api_key}
                onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })}
                placeholder={llm?.masked_key ? `Guardada: ${llm.masked_key}` : "AQ...."}
              />
            </label>
            <label>
              Modelo
              <input value={form.llm_model} onChange={(e) => setForm({ ...form, llm_model: e.target.value })} />
            </label>
            <button className="btn" disabled={busy} type="submit">
              {busy ? "Guardando…" : "Guardar clave"}
            </button>
          </form>
        )}
      </article>
    </div>
  );
}

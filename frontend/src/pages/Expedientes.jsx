import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { getError } from "../api";
import { useAuth } from "../AuthContext";
import { canMutate } from "../roles";

const EMPTY = { name: "", entity: "", sector: "MIXTO", contract_type: "PUBLICO", notes: "" };

export default function Expedientes() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);

  async function load() {
    const { data } = await api.get("/expedientes");
    setItems(data.data || []);
  }

  useEffect(() => {
    load().catch((err) => setError(getError(err)));
  }, []);

  async function create(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/expedientes", form);
      setForm(EMPTY);
      setOpen(false);
      await load();
    } catch (err) {
      setError(getError(err, "No se pudo crear el expediente"));
    } finally {
      setBusy(false);
    }
  }

  async function remove(item) {
    if (!window.confirm(`¿Eliminar ${item.code}? Se borrarán documentos, matriz y entregables.`)) return;
    setError("");
    try {
      await api.delete(`/expedientes/${item.id}`);
      await load();
    } catch (err) {
      setError(getError(err, "No se pudo eliminar el expediente"));
    }
  }

  return (
    <div className="stack">
      <div className="toolbar">
        <p className="muted">{items.length} expediente(s)</p>
        {canMutate(user) && (
          <button className="btn" type="button" onClick={() => setOpen((v) => !v)}>
            {open ? "Cancelar" : "Nuevo"}
          </button>
        )}
      </div>
      {error && <div className="alert">{error}</div>}
      {open && (
        <form className="panel grid-2" onSubmit={create}>
          <label>
            Nombre
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Entidad
            <input value={form.entity} onChange={(e) => setForm({ ...form, entity: e.target.value })} />
          </label>
          <label>
            Sector
            <select value={form.sector} onChange={(e) => setForm({ ...form, sector: e.target.value })}>
              <option value="TI">TI</option>
              <option value="OBRAS">Obras civiles</option>
              <option value="CONSULTORIA">Consultoría</option>
              <option value="SERVICIOS">Servicios</option>
              <option value="MIXTO">Mixto</option>
            </select>
          </label>
          <label>
            Tipo
            <select value={form.contract_type} onChange={(e) => setForm({ ...form, contract_type: e.target.value })}>
              <option value="PUBLICO">Público</option>
              <option value="PRIVADO">Privado</option>
            </select>
          </label>
          <div className="full">
            <button className="btn" disabled={busy} type="submit">
              {busy ? "Creando…" : "Guardar"}
            </button>
          </div>
        </form>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Nombre</th>
              <th>Entidad</th>
              <th>Sector</th>
              <th>Estado</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  No hay expedientes.
                </td>
              </tr>
            )}
            {items.map((item) => (
              <tr key={item.id}>
                <td className="mono">{item.code}</td>
                <td>{item.name}</td>
                <td>{item.entity || "—"}</td>
                <td>{item.sector}</td>
                <td>
                  <span className={`chip status-${item.status}`}>{(item.status || "").replaceAll("_", " ")}</span>
                </td>
                <td>
                  <div className="row-actions">
                    <Link to={`/expedientes/${item.id}`}>Abrir</Link>
                    {canMutate(user) && (
                      <button className="linkish" type="button" onClick={() => remove(item)}>
                        Eliminar
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

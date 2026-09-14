import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { getError } from "../api";
import { useAuth } from "../AuthContext";
import { canMutate } from "../roles";

const DOC_TYPES = [
  ["BASES", "Bases / TDR / ET"],
  ["CONSULTAS", "Consultas y respuestas"],
  ["PROPUESTA", "Propuesta del postor"],
  ["CONTRATO", "Contrato firmado"],
  ["ADENDA", "Adenda"],
  ["ANEXO", "Anexo técnico"],
  ["OTRO", "Otro"],
];

export default function ExpedienteDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const editable = canMutate(user);
  const [tab, setTab] = useState("documentos");
  const [expediente, setExpediente] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [checklist, setChecklist] = useState([]);
  const [deliverables, setDeliverables] = useState([]);
  const [docType, setDocType] = useState("BASES");
  const [files, setFiles] = useState([]);
  const [fileKey, setFileKey] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("TODOS");
  const [query, setQuery] = useState("");

  async function loadHeader() {
    const { data } = await api.get(`/expedientes/${id}`);
    setExpediente(data.data);
  }

  async function loadDocs() {
    const { data } = await api.get(`/expedientes/${id}/documents`);
    setDocuments(data.data);
  }

  async function loadMatrix() {
    const [a, b] = await Promise.all([
      api.get(`/expedientes/${id}/checklist`),
      api.get(`/expedientes/${id}/deliverables`),
    ]);
    setChecklist(a.data.data);
    setDeliverables(b.data.data);
  }

  async function refreshAll() {
    await Promise.all([loadHeader(), loadDocs(), loadMatrix()]);
  }

  useEffect(() => {
    refreshAll().catch((err) => setError(getError(err)));
  }, [id]);

  useEffect(() => {
    const status = expediente?.latest_job?.status;
    if (!["QUEUED", "RUNNING"].includes(status)) return undefined;
    const timer = setInterval(() => {
      refreshAll().catch(() => {});
    }, 2500);
    return () => clearInterval(timer);
  }, [expediente?.latest_job?.status]);

  async function upload(event) {
    event.preventDefault();
    if (!files.length) return;
    setBusy(true);
    setError("");
    const body = new FormData();
    body.append("doc_type", docType);
    files.forEach((item) => body.append("files", item));
    try {
      const { data } = await api.post(`/expedientes/${id}/documents`, body);
      setFiles([]);
      setFileKey((key) => key + 1);
      if (data.message) setError(data.message);
      await Promise.all([loadDocs(), loadHeader()]);
    } catch (err) {
      setError(getError(err, "No se pudo cargar el documento"));
    } finally {
      setBusy(false);
    }
  }

  async function removeDoc(docId) {
    if (!window.confirm("¿Eliminar este documento?")) return;
    await api.delete(`/documents/${docId}`);
    await loadDocs();
  }

  async function analyze() {
    setBusy(true);
    setError("");
    try {
      await api.post(`/expedientes/${id}/analyze`);
      await loadHeader();
    } catch (err) {
      setError(getError(err, "No se pudo iniciar el análisis"));
    } finally {
      setBusy(false);
    }
  }

  async function exportExcel() {
    setError("");
    try {
      const response = await api.get(`/expedientes/${id}/export`, { responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `Checklist_Alcance_Proyecto_${expediente?.code || "export"}.xlsx`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(getError(err, "No se pudo exportar el Excel"));
    }
  }

  async function patchItem(itemId, payload) {
    const { data } = await api.patch(`/checklist/${itemId}`, payload);
    setChecklist((rows) => rows.map((row) => (row.id === itemId ? data.data : row)));
  }

  async function patchDeliverable(itemId, payload) {
    const { data } = await api.patch(`/deliverables/${itemId}`, payload);
    setDeliverables((rows) => rows.map((row) => (row.id === itemId ? data.data : row)));
  }

  const visibleRows = useMemo(() => {
    return checklist.filter((row) => {
      if (filter !== "TODOS" && row.scope_kind !== filter) return false;
      if (query) {
        const hay = `${row.numeral} ${row.hierarchy} ${row.bases} ${row.consultas} ${row.propuesta} ${row.contrato}`.toLowerCase();
        if (!hay.includes(query.toLowerCase())) return false;
      }
      return true;
    });
  }, [checklist, filter, query]);

  if (!expediente) {
    return error ? <div className="alert">{error}</div> : <p className="muted">Cargando…</p>;
  }
  const job = expediente.latest_job;
  const analyzing = ["QUEUED", "RUNNING"].includes(job?.status);
  const stats = expediente.stats || {};

  return (
    <div className="stack">
      <Link className="crumb" to="/expedientes">
        ← Expedientes
      </Link>
      <div className="hero-card compact">
        <div>
          <p className="kicker">{expediente.code}</p>
          <h2>{expediente.name}</h2>
          <p>
            {expediente.entity || "Entidad no registrada"} · {expediente.sector} · {expediente.contract_type}
          </p>
          <div className="chips">
            <span className={`chip status-${expediente.status}`}>{(expediente.status || "").replaceAll("_", " ")}</span>
            <span className="chip">Docs {stats.documents || 0}</span>
            <span className="chip">Filas {stats.checklist || 0}</span>
            <span className="chip">Entregables {stats.deliverables || 0}</span>
            <span className="chip warn">Contradicciones {stats.contradictions || 0}</span>
          </div>
          {job?.error && <div className="alert">{job.error}</div>}
          {job?.summary?.objeto && <p className="muted">{job.summary.objeto}</p>}
        </div>
        <div className="stack tight">
          {editable && (
            <button className="btn" disabled={busy || analyzing} onClick={analyze} type="button">
              {analyzing ? "Analizando…" : "Ejecutar análisis"}
            </button>
          )}
          <button className="btn ghost" disabled={!stats.checklist} onClick={exportExcel} type="button">
            Descargar Excel
          </button>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      <div className="tabs">
        {["documentos", "checklist", "entregables"].map((key) => (
          <button key={key} className={tab === key ? "tab active" : "tab"} onClick={() => setTab(key)} type="button">
            {key === "documentos" ? "Documentos" : key === "checklist" ? "Matriz de alcance" : "Entregables"}
          </button>
        ))}
      </div>

      {tab === "documentos" && (
        <div className="stack">
          {editable && (
          <form className="panel upload-row" onSubmit={upload}>
            <label>
              Tipo documental
              <select value={docType} onChange={(e) => setDocType(e.target.value)}>
                {DOC_TYPES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Archivos PDF / DOCX / XLSX / TXT (hasta 100 MB c/u)
              <input
                key={fileKey}
                type="file"
                multiple
                accept=".pdf,.docx,.txt,.md,.xlsx,.xls,application/pdf"
                onChange={(e) => setFiles(Array.from(e.target.files || []))}
                required
              />
              {files.length > 0 && (
                <span className="muted file-hint">
                  {files.length} archivo(s): {files.map((item) => item.name).join(", ")}
                </span>
              )}
            </label>
            <button className="btn" disabled={busy} type="submit">
              {busy ? "Cargando…" : files.length > 1 ? `Adjuntar ${files.length}` : "Adjuntar"}
            </button>
          </form>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tipo</th>
                  <th>Archivo</th>
                  <th>Extracción</th>
                  <th>Tamaño</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {documents.length === 0 && (
                  <tr>
                    <td colSpan={5} className="muted">
                      Cargue las bases, el pliego de consultas, la propuesta y el contrato. El sistema no asume nombres de archivo.
                    </td>
                  </tr>
                )}
                {documents.map((doc) => (
                  <tr key={doc.id}>
                    <td>{doc.doc_type}</td>
                    <td>{doc.original_name}</td>
                    <td>
                      <span className={`chip status-${doc.extraction_status}`}>{doc.extraction_status}</span>
                    </td>
                    <td>{Math.round(doc.size_bytes / 1024)} KB</td>
                    <td>
                      {editable && (
                        <button className="linkish" onClick={() => removeDoc(doc.id)} type="button">
                          Quitar
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "checklist" && (
        <div className="stack">
          <div className="toolbar">
            <div className="chips">
              {["TODOS", "PRODUCTO", "PROYECTO"].map((key) => (
                <button key={key} className={filter === key ? "chip active" : "chip"} onClick={() => setFilter(key)} type="button">
                  {key === "TODOS" ? "Todos" : key === "PRODUCTO" ? "Alcance del producto" : "Alcance del proyecto"}
                </button>
              ))}
            </div>
            <input placeholder="Buscar numeral o texto" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <div className="table-wrap matrix">
            <table>
              <thead>
                <tr>
                  <th>A · Numeral</th>
                  <th>B · Bases / TDR / ET</th>
                  <th>C · Consultas</th>
                  <th>D · Propuesta</th>
                  <th>E · Contrato</th>
                  <th>F · Cumplimiento</th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.length === 0 && (
                  <tr>
                    <td colSpan={6} className="muted">
                      Aún no hay matriz. Cargue documentos y pulse Ejecutar análisis.
                    </td>
                  </tr>
                )}
                {visibleRows.map((row) => (
                  <tr key={row.id} className={row.has_contradiction ? "flag" : ""}>
                    <td>
                      <strong className="mono">{row.numeral}</strong>
                      <small>{row.scope_kind}</small>
                      {row.hierarchy && <small>{row.hierarchy}</small>}
                    </td>
                    <td>{row.bases}</td>
                    <td>{row.consultas}</td>
                    <td>{row.propuesta}</td>
                    <td>{row.contrato}</td>
                    <td>
                      <select value={row.compliance} onChange={(e) => patchItem(row.id, { compliance: e.target.value })}>
                        <option value="PENDIENTE">☐ Pendiente</option>
                        <option value="CUMPLIDO">☑ Cumplido</option>
                        <option value="NO_CUMPLE">☒ No cumple</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "entregables" && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Numeral</th>
                <th>Entregable identificado</th>
                <th>Referencia documental</th>
                <th>Plazo de entrega</th>
              </tr>
            </thead>
            <tbody>
              {deliverables.length === 0 && (
                <tr>
                  <td colSpan={4} className="muted">
                    Los entregables de gestión aparecerán aquí después del análisis.
                  </td>
                </tr>
              )}
              {deliverables.map((row) => (
                <tr key={row.id}>
                  <td className="mono">{row.numeral}</td>
                  <td>{row.name}</td>
                  <td>
                    <input defaultValue={row.reference} onBlur={(e) => patchDeliverable(row.id, { reference: e.target.value })} />
                  </td>
                  <td>
                    <input defaultValue={row.due_term} onBlur={(e) => patchDeliverable(row.id, { due_term: e.target.value })} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

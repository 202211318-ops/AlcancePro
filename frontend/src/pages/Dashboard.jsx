import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { getError } from "../api";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/dashboard")
      .then((res) => setData(res.data.data))
      .catch((err) => setError(getError(err)));
  }, []);

  if (error) return <div className="alert">{error}</div>;
  if (!data) return <p className="muted">Cargando…</p>;

  const cards = [
    { label: "Expedientes", value: data.expedientes },
    { label: "Pendientes", value: data.pending_items },
    { label: "Contradicciones", value: data.contradictions },
    { label: "Análisis", value: data.engine === "gemini" ? "Gemini" : "Local" },
  ];

  return (
    <div className="stack">
      <div className="toolbar">
        <p className="muted">Resumen de expedientes en MongoDB ({data.mongodb_db}).</p>
        <Link className="btn" to="/expedientes">
          Expedientes
        </Link>
      </div>
      <div className="grid-4">
        {cards.map((card) => (
          <article className="stat" key={card.label}>
            <p>{card.label}</p>
            <strong>{card.value}</strong>
          </article>
        ))}
      </div>
      <article className="panel">
        <h3>Estados</h3>
        <div className="chips">
          {["BORRADOR", "EN_ANALISIS", "LISTO", "ARCHIVADO"].map((status) => (
            <span className={`chip status-${status}`} key={status}>
              {status.replaceAll("_", " ")} · {data.by_status?.[status] || 0}
            </span>
          ))}
        </div>
      </article>
    </div>
  );
}

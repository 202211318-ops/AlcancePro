import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import api, { getError } from "../api";
import { useAuth } from "../AuthContext";
import { ROLE_LABELS } from "../roles";

export default function Users() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    const { data } = await api.get("/users");
    setItems(data.data || []);
  }

  useEffect(() => {
    if (user?.role === "ADMIN") load().catch((err) => setError(getError(err)));
  }, [user?.role]);

  if (user?.role !== "ADMIN") return <Navigate to="/" replace />;

  async function patch(id, payload) {
    try {
      await api.patch(`/users/${id}`, payload);
      await load();
    } catch (err) {
      setError(getError(err));
    }
  }

  return (
    <div className="stack">
      {error && <div className="alert">{error}</div>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Correo</th>
              <th>Rol</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{item.name}</td>
                <td>{item.email}</td>
                <td>
                  <select value={item.role} onChange={(e) => patch(item.id, { role: e.target.value })}>
                    <option value="ADMIN">{ROLE_LABELS.ADMIN}</option>
                    <option value="ANALISTA">{ROLE_LABELS.ANALISTA}</option>
                    <option value="REVISOR">{ROLE_LABELS.REVISOR}</option>
                  </select>
                </td>
                <td>
                  <button className="linkish" type="button" onClick={() => patch(item.id, { is_active: !item.is_active })}>
                    {item.is_active ? "Activo" : "Inactivo"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

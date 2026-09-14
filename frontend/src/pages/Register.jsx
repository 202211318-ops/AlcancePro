import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { getError } from "../api";

export default function Register() {
  const { user, register } = useAuth();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(form);
    } catch (err) {
      setError(getError(err, "No se pudo crear la cuenta"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-panel">
        <div className="brand brand-lg">
          <span className="brand-mark">AP</span>
          <div>
            <strong>AlcancePro</strong>
            <small>Registro</small>
          </div>
        </div>
        <form onSubmit={onSubmit} className="stack">
          {error && <div className="alert">{error}</div>}
          <label>
            Nombre
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
          </label>
          <label>
            Correo
            <input type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </label>
          <label>
            Contraseña
            <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} minLength={8} required />
          </label>
          <button className="btn" disabled={busy} type="submit">
            {busy ? "Creando…" : "Registrarme"}
          </button>
        </form>
        <p className="muted">
          <Link to="/login">Ya tengo cuenta</Link>
        </p>
      </section>
    </div>
  );
}

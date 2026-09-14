import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { getError } from "../api";

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function onSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
    } catch (err) {
      setError(getError(err, "No se pudo iniciar sesión"));
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
            <small>Inicio de sesión</small>
          </div>
        </div>
        <form onSubmit={onSubmit} className="stack" autoComplete="off">
          {error && <div className="alert">{error}</div>}
          <label>
            Correo
            <input
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              type="email"
              name="alcance-correo"
              required
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
            />
          </label>
          <label>
            Contraseña
            <input
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              type="password"
              name="alcance-clave"
              required
              autoComplete="new-password"
            />
          </label>
          <button className="btn" disabled={busy} type="submit">
            {busy ? "Entrando…" : "Entrar"}
          </button>
        </form>
        <p className="muted">
          <Link to="/registro">Crear cuenta</Link>
        </p>
      </section>
    </div>
  );
}

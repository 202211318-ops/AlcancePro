import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { ROLE_LABELS } from "../roles";
import ErrorBoundary from "./ErrorBoundary";

const LINKS = [
  { to: "/", label: "Tablero" },
  { to: "/expedientes", label: "Expedientes" },
  { to: "/usuarios", label: "Usuarios", admin: true },
  { to: "/configuracion", label: "Configuración" },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const visible = LINKS.filter((link) => !link.admin || user.role === "ADMIN");
  const current = visible.find((link) =>
    link.to === "/" ? location.pathname === "/" : location.pathname.startsWith(link.to),
  );

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">AP</span>
          <div>
            <strong>AlcancePro</strong>
            <small>Alcance contractual</small>
          </div>
        </div>
        <nav>
          {visible.map((link) => (
            <NavLink key={link.to} to={link.to} end={link.to === "/"} className="nav-item">
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="who">
            <strong>{user.name}</strong>
            <small>{ROLE_LABELS[user.role] || user.role}</small>
          </div>
          <button className="linkish" onClick={logout} type="button">
            Cerrar sesión
          </button>
        </div>
      </aside>
      <main className="content">
        <header className="topbar">
          <h1>{current?.label || "AlcancePro"}</h1>
          <span className="pill">{user.email}</span>
        </header>
        <section className="page">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </section>
      </main>
    </div>
  );
}

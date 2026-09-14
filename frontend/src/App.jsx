import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./AuthContext";
import AppShell from "./components/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Expedientes from "./pages/Expedientes";
import ExpedienteDetail from "./pages/ExpedienteDetail";
import Users from "./pages/Users";
import Settings from "./pages/Settings";

export default function App() {
  const { loading } = useAuth();
  if (loading) {
    return (
      <div className="boot">
        <div className="boot-mark">AP</div>
        <p>Cargando AlcancePro…</p>
      </div>
    );
  }
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/registro" element={<Register />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="expedientes" element={<Expedientes />} />
        <Route path="expedientes/:id" element={<ExpedienteDetail />} />
        <Route path="usuarios" element={<Users />} />
        <Route path="configuracion" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

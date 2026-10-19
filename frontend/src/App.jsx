import { useCallback, useEffect, useState } from "react";
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api } from "./api.js";
import { initials } from "./lib/helpers.js";
import Login from "./pages/Login.jsx";
import Postular from "./pages/Postular.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Employees from "./pages/Employees.jsx";
import Applicants from "./pages/Applicants.jsx";
import Approvals from "./pages/Approvals.jsx";
import Shifts from "./pages/Shifts.jsx";
import Portal from "./pages/Portal.jsx";
import EmployeeProfileRoute from "./pages/EmployeeProfile.jsx";
import { Loading } from "./components/ui.jsx";

function App() {
  const [user, setUser] = useState(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [toast, setToast] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!localStorage.getItem("rrhh-token")) {
      setSessionReady(true);
      return;
    }
    api("/api/auth/me")
      .then(setUser)
      .catch((error) => {
        localStorage.removeItem("rrhh-token");
        setLoginError(error.message);
      })
      .finally(() => setSessionReady(true));
  }, []);
  useEffect(() => {
    const expireSession = () => {
      setUser(null);
      setLoginError("La sesión venció. Inicia sesión nuevamente.");
      setSessionReady(true);
      navigate("/", { replace: true });
    };
    window.addEventListener("rrhh-session-expired", expireSession);
    return () => window.removeEventListener("rrhh-session-expired", expireSession);
  }, [navigate]);

  const notify = useCallback((message) => {
    setToast(message);
    window.setTimeout(() => setToast(""), 3500);
  }, []);
  const signIn = async (event) => {
    event.preventDefault();
    setLoginError("");
    const data = new FormData(event.currentTarget);
    const body = new URLSearchParams({ username: data.get("username"), password: data.get("password") });
    try {
      const response = await api("/api/auth/token", { method: "POST", body });
      localStorage.setItem("rrhh-token", response.access_token);
      setUser(await api("/api/auth/me"));
      navigate("/panel", { replace: true });
    } catch (error) {
      setLoginError(error.message);
    }
  };
  const signOut = () => {
    localStorage.removeItem("rrhh-token");
    setUser(null);
    navigate("/", { replace: true });
  };

  if (!sessionReady) {
    return <main className="login-page"><Loading /></main>;
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/postular" element={<Postular onBack={() => navigate("/")} />} />
        <Route path="*" element={<Login onSubmit={signIn} error={loginError} />} />
      </Routes>
    );
  }

  return (
    <Routes>
      <Route path="/postular" element={<Postular onBack={() => navigate("/")} />} />
      <Route path="/" element={<Navigate to={user.rol === "empleado" ? "/mi-espacio" : "/panel"} replace />} />
      <Route element={<AppLayout user={user} signOut={signOut} toast={toast} />}>
        <Route path="/panel" element={user.rol === "empleado" ? <Navigate to="/mi-espacio" replace /> : <Dashboard navigate={navigate} notify={notify} />} />
        <Route path="/empleados" element={user.rol === "empleado" ? <Navigate to="/mi-espacio" replace /> : <Employees navigate={navigate} notify={notify} />} />
        <Route path="/empleados/:id" element={user.rol === "empleado" ? <Navigate to="/mi-espacio" replace /> : <EmployeeProfileRoute navigate={navigate} notify={notify} />} />
        <Route path="/postulantes" element={user.rol === "empleado" ? <Navigate to="/mi-espacio" replace /> : <Applicants notify={notify} />} />
        <Route path="/aprobaciones" element={user.rol === "empleado" ? <Navigate to="/mi-espacio" replace /> : <Approvals notify={notify} />} />
        <Route path="/turnos" element={user.rol === "empleado" ? <Navigate to="/mi-espacio" replace /> : <Shifts notify={notify} />} />
        <Route path="/mi-espacio" element={user.rol === "empleado" ? <Portal notify={notify} /> : <Navigate to="/panel" replace />} />
        <Route path="*" element={<Navigate to={user.rol === "empleado" ? "/mi-espacio" : "/panel"} replace />} />
      </Route>
    </Routes>
  );
}

function AppLayout({ user, signOut, toast }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const isEmployee = user.rol === "empleado";
  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" onClick={() => navigate(isEmployee ? "/mi-espacio" : "/panel")} aria-label="Ir al inicio">
          <span className="brand-mark" /> <span>AquaChile</span>
        </button>
        {!isEmployee && (
          <nav className="main-nav" aria-label="Navegación principal">
            <NavButton active={pathname === "/panel"} onClick={() => navigate("/panel")}>Panel</NavButton>
            <NavButton active={pathname.startsWith("/empleados")} onClick={() => navigate("/empleados")}>Empleados</NavButton>
            <NavButton active={pathname === "/postulantes"} onClick={() => navigate("/postulantes")}>Postulantes</NavButton>
            <NavButton active={pathname === "/aprobaciones"} onClick={() => navigate("/aprobaciones")}>Aprobaciones</NavButton>
            <NavButton active={pathname === "/turnos"} onClick={() => navigate("/turnos")}>Turnos</NavButton>
          </nav>
        )}
        {isEmployee && (
          <nav className="main-nav employee-nav" aria-label="Navegación del colaborador">
            <NavButton active={pathname === "/mi-espacio"} onClick={() => navigate("/mi-espacio")}>Mi espacio</NavButton>
            <a href="/mi-espacio#solicitudes">Vacaciones</a><a href="/mi-espacio#asistencia">Asistencia</a><a href="/mi-espacio#documentos">Documentos</a>
          </nav>
        )}
        <button className="user-menu" onClick={signOut} title="Cerrar sesión">
          <span>{user.nombre}</span><span className="avatar avatar-small">{initials(user.nombre)}</span>
        </button>
      </header>
      <main className="page-content"><Outlet /></main>
      {toast && <div className="toast" role="status">{toast}</div>}
    </div>
  );
}

function NavButton({ active, onClick, children }) {
  return <button className={`nav-link ${active ? "active" : ""}`} onClick={onClick}>{children}</button>;
}

export default App;

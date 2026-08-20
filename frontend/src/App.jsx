import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import LoginPage from "./pages/LoginPage";
import UploadPage from "./pages/UploadPage";
import JobsPage from "./pages/JobsPage";
import JobDetailPage from "./pages/JobDetailPage";
import SettingsPage from "./pages/SettingsPage";
import MachiningPage from "./pages/MachiningPage";

function Shell({ children }) {
  const { logout } = useAuth();
  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          Kannon <span>Quote</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Upload
          </NavLink>
          <NavLink to="/jobs">Jobs</NavLink>
          <NavLink to="/machine">Machine</NavLink>
          <NavLink to="/settings">Rates</NavLink>
          <button className="linkish" onClick={logout} type="button">
            Log out
          </button>
        </nav>
      </header>
      {children}
    </div>
  );
}

function Private({ children }) {
  const { token } = useAuth();
  if (!token) return <Navigate to="/login" replace />;
  return <Shell>{children}</Shell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <Private>
            <UploadPage />
          </Private>
        }
      />
      <Route
        path="/jobs"
        element={
          <Private>
            <JobsPage />
          </Private>
        }
      />
      <Route
        path="/jobs/:id"
        element={
          <Private>
            <JobDetailPage />
          </Private>
        }
      />
      <Route
        path="/machine"
        element={
          <Private>
            <MachiningPage />
          </Private>
        }
      />
      <Route
        path="/settings"
        element={
          <Private>
            <SettingsPage />
          </Private>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

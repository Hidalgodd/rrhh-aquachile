export function ErrorNotice({ error, retry }) {
  if (!error) return null;
  return <div className="error-notice" role="alert"><span>{error}</span>{retry && <button className="text-button" onClick={retry}>Reintentar</button>}</div>;
}

export function Loading() {
  return <div className="loading"><span className="spinner" /> Cargando…</div>;
}

export function Field({ label, wide, children }) {
  return <label className={`field ${wide ? "field-wide" : ""}`}><span>{label}</span>{children}</label>;
}

export function StatusBadge({ status }) {
  const labels = { activo: "Activa", licencia: "En licencia", inactivo: "Inactiva", pendiente: "Pendiente", aprobado: "Aprobado", rechazado: "Rechazado", firmado: "Firmado", pendiente_firma: "Falta su firma", al_dia: "Al día", recibido: "Recibido", "en revisión": "En revisión", entrevista: "Entrevista", contratado: "Contratado", futuro: "Futuro", terminado: "Terminado", no_renovar: "No renovar" };
  return <span className={`status-badge status-${status}`}>{labels[status] || status}</span>;
}

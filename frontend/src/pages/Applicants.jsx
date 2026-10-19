import { useCallback, useEffect, useState } from "react";
import { api, download } from "../api.js";
import { request, dateText } from "../lib/helpers.js";
import { ErrorNotice, StatusBadge } from "../components/ui.jsx";

export default function Applicants({ notify }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  const load = useCallback(() => api("/api/postulantes").then(setItems).catch((problem) => setError(problem.message)), []);
  useEffect(() => { load(); }, [load]);
  const downloadCv = (person) => download(`/api/postulantes/${person.id_postulante}/cv`, `${person.nombre.replace(/\s/g, "-")}-CV`).catch((problem) => setError(problem.message));
  const changeStatus = async (id, estado) => {
    try { await request(`/api/postulantes/${id}/estado`, "PATCH", { estado }); notify("Estado de postulación actualizado"); load(); }
    catch (problem) { setError(problem.message); }
  };
  return <section className="content-page">
    <div className="page-heading"><div><h1>Postulantes</h1><p>{items.length} postulaciones recibidas</p></div></div>
    <ErrorNotice error={error} retry={load} />
    <div className="table-card"><table><thead><tr><th>Nombre</th><th>Cargo</th><th>Postulación</th><th>Estado</th><th>CV</th><th>Actualizar</th></tr></thead>
      <tbody>{items.map((person) => <tr key={person.id_postulante}><td><b>{person.nombre}</b><small>{person.correo}</small></td><td>{person.cargo_postulado}</td><td>{dateText(person.fecha_postulacion)}</td><td><StatusBadge status={person.estado} /></td><td><button className="text-button" onClick={() => downloadCv(person)}>Descargar</button></td><td><select value={person.estado} onChange={(event) => changeStatus(person.id_postulante, event.target.value)}><option value="recibido">Recibido</option><option value="en revisión">En revisión</option><option value="entrevista">Entrevista</option><option value="contratado">Contratado</option><option value="rechazado">Rechazado</option></select></td></tr>)}</tbody>
    </table>{!items.length && !error && <p className="empty-state">No hay postulaciones todavía.</p>}</div>
  </section>;
}

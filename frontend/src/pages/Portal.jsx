import { useCallback, useEffect, useState } from "react";
import { api, download } from "../api.js";
import { request, localDateInput, dateText, dayCountText } from "../lib/helpers.js";
import { ErrorNotice, Field, Loading, StatusBadge } from "../components/ui.jsx";

export default function Portal({ notify }) {
  const [summary, setSummary] = useState(null);
  const [requests, setRequests] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [attendance, setAttendance] = useState(null);
  const [type, setType] = useState("vacaciones");
  const [from, setFrom] = useState(localDateInput);
  const [to, setTo] = useState(localDateInput);
  const [calculation, setCalculation] = useState(null);
  const [error, setError] = useState("");
  const downloadFile = (path, filename) => download(path, filename).catch((problem) => setError(problem.message));
  const load = useCallback(async () => {
    try {
      const [person, permits, docs, attendanceInfo] = await Promise.all([
        api("/api/me/resumen"), api("/api/permisos/mios"), api("/api/documentos/mios"), api("/api/asistencia/mia"),
      ]);
      setSummary(person); setRequests(permits); setDocuments(docs); setAttendance(attendanceInfo);
    } catch (problem) { setError(problem.message); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!from || !to) { setCalculation(null); return; }
    api(`/api/permisos/calculo?tipo=${encodeURIComponent(type)}&desde=${from}&hasta=${to}`)
      .then(setCalculation).catch((problem) => setError(problem.message));
  }, [type, from, to]);
  if (!summary || !requests || !attendance) return <section className="content-page"><ErrorNotice error={error} retry={load} />{!error && <Loading />}</section>;
  const createRequest = async () => {
    try { await request("/api/permisos", "POST", { tipo: type, fecha_inicio: from, fecha_termino: to }); notify("Solicitud enviada para aprobación"); load(); }
    catch (problem) { setError(problem.message); }
  };
  const markAttendance = async () => {
    try { await request("/api/asistencia/marcar", "POST"); notify("Asistencia registrada"); load(); }
    catch (problem) { setError(problem.message); }
  };
  const signDocument = async (id) => {
    try { await request(`/api/documentos/${id}/firmar`, "POST"); notify("Documento firmado"); load(); }
    catch (problem) { setError(problem.message); }
  };
  return <section className="content-page portal-page">
    <ErrorNotice error={error} retry={load} />
    <div className="page-heading"><div><h1>Hola, {summary.primer_nombre}</h1><p>{summary.cargo} · {summary.area} · {summary.centro || "Sin centro asignado"}</p></div></div>
    <div className="portal-grid">
      <aside className="balance-card"><div className="balance-wave"><strong>{requests.saldo.disponibles}</strong><b>días disponibles</b></div><p>Te corresponden {requests.saldo.cupo} días al año. Ya usaste {requests.saldo.usados} y tienes {requests.saldo.en_tramite} en trámite.</p><div className="attendance-box" id="asistencia"><h3>Asistencia de hoy</h3><p>Entrada: <b>{attendance.hoy.entrada || "Sin marcar"}</b></p><p>Salida: <b>{attendance.hoy.salida || "Sin marcar"}</b></p><button className="button button-primary" onClick={markAttendance}>{attendance.hoy.entrada ? "Marcar salida" : "Marcar entrada"}</button></div></aside>
      <div className="portal-main">
        <section className="request-card" id="solicitudes"><h2>Pedir días libres</h2><div className="request-fields"><Field label="Tipo"><select value={type} onChange={(event) => setType(event.target.value)}><option value="vacaciones">Vacaciones</option><option value="administrativo">Permiso administrativo</option><option value="licencia medica">Licencia médica</option></select></Field><Field label="Desde"><input type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></Field><Field label="Hasta"><input type="date" value={to} onChange={(event) => setTo(event.target.value)} /></Field></div>
          <p className="muted">{calculation?.mensaje || (calculation?.dias !== undefined ? <>Son <b>{dayCountText(calculation.dias)} hábiles</b>. Tu saldo quedaría en <b>{dayCountText(calculation.saldo_quedaria)}</b>.</> : "Selecciona las fechas para calcular tu solicitud.")}</p>
          <button className="button button-primary" disabled={!calculation?.valido} onClick={createRequest}>Enviar solicitud</button></section>
        <div className="portal-bottom"><section><h2>Mis solicitudes</h2>{requests.solicitudes.map((item) => <div className="simple-row" key={item.id_permiso}><div><b>{item.tipo_label}</b><small>{dateText(item.fecha_inicio)} – {dateText(item.fecha_termino)}</small></div><span>{dayCountText(item.dias)}</span><StatusBadge status={item.estado} /></div>)}</section>
          <section id="documentos"><h2>Mis documentos</h2>{documents.map((doc) => <div className="simple-row document-row" key={doc.id_documento}><div><b>{doc.titulo}</b><small>{doc.tipo} · {dateText(doc.fecha_emision)}</small></div>{doc.estado === "pendiente_firma" ? <button className="text-button" onClick={() => signDocument(doc.id_documento)}>Firmar</button> : <><StatusBadge status={doc.estado} />{doc.tiene_archivo && <button className="text-button" onClick={() => downloadFile(`/api/documentos/${doc.id_documento}/archivo`, doc.titulo)}>Ver</button>}</>}</div>)}<button className="button button-secondary" onClick={() => downloadFile("/api/me/certificado-antiguedad", "certificado-antiguedad.pdf")}>Certificado de antigüedad (PDF)</button></section></div>
      </div>
    </div>
  </section>;
}

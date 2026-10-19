import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, download } from "../api.js";
import { request, dateText, dayCountText, money, initials } from "../lib/helpers.js";
import { ErrorNotice, Field, Loading, StatusBadge } from "../components/ui.jsx";

export default function EmployeeProfileRoute({ navigate, notify }) {
  const { id } = useParams();
  return <EmployeeProfile id={id} navigate={navigate} notify={notify} />;
}

function EmployeeProfile({ id, navigate, notify }) {
  const [person, setPerson] = useState(null);
  const [contracts, setContracts] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [attendance, setAttendance] = useState(null);
  const [tab, setTab] = useState("Contratos");
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const downloadFile = (path, filename) => download(path, filename).catch((problem) => setError(problem.message));
  const load = useCallback(async () => {
    try {
      const [employee, contractInfo, docs, attendanceInfo] = await Promise.all([
        api(`/api/empleados/${id}`), api(`/api/empleados/${id}/contratos`), api(`/api/empleados/${id}/documentos`), api(`/api/asistencia/de/${id}`),
      ]);
      setPerson(employee); setContracts(contractInfo); setDocuments(docs); setAttendance(attendanceInfo);
    } catch (problem) { setError(problem.message); }
  }, [id]);
  useEffect(() => { load(); }, [load]);
  if (!person) return <section className="content-page"><ErrorNotice error={error} retry={load} />{!error && <Loading />}</section>;
  const active = contracts?.vigente;
  const daysLeft = active?.dias_restantes;
  const tabs = ["Resumen", "Contratos", "Documentos", "Asistencia", "Vacaciones"];
  return <section className="content-page profile-page">
    <ErrorNotice error={error} retry={load} />
    <button className="back-link" onClick={() => navigate("/empleados")}>Volver a Personas</button>
    <div className="profile-layout">
      <aside className="profile-aside"><span className="avatar avatar-profile">{initials(`${person.nombres} ${person.apellidos}`)}</span><h1>{person.nombres} {person.apellidos}</h1><p>{person.cargo} · {person.area}</p><p>RUT {person.rut}<br />{person.correo}<br />Ingresó el {dateText(person.fecha_ingreso)}</p><button className="button button-primary" onClick={() => setEditing(true)}>Editar ficha</button><button className="button button-secondary" onClick={() => downloadFile(`/api/empleados/${id}/certificado-antiguedad`, "certificado-antiguedad.pdf")}>Certificado de antigüedad (PDF)</button></aside>
      <div className="profile-detail">
        <div className="profile-tabs">{tabs.map((item) => <button key={item} className={tab === item ? "active" : ""} onClick={() => setTab(item)}>{item}</button>)}</div>
        {tab === "Contratos" && <><h2>Contrato vigente</h2>{active ? <><p>{active.titulo} · sueldo base {money(active.sueldo)}</p><div className="contract-progress"><i style={{ width: `${(active.progreso || 0) * 100}%` }} /><span>hoy</span></div><div className="contract-dates"><span>{dateText(active.fecha_inicio)}</span><span>{dateText(active.fecha_fin)}</span></div><p className="request-summary">{daysLeft !== null && daysLeft <= 30 ? <><b>Vence en {dayCountText(daysLeft)}.</b> Decide si lo renuevas antes del {dateText(active.fecha_fin)}.</> : "Contrato vigente."}</p>{active.renovacion === "pendiente" && active.fecha_fin && <div className="modal-actions"><button className="button button-primary" onClick={async () => { const tipo = active.tipo === "indefinido" ? "plazo fijo" : active.tipo; const fecha_fin = window.prompt("Fecha de término (AAAA-MM-DD)"); if (!fecha_fin) return; try { await request(`/api/contratos/${active.id_contrato}/renovar`, "POST", { tipo, fecha_fin }); notify("Contrato renovado"); load(); } catch (problem) { setError(problem.message); } }}>Renovar contrato</button><button className="text-button" onClick={async () => { try { await request(`/api/contratos/${active.id_contrato}/dejar-vencer`, "POST", {}); notify("Contrato marcado para vencer"); load(); } catch (problem) { setError(problem.message); } }}>Dejar vencer</button></div>}</> : <p className="muted">No hay un contrato vigente registrado.</p>}
          <div className="profile-columns"><section><h3>Historial</h3>{contracts?.historial.map((contract) => <div className="simple-row" key={contract.id_contrato}><div><b>{contract.titulo}</b><small>{dateText(contract.fecha_inicio)} – {dateText(contract.fecha_fin)}</small></div><StatusBadge status={contract.estado} /></div>)}</section><section><h3>Documentos</h3>{documents.map((doc) => <div className="simple-row" key={doc.id_documento}><div><b>{doc.titulo}</b><small>{dateText(doc.fecha_emision)}</small></div><StatusBadge status={doc.estado} /></div>)}</section></div>
        </>}
        {tab === "Resumen" && <div className="profile-summary"><h2>Resumen de la ficha</h2><div className="detail-grid"><span>Estado</span><b><StatusBadge status={person.estado} /></b><span>Centro</span><b>{person.centro || "Sin centro asignado"}</b><span>Grupo / régimen</span><b>{person.grupo ? `Grupo ${person.grupo} · ${person.regimen}` : "Sin turno"}</b><span>Teléfono</span><b>{person.telefono || "—"}</b><span>Dirección</span><b>{person.direccion || "—"}</b><span>Fecha de nacimiento</span><b>{dateText(person.fecha_nacimiento)}</b></div></div>}
        {tab === "Documentos" && <><h2>Documentos</h2>{documents.map((doc) => <div className="simple-row" key={doc.id_documento}><div><b>{doc.titulo}</b><small>{doc.tipo} · {dateText(doc.fecha_emision)}</small></div><StatusBadge status={doc.estado} />{doc.tiene_archivo && <button className="text-button" onClick={() => downloadFile(`/api/documentos/${doc.id_documento}/archivo`, doc.titulo)}>Descargar</button>}</div>)}<DocumentUpload id={id} onSaved={() => { notify("Documento guardado"); load(); }} /></>}
        {tab === "Asistencia" && <><h2>Asistencia · {attendance?.mes}</h2>{attendance?.registros.map((item) => <div className="simple-row" key={item.fecha}><b>{dateText(item.fecha)}</b><span>Entrada {item.entrada || "—"}</span><span>Salida {item.salida || "—"}</span><b>{item.horas ?? "—"} h</b></div>)}</>}
        {tab === "Vacaciones" && <EmployeePermits id={id} />}
      </div>
    </div>
    {editing && <EditEmployeeForm person={person} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); notify("Ficha actualizada"); load(); }} />}
  </section>;
}

function DocumentUpload({ id, onSaved }) {
  const [error, setError] = useState("");
  const submit = async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const formElement = event.currentTarget;
    try { await api(`/api/empleados/${id}/documentos`, { method: "POST", body: form }); formElement.reset(); setError(""); onSaved(); }
    catch (problem) { setError(problem.message); }
  };
  return <form className="upload-form" onSubmit={submit}><h3>Agregar documento</h3><Field label="Título"><input name="titulo" required /></Field><Field label="Tipo"><select name="tipo"><option value="contrato">Contrato</option><option value="anexo">Anexo</option><option value="liquidacion">Liquidación</option><option value="identidad">Identidad</option><option value="otro">Otro</option></select></Field><Field label="Archivo"><input type="file" name="archivo" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx" /></Field><label className="checkbox-field"><input type="checkbox" name="enviar_a_firma" value="true" /> Enviar a firma</label><ErrorNotice error={error} /><button className="button button-primary">Subir documento</button></form>;
}

function EditEmployeeForm({ person, onClose, onSaved }) {
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    const values = Object.fromEntries(new FormData(event.currentTarget).entries());
    if (!values.fecha_nacimiento) values.fecha_nacimiento = null;
    if (!values.telefono) values.telefono = null;
    if (!values.direccion) values.direccion = null;
    try { await request(`/api/empleados/${person.id_empleado}`, "PATCH", values); onSaved(); }
    catch (problem) { setError(problem.message); } finally { setSaving(false); }
  };
  return <div className="modal-backdrop"><form className="modal-panel" onSubmit={submit}>
    <button type="button" className="modal-close" onClick={onClose}>×</button>
    <h2>Editar ficha</h2>
    <div className="form-grid">
      <Field label="Nombres"><input name="nombres" defaultValue={person.nombres} required /></Field>
      <Field label="Apellidos"><input name="apellidos" defaultValue={person.apellidos} required /></Field>
      <Field label="Correo"><input name="correo" type="email" defaultValue={person.correo} required /></Field>
      <Field label="Teléfono"><input name="telefono" defaultValue={person.telefono || ""} /></Field>
      <Field label="Dirección" wide><input name="direccion" defaultValue={person.direccion || ""} /></Field>
      <Field label="Fecha de nacimiento"><input name="fecha_nacimiento" type="date" defaultValue={person.fecha_nacimiento || ""} /></Field>
      <Field label="Fecha de ingreso"><input name="fecha_ingreso" type="date" defaultValue={person.fecha_ingreso} required /></Field>
      <Field label="Estado"><select name="estado" defaultValue={person.estado}><option value="activo">Activo</option><option value="licencia">En licencia</option><option value="inactivo">Inactivo</option></select></Field>
    </div>
    <ErrorNotice error={error} />
    <div className="modal-actions"><button className="button button-primary" disabled={saving}>{saving ? "Guardando…" : "Guardar cambios"}</button><button type="button" className="text-button" onClick={onClose}>Cancelar</button></div>
  </form></div>;
}

function EmployeePermits({ id }) {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");
  useEffect(() => { api(`/api/permisos/de/${id}`).then((data) => setItems(data.solicitudes)).catch((problem) => setError(problem.message)); }, [id]);
  return <><h2>Solicitudes y vacaciones</h2><ErrorNotice error={error} />{items.map((item) => <div className="simple-row" key={item.id_permiso}><div><b>{item.tipo_label}</b><small>{dateText(item.fecha_inicio)} – {dateText(item.fecha_termino)}</small></div><span>{dayCountText(item.dias)}</span><StatusBadge status={item.estado} /></div>)}</>;
}

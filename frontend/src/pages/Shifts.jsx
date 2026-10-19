import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { request } from "../lib/helpers.js";
import { ErrorNotice, Field } from "../components/ui.jsx";

export default function Shifts({ notify }) {
  const [centers, setCenters] = useState([]);
  const [centerId, setCenterId] = useState("");
  const [group, setGroup] = useState("A");
  const [regime, setRegime] = useState("7x7");
  const [grid, setGrid] = useState(null);
  const [error, setError] = useState("");
  const [assigning, setAssigning] = useState(false);
  const [people, setPeople] = useState([]);
  const [target, setTarget] = useState("");
  useEffect(() => { api("/api/centros").then((data) => { setCenters(data); if (data[0]) setCenterId(String(data[0].id_centro)); }).catch((problem) => setError(problem.message)); }, []);
  const load = useCallback(() => {
    if (!centerId) return;
    api(`/api/turnos/grilla?id_centro=${centerId}&grupo=${group}&regimen=${regime}`).then(setGrid).catch((problem) => setError(problem.message));
  }, [centerId, group, regime]);
  useEffect(() => { load(); }, [load]);
  const openAssign = async () => {
    try { setPeople(await api("/api/turnos/asignables")); setAssigning(true); }
    catch (problem) { setError(problem.message); }
  };
  const assign = async (event) => {
    event.preventDefault();
    const [id_empleado, id_turno] = target.split(":").map(Number);
    try { await request("/api/turnos/asignar", "POST", { id_empleado, id_turno }); notify("Turno asignado"); setAssigning(false); setTarget(""); load(); }
    catch (problem) { setError(problem.message); }
  };
  const allShifts = centers.find((item) => String(item.id_centro) === centerId)?.turnos || [];
  const options = allShifts.filter((item) => item.regimen === regime);
  return <section className="content-page">
    <div className="page-heading"><div><h1>Turnos</h1><p>{grid ? grid.esperados > 0 ? <><b>{grid.marcaron} de {grid.esperados}</b> personas del Grupo {group} marcaron entrada hoy.</> : <>No hay turno programado hoy para el Grupo {group}.</> : "Organiza la asistencia por centro y grupo."}</p></div><button className="button button-primary" onClick={openAssign}>Asignar turno</button></div>
    <div className="shift-controls">
      <Field label="Centro o planta"><select value={centerId} onChange={(event) => setCenterId(event.target.value)}>{centers.map((center) => <option key={center.id_centro} value={center.id_centro}>{center.nombre}</option>)}</select></Field>
      <Field label="Grupo"><select value={group} onChange={(event) => setGroup(event.target.value)}><option value="A">Grupo A</option><option value="B">Grupo B</option></select></Field>
      <div className="pills">{["7x7", "14x14"].map((item) => <button key={item} className={`pill ${regime === item ? "selected" : ""}`} onClick={() => setRegime(item)}>{item}</button>)}</div>
    </div>
    <ErrorNotice error={error} retry={load} />
    {grid && <div className="shift-grid">
      <div className="grid-header"><span>Persona</span>{grid.letras.map((letter, index) => <span className={index === grid.hoy_idx ? "today" : ""} key={`${letter}-${index}`}>{letter}</span>)}<span>Hoy</span></div>
      {grid.personas.map((person, row) => <div className="shift-row" key={person.id_empleado}><div className="shift-name"><span className={`avatar avatar-tone-${row % 4}`}>{person.iniciales}</span><b>{person.nombre}</b></div><div className="shift-track">{person.bloques.map((block, index) => <div key={index} className={`shift-block ${block.tipo}`} style={{ gridColumn: `${block.inicio + 1} / span ${block.fin - block.inicio + 1}` }}>{block.tipo === "turno" ? "Turno" : block.tipo}</div>)}</div><b className={`today-label ${person.hoy === "Sin marcar" ? "alert-text" : ""}`}>{person.hoy}</b></div>)}
      {!grid.personas.length && <p className="empty-state">No hay personas asignadas a este grupo.</p>}
      <div className="legend"><span className="work-dot" /> Turno <span className="vacation-dot" /> Vacaciones <span className="leave-dot" /> Licencia</div>
    </div>}
    {assigning && <div className="modal-backdrop"><form className="modal-panel compact-modal" onSubmit={assign}><button type="button" className="modal-close" onClick={() => setAssigning(false)}>×</button><h2>Asignar turno</h2><Field label="Persona y turno"><select value={target} onChange={(event) => setTarget(event.target.value)} required><option value="">Seleccionar persona</option>{people.map((person) => options.map((shift) => <option key={`${person.id_empleado}-${shift.id_turno}`} value={`${person.id_empleado}:${shift.id_turno}`}>{person.nombre} · {person.area} · Grupo {shift.grupo} ({shift.regimen})</option>))}</select></Field><div className="modal-actions"><button className="button button-primary">Asignar</button><button type="button" className="text-button" onClick={() => setAssigning(false)}>Cancelar</button></div></form></div>}
  </section>;
}

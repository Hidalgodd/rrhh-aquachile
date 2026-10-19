import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { request, localDateInput, dateText, initials } from "../lib/helpers.js";
import { ErrorNotice, Field, StatusBadge } from "../components/ui.jsx";

export default function Employees({ navigate, notify }) {
  const [people, setPeople] = useState([]);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [modal, setModal] = useState(false);
  const load = useCallback(async () => {
    setError("");
    try {
      const params = new URLSearchParams({ limit: "500" });
      if (query.trim()) params.set("q", query.trim());
      if (status) params.set("estado", status);
      setPeople(await api(`/api/empleados?${params}`));
    } catch (problem) { setError(problem.message); }
  }, [query, status]);
  useEffect(() => { load(); }, [load]);
  return (
    <section className="content-page">
      <div className="page-heading"><div><h1>Personas</h1><p>{people.length} resultados en la organización</p></div><button className="button button-primary" onClick={() => setModal(true)}>Nuevo empleado</button></div>
      <div className="toolbar">
        <label className="search-field">Buscar<input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Nombre, RUT o correo" /></label>
        <div className="pills">{[["", "Todas"], ["activo", "Activas"], ["licencia", "En licencia"], ["inactivo", "Inactivas"]].map(([value, label]) => <button key={value} className={`pill ${status === value ? "selected" : ""}`} onClick={() => setStatus(value)}>{label}</button>)}</div>
      </div>
      <ErrorNotice error={error} retry={load} />
      <div className="people-list">
        {people.map((person, index) => (
          <button className="person-row" key={person.id_empleado} onClick={() => navigate(`/empleados/${person.id_empleado}`)}>
            <span className={`avatar avatar-tone-${index % 4}`}>{initials(`${person.nombres} ${person.apellidos}`)}</span>
            <span className="person-name"><b>{person.nombres} {person.apellidos}</b><small>{person.rut}</small></span>
            <span className="person-meta">{person.cargo}<small>{person.area}</small></span>
            <span className="person-meta">Desde {dateText(person.fecha_ingreso)}</span>
            <StatusBadge status={person.estado} />
            <span className="edit-link">Ver ficha</span>
          </button>
        ))}
        {!people.length && !error && <p className="empty-state">No encontramos personas con esos filtros.</p>}
      </div>
      {modal && <EmployeeForm onClose={() => setModal(false)} onSaved={() => { setModal(false); notify("Empleado creado correctamente"); load(); }} />}
    </section>
  );
}

function EmployeeForm({ onClose, onSaved }) {
  const [areas, setAreas] = useState([]);
  const [roles, setRoles] = useState([]);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [areaId, setAreaId] = useState("");
  useEffect(() => {
    api("/api/areas").then((data) => { setAreas(data); if (data[0]) setAreaId(String(data[0].id_area)); }).catch((problem) => setError(problem.message));
  }, []);
  useEffect(() => {
    if (!areaId) { setRoles([]); return; }
    api(`/api/cargos?id_area=${areaId}`).then(setRoles).catch((problem) => setError(problem.message));
  }, [areaId]);
  const submit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const payload = Object.fromEntries(form.entries());
    payload.id_cargo = Number(payload.id_cargo);
    payload.fecha_nacimiento ||= null;
    try {
      await request("/api/empleados", "POST", payload);
      onSaved();
    } catch (problem) { setError(problem.message); } finally { setSaving(false); }
  };
  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <form className="employee-form modal-panel" onSubmit={submit}>
        <button type="button" className="modal-close" onClick={onClose} aria-label="Cerrar">×</button>
        <h2>Nueva ficha</h2>
        <h3>Quién es</h3>
        <div className="form-grid">
          <Field label="RUT"><input name="rut" placeholder="12.345.678-9" required /></Field>
          <Field label="Fecha de nacimiento"><input type="date" name="fecha_nacimiento" /></Field>
          <Field label="Nombres"><input name="nombres" required /></Field>
          <Field label="Apellidos"><input name="apellidos" required /></Field>
          <Field label="Correo"><input type="email" name="correo" required /></Field>
          <Field label="Teléfono"><input name="telefono" /></Field>
          <Field label="Dirección" wide><input name="direccion" /></Field>
        </div>
        <h3>Dónde trabajará</h3>
        <div className="form-grid">
          <Field label="Área"><select value={areaId} onChange={(event) => setAreaId(event.target.value)} required>{areas.map((area) => <option key={area.id_area} value={area.id_area}>{area.nombre}</option>)}</select></Field>
          <Field label="Cargo"><select name="id_cargo" required>{roles.map((role) => <option key={role.id_cargo} value={role.id_cargo}>{role.nombre}</option>)}</select></Field>
          <Field label="Fecha de ingreso"><input type="date" name="fecha_ingreso" defaultValue={localDateInput()} required /></Field>
          <Field label="Estado"><select name="estado" defaultValue="activo"><option value="activo">Activo</option><option value="licencia">En licencia</option><option value="inactivo">Inactivo</option></select></Field>
        </div>
        <ErrorNotice error={error} />
        <div className="modal-actions"><button className="button button-primary" disabled={saving || !roles.length}>{saving ? "Guardando…" : "Crear empleado"}</button><button type="button" className="text-button" onClick={onClose}>Cancelar</button></div>
      </form>
    </div>
  );
}

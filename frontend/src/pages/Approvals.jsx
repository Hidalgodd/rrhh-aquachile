import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { request, dateText, dayCountText } from "../lib/helpers.js";
import { ErrorNotice, Field, StatusBadge } from "../components/ui.jsx";

export default function Approvals({ notify }) {
  const [state, setState] = useState("pendiente");
  const [result, setResult] = useState({ solicitudes: [], conteos: {} });
  const [selected, setSelected] = useState(null);
  const [impact, setImpact] = useState(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(() => api(`/api/permisos?estado=${state}`).then((data) => {
    setResult(data);
    setSelected((current) => data.solicitudes.find((item) => item.id_permiso === current?.id_permiso) || data.solicitudes[0] || null);
  }).catch((problem) => setError(problem.message)), [state]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!selected) { setImpact(null); return; }
    api(`/api/permisos/${selected.id_permiso}/impacto`).then(setImpact).catch((problem) => setError(problem.message));
  }, [selected]);
  const resolve = async (estado) => {
    if (!selected) return;
    try { await request(`/api/permisos/${selected.id_permiso}/resolver`, "PATCH", { estado, comentario: comment || null }); notify(estado === "aprobado" ? "Solicitud aprobada" : "Solicitud rechazada"); setComment(""); load(); }
    catch (problem) { setError(problem.message); }
  };
  return <section className="content-page">
    <div className="page-heading"><div className="heading-inline"><h1>Por responder</h1><p>{result.conteos?.pendiente || 0} solicitudes esperando</p></div></div>
    <div className="pills approval-tabs">{["pendiente", "aprobado", "rechazado"].map((value) => <button className={`pill ${state === value ? "selected" : ""}`} key={value} onClick={() => setState(value)}>{value === "pendiente" ? "Pendientes" : value === "aprobado" ? "Aprobadas" : "Rechazadas"} <b>{result.conteos?.[value] || 0}</b></button>)}</div>
    <ErrorNotice error={error} retry={load} />
    <div className="approval-layout">
      <div className="approval-list">{result.solicitudes.map((item, index) => <button className={`approval-item ${selected?.id_permiso === item.id_permiso ? "selected" : ""}`} key={item.id_permiso} onClick={() => setSelected(item)}><span className={`avatar avatar-tone-${index % 4}`}>{item.iniciales}</span><span className="approval-person"><b>{item.nombre}</b><small>{item.tipo_label} · {dateText(item.fecha_inicio)}</small></span><strong>{dayCountText(item.dias)}</strong></button>)}
        {!result.solicitudes.length && <p className="muted">No hay solicitudes en esta categoría.</p>}
      </div>
      {selected && <article className="approval-detail">
        <div className="person-title"><span className="avatar avatar-large">{selected.iniciales}</span><div><h2>{selected.nombre}</h2><p>{selected.cargo} · Grupo {selected.grupo || "—"} · {selected.centro || selected.area}</p></div></div>
        <p className="request-summary">Pide <b>{dayCountText(selected.dias)} de {selected.tipo_label?.toLowerCase()}</b>, del {dateText(selected.fecha_inicio)} al {dateText(selected.fecha_termino)}.{selected.saldo_quedaria !== null && selected.saldo_quedaria !== undefined ? <> Le quedarían <b>{dayCountText(selected.saldo_quedaria)}</b> de saldo.</> : null}</p>
        {impact && <><h3>Impacto en {impact.grupo}</h3><p className="muted">Con esta solicitud, máximo {impact.maximo} de {impact.total} personas estarán ausentes esos días.</p><div className="impact-chart">{impact.dias.map((day) => <div key={day.fecha}><span className={`impact-bar ${day.es_solicitud ? "highlight" : ""}`} style={{ height: `${Math.max(12, (day.ausentes / Math.max(impact.total, 1)) * 90)}px` }} /><small>{day.dia}</small><b>{day.ausentes}</b></div>)}</div></>}
        {state === "pendiente" && <><Field label="Comentario (opcional)"><input value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Se enviará junto con la respuesta" /></Field><div className="modal-actions"><button className="button button-primary" onClick={() => resolve("aprobado")}>Aprobar</button><button className="danger-button" onClick={() => resolve("rechazado")}>Rechazar</button></div></>}
      </article>}
    </div>
  </section>;
}

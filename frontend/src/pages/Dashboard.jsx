import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { ErrorNotice, Loading } from "../components/ui.jsx";

export default function Dashboard({ navigate, notify }) {
  const [summary, setSummary] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setError("");
    try {
      const [data, shifts] = await Promise.all([api("/api/dashboard/resumen"), api("/api/turnos/resumen?regimen=7x7")]);
      setSummary(data);
      setSchedule(shifts);
    } catch (problem) { setError(problem.message); }
  }, []);
  useEffect(() => { load(); }, [load]);
  if (!summary || !schedule) return <><ErrorNotice error={error} retry={load} />{!error && <Loading />}</>;
  const chartPoints = summary.serie.meses.map((month, index) => {
    const values = summary.serie.areas.map((area) => ({ area: area.area, total: area.valores[index] }));
    return { month, values, total: values.reduce((sum, area) => sum + area.total, 0) };
  });
  const chartMax = Math.max(1, ...chartPoints.map((point) => point.total));
  return (
    <>
      <ErrorNotice error={error} retry={load} />
      <section className="dashboard-hero">
        <div className="hero-stat"><strong>{summary.dotacion}</strong><p>personas trabajan hoy en AquaChile,<br /><b>{summary.dotacion_hace_un_anio} hace un año.</b></p></div>
        <div className="area-key">{summary.serie.areas.map((area, index) => <div key={area.area}><i className={`bar-color-${index % 5}`} />{area.area} <b>{summary.por_area.find((item) => item.area === area.area)?.total || 0}</b></div>)}</div>
        <div className="chart-wrap">
          <div className="area-bars" aria-label="Dotación mensual por área">
            {chartPoints.map((point, index) => <div className="area-bar-column" key={`${point.month}-${index}`} style={{ height: `${Math.max(4, (point.total / chartMax) * 100)}%` }}><span>{point.total}</span>{point.values.map((area, areaIndex) => <i key={area.area} className={`bar-color-${areaIndex % 5}`} style={{ flexGrow: area.total }} />)}</div>)}
          </div>
          <div className="chart-months">{chartPoints.map((point, index) => <span key={`${point.month}-${index}`}>{point.month}</span>)}</div>
        </div>
        <p className="dashboard-note"><b>{summary.licencia} personas</b> están con licencia, <b>{summary.nuevos_mes} ingresaron este mes</b> y <button type="button" className="dashboard-link" onClick={() => navigate("/postulantes")}>{summary.postulantes_pendientes} postulaciones</button> esperan respuesta.</p>
      </section>
      <section className="schedule-card">
        <div className="section-title-row"><h2>Turnos 7x7, próximas dos semanas</h2><button className="text-button" onClick={() => navigate("/turnos")}>Ver turnos</button></div>
        <div className="schedule-days"><span /><div className="schedule-day-labels">{schedule.letras.map((day, index) => <span key={`${day}-${index}`}>{day}</span>)}</div></div>
        {schedule.centros.map((center) => center.grupos.map((group) => (
          <div className="schedule-row" key={`${center.id_centro}-${group.grupo}`}>
            <div><b>{center.nombre}</b><small>{group.personas} personas · Grupo {group.grupo}</small></div>
            <div className="schedule-track">{group.bloques.map((block, index) => <span key={index} className={`schedule-block ${block.tipo === "turno" ? "work" : "rest"}`} style={{ left: `${block.inicio / schedule.dias.length * 100}%`, width: `${((block.fin - block.inicio + 1) / schedule.dias.length) * 100}%` }}>Grupo {group.grupo}</span>)}</div>
          </div>
        )))}
        {!schedule.centros.length && <p className="muted">Todavía no hay turnos configurados.</p>}
      </section>
    </>
  );
}

import { useState } from "react";
import { api } from "../api.js";
import { ErrorNotice, Field } from "../components/ui.jsx";

export default function Postular({ onBack }) {
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [saving, setSaving] = useState(false);
  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      await api("/api/postulantes", { method: "POST", body: new FormData(event.currentTarget) });
      setSuccess(true);
    } catch (problem) {
      setError(problem.message);
    } finally {
      setSaving(false);
    }
  };
  const stages = [
    ["01", "Comparte tu perfil", "Cuéntanos quién eres y adjunta tu currículum."],
    ["02", "Revisamos tu postulación", "El equipo de selección revisará tu experiencia y tus antecedentes."],
    ["03", "Conversamos contigo", "Si tu perfil coincide con la búsqueda, coordinaremos entrevistas y evaluaciones."],
    ["04", "Te contamos el resultado", "Te informaremos cómo continúa el proceso."],
  ];
  return <main className="careers-page">
    <header className="careers-header">
      <a className="brand careers-brand" href="/"><span className="brand-mark" /> <span>AquaChile</span></a>
      <nav aria-label="Navegación de postulaciones">
        <a href="#proceso">Proceso de selección</a>
        <a href="https://trabajos.aquachile.com/search/?createNewAlert=false&q=" target="_blank" rel="noreferrer">Ofertas vigentes ↗</a>
        <button className="careers-login" onClick={onBack}>Ingreso colaboradores</button>
      </nav>
    </header>
    <section className="careers-hero">
      <div className="careers-hero-copy">
        <span className="eyebrow">TRABAJA CON NOSOTROS</span>
        <h1>Haz crecer tu<br />próximo desafío.</h1>
        <p>Conoce nuestras oportunidades y comparte tu experiencia con el equipo de AquaChile.</p>
        <div className="careers-actions">
          <a className="button button-primary" href="#postulacion">Enviar mi postulación</a>
          <a className="careers-secondary-link" href="https://trabajos.aquachile.com/search/?createNewAlert=false&q=" target="_blank" rel="noreferrer">Explorar ofertas vigentes ↗</a>
        </div>
      </div>
      <div className="careers-hero-art" aria-hidden="true"><span className="art-circle" /><span className="art-wave art-wave-one" /><span className="art-wave art-wave-two" /><span className="art-wave art-wave-three" /><span className="art-caption">Personas que hacen crecer<br />una gran comunidad.</span></div>
    </section>
    <section className="process-section" id="proceso">
      <div className="process-heading"><span className="eyebrow">ASÍ ES EL CAMINO</span><h2>¿Qué pasa después de postular?</h2><p>Te contamos las etapas para que sepas qué esperar.</p></div>
      <div className="process-steps">{stages.map(([number, title, description]) => <article className="process-step" key={number}><span className="process-number">{number}</span><div><h3>{title}</h3><p>{description}</p></div></article>)}</div>
    </section>
    <section className="application-section" id="postulacion">
      <div className="application-intro"><span className="eyebrow">TU HISTORIA NOS INTERESA</span><h2>{success ? "¡Gracias por acercarte!" : "Cuéntanos de ti."}</h2><p>{success ? "Recibimos tu postulación. Si tu perfil coincide con una búsqueda, el equipo de selección se pondrá en contacto contigo." : "Completa tus datos y adjunta tu currículum. También puedes revisar las vacantes disponibles en nuestro portal de empleos."}</p>
        {success && <a className="button button-secondary" href="https://trabajos.aquachile.com/search/?createNewAlert=false&q=" target="_blank" rel="noreferrer">Ver ofertas vigentes ↗</a>}
      </div>
      {!success && <form className="application-form" onSubmit={submit}>
        <div className="form-grid">
          <Field label="Nombres"><input name="nombres" autoComplete="given-name" required minLength="2" /></Field>
          <Field label="Apellidos"><input name="apellidos" autoComplete="family-name" required minLength="2" /></Field>
          <Field label="Correo electrónico"><input type="email" name="correo" autoComplete="email" required /></Field>
          <Field label="Teléfono"><input name="telefono" type="tel" autoComplete="tel" /></Field>
          <Field label="Área o cargo de interés" wide><input name="cargo_postulado" required placeholder="Ej.: Operaciones, mantenimiento, calidad…" /></Field>
          <Field label="Currículum (PDF, DOC o DOCX · máximo 5 MB)" wide><input type="file" name="cv" accept=".pdf,.doc,.docx" required /></Field>
        </div>
        <ErrorNotice error={error} />
        <button className="button button-primary" disabled={saving}>{saving ? "Enviando…" : "Enviar postulación"}</button>
      </form>}
    </section>
    <footer className="careers-footer"><a className="brand" href="/"><span className="brand-mark" /> <span>AquaChile</span></a><span>Personas, experiencia y nuevas oportunidades.</span><button className="text-button" onClick={onBack}>Volver al ingreso</button></footer>
  </main>;
}

import { Link } from "react-router-dom";

export default function Login({ onSubmit, error }) {
  return (
    <main className="login-page">
      <div className="login-waves"><i /><i /><i /><i /></div>
      <a className="login-brand brand" href="#"><span className="brand-mark" /> <span>AquaChile</span></a>
      <section className="login-content">
        <h1>Cada centro,<br />cada turno,<br />cada persona.</h1>
        <form className="login-form" onSubmit={onSubmit}>
          <label>Usuario<input name="username" autoComplete="username" required defaultValue="" /></label>
          <label>Contraseña<input type="password" name="password" autoComplete="current-password" required /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="form-actions"><button className="button button-primary">Entrar</button><Link to="/postular">Enviar postulación</Link></div>
        </form>
      </section>
    </main>
  );
}

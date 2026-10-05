import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import { loadSession, saveSession } from "../session";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(location.state?.expired ? "Сессия истекла. Войдите снова." : "");
  const [loading, setLoading] = useState(false);

  // Уже вошёл: сразу в рабочую область
  if (loadSession().token) return <Navigate to="/app" replace />;

  async function handleSubmit(event) {
    event.preventDefault(); // не перезагружать страницу при отправке формы
    setError("");
    if (!login.trim() || !password) {
      setError("Введите логин и пароль.");
      return;
    }
    setLoading(true);
    try {
      const data = await api.login(login.trim(), password);
      saveSession({ token: data.access_token, user: data.user });
      navigate("/app");
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  }

  return (
    <main className="step">
      <header className="hero reveal">
        <h1>Скрининг анемий и латентных дефицитов</h1>
        <p>ИИ-анализ лабораторных показателей для медицинских специалистов</p>
      </header>

      <form className="glass reveal" onSubmit={handleSubmit} noValidate>
        <h2>Вход для врача</h2>
        <p className="lead">Используйте выданную вам учётную запись.</p>

        <label className="field-label" htmlFor="login">Логин</label>
        <input
          id="login"
          className="input"
          autoComplete="username"
          value={login}
          onChange={(e) => setLogin(e.target.value)}
          aria-invalid={Boolean(error)}
        />

        <label className="field-label" htmlFor="password">Пароль</label>
        <div className="password">
          <input
            id="password"
            className="input"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? "login-error" : undefined}
          />
          <button type="button" className="ghost-button small" onClick={() => setShowPassword((v) => !v)} aria-pressed={showPassword}>
            {showPassword ? "Скрыть" : "Показать"}
          </button>
        </div>

        {error && (
          <p id="login-error" className="form-error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="primary-button wide" disabled={loading}>
          {loading ? "Проверяем…" : "Войти"}
        </button>
      </form>
    </main>
  );
}

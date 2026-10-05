import { useEffect } from "react";
import { Navigate, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { clearSession, loadSession } from "../session";

// Общая рамка рабочей области: шапка + содержимое страницы (Outlet).
// Вкладки режимов показываются только после выбора режима на приветственном экране.
export default function AppLayout() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const session = loadSession();
  const inMode = pathname !== "/app" && pathname !== "/app/";

  // Бэкенд ответил 401 (токен истёк): возвращаем на вход
  useEffect(() => {
    const onExpired = () => navigate("/", { replace: true, state: { expired: true } });
    window.addEventListener("session-expired", onExpired);
    return () => window.removeEventListener("session-expired", onExpired);
  }, [navigate]);

  if (!session.token) return <Navigate to="/" replace />;

  function handleLogout() {
    clearSession();
    navigate("/", { replace: true });
  }

  return (
    <>
      <header className="topbar no-print">
        <div className="topbar-inner">
          <NavLink to="/app" end className="brand crt-text">
            <span>HemoKit</span>
          </NavLink>
          {inMode && (
            <nav className="nav" aria-label="Режим работы">
              <NavLink to="/app/single" className="crt-text">
                <span>Один пациент</span>
              </NavLink>
              <NavLink to="/app/batch" className="crt-text">
                <span>Много пациентов</span>
              </NavLink>
            </nav>
          )}
          <div className="account">
            <span className="account-name">{session.user?.display_name}</span>
            <button type="button" className="ghost-button small" onClick={handleLogout}>
              Выйти
            </button>
          </div>
        </div>
      </header>
      <main className="page">
        {/* key: при смене страницы её блоки появляются заново (с анимацией) */}
        <Outlet key={pathname} />
      </main>
    </>
  );
}

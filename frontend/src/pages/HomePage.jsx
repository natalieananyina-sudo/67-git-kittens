import { Link } from "react-router-dom";

// Иконки режимов: один человек и группа
function PersonIcon() {
  return (
    <svg viewBox="0 0 48 48" width="48" height="48" aria-hidden="true">
      <circle cx="24" cy="16" r="8" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <path d="M9 41c1.5-8.5 7.5-13 15-13s13.5 4.5 15 13" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function GroupIcon() {
  return (
    <svg viewBox="0 0 48 48" width="48" height="48" aria-hidden="true">
      <circle cx="24" cy="15" r="7" fill="none" stroke="currentColor" strokeWidth="2.5" />
      <circle cx="10" cy="20" r="5" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <circle cx="38" cy="20" r="5" fill="none" stroke="currentColor" strokeWidth="2.2" />
      <path d="M11 41c1.3-7.5 6.5-11.5 13-11.5S35.7 33.5 37 41" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
      <path d="M2.5 38c.8-4.6 3.6-7.3 7.5-7.3M45.5 38c-.8-4.6-3.6-7.3-7.5-7.3" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  );
}

export default function HomePage() {
  return (
    <div className="welcome">
      <section className="welcome-text reveal">
        <h1 className="page-title">Добро пожаловать в HemoKit — сервис для скрининга латентных дефицитных состояний!</h1>
        <p className="page-lead">Выберите один из режимов работы ниже</p>
      </section>

      <div className="modes reveal">
        <Link to="/app/single" className="mode-button">
          <span className="mode-icon"><PersonIcon /></span>
          <span className="mode-title">Один пациент</span>
          <span className="mode-text">Загрузите файл с анализами одного пациента или введите показатели вручную</span>
          <span className="mode-cta">Выбрать</span>
        </Link>
        <Link to="/app/batch" className="mode-button">
          <span className="mode-icon"><GroupIcon /></span>
          <span className="mode-title">Много пациентов</span>
          <span className="mode-text">Загрузите таблицу CSV или XLSX и получите сводку по всем пациентам</span>
          <span className="mode-cta">Выбрать</span>
        </Link>
      </div>
    </div>
  );
}

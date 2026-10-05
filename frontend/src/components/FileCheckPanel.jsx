import { useState } from "react";

const SHOW_FIRST = 8;

// «Строка 3, столбец «ferritin»» — где именно проблема
function where(issue) {
  const parts = [];
  if (issue.row) parts.push(`Строка ${issue.row}`);
  if (issue.column) parts.push(`столбец «${issue.column}»`);
  return parts.join(", ");
}

// Отчёт о проверке формата файла: ошибки (красные) и предупреждения (жёлтые)
export default function FileCheckPanel({ check, fileName }) {
  const [showAll, setShowAll] = useState(false);
  if (!check) return null;
  const visible = showAll ? check.issues : check.issues.slice(0, SHOW_FIRST);

  return (
    <section className={`file-check ${check.ok ? "file-check-ok" : "file-check-bad"}`} aria-live="polite">
      <h3>
        {check.ok
          ? `Формат файла${fileName ? ` «${fileName}»` : ""} корректен`
          : `В файле${fileName ? ` «${fileName}»` : ""} найдены ошибки: ${check.errors}`}
      </h3>
      {check.ok && check.rows > 0 && (
        <p className="muted small-text">
          Строк с пациентами: {check.rows}. Распознано лабораторных показателей: {check.recognized_columns}.
        </p>
      )}
      {!check.ok && (
        <p className="small-text">
          Строки с ошибками не обрабатываются. Исправьте файл и загрузите его снова.
        </p>
      )}
      {check.issues.length > 0 && (
        <ul className="issues">
          {visible.map((issue, n) => (
            <li key={n} className={`issue issue-${issue.level}`}>
              <span className="issue-tag">{issue.level === "error" ? "Ошибка" : "Внимание"}</span>
              {where(issue) && <span className="issue-where">{where(issue)}: </span>}
              {issue.message}
            </li>
          ))}
        </ul>
      )}
      {check.issues.length > SHOW_FIRST && (
        <button type="button" className="link-button" onClick={() => setShowAll((v) => !v)}>
          {showAll ? "Свернуть" : `Показать все (${check.issues.length})`}
        </button>
      )}
      {check.issues_truncated > 0 && <p className="muted small-text">И ещё {check.issues_truncated} в файле.</p>}
    </section>
  );
}

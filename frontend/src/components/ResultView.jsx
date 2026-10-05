import { useState } from "react";
import { SEVERITY, SEX_LABELS, num, years } from "../labels";
import ModelNotice from "./ModelNotice";

// Список пунктов или абзац секции заключения
function ReportSection({ section }) {
  return (
    <section className="report-section">
      <h4>{section.title}</h4>
      {section.text && <p>{section.text}</p>}
      {section.items.length > 0 && (
        <ul>
          {section.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

// Scores модели по причинам. Это технические оценки, а не вероятности: показываем полосой и числом, без «%»
function CauseScores({ scores, chosen }) {
  const shown = scores.filter((s) => s.cause === chosen || s.score >= 0.05).slice(0, 5);
  return (
    <ul className="states">
      {shown.map((s) => (
        <li key={s.cause} className={`state ${s.cause === chosen ? "state-positive" : ""}`}>
          <span className="state-name">{s.label}</span>
          <span className="score" aria-hidden="true">
            <span className="score-fill" style={{ width: `${Math.round(s.score * 100)}%` }} />
          </span>
          <span className="state-value">
            {s.cause === chosen ? "выбрано моделью · " : ""}
            {num(s.score)}
          </span>
        </li>
      ))}
    </ul>
  );
}

const FLAG_TEXT = { low: "ниже нормы", high: "выше нормы", normal: "" };

export default function ResultView({ result }) {
  const [tab, setTab] = useState("doctor");
  const [printedOn] = useState(() => new Date().toLocaleDateString("ru-RU")); // дата для печатной версии
  const severity = SEVERITY[result.report.severity];
  const doctorSections = result.report.doctor.sections.filter((s) => s.title !== "Основание результата");
  const patient = result.report.patient;
  const sexWord = result.patient.sex === "female" ? "женщин" : "мужчин";
  const insufficient = result.screening_status === "insufficient_data";

  return (
    <article className="glass panel result">
      <header className="result-head no-print">
        <div>
          <p className="muted">
            Случай {result.case_id} · {SEX_LABELS[result.patient.sex] ?? "пол не указан"}, {years(result.patient.age)}
          </p>
          <h2 className="result-title">{result.anemia_class_label}</h2>
        </div>
        <span className={`badge ${severity.className}`}>{severity.label}</span>
      </header>

      <div className="no-print">
        <ModelNotice model={result.model} />
        {result.unit_conversions.length > 0 && (
          <details className="soft-note">
            <summary>Значения приведены в стандартные единицы ({result.unit_conversions.length})</summary>
            <ul>
              {result.unit_conversions.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </details>
        )}
      </div>

      <div className="tabs no-print" role="tablist" aria-label="Версия результата">
        <button type="button" role="tab" aria-selected={tab === "doctor"} onClick={() => setTab("doctor")}>
          Для врача
        </button>
        <button type="button" role="tab" aria-selected={tab === "patient"} onClick={() => setTab("patient")}>
          Для пациента
        </button>
      </div>

      {tab === "doctor" ? (
        <div role="tabpanel" className="tabpanel">
          <section className="conclusion">
            <h3>Предварительное заключение</h3>
            <p className="conclusion-title">{result.report.doctor.headline}</p>
            <p>{result.report.doctor.summary}</p>
          </section>

          {insufficient ? (
            <section className="report-section">
              <h4>Почему нет заключения</h4>
              <p>
                ML-модель не формирует результат, если данных недостаточно для безопасного вывода. Причина:{" "}
                <strong>{result.insufficient_reason}</strong>.
              </p>
            </section>
          ) : (
            <>
              <section className="report-section">
                <h4>Анемия (клиническое правило в составе ML-модуля)</h4>
                <p>
                  Гемоглобин <strong>{num(result.anemia.hemoglobin)} г/л</strong> при пороге {num(result.anemia.threshold)}{" "}
                  г/л для {sexWord}: анемия <strong>{result.anemia.detected ? "выявлена" : "не выявлена"}</strong>.
                </p>
              </section>

              <section className="report-section">
                <h4>Причина по ML-модели: {result.deficiency_cause_label}</h4>
                <CauseScores scores={result.model_scores} chosen={result.deficiency_cause} />
                <p className="muted small-text">
                  Числа — технические оценки модели для сравнения вариантов между собой, а не вероятности диагноза.
                </p>
                {result.missing_panels.length > 0 && (
                  <p className="muted small-text">Нет данных панели: {result.missing_panels.join("; ")}.</p>
                )}
              </section>
            </>
          )}

          {doctorSections.map((s) => (
            <ReportSection key={s.title} section={s} />
          ))}

          <details className="labs">
            <summary>Лабораторные показатели ({result.labs.length})</summary>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th scope="col">Показатель</th>
                    <th scope="col">Значение</th>
                    <th scope="col">Ориентир</th>
                    <th scope="col">Отметка</th>
                  </tr>
                </thead>
                <tbody>
                  {result.labs.map((l) => (
                    <tr key={l.key} className={l.flag !== "normal" ? "flagged" : ""}>
                      <td>{l.label}</td>
                      <td>
                        {num(l.value)} {l.unit}
                      </td>
                      <td>
                        {l.ref_low !== null ? num(l.ref_low) : "<"}
                        {l.ref_low !== null && l.ref_high !== null ? "–" : " "}
                        {l.ref_high !== null ? num(l.ref_high) : ""}
                      </td>
                      <td>{FLAG_TEXT[l.flag]}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>

          {result.warnings.length > 0 && (
            <ul className="warnings">
              {result.warnings.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}
          <p className="disclaimer">{result.report.doctor.disclaimer}</p>
        </div>
      ) : (
        <div role="tabpanel" className="tabpanel">
          {/* Только этот блок попадает на печать */}
          <div className="print-area">
            <div className="print-only print-head">
              <p>Скрининг латентных дефицитных состояний</p>
              <p>
                Результат скрининга · случай {result.case_id} · {printedOn}
              </p>
            </div>
            <h3 className="patient-headline">{patient.headline}</h3>
            {patient.sections.map((s) => (
              <ReportSection key={s.title} section={s} />
            ))}
            <p className="disclaimer">{patient.disclaimer}</p>
          </div>
          <button type="button" className="primary-button no-print" onClick={() => window.print()}>
            Распечатать для пациента
          </button>
        </div>
      )}
    </article>
  );
}

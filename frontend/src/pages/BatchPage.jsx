import { useEffect, useRef, useState } from "react";
import { api, saveBlob } from "../api";
import FileCheckPanel from "../components/FileCheckPanel";
import FileDrop from "../components/FileDrop";
import ModelNotice from "../components/ModelNotice";
import ResultView from "../components/ResultView";
import { CAUSE_SHORT, SEVERITY, SEX_LABELS, num } from "../labels";

// Причины, которые считаются дефицитом (воспаление и неопределённая причина — нет)
const DEFICIENCY_CAUSES = new Set([
  "iron_deficiency", "B12_deficiency", "folate_deficiency", "B6_deficiency", "copper_deficiency",
  "iron_B12", "iron_folate", "B12_folate",
]);

const FILTERS = [
  { key: "all", label: "Все", test: () => true },
  { key: "anemia", label: "Анемия", test: (r) => r.anemia === true },
  { key: "deficiency", label: "Дефициты", test: (r) => DEFICIENCY_CAUSES.has(r.deficiency_cause) },
  { key: "insufficient", label: "Мало данных", test: (r) => r.screening_status === "insufficient_data" },
  { key: "errors", label: "Ошибки", test: (r) => r.status === "error" },
];

function scrollTo(element) {
  const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  element?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
}

export default function BatchPage() {
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fatalCheck, setFatalCheck] = useState(null); // отчёт, если файл не удалось обработать целиком
  const [batch, setBatch] = useState(null);
  const [filter, setFilter] = useState("all");
  const [selected, setSelected] = useState(null); // { row, result?, error?, loading? }
  const tableRef = useRef(null);
  const detailRef = useRef(null);

  useEffect(() => {
    if (batch) scrollTo(tableRef.current);
  }, [batch]);

  useEffect(() => {
    if (selected?.result) scrollTo(detailRef.current);
  }, [selected]);

  async function run(file) {
    setFileName(file.name);
    setError("");
    setFatalCheck(null);
    setBatch(null);
    setSelected(null);
    setFilter("all");
    setLoading(true);
    try {
      setBatch(await api.batch(file));
    } catch (e) {
      if (e.data?.file_check) setFatalCheck(e.data.file_check);
      else setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function runDemo() {
    try {
      const blob = await api.download("/screening/batch/demo-file");
      await run(new File([blob], "demo_batch.csv", { type: "text/csv" }));
    } catch (e) {
      setError(e.message);
    }
  }

  async function downloadTemplate() {
    try {
      saveBlob(await api.download("/screening/batch/template"), "screening_template.csv");
    } catch (e) {
      setError(e.message);
    }
  }

  async function openRow(row) {
    if (row.status !== "completed") return;
    setSelected({ row, loading: true });
    try {
      setSelected({ row, result: await api.screen(row.input) });
    } catch (e) {
      setSelected({ row, error: e.message });
    }
  }

  const visible = batch ? batch.rows.filter(FILTERS.find((f) => f.key === filter).test) : [];

  return (
    <div className="stack">
      <section className="intro reveal">
        <h1 className="page-title">Много пациентов</h1>
        <p className="page-lead">
          Обязательные столбцы: patient_id, age_years, sex и hemoglobin, остальные показатели как в шаблоне (RBC, MCV,
          ferritin…). Единицу можно указать в заголовке, например «ferritin (ng/mL)». Столбцы с ФИО и контактами не
          принимаются. Если в строке не хватает анализов, модель отметит её как «Недостаточно данных».
        </p>
      </section>

      <section className="glass panel reveal">
        <FileDrop
          title="Перетащите файл с пациентами сюда"
          hint="CSV или XLSX, до 5 МБ и 1000 строк"
          onFile={run}
          onError={(message) => {
            setFatalCheck(null);
            setError(message);
          }}
          disabled={loading}
        />
        <div className="form-toolbar">
          <button type="button" className="ghost-button" onClick={downloadTemplate}>
            Скачать шаблон
          </button>
          <button type="button" className="ghost-button" onClick={runDemo} disabled={loading}>
            Проверить на демо-файле
          </button>
        </div>
        {loading && (
          <p role="status">
            Проверяем {fileName}, модель анализирует пациентов… Для большого файла это может занять до минуты.
          </p>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <FileCheckPanel check={fatalCheck} fileName={fileName} />
      </section>

      {batch && (
        <section ref={tableRef} className="glass panel reveal scroll-target">
          <h2 className="panel-title">Результаты: {fileName}</h2>
          <p className="summary-line">
            Всего {batch.summary.total} · обработано {batch.summary.completed} · с ошибками {batch.summary.errors} ·
            анемия {batch.summary.anemia_detected} · дефициты {batch.summary.with_deficiency} · недостаточно данных{" "}
            {batch.summary.insufficient_data}
          </p>
          <ModelNotice model={batch.model} />
          <FileCheckPanel check={batch.file_check} fileName={fileName} />

          <div className="filters" role="group" aria-label="Фильтр строк">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                className={filter === f.key ? "chip active" : "chip"}
                aria-pressed={filter === f.key}
                onClick={() => setFilter(f.key)}
              >
                {f.label} ({batch.rows.filter(f.test).length})
              </button>
            ))}
          </div>

          <div className="table-wrap">
            <table className="batch-table">
              <thead>
                <tr>
                  <th scope="col">№</th>
                  <th scope="col">ID случая</th>
                  <th scope="col">Пол, возраст</th>
                  <th scope="col">Hb, г/л</th>
                  <th scope="col">Результат</th>
                  <th scope="col">Причина по модели</th>
                  <th scope="col">
                    <span className="visually-hidden">Действие</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {visible.map((r) => (
                  <tr
                    key={r.row}
                    className={`${r.status === "error" ? "row-error" : "row-click"} ${selected?.row.row === r.row ? "row-selected" : ""}`}
                    onClick={() => openRow(r)}
                  >
                    <td>{r.row}</td>
                    <td>{r.case_id ?? "—"}</td>
                    {r.status === "completed" ? (
                      <>
                        <td>
                          {SEX_LABELS[r.sex]?.[0] ?? "?"}, {r.age}
                        </td>
                        <td>{num(r.hemoglobin)}</td>
                        <td>
                          <span className={`dot ${SEVERITY[r.severity].className}`} aria-hidden="true" />
                          {r.anemia_class_label}
                        </td>
                        <td>
                          {CAUSE_SHORT[r.deficiency_cause] ? <span className="tag">{CAUSE_SHORT[r.deficiency_cause]}</span> : "—"}
                        </td>
                        <td>
                          <button type="button" className="link-button" onClick={(e) => (e.stopPropagation(), openRow(r))}>
                            Открыть
                          </button>
                        </td>
                      </>
                    ) : (
                      <td colSpan={5} className="error-cell">
                        {r.errors.join(" ")}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {selected && (
        <div ref={detailRef} className="scroll-target">
          {selected.loading && <p className="glass panel">Загружаем результат случая {selected.row.case_id}…</p>}
          {selected.error && <p className="glass panel form-error">{selected.error}</p>}
          {selected.result && (
            <>
              <button type="button" className="ghost-button back-button no-print" onClick={() => scrollTo(tableRef.current)}>
                ← К таблице
              </button>
              <ResultView key={selected.row.row} result={selected.result} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

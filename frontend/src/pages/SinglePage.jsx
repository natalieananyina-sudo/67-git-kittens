import { useEffect, useRef, useState } from "react";
import { api, saveBlob } from "../api";
import FileCheckPanel from "../components/FileCheckPanel";
import FileDrop from "../components/FileDrop";
import ResultView from "../components/ResultView";
import { num } from "../labels";

const EMPTY = { case_id: "", sex: "", age: "", labs: {}, units: {} };

// Случайный псевдонимизированный ID, например C-7K2QX9
function generateId() {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  const bytes = crypto.getRandomValues(new Uint8Array(6));
  return "C-" + Array.from(bytes, (b) => alphabet[b % alphabet.length]).join("");
}

// "108,5" -> 108.5; пусто -> null; не число -> NaN
function toNumber(text) {
  const clean = String(text).trim().replace(/\s/g, "").replace(",", ".");
  if (clean === "") return null;
  return Number(clean);
}

function scrollTo(element) {
  const smooth = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  element?.scrollIntoView({ behavior: smooth ? "smooth" : "auto", block: "start" });
}

export default function SinglePage() {
  const [examples, setExamples] = useState([]);

  // Режим 1 (основной): загрузка файла
  const [fileName, setFileName] = useState("");
  const [fileCheck, setFileCheck] = useState(null);
  const [fileError, setFileError] = useState("");
  const [fileLoading, setFileLoading] = useState(false);

  // Режим 2: ручной ввод (открывается кнопкой внизу страницы)
  const [manualOpen, setManualOpen] = useState(false);
  const [catalog, setCatalog] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({}); // поле -> сообщение
  const [formError, setFormError] = useState("");
  const [openGroups, setOpenGroups] = useState(new Set(["cbc", "iron"]));
  const [manualLoading, setManualLoading] = useState(false);

  // Результат: { data, source: "file" | "manual" }
  const [result, setResult] = useState(null);
  const resultRef = useRef(null);
  const manualRef = useRef(null);
  const formRef = useRef(null);

  useEffect(() => {
    api.examples().then((ex) => setExamples(ex.examples)).catch(() => setExamples([]));
  }, []);

  // После получения результата прокручиваем к нему
  useEffect(() => {
    if (result) scrollTo(resultRef.current);
  }, [result]);

  // ---------- загрузка файла ----------
  async function runFile(file) {
    setFileName(file.name);
    setFileError("");
    setFileCheck(null);
    setResult(null);
    setFileLoading(true);
    try {
      const data = await api.screenFile(file);
      setFileCheck(data.file_check);
      setResult({ data: data.result, source: "file" });
    } catch (e) {
      // ошибки формата приходят вместе с отчётом о проверке файла
      if (e.data?.file_check) setFileCheck(e.data.file_check);
      else setFileError(e.message);
    } finally {
      setFileLoading(false);
    }
  }

  async function runExample(id) {
    if (!id) return;
    try {
      const blob = await api.download(`/screening/examples/${id}/file`);
      await runFile(new File([blob], `example_${id}.csv`, { type: "text/csv" }));
    } catch (e) {
      setFileError(e.message);
    }
  }

  async function downloadTemplate() {
    try {
      saveBlob(await api.download("/screening/batch/template"), "screening_template.csv");
    } catch (e) {
      setFileError(e.message);
    }
  }

  // ---------- ручной ввод ----------
  async function openManual() {
    setManualOpen(true);
    if (!catalog) {
      try {
        setCatalog(await api.analytes());
      } catch (e) {
        setFormError(`Не удалось загрузить справочник показателей: ${e.message}`);
      }
    }
    setTimeout(() => scrollTo(manualRef.current), 50);
  }

  const setField = (name, value) => setForm((f) => ({ ...f, [name]: value }));
  const setLab = (key, value) => setForm((f) => ({ ...f, labs: { ...f.labs, [key]: value } }));
  const setUnit = (key, value) => setForm((f) => ({ ...f, units: { ...f.units, [key]: value } }));

  function toggleGroup(key, open) {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (open) next.add(key);
      else next.delete(key);
      return next;
    });
  }

  function applyExample(id) {
    const example = examples.find((e) => e.id === id);
    if (!example || !catalog) return;
    const { input } = example;
    const labs = Object.fromEntries(Object.entries(input.laboratory_data).map(([k, v]) => [k, num(v)]));
    setForm({ case_id: input.case_id, sex: input.sex, age: String(input.age), labs, units: {} });
    setErrors({});
    setFormError("");
    setOpenGroups(new Set(catalog.analytes.filter((a) => a.key in labs).map((a) => a.group)));
  }

  function reset() {
    setForm({ ...EMPTY, labs: {}, units: {} });
    setErrors({});
    setFormError("");
  }

  // Ошибки показываем у полей, раскрываем группы, где они есть, и переводим фокус на первую
  function showErrors(fieldErrors, summary) {
    setErrors(fieldErrors);
    setFormError(summary);
    const groupsWithErrors = catalog.analytes.filter((a) => fieldErrors[`laboratory_data.${a.key}`]).map((a) => a.group);
    if (groupsWithErrors.length) setOpenGroups((prev) => new Set([...prev, ...groupsWithErrors]));
    setTimeout(() => formRef.current?.querySelector("[aria-invalid='true']")?.focus(), 50);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const clientErrors = {};
    if (!form.case_id.trim()) clientErrors.case_id = "Укажите ID случая (можно сгенерировать).";
    const age = toNumber(form.age);
    if (age === null) clientErrors.age = "Укажите возраст.";
    else if (Number.isNaN(age)) clientErrors.age = "Возраст должен быть числом.";

    const labs = {};
    const units = {};
    for (const analyte of catalog.analytes) {
      const value = toNumber(form.labs[analyte.key] ?? "");
      if (value === null) continue;
      if (Number.isNaN(value)) {
        clientErrors[`laboratory_data.${analyte.key}`] = "Значение должно быть числом.";
        continue;
      }
      labs[analyte.key] = value;
      const unit = form.units[analyte.key];
      if (unit && unit !== analyte.unit_code) units[analyte.key] = unit;
    }
    // Хватает ли данных для заключения, решает ML-модель: при нехватке она вернёт «недостаточно данных»
    if (Object.keys(clientErrors).length) {
      showErrors(clientErrors, "Проверьте отмеченные поля.");
      return;
    }

    setManualLoading(true);
    setErrors({});
    setFormError("");
    setResult(null);
    try {
      const data = await api.screen({ case_id: form.case_id.trim(), sex: form.sex || null, age, laboratory_data: labs, units });
      setResult({ data, source: "manual" });
    } catch (e) {
      const fieldErrors = Object.fromEntries(e.errors.map((err) => [err.field, err.message]));
      showErrors(fieldErrors, e.errors.length ? "Проверьте отмеченные поля." : e.message);
    } finally {
      setManualLoading(false);
    }
  }

  const refFor = (a) => (form.sex === "male" ? a.ref_male : a.ref_female);
  const resultBlock = (source) =>
    result?.source === source && (
      <div ref={resultRef} className="reveal scroll-target">
        <ResultView result={result.data} />
      </div>
    );

  return (
    <div className="stack">
      <section className="intro reveal">
        <h1 className="page-title">Один пациент</h1>
        <p className="page-lead">
          Загрузите файл с анализами пациента: CSV или XLSX с одной строкой данных, как в шаблоне. Значения в других
          единицах будут автоматически переведены в стандартные.
        </p>
      </section>

      <section className="glass panel reveal">
        <FileDrop
          title="Перетащите файл пациента сюда"
          onFile={runFile}
          onError={(message) => {
            setFileCheck(null);
            setFileError(message);
          }}
          disabled={fileLoading}
        />
        <div className="form-toolbar">
          <button type="button" className="ghost-button" onClick={downloadTemplate}>
            Скачать шаблон
          </button>
          <label className="inline-label">
            <span>Или откройте пример</span>
            <select className="input select compact" value="" onChange={(e) => runExample(e.target.value)} disabled={fileLoading}>
              <option value="">Выберите пример…</option>
              {examples.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.title}
                </option>
              ))}
            </select>
          </label>
        </div>
        {fileLoading && <p role="status">Проверяем и анализируем {fileName}…</p>}
        {fileError && (
          <p className="form-error" role="alert">
            {fileError}
          </p>
        )}
        <FileCheckPanel check={fileCheck} fileName={fileName} />
      </section>

      {resultBlock("file")}

      {/* Ручной ввод — запасной вариант, внизу страницы */}
      {!manualOpen ? (
        <div className="manual-switch reveal">
          <p className="muted">Нет файла с анализами?</p>
          <button type="button" className="ghost-button large" onClick={openManual}>
            Ввести показатели вручную
          </button>
        </div>
      ) : (
        <section ref={manualRef} className="scroll-target">
          {!catalog ? (
            <p className="glass panel">{formError || "Загружаем справочник показателей…"}</p>
          ) : (
            <form ref={formRef} className="glass panel reveal" onSubmit={handleSubmit} noValidate>
              <h2 className="panel-title">Ручной ввод показателей</h2>
              <p className="muted small-text">
                Пустые поля допустимы. Для заключения модели нужны пол, гемоглобин и хотя бы один показатель в каждой
                панели анализов, кроме одной. Если данных не хватит, сервис скажет, чего именно.
              </p>
              <div className="form-toolbar">
                <label className="inline-label">
                  <span>Заполнить примером</span>
                  <select className="input select compact" value="" onChange={(e) => applyExample(e.target.value)}>
                    <option value="">Выберите пример…</option>
                    {examples.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.title}
                      </option>
                    ))}
                  </select>
                </label>
                <button type="button" className="ghost-button" onClick={reset}>
                  Очистить форму
                </button>
              </div>

              <fieldset className="basics">
                <legend className="visually-hidden">Данные случая</legend>
                <div className="field">
                  <label className="field-label" htmlFor="case_id">ID случая</label>
                  <div className="with-button">
                    <input
                      id="case_id"
                      className="input"
                      value={form.case_id}
                      onChange={(e) => setField("case_id", e.target.value)}
                      placeholder="Например, C-7K2QX9"
                      aria-invalid={Boolean(errors.case_id)}
                      aria-describedby="case_id-hint"
                    />
                    <button type="button" className="ghost-button" onClick={() => setField("case_id", generateId())}>
                      Сгенерировать
                    </button>
                  </div>
                  <p id="case_id-hint" className={errors.case_id ? "field-error" : "hint"}>
                    {errors.case_id ?? "Псевдонимизированный ID, без ФИО и других персональных данных."}
                  </p>
                </div>

                <div className="field">
                  <span className="field-label" id="sex-label">Пол</span>
                  <div className="segmented" role="radiogroup" aria-labelledby="sex-label">
                    {[
                      ["female", "Женский"],
                      ["male", "Мужской"],
                    ].map(([value, label]) => (
                      <label key={value} className={form.sex === value ? "active" : ""}>
                        <input
                          type="radio"
                          name="sex"
                          value={value}
                          checked={form.sex === value}
                          onChange={() => setField("sex", value)}
                          aria-invalid={Boolean(errors.sex)}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                  {errors.sex && <p className="field-error">{errors.sex}</p>}
                </div>

                <div className="field">
                  <label className="field-label" htmlFor="age">Возраст, лет</label>
                  <input
                    id="age"
                    className="input"
                    inputMode="numeric"
                    value={form.age}
                    onChange={(e) => setField("age", e.target.value)}
                    aria-invalid={Boolean(errors.age)}
                  />
                  {errors.age && <p className="field-error">{errors.age}</p>}
                </div>
              </fieldset>

              {catalog.groups.map((group) => {
                const items = catalog.analytes.filter((a) => a.group === group.key);
                const filled = items.filter((a) => (form.labs[a.key] ?? "").trim() !== "").length;
                return (
                  <details
                    key={group.key}
                    className="group"
                    open={openGroups.has(group.key)}
                    onToggle={(e) => toggleGroup(group.key, e.currentTarget.open)}
                  >
                    <summary>
                      <span>{group.label}</span>
                      <span className="muted">
                        заполнено {filled} из {items.length}
                      </span>
                    </summary>
                    <div className="lab-grid">
                      {items.map((a) => {
                        const fieldKey = `laboratory_data.${a.key}`;
                        const ref = refFor(a);
                        const unit = form.units[a.key] ?? a.unit_code;
                        return (
                          <div key={a.key} className="field">
                            <label className="field-label" htmlFor={`lab-${a.key}`}>
                              {a.label}
                              {a.required && <span className="required"> (нужен для заключения)</span>}
                            </label>
                            <div className="with-unit">
                              <input
                                id={`lab-${a.key}`}
                                className="input"
                                inputMode="decimal"
                                value={form.labs[a.key] ?? ""}
                                onChange={(e) => setLab(a.key, e.target.value)}
                                aria-invalid={Boolean(errors[fieldKey])}
                              />
                              {a.alt_units.length ? (
                                <select
                                  className="input select unit"
                                  value={unit}
                                  onChange={(e) => setUnit(a.key, e.target.value)}
                                  aria-label={`Единица: ${a.label}`}
                                >
                                  <option value={a.unit_code}>{a.unit}</option>
                                  {a.alt_units.map((u) => (
                                    <option key={u.code} value={u.code}>
                                      {u.label}
                                    </option>
                                  ))}
                                </select>
                              ) : (
                                <span className="unit-text">{a.unit}</span>
                              )}
                            </div>
                            <p className={errors[fieldKey] ? "field-error" : "hint"}>
                              {errors[fieldKey] ??
                                (unit !== a.unit_code
                                  ? `Будет переведено в ${a.unit}`
                                  : ref && (ref[0] !== null || ref[1] !== null)
                                    ? `Ориентир: ${ref[0] !== null ? num(ref[0]) : "до"}${ref[0] !== null && ref[1] !== null ? "–" : " "}${ref[1] !== null ? num(ref[1]) : ""} ${a.unit}`
                                    : "")}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </details>
                );
              })}

              {formError && (
                <p className="form-error" role="alert">
                  {formError}
                </p>
              )}
              <button type="submit" className="primary-button" disabled={manualLoading}>
                {manualLoading ? "Анализируем…" : "Выполнить анализ"}
              </button>
            </form>
          )}
        </section>
      )}

      {resultBlock("manual")}
    </div>
  );
}

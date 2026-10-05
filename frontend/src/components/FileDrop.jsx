import { useRef, useState } from "react";
import { MAX_FILE_MB, precheckFile } from "../api";

// Зона загрузки файла: перетаскивание или кнопка «Выбрать файл».
// Перед отправкой проверяем расширение и размер прямо в браузере.
export default function FileDrop({ title, hint, onFile, onError, disabled }) {
  const [over, setOver] = useState(false);
  const inputRef = useRef(null);

  function take(file) {
    const problem = precheckFile(file);
    if (problem) onError(problem);
    else onFile(file);
  }

  return (
    <div
      className={`dropzone ${over ? "over" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        if (!disabled) take(e.dataTransfer.files[0]);
      }}
    >
      <p className="dropzone-title">{title}</p>
      <p className="muted">{hint ?? `CSV или XLSX, до ${MAX_FILE_MB} МБ`}</p>
      <button type="button" className="primary-button" onClick={() => inputRef.current?.click()} disabled={disabled}>
        Выбрать файл
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.xlsx"
        className="visually-hidden"
        tabIndex={-1}
        onChange={(e) => {
          take(e.target.files[0]);
          e.target.value = ""; // чтобы тот же файл можно было выбрать повторно
        }}
      />
    </div>
  );
}

// Единственное место, где фронтенд общается с бэкендом.
import { clearSession, loadSession } from "./session";

// Ошибка запроса: message — понятный текст, errors — список {field, message},
// data — полный ответ сервера (например, отчёт о проверке файла file_check)
export class ApiError extends Error {
  constructor(message, { status = 0, errors = [], data = null } = {}) {
    super(message);
    this.status = status;
    this.errors = errors;
    this.data = data;
  }
}

async function request(path, { method = "GET", body, form, auth = true, raw = false } = {}) {
  const headers = {};
  const { token } = loadSession();
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let payload;
  if (form) {
    payload = form; // FormData: заголовок Content-Type браузер поставит сам
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`/api/v1${path}`, { method, headers, body: payload });
  } catch {
    throw new ApiError("Сервер недоступен. Проверьте, что бэкенд запущен.");
  }

  // Токен истёк или недействителен: выходим и сообщаем приложению
  if (response.status === 401 && auth) {
    clearSession();
    window.dispatchEvent(new Event("session-expired"));
  }

  if (!response.ok) {
    let data = null;
    try {
      data = await response.json();
    } catch {
      // ответ не в формате JSON
    }
    const errors = Array.isArray(data?.errors) ? data.errors : [];
    const detail = typeof data?.detail === "string" ? data.detail : null;
    const message = detail ?? errors[0]?.message ?? `Ошибка сервера (${response.status}).`;
    throw new ApiError(message, { status: response.status, errors, data });
  }
  return raw ? response : response.json();
}

function upload(path, file) {
  const form = new FormData();
  form.append("file", file);
  return request(path, { method: "POST", form });
}

export const api = {
  login: (login, password) => request("/auth/login", { method: "POST", body: { login, password }, auth: false }),
  health: () => request("/health", { auth: false }),
  analytes: () => request("/analytes", { auth: false }),
  examples: () => request("/screening/examples"),
  screen: (input) => request("/screening", { method: "POST", body: input }),
  screenFile: (file) => upload("/screening/file", file), // один пациент из файла
  batch: (file) => upload("/screening/batch", file), // много пациентов из файла
  // Скачивание файла с авторизацией (шаблон, демо-файл, пример)
  download: async (path) => (await request(path, { raw: true })).blob(),
};

// Сохраняет Blob как файл на компьютере пользователя
export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

// Проверки файла до отправки на сервер (быстрая обратная связь)
export const MAX_FILE_MB = 5;
export function precheckFile(file) {
  if (!file) return "Файл не выбран.";
  if (!/\.(csv|xlsx)$/i.test(file.name)) return `«${file.name}»: поддерживаются только файлы CSV и XLSX.`;
  if (file.size === 0) return `«${file.name}»: файл пустой.`;
  if (file.size > MAX_FILE_MB * 1024 * 1024) return `«${file.name}»: файл больше ${MAX_FILE_MB} МБ.`;
  return null;
}

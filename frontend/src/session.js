// Сессия врача: токен и данные пользователя.
// sessionStorage живёт, пока открыта вкладка: после закрытия вкладки нужно войти заново.
// Данные пациентов здесь НЕ хранятся.
const KEY = "anemia_screening_session";

export function loadSession() {
  try {
    const raw = sessionStorage.getItem(KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function saveSession(session) {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(session));
  } catch {
    // хранилище недоступно (приватный режим): работаем без сохранения
  }
}

export function clearSession() {
  try {
    sessionStorage.removeItem(KEY);
  } catch {
    // ничего не делаем
  }
}

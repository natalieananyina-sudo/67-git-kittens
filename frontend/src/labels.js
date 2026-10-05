// Подписи для интерфейса

export const SEX_LABELS = { female: "Женщина", male: "Мужчина" };

// Короткие названия причин (deficiency_cause модели) для таблицы «Много пациентов»
export const CAUSE_SHORT = {
  iron_deficiency: "Железо",
  B12_deficiency: "B12",
  folate_deficiency: "Фолаты",
  B6_deficiency: "B6",
  copper_deficiency: "Медь",
  inflammation: "Воспаление",
  iron_B12: "Железо + B12",
  iron_folate: "Железо + фолаты",
  B12_folate: "B12 + фолаты",
  undetermined: "Не определена",
};

export const SEVERITY = {
  attention: { label: "Анемия", className: "sev-attention" },
  watch: { label: "Требует уточнения", className: "sev-watch" },
  ok: { label: "Без отклонений", className: "sev-ok" },
  insufficient: { label: "Недостаточно данных", className: "sev-muted" },
};

// 1 год, 2 года, 5 лет
export function years(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${n} год`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${n} года`;
  return `${n} лет`;
}

// 12.5 -> "12,5"
export function num(value) {
  if (value === null || value === undefined) return "—";
  return String(Math.round(value * 1000) / 1000).replace(".", ",");
}

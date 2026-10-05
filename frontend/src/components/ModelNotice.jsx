// Предупреждение, если финальная ML-модель не загрузилась и работает демо-резерв
export default function ModelNotice({ model }) {
  if (!model?.is_demo) return null;
  return (
    <p className="notice" role="note">
      <strong>Демонстрационный режим.</strong> {model.note}
    </p>
  );
}

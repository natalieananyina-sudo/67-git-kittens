"""
Обучение финальной модели и сохранение артефактов.

Сохраняет:
- models/model.pkl — финальная модель
- models/label_encoder.pkl — LabelEncoder для XGBoost/LightGBM
- reports/metrics.json — метрики на test
"""
import os
import sys
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, balanced_accuracy_score,
    classification_report, confusion_matrix
)

# Пути
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'src'))

from preprocess import load_features, split_data, LEAKAGE_COLS


def train_random_forest(X_train, y_train, random_state=42):
    """Обучает RandomForest — финальную модель."""
    model = RandomForestClassifier(
        n_estimators=300,
        class_weight='balanced',
        random_state=random_state,
        n_jobs=-1
    )
    model.fit(X_train, y_train)
    return model


def main():
    print("=" * 60)
    print("Обучение финальной модели")
    print("=" * 60)

    # Загрузка
    df = load_features()
    X_train, X_test, y_train, y_test, ids_train, ids_test = split_data(df)
    print(f"\nTrain: {X_train.shape}")
    print(f"Test:  {X_test.shape}")

    # Обучение
    print("\nОбучение RandomForest...")
    model = train_random_forest(X_train, y_train)

    # Оценка
    y_pred = model.predict(X_test)

    metrics = {
        'model': 'RandomForest',
        'n_estimators': 300,
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'macro_f1': float(f1_score(y_test, y_pred, average='macro')),
        'balanced_accuracy': float(balanced_accuracy_score(y_test, y_pred)),
        'per_class': classification_report(y_test, y_pred, output_dict=True)
    }

    print(f"\n=== Метрики на test ===")
    print(f"Accuracy:     {metrics['accuracy']:.4f}")
    print(f"Macro-F1:     {metrics['macro_f1']:.4f}")
    print(f"Balanced acc: {metrics['balanced_accuracy']:.4f}")

    # Сохранение
    models_dir = os.path.join(BASE_DIR, 'models')
    reports_dir = os.path.join(BASE_DIR, 'reports')
    os.makedirs(models_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    model_path = os.path.join(models_dir, 'model.pkl')
    metrics_path = os.path.join(reports_dir, 'metrics.json')

    joblib.dump(model, model_path)
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"\nСохранено:")
    print(f"  Модель:  {model_path}")
    print(f"  Метрики: {metrics_path}")


if __name__ == '__main__':
    main()
"""
Препроцессинг данных для модели скрининга анемий.

Модуль содержит функции:
- load_features: загрузка df_features.csv
- get_feature_columns: список признаков (без утечек)
- split_data: train/test split stratified
- save_splits: сохранение X_train, X_test, y_train, y_test

Пути строятся относительно корня проекта — работают из любой директории.
"""
import os
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# ============ КОНСТАНТЫ ============

# Корень проекта (на 2 уровня выше от src/preprocess.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Пути по умолчанию
DEFAULT_INPUT = os.path.join(BASE_DIR, 'data', 'processed', 'df_features.csv')
DEFAULT_OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'processed')

# Колонки-таргеты (не использовать как признаки)
TARGET_COLS = [
    'anemia',
    'iron_deficiency', 'B12_deficiency', 'folate_deficiency',
    'B6_deficiency', 'copper_deficiency', 'inflammation_anemia',
    'mixed_deficiency',
    'anemia_class', 'deficiency_cause'
]

# Идентификатор (не использовать как признак)
ID_COLS = ['patient_id']

# Строковые колонки (не использовать как признаки — есть числовые дубликаты)
# sex → sex_M (0/1), age_group → age_years
STRING_COLS = ['sex', 'age_group']

# Все колонки-утечки + строковые
LEAKAGE_COLS = TARGET_COLS + ID_COLS + STRING_COLS

# Основной таргет для мультикласса
TARGET_MULTI = 'anemia_class'

# RANDOM_STATE для воспроизводимости
RANDOM_STATE = 42


# ============ ФУНКЦИИ ============

def load_features(path=None):
    """
    Загружает df_features.csv.

    По умолчанию — из data/processed/df_features.csv (от корня проекта).
    """
    if path is None:
        path = DEFAULT_INPUT

    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл не найден: {path}")

    return pd.read_csv(path)


def get_feature_columns(df):
    """Возвращает список признаков (без утечек)."""
    return [c for c in df.columns if c not in LEAKAGE_COLS]


def split_data(df, target=TARGET_MULTI, test_size=0.2, random_state=RANDOM_STATE):
    """
    Разделяет на train/test.

    - X: признаки (без утечек)
    - y: таргет (anemia_class)
    - Stratified по target
    - Сохраняет patient_id отдельно

    Возвращает: X_train, X_test, y_train, y_test, ids_train, ids_test
    """
    X = df.drop(columns=LEAKAGE_COLS)
    y = df[target]
    ids = df['patient_id']

    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X, y, ids,
        test_size=test_size,
        stratify=y,
        random_state=random_state
    )

    return X_train, X_test, y_train, y_test, ids_train, ids_test


def save_splits(X_train, X_test, y_train, y_test, ids_train, ids_test,
                output_dir=None):
    """
    Сохраняет train/test в CSV.

    По умолчанию — в data/processed/ (от корня проекта).
    """
    if output_dir is None:
        output_dir = DEFAULT_OUTPUT_DIR

    os.makedirs(output_dir, exist_ok=True)

    X_train.to_csv(os.path.join(output_dir, 'X_train.csv'), index=False)
    X_test.to_csv(os.path.join(output_dir, 'X_test.csv'), index=False)
    y_train.to_csv(os.path.join(output_dir, 'y_train.csv'), index=False)
    y_test.to_csv(os.path.join(output_dir, 'y_test.csv'), index=False)
    ids_train.to_csv(os.path.join(output_dir, 'train_ids.csv'), index=False, header=['patient_id'])
    ids_test.to_csv(os.path.join(output_dir, 'test_ids.csv'), index=False, header=['patient_id'])

    print(f"Сохранено в {output_dir}/")
    print(f"  X_train:   {X_train.shape}")
    print(f"  X_test:    {X_test.shape}")
    print(f"  y_train:   {y_train.shape}")
    print(f"  y_test:    {y_test.shape}")
    print(f"  train_ids: {ids_train.shape}")
    print(f"  test_ids:  {ids_test.shape}")


# ============ ТЕСТОВЫЙ ЗАПУСК ============

if __name__ == '__main__':
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"Входной файл: {DEFAULT_INPUT}")
    print(f"Выходная папка: {DEFAULT_OUTPUT_DIR}\n")

    # Загрузка
    df = load_features()
    print(f"Загружено: {df.shape}\n")

    # Признаки
    features = get_feature_columns(df)
    print(f"Признаков: {len(features)}")
    print(f"Утечки (исключены): {LEAKAGE_COLS}\n")

    # Split
    X_train, X_test, y_train, y_test, ids_train, ids_test = split_data(df)
    print(f"Train: {X_train.shape}")
    print(f"Test:  {X_test.shape}\n")

    # Проверка стратификации
    print("Распределение классов в train:")
    print(y_train.value_counts(normalize=True).round(3))
    print("\nРаспределение классов в test:")
    print(y_test.value_counts(normalize=True).round(3))

    # Проверка совпадения пропорций
    train_dist = y_train.value_counts(normalize=True)
    test_dist = y_test.value_counts(normalize=True)
    max_diff = (train_dist - test_dist).abs().max()
    print(f"\nMax разница пропорций train/test: {max_diff:.4f}")
    print(f"Стратификация {'корректна' if max_diff < 0.03 else 'НЕКОРРЕКТНА'}\n")

    # Сохранение
    save_splits(X_train, X_test, y_train, y_test, ids_train, ids_test)

    print("\nГотово!")
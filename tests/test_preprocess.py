"""
Тесты для модуля src/preprocess.py.

Проверяют:
- Загрузку df_features.csv
- Отсутствие утечек в признаках
- Размеры train/test
- Стратификацию split
- Отсутствие NaN в таргетах
"""
import sys
import os

# Добавляем src/ в путь импортов
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(BASE_DIR, 'src'))

import pytest
import pandas as pd

from preprocess import (
    load_features, get_feature_columns, split_data,
    LEAKAGE_COLS, TARGET_MULTI
)


# ============ ФИКСТУРЫ ============
@pytest.fixture(scope='module')
def df():
    """Загружает df_features.csv один раз для всех тестов."""
    return load_features()


@pytest.fixture(scope='module')
def splits(df):
    """Делает split один раз для всех тестов."""
    return split_data(df)


# ============ ТЕСТЫ ============

def test_load_features(df):
    """Проверяет, что df_features.csv загружается и имеет правильный размер."""
    assert df.shape == (840, 89), f"Ожидалось (840, 89), получено {df.shape}"
    assert 'patient_id' in df.columns
    assert 'anemia_class' in df.columns


def test_no_leakage_in_features(df):
    """Проверяет, что таргеты и строковые колонки не попали в признаки."""
    features = get_feature_columns(df)
    for col in LEAKAGE_COLS:
        assert col not in features, f"Утечка: {col} в признаках"


def test_feature_count(df):
    """Проверяет, что признаков 76."""
    features = get_feature_columns(df)
    assert len(features) == 76, f"Ожидалось 76 признаков, получено {len(features)}"


def test_no_string_columns_in_features(df):
    """Проверяет, что в X нет строковых колонок."""
    features = get_feature_columns(df)
    object_cols = df[features].select_dtypes(include='object').columns.tolist()
    assert len(object_cols) == 0, f"В X есть строковые колонки: {object_cols}"


def test_split_sizes(splits):
    """Проверяет размеры train/test."""
    X_train, X_test, y_train, y_test, ids_train, ids_test = splits
    assert X_train.shape == (672, 76), f"Train: ожидалось (672, 76), получено {X_train.shape}"
    assert X_test.shape == (168, 76), f"Test: ожидалось (168, 76), получено {X_test.shape}"
    assert y_train.shape == (672,)
    assert y_test.shape == (168,)


def test_stratification(splits):
    """Проверяет, что пропорции классов в train/test совпадают."""
    _, _, y_train, y_test, _, _ = splits
    train_dist = y_train.value_counts(normalize=True)
    test_dist = y_test.value_counts(normalize=True)
    max_diff = (train_dist - test_dist).abs().max()
    assert max_diff < 0.03, f"Стратификация нарушена: max diff = {max_diff}"


def test_no_nan_in_targets(splits):
    """Проверяет, что в таргетах нет NaN."""
    _, _, y_train, y_test, _, _ = splits
    assert y_train.notna().all(), "NaN в y_train"
    assert y_test.notna().all(), "NaN в y_test"


def test_ids_match_sizes(splits):
    """Проверяет, что количество ID совпадает с train/test."""
    X_train, X_test, _, _, ids_train, ids_test = splits
    assert len(ids_train) == len(X_train)
    assert len(ids_test) == len(X_test)


def test_all_classes_in_test(splits):
    """Проверяет, что все 12 классов есть в test (благодаря стратификации)."""
    _, _, _, y_test, _, _ = splits
    assert y_test.nunique() == 12, f"В test не все классы: {y_test.nunique()}"
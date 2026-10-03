"""Train the reproducible hackathon classifier and export portable coefficients.

Usage: python ml/train.py /path/to/deficiency_anemia.csv
Only the derived JSON model is shipped with the web app. The CSV stays local.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

FEATURES = [
    "age_years", "sex", "hemoglobin", "RBC", "hematocrit", "MCV", "MCH",
    "MCHC", "RDW", "platelets", "WBC", "reticulocytes", "ferritin",
    "serum_iron", "transferrin", "TIBC", "UIBC", "TSAT", "sTfR", "Ret_He",
    "vitamin_B12", "active_B12", "MMA", "homocysteine", "folate",
    "vitamin_B6", "copper", "ceruloplasmin", "CRP", "ESR", "creatinine",
    "eGFR", "TSH", "albumin", "LDH", "indirect_bilirubin", "haptoglobin",
]


def matrix(frame, medians):
    raw = frame[FEATURES].copy()
    raw["sex"] = raw["sex"].map({"F": 0.0, "M": 1.0})
    raw = raw.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=float)
    missing = np.isnan(raw).astype(float)
    return np.concatenate((np.where(np.isnan(raw), medians, raw), missing), axis=1)


def fit(train, valid):
    raw = train[FEATURES].copy()
    raw["sex"] = raw["sex"].map({"F": 0.0, "M": 1.0})
    medians = raw.apply(pd.to_numeric, errors="coerce").median().fillna(0).to_numpy()
    scale = StandardScaler().fit(matrix(train, medians))
    model = LogisticRegression(max_iter=3000, C=0.3, class_weight="balanced")
    model.fit(scale.transform(matrix(train, medians)), train.anemia_class)
    pred = model.predict(scale.transform(matrix(valid, medians)))
    markers = ["ferritin", "serum_iron", "TSAT", "sTfR", "Ret_He", "vitamin_B12",
               "active_B12", "MMA", "homocysteine", "folate", "vitamin_B6",
               "copper", "ceruloplasmin", "CRP"]
    anemia = valid.hemoglobin.to_numpy() < np.where(valid.sex.to_numpy() == "F", 120, 130)
    no_anemia_classes = {"no_anemia_no_deficiency", "latent_deficiency",
                         "B12_deficiency_no_anemia", "folate_deficiency_no_anemia"}
    anemia_classes = {"iron_deficiency_anemia", "B12_deficiency_anemia",
                      "folate_deficiency_anemia", "inflammation_anemia", "anemia_other"}
    disagreement = np.array([(has_anemia and label in no_anemia_classes) or
                             (not has_anemia and label in anemia_classes)
                             for has_anemia, label in zip(anemia, pred)])
    emitted = (valid[markers].notna().sum(axis=1).to_numpy() >= 2) & ~disagreement
    scores = {
        "rows_train": len(train), "rows_test": len(valid),
        "accuracy": round(accuracy_score(valid.anemia_class, pred), 4),
        "macro_f1": round(f1_score(valid.anemia_class, pred, average="macro"), 4),
        "policy_emitted": int(emitted.sum()),
        "policy_abstained": int((~emitted).sum()),
        "accuracy_when_emitted": round(accuracy_score(valid.anemia_class.to_numpy()[emitted], pred[emitted]), 4),
        "per_class": classification_report(valid.anemia_class, pred, output_dict=True, zero_division=0),
    }
    return medians, scale, model, scores


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    data = pd.read_csv(sys.argv[1])
    if data.patient_id.duplicated().any():
        raise ValueError("Duplicate patient_id")
    train, test = train_test_split(data, test_size=0.2, stratify=data.anemia_class, random_state=42)
    _, _, _, scores = fit(train, test)
    # Refit on all supplied data only after held-out evaluation.
    medians, scale, model, _ = fit(data, test)
    output = Path(__file__).resolve().parents[1] / "lib" / "model.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({
        "features": FEATURES, "medians": medians.tolist(),
        "mean": scale.mean_.tolist(), "scale": scale.scale_.tolist(),
        "classes": model.classes_.tolist(), "coef": model.coef_.tolist(),
        "intercept": model.intercept_.tolist(),
    }, ensure_ascii=False, separators=(",", ":")))
    metrics = output.parent / "evaluation.json"
    metrics.write_text(json.dumps(scores, ensure_ascii=False, indent=2))
    print(json.dumps({k: scores[k] for k in ("rows_train", "rows_test", "accuracy", "macro_f1")}, ensure_ascii=False))


if __name__ == "__main__":
    main()

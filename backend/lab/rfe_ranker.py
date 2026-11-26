from hashlib import sha256
import json

import numpy as np
from sklearn.feature_selection import RFE
from sklearn.metrics import balanced_accuracy_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

SEED = 1080
RFE_MINIMUM_DAYS = 6


class InadequateSample(ValueError):
    pass


def snapshot_training_rows(samples, measures):
    """把申报时冻结的训练样本还原成拟合输入，标签以快照为准。"""
    requested = [item.id for item in measures]
    rows = []
    for sample in sorted(samples, key=lambda item: (item.day, item.id)):
        values = sample.values
        if any(str(item) not in values for item in requested):
            continue
        rows.append({
            "run_id": sample.run_id,
            "day": sample.day.isoformat(),
            "shift": sample.shift,
            "camera_review": int(sample.camera_review),
            "inputs": [values[str(item)] for item in requested],
        })
    return rows


def _selector(budget):
    return RFE(LinearSVC(dual=False, class_weight="balanced", random_state=SEED),
               n_features_to_select=budget, step=1)


def fit_rows(rows, measure_ids, budget):
    labels = [row["camera_review"] for row in rows]
    groups = [row["day"] for row in rows]
    shifts = [row["shift"] for row in rows]
    if len(set(groups)) < RFE_MINIMUM_DAYS or set(shifts) != {"dawn", "dusk"} or len(set(labels)) != 2:
        raise InadequateSample("需要至少六个日期、早晚两班及两类镜头人工复看标签的全项目记录。")
    x, y, day_groups = np.asarray([row["inputs"] for row in rows]), np.asarray(labels), np.asarray(groups)
    folds = []
    for train, held in GroupKFold(n_splits=3).split(x, y, day_groups):
        if len(set(y[train])) != 2 or len(set(y[held])) != 2:
            raise InadequateSample("按日期留组后有折缺少一类镜头复看标签，需补样。")
        scaler = StandardScaler().fit(x[train])
        train_x, held_x = scaler.transform(x[train]), scaler.transform(x[held])
        fit = _selector(budget).fit(train_x, y[train])
        plain = LinearSVC(dual=False, class_weight="balanced", random_state=SEED).fit(train_x, y[train])
        folds.append({"held_days": sorted(set(day_groups[held])),
                      "compact": round(balanced_accuracy_score(y[held], fit.predict(held_x)), 4),
                      "full": round(balanced_accuracy_score(y[held], plain.predict(held_x)), 4)})
    result = make_pipeline(StandardScaler(), _selector(budget)).fit(x, y).named_steps["rfe"]
    metrics = {"model": "RFE + LinearSVC", "seed": SEED, "folds": folds, "samples": len(x),
               "compact_score": round(sum(fold["compact"] for fold in folds) / len(folds), 4),
               "full_score": round(sum(fold["full"] for fold in folds) / len(folds), 4),
               "input_sha256": sha256(json.dumps(
                   [[row["inputs"] for row in rows], labels, groups]).encode()).hexdigest()}
    return {item: (bool(keep), int(rank)) for item, keep, rank in
            zip(measure_ids, result.support_, result.ranking_, strict=True)}, metrics

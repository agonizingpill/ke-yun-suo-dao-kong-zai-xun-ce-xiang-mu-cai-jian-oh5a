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


def _selector(budget):
    return RFE(LinearSVC(dual=False, class_weight="balanced", random_state=SEED),
               n_features_to_select=budget, step=1)


def fit_optional(runs, measures, budget):
    requested = [item.id for item in measures]
    inputs, labels, groups, shifts = [], [], [], []
    for run in runs:
        by_id = {mark.measure_id: mark.value for mark in run.marks}
        if not set(requested).issubset(by_id):
            continue
        inputs.append([by_id[item] for item in requested])
        labels.append(int(run.camera_review))
        groups.append(run.day.isoformat())
        shifts.append(run.shift)
    if len(set(groups)) < RFE_MINIMUM_DAYS or set(shifts) != {"dawn", "dusk"} or len(set(labels)) != 2:
        raise InadequateSample("需要至少六个日期、早晚两班及两类镜头人工复看标签的全项目记录。")
    x, y, day_groups = np.asarray(inputs), np.asarray(labels), np.asarray(groups)
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
               "input_sha256": sha256(json.dumps([inputs, labels, groups]).encode()).hexdigest()}
    return {item: (bool(keep), int(rank)) for item, keep, rank in
            zip(requested, result.support_, result.ranking_, strict=True)}, metrics

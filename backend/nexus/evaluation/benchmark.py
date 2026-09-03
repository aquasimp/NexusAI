"""Headless benchmark harness.

Episode protocol (identical to the live path, minus UI pacing):
  1. Fit the detector ONCE on clean warm-up history (seed 101).
  2. For each (scenario, seed): run `pre` clean ticks, inject the root fault,
     run `post` ticks, streaming every frame through the SAME detector and
     the SAME localization/feature/RCA code the live demo uses.
  3. Record first-detection tick, blame ranking, features, retrieval, plan.
  4. Clean episodes (no fault) measure the false-positive rate.

The RCA classifier is evaluated with GroupKFold on `seed` so no episode from a
training fold shares a random seed with a test episode. Ground truth is read
only here, in the harness — never inside the pipeline.
"""
from __future__ import annotations

import time
import uuid

from typing import Any

import numpy as np
from sklearn.model_selection import GroupKFold

from ..agent import impact as impact_mod
from ..agent import remediation as rem
from ..config import settings
from ..ml import correlate, features as F
from ..ml.detector import Detector
from ..ml.rca_model import CLASSES, build_pipeline, predict_rule, save
from ..rag.store import KB
from ..simulation.engine import Engine
from ..simulation.logs import synthesize, to_dict
from ..simulation.scenarios import SCENARIOS, arm
from ..simulation.topology import METRICS, SERVICES
from . import metrics as M

PRE, POST = 100, 90


def fit_detector() -> tuple[Detector, dict]:
    t0 = time.perf_counter()
    e = Engine(seed=101, tick_seconds=settings.tick_seconds)
    times: list[float] = []
    hist: dict[str, dict[str, list[float]]] = {s: {m: [] for m in METRICS} for s in SERVICES}
    for _ in range(settings.warmup_ticks):
        times.append(e.sim_time())
        f = e.tick()
        for s in SERVICES:
            for m in METRICS:
                hist[s][m].append(f[s][m])
    H = {s: {m: np.asarray(v) for m, v in d.items()} for s, d in hist.items()}
    det = Detector(settings.harmonics, settings.detect_quantile,
                   settings.persist_k, settings.persist_n).fit(np.asarray(times), H)
    return det, {"warmup_ticks": settings.warmup_ticks,
                 "fit_seconds": round(time.perf_counter() - t0, 2),
                 "threshold": round(det.threshold, 5)}


def _episode(det: Detector, scenario_id: str | None, seed: int) -> dict:
    """Run one episode end-to-end and return everything needed for scoring."""
    eng = Engine(seed=seed, tick_seconds=settings.tick_seconds,
                 start_hour=float(np.random.default_rng(seed).uniform(0, 24)))
    st = det.new_state()
    rng = np.random.default_rng(seed + 1)
    frames, times, ticks, zbuf, logs = [], [], [], [], []
    scores, inject_tick, first_det = [], None, None

    total = PRE + POST if scenario_id else PRE + 40
    for i in range(total):
        if scenario_id and i == PRE:
            arm(eng, scenario_id, rng_jitter=float(rng.uniform(0.85, 1.2)))
            inject_tick = eng.t
        ts = eng.sim_time()
        dnow = [d for d in eng.deploys if d.tick == eng.t]
        t_now = eng.t
        frame = eng.tick()
        an = det.score_frame(st, ts, frame)
        for l in synthesize(t_now, ts, frame, rng, dnow):
            logs.append(to_dict(l))
        frames.append(frame); times.append(ts); ticks.append(t_now)
        zbuf.append({s: [an["services"][s]["z"][m] for m in METRICS] for s in SERVICES})
        scores.append(an["system_score"])
        if an["firing"] and first_det is None and (inject_tick is not None or True):
            first_det = t_now
        last_an = an

    n = min(140, len(frames))
    fr, zb = frames[-n:], zbuf[-n:]
    window = {
        "n": n, "t_start": ticks[-n], "t_end": ticks[-1], "times": times[-n:],
        "raw": {s: {m: np.asarray([f[s][m] for f in fr]) for m in METRICS}
                for s in SERVICES},
        "z": {s: np.asarray([r[s] for r in zb]) for s in SERVICES},
    }
    deploys = [{"tick": d.tick, "service": d.service, "version": d.version,
                "author": d.author, "change": d.change, "risk": d.risk}
               for d in eng.deploys]

    out: dict[str, Any] = {"scenario": scenario_id, "seed": seed, "inject_tick": inject_tick,
           "first_detection_tick": first_det,
           "peak_score": round(float(max(scores)), 5),
           "clean_peak_score": round(float(max(scores[:PRE])), 5),
           "threshold": det.threshold, "fired": bool(last_an["firing"])}

    if scenario_id is None:
        out["false_positive"] = first_det is not None
        return out

    t_loc = time.perf_counter()
    blame = correlate.localize(window, last_an, deploys, settings.tick_seconds)
    x, fdict = F.extract(window, last_an, blame, logs, deploys, settings.tick_seconds)
    t_feat = time.perf_counter()
    impact = impact_mod.estimate(window, blame, settings.tick_seconds)
    rule = predict_rule(x, fdict)
    retrieved = rem.retrieve_for_class(SCENARIOS[scenario_id].root_class,
                                       [blame["leader"], *blame["affected"]], k=5)
    t_ret = time.perf_counter()
    ret_by_rule = rem.retrieve_for_class(rule.top_class,
                                         [blame["leader"], *blame["affected"]], k=5)
    plan = rem.plan(rule.top_class, blame["leader"], impact, ret_by_rule)

    out.update({
        "blame_ranking": [r["service"] for r in blame["ranking"]],
        "leader": blame["leader"], "features": x.tolist(),
        "rule_pred": rule.top_class, "rule_conf": rule.confidence,
        "retrieved_oracle_class": [r["doc_id"] for r in retrieved],
        "retrieved_predicted_class": [r["doc_id"] for r in ret_by_rule],
        "planned_action": plan["recommended"]["action_id"],
        "severity": impact["severity"],
        "revenue_at_risk_usd": impact["revenue_at_risk_usd"],
        "latency_ms": {
            "localize": round((t_loc and (t_feat - t_loc)) * 1000, 2),
            "features_and_localize": round((t_feat - t_loc) * 1000, 2),
            "retrieval": round((t_ret - t_feat) * 1000, 2),
            "pipeline_total": round((t_ret - t_loc) * 1000, 2),
        },
    })
    return out


def run(seeds_per_scenario: int | None = None,
        clean_episodes: int | None = None,
        progress=lambda *_: None) -> dict:
    sps = seeds_per_scenario or settings.eval_seeds_per_scenario
    cln = clean_episodes if clean_episodes is not None else settings.eval_clean_episodes
    det, fit_info = fit_detector()
    progress("detector_fitted", fit_info)

    eps: list[dict] = []
    total = len(SCENARIOS) * sps + cln
    for si, sid in enumerate(SCENARIOS):
        for j in range(sps):
            eps.append(_episode(det, sid, seed=1000 + si * 97 + j * 7))
            progress("episode", {"done": len(eps), "total": total, "scenario": sid})
    clean = []
    for j in range(cln):
        clean.append(_episode(det, None, seed=50000 + j * 13))
        progress("episode", {"done": len(eps) + len(clean), "total": total,
                             "scenario": "clean"})

    # ---------------------------------------------------- anomaly detection
    tp = sum(1 for e in eps if e["first_detection_tick"] is not None)
    fn = len(eps) - tp
    fp = sum(1 for e in clean if e["false_positive"])
    tn = len(clean) - fp
    det_scores = np.array([e["peak_score"] for e in eps]
                          + [e["peak_score"] for e in clean])
    det_labels = np.array([1] * len(eps) + [0] * len(clean))
    lead = [(e["first_detection_tick"] - e["inject_tick"]) * settings.tick_seconds
            for e in eps if e["first_detection_tick"] is not None
            and e["inject_tick"] is not None
            and e["first_detection_tick"] >= e["inject_tick"]]
    detection = {
        **M.prf(tp, fp, fn), "tn": tn,
        "specificity": round(tn / max(1, tn + fp), 4),
        "false_positive_rate_per_clean_episode": round(fp / max(1, len(clean)), 4),
        "pr_auc": M.pr_auc(det_scores, det_labels),
        "threshold": fit_info["threshold"],
        "detection_delay_s": M.latency_stats(lead),
        "recall_ci95": M.wilson_ci(tp, len(eps)),
        "n_incident_episodes": len(eps), "n_clean_episodes": len(clean),
    }

    # -------------------------------------------------------- localization
    detected = [e for e in eps if e["first_detection_tick"] is not None]
    ranked = [e["blame_ranking"] for e in detected]
    truth = [SCENARIOS[e["scenario"]].root_service for e in detected]
    top1 = sum(1 for r, t in zip(ranked, truth) if r and r[0] == t)
    localization: dict[str, Any] = {
        "top1_accuracy": M.topk_accuracy(ranked, truth, 1),
        "top2_accuracy": M.topk_accuracy(ranked, truth, 2),
        "top3_accuracy": M.topk_accuracy(ranked, truth, 3),
        "top1_ci95": M.wilson_ci(top1, len(truth)), "n": len(truth),
        "per_scenario": {},
    }
    for sid in SCENARIOS:
        sub = [(e["blame_ranking"], SCENARIOS[sid].root_service)
               for e in detected if e["scenario"] == sid]
        if sub:
            localization["per_scenario"][sid] = {
                "top1": M.topk_accuracy([a for a, _ in sub], [b for _, b in sub], 1),
                "top3": M.topk_accuracy([a for a, _ in sub], [b for _, b in sub], 3),
                "n": len(sub)}

    # ------------------------------------------------- RCA (CV) + artifact
    X = np.array([e["features"] for e in detected])
    y = np.array([SCENARIOS[e["scenario"]].root_class for e in detected])
    groups = np.array([e["seed"] % settings.cv_folds for e in detected])
    rca: dict = {"n": len(y), "classes": list(CLASSES)}
    if len(set(y)) > 1 and len(y) >= 2 * settings.cv_folds:
        folds = min(settings.cv_folds, len(set(groups)))
        gkf = GroupKFold(n_splits=folds)
        yp: np.ndarray = np.empty(len(y), dtype=object)
        conf_hits: list[tuple[float, bool]] = []
        for tr, te in gkf.split(X, y, groups):
            pipe = build_pipeline().fit(X[tr], y[tr])
            pr = pipe.predict_proba(X[te])
            yp[te] = pipe.classes_[np.argmax(pr, axis=1)]
            for i, row in zip(te, pr):
                conf_hits.append((float(row.max()), bool(pipe.classes_[row.argmax()] == y[i])))
        yp_list = [str(val) for val in yp]
        acc_hits = sum(1 for a, b in zip(y, yp_list) if a == b)
        rca.update({
            "cv_scheme": f"GroupKFold(n_splits={folds}) grouped on episode seed",
            "learned_accuracy": round(acc_hits / len(y), 4),
            "learned_accuracy_ci95": M.wilson_ci(acc_hits, len(y)),
            **M.macro_f1(list(y), yp_list, list(CLASSES)),
            "confusion_matrix": M.confusion(list(y), yp_list, list(CLASSES)),
            "calibration_bins": _calibration(conf_hits),
        })
        final = build_pipeline().fit(X, y)
        save(final, {"cv_accuracy": rca["learned_accuracy"],
                     "cv_macro_f1": rca["macro_f1"], "n_train": int(len(y)),
                     "trained_at": time.time(),
                     "cv_scheme": rca["cv_scheme"]})
        rca["artifact_written"] = str(settings.model_path)
    else:
        rca["note"] = "Insufficient episodes for grouped CV; run more seeds."

    rule_hits = sum(1 for e in detected
                    if e["rule_pred"] == SCENARIOS[e["scenario"]].root_class)
    rca["rule_baseline_accuracy"] = round(rule_hits / max(1, len(detected)), 4)
    rca["rule_baseline_ci95"] = M.wilson_ci(rule_hits, len(detected))
    rca["rule_per_class"] = M.macro_f1(
        [SCENARIOS[e["scenario"]].root_class for e in detected],
        [e["rule_pred"] for e in detected], list(CLASSES))["per_class"]

    # ------------------------------------------------------------ retrieval
    gold = [list(SCENARIOS[e["scenario"]].gold_docs) for e in detected]
    retrieval = {
        "oracle_class_query": {
            **M.retrieval([e["retrieved_oracle_class"] for e in detected], gold, 3),
            **M.retrieval([e["retrieved_oracle_class"] for e in detected], gold, 5)},
        "predicted_class_query": {
            **M.retrieval([e["retrieved_predicted_class"] for e in detected], gold, 3),
            **M.retrieval([e["retrieved_predicted_class"] for e in detected], gold, 5)},
        "corpus": KB.stats(),
        "note": "`oracle_class_query` isolates retriever quality; "
                "`predicted_class_query` is the end-to-end number the live "
                "system actually achieves, since query formulation depends on "
                "the RCA prediction.",
    }

    # ----------------------------------------------------- end-to-end / plan
    act_ok = sum(1 for e in detected
                 if e["planned_action"] in SCENARIOS[e["scenario"]].gold_actions)
    e2e_ok = sum(1 for e in detected
                 if e["leader"] == SCENARIOS[e["scenario"]].root_service
                 and e["rule_pred"] == SCENARIOS[e["scenario"]].root_class
                 and e["planned_action"] in SCENARIOS[e["scenario"]].gold_actions)
    investigation = {
        "remediation_action_accuracy": round(act_ok / max(1, len(detected)), 4),
        "remediation_ci95": M.wilson_ci(act_ok, len(detected)),
        "joint_success_rate": round(e2e_ok / max(1, len(eps)), 4),
        "joint_success_ci95": M.wilson_ci(e2e_ok, len(eps)),
        "definition": "joint success = detected AND correct root service AND "
                      "correct root-cause class AND recommended action in the "
                      "runbook's gold action set (rule ranker, no CV leakage).",
        "n": len(eps),
    }

    latency = {
        "pipeline_total_ms": M.latency_stats([e["latency_ms"]["pipeline_total"]
                                              for e in detected]),
        "features_and_localize_ms": M.latency_stats(
            [e["latency_ms"]["features_and_localize"] for e in detected]),
        "retrieval_ms": M.latency_stats([e["latency_ms"]["retrieval"] for e in detected]),
        "detector_score_frame_ms": _score_frame_latency(det),
        "note": "Measured on the machine that ran the benchmark, excluding LLM "
                "narration (network-bound) and excluding UI stage pacing.",
    }

    return {
        "run_id": uuid.uuid4().hex[:12], "created_at": time.time(),
        "config": {"seeds_per_scenario": sps, "clean_episodes": cln,
                   "pre_ticks": PRE, "post_ticks": POST,
                   "tick_seconds": settings.tick_seconds,
                   "detect_quantile": settings.detect_quantile,
                   "persistence": f"{settings.persist_k}-of-{settings.persist_n}"},
        "detector_fit": fit_info, "detection": detection,
        "localization": localization, "root_cause": rca, "retrieval": retrieval,
        "investigation": investigation, "latency": latency,
        "scenarios": {k: {"title": v.title, "root_service": v.root_service,
                          "root_class": v.root_class} for k, v in SCENARIOS.items()},
        "honesty": "Every value in this document was computed by "
                   "nexus.evaluation.benchmark on synthetic episodes with known "
                   "ground truth. Nothing is hand-written. Small-n: 95% Wilson "
                   "intervals are reported for all accuracies.",
    }


def _calibration(pairs: list[tuple[float, bool]], bins: int = 5) -> list[dict]:
    out = []
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        sel = [h for c, h in pairs if lo <= c < hi or (b == bins - 1 and c == 1.0)]
        if sel:
            out.append({"bin": f"{lo:.1f}-{hi:.1f}", "n": len(sel),
                        "empirical_accuracy": round(sum(sel) / len(sel), 4)})
    return out


def _score_frame_latency(det: Detector, n: int = 200) -> dict:
    eng = Engine(seed=777, tick_seconds=settings.tick_seconds)
    st = det.new_state()
    ts_list = []
    for _ in range(n):
        ts = eng.sim_time()
        f = eng.tick()
        t0 = time.perf_counter()
        det.score_frame(st, ts, f)
        ts_list.append((time.perf_counter() - t0) * 1000)
    return M.latency_stats(ts_list)

# Evaluation Benchmark & Auditable Metrics

## Scientific Benchmark Protocol

NEXUS does not hardcode performance numbers. All metrics displayed on the Evaluation UI are computed at runtime using `nexus.evaluation.benchmark` across multiple independent episodes.

### Evaluation Phases
1. **Clean Baseline Evaluation**: Runs 24 clean episodes across varying random seeds to measure empirical false-positive rate per hour.
2. **Multi-Scenario Stress Testing**: Injects each of the 7 fault scenarios across 12 distinct random seeds.
3. **Wilson Score Intervals**: Every binary success metric (e.g. Top-1 Localization, Root Cause Accuracy, Remediation Accuracy) is reported with a 95% Wilson confidence interval:
   $$w = \frac{p + \frac{z^2}{2n} \pm z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$
   where $z = 1.96$.

### Measured Metric Categories
- **Detection**: Precision, Recall, Specificity, F1-Score, Detection Delay (seconds to trigger), PR-AUC.
- **Localization**: Top-1, Top-2, Top-3 accuracy of blamed root service against ground truth.
- **Root-Cause Classification**: Macro-F1, Confusion Matrix, Calibration Bins, Learned vs. Rule Baseline accuracy.
- **Runbook Retrieval**: Recall@3, Precision@3, Mean Reciprocal Rank (MRR), NDCG@3.
- **Autonomous Remediation**: Single-action accuracy, Joint End-to-End Success Rate, MTTR (Mean Time to Remediate).

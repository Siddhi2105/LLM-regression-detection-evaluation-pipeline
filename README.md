# LLM Regression Detection & Evaluation Pipeline

An automated CI/CD pipeline that evaluates LLM prompt changes against a golden dataset and detects quality regressions before deployment.

## Problem

LLM applications can become less accurate after a prompt or model change without causing traditional software errors. A change may improve some outputs while causing previously correct cases to fail.

This project solves that problem by automatically evaluating LLM behavior against a fixed golden dataset, comparing versions, identifying regressions, and flagging quality drops before they reach production.

## What It Does

- Evaluates an LLM customer support email classifier
- Tests prompt versions against a fixed golden dataset
- Measures accuracy and error rate
- Compares baseline and candidate prompt versions
- Identifies individual regression cases
- Classifies results as PASS, WARNING, or CRITICAL
- Runs regression checks through GitHub Actions
- Generates detailed HTML evaluation reports
- Detects performance drift across multiple evaluation runs

## Tech Stack

Python · OpenAI API · Pydantic · PyYAML · Pytest · GitHub Actions · Docker · Slack

## How It Works

```text
Prompt Change
     ↓
Golden Dataset Evaluation
     ↓
Accuracy & Error Rate
     ↓
Compare Versions
     ↓
Detect Regressions
     ↓
PASS / WARNING / CRITICAL
     ↓
CI Decision
````

## Regression Thresholds

| Accuracy Drop         | Result   |
| --------------------- | -------- |
| < 3 percentage points | PASS     |
| 3–8 percentage points | WARNING  |
| > 8 percentage points | CRITICAL |

Critical regressions cause the CI check to fail, allowing protected branches to prevent the change from being merged.

## Example

```text
Baseline (v1):   95% accuracy
Candidate (v2):  90% accuracy
Change:          -5 percentage points
Status:          REGRESSION
Severity:        WARNING
```

The pipeline also identifies the specific cases responsible for the regression.

```text
006: technical → general (regression)
```

## Evaluation Report

The pipeline generates an HTML evaluation report containing:

* Baseline vs candidate accuracy
* Accuracy change and regression severity
* Individual regression cases
* Prompt differences
* Evaluation history
* Performance drift status

Example:

```text
REGRESSION DETECTED

Baseline: 95.0%
Current:  90.0%
Change:   -5.0%

Severity: WARNING
Manual Review Required
```

## CI/CD

GitHub Actions automatically runs the regression evaluation and automated tests during pull requests.

```text
Pull Request
     ↓
Run Evaluation
     ↓
Compare Results
     ↓
Regression Check
     ↓
Run Tests
     ↓
Pass or Block
```

## Project Structure

```text
LLM-regression-detection-evaluation-pipeline/
│
├── .github/
│   └── workflows/
│       └── eval-on-pr.yml
│
├── prompts/
│   ├── v1.yaml
│   └── v2.yaml
│
├── data/
│   ├── golden/
│   │   └── golden_dataset.json
│   └── results/
│
├── src/
│   ├── llm/
│   │   └── classifier.py
│   ├── models/
│   │   └── schema.py
│   ├── evaluation/
│   │   ├── runner.py
│   │   ├── scorer.py
│   │   ├── diff.py
│   │   └── ci_check.py
│   ├── reporting/
│   │   └── html_report.py
│   └── alerting/
│       ├── slack.py
│       └── drift.py
│
├── tests/
│   └── test_diff_engine.py
│
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt
└── README.md
```

## Run Locally

```bash
pip install -r requirements.txt
python -m src.evaluation.ci_check
python -m pytest
```
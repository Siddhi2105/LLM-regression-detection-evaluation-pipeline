````markdown
# LLM Regression Detection & Evaluation Pipeline

An automated CI/CD pipeline that tests LLM prompt changes against a golden dataset and detects quality regressions before deployment.

## What it does

- Evaluates LLM outputs on a fixed golden dataset
- Measures accuracy and error rate
- Compares prompt versions against a baseline
- Identifies individual regression cases
- Classifies results as PASS, WARNING, or CRITICAL
- Runs automatically through GitHub Actions
- Generates HTML evaluation reports
- Detects performance drift across multiple evaluation runs

## Tech Stack

Python · OpenAI API · Pydantic · PyYAML · Pytest · GitHub Actions · Docker · Slack

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
│   │
│   ├── models/
│   │   └── schema.py
│   │
│   ├── evaluation/
│   │   ├── runner.py
│   │   ├── scorer.py
│   │   ├── diff.py
│   │   └── ci_check.py
│   │
│   ├── reporting/
│   │   └── html_report.py
│   │
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
````

## Example

```text
Baseline (v1):   95% accuracy
Candidate (v2):  90% accuracy
Change:          -5%
Result:          REGRESSION — WARNING
```

## Key Idea

Treat LLM prompt changes like software changes: evaluate, compare, and catch regressions before they reach production.

## Run

```bash
pip install -r requirements.txt
python -m src.evaluation.ci_check
python -m pytest
```

```



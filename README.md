LLM Regression Detection & Evaluation Pipeline

An automated CI/CD pipeline that tests LLM prompt changes against a golden dataset and detects quality regressions before deployment.

What it does

- Evaluates LLM outputs on a fixed golden dataset
- Measures accuracy and error rate
- Compares prompt versions against a baseline
- Identifies individual regression cases
- Classifies results as PASS, WARNING, or CRITICAL
- Runs automatically through GitHub Actions
- Generates HTML evaluation reports
- Includes multi-run drift detection

Tech Stack

Python · OpenAI API · Pydantic · PyYAML · Pytest · GitHub Actions · Docker · Slack

Project Structure

LLM-regression-detection-evaluation-pipeline/
├── .github/workflows/
│   └── eval-on-pr.yml
├── prompts/
│   ├── v1.yaml
│   └── v2.yaml
├── data/golden/
│   └── golden_dataset.json
├── src/
│   ├── llm/
│   ├── evaluation/
│   ├── reporting/
│   └── alerting/
├── tests/
│   └── test_diff_engine.py
├── Dockerfile
├── requirements.txt
└── README.md

Example

Baseline (v1):   95% accuracy
Candidate (v2):  90% accuracy
Change:          -5%
Result:          REGRESSION — WARNING

Key Idea

Treat LLM prompt changes like software changes: evaluate, compare, and catch regressions before they reach production.

Run

pip install -r requirements.txt
python -m src.evaluation.ci_check
python -m pytest
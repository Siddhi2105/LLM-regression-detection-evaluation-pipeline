import json
import os
import difflib
import html

from src.evaluation.diff import compare_runs
from src.alerting.drift import load_accuracies, detect_drift


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_prompt(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def classify_case(old_case, new_case):
    """
    Determine the status of a test case.

    pass:
        New prediction is correct.

    regression:
        Old prediction was correct,
        new prediction is incorrect.

    fixed:
        Old prediction was incorrect,
        new prediction is correct.

    changed:
        Prediction changed, but there was no
        correct/incorrect transition.

    fail:
        New prediction is incorrect and
        prediction did not change.
    """

    expected = old_case["expected_category"]

    old_prediction = old_case["predicted_category"]
    new_prediction = new_case["predicted_category"]

    old_correct = old_prediction == expected
    new_correct = new_prediction == expected

    if old_correct and new_correct:
        return "pass"

    if old_correct and not new_correct:
        return "regression"

    if not old_correct and new_correct:
        return "fixed"

    if old_prediction != new_prediction:
        return "changed"

    return "fail"


def build_all_cases(old_run, new_run):

    old_cases = {
        case["id"]: case
        for case in old_run["results"]
    }

    new_cases = {
        case["id"]: case
        for case in new_run["results"]
    }

    cases = []

    for case_id in old_cases:

        if case_id not in new_cases:
            continue

        old_case = old_cases[case_id]
        new_case = new_cases[case_id]

        status = classify_case(
            old_case,
            new_case
        )

        cases.append({
            "id": case_id,
            "email": old_case["email"],
            "expected_category":
                old_case["expected_category"],
            "expected_summary":
                old_case["expected_summary"],
            "old_prediction":
                old_case["predicted_category"],
            "new_prediction":
                new_case["predicted_category"],
            "old_summary":
                old_case["predicted_summary"],
            "new_summary":
                new_case["predicted_summary"],
            "status": status
        })

    return cases


def create_prompt_diff(old_prompt, new_prompt):

    old_lines = old_prompt.splitlines()
    new_lines = new_prompt.splitlines()

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="v1.yaml",
        tofile="v2.yaml",
        lineterm=""
    )

    output = ""

    for line in diff:

        escaped = html.escape(line)

        if line.startswith("+") and not line.startswith("+++"):
            output += (
                f'<div class="diff-added">{escaped}</div>'
            )

        elif line.startswith("-") and not line.startswith("---"):
            output += (
                f'<div class="diff-removed">{escaped}</div>'
            )

        elif line.startswith("@@"):
            output += (
                f'<div class="diff-location">{escaped}</div>'
            )

        else:
            output += (
                f'<div class="diff-normal">{escaped}</div>'
            )

    if not output:
        output = """
        <div class="diff-normal">
            No prompt differences detected.
        </div>
        """

    return output


# ============================================================
# REPORT GENERATOR
# ============================================================

def generate_html_report(
    comparison,
    old_run,
    new_run,
    old_prompt,
    new_prompt,
    output_path
):

    cases = build_all_cases(
        old_run,
        new_run
    )

    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    total_cases = len(cases)

    pass_count = sum(
        1 for case in cases
        if case["status"] in ["pass", "fixed"]
    )

    failure_count = total_cases - pass_count

    regression_count = sum(
        1 for case in cases
        if case["status"] == "regression"
    )

    fixed_count = sum(
        1 for case in cases
        if case["status"] == "fixed"
    )

    other_changes = sum(
        1 for case in cases
        if case["status"] == "changed"
    )

    fail_count = sum(
        1 for case in cases
        if case["status"] == "fail"
    )

    # --------------------------------------------------------
    # ACCURACY
    # --------------------------------------------------------

    old_accuracy = comparison["old_accuracy"]
    new_accuracy = comparison["new_accuracy"]

    accuracy_change = comparison["accuracy_change"]

    old_error = 1 - old_accuracy
    new_error = 1 - new_accuracy
    # --------------------------------------------------------
    # DRIFT DETECTION
    # --------------------------------------------------------

    drift_results = load_accuracies()

    drift = detect_drift(drift_results)

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    system_status = comparison["status"]
    severity = comparison["severity"]

    if system_status == "regression":

        status_text = "REGRESSION DETECTED"
        status_class = "warning"
        status_icon = "⚠"

    elif system_status == "improvement":

        status_text = "IMPROVEMENT DETECTED"
        status_class = "success"
        status_icon = "✓"

    else:

        status_text = "NO REGRESSION DETECTED"
        status_class = "success"
        status_icon = "✓"

    # --------------------------------------------------------
    # CATEGORY REGRESSIONS
    # --------------------------------------------------------

    categories = {
        "billing": 0,
        "technical": 0,
        "account": 0,
        "general": 0
    }

    for case in cases:

        if case["status"] == "regression":

            category = case["expected_category"]

            if category in categories:
                categories[category] += 1

    max_category = max(
        categories.values()
    ) if categories else 1

    # --------------------------------------------------------
    # CATEGORY CHART
    # --------------------------------------------------------

    category_chart = ""

    for category, count in categories.items():

        if max_category == 0:
            width = 0
        else:
            width = (count / max_category) * 100

        category_chart += f"""
        <div class="category-row">

            <div class="category-name">
                {category.title()}
            </div>

            <div class="category-bar-bg">

                <div
                    class="category-bar"
                    style="width:{width}%"
                ></div>

            </div>

            <div class="category-count">
                {count}
            </div>

        </div>
        """

    # --------------------------------------------------------
    # CASE TABLE
    # --------------------------------------------------------

    table_rows = ""

    for case in cases:

        status = case["status"]

        if status == "pass":

            badge_class = "pass"
            badge_text = "PASS"

        elif status == "regression":

            badge_class = "regression"
            badge_text = "REGRESSION"

        elif status == "fixed":

            badge_class = "fixed"
            badge_text = "FIXED"

        elif status == "changed":

            badge_class = "changed"
            badge_text = "CHANGED"

        else:

            badge_class = "fail"
            badge_text = "FAIL"

        old_prediction = case["old_prediction"]
        new_prediction = case["new_prediction"]

        old_class = (
            "correct"
            if old_prediction == case["expected_category"]
            else "incorrect"
        )

        new_class = (
            "correct"
            if new_prediction == case["expected_category"]
            else "incorrect"
        )

        safe_email = html.escape(
            case["email"]
        )

        safe_expected_summary = html.escape(
            case["expected_summary"]
        )

        safe_old_summary = html.escape(
            case["old_summary"]
        )

        safe_new_summary = html.escape(
            case["new_summary"]
        )

        table_rows += f"""
        <tr
            class="case-row"
            data-case-id="{case["id"]}"
            data-status="{status}"
            onclick="toggleCase('{case["id"]}')"
        >

            <td>
                <strong>{case["id"]}</strong>
            </td>

            <td>
                <span class="category-tag">
                    {case["expected_category"]}
                </span>
            </td>

            <td>
                <span class="prediction {old_class}">
                    {old_prediction}
                </span>
            </td>

            <td>
                <span class="arrow">→</span>

                <span class="prediction {new_class}">
                    {new_prediction}
                </span>
            </td>

            <td>
                <span class="status-badge {badge_class}">
                    {badge_text}
                </span>
            </td>

        </tr>

        <tr
            id="details-{case["id"]}"
            class="case-details"
        >

            <td colspan="5">

                <div class="details-box">

                    <div class="details-grid">

                        <div>
                            <div class="detail-label">
                                CUSTOMER EMAIL
                            </div>

                            <div class="detail-value">
                                {safe_email}
                            </div>
                        </div>

                        <div>
                            <div class="detail-label">
                                EXPECTED CATEGORY
                            </div>

                            <div class="detail-value">
                                {case["expected_category"]}
                            </div>
                        </div>

                        <div>
                            <div class="detail-label">
                                EXPECTED SUMMARY
                            </div>

                            <div class="detail-value">
                                {safe_expected_summary}
                            </div>
                        </div>

                        <div>
                            <div class="detail-label">
                                {comparison["old_version"]} SUMMARY
                            </div>

                            <div class="detail-value">
                                {safe_old_summary}
                            </div>
                        </div>

                        <div>
                            <div class="detail-label">
                                {comparison["new_version"]} SUMMARY
                            </div>

                            <div class="detail-value">
                                {safe_new_summary}
                            </div>
                        </div>

                    </div>

                </div>

            </td>

        </tr>
        """

    # --------------------------------------------------------
    # PROMPT DIFF
    # --------------------------------------------------------

    prompt_diff = create_prompt_diff(
        old_prompt,
        new_prompt
    )

    # --------------------------------------------------------
    # RELEASE GATE
    # --------------------------------------------------------

    if severity == "critical":

        gate_class = "gate-critical"
        gate_icon = "✕"
        gate_title = "RELEASE BLOCKED"

        gate_message = (
            "Critical regression detected. "
            "The current release should not proceed."
        )

    elif severity == "warning":

        gate_class = "gate-warning"
        gate_icon = "⚠"
        gate_title = "MANUAL REVIEW REQUIRED"

        gate_message = (
            "Performance decreased beyond the warning "
            "threshold. Review the changed cases before release."
        )

    else:

        gate_class = "gate-pass"
        gate_icon = "✓"
        gate_title = "RELEASE PASSED"

        gate_message = (
            "No significant regression was detected."
        )

    # --------------------------------------------------------
    # INSIGHT
    # --------------------------------------------------------

    if accuracy_change < 0:

        insight = f"""
        The new prompt version
        <strong>{comparison["new_version"]}</strong>
        reduced classification accuracy from
        <strong>{old_accuracy:.0%}</strong>
        to
        <strong>{new_accuracy:.0%}</strong>.
        This is a
        <strong>
            {abs(accuracy_change):.0%} percentage-point decrease
        </strong>
        from the baseline.
        """

    elif accuracy_change > 0:

        insight = f"""
        The new prompt version
        <strong>{comparison["new_version"]}</strong>
        improved classification accuracy from
        <strong>{old_accuracy:.0%}</strong>
        to
        <strong>{new_accuracy:.0%}</strong>.
        This is a
        <strong>
            {accuracy_change:.0%} percentage-point improvement
        </strong>
        from the baseline.
        """

    else:

        insight = """
        The new prompt version produced the same
        classification accuracy as the baseline.
        """

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    html_report = f"""
<!DOCTYPE html>

<html lang="en">

<head>

<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>
    LLM Regression Detection System
</title>

<style>

* {{
    box-sizing: border-box;
}}

html {{
    scroll-behavior: smooth;
}}

body {{

    margin: 0;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background: #edf1f4;

    color: #1f2933;

}}


/* ============================================================
   TOP NAVIGATION
   ============================================================ */

.topbar {{

    position: sticky;

    top: 0;

    z-index: 1000;

    min-height: 60px;

    background:
        linear-gradient(
            90deg,
            #172536,
            #24384d
        );

    color: white;

    display: flex;

    align-items: center;

    justify-content: space-between;

    padding: 0 22px;

    box-shadow:
        0 3px 12px rgba(0,0,0,0.16);

}}

.logo-area {{

    display: flex;

    align-items: center;

    gap: 11px;

}}

.logo {{

    width: 36px;
    height: 36px;

    border: 1px solid #5791c4;

    border-radius: 8px;

    display: flex;

    align-items: center;

    justify-content: center;

    color: #8fc1ec;

    font-size: 18px;

}}

.title {{

    font-size: 17px;

    font-weight: 700;

}}

.title span {{

    color: #9eacb9;

    font-weight: 400;

}}

.nav {{

    height: 60px;

    display: flex;

    align-items: center;

    gap: 4px;

}}

.nav-button {{

    height: 100%;

    border: none;

    background: transparent;

    color: #b8c5d1;

    padding: 0 14px;

    cursor: pointer;

    border-bottom: 3px solid transparent;

    transition:
        color 160ms ease,
        background 160ms ease,
        border-color 160ms ease;

}}

.nav-button:hover {{

    color: white;

    background: rgba(255,255,255,0.05);

}}

.nav-button.active {{

    color: #69a9dd;

    border-bottom-color: #4285c5;

}}


/* ============================================================
   MAIN
   ============================================================ */

.dashboard {{

    max-width: 1500px;

    margin: auto;

    padding: 14px;

}}


/* ============================================================
   PAGES
   ============================================================ */

.page {{

    display: none;

}}

.page.active {{

    display: block;

    animation:
        pageFadeIn
        220ms
        ease
        both;

}}

@keyframes pageFadeIn {{

    from {{
        opacity: 0;
        transform: translateY(5px);
    }}

    to {{
        opacity: 1;
        transform: translateY(0);
    }}

}}


/* ============================================================
   STATUS PANEL
   ============================================================ */

.status-panel {{

    background:
        linear-gradient(
            90deg,
            #243444,
            #2d4053
        );

    color: white;

    border-radius: 7px;

    overflow: hidden;

    box-shadow:
        0 3px 10px rgba(0,0,0,0.15);

    margin-bottom: 12px;

}}

.status-title {{

    padding: 10px 15px;

    border-bottom: 1px solid #455666;

    font-size: 15px;

    font-weight: 700;

}}

.status-highlight {{

    color: #e8bd65;

    font-weight: 400;

}}

.timestamp {{

    float: right;

    color: #c3ccd5;

    font-size: 11px;

    font-weight: 400;

}}

.metrics {{

    display: grid;

    grid-template-columns:
        repeat(5, 1fr);

}}

.metric {{

    text-align: center;

    padding: 12px 5px 15px;

}}

.metric-label {{

    font-size: 10px;

    text-transform: uppercase;

    color: #e3e8ed;

}}

.metric-value {{

    font-size: 28px;

    font-weight: 300;

    margin-top: 3px;

    transition: transform 180ms ease;

}}

.metric:hover .metric-value {{

    transform: translateY(-2px);

}}

.metric-change {{

    color: #e16a6a;

    font-size: 18px;

}}


/* ============================================================
   RELEASE GATE
   ============================================================ */

.release-gate {{

    padding: 18px;

    border-radius: 7px;

    margin-bottom: 12px;

    border: 1px solid;

    transition:
        box-shadow 180ms ease,
        transform 180ms ease;

}}

.release-gate:hover {{

    transform: translateY(-1px);

    box-shadow:
        0 4px 12px rgba(0,0,0,0.08);

}}

.gate-warning {{

    background: #fff7e7;

    border-color: #e7c778;

}}

.gate-critical {{

    background: #fff0ef;

    border-color: #e0aaa6;

}}

.gate-pass {{

    background: #edf8f0;

    border-color: #afd2b8;

}}

.gate-icon {{

    font-size: 28px;

    font-weight: 700;

    float: left;

    margin-right: 13px;

}}

.gate-title {{

    font-size: 16px;

    font-weight: 800;

}}

.gate-message {{

    margin-top: 4px;

    color: #58636c;

    font-size: 12px;

}}


/* ============================================================
   GRID
   ============================================================ */

.content-grid {{

    display: grid;

    grid-template-columns:
        minmax(0, 3fr)
        minmax(300px, 1fr);

    gap: 12px;

}}


/* ============================================================
   CARDS
   ============================================================ */

.card {{

    background: white;

    border: 1px solid #d3d8dc;

    border-radius: 7px;

    overflow: hidden;

    box-shadow:
        0 2px 5px rgba(0,0,0,0.07);

    margin-bottom: 12px;

    transition:
        box-shadow 180ms ease,
        transform 180ms ease;

}}

.card:hover {{

    box-shadow:
        0 5px 14px rgba(0,0,0,0.09);

}}

.card-header {{

    min-height: 40px;

    padding: 11px 14px;

    background:
        linear-gradient(
            #ffffff,
            #f2f4f5
        );

    border-bottom: 1px solid #d5dadd;

    font-size: 13px;

    font-weight: 700;

    text-transform: uppercase;

}}

.card-body {{

    padding: 15px;

}}


/* ============================================================
   FILTERS
   ============================================================ */

.filters {{

    float: right;

    display: flex;

    gap: 5px;

}}

.filter {{

    border: 1px solid #c7cfd5;

    background: #edf0f2;

    border-radius: 5px;

    padding: 5px 10px;

    font-size: 10px;

    font-weight: 700;

    cursor: pointer;

    transition:
        background 160ms ease,
        color 160ms ease,
        border-color 160ms ease,
        transform 160ms ease;

}}

.filter:hover {{

    background: #dfe6eb;

    transform: translateY(-1px);

}}

.filter.active {{

    background: #397eaf;

    color: white;

    border-color: #397eaf;

}}

.case-hidden {{

    display: none !important;

}}


/* ============================================================
   SEARCH
   ============================================================ */

.search-box {{

    margin: 12px;

}}

.search-box input {{

    width: 100%;

    padding: 10px 11px;

    border: 1px solid #cdd4d9;

    border-radius: 5px;

    outline: none;

    font-size: 12px;

    transition:
        border-color 160ms ease,
        box-shadow 160ms ease;

}}

.search-box input:focus {{

    border-color: #4d8bb9;

    box-shadow:
        0 0 0 3px rgba(77,139,185,0.10);

}}


/* ============================================================
   TABLE
   ============================================================ */

.table-container {{

    overflow-x: auto;

}}

table {{

    width: 100%;

    border-collapse: collapse;

    font-size: 12px;

}}

thead th {{

    background: #e9edef;

    color: #182028;

    text-align: left;

    padding: 10px;

    border-bottom: 1px solid #ccd3d8;

}}

tbody td {{

    padding: 10px;

    border-bottom: 1px solid #e1e5e8;

}}

.case-row {{

    cursor: pointer;

    transition:
        background 150ms ease;

}}

.case-row:hover {{

    background: #f5f8fa;

}}

.case-details {{

    display: none;

}}

.case-details.open {{

    display: table-row;

    animation:
        detailsOpen
        180ms
        ease
        both;

}}

@keyframes detailsOpen {{

    from {{
        opacity: 0;
    }}

    to {{
        opacity: 1;
    }}

}}

.details-box {{

    background: #f6f8fa;

    border-left: 3px solid #4c83ad;

    padding: 16px;

}}

.details-grid {{

    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 15px;

}}

.detail-label {{

    font-size: 9px;

    color: #7b8790;

    font-weight: 700;

    letter-spacing: 0.7px;

    margin-bottom: 4px;

}}

.detail-value {{

    font-size: 12px;

    color: #27333d;

}}

.category-tag {{

    display: inline-block;

    padding: 3px 7px;

    background: #edf2f6;

    border-radius: 4px;

    font-size: 10px;

    font-weight: 700;

}}

.prediction {{

    font-weight: 700;

}}

.prediction.correct {{

    color: #287443;

}}

.prediction.incorrect {{

    color: #b53c37;

}}

.arrow {{

    color: #87939d;

    margin: 0 5px;

}}

.status-badge {{

    display: inline-block;

    padding: 4px 8px;

    border-radius: 5px;

    font-size: 9px;

    font-weight: 700;

}}

.status-badge.pass {{

    background: #dcefe1;

    color: #27713b;

}}

.status-badge.regression {{

    background: #f5d3cf;

    color: #963831;

}}

.status-badge.fixed {{

    background: #dcefe1;

    color: #27713b;

}}

.status-badge.changed {{

    background: #f8e8c7;

    color: #95681e;

}}

.status-badge.fail {{

    background: #f5d3cf;

    color: #963831;

}}


/* ============================================================
   CHARTS
   ============================================================ */

.chart {{

    padding: 15px;

}}

.category-row {{

    display: grid;

    grid-template-columns:
        80px 1fr 25px;

    align-items: center;

    gap: 8px;

    margin-bottom: 15px;

    font-size: 11px;

}}

.category-name {{

    text-transform: capitalize;

}}

.category-bar-bg {{

    height: 20px;

    background: #edf0f2;

    border-radius: 3px;

    overflow: hidden;

}}

.category-bar {{

    height: 100%;

    background: #4b82ae;

    border-radius: 3px;

    transition:
        width 400ms ease;

}}

.category-count {{

    text-align: right;

    font-weight: 700;

}}


/* ============================================================
   ACCURACY
   ============================================================ */

.accuracy-chart {{

    height: 190px;

    display: flex;

    align-items: flex-end;

    justify-content: center;

    gap: 55px;

    border-bottom: 1px solid #cbd2d7;

}}

.accuracy-column {{

    width: 70px;

    text-align: center;

}}

.accuracy-bar-container {{

    height: 145px;

    display: flex;

    align-items: flex-end;

    justify-content: center;

}}

.accuracy-bar {{

    width: 45px;

    background: #4d84ad;

    border-radius: 3px 3px 0 0;

    transition:
        height 500ms ease;

}}

.accuracy-bar.old {{

    height: {old_accuracy * 145}px;

}}

.accuracy-bar.new {{

    height: {new_accuracy * 145}px;

}}

.accuracy-number {{

    font-weight: 700;

    font-size: 13px;

    margin-top: 7px;

}}

.accuracy-label {{

    font-size: 10px;

    color: #6d7982;

}}


/* ============================================================
   INSIGHTS
   ============================================================ */

.insight-list {{

    margin: 0;

    padding-left: 20px;

}}

.insight-list li {{

    margin-bottom: 8px;

    font-size: 12px;

}}

.action-title {{

    margin-top: 18px;

    margin-bottom: 8px;

    font-size: 12px;

    font-weight: 700;

    text-transform: uppercase;

}}

.action-list {{

    display: flex;

    flex-direction: column;

    gap: 7px;

}}

.action-list label {{

    font-size: 12px;

    display: flex;

    gap: 7px;

    align-items: center;

}}


/* ============================================================
   METADATA
   ============================================================ */

.metadata-grid {{

    display: grid;

    grid-template-columns:
        repeat(4, 1fr);

    gap: 10px;

}}

.metadata-item {{

    background: #f4f6f7;

    border: 1px solid #dfe4e7;

    border-radius: 5px;

    padding: 12px;

}}

.metadata-label {{

    font-size: 9px;

    color: #7b8790;

    text-transform: uppercase;

}}

.metadata-value {{

    font-size: 13px;

    font-weight: 700;

    margin-top: 3px;

}}


/* ============================================================
   PROJECTS / HISTORY / SETTINGS
   ============================================================ */

.info-grid {{

    display: grid;

    grid-template-columns:
        repeat(2, 1fr);

    gap: 15px;

}}

.info-box {{

    background: #f5f7f8;

    border: 1px solid #dfe4e7;

    padding: 18px;

    border-radius: 6px;

}}

.info-box h3 {{

    margin: 0 0 7px;

    font-size: 14px;

}}

.info-box p {{

    margin: 0;

    font-size: 12px;

    color: #65717a;

}}

.history-row {{

    display: grid;

    grid-template-columns:
        100px 120px 120px 1fr;

    padding: 13px;

    border-bottom: 1px solid #e0e4e7;

    font-size: 12px;

    align-items: center;

}}

.history-header {{

    font-weight: 700;

    background: #edf0f2;

}}

.setting-row {{

    display: flex;

    justify-content: space-between;

    padding: 14px 0;

    border-bottom: 1px solid #e4e7e9;

    font-size: 13px;

}}

.setting-value {{

    font-weight: 700;

}}


/* ============================================================
   PROMPT DIFF
   ============================================================ */

.diff-viewer {{

    background: #17212b;

    color: #d8e0e7;

    border-radius: 6px;

    overflow: auto;

    padding: 15px;

    font-family:
        Consolas,
        "Courier New",
        monospace;

    font-size: 11px;

    line-height: 1.7;

    max-height: 500px;

}}

.diff-added {{

    background: rgba(50,150,80,0.18);

    color: #9be0ae;

}}

.diff-removed {{

    background: rgba(190,60,60,0.18);

    color: #f09b9b;

}}

.diff-location {{

    color: #82b9e8;

}}

.diff-normal {{

    color: #aeb8c1;

}}


/* ============================================================
   FOOTER
   ============================================================ */

.footer {{

    text-align: center;

    color: #7b8790;

    font-size: 10px;

    padding: 18px;

}}


/* ============================================================
   RESPONSIVE
   ============================================================ */

@media (max-width: 950px) {{

    .content-grid {{
        grid-template-columns: 1fr;
    }}

    .metrics {{
        grid-template-columns:
            repeat(3, 1fr);
    }}

    .metadata-grid {{
        grid-template-columns:
            repeat(2, 1fr);
    }}

}}

@media (max-width: 650px) {{

    .topbar {{
        flex-direction: column;
        height: auto;
        padding: 10px;
    }}

    .nav {{
        width: 100%;
        height: 45px;
        justify-content: center;
    }}

    .nav-button {{
        height: 45px;
        padding: 0 8px;
        font-size: 11px;
    }}

    .metrics {{
        grid-template-columns:
            repeat(2, 1fr);
    }}

    .details-grid,
    .info-grid {{
        grid-template-columns: 1fr;
    }}

    .metadata-grid {{
        grid-template-columns: 1fr;
    }}

    .title span {{
        display: none;
    }}

    .filters {{
        float: none;
        margin-top: 10px;
        flex-wrap: wrap;
    }}

}}


</style>

</head>


<body>


<!-- ==========================================================
     TOP NAVIGATION
     ========================================================== -->

<div class="topbar">

    <div class="logo-area">

        <div class="logo">
            ◉
        </div>

        <div class="title">

            LLM REGRESSION DETECTION SYSTEM

            <span>
                · Automated Evaluation Platform
            </span>

        </div>

    </div>


    <div class="nav">

        <button
            class="nav-button active"
            onclick="showPage('dashboard', this)"
        >
            ▦ Dashboard
        </button>

        <button
            class="nav-button"
            onclick="showPage('projects', this)"
        >
            □ Projects
        </button>

        <button
            class="nav-button"
            onclick="showPage('history', this)"
        >
            ◷ History
        </button>

        <button
            class="nav-button"
            onclick="showPage('settings', this)"
        >
            ⚙ Settings
        </button>

    </div>

</div>


<div class="dashboard">


<!-- ==========================================================
     DASHBOARD
     ========================================================== -->

<div
    id="dashboard"
    class="page active"
>


    <!-- STATUS -->

    <div class="status-panel">

        <div class="status-title">

            REGRESSION STATUS:

            <span class="status-highlight">
                {status_text}
            </span>

            <span class="timestamp">
                Evaluation Run: 2026-09-05
            </span>

        </div>


        <div class="metrics">


            <div class="metric">

                <div class="metric-label">
                    Total Test Cases
                </div>

                <div class="metric-value">
                    {total_cases}
                </div>

            </div>


            <div class="metric">

                <div class="metric-label">
                    Pass Rate
                </div>

                <div class="metric-value">

                    {new_accuracy:.1%}

                    <span class="metric-change">
                        ({accuracy_change:+.1%})
                    </span>

                </div>

            </div>


            <div class="metric">

                <div class="metric-label">
                    Regressions
                </div>

                <div class="metric-value">
                    {regression_count}
                </div>

            </div>


            <div class="metric">

                <div class="metric-label">
                    Error Rate
                </div>

                <div class="metric-value">
                    {new_error:.1%}
                </div>

            </div>


            <div class="metric">

                <div class="metric-label">
                    Severity
                </div>

                <div class="metric-value">
                    {severity.upper()}
                </div>

            </div>

        </div>

    </div>


    <!-- RELEASE GATE -->

    <div class="release-gate {gate_class}">

        <div class="gate-icon">
            {gate_icon}
        </div>

        <div>

            <div class="gate-title">
                {gate_title}
            </div>

            <div class="gate-message">
                {gate_message}
            </div>

        </div>

        <div style="clear:both;"></div>

    </div>


    <!-- MAIN GRID -->

    <div class="content-grid">


        <!-- LEFT -->

        <div>


            <!-- CASE ANALYSIS -->

            <div class="card">

                <div class="card-header">

                    Case-Level Analysis

                    <div class="filters">

                        <button
                            class="filter active"
                            onclick="filterCases('all', this)"
                        >
                            ALL
                        </button>

                        <button
                            class="filter"
                            onclick="filterCases('pass', this)"
                        >
                            PASS
                        </button>

                        <button
                            class="filter"
                            onclick="filterCases('fail', this)"
                        >
                            FAIL
                        </button>

                        <button
                            class="filter"
                            onclick="filterCases('regression', this)"
                        >
                            REGRESSION
                        </button>

                    </div>

                </div>


                <div class="search-box">

                    <input
                        type="text"
                        id="caseSearch"
                        placeholder="Search test case, category, or email..."
                        oninput="searchCases()"
                    >

                </div>


                <div class="table-container">

                    <table>

                        <thead>

                            <tr>

                                <th>
                                    TEST CASE
                                </th>

                                <th>
                                    EXPECTED
                                </th>

                                <th>
                                    {comparison["old_version"]}
                                </th>

                                <th>
                                    {comparison["new_version"]}
                                </th>

                                <th>
                                    STATUS
                                </th>

                            </tr>

                        </thead>


                        <tbody>

                            {table_rows}

                        </tbody>

                    </table>

                </div>

            </div>


            <!-- INSIGHTS -->

            <div class="card">

                <div class="card-header">
                    Analysis & Insights
                </div>

                <div class="card-body">

                    <ul class="insight-list">

                        <li>
                            {insight}
                        </li>

                        <li>
                            <strong>
                                {regression_count}
                            </strong>
                            regression case(s) detected.
                        </li>

                        <li>
                            <strong>
                                {fixed_count}
                            </strong>
                            case(s) improved and

                            <strong>
                                {other_changes}
                            </strong>

                            case(s) changed without a
                            correct/incorrect transition.
                        </li>

                        <li>
                            Current classification error rate:

                            <strong>
                                {new_error:.1%}
                            </strong>

                        </li>

                    </ul>


                    <div class="action-title">
                        Actions Required
                    </div>


                    <div class="action-list">

                        <label>
                            <input type="checkbox">
                            Investigate regression cases
                        </label>

                        <label>
                            <input type="checkbox">
                            Review prompt differences
                        </label>

                        <label>
                            <input type="checkbox">
                            Re-run evaluation after changes
                        </label>

                    </div>

                </div>

            </div>


            <!-- PROMPT DIFF -->

            <div class="card">

                <div class="card-header">
                    Prompt Change Analysis
                </div>

                <div class="card-body">

                    <p
                        style="
                            font-size:12px;
                            color:#65717a;
                            margin-top:0;
                        "
                    >
                        Changes detected between the baseline and
                        current prompt configuration.
                    </p>


                    <div class="diff-viewer">

                        {prompt_diff}

                    </div>

                </div>

            </div>


            <!-- EVALUATION DETAILS -->

            <div class="card">

                <div class="card-header">
                    Evaluation Details
                </div>

                <div class="card-body">

                    <div class="metadata-grid">

                        <div class="metadata-item">

                            <div class="metadata-label">
                                Baseline
                            </div>

                            <div class="metadata-value">
                                {comparison["old_version"]}
                            </div>

                        </div>


                        <div class="metadata-item">

                            <div class="metadata-label">
                                Current
                            </div>

                            <div class="metadata-value">
                                {comparison["new_version"]}
                            </div>

                        </div>


                        <div class="metadata-item">

                            <div class="metadata-label">
                                Baseline Accuracy
                            </div>

                            <div class="metadata-value">
                                {old_accuracy:.1%}
                            </div>

                        </div>


                        <div class="metadata-item">

                            <div class="metadata-label">
                                Current Accuracy
                            </div>

                            <div class="metadata-value">
                                {new_accuracy:.1%}
                            </div>

                        </div>

                    </div>

                </div>

            </div>


        </div>


        <!-- RIGHT -->

        <div>


            <!-- CATEGORY -->

            <div class="card">

                <div class="card-header">
                    Regressions by Category
                </div>

                <div class="chart">

                    {category_chart}

                </div>

            </div>


            <!-- ACCURACY -->

            <div class="card">

                <div class="card-header">
                    Accuracy Comparison
                </div>

                <div class="chart">

                    <div class="accuracy-chart">


                        <div class="accuracy-column">

                            <div class="accuracy-bar-container">

                                <div class="accuracy-bar old"></div>

                            </div>

                            <div class="accuracy-number">
                                {old_accuracy:.0%}
                            </div>

                            <div class="accuracy-label">
                                {comparison["old_version"]}
                            </div>

                        </div>


                        <div class="accuracy-column">

                            <div class="accuracy-bar-container">

                                <div class="accuracy-bar new"></div>

                            </div>

                            <div class="accuracy-number">
                                {new_accuracy:.0%}
                            </div>

                            <div class="accuracy-label">
                                {comparison["new_version"]}
                            </div>

                        </div>


                    </div>

                </div>

            </div>


            <!-- REGRESSION SUMMARY -->

            <div class="card">

                <div class="card-header">
                    Regression Summary
                </div>

                <div class="chart">


                    <div class="category-row">

                        <div class="category-name">
                            Regressions
                        </div>

                        <div class="category-bar-bg">

                            <div
                                class="category-bar"
                                style="
                                    width:
                                    {
                                        (
                                            regression_count
                                            /
                                            max(total_cases, 1)
                                            * 100
                                        )
                                    }%;
                                    background:#bd4a47;
                                "
                            ></div>

                        </div>

                        <div class="category-count">
                            {regression_count}
                        </div>

                    </div>


                    <div class="category-row">

                        <div class="category-name">
                            Fixed
                        </div>

                        <div class="category-bar-bg">

                            <div
                                class="category-bar"
                                style="
                                    width:
                                    {
                                        (
                                            fixed_count
                                            /
                                            max(total_cases, 1)
                                            * 100
                                        )
                                    }%;
                                    background:#5b996b;
                                "
                            ></div>

                        </div>

                        <div class="category-count">
                            {fixed_count}
                        </div>

                    </div>


                    <div class="category-row">

                        <div class="category-name">
                            Other
                        </div>

                        <div class="category-bar-bg">

                            <div
                                class="category-bar"
                                style="
                                    width:
                                    {
                                        (
                                            other_changes
                                            /
                                            max(total_cases, 1)
                                            * 100
                                        )
                                    }%;
                                    background:#d09a43;
                                "
                            ></div>

                        </div>

                        <div class="category-count">
                            {other_changes}
                        </div>

                    </div>


                </div>

            </div>


        </div>

    </div>


</div>


<!-- ==========================================================
     PROJECTS
     ========================================================== -->

<div
    id="projects"
    class="page"
>

    <div class="card">

        <div class="card-header">
            Project Overview
        </div>

        <div class="card-body">

            <div class="info-grid">


                <div class="info-box">

                    <h3>
                        LLM Regression Detection System
                    </h3>

                    <p>
                        An automated evaluation pipeline that
                        compares LLM-powered features against a
                        human-verified golden dataset and detects
                        quality regressions between releases.
                    </p>

                </div>


                <div class="info-box">

                    <h3>
                        Current Evaluation
                    </h3>

                    <p>
                        Comparing
                        <strong>
                            {comparison["old_version"]}
                        </strong>

                        against

                        <strong>
                            {comparison["new_version"]}
                        </strong>

                        across

                        <strong>
                            {total_cases}
                        </strong>

                        test cases.
                    </p>

                </div>


                <div class="info-box">

                    <h3>
                        Evaluation Target
                    </h3>

                    <p>
                        Customer-support email classification
                        across billing, technical, account,
                        and general categories.
                    </p>

                </div>


                <div class="info-box">

                    <h3>
                        Golden Dataset
                    </h3>

                    <p>
                        Human-verified evaluation examples used
                        as the stable baseline for regression
                        testing.
                    </p>

                </div>


            </div>

        </div>

    </div>


    <div class="card">

        <div class="card-header">
            Pipeline
        </div>

        <div class="card-body">

            <div
                style="
                    font-family:monospace;
                    background:#17212b;
                    color:#d8e0e7;
                    padding:20px;
                    border-radius:6px;
                    font-size:12px;
                    line-height:2;
                    overflow-x:auto;
                "
            >

                Prompt Version
                →
                LLM Classifier
                →
                Golden Dataset
                →
                Evaluation
                →
                Diff Engine
                →
                Release Gate

            </div>

        </div>

    </div>

</div>


<!-- ==========================================================
     HISTORY
     ========================================================== -->

<div
    id="history"
    class="page"
>

    <div class="card">

        <div class="card-header">
            Evaluation History
        </div>


        <div class="history-row history-header">

            <div>VERSION</div>
            <div>ACCURACY</div>
            <div>ERROR RATE</div>
            <div>STATUS</div>

        </div>


        <div class="history-row">

            <div>
                {comparison["old_version"]}
            </div>

            <div>
                {old_accuracy:.1%}
            </div>

            <div>
                {old_error:.1%}
            </div>

            <div>
                BASELINE
            </div>

        </div>


        <div class="history-row">

            <div>
                {comparison["new_version"]}
            </div>

            <div>
                {new_accuracy:.1%}
            </div>

            <div>
                {new_error:.1%}
            </div>

            <div>

                <span class="status-badge {status_class}">
                    {status_text}
                </span>

            </div>

        </div>

    </div>


    <div class="card">

    <div class="card-header">
        Evaluation Trend
    </div>

    <div class="card-body">

        <div style="
            background:#f5f7f8;
            border:1px solid #dfe4e7;
            border-radius:6px;
            padding:15px;
        ">

            <div style="
                font-size:12px;
                font-weight:700;
                margin-bottom:8px;
            ">
                DRIFT STATUS
            </div>

            <div style="
                font-size:20px;
                font-weight:700;
                margin-bottom:8px;
            ">
                {
                    "DRIFT DETECTED"
                    if drift["drift_detected"]
                    else "NO DRIFT DETECTED"
                }
            </div>

            <div style="
                color:#65717a;
                font-size:12px;
            ">
                {drift["message"]}
            </div>

            <div style="
                margin-top:12px;
                color:#65717a;
                font-size:11px;
            ">
                Evaluation runs available:
                <strong>{len(drift_results)}</strong>
            </div>

            {
                f'''
                <div style="
                    margin-top:8px;
                    color:#65717a;
                    font-size:11px;
                ">
                    Accuracy change across recent runs:
                    <strong>{drift["change"]:+.1%}</strong>
                </div>
                '''
                if "change" in drift
                else ""
            }

        </div>

    </div>

</div>

</div>


<!-- ==========================================================
     SETTINGS
     ========================================================== -->

<div
    id="settings"
    class="page"
>

    <div class="card">

        <div class="card-header">
            Regression Detection Settings
        </div>

        <div class="card-body">


            <div class="setting-row">

                <span>
                    PASS threshold
                </span>

                <span class="setting-value">
                    &lt; 3 percentage-point drop
                </span>

            </div>


            <div class="setting-row">

                <span>
                    WARNING threshold
                </span>

                <span class="setting-value">
                    3–8 percentage-point drop
                </span>

            </div>


            <div class="setting-row">

                <span>
                    CRITICAL threshold
                </span>

                <span class="setting-value">
                    &gt; 8 percentage-point drop
                </span>

            </div>


            <div class="setting-row">

                <span>
                    Evaluation metric
                </span>

                <span class="setting-value">
                    Classification Accuracy
                </span>

            </div>


            <div class="setting-row">

                <span>
                    Dataset size
                </span>

                <span class="setting-value">
                    {total_cases} cases
                </span>

            </div>


            <div class="setting-row">

                <span>
                    Current release
                </span>

                <span class="setting-value">
                    {comparison["new_version"]}
                </span>

            </div>

        </div>

    </div>


    <div class="card">

        <div class="card-header">
            About the Release Gate
        </div>

        <div class="card-body">

            <p
                style="
                    font-size:12px;
                    color:#65717a;
                "
            >
                The release gate compares the new prompt version
                with the baseline. A small accuracy change passes,
                a moderate drop requires manual review, and a
                large drop blocks the release.
            </p>

        </div>

    </div>

</div>


<div class="footer">

    LLM Regression Detection System
    · Automated Evaluation & Release Quality Platform

</div>


</div>


<!-- ==========================================================
     JAVASCRIPT
     ========================================================== -->

<script>

/* ==========================================================
   PAGE NAVIGATION
   ========================================================== */

function showPage(pageId, button) {{

    const pages =
        document.querySelectorAll(".page");

    pages.forEach(function(page) {{

        page.classList.remove("active");

    }});


    const selectedPage =
        document.getElementById(pageId);

    if (selectedPage) {{

        selectedPage.classList.add("active");

    }}


    const buttons =
        document.querySelectorAll(".nav-button");

    buttons.forEach(function(btn) {{

        btn.classList.remove("active");

    }});


    if (button) {{

        button.classList.add("active");

    }}


    window.scrollTo({{

        top: 0,

        behavior: "smooth"

    }});

}}


/* ==========================================================
   CASE FILTER
   ========================================================== */

let activeCaseFilter = "all";


function caseMatchesFilter(row) {{

    const status =
        row.dataset.status;


    if (activeCaseFilter === "all") {{

        return true;

    }}


    if (activeCaseFilter === "pass") {{

        return (
            status === "pass" ||
            status === "fixed"
        );

    }}


    if (activeCaseFilter === "fail") {{

        return (
            status === "fail" ||
            status === "regression"
        );

    }}


    if (activeCaseFilter === "regression") {{

        return status === "regression";

    }}


    return true;

}}


/* ==========================================================
   APPLY FILTER + SEARCH
   ========================================================== */

function updateVisibleCases() {{

    const searchInput =
        document.getElementById("caseSearch");


    const search =
        searchInput
            ? searchInput.value
                .trim()
                .toLowerCase()
            : "";


    const rows =
        document.querySelectorAll(".case-row");


    rows.forEach(function(row) {{

        const text =
            row.innerText.toLowerCase();


        const matchesSearch =
            search === "" ||
            text.includes(search);


        const matchesFilter =
            caseMatchesFilter(row);


        const shouldShow =
            matchesSearch &&
            matchesFilter;


        row.classList.toggle(
            "case-hidden",
            !shouldShow
        );


        /*
           If the case becomes hidden,
           close its details.
        */

        if (!shouldShow) {{

            const caseId =
                row.dataset.caseId;


            const details =
                document.getElementById(
                    "details-" + caseId
                );


            if (details) {{

                details.classList.remove(
                    "open"
                );

            }}

        }}

    }});

}}


/* ==========================================================
   FILTER BUTTON
   ========================================================== */

function filterCases(filter, button) {{

    activeCaseFilter = filter;


    const buttons =
        document.querySelectorAll(".filter");


    buttons.forEach(function(btn) {{

        btn.classList.remove("active");

    }});


    if (button) {{

        button.classList.add("active");

    }}


    updateVisibleCases();

}}


/* ==========================================================
   SEARCH
   ========================================================== */

function searchCases() {{

    updateVisibleCases();

}}


/* ==========================================================
   CASE DETAILS
   ========================================================== */

function toggleCase(caseId) {{

    const details =
        document.getElementById(
            "details-" + caseId
        );


    if (!details) {{

        return;

    }}


    /*
       Close other open cases.
    */

    const openDetails =
        document.querySelectorAll(
            ".case-details.open"
        );


    openDetails.forEach(function(item) {{

        if (item !== details) {{

            item.classList.remove("open");

        }}

    }});


    details.classList.toggle("open");

}}


/* ==========================================================
   INITIALIZATION
   ========================================================== */

document.addEventListener(
    "DOMContentLoaded",
    function() {{

        updateVisibleCases();

    }}
);

</script>


</body>

</html>
"""

    # --------------------------------------------------------
    # SAVE REPORT
    # --------------------------------------------------------

    output_directory = os.path.dirname(
        output_path
    )

    if output_directory:

        os.makedirs(
            output_directory,
            exist_ok=True
        )


    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(html_report)


# ============================================================
# RUN REPORT
# ============================================================

if __name__ == "__main__":

    old_result_path = (
        "data/results/run_v1_20260906.json"
    )

    new_result_path = (
        "data/results/run_v2_20260905.json"
    )

    old_prompt_path = (
        "prompts/v1.yaml"
    )

    new_prompt_path = (
        "prompts/v2.yaml"
    )


    # --------------------------------------------------------
    # LOAD RESULTS
    # --------------------------------------------------------

    v1 = load_json(
        old_result_path
    )

    v2 = load_json(
        new_result_path
    )


    # --------------------------------------------------------
    # LOAD PROMPTS
    # --------------------------------------------------------

    v1_prompt = load_prompt(
        old_prompt_path
    )

    v2_prompt = load_prompt(
        new_prompt_path
    )


    # --------------------------------------------------------
    # COMPARE RUNS
    # --------------------------------------------------------
    print("DEBUG v1 accuracy:", v1["accuracy"])
    print("DEBUG v2 accuracy:", v2["accuracy"])
    print("DEBUG comparison:", compare_runs(v1, v2))
    comparison = compare_runs(
        v1,
        v2
    )


    # --------------------------------------------------------
    # GENERATE REPORT
    # --------------------------------------------------------

    generate_html_report(

        comparison=comparison,

        old_run=v1,

        new_run=v2,

        old_prompt=v1_prompt,

        new_prompt=v2_prompt,

        output_path=(
            "reports/report_v2_vs_v1.html"
        )

    )


    print(
        "Advanced HTML report generated successfully."
    )
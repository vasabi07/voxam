"""
Model Comparison and Scoring Tool

Aggregates results from all evaluation scripts and generates:
1. Side-by-side comparison table
2. Quality scores (manual input)
3. Cost analysis
4. Final recommendations

Usage:
    python evaluation/compare_models.py --generate-template
    python evaluation/compare_models.py --score
    python evaluation/compare_models.py --compare
"""

import argparse
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

RESULTS_DIR = Path(__file__).parent / "results"

# Scoring criteria weights
SCORING_WEIGHTS = {
    "text_accuracy": 0.30,      # How accurate is the text extraction?
    "table_extraction": 0.20,    # Are tables preserved as markdown?
    "equation_formula": 0.20,    # LaTeX output for math/chemistry
    "diagram_handling": 0.10,    # Are figures described/OCR'd?
    "speed": 0.10,               # Pages per second
    "cost": 0.10,                # $ per 1000 pages
}


@dataclass
class ModelScore:
    """Scores for a model on a document."""
    model: str
    document: str
    text_accuracy: int  # 1-10
    table_extraction: int  # 1-10
    equation_formula: int  # 1-10
    diagram_handling: int  # 1-10
    speed_score: int  # 1-10 (calculated from latency)
    cost_score: int  # 1-10 (calculated from cost)
    notes: str = ""

    @property
    def weighted_score(self) -> float:
        """Calculate weighted total score."""
        return (
            self.text_accuracy * SCORING_WEIGHTS["text_accuracy"] +
            self.table_extraction * SCORING_WEIGHTS["table_extraction"] +
            self.equation_formula * SCORING_WEIGHTS["equation_formula"] +
            self.diagram_handling * SCORING_WEIGHTS["diagram_handling"] +
            self.speed_score * SCORING_WEIGHTS["speed"] +
            self.cost_score * SCORING_WEIGHTS["cost"]
        ) * 10  # Scale to 0-100


def load_all_results() -> dict:
    """Load all evaluation results from the results directory."""
    results = {}

    if not RESULTS_DIR.exists():
        print(f"Results directory not found: {RESULTS_DIR}")
        return results

    for summary_file in RESULTS_DIR.glob("*_summary.json"):
        with open(summary_file) as f:
            data = json.load(f)

        # Extract provider and model from filename
        name = summary_file.stem.replace("_summary", "")
        results[name] = data

    return results


def generate_scoring_template():
    """Generate a scoring template file for manual quality assessment."""

    template = {
        "instructions": """
SCORING GUIDE (1-10 scale):

TEXT ACCURACY:
- 10: Perfect extraction, no errors
- 7-9: Minor errors (punctuation, spacing)
- 4-6: Some words/sentences wrong
- 1-3: Major portions incorrect or missing

TABLE EXTRACTION:
- 10: Perfect markdown tables
- 7-9: Tables present, minor formatting issues
- 4-6: Tables partially extracted
- 1-3: Tables not recognized or badly mangled

EQUATION/FORMULA:
- 10: Perfect LaTeX, renders correctly
- 7-9: LaTeX with minor errors
- 4-6: Some equations as plain text
- 1-3: Equations missing or unreadable

DIAGRAM HANDLING:
- 10: Accurate descriptions of all figures
- 7-9: Most figures described
- 4-6: Some figures noted
- 1-3: Figures ignored or wrong
""",
        "scores": []
    }

    # Load results to generate entries
    results = load_all_results()

    for result_name, data in results.items():
        if "results" not in data:
            continue

        for doc_result in data["results"]:
            doc_name = doc_result.get("doc_name", "unknown")

            template["scores"].append({
                "model": result_name,
                "document": doc_name,
                "text_accuracy": 0,
                "table_extraction": 0,
                "equation_formula": 0,
                "diagram_handling": 0,
                "notes": "",
            })

    output_path = RESULTS_DIR / "scoring_template.json"
    with open(output_path, "w") as f:
        json.dump(template, f, indent=2)

    print(f"Scoring template generated: {output_path}")
    print()
    print("Next steps:")
    print("1. Review the preview files in the results directory")
    print("2. Fill in scores (1-10) for each model+document combination")
    print("3. Run: python evaluation/compare_models.py --score")


def calculate_speed_score(avg_latency_ms: float) -> int:
    """Convert latency to a 1-10 score."""
    if avg_latency_ms <= 500:
        return 10
    elif avg_latency_ms <= 1000:
        return 9
    elif avg_latency_ms <= 2000:
        return 8
    elif avg_latency_ms <= 3000:
        return 7
    elif avg_latency_ms <= 5000:
        return 6
    elif avg_latency_ms <= 10000:
        return 5
    elif avg_latency_ms <= 20000:
        return 4
    elif avg_latency_ms <= 40000:
        return 3
    elif avg_latency_ms <= 60000:
        return 2
    else:
        return 1


def calculate_cost_score(cost_per_1000_pages: float) -> int:
    """Convert cost to a 1-10 score."""
    if cost_per_1000_pages <= 1:
        return 10
    elif cost_per_1000_pages <= 2:
        return 9
    elif cost_per_1000_pages <= 5:
        return 8
    elif cost_per_1000_pages <= 10:
        return 7
    elif cost_per_1000_pages <= 20:
        return 6
    elif cost_per_1000_pages <= 50:
        return 5
    elif cost_per_1000_pages <= 100:
        return 4
    elif cost_per_1000_pages <= 200:
        return 3
    elif cost_per_1000_pages <= 500:
        return 2
    else:
        return 1


def load_scores() -> list[ModelScore]:
    """Load manual scores from the scoring template."""
    scores_path = RESULTS_DIR / "scoring_template.json"

    if not scores_path.exists():
        print(f"Scoring template not found: {scores_path}")
        print("Run with --generate-template first")
        return []

    with open(scores_path) as f:
        data = json.load(f)

    results = load_all_results()
    scores = []

    for score_entry in data.get("scores", []):
        model = score_entry["model"]
        document = score_entry["document"]

        # Find corresponding result for speed/cost
        result_data = results.get(model, {})
        doc_results = [
            r for r in result_data.get("results", [])
            if r.get("doc_name") == document
        ]

        if doc_results:
            doc_result = doc_results[0]
            avg_latency = doc_result.get("avg_latency_per_page_ms", 0) or \
                          doc_result.get("total_time_seconds", 0) * 1000 / max(doc_result.get("total_pages", 1), 1)
            cost_estimate = doc_result.get("cost_estimate", 0)

            # Scale cost to per-1000-pages estimate
            pages_tested = doc_result.get("pages_tested", 1) or doc_result.get("total_pages", 1)
            cost_per_1000 = (cost_estimate / max(pages_tested, 1)) * 1000

            speed_score = calculate_speed_score(avg_latency)
            cost_score = calculate_cost_score(cost_per_1000)
        else:
            speed_score = 5
            cost_score = 5

        scores.append(ModelScore(
            model=model,
            document=document,
            text_accuracy=score_entry.get("text_accuracy", 0),
            table_extraction=score_entry.get("table_extraction", 0),
            equation_formula=score_entry.get("equation_formula", 0),
            diagram_handling=score_entry.get("diagram_handling", 0),
            speed_score=speed_score,
            cost_score=cost_score,
            notes=score_entry.get("notes", ""),
        ))

    return scores


def print_comparison():
    """Print comparison table of all results."""

    results = load_all_results()

    if not results:
        print("No results found. Run evaluation scripts first.")
        return

    print("\n" + "=" * 80)
    print("MODEL COMPARISON - RAW METRICS")
    print("=" * 80)

    # Header
    print(f"\n{'Model':<30} {'Chars':<12} {'Pages':<8} {'Time':<12} {'Chars/pg':<10}")
    print("-" * 80)

    for result_name, data in sorted(results.items()):
        total_chars = sum(r.get("total_chars", 0) for r in data.get("results", []))
        total_pages = sum(
            r.get("pages_tested", 0) or r.get("total_pages", 0)
            for r in data.get("results", [])
        )
        total_time = sum(
            r.get("total_latency_ms", 0) / 1000 or r.get("total_time_seconds", 0)
            for r in data.get("results", [])
        )
        chars_per_page = total_chars / max(total_pages, 1)

        print(f"{result_name:<30} {total_chars:>10,} {total_pages:>6} {total_time:>10.1f}s {chars_per_page:>8,.0f}")

    print()

    # Document breakdown
    print("\n" + "=" * 80)
    print("BREAKDOWN BY DOCUMENT")
    print("=" * 80)

    for doc_name in ["cs", "physics", "chemistry", "biology"]:
        print(f"\n### {doc_name.upper()}")
        print(f"{'Model':<30} {'Chars':<10} {'Time':<10} {'Tables':<8} {'Equations':<10}")
        print("-" * 70)

        for result_name, data in sorted(results.items()):
            doc_results = [
                r for r in data.get("results", [])
                if r.get("doc_name") == doc_name
            ]
            if not doc_results:
                continue

            r = doc_results[0]
            chars = r.get("total_chars", 0)
            time_s = r.get("total_latency_ms", 0) / 1000 or r.get("total_time_seconds", 0)
            tables = "Yes" if r.get("has_tables") else "No"
            equations = "Yes" if r.get("has_equations") else "No"

            print(f"{result_name:<30} {chars:>8,} {time_s:>8.1f}s {tables:<8} {equations:<10}")


def print_scores():
    """Print weighted scores from manual evaluation."""

    scores = load_scores()

    if not scores:
        return

    # Check if any scores have been filled in
    filled_scores = [s for s in scores if s.text_accuracy > 0]

    if not filled_scores:
        print("No scores filled in yet.")
        print("Please edit the scoring template and fill in scores (1-10).")
        return

    print("\n" + "=" * 80)
    print("MODEL SCORES (Manual Quality Assessment)")
    print("=" * 80)

    # Aggregate scores by model
    model_scores = {}
    for score in filled_scores:
        if score.model not in model_scores:
            model_scores[score.model] = []
        model_scores[score.model].append(score)

    print(f"\n{'Model':<30} {'Avg Score':<12} {'Text':<8} {'Tables':<8} {'Eqns':<8} {'Speed':<8} {'Cost':<8}")
    print("-" * 90)

    ranked_models = []

    for model, scores_list in sorted(model_scores.items()):
        avg_total = sum(s.weighted_score for s in scores_list) / len(scores_list)
        avg_text = sum(s.text_accuracy for s in scores_list) / len(scores_list)
        avg_tables = sum(s.table_extraction for s in scores_list) / len(scores_list)
        avg_eqns = sum(s.equation_formula for s in scores_list) / len(scores_list)
        avg_speed = sum(s.speed_score for s in scores_list) / len(scores_list)
        avg_cost = sum(s.cost_score for s in scores_list) / len(scores_list)

        ranked_models.append((model, avg_total))

        print(f"{model:<30} {avg_total:>10.1f} {avg_text:>6.1f} {avg_tables:>6.1f} "
              f"{avg_eqns:>6.1f} {avg_speed:>6.1f} {avg_cost:>6.1f}")

    # Print ranking
    print("\n" + "=" * 80)
    print("FINAL RANKING")
    print("=" * 80)

    ranked_models.sort(key=lambda x: x[1], reverse=True)

    for i, (model, score) in enumerate(ranked_models, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else "  "
        print(f"{medal} {i}. {model}: {score:.1f}/100")

    # Print recommendation
    if ranked_models:
        winner = ranked_models[0][0]
        print(f"\n{'='*80}")
        print(f"RECOMMENDATION: {winner}")
        print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(description="Compare VLM/OCR model evaluation results")
    parser.add_argument(
        "--generate-template",
        action="store_true",
        help="Generate scoring template for manual quality assessment",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="Show weighted scores from manual evaluation",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Show raw metrics comparison",
    )

    args = parser.parse_args()

    if args.generate_template:
        generate_scoring_template()
    elif args.score:
        print_scores()
    elif args.compare:
        print_comparison()
    else:
        # Default: show both comparison and scores
        print_comparison()
        print_scores()


if __name__ == "__main__":
    main()

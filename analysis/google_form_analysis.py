import argparse
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

sns.set(style="whitegrid", font_scale=1.05)


def load_responses(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df.columns = df.columns.str.strip()
    return df


def save_summary(df: pd.DataFrame, label: str, output_dir: Path):
    output_path = output_dir / f"summary_{label}.csv"
    df.to_csv(output_path, index=True)
    print(f"Saved summary table: {output_path}")


def plot_categorical_distribution(df: pd.DataFrame, column: str, output_dir: Path):
    counts = df[column].fillna("Missing").value_counts(dropna=False)
    summary = counts.rename_axis(column).reset_index(name="count")
    save_summary(summary.set_index(column), f"{column}_distribution", output_dir)

    fig, ax = plt.subplots(figsize=(8, 5))
    counts.plot(kind="bar", color="tab:blue", ax=ax)
    ax.set_title(f"Distribution of {column}")
    ax.set_xlabel(column)
    ax.set_ylabel("Count")
    plt.tight_layout()
    fig.savefig(output_dir / f"bar_{column}.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 6))
    counts.plot(kind="pie", autopct="%.1f%%", startangle=90, counterclock=False, ax=ax)
    ax.set_ylabel("")
    ax.set_title(f"Pie chart of {column}")
    plt.tight_layout()
    fig.savefig(output_dir / f"pie_{column}.png")
    plt.close(fig)


def map_likert(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    mapping = {
        "Strongly disagree": 1,
        "Disagree": 2,
        "Neutral": 3,
        "Agree": 4,
        "Strongly agree": 5,
        "Never": 1,
        "Rarely": 2,
        "Sometimes": 3,
        "Often": 4,
        "Always": 5,
        "Very Low": 1,
        "Low": 2,
        "Medium": 3,
        "High": 4,
        "Very High": 5,
    }
    return series.map(mapping).astype(float)


def demographics_analysis(df: pd.DataFrame, output_dir: Path):
    demographic_cols = [col for col in df.columns if col in ["Q1", "Q2", "Q3", "Q4", "Q5"]]
    if not demographic_cols:
        print("No demographic columns Q1-Q5 found.")
        return

    demo_summary = {}
    for col in demographic_cols:
        counts = df[col].fillna("Missing").value_counts(dropna=False)
        percents = counts / counts.sum() * 100
        summary = pd.DataFrame({"count": counts, "percent": percents.round(2)})
        demo_summary[col] = summary
        save_summary(summary, f"demographics_{col}", output_dir)
        plot_categorical_distribution(df, col, output_dir)

    print("Demographics analysis complete.")
    return demo_summary


def regression_analysis(df: pd.DataFrame, output_dir: Path):
    if "Q6" not in df.columns or "Q7" not in df.columns:
        print("Requires Q6 and Q7 for regression analysis.")
        return

    x = pd.to_numeric(df["Q7"], errors="coerce")
    y = pd.to_numeric(df["Q6"], errors="coerce")
    regression_df = pd.DataFrame({"Fuel Expenditure (Q7)": x, "Target (Q6)": y}).dropna()
    if regression_df.empty:
        print("No valid numeric Q6/Q7 data available for regression.")
        return

    slope, intercept, r_value, p_value, std_err = stats.linregress(regression_df.iloc[:, 0], regression_df.iloc[:, 1])

    summary = pd.DataFrame(
        {
            "slope": [slope],
            "intercept": [intercept],
            "r_squared": [r_value**2],
            "p_value": [p_value],
            "std_err": [std_err],
        }
    )
    save_summary(summary, "regression_Q7_vs_Q6", output_dir)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.regplot(x=regression_df.columns[0], y=regression_df.columns[1], data=regression_df, ax=ax, scatter_kws={"alpha": 0.6})
    ax.set_title("Regression: Q6 vs Q7")
    ax.set_xlabel("Fuel Expenditure (Q7)")
    ax.set_ylabel("Q6")
    plt.tight_layout()
    fig.savefig(output_dir / "regression_Q7_vs_Q6.png")
    plt.close(fig)

    numeric_cols = [col for col in df.columns if col in ["Q6", "Q7"]]
    for col in numeric_cols:
        if col != "Q7":
            other = pd.to_numeric(df[col], errors="coerce")
            paired = pd.DataFrame({"Q7": x, col: other}).dropna()
            if paired.shape[0] > 5:
                slope, intercept, r_value, p_value, std_err = stats.linregress(paired["Q7"], paired[col])
                summary = pd.DataFrame(
                    {
                        "x": ["Q7"],
                        "y": [col],
                        "slope": [slope],
                        "intercept": [intercept],
                        "r_squared": [r_value**2],
                        "p_value": [p_value],
                        "std_err": [std_err],
                    }
                )
                save_summary(summary, f"regression_Q7_vs_{col}", output_dir)

    print("Regression analysis complete.")


def group_comparison(df: pd.DataFrame, output_dir: Path):
    if "Q8" not in df.columns:
        print("Q8 group variable not found.")
        return

    df_clean = df[["Q8", "Q6", "Q7"]].copy()
    df_clean["Q6"] = pd.to_numeric(df_clean["Q6"], errors="coerce")
    df_clean["Q7"] = pd.to_numeric(df_clean["Q7"], errors="coerce")
    groups = df_clean["Q8"].dropna().unique()
    numeric_targets = ["Q6", "Q7"]

    for target in numeric_targets:
        data = [group[target].dropna().values for _, group in df_clean.groupby("Q8")]
        if len(data) < 2:
            continue
        if len(groups) == 2:
            stat, p_value = stats.ttest_ind(data[0], data[1], equal_var=False, nan_policy="omit")
            test_name = "t-test"
        else:
            stat, p_value = stats.f_oneway(*data)
            test_name = "ANOVA"
        summary = pd.DataFrame(
            {"group_count": [len(groups)], "test": [test_name], "statistic": [stat], "p_value": [p_value]}
        )
        save_summary(summary, f"group_comparison_{target}", output_dir)

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.boxplot(x="Q8", y=target, data=df_clean, ax=ax)
        ax.set_title(f"Group comparison of {target} by Q8")
        ax.set_xlabel("Q8")
        ax.set_ylabel(target)
        plt.xticks(rotation=30)
        plt.tight_layout()
        fig.savefig(output_dir / f"boxplot_Q8_{target}.png")
        plt.close(fig)

    print("Group comparison analysis complete.")


def productivity_stress_analysis(df: pd.DataFrame, output_dir: Path):
    cols = [col for col in ["Q9", "Q10", "Q11", "Q12", "Q13"] if col in df.columns]
    if not cols:
        print("No Q9-Q13 columns found for productivity/stress analysis.")
        return

    mapped = df[cols].apply(map_likert)
    composite = mapped.mean(axis=1)
    df_out = pd.DataFrame({"composite_score": composite})
    df_out.to_csv(output_dir / "productivity_stress_scores.csv", index=False)

    summary = df_out["composite_score"].describe().round(3).to_frame(name="value")
    save_summary(summary, "productivity_stress_summary", output_dir)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.histplot(df_out["composite_score"].dropna(), bins=12, kde=True, color="tab:green", ax=ax)
    ax.set_title("Productivity / Stress Composite Score Distribution")
    ax.set_xlabel("Composite score (Q9-Q13 average)")
    ax.set_ylabel("Count")
    plt.tight_layout()
    fig.savefig(output_dir / "histogram_productivity_stress.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.kdeplot(df_out["composite_score"].dropna(), fill=True, ax=ax)
    ax.set_title("Density of Productivity / Stress Composite Score")
    ax.set_xlabel("Composite score")
    plt.tight_layout()
    fig.savefig(output_dir / "density_productivity_stress.png")
    plt.close(fig)

    print("Productivity / stress score analysis complete.")


def chi_square_analysis(df: pd.DataFrame, output_dir: Path):
    if "Q14" not in df.columns:
        print("Q14 not found for chi-square analysis.")
        return

    compare_vars = [col for col in ["Q1", "Q3"] if col in df.columns]
    if not compare_vars:
        print("No valid categorical comparison columns available for Q14 chi-square analysis.")
        return

    for group_col in compare_vars:
        contingency = pd.crosstab(df[group_col].fillna("Missing"), df["Q14"].fillna("Missing"))
        summary_name = f"chi2_{group_col}_vs_Q14"
        save_summary(contingency, summary_name, output_dir)

        chi2, p, dof, expected = stats.chi2_contingency(contingency)
        summary = pd.DataFrame(
            {
                "chi2": [chi2],
                "p_value": [p],
                "degrees_of_freedom": [dof],
            }
        )
        save_summary(summary, summary_name + "_results", output_dir)

        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(contingency, annot=True, fmt="d", cmap="Blues", ax=ax)
        ax.set_title(f"Contingency table heatmap: {group_col} vs Q14")
        plt.tight_layout()
        fig.savefig(output_dir / f"heatmap_{group_col}_Q14.png")
        plt.close(fig)

    print("Chi-square analysis complete.")


def awareness_analysis(df: pd.DataFrame, output_dir: Path):
    if "Q15" not in df.columns:
        print("Q15 not found for awareness analysis.")
        return

    counts = df["Q15"].fillna("Missing").value_counts(dropna=False)
    summary = counts.rename_axis("Q15").reset_index(name="count")
    save_summary(summary.set_index("Q15"), "awareness_Q15", output_dir)

    fig, ax = plt.subplots(figsize=(8, 5))
    counts.plot(kind="bar", color="tab:orange", ax=ax)
    ax.set_title("Awareness frequency (Q15)")
    ax.set_xlabel("Q15")
    ax.set_ylabel("Count")
    plt.tight_layout()
    fig.savefig(output_dir / "bar_Q15_awareness.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 6))
    counts.plot(kind="pie", autopct="%.1f%%", startangle=90, counterclock=False, ax=ax)
    ax.set_ylabel("")
    ax.set_title("Awareness share (Q15)")
    plt.tight_layout()
    fig.savefig(output_dir / "pie_Q15_awareness.png")
    plt.close(fig)

    print("Awareness analysis complete.")


def perception_analysis(df: pd.DataFrame, output_dir: Path):
    cols = [col for col in ["Q16", "Q17", "Q18"] if col in df.columns]
    if not cols:
        print("No Q16-Q18 columns found for perception analysis.")
        return

    mapped = df[cols].apply(map_likert)
    means = mapped.mean(skipna=True).round(3)
    overall_index = mapped.mean(axis=1).mean()

    summary = means.to_frame(name="mean_score")
    summary.loc["overall_index"] = overall_index
    save_summary(summary, "perception_scores", output_dir)

    proportion_df = pd.DataFrame()
    for col in cols:
        value_counts = df[col].fillna("Missing").value_counts(dropna=False)
        prop = (value_counts / value_counts.sum()).rename(f"{col}_proportion")
        proportion_df = pd.concat([proportion_df, prop], axis=1)

    proportion_df.fillna(0, inplace=True)
    proportion_df.to_csv(output_dir / "likert_proportions_Q16_Q18.csv")

    fig, ax = plt.subplots(figsize=(10, 6))
    proportion_df.T.plot(kind="bar", stacked=True, ax=ax, colormap="tab20")
    ax.set_title("Likert distribution for Q16-Q18")
    ax.set_xlabel("Question")
    ax.set_ylabel("Proportion")
    ax.legend(title="Response", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    fig.savefig(output_dir / "stacked_likert_Q16_Q18.png")
    plt.close(fig)

    print("Perception / Likert analysis complete.")


def main():
    parser = argparse.ArgumentParser(description="Analyze Google Form response data with demographic, regression, group, chi-square, and Likert analyses.")
    parser.add_argument("csv", help="Path to the Google Form responses CSV file")
    parser.add_argument("--output", default="analysis_outputs", help="Directory where charts and tables will be saved")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_responses(args.csv)
    print(f"Loaded {len(df)} rows from {args.csv}")

    demographics_analysis(df, output_dir)
    regression_analysis(df, output_dir)
    group_comparison(df, output_dir)
    productivity_stress_analysis(df, output_dir)
    chi_square_analysis(df, output_dir)
    awareness_analysis(df, output_dir)
    perception_analysis(df, output_dir)

    print(f"Analysis complete. Results saved in {output_dir.resolve()}")


if __name__ == "__main__":
    main()

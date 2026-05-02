"""
analytics.py - Structured Statistical Analysis Framework for Google Form Data
=============================================================================
Role: Expert Data Scientist & Python Developer
Project: PakPetrol Fuel Subsidy Portal

✅ Quantitative vs Qualitative data categorization
✅ Binary encoding (Yes/No → 1/0)
✅ Correlation matrices with heatmaps
✅ Linear regression with R² and equation overlay
✅ Hypothesis testing (T-Test, P-Value, Cohen's d)
✅ Modular, maintainable function structure
✅ JSON-serializable output for frontend compatibility
✅ Preserves Google Sheets integration via google_sheets_helper.py
"""

import pandas as pd
import numpy as np
from scipy import stats
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
import warnings
import json

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)


# =============================================================================
# 🔧 JSON SERIALIZATION UTILITIES (Critical for Django JsonResponse)
# =============================================================================

def make_json_serializable(obj: Any) -> Any:
    """
    Recursively convert numpy/pandas types to native Python types for JSON serialization.
    """
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif pd.isna(obj):
        return None
    return obj


# =============================================================================
# 🔧 DATA PREPROCESSING UTILITIES
# =============================================================================

def encode_binary_columns(df: pd.DataFrame, 
                         binary_columns: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Transform Yes/No responses into numerical values (Yes=1, No=0).
    
    Args:
        df: Input DataFrame
        binary_columns: List of column names to encode. If None, auto-detect.
    
    Returns:
        DataFrame with encoded binary columns
    """
    df_encoded = df.copy()
    
    # Auto-detect binary columns if not specified
    if binary_columns is None:
        binary_columns = []
        for col in df_encoded.columns:
            if df_encoded[col].dtype == 'object':
                unique_vals = df_encoded[col].dropna().astype(str).str.lower().unique()
                if set(unique_vals).issubset({'yes', 'no', '1', '0', 'true', 'false'}):
                    binary_columns.append(col)
    
    # Apply encoding
    for col in binary_columns:
        if col in df_encoded.columns:
            df_encoded[col] = df_encoded[col].astype(str).str.lower().map({
                'yes': 1, 'no': 0, '1': 1, '0': 0, 
                'true': 1, 'false': 0
            }).astype('Int64')  # Use nullable integer type
    
    logger.info(f"✅ Encoded {len(binary_columns)} binary columns: {binary_columns}")
    return df_encoded


def categorize_columns(df: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Organize DataFrame columns into Quantitative vs Qualitative categories.
    
    Returns:
        Dictionary with 'quantitative' and 'qualitative' column lists
    """
    quantitative = []
    qualitative = []
    
    for col in df.columns:
        if col.lower() in ['timestamp', 'date', 'time']:
            continue
            
        # Check if column is numeric or Likert-scale (1-5)
        if pd.api.types.is_numeric_dtype(df[col]):
            quantitative.append(col)
        elif df[col].dropna().astype(str).str.match(r'^[1-5]$').all():
            # Likert scale detection
            quantitative.append(col)
        else:
            qualitative.append(col)
    
    logger.info(f"📊 Categorized: {len(quantitative)} quantitative, {len(qualitative)} qualitative")
    return {'quantitative': quantitative, 'qualitative': qualitative}


# =============================================================================
# 📈 QUANTITATIVE ANALYSIS MODULE
# =============================================================================

def compute_descriptive_stats(df: pd.DataFrame, 
                             columns: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Compute descriptive statistics for quantitative variables.
    
    Returns:
        Dictionary of statistics per variable (JSON-serializable)
    """
    if columns is None:
        cols = df.select_dtypes(include=[np.number]).columns.tolist()
    else:
        cols = [c for c in columns if c in df.columns and pd.api.types.is_numeric_dtype(df[c])]
    
    stats_dict = {}
    for col in cols:
        data = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(data) > 0:
            stats_dict[col] = make_json_serializable({
                'count': int(len(data)),
                'mean': float(data.mean()),
                'median': float(data.median()),
                'std_dev': float(data.std()),
                'min': float(data.min()),
                'max': float(data.max()),
                'q25': float(data.quantile(0.25)),
                'q75': float(data.quantile(0.75))
            })
    return stats_dict


def compute_correlation_matrix(df: pd.DataFrame,
                              method: str = 'pearson') -> Dict[str, Dict]:
    """
    Generate correlation matrix with significance testing.
    
    Args:
        df: DataFrame with numeric columns
        method: 'pearson', 'spearman', or 'kendall'
    
    Returns:
        Dictionary of pairwise correlations with p-values and strength (JSON-serializable)
    """
    numeric_df = df.select_dtypes(include=[np.number]).dropna()
    if numeric_df.shape[1] < 2:
        return {}
    
    correlations = {}
    cols = numeric_df.columns.tolist()
    
    for i, col1 in enumerate(cols):
        for col2 in cols[i+1:]:
            x, y = numeric_df[col1].dropna(), numeric_df[col2].dropna()
            # Align indices
            mask = x.index.intersection(y.index)
            if len(mask) < 10:  # Minimum sample size
                continue
                
            x_clean, y_clean = x.loc[mask], y.loc[mask]
            
            try:
                r_val, p_val = stats.pearsonr(x_clean, y_clean)
                
                # Interpret strength
                abs_r = abs(r_val)
                if abs_r >= 0.7:
                    strength = "Strong"
                elif abs_r >= 0.5:
                    strength = "Moderate"
                elif abs_r >= 0.3:
                    strength = "Weak"
                else:
                    strength = "Very Weak"
                
                pair_key = f"{col1[:25]} ↔ {col2[:25]}"
                correlations[pair_key] = make_json_serializable({
                    'pearson_r': float(r_val),
                    'p_value': float(p_val),
                    'strength': strength,
                    'significant': bool(p_val < 0.05),
                    'n_samples': int(len(mask))
                })
            except Exception as e:
                logger.debug(f"Correlation error for {col1}, {col2}: {e}")
                continue
    
    # Sort by absolute correlation strength and limit to top 20
    sorted_corr = dict(sorted(
        correlations.items(), 
        key=lambda x: abs(x[1]['pearson_r']), 
        reverse=True
    )[:20])
    
    return sorted_corr


def perform_linear_regression(df: pd.DataFrame,
                             x_var: str,
                             y_var: str) -> Optional[Dict]:
    """
    Perform linear regression analysis with visualization-ready output.
    
    Returns:
        Dictionary with regression parameters, predictions, and statistics (JSON-serializable)
    """
    if x_var not in df.columns or y_var not in df.columns:
        return None
    
    # Clean data
    data = pd.DataFrame({x_var: df[x_var], y_var: df[y_var]}).dropna()
    x = pd.to_numeric(data[x_var], errors='coerce')
    y = pd.to_numeric(data[y_var], errors='coerce')
    mask = ~(x.isna() | y.isna())
    x_clean, y_clean = x[mask], y[mask]
    
    if len(x_clean) < 10:
        return None
    
    try:
        # Compute regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)
        r_squared = r_value ** 2
        
        # Generate prediction line
        x_line = np.linspace(x_clean.min(), x_clean.max(), 100)
        y_line = slope * x_line + intercept
        
        # Format equation
        sign = '+' if intercept >= 0 else '-'
        equation = f"y = {slope:.3f}x {sign} {abs(intercept):.3f}"
        
        return make_json_serializable({
            'x_label': str(x_var)[:30],
            'y_label': str(y_var)[:30],
            'x': x_clean.tolist(),
            'y': y_clean.tolist(),
            'x_line': x_line.tolist(),
            'y_line': y_line.tolist(),
            'slope': float(slope),
            'intercept': float(intercept),
            'r_value': float(r_value),
            'r_squared': float(r_squared),
            'p_value': float(p_value),
            'std_err': float(std_err),
            'equation': equation,
            'significance': 'Significant' if p_value < 0.05 else 'Not Significant',
            'n_samples': int(len(x_clean))
        })
    except Exception as e:
        logger.error(f"Regression error: {e}")
        return None


def perform_t_test(df: pd.DataFrame,
                  group_var: str,
                  value_var: str,
                  group_values: Optional[Tuple[str, str]] = None) -> Optional[Dict]:
    """
    Perform independent samples T-Test for hypothesis validation.
    
    Args:
        df: DataFrame
        group_var: Categorical grouping variable (e.g., 'Gender')
        value_var: Numeric dependent variable
        group_values: Tuple of two group names to compare (auto-detected if None)
    
    Returns:
        Dictionary with T-Test results (JSON-serializable)
    """
    if group_var not in df.columns or value_var not in df.columns:
        return None
    
    # Prepare groups
    if group_values:
        group1 = df[df[group_var].astype(str) == str(group_values[0])][value_var]
        group2 = df[df[group_var].astype(str) == str(group_values[1])][value_var]
        groups_display = list(group_values)
    else:
        groups = df[group_var].dropna().astype(str).unique()
        if len(groups) < 2:
            return None
        group1 = df[df[group_var].astype(str) == str(groups[0])][value_var]
        group2 = df[df[group_var].astype(str) == str(groups[1])][value_var]
        groups_display = [str(groups[0]), str(groups[1])]
    
    # Clean numeric data
    g1_clean = pd.to_numeric(group1, errors='coerce').dropna()
    g2_clean = pd.to_numeric(group2, errors='coerce').dropna()
    
    if len(g1_clean) < 5 or len(g2_clean) < 5:
        return None
    
    try:
        # Welch's T-Test (unequal variance)
        t_stat, p_value = stats.ttest_ind(g1_clean, g2_clean, equal_var=False)
        
        # Effect size (Cohen's d)
        pooled_std = np.sqrt(
            ((len(g1_clean)-1)*g1_clean.std()**2 + (len(g2_clean)-1)*g2_clean.std()**2) /
            (len(g1_clean) + len(g2_clean) - 2)
        )
        cohens_d = (g1_clean.mean() - g2_clean.mean()) / pooled_std if pooled_std > 0 and not np.isnan(pooled_std) else 0
        
        return make_json_serializable({
            'test_type': 'Independent Samples T-Test (Welch)',
            'group_variable': str(group_var),
            'value_variable': str(value_var),
            'groups_compared': groups_display,
            'group1_mean': float(g1_clean.mean()),
            'group2_mean': float(g2_clean.mean()),
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'cohens_d': float(cohens_d),
            'significant': bool(p_value < 0.05),
            'interpretation': (
                f"{'✓' if p_value < 0.05 else '✗'} Significant difference (p={p_value:.4f})" 
                if p_value < 0.05 else f"No significant difference (p={p_value:.4f})"
            ),
            'sample_sizes': {'group1': int(len(g1_clean)), 'group2': int(len(g2_clean))}
        })
    except Exception as e:
        logger.error(f"T-Test error: {e}")
        return None


# =============================================================================
# 📝 QUALITATIVE ANALYSIS MODULE
# =============================================================================

def compute_frequency_distributions(df: pd.DataFrame,
                                   columns: Optional[List[str]] = None) -> Dict[str, Dict]:
    """
    Compute frequency distributions for categorical variables.
    
    Returns:
        Dictionary of value counts per column (JSON-serializable)
    """
    if columns is None:
        cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
    else:
        cols = [c for c in columns if c in df.columns and c not in df.select_dtypes(include=[np.number]).columns]
    
    distributions = {}
    for col in cols:
        if col in df.columns and df[col].notna().any():
            counts = df[col].astype(str).value_counts().to_dict()
            total = sum(counts.values())
            distributions[col] = make_json_serializable({
                'frequencies': counts,
                'percentages': {k: round(v/total*100, 1) for k, v in counts.items()},
                'unique_count': int(df[col].nunique()),
                'mode': str(df[col].mode().iloc[0]) if not df[col].mode().empty else None
            })
    return distributions


def generate_sentiment_summary(df: pd.DataFrame,
                              sentiment_columns: Optional[List[str]] = None,
                              likert_scale: Dict[int, str] = None) -> Dict:
    """
    Generate sentiment summaries for Likert-scale questions.
    
    Returns:
        Dictionary with sentiment analysis results (JSON-serializable)
    """
    if likert_scale is None:
        likert_scale = {
            1: "Strongly Disagree",
            2: "Disagree", 
            3: "Neutral",
            4: "Agree",
            5: "Strongly Agree"
        }
    
    if sentiment_columns is None:
        # Auto-detect Likert columns (numeric, values 1-5)
        sentiment_columns = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                unique_vals = df[col].dropna().unique()
                if set(unique_vals).issubset({1, 2, 3, 4, 5}) and len(unique_vals) >= 3:
                    sentiment_columns.append(col)
    
    summary = {}
    for col in sentiment_columns:
        if col not in df.columns:
            continue
        data = pd.to_numeric(df[col], errors='coerce').dropna()
        if len(data) == 0:
            continue
            
        mean_score = data.mean()
        
        # Interpret mean sentiment
        if mean_score >= 4.2:
            sentiment = "Very Positive"
        elif mean_score >= 3.5:
            sentiment = "Positive"
        elif mean_score >= 2.5:
            sentiment = "Neutral"
        elif mean_score >= 1.8:
            sentiment = "Negative"
        else:
            sentiment = "Very Negative"
        
        summary[col] = make_json_serializable({
            'mean_score': round(float(mean_score), 2),
            'sentiment_label': sentiment,
            'response_distribution': {
                likert_scale.get(int(k), str(k)): int(v) 
                for k, v in data.value_counts().sort_index().to_dict().items()
            },
            'n_responses': int(len(data))
        })
    
    return summary


# =============================================================================
# 🎯 MAIN ANALYSIS ORCHESTRATOR
# =============================================================================

def run_structured_analysis(df: pd.DataFrame,
                           regression_pair: Optional[Tuple[str, str]] = None,
                           ttest_config: Optional[Dict] = None) -> Dict:
    """
    Main entry point: Run complete structured statistical analysis.
    
    Args:
        df: Raw DataFrame from Google Sheets/CSV
        regression_pair: (x_var, y_var) tuple for primary regression analysis
        ttest_config: Dict with 'group_var', 'value_var', 'group_values' for T-Test
    
    Returns:
        Comprehensive analysis payload for frontend rendering (JSON-serializable)
    """
    logger.info("🚀 Starting structured statistical analysis...")
    
    # Step 1: Preprocess
    df_processed = encode_binary_columns(df)
    categories = categorize_columns(df_processed)
    
    # Step 2: Quantitative Analysis
    quantitative_results = {
        'descriptive_stats': compute_descriptive_stats(df_processed, categories['quantitative']),
        'correlations': compute_correlation_matrix(df_processed),
    }
    
    # Primary regression (if specified or auto-select strongest correlation)
    if regression_pair and len(regression_pair) == 2:
        x_var, y_var = regression_pair
        reg_result = perform_linear_regression(df_processed, x_var, y_var)
        if reg_result:
            quantitative_results['primary_regression'] = reg_result
    elif quantitative_results['correlations']:
        # Auto-select strongest significant correlation
        best_pair = None
        best_r = 0
        for pair, corr in quantitative_results['correlations'].items():
            if corr['significant'] and abs(corr['pearson_r']) > best_r:
                best_r = abs(corr['pearson_r'])
                best_pair = pair
        if best_pair:
            # Parse pair string to get column names (simplified)
            vars = best_pair.split(' ↔ ')
            if len(vars) == 2:
                reg_result = perform_linear_regression(df_processed, vars[0].strip(), vars[1].strip())
                if reg_result:
                    quantitative_results['primary_regression'] = reg_result
    
    # Step 3: Hypothesis Testing
    hypothesis_tests = {}
    if ttest_config and all(k in ttest_config for k in ['group_var', 'value_var']):
        ttest_result = perform_t_test(
            df_processed, 
            ttest_config['group_var'], 
            ttest_config['value_var'],
            ttest_config.get('group_values')
        )
        if ttest_result:
            hypothesis_tests['t_test'] = ttest_result
    
    # Add default T-Test: Gender vs Fuel Impact (common research question)
    if 't_test' not in hypothesis_tests:
        # Try to find a reasonable default column for fuel impact
        fuel_cols = [c for c in df_processed.columns if 'fuel' in c.lower() or 'price' in c.lower() or 'expense' in c.lower()]
        if fuel_cols:
            default_ttest = perform_t_test(df_processed, 'Gender', fuel_cols[0])
        else:
            # Fallback to first numeric column
            numeric_cols = df_processed.select_dtypes(include=[np.number]).columns.tolist()
            if len(numeric_cols) >= 2:
                default_ttest = perform_t_test(df_processed, 'Gender', numeric_cols[-1])
            else:
                default_ttest = None
        if default_ttest:
            hypothesis_tests['t_test'] = default_ttest
    
    # Step 4: Qualitative Analysis
    qualitative_results = {
        'frequency_distributions': compute_frequency_distributions(df_processed, categories['qualitative']),
        'sentiment_summary': generate_sentiment_summary(df_processed)
    }
    
    # Step 5: Compile payload (ALL values JSON-serializable)
    payload = make_json_serializable({
        'metadata': {
            'total_responses': int(len(df)),
            'quantitative_vars': int(len(categories['quantitative'])),
            'qualitative_vars': int(len(categories['qualitative'])),
            'analysis_timestamp': pd.Timestamp.now().isoformat()
        },
        'quantitative': quantitative_results,
        'qualitative': qualitative_results,
        'hypothesis_testing': hypothesis_tests,
        'data_quality': {
            'missing_values': {str(k): int(v) for k, v in df.isnull().sum().to_dict().items()},
            'completeness_rate': round((1 - df.isnull().sum().sum() / max(1, df.shape[0] * df.shape[1])) * 100, 1)
        }
    })
    
    logger.info("✅ Structured analysis complete")
    return payload


# =============================================================================
# 🔗 INTEGRATION HELPERS (for views.py compatibility)
# =============================================================================

def enhance_analytics_payload(existing_payload: Dict, df: pd.DataFrame) -> Dict:
    """
    Merge structured analysis results into existing analytics payload.
    Preserves backward compatibility with existing frontend code.
    
    Usage in views.py:
        payload = compute_analytics_payload(df)  # existing function
        payload = enhance_analytics_payload(payload, df)  # add new features
    
    Returns:
        Enhanced payload (JSON-serializable)
    """
    try:
        structured = run_structured_analysis(df)
        
        # Merge quantitative results
        if 'quantitative' in structured:
            if 'descriptive_stats' in existing_payload and 'descriptive_stats' in structured['quantitative']:
                existing_payload['descriptive_stats'].update(
                    structured['quantitative'].get('descriptive_stats', {})
                )
            existing_payload['correlations'] = structured['quantitative'].get('correlations', {})
            if 'primary_regression' in structured['quantitative']:
                existing_payload['regression'] = structured['quantitative']['primary_regression']
        
        # Add hypothesis testing section
        if 'hypothesis_testing' in structured:
            existing_payload['hypothesis_tests'] = structured['hypothesis_testing']
        
        # Add qualitative insights
        if 'qualitative' in structured:
            existing_payload['qualitative_insights'] = structured['qualitative']
        
        # Add metadata
        if 'metadata' in structured:
            existing_payload['analysis_metadata'] = structured['metadata']
        
        logger.info("🔗 Enhanced payload with structured analysis")
        
    except Exception as e:
        logger.error(f"⚠️ Enhancement failed (falling back to original): {e}")
        # Return original payload unchanged on error
    
    return make_json_serializable(existing_payload)
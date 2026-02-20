"""
Calculation Agent
Performs mathematical and statictical analysis that LLMs strguggle with

Capabilities:
- Compare periods (% change, absolute difference)
- Statistical significance testing
- Trend analysis
- Identify outliers
- Correlation analysis

"""
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
import numpy as np
from scipy import stats
from decimal import Decimal

class CalculationAgent(BaseAgent):
    """
    Handles numerical computations with precision
    
    Why seprate from LLM?
    -LLMs make math errors
    - Need exact calulations for buiseness decisions
    - Faster than LLM calls
    """

    def __init__(self, config: Optional[Dict] = None):
        super().__init__("calculation", config)
        # No LLM needed - pure Python math!

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate we have a task and required data"""
        return (
            isinstance(input_data, dict) and
            'task' in input_data
        )
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate calculation method"""
        
        task = input_data['task']
        params = input_data.get('params', {})
        dependency_results = input_data.get('dependency_results', {})
        
        self.logger.info(f"Executing calculation task: {task}")

        # Route to specific calculation
        if task == 'compare_periods':
            return self._compare_periods(dependency_results, params)
        elif task == 'identify_biggest_changes':
            return self._identify_biggest_changes(dependency_results, params)
        elif task == 'analyze_trend':
            return self._analyze_trend(dependency_results, params)
        elif task == 'statistical_significance':
            return self._test_significance(dependency_results, params)
        else:
            raise ValueError(f"Unknown calculation task: {task}")
        
    def _compare_periods(
        self, 
        dependency_results: Dict,
        params: Dict
    ) -> Dict[str, Any]:
        """
        Compare two time periods
        
        Input from dependencies:
        - Step 1 result: current period data
        - Step 2 result: comparison period data
        """
        
        self.logger.info("Comparing time periods...")
        
        # Extract data from dependent steps
        current_data = None
        comparison_data = None
        
        for step_num, result in dependency_results.items():
            if result.get('status') == 'success':
                # FIX: Access result directly, not nested in 'data'
                step_result = result.get('result', {})
                
                # Get the SQL results
                sql_results = step_result.get('results', [])
                
                # Determine which period based on params
                params_data = step_result.get('params', {})
                time_period = params_data.get('time_period', {})
                
                # Check if this is current or comparison period
                period_label = params_data.get('label', '')
                
                if 'current' in period_label.lower():
                    current_data = sql_results
                    self.logger.info(f"Found current period data: {len(sql_results)} rows")
                elif 'comparison' in period_label.lower():
                    comparison_data = sql_results
                    self.logger.info(f"Found comparison period data: {len(sql_results)} rows")
                elif current_data is None:
                    # First result = current
                    current_data = sql_results
                    self.logger.info(f"Assigned first result as current: {len(sql_results)} rows")
                elif comparison_data is None:
                    # Second result = comparison
                    comparison_data = sql_results
                    self.logger.info(f"Assigned second result as comparison: {len(sql_results)} rows")
        
        if not current_data or not comparison_data:
            self.logger.error(f"Missing data - Current: {current_data is not None}, Comparison: {comparison_data is not None}")
            raise ValueError("Missing data from dependencies")
        
        # Extract metric values
        current_value = self._extract_metric_value(current_data)
        comparison_value = self._extract_metric_value(comparison_data)
        
        self.logger.info(f"Current value: {current_value}, Comparison value: {comparison_value}")
        
        # Calculate changes
        absolute_change = current_value - comparison_value
        
        if comparison_value != 0:
            percentage_change = (absolute_change / comparison_value) * 100
        else:
            percentage_change = 0 if absolute_change == 0 else float('inf')
        
        # Determine direction
        if absolute_change > 0:
            direction = "increase"
        elif absolute_change < 0:
            direction = "decrease"
        else:
            direction = "no change"
        
        # Statistical significance (simple version)
        is_significant = abs(percentage_change) > 5  # >5% change is "significant"
        
        result = {
            'current_value': float(current_value),
            'comparison_value': float(comparison_value),
            'absolute_change': float(absolute_change),
            'percentage_change': round(percentage_change, 2),
            'direction': direction,
            'is_significant': is_significant,
            'interpretation': self._interpret_change(percentage_change, direction)
        }
        
        self.logger.info(f"Comparison: {percentage_change:+.1f}% change")
        
        return result
    
    def _identify_biggest_changes(
        self,
        dependency_results: Dict,
        params: Dict
    ) -> Dict[str, Any]:
        """
        Find dimensions with biggest changes
        
        Used for root cause analysis:
        "Which product category dropped most?"
        """

        self.logger.info("Identifying biggest changes by dimension...")

        # Get breakdown data from dependencies
        breakdown_data = None

        for step_num, result in dependency_results.items():
            if result.get('status') == 'success':
                step_result = result['data']['result']
                if 'breakdown' in step_result.get('task', ''):
                    breakdown_data = step_result['results']
                    break

            if not breakdown_data:
                raise ValueError("No breakdown data found in dependencies")
            
            # Analyze each dimension
            changes = []

            for row in breakdown_data:
                # Assuming row has: dimension, current_value, previous_value
                dimension_name = self._get_dimension_name(row)
                current = self._extract_value(row, 'revenue', 'current')
                previous = self._extract_value(row, 'revenue', 'previous')

                if previous and previous != 0:
                    pct_change = ((current - previous) / previous) * 100

                    changes.append({
                        'dimension': dimension_name,
                        'current_value': float(current),
                        'previous_value': float(previous),
                        'absolute_change': float(current - previous),
                        'percentage_change': round(pct_change, 2)
                    })

            # Sort by absolute percentage change(biggest impact first)
        changes.sort(key=lambda x: abs(x['percentage_change']), reverse=True)

        # Top 5 biggest changes
        top_changes = changes[:5]

        result = {
            'top_changes': top_changes,
            'total_dimensions_analyzed': len(changes),
            'biggest_drop': max(changes, key=lambda x: -x['percentage_change']) if changes else None,
            'biggest_gain': max(changes, key=lambda x: x['percentage_change']) if changes else None
        }
        
        self.logger.info(f"Found {len(top_changes)} significant changes")
        
        return result
    
    def _analyze_trend(
        self,
        dependency_results: Dict,
        params: Dict
    ) -> Dict[str, Any]:
        """
        Analyze time-series trend
        
        Detects:
        - Overall trend (up/down/flat)
        - Seasonality patterns
        - Anomalies
        """ 
        self.logger.info("Analyzing trend...")

        # Get time-series data
        timeseries_data = None

        for step_num, result in dependency_results.items():
            if result.get('status') == 'success':
                step_result = result['data']['result']
                if 'timeseries' in step_result.get('task', ''):
                    timeseries_data = step_result['results']
                    break

        if not timeseries_data or len(timeseries_data) < 3:
            raise ValueError("Insufficient time-series data (need at least 3 points)")
        
        # extract values
        values = [float(self._extract_metric_value([row])) for row in timeseries_data]


        # Calculate trend using linear regression
        x = np.arange(len(values))
        slope, intercept = np.polyfit(x, values, 1)

        # Caclualte R-Squared (how well trend fits)

        y_pred = slope * x + intercept
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Determine trend direction
        if slope > 0:
            trend_direction = "increasing"
        elif slope < 0:
            trend_direction = "decreasing"
        else:
            trend_direction = "flat"

        # Detect anomalies (values >2 std deviations from mean)
        mean_val = np.mean(values)
        std_val = np.std(values)
        anomalies = []

        for i, val in enumerate(values):
            z_score = abs((val - mean_val) / std_val) if std_val > 0 else 0
            if z_score > 2:
                anomalies.append({
                    'index': i,
                    'value': float(val),
                    'z_score': round(float(z_score), 2)
                })

        result = {
            'trend_direction': trend_direction,
            'slope': round(float(slope), 2),
            'r_squared': round(float(r_squared), 3),
            'trend_strength': 'strong' if r_squared > 0.7 else 'moderate' if r_squared > 0.4 else 'weak',
            'mean': round(float(mean_val), 2),
            'std_dev': round(float(std_val), 2),
            'anomalies_count': len(anomalies),
            'anomalies': anomalies[:3]  # Top 3 anomalies
        }
        self.logger.info(f"Trend: {trend_direction} (R²={r_squared:.2f})")
        return result
        
    def _test_significance(
        self,
        dependency_results: Dict,
        params: Dict
    ) -> Dict[str, Any]:
        """
        Statistical significance test (t-test)
        
        Answers: "Is this change real or random?"
        """
        self.logger.info("Running statistical significance test...")

        # Extract tow groups of data
        group_a = params.get('group_a', [])
        group_b = params.get('group_b', [])

        if not group_a or not group_b:
            raise ValueError("Need two groups for significance test")
        
        #Perform independent t-test
        t_stat, p_value = stats.ttest_ind(group_a, group_b)

        #Interpret p-value
        alpha = 0.05
        is_significant = p_value < alpha

        # Calculate effect size(Cohen's d)
        mean_diff = np.mean(group_a) - np.mean(group_b)
        pooled_std = np.sqrt((np.std(group_a)**2 + np.std(group_b)**2) / 2)
        cohens_d = mean_diff / pooled_std if pooled_std != 0 else 0

        # Effect size interpretation
        if abs(cohens_d) < 0.2:
            effect_size = "negligible"
        elif abs(cohens_d) < 0.5:
            effect_size = "small"
        elif abs(cohens_d) < 0.8:
            effect_size = "medium"
        else:
            effect_size = "large"

        result = {
            't_statistic': round(float(t_stat), 3),
            'p_value': round(float(p_value), 4),
            'is_significant': is_significant,
            'confidence_level': f"{(1-alpha)*100}%",
            'cohens_d': round(float(cohens_d), 3),
            'effect_size': effect_size,
            'interpretation': self._interpret_significance(p_value, cohens_d)
        }
        
        self.logger.info(f"Significance: p={p_value:.4f}, {'significant' if is_significant else 'not significant'}")
        
        return result
    
    # Helper methods

    def _extract_metric_value(self, data: List[Dict]) -> float:
        """Extract metric value from query results"""
        if not data:
            return 0.0
        
        row = data[0]

        # Common metric column names
        metric_cols = ['revenue', 'sum', 'total', 'count', 'avg', 'average']

        for col in  metric_cols:
            if col in row:
                value = row[col]
                if isinstance(value, Decimal):
                    return float(value)
                return float(value)
            
         # If no known column, take first numeric value
        for value in row.values():
            if isinstance(value, (int, float, Decimal)):
                return float(value)
        
        return 0.0   

    def _get_dimension_name(self, row: Dict) -> str:
        """Get dimension value from row"""
        # Look for dimension columns
        dimension_cols = ['product_category', 'region', 'customer_segment']

        for col in dimension_cols:
            if col in row:
                return str(row[col])
            
        # Return first string column
        for key, value in row.items():
            if isinstance(value, str):
                return value
            
        return "Unknown"
    
    def _extract_value(self, row: Dict, metric: str, period: str) -> float:
        """Extract specific value from row"""
        # Try exact match
        if metric in row:
            return float(row[metric])
        
        # Try with period suffix
        col_name = f"{metric}_{period}"
        if col_name in row:
            return float(row[col_name])
        
        return 0.0
    

    
    def _interpret_change(self, pct_change: float, direction: str) -> str:
        """Human readable interpratation of change"""
        abs_change = abs(pct_change)

        if abs_change < 2:
            return f"Minimal {direction} (within normal variance)"
        elif abs_change < 10:
            return f"Moderate {direction} - investigate if unexpected"
        elif abs_change < 25:
            return f"Significant {direction} - requires attention"
        else:
            return f"Major {direction} - urgent investigation needed"
    
    def _interpret_significance(self, p_value: float, cohens_d: float) -> str:
        """Interpret statistical test results"""
        if p_value < 0.01:
            confidence = "very high confidence (99%)"
        elif p_value < 0.05:
            confidence = "high confidence (95%)"
        else:
            confidence = "low confidence - may be random chance"
        
        effect = "large" if abs(cohens_d) > 0.8 else "moderate" if abs(cohens_d) > 0.5 else "small"
        
        return f"Difference is real with {confidence}. Effect size is {effect}."

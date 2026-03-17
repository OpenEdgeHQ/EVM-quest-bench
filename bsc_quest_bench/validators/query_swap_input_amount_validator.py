"""
Validator for query_swap_input_amount atomic problem.
Validates that the LLM correctly queries the required input amount using PancakeSwap Router's getAmountsIn function.
"""

from typing import Dict, Any, Optional


class QuerySwapInputAmountValidator:
    """Validator for PancakeSwap swap input amount query operations"""
    
    def __init__(
        self,
        router_address: str,
        amount_out: float,
        token_in_address: str,
        token_out_address: str,
        token_in_decimals: int = 18,
        token_out_decimals: int = 18,
        token_in_symbol: str = "USDT",
        token_out_symbol: str = "BUSD",
        expected_amounts: Optional[list] = None
    ):
        """
        Initialize validator with swap parameters.
        
        Args:
            router_address: PancakeSwap Router address
            amount_out: Desired output amount (in token units)
            token_in_address: Input token address
            token_out_address: Output token address
            token_in_decimals: Input token decimals (default: 18)
            token_out_decimals: Output token decimals (default: 18)
            token_in_symbol: Input token symbol (default: "USDT")
            token_out_symbol: Output token symbol (default: "BUSD")
            expected_amounts: Expected amounts array from chain query (set by quest_executor)
        """
        self.router_address = router_address.lower()
        self.amount_out = amount_out
        self.token_in_address = token_in_address.lower()
        self.token_out_address = token_out_address.lower()
        self.token_in_decimals = token_in_decimals
        self.token_out_decimals = token_out_decimals
        self.token_in_symbol = token_in_symbol
        self.token_out_symbol = token_out_symbol
        self.expected_amounts = expected_amounts
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the swap input amount query result.
        
        Scoring:
        - Query execution success: 30 points
        - Return format correctness: 30 points
        - Input amount correctness: 40 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains expected_amounts if available)
            state_after: Not used for query operations
            
        Returns:
            Validation result with score and feedback
        """
        # For query operations, the query result is in 'tx'
        query_result = tx.get('query_result', {})
        score = 0
        max_score = 100
        checks = []
        feedback_parts = []
        
        # Use expected amounts from state_before if not set during initialization
        if self.expected_amounts is None and 'expected_amounts' in state_before:
            self.expected_amounts = state_before['expected_amounts']
        
        # Check 1: Query execution success (30 points)
        query_success = query_result.get('success', False)
        error_msg = query_result.get('error', '')
        
        if query_success:
            score += 30
            checks.append({
                'name': 'Query Execution Success',
                'passed': True,
                'message': 'Query executed successfully'
            })
        else:
            checks.append({
                'name': 'Query Execution Success',
                'passed': False,
                'message': f"Query execution failed: {error_msg}"
            })
            return {
                'passed': False,
                'score': score,
                'max_score': max_score,
                'checks': checks,
                'feedback': '❌ Query execution failed'
            }
        
        # Extract data from query result
        data = query_result.get('data', {})
        
        # Check 2: Return format correctness (30 points)
        required_fields = ['amounts', 'amount_in', 'amount_out']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            score += 30
            checks.append({
                'name': 'Return Format Correct',
                'passed': True,
                'message': f'All required fields present: {required_fields}'
            })
        else:
            checks.append({
                'name': 'Return Format Correct',
                'passed': False,
                'message': f'Missing required fields: {missing_fields}'
            })
            feedback_parts.append(f"⚠️  Missing fields: {', '.join(missing_fields)}")
        
        # Check 3: Input amount correctness (40 points)
        if self.expected_amounts:
            try:
                # Parse amounts from query result data
                returned_amounts = data.get('amounts', [])
                if isinstance(returned_amounts, list) and len(returned_amounts) >= 2:
                    # amounts[0] is the required input, amounts[-1] is the desired output
                    returned_amount_in = int(returned_amounts[0]) if isinstance(returned_amounts[0], (int, str)) else int(returned_amounts[0])
                    returned_amount_out = int(returned_amounts[-1]) if isinstance(returned_amounts[-1], (int, str)) else int(returned_amounts[-1])
                else:
                    # Try to get from amount_in field
                    returned_amount_in = int(data.get('amount_in', 0))
                    returned_amount_out = int(data.get('amount_out', 0))
                
                expected_amount_in = int(self.expected_amounts[0])
                expected_amount_out = int(self.expected_amounts[-1])
                
                # Check if amounts match (with 1% tolerance for rounding)
                amount_in_diff_percent = abs(returned_amount_in - expected_amount_in) / expected_amount_in * 100 if expected_amount_in > 0 else 0
                amount_out_diff_percent = abs(returned_amount_out - expected_amount_out) / expected_amount_out * 100 if expected_amount_out > 0 else 0
                
                if amount_in_diff_percent <= 1 and amount_out_diff_percent <= 1:
                    score += 40
                    checks.append({
                        'name': 'Input Amount Correctness',
                        'passed': True,
                        'message': f'Input amount: {returned_amount_in}, Output amount: {returned_amount_out}'
                    })
                    feedback_parts.append("✅ Input amount calculated correctly!")
                else:
                    partial_score = max(0, int(40 * (1 - min(amount_in_diff_percent, amount_out_diff_percent) / 10)))
                    score += partial_score
                    checks.append({
                        'name': 'Input Amount Correctness',
                        'passed': False,
                        'message': f'Amount mismatch - Expected input: {expected_amount_in}, Got: {returned_amount_in} (diff: {amount_in_diff_percent:.2f}%); Expected output: {expected_amount_out}, Got: {returned_amount_out} (diff: {amount_out_diff_percent:.2f}%)'
                    })
                    feedback_parts.append(f"⚠️  Input amount difference: {amount_in_diff_percent:.2f}%, Output amount difference: {amount_out_diff_percent:.2f}%")
            except (ValueError, KeyError, TypeError) as e:
                checks.append({
                    'name': 'Input Amount Correctness',
                    'passed': False,
                    'message': f'Failed to parse amounts: {str(e)}'
                })
                feedback_parts.append(f"❌ Failed to parse amounts: {str(e)}")
        else:
            checks.append({
                'name': 'Input Amount Correctness',
                'passed': False,
                'message': 'No expected amounts available for comparison'
            })
            feedback_parts.append("⚠️  Cannot verify amounts: no expected values")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! Swap input amount queried correctly!"
        elif score >= 60:
            feedback = "✅ Query mostly correct. " + " ".join(feedback_parts)
        else:
            feedback = "❌ Query needs improvement. " + " ".join(feedback_parts)
        
        return {
            'passed': score >= 60,  # Pass threshold: 60%
            'score': score,
            'max_score': max_score,
            'checks': checks,
            'feedback': feedback
        }


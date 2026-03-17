"""
Validator for query_staked_amount atomic problem.
Validates that the LLM correctly queries the staked amount using the staking contract's userInfo function.
"""

from typing import Dict, Any, Optional


class QueryStakedAmountValidator:
    """Validator for staking contract staked amount query operations"""
    
    def __init__(
        self,
        pool_address: str,
        query_address: str,
        expected_staked_amount: float,
        token_decimals: int = 18
    ):
        """
        Initialize validator with staking query parameters.
        
        Args:
            pool_address: SimpleStaking contract address
            query_address: User address to query staked amount for
            expected_staked_amount: Expected staked amount (in token units)
            token_decimals: Token decimals (default: 18 for CAKE)
        """
        self.pool_address = pool_address.lower()
        self.query_address = query_address.lower()
        self.expected_staked_amount = expected_staked_amount
        self.token_decimals = token_decimals
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the staked amount query result.
        
        Scoring:
        - Query execution success: 30 points
        - Return format correctness: 30 points
        - Staked amount correctness: 40 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains actual staked amount if available)
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
        
        # Get expected staked amount from state_before if set by quest_executor
        expected_staked_amount_wei = state_before.get('staked_amount')
        if expected_staked_amount_wei is None:
            # Calculate from expected_staked_amount parameter
            from decimal import Decimal
            expected_staked_amount_wei = int(Decimal(str(self.expected_staked_amount)) * Decimal(10**self.token_decimals))
        
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
        required_fields = ['staked_amount', 'deposit_time']
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
        
        # Check 3: Staked amount correctness (40 points)
        try:
            # Parse staked amount from query result
            returned_staked_amount = data.get('staked_amount', '0')
            if isinstance(returned_staked_amount, str):
                returned_staked_amount_wei = int(returned_staked_amount)
            else:
                returned_staked_amount_wei = int(returned_staked_amount)
            
            # Check if amounts match (with 1% tolerance for rounding)
            if expected_staked_amount_wei > 0:
                amount_diff_percent = abs(returned_staked_amount_wei - expected_staked_amount_wei) / expected_staked_amount_wei * 100
            else:
                # If expected is 0, check if returned is also 0
                amount_diff_percent = 0 if returned_staked_amount_wei == 0 else 100
            
            if amount_diff_percent <= 1:
                score += 40
                checks.append({
                    'name': 'Staked Amount Correctness',
                    'passed': True,
                    'message': f'Staked amount: {returned_staked_amount_wei} wei ({returned_staked_amount_wei / 10**self.token_decimals:.6f} tokens)'
                })
                feedback_parts.append("✅ Staked amount queried correctly!")
            else:
                partial_score = max(0, int(40 * (1 - amount_diff_percent / 10)))
                score += partial_score
                checks.append({
                    'name': 'Staked Amount Correctness',
                    'passed': False,
                    'message': f'Amount mismatch - Expected: {expected_staked_amount_wei} wei, Got: {returned_staked_amount_wei} wei (diff: {amount_diff_percent:.2f}%)'
                })
                feedback_parts.append(f"⚠️  Staked amount difference: {amount_diff_percent:.2f}%")
        except (ValueError, KeyError, TypeError) as e:
            checks.append({
                'name': 'Staked Amount Correctness',
                'passed': False,
                'message': f'Failed to parse staked amount: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse staked amount: {str(e)}")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! Staked amount queried correctly!"
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


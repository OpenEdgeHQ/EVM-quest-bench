"""
Query ERC20 Balance Validator

Validate correctness of ERC20 token balance query operation
"""

from typing import Dict, Any, List


class QueryERC20BalanceValidator:
    """Query ERC20 Balance Validator"""
    
    def __init__(self, token_address: str, query_address: str, token_decimals: int = 18, expected_balance: float = None, **kwargs):
        """
        Initialize validator
        
        Args:
            token_address: ERC20 token contract address
            query_address: Address to query balance for
            token_decimals: Token decimal places (default: 18)
            expected_balance: Expected balance (not used in validation, set via Anvil)
        """
        self.token_address = token_address.lower()
        self.query_address = query_address.lower()
        self.token_decimals = token_decimals
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate query result
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: State before query (contains actual token balance)
            state_after: State after query
            
        Returns:
            Validation result dictionary
        """
        checks = []
        score = 0
        
        # For query operations, the result is stored in the tx object
        query_result = tx.get('query_result', {})
        
        # Check 1: Query executed successfully (30 points)
        query_success = query_result.get('success', False)
        error_msg = query_result.get('error', '')
        
        checks.append({
            'name': 'Query Execution Success',
            'passed': query_success,
            'message': 'Query executed successfully' if query_success else f'Query failed: {error_msg}',
            'score': 30 if query_success else 0
        })
        if query_success:
            score += 30
        else:
            # If query failed, return early
            return {
                'passed': False,
                'score': score,
                'max_score': self.max_score,
                'checks': checks,
                'feedback': self._generate_feedback(checks, score, False),
                'details': {
                    'token_address': self.token_address,
                    'query_address': self.query_address,
                    'error': error_msg
                }
            }
        
        # Check 2: Return format correct (30 points)
        # Expected format: { balance_raw: string, balance_formatted: string }
        returned_data = query_result.get('data', {})
        has_balance_raw = 'balance_raw' in returned_data
        
        format_correct = has_balance_raw
        format_score = 30 if format_correct else 0
        
        checks.append({
            'name': 'Return Format Correct',
            'passed': format_correct,
            'message': f"Expected 'balance_raw' field in result. Got: {list(returned_data.keys())}",
            'score': format_score
        })
        if format_correct:
            score += format_score
        else:
            # If format is incorrect, can't validate correctness
            return {
                'passed': False,
                'score': score,
                'max_score': self.max_score,
                'checks': checks,
                'feedback': self._generate_feedback(checks, score, False),
                'details': {
                    'token_address': self.token_address,
                    'query_address': self.query_address,
                    'returned_keys': list(returned_data.keys())
                }
            }
        
        # Check 3: Balance value correctness (40 points)
        # Compare returned balance with actual chain state
        returned_balance_raw = returned_data.get('balance_raw', '')
        
        # Get actual token balance from state_before
        actual_balance = state_before.get('token_balance', 0)
        
        try:
            # Convert returned balance to int
            if isinstance(returned_balance_raw, str):
                if returned_balance_raw.startswith('0x'):
                    returned_balance = int(returned_balance_raw, 16)
                else:
                    returned_balance = int(returned_balance_raw)
            else:
                returned_balance = int(returned_balance_raw)
            
            # Balance should match exactly
            balance_correct = returned_balance == actual_balance
            
            # Calculate human-readable values
            actual_balance_formatted = actual_balance / (10 ** self.token_decimals)
            returned_balance_formatted = returned_balance / (10 ** self.token_decimals)
            
            checks.append({
                'name': 'Balance Correctness',
                'passed': balance_correct,
                'message': f"Expected: {actual_balance} ({actual_balance_formatted:.6f} tokens), "
                          f"Got: {returned_balance} ({returned_balance_formatted:.6f} tokens)",
                'score': 40 if balance_correct else 0
            })
            if balance_correct:
                score += 40
            
            balance_value_for_details = returned_balance
            
        except (ValueError, TypeError) as e:
            checks.append({
                'name': 'Balance Correctness',
                'passed': False,
                'message': f"Failed to parse balance value: {e}",
                'score': 0
            })
            balance_value_for_details = None
            actual_balance_formatted = 0
            returned_balance_formatted = 0
        
        # Determine if passed
        passed = all(check['passed'] for check in checks)
        
        # Generate feedback
        feedback = self._generate_feedback(checks, score, passed)
        
        return {
            'passed': passed,
            'score': score,
            'max_score': self.max_score,
            'checks': checks,
            'feedback': feedback,
            'details': {
                'token_address': self.token_address,
                'query_address': self.query_address,
                'token_decimals': self.token_decimals,
                'expected_balance_raw': actual_balance,
                'expected_balance_formatted': actual_balance_formatted,
                'returned_balance_raw': balance_value_for_details,
                'returned_balance_formatted': returned_balance_formatted if balance_value_for_details else None
            }
        }
    
    def _generate_feedback(
        self,
        checks: List[Dict[str, Any]],
        score: int,
        passed: bool
    ) -> str:
        """
        Generate feedback message
        
        Args:
            checks: List of check items
            score: Total score
            passed: Whether validation passed
            
        Returns:
            Feedback string
        """
        lines = []
        
        if passed:
            lines.append("🎉 Congratulations! ERC20 balance query executed correctly!")
            lines.append(f"Final Score: {score}/{self.max_score}")
        else:
            lines.append("❌ Query validation failed, please check the following issues:")
            failed_checks = [c for c in checks if not c['passed']]
            for check in failed_checks:
                lines.append(f"  - {check['name']}: {check['message']}")
            lines.append(f"\nCurrent Score: {score}/{self.max_score}")
        
        return '\n'.join(lines)


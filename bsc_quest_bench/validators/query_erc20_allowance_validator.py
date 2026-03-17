"""
Query ERC20 Allowance Validator

Validate correctness of ERC20 token allowance query operation
"""

from typing import Dict, Any, List


class QueryERC20AllowanceValidator:
    """Query ERC20 Allowance Validator"""
    
    def __init__(
        self, 
        token_address: str, 
        owner_address: str, 
        spender_address: str,
        token_decimals: int = 18,
        expected_allowance: float = None,
        **kwargs
    ):
        """
        Initialize validator
        
        Args:
            token_address: ERC20 token contract address
            owner_address: Token owner address
            spender_address: Spender address
            token_decimals: Token decimal places (default: 18)
            expected_allowance: Expected allowance (not used in validation, set via Anvil)
        """
        self.token_address = token_address.lower()
        self.owner_address = owner_address.lower()
        self.spender_address = spender_address.lower()
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
            state_before: State before query (contains actual allowance)
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
                    'owner_address': self.owner_address,
                    'spender_address': self.spender_address,
                    'error': error_msg
                }
            }
        
        # Check 2: Return format correct (30 points)
        # Expected format: { allowance_raw: string, allowance_formatted: string }
        returned_data = query_result.get('data', {})
        has_allowance_raw = 'allowance_raw' in returned_data
        
        format_correct = has_allowance_raw
        format_score = 30 if format_correct else 0
        
        checks.append({
            'name': 'Return Format Correct',
            'passed': format_correct,
            'message': f"Expected 'allowance_raw' field in result. Got: {list(returned_data.keys())}",
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
                    'owner_address': self.owner_address,
                    'spender_address': self.spender_address,
                    'returned_keys': list(returned_data.keys())
                }
            }
        
        # Check 3: Allowance value correctness (40 points)
        # Compare returned allowance with actual chain state
        returned_allowance_raw = returned_data.get('allowance_raw', '')
        
        # Get actual allowance from state_before
        actual_allowance = state_before.get('allowance', 0)
        
        try:
            # Convert returned allowance to int
            if isinstance(returned_allowance_raw, str):
                if returned_allowance_raw.startswith('0x'):
                    returned_allowance = int(returned_allowance_raw, 16)
                else:
                    returned_allowance = int(returned_allowance_raw)
            else:
                returned_allowance = int(returned_allowance_raw)
            
            # Allowance should match exactly
            allowance_correct = returned_allowance == actual_allowance
            
            # Calculate human-readable values
            actual_allowance_formatted = actual_allowance / (10 ** self.token_decimals)
            returned_allowance_formatted = returned_allowance / (10 ** self.token_decimals)
            
            checks.append({
                'name': 'Allowance Correctness',
                'passed': allowance_correct,
                'message': f"Expected: {actual_allowance} ({actual_allowance_formatted:.6f} tokens), "
                          f"Got: {returned_allowance} ({returned_allowance_formatted:.6f} tokens)",
                'score': 40 if allowance_correct else 0
            })
            if allowance_correct:
                score += 40
            
            allowance_value_for_details = returned_allowance
            
        except (ValueError, TypeError) as e:
            checks.append({
                'name': 'Allowance Correctness',
                'passed': False,
                'message': f"Failed to parse allowance value: {e}",
                'score': 0
            })
            allowance_value_for_details = None
            actual_allowance_formatted = 0
            returned_allowance_formatted = 0
        
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
                'owner_address': self.owner_address,
                'spender_address': self.spender_address,
                'token_decimals': self.token_decimals,
                'expected_allowance_raw': actual_allowance,
                'expected_allowance_formatted': actual_allowance_formatted,
                'returned_allowance_raw': allowance_value_for_details,
                'returned_allowance_formatted': returned_allowance_formatted if allowance_value_for_details else None
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
            lines.append("🎉 Congratulations! ERC20 allowance query executed correctly!")
            lines.append(f"Final Score: {score}/{self.max_score}")
        else:
            lines.append("❌ Query validation failed, please check the following issues:")
            failed_checks = [c for c in checks if not c['passed']]
            for check in failed_checks:
                lines.append(f"  - {check['name']}: {check['message']}")
            lines.append(f"\nCurrent Score: {score}/{self.max_score}")
        
        return '\n'.join(lines)


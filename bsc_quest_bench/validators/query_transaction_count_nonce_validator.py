"""
Validator for query_transaction_count_nonce atomic problem.
Validates that the LLM correctly queries transaction count (nonce).
"""

from typing import Dict, Any


class QueryTransactionCountNonceValidator:
    """Validator for transaction count (nonce) query operations"""
    
    def __init__(self, query_address: str):
        """
        Initialize validator with query parameters.
        
        Args:
            query_address: Address to query nonce for
        """
        self.query_address = query_address.lower()
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the transaction count (nonce) query result.
        
        Scoring:
        - Query execution success: 40 points
        - Return format correctness: 30 points
        - Nonce validity: 30 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains reference nonce)
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
        
        # Get reference nonce from state_before (set by quest_executor)
        reference_nonce = state_before.get('reference_nonce', None)
        
        # Check 1: Query execution success (40 points)
        query_success = query_result.get('success', False)
        error_msg = query_result.get('error', '')
        
        if query_success:
            score += 40
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
        required_fields = ['nonce']
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
        
        # Check 3: Nonce validity (30 points)
        try:
            returned_nonce = data.get('nonce', -1)
            if isinstance(returned_nonce, str):
                returned_nonce = int(returned_nonce)
            else:
                returned_nonce = int(returned_nonce)
            
            validation_passed = True
            validation_messages = []
            
            # Nonce must be non-negative
            if returned_nonce < 0:
                validation_passed = False
                validation_messages.append(f'Nonce must be non-negative, got: {returned_nonce}')
            
            # If reference nonce is available, check they're reasonably close
            # Nonce should not differ by more than a few transactions
            if reference_nonce is not None and validation_passed:
                nonce_diff = abs(returned_nonce - reference_nonce)
                if nonce_diff > 10:
                    # This is a warning, but we'll still pass if nonce is valid
                    validation_messages.append(f'Nonce differs from reference by {nonce_diff}')
                
                # Check if we got both pending and latest states (bonus check)
                pending_nonce = data.get('nonce_pending', None)
                latest_nonce = data.get('nonce_latest', None)
                
                if pending_nonce is not None and latest_nonce is not None:
                    # Validate the relationship between pending and latest
                    if isinstance(pending_nonce, str):
                        pending_nonce = int(pending_nonce)
                    else:
                        pending_nonce = int(pending_nonce)
                    
                    if isinstance(latest_nonce, str):
                        latest_nonce = int(latest_nonce)
                    else:
                        latest_nonce = int(latest_nonce)
                    
                    if pending_nonce < latest_nonce:
                        validation_messages.append('Warning: pending nonce should be >= latest nonce')
                    else:
                        validation_messages.append(f'Good: Both pending ({pending_nonce}) and latest ({latest_nonce}) nonces provided')
            
            if validation_passed:
                score += 30
                message = f'Nonce is valid: {returned_nonce}'
                if validation_messages:
                    message += ' (' + '; '.join(validation_messages) + ')'
                checks.append({
                    'name': 'Nonce Validity',
                    'passed': True,
                    'message': message
                })
                feedback_parts.append("✅ Transaction count (nonce) queried correctly!")
            else:
                checks.append({
                    'name': 'Nonce Validity',
                    'passed': False,
                    'message': '; '.join(validation_messages)
                })
                feedback_parts.append(f"⚠️  Nonce validation issues")
        except (ValueError, KeyError, TypeError) as e:
            checks.append({
                'name': 'Nonce Validity',
                'passed': False,
                'message': f'Failed to parse nonce: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse nonce: {str(e)}")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! Transaction count (nonce) queried correctly!"
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


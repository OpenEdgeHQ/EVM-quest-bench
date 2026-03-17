"""
Validator for query_current_block_number atomic problem.
Validates that the LLM correctly queries the current block number.
"""

from typing import Dict, Any


class QueryCurrentBlockNumberValidator:
    """Validator for blockchain current block number query operations"""
    
    def __init__(self):
        """
        Initialize validator for current block number query.
        
        No parameters needed as block number is dynamic and always changing.
        """
        pass
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the current block number query result.
        
        Scoring:
        - Query execution success: 50 points
        - Return format correctness: 25 points
        - Block number validity: 25 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains reference block number)
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
        
        # Get reference block number from state_before (set by quest_executor)
        reference_block_number = state_before.get('reference_block_number', 0)
        
        # Check 1: Query execution success (50 points)
        query_success = query_result.get('success', False)
        error_msg = query_result.get('error', '')
        
        if query_success:
            score += 50
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
        
        # Check 2: Return format correctness (25 points)
        required_fields = ['block_number']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            score += 25
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
        
        # Check 3: Block number validity (25 points)
        try:
            returned_block_number = data.get('block_number', 0)
            if isinstance(returned_block_number, str):
                returned_block_number = int(returned_block_number)
            else:
                returned_block_number = int(returned_block_number)
            
            # Block number must be positive
            if returned_block_number <= 0:
                checks.append({
                    'name': 'Block Number Validity',
                    'passed': False,
                    'message': f'Block number must be positive, got: {returned_block_number}'
                })
                feedback_parts.append(f"⚠️  Invalid block number: {returned_block_number}")
            # Block number should be reasonably close to reference block (within 100 blocks)
            # This accounts for blocks mined during execution
            elif reference_block_number > 0 and abs(returned_block_number - reference_block_number) > 100:
                checks.append({
                    'name': 'Block Number Validity',
                    'passed': False,
                    'message': f'Block number seems incorrect - Expected around {reference_block_number}, Got: {returned_block_number}'
                })
                feedback_parts.append(f"⚠️  Block number mismatch")
            else:
                score += 25
                checks.append({
                    'name': 'Block Number Validity',
                    'passed': True,
                    'message': f'Block number is valid: {returned_block_number}'
                })
                feedback_parts.append("✅ Current block number queried correctly!")
        except (ValueError, KeyError, TypeError) as e:
            checks.append({
                'name': 'Block Number Validity',
                'passed': False,
                'message': f'Failed to parse block number: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse block number: {str(e)}")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! Current block number queried correctly!"
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


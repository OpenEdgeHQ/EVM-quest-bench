"""
Validator for query_nft_balance atomic problem.
Validates that the LLM correctly queries ERC721 NFT balance.
"""

from typing import Dict, Any


class QueryNFTBalanceValidator:
    """Validator for ERC721 NFT balance query operations"""
    
    def __init__(
        self,
        nft_address: str,
        query_address: str,
        expected_balance: int
    ):
        """
        Initialize validator with NFT balance query parameters.
        
        Args:
            nft_address: ERC721 NFT contract address
            query_address: Address to query balance for
            expected_balance: Expected NFT balance count
        """
        self.nft_address = nft_address.lower()
        self.query_address = query_address.lower()
        self.expected_balance = expected_balance
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the NFT balance query result.
        
        Scoring:
        - Query execution success: 40 points
        - Return format correctness: 30 points
        - Balance correctness: 30 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains actual balance if available)
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
        
        # Get expected balance from state_before if set by quest_executor
        expected_balance = state_before.get('nft_balance', self.expected_balance)
        
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
        required_fields = ['balance']
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
        
        # Check 3: Balance correctness (30 points)
        try:
            returned_balance = data.get('balance', 0)
            if isinstance(returned_balance, str):
                returned_balance = int(returned_balance)
            else:
                returned_balance = int(returned_balance)
            
            if returned_balance == expected_balance:
                score += 30
                checks.append({
                    'name': 'Balance Correctness',
                    'passed': True,
                    'message': f'NFT balance correct: {returned_balance} NFTs'
                })
                feedback_parts.append("✅ NFT balance queried correctly!")
            else:
                checks.append({
                    'name': 'Balance Correctness',
                    'passed': False,
                    'message': f'Balance mismatch - Expected: {expected_balance}, Got: {returned_balance}'
                })
                feedback_parts.append(f"⚠️  Balance mismatch")
        except (ValueError, KeyError, TypeError) as e:
            checks.append({
                'name': 'Balance Correctness',
                'passed': False,
                'message': f'Failed to parse balance: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse balance: {str(e)}")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! NFT balance queried correctly!"
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


"""
Validator for query_nft_owner atomic problem.
Validates that the LLM correctly queries ERC721 NFT owner using the ownerOf function.
"""

from typing import Dict, Any


class QueryNFTOwnerValidator:
    """Validator for ERC721 NFT owner query operations"""
    
    def __init__(
        self,
        nft_address: str,
        token_id: int,
        expected_owner: str
    ):
        """
        Initialize validator with NFT query parameters.
        
        Args:
            nft_address: ERC721 NFT contract address
            token_id: NFT token ID to query
            expected_owner: Expected owner address
        """
        self.nft_address = nft_address.lower()
        self.token_id = token_id
        self.expected_owner = expected_owner.lower()
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the NFT owner query result.
        
        Scoring:
        - Query execution success: 40 points
        - Return format correctness: 30 points
        - Owner address correctness: 30 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains actual owner if available)
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
        
        # Get expected owner from state_before if set by quest_executor
        expected_owner = state_before.get('nft_owner', self.expected_owner)
        
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
        required_fields = ['owner']
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
        
        # Check 3: Owner address correctness (30 points)
        try:
            returned_owner = data.get('owner', '').lower()
            
            if returned_owner == expected_owner:
                score += 30
                checks.append({
                    'name': 'Owner Address Correctness',
                    'passed': True,
                    'message': f'NFT owner correct: {returned_owner}'
                })
                feedback_parts.append("✅ NFT owner queried correctly!")
            else:
                checks.append({
                    'name': 'Owner Address Correctness',
                    'passed': False,
                    'message': f'Owner mismatch - Expected: {expected_owner}, Got: {returned_owner}'
                })
                feedback_parts.append(f"⚠️  Owner address mismatch")
        except (KeyError, TypeError) as e:
            checks.append({
                'name': 'Owner Address Correctness',
                'passed': False,
                'message': f'Failed to parse owner address: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse owner address: {str(e)}")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! NFT owner queried correctly!"
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


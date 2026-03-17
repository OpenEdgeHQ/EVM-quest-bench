"""
Validator for query_nft_token_uri atomic problem.
Validates that the LLM correctly queries ERC721 NFT token URI.
"""

from typing import Dict, Any


class QueryNFTTokenURIValidator:
    """Validator for ERC721 NFT token URI query operations"""
    
    def __init__(
        self,
        nft_address: str,
        token_id: int
    ):
        """
        Initialize validator with NFT query parameters.
        
        Args:
            nft_address: ERC721 NFT contract address
            token_id: NFT token ID to query
        """
        self.nft_address = nft_address.lower()
        self.token_id = token_id
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the NFT token URI query result.
        
        Scoring:
        - Query execution success: 40 points
        - Return format correctness: 30 points
        - Token URI format validation: 30 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains actual token URI if available)
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
        
        # Get expected token URI from state_before if set by quest_executor
        expected_token_uri = state_before.get('token_uri')
        
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
        required_fields = ['tokenURI']
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
        
        # Check 3: Token URI format validation (30 points)
        try:
            returned_token_uri = data.get('tokenURI', '')
            
            # Check if it's a non-empty string
            if isinstance(returned_token_uri, str) and len(returned_token_uri) > 0:
                # If we have expected token URI, check if it matches
                if expected_token_uri is not None:
                    if returned_token_uri == expected_token_uri:
                        score += 30
                        checks.append({
                            'name': 'Token URI Format Validation',
                            'passed': True,
                            'message': f'Token URI correct: {returned_token_uri[:100]}{"..." if len(returned_token_uri) > 100 else ""}'
                        })
                        feedback_parts.append("✅ Token URI queried correctly!")
                    else:
                        checks.append({
                            'name': 'Token URI Format Validation',
                            'passed': False,
                            'message': f'Token URI mismatch - Expected: {expected_token_uri[:50]}..., Got: {returned_token_uri[:50]}...'
                        })
                        feedback_parts.append(f"⚠️  Token URI mismatch")
                else:
                    # No expected value, just validate it's a non-empty string
                    score += 30
                    checks.append({
                        'name': 'Token URI Format Validation',
                        'passed': True,
                        'message': f'Token URI is valid non-empty string: {returned_token_uri[:100]}{"..." if len(returned_token_uri) > 100 else ""}'
                    })
                    feedback_parts.append("✅ Token URI format valid!")
            else:
                checks.append({
                    'name': 'Token URI Format Validation',
                    'passed': False,
                    'message': f'Token URI must be a non-empty string, got: {type(returned_token_uri).__name__}'
                })
                feedback_parts.append(f"❌ Invalid token URI format")
        except (KeyError, TypeError) as e:
            checks.append({
                'name': 'Token URI Format Validation',
                'passed': False,
                'message': f'Failed to parse token URI: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse token URI: {str(e)}")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! NFT token URI queried correctly!"
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


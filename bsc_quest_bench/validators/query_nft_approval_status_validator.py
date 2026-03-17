"""
Validator for query_nft_approval_status

Validates:
1. Query execution success
2. Return format (approved_address field)
3. Approved address correctness
"""

from typing import Dict, Any


class QueryNFTApprovalStatusValidator:
    """Validator for NFT approval status query"""
    
    def __init__(
        self,
        nft_address: str,
        nft_symbol: str,
        token_id: int,
        expected_approved_address: str
    ):
        """
        Initialize validator
        
        Args:
            nft_address: NFT contract address
            nft_symbol: NFT collection symbol
            token_id: Token ID to query
            expected_approved_address: Expected approved address
        """
        self.nft_address = nft_address.lower()
        self.nft_symbol = nft_symbol
        self.token_id = token_id
        self.expected_approved_address = expected_approved_address.lower()
        
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
            state_before: State before query (contains actual approved address)
            state_after: State after query (not used for queries)
            
        Returns:
            Validation result dictionary
        """
        result = {
            'passed': False,
            'score': 0,
            'max_score': 100,
            'checks': [],
            'feedback': ''
        }
        
        # Extract query result and actual value
        query_result = tx.get('query_result', {})
        actual_approved_address = state_before.get('approved_address', '0x0000000000000000000000000000000000000000')
        
        # Check 1: Query execution success (30 points)
        if query_result.get('success'):
            result['score'] += 30
            result['checks'].append({
                'name': 'Query Execution Success',
                'passed': True,
                'points': 30,
                'message': 'Query executed successfully'
            })
        else:
            result['checks'].append({
                'name': 'Query Execution Success',
                'passed': False,
                'points': 0,
                'message': f"Query failed: {query_result.get('error', 'Unknown error')}"
            })
            result['feedback'] = '❌ Query execution failed. Please check your code.'
            return result
        
        data = query_result.get('data', {})
        
        # Check 2: Return format (30 points)
        if 'approved_address' in data:
            result['score'] += 30
            result['checks'].append({
                'name': 'Return Format Correct',
                'passed': True,
                'points': 30,
                'message': f"Expected 'approved_address' field in result. Got: {list(data.keys())}"
            })
        else:
            result['checks'].append({
                'name': 'Return Format Correct',
                'passed': False,
                'points': 0,
                'message': f"Missing 'approved_address' field. Got: {list(data.keys())}"
            })
            result['feedback'] = "❌ Return format incorrect. Expected 'approved_address' field."
            return result
        
        # Check 3: Approved address correctness (40 points)
        returned_address = data.get('approved_address', '').lower()
        actual_approved_address = actual_approved_address.lower()
        expected_address = self.expected_approved_address.lower()
        
        # Normalize zero address
        zero_address = '0x0000000000000000000000000000000000000000'
        if returned_address == '0x0':
            returned_address = zero_address
        if actual_approved_address == '0x0':
            actual_approved_address = zero_address
        if expected_address == '0x0':
            expected_address = zero_address
        
        if returned_address == expected_address == actual_approved_address:
            result['score'] += 40
            result['checks'].append({
                'name': 'Approval Correctness',
                'passed': True,
                'points': 40,
                'message': f"Expected: {expected_address}, Got: {returned_address}"
            })
            result['passed'] = True
            result['feedback'] = '🎉 Congratulations! NFT approval status queried correctly!'
        else:
            result['checks'].append({
                'name': 'Approval Correctness',
                'passed': False,
                'points': 0,
                'message': f"Expected: {expected_address}, Got: {returned_address}, Actual: {actual_approved_address}"
            })
            result['feedback'] = f"❌ Approved address incorrect. Expected {expected_address}, but got {returned_address}"
        
        return result


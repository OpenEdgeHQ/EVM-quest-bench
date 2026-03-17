"""
ERC721 Approve Validator

Validate ERC721 NFT approve operation execution.
"""

from typing import Dict, Any


class ERC721ApproveValidator:
    """Validate ERC721 approval operation"""
    
    def __init__(
        self,
        nft_address: str,
        spender_address: str,
        token_id: int
    ):
        self.nft_address = nft_address.lower()
        self.spender_address = spender_address.lower()
        self.token_id = token_id
        
        # approve(address,uint256) function selector
        self.expected_selector = '0x095ea7b3'
        
        # Total 100 points
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate ERC721 approval transaction
        
        Checks:
        1. Transaction executed successfully (30 points)
        2. Approved address correctly set (50 points)
        3. Used function: approve function (correct selector)(20 points)
        """
        checks = []
        total_score = 0
        
        # 1. Validate transaction success (30 points)
        tx_status = receipt.get('status', 0)
        if tx_status == 1:
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'message': 'Transaction executed successfully',
                'score': 30
            })
            total_score += 30
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'message': f'Transaction failed with status: {tx_status}',
                'score': 30
            })
            # If transaction failed, return directly
            return {
                'passed': False,
                'score': 0,
                'max_score': self.max_score,
                'checks': checks,
                'details': {
                    'nft_address': self.nft_address,
                    'token_id': self.token_id,
                    'spender_address': self.spender_address,
                    'transaction_status': tx_status
                }
            }
        
        # 2. Validate approved address (40 points)
        approved_before = state_before.get('nft_approved', '').lower() if state_before.get('nft_approved') else None
        approved_after = state_after.get('nft_approved', '').lower() if state_after.get('nft_approved') else None
        
        if approved_after and approved_after == self.spender_address:
            checks.append({
                'name': 'Approval Check',
                'passed': True,
                'message': f'NFT #{self.token_id} correctly approved for {self.spender_address}',
                'score': 50,
                'details': {
                    'approved_before': approved_before,
                    'approved_after': approved_after,
                    'expected': self.spender_address
                }
            })
            total_score += 50
        else:
            checks.append({
                'name': 'Approval Check',
                'passed': False,
                'message': f'Approval not set correctly. Expected: {self.spender_address}, Got: {approved_after}',
                'score': 50,
                'details': {
                    'approved_before': approved_before,
                    'approved_after': approved_after,
                    'expected': self.spender_address
                }
            })
        
        # 3. Validate Used function: correct function selector (20 points)
        tx_data = tx.get('data', '') or tx.get('input', '')
        
        if isinstance(tx_data, bytes):
            tx_data = tx_data.hex()
        if isinstance(tx_data, str) and tx_data.startswith('0x'):
            tx_data = tx_data[2:]
        
        # Extract function selector (First 4 bytes = 8 hex chars)
        if len(tx_data) >= 8:
            actual_selector = '0x' + tx_data[:8]
            
            if actual_selector.lower() == self.expected_selector.lower():
                checks.append({
                    'name': 'Function Selector',
                    'passed': True,
                    'message': f'Correct approve selector: {actual_selector}',
                    'score': 20,
                    'details': {
                        'expected': self.expected_selector,
                        'actual': actual_selector
                    }
                })
                total_score += 20
            else:
                checks.append({
                    'name': 'Function Selector',
                    'passed': False,
                    'message': f'Incorrect function selector. Expected approve ({self.expected_selector}), got {actual_selector}',
                    'score': 20,
                    'details': {
                        'expected': self.expected_selector,
                        'actual': actual_selector
                    }
                })
        else:
            checks.append({
                'name': 'Function Selector',
                'passed': False,
                'message': 'Transaction data too short or missing',
                'score': 20
            })
        
        # Aggregate results
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': self.max_score,
            'checks': checks,
            'details': {
                'nft_address': self.nft_address,
                'token_id': self.token_id,
                'spender_address': self.spender_address,
                'approved_before': approved_before,
                'approved_after': approved_after,
                'expected_selector': self.expected_selector,
                'actual_selector': actual_selector if len(tx_data) >= 8 else 'N/A'
            }
        }


"""
ERC721 Safe Transfer Validator

Validate ERC721 NFT safe transfer execution.
"""

from typing import Dict, Any


class ERC721SafeTransferValidator:
    """Validate ERC721 safe transfer"""
    
    def __init__(
        self,
        nft_address: str,
        to_address: str,
        token_id: int
    ):
        self.nft_address = nft_address.lower()
        self.to_address = to_address.lower()
        self.token_id = token_id
        
        # safeTransferFrom(address,address,uint256) function selector
        self.expected_selector = '0x42842e0e'
        
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
        Validate ERC721 safe transfer transaction
        
        Checks:
        1. Transaction executed successfully
        2. NFT ownership correctly transferred
        3. Used function: safeTransferFrom function (correct selector)
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
                    'to_address': self.to_address,
                    'transaction_status': tx_status
                }
            }
        
        # 2. Validate NFT ownership transfer (40 points)
        owner_before = state_before.get('nft_owner', '').lower() if state_before.get('nft_owner') else None
        owner_after = state_after.get('nft_owner', '').lower() if state_after.get('nft_owner') else None
        
        if owner_after and owner_after == self.to_address:
            checks.append({
                'name': 'NFT Ownership Transfer',
                'passed': True,
                'message': f'NFT #{self.token_id} correctly transferred to {self.to_address}',
                'score': 40,
                'details': {
                    'owner_before': owner_before,
                    'owner_after': owner_after,
                    'expected': self.to_address
                }
            })
            total_score += 40
        else:
            checks.append({
                'name': 'NFT Ownership Transfer',
                'passed': False,
                'message': f'NFT ownership not transferred correctly. Expected: {self.to_address}, Got: {owner_after}',
                'score': 40,
                'details': {
                    'owner_before': owner_before,
                    'owner_after': owner_after,
                    'expected': self.to_address
                }
            })
        
        # 3. Validate Used function: correct function selector (30 points)
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
                    'message': f'Correct safeTransferFrom selector: {actual_selector}',
                    'score': 30,
                    'details': {
                        'expected': self.expected_selector,
                        'actual': actual_selector
                    }
                })
                total_score += 30
            else:
                checks.append({
                    'name': 'Function Selector',
                    'passed': False,
                    'message': f'Incorrect function selector. Expected safeTransferFrom ({self.expected_selector}), got {actual_selector}',
                    'score': 30,
                    'details': {
                        'expected': self.expected_selector,
                        'actual': actual_selector,
                        'note': 'Should use safeTransferFrom(address,address,uint256), not transferFrom'
                    }
                })
        else:
            checks.append({
                'name': 'Function Selector',
                'passed': False,
                'message': 'Transaction data too short or missing',
                'score': 30
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
                'expected_recipient': self.to_address,
                'owner_before': owner_before,
                'owner_after': owner_after,
                'expected_selector': self.expected_selector,
                'actual_selector': actual_selector if len(tx_data) >= 8 else 'N/A'
            }
        }


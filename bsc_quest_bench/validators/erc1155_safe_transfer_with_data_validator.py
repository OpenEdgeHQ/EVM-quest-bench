"""
ERC1155 Safe Transfer with Data Validator

Validate ERC1155 safe transfer operation with data parameter.
"""

from typing import Dict, Any


class ERC1155SafeTransferWithDataValidator:
    """Validate ERC1155 safeTransferFrom operation with data"""
    
    def __init__(
        self,
        nft_address: str,
        to_address: str,
        token_id: int,
        amount: int,
        data_message: str
    ):
        self.nft_address = nft_address.lower()
        self.to_address = to_address.lower()
        self.token_id = token_id
        self.expected_amount = amount
        self.data_message = data_message
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate ERC1155 transfer transaction with data
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result dictionary
        
        Checks:
        1. Transaction executed successfully (30 points)
        2. Correct contract called: ERC1155 contract (15 points)
        3. Used function: safeTransferFrom (15 points)
        4. Data parameter not empty (10 points)
        5. Sender balance decreased, receiver balance increased (30 points)
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
                    'to_address': self.to_address,
                    'token_id': self.token_id,
                    'expected_amount': self.expected_amount,
                    'transaction_status': tx_status
                }
            }
        
        # 2. ValidateCorrect contract called: ERC1155 contract (15 points)
        tx_to = tx.get('to', '').lower()
        if tx_to == self.nft_address:
            checks.append({
                'name': 'Contract Address',
                'passed': True,
                'message': f'Correct ERC1155 contract: {tx_to}',
                'score': 15
            })
            total_score += 15
        else:
            checks.append({
                'name': 'Contract Address',
                'passed': False,
                'message': f'Wrong contract. Expected: {self.nft_address}, Got: {tx_to}',
                'score': 15
            })
        
        # 3. Validate Used function: safeTransferFrom (20 points)
        tx_data = tx.get('data', '') or tx.get('input', '')
        
        if isinstance(tx_data, bytes):
            tx_data = tx_data.hex()
        if isinstance(tx_data, str) and tx_data.startswith('0x'):
            tx_data = tx_data[2:]
        
        # safeTransferFrom(address,address,uint256,uint256,bytes) function selector
        expected_selector = '0xf242432a'
        actual_selector = 'N/A'
        
        if len(tx_data) >= 8:
            actual_selector = '0x' + tx_data[:8]
            
            if actual_selector.lower() == expected_selector.lower():
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'message': f'Correct safeTransferFrom selector: {actual_selector}',
                    'score': 15,
                    'details': {
                        'expected': expected_selector,
                        'actual': actual_selector
                    }
                })
                total_score += 15
            else:
                checks.append({
                    'name': 'Function Signature',
                    'passed': False,
                    'message': f'Incorrect function selector. Expected safeTransferFrom ({expected_selector}), got {actual_selector}',
                    'score': 15,
                    'details': {
                        'expected': expected_selector,
                        'actual': actual_selector
                    }
                })
        else:
            checks.append({
                'name': 'Function Signature',
                'passed': False,
                'message': 'Transaction data too short or missing',
                'score': 20
            })
        
        # 4. Validate data parameter not empty (10 points)
        # safeTransferFrom encoding format:
        # selector (4 bytes) + from (32 bytes) + to (32 bytes) + id (32 bytes) + amount (32 bytes) + data offset (32 bytes) + data length + data
        # If data is not empty, transaction data should be longer than 4 + 32*5 = 164 bytes (82 hex chars)
        data_check_passed = False
        if len(tx_data) > 200:  # Allow margin, should be significantly longer if data exists
            data_check_passed = True
            checks.append({
                'name': 'Data Parameter',
                'passed': True,
                'message': 'Data parameter is non-empty',
                'score': 10,
                'details': {
                    'tx_data_length': len(tx_data),
                    'note': 'Transaction includes additional data bytes'
                }
            })
            total_score += 10
        else:
            checks.append({
                'name': 'Data Parameter',
                'passed': False,
                'message': 'Data parameter appears to be empty or missing',
                'score': 10,
                'details': {
                    'tx_data_length': len(tx_data),
                    'note': 'Expected data parameter to be non-empty'
                }
            })
        
        # 5. Validate balance change (30 points)
        sender_balance_before = state_before.get('erc1155_balance', 0)
        sender_balance_after = state_after.get('erc1155_balance', 0)
        recipient_balance_before = state_before.get('target_erc1155_balance', 0)
        recipient_balance_after = state_after.get('target_erc1155_balance', 0)
        
        sender_decrease = sender_balance_before - sender_balance_after
        recipient_increase = recipient_balance_after - recipient_balance_before
        
        balance_check_passed = (
            sender_decrease == self.expected_amount and
            recipient_increase == self.expected_amount
        )
        
        if balance_check_passed:
            checks.append({
                'name': 'Balance Transfer',
                'passed': True,
                'message': f'Balances changed correctly: -{self.expected_amount} from sender, +{self.expected_amount} to recipient',
                'score': 30,
                'details': {
                    'sender_balance_before': sender_balance_before,
                    'sender_balance_after': sender_balance_after,
                    'sender_decrease': sender_decrease,
                    'recipient_balance_before': recipient_balance_before,
                    'recipient_balance_after': recipient_balance_after,
                    'recipient_increase': recipient_increase,
                    'expected_amount': self.expected_amount
                }
            })
            total_score += 30
        else:
            checks.append({
                'name': 'Balance Transfer',
                'passed': False,
                'message': f'Balance mismatch. Expected: {self.expected_amount}, Sender decrease: {sender_decrease}, Recipient increase: {recipient_increase}',
                'score': 30,
                'details': {
                    'sender_balance_before': sender_balance_before,
                    'sender_balance_after': sender_balance_after,
                    'sender_decrease': sender_decrease,
                    'recipient_balance_before': recipient_balance_before,
                    'recipient_balance_after': recipient_balance_after,
                    'recipient_increase': recipient_increase,
                    'expected_amount': self.expected_amount
                }
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
                'to_address': self.to_address,
                'token_id': self.token_id,
                'expected_amount': self.expected_amount,
                'data_message': self.data_message,
                'sender_balance_before': sender_balance_before,
                'sender_balance_after': sender_balance_after,
                'recipient_balance_before': recipient_balance_before,
                'recipient_balance_after': recipient_balance_after,
                'actual_selector': actual_selector,
                'tx_data_length': len(tx_data)
            }
        }


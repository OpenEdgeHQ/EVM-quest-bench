"""
ERC1363 Transfer with Callback Validator

Validate ERC1363 token transferAndCall operation execution.
"""

from typing import Dict, Any
from decimal import Decimal


class ERC20TransferWithCallback1363Validator:
    """Validate ERC1363 transferAndCall operation"""
    
    def __init__(
        self,
        token_address: str,
        to_address: str,
        amount: float,
        token_decimals: int = 18
    ):
        self.token_address = token_address.lower()
        self.to_address = to_address.lower()
        
        # Use Decimal for precise calculation
        self.expected_amount = int(Decimal(str(amount)) * Decimal(10 ** token_decimals))
        self.token_decimals = token_decimals
        
        # transferAndCall(address,uint256,bytes) function selector (use 3-param version to avoid overload issues)
        self.expected_selector = '0x1296ee62'
        
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
        Validate ERC1363 transferAndCall transaction
        
        Checks:
        1. Transaction executed successfully (30%)
        2. Sender token balance correctly decreased (40%)
        3. Receiver token balance correctly increased (20%)
        4. Used function: transferAndCall function (correct selector)(10%)
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
                    'token_address': self.token_address,
                    'to_address': self.to_address,
                    'expected_amount': self.expected_amount,
                    'transaction_status': tx_status
                }
            }
        
        # 2. Validate sender token balance decrease (40 points)
        sender_balance_before = state_before.get('token_balance', 0)
        sender_balance_after = state_after.get('token_balance', 0)
        actual_decrease = sender_balance_before - sender_balance_after
        
        if actual_decrease == self.expected_amount:
            checks.append({
                'name': 'Sender Token Balance Decrease',
                'passed': True,
                'message': f'Sender balance correctly decreased by {self.expected_amount} units',
                'score': 40,
                'details': {
                    'balance_before': sender_balance_before,
                    'balance_after': sender_balance_after,
                    'actual_decrease': actual_decrease,
                    'expected_decrease': self.expected_amount
                }
            })
            total_score += 40
        else:
            checks.append({
                'name': 'Sender Token Balance Decrease',
                'passed': False,
                'message': f'Balance decrease mismatch. Expected: {self.expected_amount}, Got: {actual_decrease}',
                'score': 40,
                'details': {
                    'balance_before': sender_balance_before,
                    'balance_after': sender_balance_after,
                    'actual_decrease': actual_decrease,
                    'expected_decrease': self.expected_amount
                }
            })
        
        # 3. Validate receiver token balance increase (20 points)
        receiver_balance_before = state_before.get('target_token_balance', 0)
        receiver_balance_after = state_after.get('target_token_balance', 0)
        actual_increase = receiver_balance_after - receiver_balance_before
        
        if actual_increase == self.expected_amount:
            checks.append({
                'name': 'Receiver Token Balance Increase',
                'passed': True,
                'message': f'Receiver balance correctly increased by {self.expected_amount} units',
                'score': 20,
                'details': {
                    'balance_before': receiver_balance_before,
                    'balance_after': receiver_balance_after,
                    'actual_increase': actual_increase,
                    'expected_increase': self.expected_amount
                }
            })
            total_score += 20
        else:
            checks.append({
                'name': 'Receiver Token Balance Increase',
                'passed': False,
                'message': f'Balance increase mismatch. Expected: {self.expected_amount}, Got: {actual_increase}',
                'score': 20,
                'details': {
                    'balance_before': receiver_balance_before,
                    'balance_after': receiver_balance_after,
                    'actual_increase': actual_increase,
                    'expected_increase': self.expected_amount
                }
            })
        
        # 4. Validate Used function: correct function selector (10 points)
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
                    'message': f'Correct transferAndCall selector: {actual_selector}',
                    'score': 10,
                    'details': {
                        'expected': self.expected_selector,
                        'actual': actual_selector
                    }
                })
                total_score += 10
            else:
                checks.append({
                    'name': 'Function Selector',
                    'passed': False,
                    'message': f'Incorrect function selector. Expected transferAndCall ({self.expected_selector}), got {actual_selector}',
                    'score': 10,
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
                'score': 10
            })
        
        # Aggregate results
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'passed': all_passed,
            'score': total_score,
            'max_score': self.max_score,
            'checks': checks,
            'details': {
                'token_address': self.token_address,
                'to_address': self.to_address,
                'expected_amount': self.expected_amount,
                'sender_balance_before': sender_balance_before,
                'sender_balance_after': sender_balance_after,
                'receiver_balance_before': receiver_balance_before,
                'receiver_balance_after': receiver_balance_after,
                'expected_selector': self.expected_selector,
                'actual_selector': actual_selector if len(tx_data) >= 8 else 'N/A'
            }
        }


"""
ERC20 Burn Validator

Validates that ERC20 tokens were successfully burned (destroyed) by transferring to zero address
"""

from typing import Dict, Any


class ERC20BurnValidator:
    """Validator for ERC20 token burn transactions"""
    
    def __init__(self, token_address: str, amount: float, token_decimals: int = 18):
        """
        Initialize validator
        
        Args:
            token_address: ERC20 token contract address
            amount: Expected burn amount (in tokens, not wei)
            token_decimals: Token decimal places (default 18)
        """
        from decimal import Decimal
        
        self.expected_token = token_address.lower()
        # Convert amount to smallest unit (wei equivalent for tokens)
        self.expected_amount = int(Decimal(str(amount)) * Decimal(10**token_decimals))
        self.token_decimals = token_decimals
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the transaction execution results
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: Blockchain state before transaction
            state_after: Blockchain state after transaction
            
        Returns:
            Validation results including score and details
        """
        score = 0
        details = {}
        checks = []
        
        # Check 1: Transaction success (30 points)
        tx_success = receipt.get('status') == 1
        if tx_success:
            score += 30
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'points': 30,
                'message': 'Transaction executed successfully'
            })
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'points': 0,
                'message': f"Transaction failed with status: {receipt.get('status')}"
            })
            return {
                'score': score,
                'max_score': self.max_score,
                'passed': False,
                'checks': checks,
                'details': details
            }
        
        # Check 2: Token contract address correct (20 points)
        actual_to = tx.get('to', '').lower()
        contract_correct = actual_to == self.expected_token
        
        if contract_correct:
            score += 20
            checks.append({
                'name': 'Token Contract',
                'passed': True,
                'points': 20,
                'message': f'Correct token contract: {self.expected_token}'
            })
        else:
            checks.append({
                'name': 'Token Contract',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_token}, Got: {actual_to}'
            })
        
        details['expected_token'] = self.expected_token
        details['actual_to'] = actual_to
        
        # Check 3: Function signature and zero address (20 points)
        # ERC20 transfer function selector: 0xa9059cbb (keccak256("transfer(address,uint256)"))
        # Zero address for burn: 0x0000000000000000000000000000000000000000
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:
            function_selector = tx_data[:10].lower()
            expected_selector = '0xa9059cbb'  # transfer(address,uint256)
            
            if function_selector == expected_selector:
                # Check if recipient is zero address (burn address)
                if len(tx_data) >= 74:  # 0x(2) + selector(8) + address(64) = 74
                    to_address_hex = tx_data[10:74]
                    to_address = '0x' + to_address_hex[-40:].lower()
                    zero_address = '0x0000000000000000000000000000000000000000'
                    
                    if to_address == zero_address:
                        score += 20
                        checks.append({
                            'name': 'Function Signature & Zero Address',
                            'passed': True,
                            'points': 20,
                            'message': 'Correct transfer to zero address (burn)'
                        })
                    else:
                        checks.append({
                            'name': 'Function Signature & Zero Address',
                            'passed': False,
                            'points': 0,
                            'message': f'Transfer to wrong address: {to_address}, expected zero address'
                        })
                    
                    details['transfer_to'] = to_address
                    
                    # Decode amount from data
                    try:
                        if len(tx_data) >= 138:  # 0x(2) + selector(8) + address(64) + amount(64) = 138
                            amount_hex = tx_data[74:138]
                            amount_value = int(amount_hex, 16)
                            details['decoded_amount'] = amount_value
                    except Exception as e:
                        details['decode_error'] = str(e)
                else:
                    checks.append({
                        'name': 'Function Signature & Zero Address',
                        'passed': False,
                        'points': 0,
                        'message': 'Transaction data too short to decode'
                    })
            else:
                checks.append({
                    'name': 'Function Signature & Zero Address',
                    'passed': False,
                    'points': 0,
                    'message': f'Expected transfer function: {expected_selector}, Got: {function_selector}'
                })
        else:
            checks.append({
                'name': 'Function Signature & Zero Address',
                'passed': False,
                'points': 0,
                'message': 'No data field or too short'
            })
        
        details['function_selector'] = tx_data[:10] if tx_data else None
        
        # Check 4: Token balance decreased (30 points)
        balance_before = state_before.get('token_balance', 0)
        balance_after = state_after.get('token_balance', 0)
        balance_decrease = balance_before - balance_after
        
        # Allow small tolerance for potential rounding
        tolerance = int(self.expected_amount * 0.001) or 1
        balance_correct = abs(balance_decrease - self.expected_amount) <= tolerance
        
        if balance_correct:
            score += 30
            checks.append({
                'name': 'Token Balance Decrease',
                'passed': True,
                'points': 30,
                'message': f'Token balance decreased by {balance_decrease} ({balance_decrease / 10**self.token_decimals:.6f})'
            })
        else:
            checks.append({
                'name': 'Token Balance Decrease',
                'passed': False,
                'points': 0,
                'message': f'Expected decrease: {self.expected_amount}, Got: {balance_decrease}'
            })
        
        details['balance_before'] = balance_before
        details['balance_after'] = balance_after
        details['balance_decrease'] = balance_decrease
        details['expected_burn'] = self.expected_amount
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }


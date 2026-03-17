"""
ERC20 Transfer Max Amount Validator

Validates that the entire ERC20 token balance was transferred
"""

from typing import Dict, Any


class ERC20TransferMaxAmountValidator:
    """Validator for ERC20 maximum amount transfer"""
    
    def __init__(self, token_address: str, to_address: str, token_decimals: int = 18):
        """
        Initialize validator
        
        Args:
            token_address: ERC20 token contract address
            to_address: Expected recipient address
            token_decimals: Token decimal places (default 18)
        """
        self.expected_token = token_address.lower()
        self.expected_recipient = to_address.lower()
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
        
        # Check 3: Function signature (10 points)
        # ERC20 transfer function selector: 0xa9059cbb (keccak256("transfer(address,uint256)"))
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:
            function_selector = tx_data[:10].lower()
            expected_selector = '0xa9059cbb'  # transfer(address,uint256)
            
            if function_selector == expected_selector:
                score += 10
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 10,
                    'message': 'Correct ERC20 transfer function signature'
                })
                
                # Decode parameters from data
                try:
                    if len(tx_data) >= 138:  # 0x(2) + selector(8) + to(64) + amount(64) = 138
                        to_hex = tx_data[10:74]  # Next 64 chars (32 bytes)
                        amount_hex = tx_data[74:138]  # Next 64 chars (32 bytes)
                        
                        # Extract address (last 40 hex chars of the 64 char field)
                        to_addr = '0x' + to_hex[-40:].lower()
                        amount_value = int(amount_hex, 16)
                        
                        details['decoded_to'] = to_addr
                        details['decoded_amount'] = amount_value
                        
                        # Verify recipient address
                        if to_addr == self.expected_recipient:
                            details['recipient_address_correct'] = True
                        else:
                            details['recipient_address_correct'] = False
                            details['recipient_mismatch'] = f'Expected: {self.expected_recipient}, Got: {to_addr}'
                except Exception as e:
                    details['decode_error'] = str(e)
            else:
                checks.append({
                    'name': 'Function Signature',
                    'passed': False,
                    'points': 0,
                    'message': f'Expected: {expected_selector}, Got: {function_selector}'
                })
        else:
            checks.append({
                'name': 'Function Signature',
                'passed': False,
                'points': 0,
                'message': 'No data field or too short'
            })
        
        details['function_selector'] = tx_data[:10] if tx_data else None
        
        # Check 4: Maximum amount transferred (20 points)
        # Transfer amount should equal the initial balance
        balance_before = state_before.get('token_balance', 0)
        balance_after = state_after.get('token_balance', 0)
        
        # The transferred amount (from balance decrease)
        actual_transferred = balance_before - balance_after
        
        # Expected max transfer = entire balance
        expected_max_transfer = balance_before
        
        # Allow small tolerance (0.1% or 1 token unit, whichever is larger)
        tolerance = max(int(expected_max_transfer * 0.001), 1)
        transfer_correct = abs(actual_transferred - expected_max_transfer) <= tolerance
        
        if transfer_correct:
            score += 20
            checks.append({
                'name': 'Maximum Amount Transferred',
                'passed': True,
                'points': 20,
                'message': f'Transferred entire balance: {actual_transferred / 10**self.token_decimals:.6f} tokens'
            })
        else:
            checks.append({
                'name': 'Maximum Amount Transferred',
                'passed': False,
                'points': 0,
                'message': f'Expected: {expected_max_transfer / 10**self.token_decimals:.6f} tokens, Transferred: {actual_transferred / 10**self.token_decimals:.6f} tokens'
            })
        
        details['balance_before'] = balance_before
        details['expected_max_transfer'] = expected_max_transfer
        details['actual_transferred'] = actual_transferred
        
        # Check 5: Sender balance zero or minimal (20 points)
        # After transferring max amount, balance should be 0 or very close to 0
        # Allow up to 0.01 tokens remaining (10^(decimals-2))
        max_remaining = 10**(self.token_decimals - 2)
        
        balance_minimal = balance_after <= max_remaining
        
        if balance_minimal:
            score += 20
            checks.append({
                'name': 'Sender Balance Minimal',
                'passed': True,
                'points': 20,
                'message': f'Sender token balance minimal: {balance_after / 10**self.token_decimals:.10f} tokens (< 0.01)'
            })
        else:
            checks.append({
                'name': 'Sender Balance Minimal',
                'passed': False,
                'points': 0,
                'message': f'Sender balance too high: {balance_after / 10**self.token_decimals:.6f} tokens (should be < 0.01)'
            })
        
        details['balance_after'] = balance_after
        details['max_remaining_allowed'] = max_remaining
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }


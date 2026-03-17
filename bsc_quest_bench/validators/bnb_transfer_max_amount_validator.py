"""
BNB Transfer Max Amount Validator

Validates that maximum BNB amount (balance - gas) was transferred
"""

from typing import Dict, Any


class BNBTransferMaxAmountValidator:
    """Validator for BNB maximum amount transfer"""
    
    def __init__(self, to_address: str):
        """
        Initialize validator
        
        Args:
            to_address: Expected recipient address
        """
        self.expected_recipient = to_address.lower()
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
        
        # Check 2: Recipient address correct (20 points)
        actual_to = tx.get('to', '').lower()
        recipient_correct = actual_to == self.expected_recipient
        
        if recipient_correct:
            score += 20
            checks.append({
                'name': 'Recipient Address',
                'passed': True,
                'points': 20,
                'message': f'Correct recipient: {self.expected_recipient}'
            })
        else:
            checks.append({
                'name': 'Recipient Address',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_recipient}, Got: {actual_to}'
            })
        
        details['expected_recipient'] = self.expected_recipient
        details['actual_to'] = actual_to
        
        # Check 3: Maximum amount transferred (30 points)
        # Max amount = balance_before - gas_cost
        balance_before = state_before.get('balance', 0)
        balance_after = state_after.get('balance', 0)
        
        gas_used = receipt.get('gasUsed', 0)
        gas_price = receipt.get('effectiveGasPrice', 0)
        gas_cost = gas_used * gas_price
        
        # The actual transferred amount
        actual_transferred = tx.get('value', 0)
        
        # Expected max transfer = balance - gas cost
        expected_max_transfer = balance_before - gas_cost
        
        # Allow small tolerance (0.1% or 1000 wei, whichever is larger)
        tolerance = max(int(expected_max_transfer * 0.001), 1000)
        transfer_correct = abs(actual_transferred - expected_max_transfer) <= tolerance
        
        if transfer_correct:
            score += 30
            checks.append({
                'name': 'Maximum Amount Transferred',
                'passed': True,
                'points': 30,
                'message': f'Transferred max amount: {actual_transferred / 10**18:.6f} BNB (balance: {balance_before / 10**18:.6f} BNB, gas: {gas_cost / 10**18:.6f} BNB)'
            })
        else:
            checks.append({
                'name': 'Maximum Amount Transferred',
                'passed': False,
                'points': 0,
                'message': f'Expected: {expected_max_transfer / 10**18:.6f} BNB, Transferred: {actual_transferred / 10**18:.6f} BNB'
            })
        
        details['balance_before'] = balance_before
        details['gas_cost'] = gas_cost
        details['expected_max_transfer'] = expected_max_transfer
        details['actual_transferred'] = actual_transferred
        
        # Check 4: Sender balance minimal (20 points)
        # After transferring max amount, balance should be close to 0
        # Only dust should remain (less than 0.0001 BNB = 100000000000000 wei)
        max_remaining = 100000000000000  # 0.0001 BNB
        
        balance_minimal = balance_after <= max_remaining
        
        if balance_minimal:
            score += 20
            checks.append({
                'name': 'Sender Balance Minimal',
                'passed': True,
                'points': 20,
                'message': f'Sender balance minimal: {balance_after / 10**18:.10f} BNB (< 0.0001 BNB)'
            })
        else:
            checks.append({
                'name': 'Sender Balance Minimal',
                'passed': False,
                'points': 0,
                'message': f'Sender balance too high: {balance_after / 10**18:.6f} BNB (should be < 0.0001 BNB)'
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


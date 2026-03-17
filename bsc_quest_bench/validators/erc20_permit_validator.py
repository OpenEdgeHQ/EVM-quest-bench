"""
ERC20 Permit Validator (EIP-2612)

Validates that the permit function correctly sets token allowance using signature-based approval.
"""

from typing import Dict, Any
from decimal import Decimal


class ERC20PermitValidator:
    """Validator for EIP-2612 permit operations"""
    
    def __init__(
        self,
        token_address: str,
        owner_address: str,
        spender_address: str,
        value: float,
        token_decimals: int = 18
    ):
        self.token_address = token_address.lower()
        self.owner_address = owner_address.lower()
        self.spender_address = spender_address.lower()
        
        # Use Decimal for precise calculation
        self.expected_allowance = int(Decimal(str(value)) * Decimal(10 ** token_decimals))
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
        Validate EIP-2612 permit transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result dictionary
            
        Checks:
        1. Transaction success (40%)
        2. Allowance correctly set (60%)
        """
        
        checks = []
        score = 0
        details = {
            'token_address': self.token_address,
            'owner_address': self.owner_address,
            'spender_address': self.spender_address,
            'expected_allowance': self.expected_allowance
        }
        
        # Check 1: Transaction success (40 points)
        tx_success = receipt.get('status') == 1
        if tx_success:
            score += 40
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'points': 40,
                'message': 'Permit transaction executed successfully'
            })
        else:
            checks.append({
                'name': 'Transaction Success',
                'passed': False,
                'points': 0,
                'message': f"Transaction failed with status: {receipt.get('status')}"
            })
            # Early return on transaction failure
            return {
                'score': score,
                'max_score': self.max_score,
                'passed': False,
                'checks': checks,
                'details': details
            }
        
        # Check 2: Allowance correctly set (60 points)
        # Get allowance from state_after (should be queried by executor)
        actual_allowance = state_after.get('allowance', 0)
        details['allowance_before'] = state_before.get('allowance', 0)
        details['allowance_after'] = actual_allowance
        
        if actual_allowance == self.expected_allowance:
            score += 60
            checks.append({
                'name': 'Allowance Set Correctly',
                'passed': True,
                'points': 60,
                'message': f'Allowance correctly set to {self.expected_allowance} units',
                'details': {
                    'expected': self.expected_allowance,
                    'actual': actual_allowance
                }
            })
        else:
            checks.append({
                'name': 'Allowance Set Correctly',
                'passed': False,
                'points': 0,
                'message': f'Allowance mismatch. Expected: {self.expected_allowance}, Got: {actual_allowance}',
                'details': {
                    'expected': self.expected_allowance,
                    'actual': actual_allowance
                }
            })
        
        # Determine overall pass/fail
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': all_passed,
            'checks': checks,
            'details': details
        }


"""
WBNB Deposit Validator

Validates that BNB was successfully deposited into the WBNB contract
"""

from typing import Dict, Any


class WBNBDepositValidator:
    """Validator for WBNB deposit transactions"""
    
    def __init__(self, wbnb_address: str, amount: float):
        """
        Initialize validator
        
        Args:
            wbnb_address: WBNB contract address
            amount: Expected deposit amount in BNB (float)
        """
        from decimal import Decimal
        
        self.expected_wbnb = wbnb_address.lower()
        # Convert BNB to wei
        self.expected_amount = int(Decimal(str(amount)) * Decimal(10**18))
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
        
        # Check 2: Contract address correct (20 points)
        actual_to = tx.get('to', '').lower()
        contract_correct = actual_to == self.expected_wbnb
        
        if contract_correct:
            score += 20
            checks.append({
                'name': 'Contract Address',
                'passed': True,
                'points': 20,
                'message': f'Correct WBNB contract: {self.expected_wbnb}'
            })
        else:
            checks.append({
                'name': 'Contract Address',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_wbnb}, Got: {actual_to}'
            })
        
        details['expected_wbnb'] = self.expected_wbnb
        details['actual_to'] = actual_to
        
        # Check 3: Function signature (20 points)
        # WBNB deposit function selector: 0xd0e30db0 (keccak256("deposit()"))
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:
            function_selector = tx_data[:10].lower()
            expected_selector = '0xd0e30db0'  # deposit()
            
            if function_selector == expected_selector:
                score += 20
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 20,
                    'message': 'Correct WBNB deposit function signature'
                })
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
        
        # Check 4: Deposit amount correct (20 points)
        actual_value = int(tx.get('value', 0))
        
        # Allow small tolerance
        tolerance = int(self.expected_amount * 0.001)
        amount_correct = abs(actual_value - self.expected_amount) <= tolerance
        
        if amount_correct:
            score += 20
            checks.append({
                'name': 'Deposit Amount',
                'passed': True,
                'points': 20,
                'message': f'Correct amount: {actual_value} wei ({actual_value / 10**18:.6f} BNB)'
            })
        else:
            checks.append({
                'name': 'Deposit Amount',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_amount} wei, Got: {actual_value} wei'
            })
        
        details['expected_amount'] = self.expected_amount
        details['actual_amount'] = actual_value
        
        # Check 5: WBNB token balance increased (10 points)
        wbnb_balance_before = state_before.get('token_balance', 0)
        wbnb_balance_after = state_after.get('token_balance', 0)
        balance_increase = wbnb_balance_after - wbnb_balance_before
        
        balance_correct = abs(balance_increase - self.expected_amount) <= tolerance
        
        if balance_correct:
            score += 10
            checks.append({
                'name': 'WBNB Balance Increase',
                'passed': True,
                'points': 10,
                'message': f'WBNB balance increased by {balance_increase} wei'
            })
        else:
            checks.append({
                'name': 'WBNB Balance Increase',
                'passed': False,
                'points': 0,
                'message': f'Expected increase: {self.expected_amount} wei, Got: {balance_increase} wei'
            })
        
        details['wbnb_balance_before'] = wbnb_balance_before
        details['wbnb_balance_after'] = wbnb_balance_after
        details['balance_increase'] = balance_increase
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }


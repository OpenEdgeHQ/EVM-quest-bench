"""
Contract Payable Fallback Validator

Validates that BNB is sent directly to a contract (triggering fallback/receive)
"""

from typing import Dict, Any


class ContractPayableFallbackValidator:
    """Validator for payable fallback/receive function calls"""
    
    def __init__(self, contract_address: str, amount: float):
        """
        Initialize validator
        
        Args:
            contract_address: Contract address with payable fallback/receive
            amount: Expected BNB amount to send
        """
        self.expected_contract = contract_address.lower()
        self.expected_amount = amount
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the payable fallback transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: Blockchain state before transaction
            state_after: Blockchain state after transaction
            
        Returns:
            Validation results including score and details
        """
        checks = []
        score = 0
        details = {}
        
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
        contract_correct = actual_to == self.expected_contract
        
        if contract_correct:
            score += 20
            checks.append({
                'name': 'Contract Address',
                'passed': True,
                'points': 20,
                'message': f'Correct contract: {self.expected_contract}'
            })
        else:
            checks.append({
                'name': 'Contract Address',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_contract}, Got: {actual_to}'
            })
        
        details['expected_contract'] = self.expected_contract
        details['actual_to'] = actual_to
        
        # Check 3: Correct BNB amount sent (20 points)
        actual_value = int(tx.get('value', 0))
        expected_value_wei = int(self.expected_amount * 10**18)
        
        # Allow 10 wei tolerance for floating point conversion
        value_correct = abs(actual_value - expected_value_wei) <= 10
        
        if value_correct:
            score += 20
            checks.append({
                'name': 'BNB Amount',
                'passed': True,
                'points': 20,
                'message': f'Correct amount: {self.expected_amount} BNB'
            })
        else:
            actual_bnb = actual_value / 10**18
            checks.append({
                'name': 'BNB Amount',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_amount} BNB, Got: {actual_bnb} BNB'
            })
        
        details['expected_amount'] = self.expected_amount
        details['actual_value_wei'] = actual_value
        details['expected_value_wei'] = expected_value_wei
        
        # Check 4: Empty data field (15 points)
        # Data should be empty, '0x', or not present
        tx_data = tx.get('data', '0x')
        
        # Normalize empty data
        is_empty = (
            tx_data is None or 
            tx_data == '' or 
            tx_data == '0x' or
            (isinstance(tx_data, bytes) and len(tx_data) == 0)
        )
        
        if is_empty:
            score += 15
            checks.append({
                'name': 'Empty Data Field',
                'passed': True,
                'points': 15,
                'message': 'Correct: No function call data (triggers fallback/receive)'
            })
        else:
            checks.append({
                'name': 'Empty Data Field',
                'passed': False,
                'points': 0,
                'message': f'Data field should be empty, got: {tx_data}'
            })
        
        details['data_field'] = str(tx_data) if tx_data else 'empty'
        
        # Check 5: Contract balance increased (15 points)
        target_balance_before = state_before.get('target_balance', 0)
        target_balance_after = state_after.get('target_balance', 0)
        
        # Convert wei to BNB for comparison
        balance_increase_wei = target_balance_after - target_balance_before
        balance_increase = balance_increase_wei / 10**18 if isinstance(balance_increase_wei, int) else balance_increase_wei
        expected_increase = self.expected_amount
        
        # Allow small tolerance for gas and rounding
        balance_correct = abs(balance_increase - expected_increase) < 0.0001
        
        if balance_correct:
            score += 15
            checks.append({
                'name': 'Contract Balance Increase',
                'passed': True,
                'points': 15,
                'message': f'Contract balance increased by {balance_increase:.6f} BNB'
            })
        else:
            checks.append({
                'name': 'Contract Balance Increase',
                'passed': False,
                'points': 0,
                'message': f'Expected increase: {expected_increase} BNB, Actual: {balance_increase:.6f} BNB'
            })
        
        details['target_balance_before'] = target_balance_before
        details['target_balance_after'] = target_balance_after
        details['balance_increase_wei'] = balance_increase_wei
        details['balance_increase_bnb'] = balance_increase
        
        # Determine if all checks passed
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': all_passed,
            'checks': checks,
            'details': details
        }


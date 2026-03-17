"""
Contract Call with Value Validator

Validates that a payable contract function call with BNB value is correctly executed
"""

from typing import Dict, Any


class ContractCallWithValueValidator:
    """Validator for contract calls with BNB value attached"""
    
    def __init__(self, contract_address: str, amount: float):
        """
        Initialize validator
        
        Args:
            contract_address: DonationBox contract address
            amount: Amount of BNB to send (in BNB, not wei)
        """
        from decimal import Decimal
        
        self.expected_contract = contract_address.lower()
        # Use Decimal for precise BNB to wei conversion
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
        Validate the contract call with value transaction
        
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
        
        # Check 3: Function signature (20 points)
        # donate() function selector: 0xed88c68e
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:  # 0x + 8 hex chars (4 bytes)
            function_selector = tx_data[:10].lower()
            expected_selector = '0xed88c68e'  # donate()
            
            if function_selector == expected_selector:
                score += 20
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 20,
                    'message': 'Correct donate() function signature'
                })
            else:
                checks.append({
                    'name': 'Function Signature',
                    'passed': False,
                    'points': 0,
                    'message': f'Expected: {expected_selector}, Got: {function_selector}'
                })
            
            details['function_selector'] = function_selector
        else:
            checks.append({
                'name': 'Function Signature',
                'passed': False,
                'points': 0,
                'message': 'No data field or too short'
            })
            details['function_selector'] = 'N/A'
        
        # Check 4: Value sent (15 points)
        actual_value = tx.get('value', 0)
        if isinstance(actual_value, str):
            actual_value = int(actual_value, 16) if actual_value.startswith('0x') else int(actual_value)
        
        # Allow 1 wei tolerance for rounding
        value_correct = abs(actual_value - self.expected_amount) <= 1
        
        if value_correct:
            score += 15
            checks.append({
                'name': 'Value Sent',
                'passed': True,
                'points': 15,
                'message': f'Correct BNB amount sent: {actual_value / 10**18:.6f} BNB'
            })
        else:
            checks.append({
                'name': 'Value Sent',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_amount / 10**18:.6f} BNB, Got: {actual_value / 10**18:.6f} BNB'
            })
        
        details['expected_value'] = self.expected_amount / 10**18
        details['actual_value'] = actual_value / 10**18
        
        # Check 5: Contract balance increased (15 points)
        contract_balance_before = state_before.get('target_balance', 0)
        contract_balance_after = state_after.get('target_balance', 0)
        
        balance_increase = contract_balance_after - contract_balance_before
        
        # Allow 1 wei tolerance
        balance_correct = abs(balance_increase - self.expected_amount) <= 1
        
        if balance_correct:
            score += 15
            checks.append({
                'name': 'Contract Balance Increased',
                'passed': True,
                'points': 15,
                'message': f'Contract balance increased by {balance_increase / 10**18:.6f} BNB'
            })
        else:
            checks.append({
                'name': 'Contract Balance Increased',
                'passed': False,
                'points': 0,
                'message': f'Expected increase: {self.expected_amount / 10**18:.6f} BNB, Actual: {balance_increase / 10**18:.6f} BNB'
            })
        
        details['contract_balance_before'] = contract_balance_before / 10**18
        details['contract_balance_after'] = contract_balance_after / 10**18
        details['balance_increase'] = balance_increase / 10**18
        
        # Determine if all checks passed
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': all_passed,
            'checks': checks,
            'details': details
        }


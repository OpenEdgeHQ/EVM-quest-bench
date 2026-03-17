"""
BNB Transfer to Contract Validator

Validates that a BNB transfer is sent to a valid contract address
"""

from typing import Dict, Any


class BNBTransferToContractValidator:
    """Validator for BNB transfers to smart contract addresses"""
    
    def __init__(self, contract_address: str, amount: float):
        """
        Initialize validator
        
        Args:
            contract_address: Expected contract address
            amount: Expected transfer amount in BNB (float)
        """
        from decimal import Decimal
        
        self.expected_to = contract_address.lower()
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
        
        # Check 2: Recipient is a contract address (20 points)
        actual_to = tx.get('to', '').lower()
        to_correct = actual_to == self.expected_to
        
        # Check if target is a contract (has code)
        target_code_size = state_before.get('contract_code_size', 0)
        is_contract = target_code_size > 0
        
        if to_correct and is_contract:
            score += 20
            checks.append({
                'name': 'Recipient is Contract',
                'passed': True,
                'points': 20,
                'message': f'Correct contract address: {self.expected_to} (code size: {target_code_size} bytes)'
            })
        else:
            # Failed: either wrong address or not a contract
            if to_correct and not is_contract:
                error_msg = f'Address correct but target is not a contract (code size: 0)'
            else:
                error_msg = f'Expected contract: {self.expected_to}, Got: {actual_to}'
            
            checks.append({
                'name': 'Recipient is Contract',
                'passed': False,
                'points': 0,
                'message': error_msg
            })
        
        details['expected_to'] = self.expected_to
        details['actual_to'] = actual_to
        details['is_contract'] = is_contract
        details['contract_code_size'] = target_code_size
        
        # Check 3: Transfer amount (30 points)
        actual_value = int(tx.get('value', 0))
        amount_correct = actual_value == self.expected_amount
        
        if amount_correct:
            score += 30
            checks.append({
                'name': 'Transfer Amount',
                'passed': True,
                'points': 30,
                'message': f'Correct amount: {self.expected_amount} wei'
            })
        else:
            checks.append({
                'name': 'Transfer Amount',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_amount} wei, Got: {actual_value} wei'
            })
        
        details['expected_amount'] = self.expected_amount
        details['actual_amount'] = actual_value
        
        # Check 4: Contract balance change (20 points)
        contract_balance_before = state_before.get('target_balance', 0)
        contract_balance_after = state_after.get('target_balance', 0)
        
        expected_contract_balance = contract_balance_before + self.expected_amount
        balance_diff = abs(contract_balance_after - expected_contract_balance)
        
        # Allow 0.1% tolerance for rounding errors
        tolerance = max(int(self.expected_amount * 0.001), 1)
        balance_correct = balance_diff <= tolerance
        
        if balance_correct:
            score += 20
            checks.append({
                'name': 'Contract Balance Change',
                'passed': True,
                'points': 20,
                'message': f'Contract balance increased by {self.expected_amount} wei'
            })
        else:
            checks.append({
                'name': 'Contract Balance Change',
                'passed': False,
                'points': 0,
                'message': f'Expected increase: {self.expected_amount} wei, Actual: {contract_balance_after - contract_balance_before} wei'
            })
        
        details['contract_balance_before'] = contract_balance_before
        details['contract_balance_after'] = contract_balance_after
        details['contract_balance_change'] = contract_balance_after - contract_balance_before
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }


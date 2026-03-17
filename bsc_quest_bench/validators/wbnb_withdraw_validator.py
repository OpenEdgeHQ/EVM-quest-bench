"""
WBNB Withdraw Validator

Validates that WBNB was successfully withdrawn and converted back to native BNB
"""

from typing import Dict, Any


class WBNBWithdrawValidator:
    """Validator for WBNB withdraw transactions"""
    
    def __init__(self, wbnb_address: str, amount: float, **kwargs):
        """
        Initialize validator
        
        Args:
            wbnb_address: WBNB contract address
            amount: Expected withdrawal amount in WBNB/BNB (float)
        """
        from decimal import Decimal
        
        if not wbnb_address:
            raise ValueError("wbnb_address is required but was None or empty")
        
        self.expected_wbnb = wbnb_address.lower()
        # Convert amount to wei
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
        # WBNB withdraw function selector: 0x2e1a7d4d (keccak256("withdraw(uint256)"))
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:
            function_selector = tx_data[:10].lower()
            expected_selector = '0x2e1a7d4d'  # withdraw(uint256)
            
            if function_selector == expected_selector:
                score += 20
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 20,
                    'message': 'Correct WBNB withdraw function signature'
                })
                
                # Decode amount from data
                try:
                    if len(tx_data) >= 74:  # 0x(2) + selector(8) + amount(64) = 74
                        amount_hex = tx_data[10:74]
                        amount_value = int(amount_hex, 16)
                        details['decoded_amount'] = amount_value
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
        
        # Check 4: WBNB token balance decreased (15 points)
        wbnb_balance_before = state_before.get('token_balance', 0)
        wbnb_balance_after = state_after.get('token_balance', 0)
        balance_decrease = wbnb_balance_before - wbnb_balance_after
        
        # Allow small tolerance
        tolerance = int(self.expected_amount * 0.001)
        balance_correct = abs(balance_decrease - self.expected_amount) <= tolerance
        
        if balance_correct:
            score += 15
            checks.append({
                'name': 'WBNB Balance Decrease',
                'passed': True,
                'points': 15,
                'message': f'WBNB balance decreased by {balance_decrease} wei ({balance_decrease / 10**18:.6f})'
            })
        else:
            checks.append({
                'name': 'WBNB Balance Decrease',
                'passed': False,
                'points': 0,
                'message': f'Expected decrease: {self.expected_amount} wei, Got: {balance_decrease} wei'
            })
        
        details['wbnb_balance_before'] = wbnb_balance_before
        details['wbnb_balance_after'] = wbnb_balance_after
        details['balance_decrease'] = balance_decrease
        
        # Check 5: Native BNB balance increased (15 points)
        # BNB balance should increase by withdrawal amount, minus gas cost
        bnb_balance_before = state_before.get('balance', 0)
        bnb_balance_after = state_after.get('balance', 0)
        gas_used = receipt.get('gasUsed', 0)
        gas_price = receipt.get('effectiveGasPrice', 0)
        gas_cost = gas_used * gas_price
        
        # Expected BNB balance: before + withdrawal - gas
        expected_bnb_after = bnb_balance_before + self.expected_amount - gas_cost
        bnb_diff = abs(bnb_balance_after - expected_bnb_after)
        
        # Allow 0.1% tolerance for BNB balance (gas estimation variations)
        bnb_tolerance = int(self.expected_amount * 0.001)  # 0.1% tolerance
        bnb_balance_correct = bnb_diff <= bnb_tolerance
        
        if bnb_balance_correct:
            score += 15
            checks.append({
                'name': 'BNB Balance Increase',
                'passed': True,
                'points': 15,
                'message': f'BNB balance increased correctly (withdrawal: {self.expected_amount} wei, gas: {gas_cost} wei)'
            })
        else:
            actual_increase = bnb_balance_after - bnb_balance_before
            checks.append({
                'name': 'BNB Balance Increase',
                'passed': False,
                'points': 0,
                'message': f'Expected increase: {self.expected_amount - gas_cost} wei, Got: {actual_increase} wei'
            })
        
        details['bnb_balance_before'] = bnb_balance_before
        details['bnb_balance_after'] = bnb_balance_after
        details['gas_cost'] = gas_cost
        details['expected_bnb_increase'] = self.expected_amount - gas_cost
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }


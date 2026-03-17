"""
Validator for DelegateCall operations
"""

from typing import Dict, Any


class ContractDelegateCallValidator:
    """Validate delegatecall proxy call"""
    
    def __init__(self, proxy_address: str, implementation_address: str, value: float):
        """
        Initialize validator
        
        Args:
            proxy_address: Proxy contract address
            implementation_address: Implementation contract address
            value: Expected value to be set
        """
        self.expected_proxy = proxy_address.lower()
        self.expected_implementation = implementation_address.lower()
        self.expected_value = int(value)  # Convert to int
        self.max_score = 100
    
    def validate(self, tx: Dict[str, Any], receipt: Dict[str, Any], state_before: Dict[str, Any], state_after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate delegatecall transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
        
        Returns:
            Validation results including score and details
        """
        checks = []
        score = 0
        details = {}
        
        # 1. Validate transaction success (30 points)
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
        
        # 2. Validate called proxy contract (20 points)
        actual_to = tx.get('to', '').lower()
        contract_correct = actual_to == self.expected_proxy
        
        if contract_correct:
            score += 20
            checks.append({
                'name': 'Proxy Contract Address',
                'passed': True,
                'points': 20,
                'message': f'Correct proxy contract: {self.expected_proxy}'
            })
        else:
            checks.append({
                'name': 'Proxy Contract Address',
                'passed': False,
                'points': 0,
                'message': f'Expected proxy: {self.expected_proxy}, Got: {actual_to}'
            })
        
        details['expected_proxy'] = self.expected_proxy
        details['actual_to'] = actual_to
        
        # 3. Validatefunction selector setValue(uint256) = 0x55241077 (20 points)
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:  # 0x + 8 hex chars (4 bytes)
            function_selector = tx_data[:10].lower()
            expected_selector = '0x55241077'  # setValue(uint256)
            
            if function_selector == expected_selector:
                score += 20
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 20,
                    'message': 'Correct setValue(uint256) function signature'
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
        
        # 4. Validate proxy contract storage updated (15 points)
        proxy_value_before = state_before.get('proxy_value', 0)
        proxy_value_after = state_after.get('proxy_value', 0)
        
        value_updated = proxy_value_after == self.expected_value and proxy_value_after != proxy_value_before
        
        if value_updated:
            score += 15
            checks.append({
                'name': 'Proxy Storage Updated',
                'passed': True,
                'points': 15,
                'message': f'Proxy value correctly updated: {proxy_value_before} → {proxy_value_after}'
            })
        else:
            checks.append({
                'name': 'Proxy Storage Updated',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_value}, Before: {proxy_value_before}, After: {proxy_value_after}'
            })
        
        details['proxy_value_before'] = proxy_value_before
        details['proxy_value_after'] = proxy_value_after
        details['expected_value'] = self.expected_value
        
        # 5. Validate implementation contract storage unchanged (15 points)
        impl_value_before = state_before.get('implementation_value', 0)
        impl_value_after = state_after.get('implementation_value', 0)
        
        impl_unchanged = impl_value_before == impl_value_after
        
        if impl_unchanged:
            score += 15
            checks.append({
                'name': 'Implementation Storage Unchanged',
                'passed': True,
                'points': 15,
                'message': f'Implementation value unchanged: {impl_value_before} (correct)'
            })
        else:
            checks.append({
                'name': 'Implementation Storage Unchanged',
                'passed': False,
                'points': 0,
                'message': f'Implementation changed: {impl_value_before} → {impl_value_after} (should remain unchanged)'
            })
        
        details['impl_value_before'] = impl_value_before
        details['impl_value_after'] = impl_value_after
        
        # Determine if all checks passed
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': all_passed,
            'checks': checks,
            'details': details
        }


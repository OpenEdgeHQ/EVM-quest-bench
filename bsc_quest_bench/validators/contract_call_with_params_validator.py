"""
Contract Call with Parameters Validator

Validates that a contract function call with parameters is correctly executed
"""

from typing import Dict, Any


class ContractCallWithParamsValidator:
    """Validator for contract calls with parameters"""
    
    def __init__(self, contract_address: str, message: str):
        """
        Initialize validator
        
        Args:
            contract_address: MessageBoard contract address
            message: Expected message to be stored
        """
        self.expected_contract = contract_address.lower()
        self.expected_message = message
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the contract call with parameters transaction
        
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
        
        # Check 1: Transaction success (40 points)
        tx_success = receipt.get('status') == 1
        
        if tx_success:
            score += 40
            checks.append({
                'name': 'Transaction Success',
                'passed': True,
                'points': 40,
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
        # setMessage(string) function selector: 0x368b8772
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:  # 0x + 8 hex chars (4 bytes)
            function_selector = tx_data[:10].lower()
            expected_selector = '0x368b8772'  # setMessage(string)
            
            if function_selector == expected_selector:
                score += 20
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 20,
                    'message': 'Correct setMessage(string) function signature'
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
        
        # Check 4: Message stored correctly (20 points)
        stored_message = state_after.get('message_value', '')
        
        message_correct = stored_message == self.expected_message
        
        if message_correct:
            score += 20
            checks.append({
                'name': 'Message Stored',
                'passed': True,
                'points': 20,
                'message': f'Message correctly stored: "{stored_message}"'
            })
        else:
            checks.append({
                'name': 'Message Stored',
                'passed': False,
                'points': 0,
                'message': f'Expected: "{self.expected_message}", Got: "{stored_message}"'
            })
        
        details['expected_message'] = self.expected_message
        details['stored_message'] = stored_message
        
        # Determine if all checks passed
        all_passed = all(check['passed'] for check in checks)
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': all_passed,
            'checks': checks,
            'details': details
        }


"""
ERC20 Revoke Approval Validator

Validates that ERC20 approval was successfully revoked (allowance set to zero)
"""

from typing import Dict, Any


class ERC20RevokeApprovalValidator:
    """Validator for ERC20 revoke approval transactions"""
    
    def __init__(self, token_address: str, spender_address: str):
        """
        Initialize validator
        
        Args:
            token_address: ERC20 token contract address
            spender_address: Address whose approval should be revoked
        """
        self.expected_token = token_address.lower()
        self.expected_spender = spender_address.lower()
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
        
        # Check 3: Function signature (20 points)
        # ERC20 approve function selector: 0x095ea7b3 (keccak256("approve(address,uint256)"))
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:
            function_selector = tx_data[:10].lower()
            expected_selector = '0x095ea7b3'  # approve(address,uint256)
            
            if function_selector == expected_selector:
                score += 20
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 20,
                    'message': 'Correct ERC20 approve function signature'
                })
                
                # Decode parameters from data
                try:
                    if len(tx_data) >= 138:  # 0x(2) + selector(8) + spender(64) + amount(64) = 138
                        spender_hex = tx_data[10:74]  # Next 64 chars (32 bytes)
                        amount_hex = tx_data[74:138]  # Next 64 chars (32 bytes)
                        
                        # Extract address (last 40 hex chars of the 64 char field)
                        spender_addr = '0x' + spender_hex[-40:].lower()
                        amount_value = int(amount_hex, 16)
                        
                        details['decoded_spender'] = spender_addr
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
        
        # Check 4: Allowance revoked (set to 0) (30 points)
        allowance_before = state_before.get('allowance', 0)
        allowance_after = state_after.get('allowance', 0)
        
        # Allowance should be 0 after revoke
        allowance_revoked = allowance_after == 0
        
        if allowance_revoked:
            score += 30
            checks.append({
                'name': 'Allowance Revoked',
                'passed': True,
                'points': 30,
                'message': f'Allowance successfully revoked (before: {allowance_before}, after: 0)'
            })
        else:
            checks.append({
                'name': 'Allowance Revoked',
                'passed': False,
                'points': 0,
                'message': f'Allowance not revoked (expected: 0, got: {allowance_after})'
            })
        
        details['allowance_before'] = allowance_before
        details['allowance_after'] = allowance_after
        details['expected_spender'] = self.expected_spender
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }


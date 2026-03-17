"""
ERC20 Token Transfer Validator

Validates that an ERC20 token transfer transaction is correctly executed
"""

from typing import Dict, Any


class ERC20TransferValidator:
    """Validator for ERC20 token transfers"""
    
    def __init__(self, token_address: str, to_address: str, amount: float, token_decimals: int = 18):
        """
        Initialize validator
        
        Args:
            token_address: ERC20 token contract address
            to_address: Expected recipient address
            amount: Expected transfer amount in tokens (float)
            token_decimals: Token decimals (default: 18)
        """
        from decimal import Decimal
        
        self.expected_token = token_address.lower()
        self.expected_to = to_address.lower()
        # Convert token amount to smallest unit
        self.expected_amount = int(Decimal(str(amount)) * Decimal(10 ** token_decimals))
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
        contract_correct = actual_to == self.expected_token
        
        if contract_correct:
            score += 20
            checks.append({
                'name': 'Contract Address',
                'passed': True,
                'points': 20,
                'message': f'Correct token contract: {self.expected_token}'
            })
        else:
            checks.append({
                'name': 'Contract Address',
                'passed': False,
                'points': 0,
                'message': f'Expected: {self.expected_token}, Got: {actual_to}'
            })
        
        details['expected_token'] = self.expected_token
        details['actual_to'] = actual_to
        
        # Check 3: Function signature (20 points)
        # ERC20 transfer function selector: 0xa9059cbb (first 4 bytes of keccak256("transfer(address,uint256)"))
        tx_data = tx.get('data', '0x')
        
        if tx_data and len(tx_data) >= 10:  # 0x + 8 hex chars (4 bytes)
            function_selector = tx_data[:10].lower()
            expected_selector = '0xa9059cbb'  # transfer(address,uint256)
            
            if function_selector == expected_selector:
                score += 20
                checks.append({
                    'name': 'Function Signature',
                    'passed': True,
                    'points': 20,
                    'message': 'Correct ERC20 transfer function signature'
                })
                
                # Decode parameters from data
                try:
                    # Data format: 0x + function_selector (8 chars) + address (64 chars) + amount (64 chars)
                    if len(tx_data) >= 138:  # 0x(2) + selector(8) + address(64) + amount(64) = 138
                        recipient_hex = tx_data[10:74]  # Skip 0x and selector
                        amount_hex = tx_data[74:138]
                        
                        # Convert to addresses and amounts
                        recipient_address = '0x' + recipient_hex[-40:]  # Last 40 chars (20 bytes)
                        amount_value = int(amount_hex, 16)
                        
                        details['decoded_recipient'] = recipient_address.lower()
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
        
        # Check 4: Token balance changes (30 points)
        sender_balance_before = state_before.get('token_balance', 0)
        sender_balance_after = state_after.get('token_balance', 0)
        receiver_balance_before = state_before.get('target_token_balance', 0)
        receiver_balance_after = state_after.get('target_token_balance', 0)
        
        sender_change = sender_balance_after - sender_balance_before
        receiver_change = receiver_balance_after - receiver_balance_before
        
        # Check if changes match expected
        sender_correct = sender_change == -self.expected_amount
        receiver_correct = receiver_change == self.expected_amount
        
        if sender_correct and receiver_correct:
            score += 30
            checks.append({
                'name': 'Token Balance Changes',
                'passed': True,
                'points': 30,
                'message': f'Correct token balance changes: -{self.expected_amount} (sender), +{self.expected_amount} (receiver)'
            })
        else:
            # Balance changes incorrect - no partial credit for consistency
            error_parts = []
            if not sender_correct:
                error_parts.append(f'Sender: expected -{self.expected_amount}, got {sender_change}')
            if not receiver_correct:
                error_parts.append(f'Receiver: expected +{self.expected_amount}, got {receiver_change}')
            
            checks.append({
                'name': 'Token Balance Changes',
                'passed': False,
                'points': 0,
                'message': ' | '.join(error_parts) if error_parts else 'Balance changes incorrect'
            })
        
        details['sender_balance_before'] = sender_balance_before
        details['sender_balance_after'] = sender_balance_after
        details['sender_change'] = sender_change
        details['receiver_balance_before'] = receiver_balance_before
        details['receiver_balance_after'] = receiver_balance_after
        details['receiver_change'] = receiver_change
        details['expected_amount'] = self.expected_amount
        
        # Final result
        passed = score >= self.max_score * 0.8  # 80% threshold
        
        return {
            'score': score,
            'max_score': self.max_score,
            'passed': passed,
            'checks': checks,
            'details': details
        }


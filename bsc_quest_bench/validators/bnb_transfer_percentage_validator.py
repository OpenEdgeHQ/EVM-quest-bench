"""
BNB Percentage Transfer Validator

Validates BNB percentage transfer transactions
"""

from typing import Dict, Any, List


class BNBTransferPercentageValidator:
    """BNB Percentage Transfer Validator"""
    
    def __init__(self, to_address: str, percentage: int):
        """
        Initialize validator
        
        Args:
            to_address: Expected recipient address
            percentage: Expected percentage of balance to transfer (e.g., 50 for 50%)
        """
        self.expected_to = to_address.lower()
        self.percentage = percentage
        self.max_score = 100
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate transaction
        
        Args:
            tx: Transaction object
            receipt: Transaction receipt
            state_before: State before transaction
            state_after: State after transaction
            
        Returns:
            Validation result dictionary
        """
        checks = []
        score = 0
        
        # Get balance before transaction
        balance_before = state_before.get('balance', 0)
        
        # Calculate expected transfer amount (percentage of balance before)
        expected_amount_wei = int(balance_before * self.percentage / 100)
        
        # Check 1: Transaction success (30 points)
        tx_success = receipt.get('status') == 1
        checks.append({
            'name': 'Transaction Success',
            'passed': tx_success,
            'message': 'Transaction executed successfully' if tx_success else 'Transaction failed',
            'score': 30 if tx_success else 0
        })
        if tx_success:
            score += 30
        
        # Check 2: Target address correct (20 points)
        actual_to = tx.get('to', '').lower() if tx.get('to') else ''
        to_correct = actual_to == self.expected_to
        checks.append({
            'name': 'Target Address Correct',
            'passed': to_correct,
            'message': f"Expected: {self.expected_to}, Actual: {actual_to}",
            'score': 20 if to_correct else 0
        })
        if to_correct:
            score += 20
        
        # Check 3: Transfer amount is correct percentage (30 points)
        actual_value = int(tx.get('value', 0))
        
        # Allow 0.1% tolerance for calculation differences
        tolerance = int(expected_amount_wei * 0.001)
        amount_correct = abs(actual_value - expected_amount_wei) <= tolerance
        
        checks.append({
            'name': 'Transfer Amount Correct',
            'passed': amount_correct,
            'message': f"Expected: {expected_amount_wei} wei ({self.percentage}% of {balance_before} wei), "
                      f"Actual: {actual_value} wei ({actual_value/balance_before*100:.2f}% of balance)",
            'score': 30 if amount_correct else 0
        })
        if amount_correct:
            score += 30
        
        # Check 4: Gas settings reasonable (10 points)
        gas_used = receipt.get('gasUsed', 0)
        # Support both 'gas' (web3.py style) and 'gasLimit' (ethers.js style)
        gas_limit = tx.get('gas', 0) or tx.get('gasLimit', 0)
        
        # Basic transfer gas should be around 21000
        # gas limit should be sufficient and not excessively high
        # Note: system_config suggests gasLimit: 100000n as default, so we use 500000 as upper bound
        gas_reasonable = (
            gas_used >= 21000 and 
            gas_limit >= gas_used and 
            gas_limit <= 500000
        )
        
        checks.append({
            'name': 'Gas Settings Reasonable',
            'passed': gas_reasonable,
            'message': f"Gas Used: {gas_used}, Gas Limit: {gas_limit}",
            'score': 10 if gas_reasonable else 0
        })
        if gas_reasonable:
            score += 10
        
        # Check 5: Balance change correct (10 points)
        balance_after = state_after.get('balance', 0)
        balance_change = balance_before - balance_after
        
        # Balance change should equal transfer amount + gas fee
        gas_cost = gas_used * receipt.get('effectiveGasPrice', 0)
        expected_balance_change = actual_value + gas_cost
        
        # Allow 0.1% tolerance
        balance_tolerance = int(expected_balance_change * 0.001)
        balance_correct = abs(balance_change - expected_balance_change) <= balance_tolerance
        
        checks.append({
            'name': 'Balance Change Correct',
            'passed': balance_correct,
            'message': f"Balance decrease: {balance_change} wei (Transfer {actual_value} + Gas {gas_cost}), "
                      f"Balance change percentage: {balance_change/balance_before*100:.2f}%",
            'score': 10 if balance_correct else 0
        })
        if balance_correct:
            score += 10
        
        # Judge if passed
        passed = all(check['passed'] for check in checks)
        
        # Generate feedback
        feedback = self._generate_feedback(checks, score, passed)
        
        return {
            'passed': passed,
            'score': score,
            'max_score': self.max_score,
            'checks': checks,
            'feedback': feedback,
            'details': {
                'expected_to': self.expected_to,
                'percentage': self.percentage,
                'balance_before': balance_before,
                'expected_amount': expected_amount_wei,
                'actual_to': actual_to,
                'actual_amount': actual_value,
                'gas_used': gas_used,
                'balance_change': balance_change
            }
        }
    
    def _generate_feedback(
        self,
        checks: List[Dict[str, Any]],
        score: int,
        passed: bool
    ) -> str:
        """
        Generate feedback message
        
        Args:
            checks: List of check items
            score: Total score
            passed: Whether validation passed
            
        Returns:
            Feedback string
        """
        lines = []
        
        if passed:
            lines.append("🎉 Congratulations! All validation checks passed!")
            lines.append(f"Final Score: {score}/{self.max_score}")
        else:
            lines.append("❌ Validation failed, please check the following issues:")
            failed_checks = [c for c in checks if not c['passed']]
            for check in failed_checks:
                lines.append(f"  - {check['name']}: {check['message']}")
            lines.append(f"\nCurrent Score: {score}/{self.max_score}")
        
        return '\n'.join(lines)


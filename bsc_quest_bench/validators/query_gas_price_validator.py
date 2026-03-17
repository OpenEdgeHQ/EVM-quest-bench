"""
Validator for query_gas_price atomic problem.
Validates that the LLM correctly queries gas price and EIP-1559 parameters.
"""

from typing import Dict, Any


class QueryGasPriceValidator:
    """Validator for gas price and EIP-1559 fee parameters query operations"""
    
    def __init__(self):
        """
        Initialize validator for gas price query.
        
        No parameters needed as gas price is dynamic and always changing.
        """
        pass
    
    def validate(
        self,
        tx: Dict[str, Any],
        receipt: Dict[str, Any],
        state_before: Dict[str, Any],
        state_after: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate the gas price query result.
        
        Scoring:
        - Query execution success: 40 points
        - Return format correctness (EIP-1559 fields): 30 points
        - Gas price validity: 30 points
        
        Args:
            tx: Transaction object (for queries, this contains the query result)
            receipt: Transaction receipt (not used for queries)
            state_before: Chain state before execution (contains reference gas prices)
            state_after: Not used for query operations
            
        Returns:
            Validation result with score and feedback
        """
        # For query operations, the query result is in 'tx'
        query_result = tx.get('query_result', {})
        score = 0
        max_score = 100
        checks = []
        feedback_parts = []
        
        # Get reference gas prices from state_before (set by quest_executor)
        reference_max_fee = state_before.get('reference_max_fee_per_gas', 0)
        reference_priority_fee = state_before.get('reference_max_priority_fee_per_gas', 0)
        
        # Check 1: Query execution success (40 points)
        query_success = query_result.get('success', False)
        error_msg = query_result.get('error', '')
        
        if query_success:
            score += 40
            checks.append({
                'name': 'Query Execution Success',
                'passed': True,
                'message': 'Query executed successfully'
            })
        else:
            checks.append({
                'name': 'Query Execution Success',
                'passed': False,
                'message': f"Query execution failed: {error_msg}"
            })
            return {
                'passed': False,
                'score': score,
                'max_score': max_score,
                'checks': checks,
                'feedback': '❌ Query execution failed'
            }
        
        # Extract data from query result
        data = query_result.get('data', {})
        
        # Check 2: Return format correctness - EIP-1559 fields (30 points)
        required_fields = ['maxFeePerGas', 'maxPriorityFeePerGas']
        missing_fields = [field for field in required_fields if field not in data]
        
        if not missing_fields:
            score += 30
            checks.append({
                'name': 'Return Format Correct',
                'passed': True,
                'message': f'All required EIP-1559 fields present: {required_fields}'
            })
        else:
            checks.append({
                'name': 'Return Format Correct',
                'passed': False,
                'message': f'Missing required EIP-1559 fields: {missing_fields}'
            })
            feedback_parts.append(f"⚠️  Missing EIP-1559 fields: {', '.join(missing_fields)}")
        
        # Check 3: Gas price validity (30 points)
        try:
            max_fee_per_gas = data.get('maxFeePerGas', '0')
            max_priority_fee_per_gas = data.get('maxPriorityFeePerGas', '0')
            
            # Convert to integers
            if isinstance(max_fee_per_gas, str):
                max_fee_per_gas = int(max_fee_per_gas)
            else:
                max_fee_per_gas = int(max_fee_per_gas)
            
            if isinstance(max_priority_fee_per_gas, str):
                max_priority_fee_per_gas = int(max_priority_fee_per_gas)
            else:
                max_priority_fee_per_gas = int(max_priority_fee_per_gas)
            
            # Validation criteria:
            # 1. Both values must be positive
            # 2. maxFeePerGas should be >= maxPriorityFeePerGas (base fee + priority fee)
            # 3. Values should be in reasonable range (not too high, not zero)
            
            validation_passed = True
            validation_messages = []
            
            if max_fee_per_gas <= 0:
                validation_passed = False
                validation_messages.append("maxFeePerGas must be positive")
            
            if max_priority_fee_per_gas < 0:
                validation_passed = False
                validation_messages.append("maxPriorityFeePerGas must be non-negative")
            
            if max_fee_per_gas < max_priority_fee_per_gas:
                validation_passed = False
                validation_messages.append("maxFeePerGas should be >= maxPriorityFeePerGas")
            
            # Check if values are in reasonable range (BSC typical range: 3-50 Gwei)
            # 1 Gwei = 10^9 wei
            min_reasonable = 1 * 10**9  # 1 Gwei
            max_reasonable = 1000 * 10**9  # 1000 Gwei (extremely high, but possible)
            
            if max_fee_per_gas < min_reasonable or max_fee_per_gas > max_reasonable:
                # This is a warning, not a failure
                validation_messages.append(f"maxFeePerGas seems unusual: {max_fee_per_gas / 10**9:.2f} Gwei")
            
            # If reference values are available, check they're reasonably close (within 10x factor)
            if reference_max_fee > 0:
                if max_fee_per_gas > reference_max_fee * 10 or max_fee_per_gas < reference_max_fee / 10:
                    validation_messages.append(f"maxFeePerGas differs significantly from reference")
            
            if validation_passed:
                score += 30
                checks.append({
                    'name': 'Gas Price Validity',
                    'passed': True,
                    'message': f'Gas prices are valid - maxFeePerGas: {max_fee_per_gas / 10**9:.4f} Gwei, maxPriorityFeePerGas: {max_priority_fee_per_gas / 10**9:.4f} Gwei'
                })
                feedback_parts.append("✅ Gas prices queried correctly!")
            else:
                checks.append({
                    'name': 'Gas Price Validity',
                    'passed': False,
                    'message': '; '.join(validation_messages)
                })
                feedback_parts.append(f"⚠️  Gas price validation issues")
        except (ValueError, KeyError, TypeError) as e:
            checks.append({
                'name': 'Gas Price Validity',
                'passed': False,
                'message': f'Failed to parse gas prices: {str(e)}'
            })
            feedback_parts.append(f"❌ Failed to parse gas prices: {str(e)}")
        
        # Generate final feedback
        if score == max_score:
            feedback = "🎉 Congratulations! Gas prices and EIP-1559 parameters queried correctly!"
        elif score >= 60:
            feedback = "✅ Query mostly correct. " + " ".join(feedback_parts)
        else:
            feedback = "❌ Query needs improvement. " + " ".join(feedback_parts)
        
        return {
            'passed': score >= 60,  # Pass threshold: 60%
            'score': score,
            'max_score': max_score,
            'checks': checks,
            'feedback': feedback
        }


"""
Example Usage - Demonstrates how to use the refactored BSC Quest Bench

This example shows:
1. How questions are loaded
2. How random parameters are generated
3. How prompts are constructed
4. The three-part prompt structure
"""

import json
import asyncio
from pathlib import Path
from parameter_generator import ParameterGenerator, format_parameter_value


async def main():
    print("="*80)
    print("BSC Quest Bench - Architecture Example")
    print("="*80)
    print()
    
    # 1. Load system configuration (universal for all questions)
    print("1. Loading System Configuration...")
    print("-"*80)
    
    config_file = Path(__file__).parent / 'system_config.json'
    with open(config_file, 'r', encoding='utf-8') as f:
        system_config = json.load(f)
    
    print("Role Prompt:")
    print(f"  {system_config['role_prompt'][:100]}...")
    print()
    print("Environment Description:")
    print(f"  {system_config['environment_description'][:100]}...")
    print()
    
    # 2. Load question configuration
    print("2. Loading Question Configuration...")
    print("-"*80)
    
    question_file = Path(__file__).parent / 'question_bank' / 'basic_transactions' / 'native_transfer' / 'bnb_transfer_basic.json'
    with open(question_file, 'r', encoding='utf-8') as f:
        question = json.load(f)
    
    print(f"Question ID: {question['id']}")
    print(f"Title: {question['title']}")
    print(f"Description: {question['description']}")
    print()
    
    # 3. Generate random parameters
    print("3. Generating Random Parameters...")
    print("-"*80)
    
    param_generator = ParameterGenerator(seed=42)  # Use seed for reproducibility in this example
    generated_params = param_generator.generate_parameters(question['parameters'])
    
    print("Generated Parameters:")
    for param_name, param_value in generated_params.items():
        param_config = question['parameters'][param_name]
        formatted = format_parameter_value(param_value, param_config)
        print(f"  - {param_name}: {formatted}")
        print(f"    (raw value: {param_value})")
    print()
    
    # 4. Generate natural language prompt
    print("4. Generating Natural Language Prompt...")
    print("-"*80)
    
    # Choose first template for this example
    template = question['natural_language_templates'][0]
    print(f"Template: {template}")
    print()
    
    # Fill in parameters
    natural_language_prompt = template
    for param_name, param_value in generated_params.items():
        param_config = question['parameters'][param_name]
        formatted_value = format_parameter_value(param_value, param_config)
        natural_language_prompt = natural_language_prompt.replace(f"{{{param_name}}}", formatted_value)
    
    print(f"Filled Prompt: {natural_language_prompt}")
    print()
    
    # 5. Construct full prompt (3 parts combined)
    print("5. Constructing Full Prompt...")
    print("-"*80)
    
    full_prompt = f"{system_config['role_prompt']}\n\n{system_config['environment_description']}\n\nTask:\n{natural_language_prompt}"
    
    print("Full Prompt Structure:")
    print()
    print("[PART 1: ROLE]")
    print(system_config['role_prompt'])
    print()
    print("[PART 2: ENVIRONMENT]")
    print(system_config['environment_description'][:200] + "...")
    print()
    print("[PART 3: NATURAL LANGUAGE TASK]")
    print(natural_language_prompt)
    print()
    
    # 6. Show what's NOT in the prompt
    print("6. What's NOT in the Prompt")
    print("-"*80)
    print("✅ No code templates")
    print("✅ No step-by-step implementation guides")
    print("✅ No hardcoded test values")
    print("✅ No hints about implementation details")
    print()
    print("The LLM must understand the requirement and generate code independently!")
    print()
    
    # 7. Show parameter generation ranges
    print("7. Parameter Generation Configuration")
    print("-"*80)
    
    for param_name, param_config in question['parameters'].items():
        print(f"\n{param_name}:")
        print(f"  Type: {param_config['type']}")
        if 'unit' in param_config:
            print(f"  Unit: {param_config['unit']}")
        print(f"  Generation: {json.dumps(param_config['generation'], indent=4)}")
    
    print()
    print("="*80)
    print("Example Complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())


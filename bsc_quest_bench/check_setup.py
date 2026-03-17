#!/usr/bin/env python3
"""
BSC Quest Bench Setup Checker

Verifies that the project is correctly configured and all dependencies are available.
"""

import sys
from pathlib import Path

def check_file_exists(filepath: Path, description: str) -> bool:
    """Check if a file exists"""
    if filepath.exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} NOT FOUND")
        return False

def check_directory_exists(dirpath: Path, description: str) -> bool:
    """Check if a directory exists"""
    if dirpath.exists() and dirpath.is_dir():
        print(f"✅ {description}: {dirpath}")
        return True
    else:
        print(f"❌ {description}: {dirpath} NOT FOUND")
        return False

def main():
    print("="*80)
    print("🔍 BSC Quest Bench Setup Checker")
    print("="*80)
    print()
    
    project_root = Path(__file__).parent
    all_checks_passed = True
    
    # Check core Python files
    print("📦 Core Python Files:")
    all_checks_passed &= check_file_exists(project_root / "quest_controller.py", "Controller")
    all_checks_passed &= check_file_exists(project_root / "quest_env.py", "Environment")
    all_checks_passed &= check_file_exists(project_root / "quest_executor.py", "Executor")
    all_checks_passed &= check_file_exists(project_root / "parameter_generator.py", "Parameter Generator")
    all_checks_passed &= check_file_exists(project_root / "run_quest_bench.py", "Main Runner")
    print()
    
    # Check directories
    print("📁 Core Directories:")
    all_checks_passed &= check_directory_exists(project_root / "validators", "Validators")
    all_checks_passed &= check_directory_exists(project_root / "question_bank", "Question Bank")
    all_checks_passed &= check_directory_exists(project_root / "skill_runner", "Skill Runner")
    all_checks_passed &= check_directory_exists(project_root / "skill_manager", "Skill Manager")
    all_checks_passed &= check_directory_exists(project_root / "contracts", "Contracts")
    print()
    
    # Check TypeScript runner
    print("🔧 TypeScript Runtime:")
    all_checks_passed &= check_file_exists(project_root / "skill_runner" / "runBscSkill.ts", "TypeScript Runner")
    all_checks_passed &= check_file_exists(project_root / "skill_runner" / "package.json", "Package Config")
    all_checks_passed &= check_file_exists(project_root / "skill_runner" / "tsconfig.json", "TypeScript Config")
    print()
    
    # Check dependencies
    print("📚 Dependencies:")
    all_checks_passed &= check_file_exists(project_root / "requirements.txt", "Python Requirements")
    all_checks_passed &= check_file_exists(project_root / "README.md", "Documentation")
    print()
    
    # Try importing core modules
    print("🐍 Python Module Imports:")
    try:
        sys.path.insert(0, str(project_root))
        from quest_env import QuestEnvironment
        print("✅ quest_env imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import quest_env: {e}")
        all_checks_passed = False
    
    try:
        from quest_controller import QuestController
        print("✅ quest_controller imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import quest_controller: {e}")
        all_checks_passed = False
    
    try:
        from quest_executor import QuestExecutor
        print("✅ quest_executor imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import quest_executor: {e}")
        all_checks_passed = False
    print()
    
    # Count validators and questions
    print("📊 Content Statistics:")
    validator_count = len(list((project_root / "validators").glob("*_validator.py")))
    print(f"  Validators: {validator_count}")
    
    question_count = len(list((project_root / "question_bank").rglob("*.json")))
    print(f"  Questions: {question_count}")
    print()
    
    # Final result
    print("="*80)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED - Project is ready to use!")
        print()
        print("Next steps:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Install TypeScript deps: cd skill_runner && bun install")
        print("  3. Run benchmark: python run_quest_bench.py --model gpt-4o --max-questions 1")
    else:
        print("❌ SOME CHECKS FAILED - Please review errors above")
        return 1
    print("="*80)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


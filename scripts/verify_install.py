#!/usr/bin/env python
"""
Installation verification script for AvatarFactory.

Run this after installation to verify everything is set up correctly.
"""

import sys


def print_section(title):
    """Print section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def check_python_version():
    """Check Python version"""
    print_section("1. Python Version")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Python 3.10+ required")
        return False
    else:
        print("✅ Python version OK")
        return True


def check_required_packages():
    """Check if required packages are installed"""
    print_section("2. Required Packages")

    required = {
        'anthropic': 'Anthropic (for Claude)',
        'pydantic': 'Pydantic (data validation)',
        'typer': 'Typer (CLI)',
        'rich': 'Rich (terminal UI)',
        'yaml': 'PyYAML (config files)',
        'dotenv': 'python-dotenv (environment variables)',
    }

    optional = {
        'openai': 'OpenAI (for Azure OpenAI and OpenAI support)',
    }

    all_ok = True

    print("\nRequired packages:")
    for package, description in required.items():
        try:
            __import__(package)
            print(f"  ✅ {description}")
        except ImportError:
            print(f"  ❌ {description} - NOT FOUND")
            all_ok = False

    print("\nOptional packages:")
    for package, description in optional.items():
        try:
            __import__(package)
            print(f"  ✅ {description}")
        except ImportError:
            print(f"  ⚠️  {description} - not installed (OK if not using)")

    return all_ok


def check_avatarfactory_package():
    """Check if avatarfactory package is importable"""
    print_section("3. AvatarFactory Package")

    try:
        import avatarfactory
        print(f"✅ AvatarFactory package found")
        print(f"   Version: {avatarfactory.__version__}")

        # Check core modules
        modules = [
            'avatarfactory.core.knowledges',
            'avatarfactory.core.llm_provider',
            'avatarfactory.agents.base',
            'avatarfactory.agents.orchestrator',
            'avatarfactory.models.schemas',
        ]

        print("\nCore modules:")
        for module in modules:
            try:
                __import__(module)
                print(f"  ✅ {module}")
            except ImportError as e:
                print(f"  ❌ {module} - {e}")
                return False

        return True

    except ImportError as e:
        print(f"❌ AvatarFactory package not found: {e}")
        print("\nTry running: pip install -e .")
        return False


def check_env_file():
    """Check if .env file exists"""
    print_section("4. Configuration")

    import os
    from pathlib import Path

    env_path = Path(".env")

    if env_path.exists():
        print("✅ .env file found")

        # Load and check for API keys
        from dotenv import load_dotenv
        load_dotenv()

        provider = os.getenv("AVATARFACTORY_LLM_PROVIDER", "anthropic")
        print(f"   Provider: {provider}")

        # Check provider-specific keys
        if provider == "anthropic":
            if os.getenv("ANTHROPIC_API_KEY"):
                print("   ✅ ANTHROPIC_API_KEY is set")
            else:
                print("   ⚠️  ANTHROPIC_API_KEY not set")

        elif provider == "azure_openai":
            if os.getenv("AZURE_OPENAI_API_KEY"):
                print("   ✅ AZURE_OPENAI_API_KEY is set")
            else:
                print("   ❌ AZURE_OPENAI_API_KEY not set")

            if os.getenv("AZURE_OPENAI_ENDPOINT"):
                print("   ✅ AZURE_OPENAI_ENDPOINT is set")
            else:
                print("   ❌ AZURE_OPENAI_ENDPOINT not set")

        elif provider == "openai":
            if os.getenv("OPENAI_API_KEY"):
                print("   ✅ OPENAI_API_KEY is set")
            else:
                print("   ❌ OPENAI_API_KEY not set")

        return True
    else:
        print("⚠️  .env file not found")
        print("\nCreate it from example:")
        print("  cp .env.example .env")
        print("  # Then edit .env to add your API keys")
        return False


def check_cli_command():
    """Check if CLI command is available"""
    print_section("5. CLI Command")

    import subprocess

    try:
        result = subprocess.run(
            ['avatarfactory', 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            print("✅ CLI command works")
            print(f"   {result.stdout.strip()}")
            return True
        else:
            print("❌ CLI command failed")
            return False

    except FileNotFoundError:
        print("❌ 'avatarfactory' command not found")
        print("\nTry running: pip install -e .")
        return False
    except Exception as e:
        print(f"⚠️  Could not test CLI: {e}")
        return False


def check_knowledges():
    """Check if knowledges directory exists"""
    print_section("6. Knowledges")

    from pathlib import Path
    import os

    kb_path = Path(os.getenv("AVATARFACTORY_KB_PATH", "./knowledges"))

    if kb_path.exists():
        print(f"✅ Knowledges directory found: {kb_path}")

        # Check subdirectories
        subdirs = ['personas', 'content_library', 'experiments', 'platform_rules']
        for subdir in subdirs:
            if (kb_path / subdir).exists():
                print(f"   ✅ {subdir}/")
            else:
                print(f"   ⚠️  {subdir}/ not found (will be created on first use)")

        return True
    else:
        print(f"⚠️  Knowledges directory not found at: {kb_path}")
        print("   (Will be created automatically on first use)")
        return True  # Not a critical issue


def main():
    """Run all checks"""
    print("\n" + "="*60)
    print("  AvatarFactory Installation Verification")
    print("="*60)

    checks = [
        ("Python Version", check_python_version),
        ("Packages", check_required_packages),
        ("AvatarFactory Package", check_avatarfactory_package),
        ("Configuration", check_env_file),
        ("CLI Command", check_cli_command),
        ("Knowledges", check_knowledges),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            results[name] = False

    # Summary
    print_section("Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print(f"\nPassed: {passed}/{total}")

    if all(results.values()):
        print("\n🎉 All checks passed! AvatarFactory is ready to use.")
        print("\nNext steps:")
        print("  1. Make sure .env has your API key")
        print("  2. Run: avatarfactory chat")
        print("  3. Start creating personas!")
        return 0
    else:
        print("\n⚠️  Some checks failed. See details above.")
        print("\nCommon fixes:")
        print("  • Missing packages: pip install -r requirements.txt")
        print("  • Package not found: pip install -e .")
        print("  • Missing .env: cp .env.example .env")
        return 1


if __name__ == "__main__":
    sys.exit(main())

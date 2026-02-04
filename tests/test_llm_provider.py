"""
Test script for multi-LLM provider support.

Run this to verify your LLM configuration is working.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_provider():
    """Test the configured LLM provider"""
    try:
        from avatarfactory.core.llm_provider import LLMProviderFactory

        print("=" * 60)
        print("AvatarFactory LLM Provider Test")
        print("=" * 60)

        # Create provider from environment
        print("\n1️⃣  Detecting provider from environment...")
        provider = LLMProviderFactory.from_env()

        print(f"   ✅ Provider: {provider.__class__.__name__}")
        print(f"   ✅ Model: {provider.model}")

        # Validate configuration
        print("\n2️⃣  Validating configuration...")
        is_valid = provider.validate_config()
        if is_valid:
            print("   ✅ Configuration is valid")
        else:
            print("   ❌ Configuration is invalid")
            print("   Check your .env file for missing keys")
            return False

        # Test generation
        print("\n3️⃣  Testing text generation...")
        print("   Sending test prompt...")

        response = await provider.generate(
            prompt="Say 'Hello from AvatarFactory!' and nothing else.",
            temperature=0.5,
            max_tokens=50,
        )

        print(f"   ✅ Response received: {response[:100]}")

        # Test with system prompt
        print("\n4️⃣  Testing with system prompt...")
        response2 = await provider.generate(
            prompt="What is 2+2?",
            system="You are a helpful math tutor. Be concise.",
            temperature=0.3,
            max_tokens=50,
        )

        print(f"   ✅ Response: {response2[:100]}")

        print("\n" + "=" * 60)
        print("✅ All tests passed! Your LLM provider is working correctly.")
        print("=" * 60)

        return True

    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        print("\nMissing dependencies. Install with:")
        print("  pip install openai  # For Azure OpenAI or OpenAI")
        return False

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check your .env file configuration")
        print("2. Verify API keys are correct")
        print("3. For Azure: check endpoint URL")
        print("4. Check internet connection")
        return False


if __name__ == "__main__":
    # Check environment variables
    provider_type = os.getenv("AVATARFACTORY_LLM_PROVIDER", "anthropic")
    print(f"\nConfigured provider: {provider_type}")
    print(f"Model: {os.getenv('AVATARFACTORY_MODEL', 'default')}\n")

    # Run test
    success = asyncio.run(test_provider())

    sys.exit(0 if success else 1)

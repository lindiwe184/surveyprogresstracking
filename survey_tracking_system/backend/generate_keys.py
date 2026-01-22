#!/usr/bin/env python3
"""
Generate secure keys for the Survey Tracking System authentication.
Run this script to generate production-ready secret keys.
"""

import secrets

def generate_keys():
    """Generate secure random keys for authentication."""
    
    print("🔐 Generating Secure Authentication Keys")
    print("=" * 50)
    
    # Generate SECRET_KEY (32 bytes = 256 bits)
    secret_key = secrets.token_urlsafe(32)
    
    # Generate JWT_SECRET_KEY (32 bytes = 256 bits)  
    jwt_secret_key = secrets.token_urlsafe(32)
    
    print("\n📝 Add these to your .env file:")
    print("-" * 30)
    print(f"SECRET_KEY={secret_key}")
    print(f"JWT_SECRET_KEY={jwt_secret_key}")
    
    print("\n⚠️  Important Security Notes:")
    print("• Keep these keys secure and never commit to version control")
    print("• Use different keys for development and production")
    print("• Store production keys in secure environment variables")
    print("• Regenerate keys if ever compromised")
    
    print("\n✅ Keys generated successfully!")

if __name__ == "__main__":
    generate_keys()
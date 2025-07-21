#!/usr/bin/env python3
"""
Test Neo4j authentication with different passwords.
"""

from neo4j import GraphDatabase
import sys

def test_neo4j_connection(password):
    """Test Neo4j connection with given password."""
    try:
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", password))
        with driver.session() as session:
            result = session.run("RETURN 'Connected!' as message")
            message = result.single()["message"]
            print(f"✅ SUCCESS with password: '{password}' - {message}")
            driver.close()
            return True
    except Exception as e:
        print(f"❌ FAILED with password: '{password}' - {e}")
        return False

def main():
    """Test common Neo4j passwords."""
    print("🔍 Testing Neo4j Authentication")
    print("=" * 40)
    
    # Common passwords to try
    passwords_to_try = [
        "password123",
        "password",
        "neo4j",
        "admin",
        "test",
        "",  # Empty password
    ]
    
    for password in passwords_to_try:
        if test_neo4j_connection(password):
            print(f"\n🎉 Found working password: '{password}'")
            print(f"Update your .env file:")
            print(f"NEO4J_PASSWORD={password}")
            return 0
    
    print("\n❌ None of the common passwords worked.")
    print("Please check your Neo4j container setup.")
    return 1

if __name__ == "__main__":
    sys.exit(main())
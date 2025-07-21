#!/usr/bin/env python3
"""
Detailed Neo4j debugging script.
"""

import time
import requests
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

def check_neo4j_http():
    """Check Neo4j HTTP endpoint."""
    try:
        response = requests.get("http://localhost:7474", timeout=5)
        print(f"✅ Neo4j HTTP: Status {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Neo4j HTTP: {e}")
        return False

def test_neo4j_auth_detailed():
    """Test Neo4j authentication with detailed error info."""
    load_dotenv()
    
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    username = os.getenv('NEO4J_USERNAME', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD', 'password123')
    
    print(f"Testing connection:")
    print(f"  URI: {uri}")
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        # Test basic connection
        with driver.session() as session:
            result = session.run("RETURN 'Hello Neo4j!' as message")
            message = result.single()["message"]
            print(f"✅ Connection successful: {message}")
            
            # Test database info
            result = session.run("CALL dbms.components() YIELD name, versions, edition")
            record = result.single()
            if record:
                print(f"✅ Neo4j Version: {record['versions'][0]}")
                print(f"✅ Neo4j Edition: {record['edition']}")
        
        driver.close()
        return True
        
    except Exception as e:
        print(f"❌ Neo4j Connection Failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        return False

def wait_for_neo4j():
    """Wait for Neo4j to be ready."""
    print("🕐 Waiting for Neo4j to be ready...")
    
    for i in range(12):  # Wait up to 2 minutes
        print(f"   Attempt {i+1}/12...")
        
        if check_neo4j_http() and test_neo4j_auth_detailed():
            print("✅ Neo4j is ready!")
            return True
        
        time.sleep(10)
    
    print("❌ Neo4j failed to start within 2 minutes")
    return False

def main():
    """Main debug function."""
    print("🔍 Detailed Neo4j Debug")
    print("=" * 30)
    
    # Check if Neo4j is ready
    if wait_for_neo4j():
        print("\n🎉 Neo4j is working correctly!")
        print("You can now run: python demo_memory_extractor.py")
    else:
        print("\n❌ Neo4j setup failed")
        print("Try recreating the container:")
        print("docker stop neo4j-memory && docker rm neo4j-memory")
        print("docker run -d --name neo4j-memory -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:4.4")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Setup Verification Script for Compliance Memory Management Module.

This script verifies that all prerequisites are properly configured.
"""

import os
import sys
import requests
import redis
from neo4j import GraphDatabase
from dotenv import load_dotenv

def check_ollama():
    """Check if Ollama is running and accessible."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print("✅ Ollama: Running")
            print(f"   Available models: {len(models)}")
            for model in models[:3]:  # Show first 3 models
                print(f"   - {model.get('name', 'Unknown')}")
            return True
        else:
            print("❌ Ollama: Not responding properly")
            return False
    except Exception as e:
        print(f"❌ Ollama: Not accessible - {e}")
        return False

def check_redis():
    """Check if Redis is running and accessible."""
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        info = r.info()
        print("✅ Redis: Running")
        print(f"   Version: {info.get('redis_version', 'Unknown')}")
        print(f"   Memory used: {info.get('used_memory_human', 'Unknown')}")
        return True
    except Exception as e:
        print(f"❌ Redis: Not accessible - {e}")
        return False

def check_neo4j():
    """Check if Neo4j is running and accessible."""
    try:
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password123"))
        with driver.session() as session:
            result = session.run("CALL dbms.components() YIELD name, versions, edition")
            record = result.single()
            if record:
                print("✅ Neo4j: Running")
                print(f"   Version: {record['versions'][0] if record['versions'] else 'Unknown'}")
                print(f"   Edition: {record['edition']}")
                return True
        driver.close()
    except Exception as e:
        print(f"❌ Neo4j: Not accessible - {e}")
        return False

def check_environment():
    """Check environment configuration."""
    load_dotenv()
    
    required_vars = [
        'REDIS_HOST', 'REDIS_PORT', 'NEO4J_URI', 'NEO4J_USERNAME', 
        'NEO4J_PASSWORD', 'OLLAMA_BASE_URL', 'OLLAMA_DEFAULT_MODEL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Environment: Missing variables - {', '.join(missing_vars)}")
        return False
    else:
        print("✅ Environment: All required variables set")
        return True

def check_python_dependencies():
    """Check if required Python packages are installed."""
    required_packages = [
        'redis', 'neo4j', 'requests', 'python-dotenv', 
        'pytest', 'fastapi', 'uvicorn'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Python Dependencies: Missing packages - {', '.join(missing_packages)}")
        print(f"   Install with: pip install {' '.join(missing_packages)}")
        return False
    else:
        print("✅ Python Dependencies: All required packages installed")
        return True

def main():
    """Run all verification checks."""
    print("🔍 Verifying Compliance Memory Management Setup")
    print("=" * 50)
    
    checks = [
        ("Environment Configuration", check_environment),
        ("Python Dependencies", check_python_dependencies),
        ("Ollama LLM Service", check_ollama),
        ("Redis Database", check_redis),
        ("Neo4j Database", check_neo4j),
    ]
    
    results = {}
    for name, check_func in checks:
        print(f"\n📋 Checking {name}...")
        results[name] = check_func()
    
    print("\n" + "=" * 50)
    print("📊 SETUP VERIFICATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All checks passed! System is ready.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
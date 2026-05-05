#!/usr/bin/env python3
"""Quick test of mock-rgs endpoints."""

import requests
import json

BASE_URL = "http://localhost:3008"
SESSION_ID = "test-123"

def test_authenticate():
    """Test authenticate endpoint."""
    print("\n🔐 Testing /wallet/authenticate...")
    response = requests.post(f"{BASE_URL}/wallet/authenticate", json={
        "sessionID": SESSION_ID,
        "language": "en"
    })
    data = response.json()
    print(f"✅ Balance: ${data['balance']['amount']/1000000:.2f}")
    print(f"   Session: {data['sessionID']}")
    return data

def test_play():
    """Test play endpoint with real game engine."""
    print("\n🎰 Testing /wallet/play...")
    response = requests.post(f"{BASE_URL}/wallet/play", json={
        "sessionID": SESSION_ID,
        "amount": 1000000,
        "mode": "base"
    })
    data = response.json()
    book = data.get('book', {})
    print(f"✅ Bet: ${data['betAmount']/1000000:.2f}")
    print(f"   Payout Multiplier: {book.get('payoutMultiplier', 0)/100:.2f}x")
    print(f"   Win: ${data['winAmount']/1000000:.2f}")
    print(f"   Balance: ${data['balance']['amount']/1000000:.2f}")
    print(f"   Events: {len(book.get('events', []))}")
    return data

def test_end_round():
    """Test end-round endpoint."""
    print("\n✅ Testing /wallet/end-round...")
    response = requests.post(f"{BASE_URL}/wallet/end-round", json={
        "sessionID": SESSION_ID
    })
    data = response.json()
    print(f"✅ Final Balance: ${data['balance']['amount']/1000000:.2f}")
    return data

def test_health():
    """Test health check."""
    print("\n❤️  Testing /health...")
    response = requests.get(f"{BASE_URL}/health")
    data = response.json()
    print(f"✅ Status: {data['status']}")
    print(f"   Active Sessions: {data['sessions']}")
    return data

if __name__ == "__main__":
    print("="*60)
    print("🧪 Mock RGS Server Test Suite")
    print("="*60)
    
    try:
        test_health()
        test_authenticate()
        test_play()
        test_end_round()
        
        print("\n" + "="*60)
        print("✅ All tests passed!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("Make sure the server is running: ./start.sh")

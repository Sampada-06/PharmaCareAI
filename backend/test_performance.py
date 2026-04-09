"""
Performance Test Script
Tests the speed of optimized endpoints
"""

import time
import requests
import json

API_BASE = "http://127.0.0.1:8000"

def test_endpoint(name, url, headers=None):
    """Test endpoint performance"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        start = time.time()
        response = requests.get(url, headers=headers, timeout=10)
        duration = time.time() - start
        
        print(f"Status: {response.status_code}")
        print(f"Time: {duration:.3f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Records: {len(data)}")
            elif isinstance(data, dict):
                if 'data' in data:
                    print(f"Records: {len(data['data']) if isinstance(data['data'], list) else 'N/A'}")
                if 'count' in data:
                    print(f"Count: {data['count']}")
        
        # Performance rating
        if duration < 0.5:
            print("⚡ EXCELLENT - Very fast!")
        elif duration < 1.0:
            print("✅ GOOD - Fast enough")
        elif duration < 2.0:
            print("⚠️  ACCEPTABLE - Could be faster")
        else:
            print("❌ SLOW - Needs optimization")
            
        return duration
        
    except requests.exceptions.Timeout:
        print("❌ TIMEOUT - Request took too long (>10s)")
        return 10.0
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return -1

def main():
    print("\n" + "="*60)
    print("PHARMACY APP PERFORMANCE TEST")
    print("="*60)
    
    # Test public endpoints (no auth needed)
    tests = [
        ("Medicines List", f"{API_BASE}/medicines"),
        ("Categories", f"{API_BASE}/categories"),
        ("Admin Orders", f"{API_BASE}/admin/orders"),
        ("Dashboard Stats", f"{API_BASE}/api/admin/dashboard/stats"),
        ("Inventory All", f"{API_BASE}/api/admin/inventory/all"),
        ("Low Stock Items", f"{API_BASE}/api/admin/inventory/low-stock"),
        ("Delivery Orders", f"{API_BASE}/api/delivery-agency/orders"),
    ]
    
    results = {}
    total_time = 0
    
    for name, url in tests:
        duration = test_endpoint(name, url)
        if duration > 0:
            results[name] = duration
            total_time += duration
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    
    if results:
        avg_time = total_time / len(results)
        print(f"\nTotal Tests: {len(results)}")
        print(f"Total Time: {total_time:.3f} seconds")
        print(f"Average Time: {avg_time:.3f} seconds")
        
        print("\n📊 Results by Speed:")
        sorted_results = sorted(results.items(), key=lambda x: x[1])
        for name, duration in sorted_results:
            status = "⚡" if duration < 0.5 else "✅" if duration < 1.0 else "⚠️" if duration < 2.0 else "❌"
            print(f"  {status} {name}: {duration:.3f}s")
        
        # Overall rating
        print("\n🎯 Overall Performance:")
        if avg_time < 0.5:
            print("  ⚡ EXCELLENT - System is very fast!")
        elif avg_time < 1.0:
            print("  ✅ GOOD - System performance is acceptable")
        elif avg_time < 2.0:
            print("  ⚠️  ACCEPTABLE - Some optimization recommended")
        else:
            print("  ❌ SLOW - Optimization needed")
    else:
        print("\n❌ No successful tests")
    
    print("\n" + "="*60)
    print("Test complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()

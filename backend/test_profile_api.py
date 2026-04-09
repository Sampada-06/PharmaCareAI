"""
Test script to verify profile API endpoints work correctly
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_profile_flow():
    """Test complete profile flow: register, login, view, update"""
    
    print("=" * 60)
    print("PROFILE API TEST")
    print("=" * 60)
    
    # Test data
    test_user = {
        "name": "Test User Profile",
        "email": f"testprofile{hash('test')}@example.com",
        "phone": "9876543210",
        "password": "testpass123"
    }
    
    # 1. Register new user
    print("\n1️⃣  Registering new user...")
    try:
        response = requests.post(f"{BASE_URL}/register", json=test_user)
        if response.status_code == 200:
            print("✅ Registration successful")
        else:
            print(f"⚠️  Registration response: {response.status_code}")
            print(f"   Using existing user for testing")
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return
    
    # 2. Login
    print("\n2️⃣  Logging in...")
    try:
        login_data = {
            "username": test_user["email"],
            "password": test_user["password"]
        }
        response = requests.post(
            f"{BASE_URL}/login",
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            user_data = data.get("user")
            print("✅ Login successful")
            print(f"   User ID: {user_data.get('id')[:8]}...")
            print(f"   Name: {user_data.get('name')}")
            print(f"   Email: {user_data.get('email')}")
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Get current user profile
    print("\n3️⃣  Fetching profile (GET /me)...")
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers)
        if response.status_code == 200:
            profile = response.json()
            print("✅ Profile fetched successfully")
            print(f"   Name: {profile.get('name')}")
            print(f"   Email: {profile.get('email')}")
            print(f"   Phone: {profile.get('phone')}")
            print(f"   Blood Group: {profile.get('blood_group') or 'Not set'}")
            print(f"   Allergies: {profile.get('allergies') or 'Not set'}")
        else:
            print(f"❌ Failed to fetch profile: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Profile fetch failed: {e}")
        return
    
    # 4. Update profile
    print("\n4️⃣  Updating profile (PATCH /me)...")
    try:
        update_data = {
            "phone": "1234567890",
            "date_of_birth": "1990-01-15",
            "blood_group": "O+",
            "allergies": "Penicillin, Peanuts",
            "chronic_conditions": "Hypertension",
            "current_medications": "Amlodipine 5mg",
            "primary_doctor": "Dr. Smith"
        }
        
        response = requests.patch(
            f"{BASE_URL}/me",
            json=update_data,
            headers=headers
        )
        
        if response.status_code == 200:
            updated_profile = response.json()
            print("✅ Profile updated successfully")
            print(f"   Phone: {updated_profile.get('phone')}")
            print(f"   DOB: {updated_profile.get('date_of_birth')}")
            print(f"   Blood Group: {updated_profile.get('blood_group')}")
            print(f"   Allergies: {updated_profile.get('allergies')}")
            print(f"   Conditions: {updated_profile.get('chronic_conditions')}")
            print(f"   Medications: {updated_profile.get('current_medications')}")
            print(f"   Doctor: {updated_profile.get('primary_doctor')}")
        else:
            print(f"❌ Profile update failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return
    except Exception as e:
        print(f"❌ Profile update failed: {e}")
        return
    
    # 5. Verify update persisted
    print("\n5️⃣  Verifying update persisted...")
    try:
        response = requests.get(f"{BASE_URL}/me", headers=headers)
        if response.status_code == 200:
            profile = response.json()
            
            # Check if updates persisted
            checks = [
                ("Phone", profile.get('phone') == "1234567890"),
                ("Blood Group", profile.get('blood_group') == "O+"),
                ("Allergies", profile.get('allergies') == "Penicillin, Peanuts"),
                ("Conditions", profile.get('chronic_conditions') == "Hypertension"),
                ("Medications", profile.get('current_medications') == "Amlodipine 5mg"),
                ("Doctor", profile.get('primary_doctor') == "Dr. Smith")
            ]
            
            all_passed = True
            for field, passed in checks:
                status = "✅" if passed else "❌"
                print(f"   {status} {field}: {'Persisted' if passed else 'Failed'}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print("\n🎉 All tests passed! Profile feature working correctly.")
            else:
                print("\n⚠️  Some checks failed. Review the output above.")
        else:
            print(f"❌ Failed to verify: {response.status_code}")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    print("\n⚠️  Make sure the backend is running on http://127.0.0.1:8000")
    print("   Run: uvicorn app.main:app --reload --port 8000\n")
    
    try:
        # Check if backend is running
        response = requests.get(f"{BASE_URL}/docs", timeout=2)
        if response.status_code == 200:
            test_profile_flow()
        else:
            print("❌ Backend is not responding correctly")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Please start the backend server first.")
    except Exception as e:
        print(f"❌ Error: {e}")

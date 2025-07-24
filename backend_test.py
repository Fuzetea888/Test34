#!/usr/bin/env python3
"""
Comprehensive Backend API Tests for Family Dom Maroc
Tests authentication, provider profiles, booking system, and data validation
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import sys
import os

# Get backend URL from frontend .env file
def get_backend_url():
    try:
        with open('/app/frontend/.env', 'r') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    return line.split('=', 1)[1].strip()
    except:
        pass
    return "https://f920b57e-30c2-4106-8448-57fe4b3eef03.preview.emergentagent.com"

BASE_URL = get_backend_url() + "/api"
print(f"Testing backend at: {BASE_URL}")

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def assert_test(self, condition, test_name, error_msg=""):
        if condition:
            print(f"✅ {test_name}")
            self.passed += 1
        else:
            print(f"❌ {test_name}: {error_msg}")
            self.failed += 1
            self.errors.append(f"{test_name}: {error_msg}")
            
    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"Total: {self.passed + self.failed}")
        
        if self.errors:
            print(f"\n{'='*60}")
            print("FAILED TESTS:")
            print(f"{'='*60}")
            for error in self.errors:
                print(f"• {error}")

# Global test results
results = TestResults()

def test_health_check():
    """Test basic API health check"""
    print(f"\n{'='*60}")
    print("TESTING: API Health Check")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}/", timeout=10)
        results.assert_test(
            response.status_code == 200,
            "API Health Check",
            f"Expected 200, got {response.status_code}"
        )
        
        if response.status_code == 200:
            data = response.json()
            results.assert_test(
                "Family Dom Maroc API" in data.get("message", ""),
                "API Message Check",
                f"Unexpected message: {data}"
            )
    except Exception as e:
        results.assert_test(False, "API Health Check", f"Connection error: {str(e)}")

def test_user_registration():
    """Test user registration for both client and provider types"""
    print(f"\n{'='*60}")
    print("TESTING: User Registration System")
    print(f"{'='*60}")
    
    # Test client registration
    client_data = {
        "email": f"client_{uuid.uuid4().hex[:8]}@familydom.ma",
        "password": "SecurePass123!",
        "full_name": "Amina Benali",
        "phone": "+212661234567",
        "user_type": "client",
        "city": "Casablanca",
        "address": "123 Rue Mohammed V, Casablanca"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=client_data, timeout=10)
        results.assert_test(
            response.status_code == 200,
            "Client Registration",
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        )
        
        if response.status_code == 200:
            data = response.json()
            results.assert_test(
                "access_token" in data,
                "Client Registration Token",
                "No access token in response"
            )
            results.assert_test(
                data.get("user", {}).get("user_type") == "client",
                "Client User Type",
                f"Expected client, got {data.get('user', {}).get('user_type')}"
            )
            
            # Store client token for later tests
            global client_token, client_user_id
            client_token = data["access_token"]
            client_user_id = data["user"]["id"]
            
    except Exception as e:
        results.assert_test(False, "Client Registration", f"Request error: {str(e)}")
    
    # Test provider registration
    provider_data = {
        "email": f"provider_{uuid.uuid4().hex[:8]}@familydom.ma",
        "password": "SecurePass123!",
        "full_name": "Youssef Alami",
        "phone": "+212662345678",
        "user_type": "provider",
        "city": "Rabat",
        "address": "456 Avenue Hassan II, Rabat"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=provider_data, timeout=10)
        results.assert_test(
            response.status_code == 200,
            "Provider Registration",
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        )
        
        if response.status_code == 200:
            data = response.json()
            results.assert_test(
                "access_token" in data,
                "Provider Registration Token",
                "No access token in response"
            )
            results.assert_test(
                data.get("user", {}).get("user_type") == "provider",
                "Provider User Type",
                f"Expected provider, got {data.get('user', {}).get('user_type')}"
            )
            
            # Store provider token for later tests
            global provider_token, provider_user_id
            provider_token = data["access_token"]
            provider_user_id = data["user"]["id"]
            
    except Exception as e:
        results.assert_test(False, "Provider Registration", f"Request error: {str(e)}")

def test_user_login():
    """Test user login functionality"""
    print(f"\n{'='*60}")
    print("TESTING: User Login System")
    print(f"{'='*60}")
    
    # Test with invalid credentials
    invalid_login = {
        "email": "nonexistent@familydom.ma",
        "password": "wrongpassword"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json=invalid_login, timeout=10)
        results.assert_test(
            response.status_code == 401,
            "Invalid Login Rejection",
            f"Expected 401, got {response.status_code}"
        )
    except Exception as e:
        results.assert_test(False, "Invalid Login Test", f"Request error: {str(e)}")

def test_profile_access():
    """Test profile access with authentication"""
    print(f"\n{'='*60}")
    print("TESTING: Profile Access System")
    print(f"{'='*60}")
    
    # Test without authentication
    try:
        response = requests.get(f"{BASE_URL}/profile", timeout=10)
        results.assert_test(
            response.status_code == 403,
            "Unauthenticated Profile Access",
            f"Expected 403, got {response.status_code}"
        )
    except Exception as e:
        results.assert_test(False, "Unauthenticated Profile Test", f"Request error: {str(e)}")
    
    # Test with client authentication
    if 'client_token' in globals():
        headers = {"Authorization": f"Bearer {client_token}"}
        try:
            response = requests.get(f"{BASE_URL}/profile", headers=headers, timeout=10)
            results.assert_test(
                response.status_code == 200,
                "Client Profile Access",
                f"Expected 200, got {response.status_code}. Response: {response.text}"
            )
            
            if response.status_code == 200:
                data = response.json()
                results.assert_test(
                    data.get("user_type") == "client",
                    "Client Profile Data",
                    f"Expected client user type, got {data.get('user_type')}"
                )
        except Exception as e:
            results.assert_test(False, "Client Profile Access", f"Request error: {str(e)}")

def test_provider_profile_system():
    """Test provider profile creation and retrieval"""
    print(f"\n{'='*60}")
    print("TESTING: Provider Profile System")
    print(f"{'='*60}")
    
    if 'provider_token' not in globals():
        results.assert_test(False, "Provider Profile Test", "No provider token available")
        return
    
    headers = {"Authorization": f"Bearer {provider_token}"}
    
    # Test provider profile creation
    profile_data = {
        "services": ["menage", "bricolage"],
        "hourly_rate": {
            "menage": 80.0,
            "bricolage": 120.0
        },
        "experience_years": 5,
        "description": "Professionnel expérimenté en ménage et bricolage à Rabat. Service de qualité garantie.",
        "availability": {
            "monday": ["09:00", "10:00", "11:00", "14:00", "15:00"],
            "tuesday": ["09:00", "10:00", "11:00", "14:00", "15:00"],
            "wednesday": ["09:00", "10:00", "11:00"],
            "thursday": ["14:00", "15:00", "16:00"],
            "friday": ["09:00", "10:00", "11:00", "14:00", "15:00"]
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/provider/profile", json=profile_data, headers=headers, timeout=10)
        results.assert_test(
            response.status_code == 200,
            "Provider Profile Creation",
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        )
        
        if response.status_code == 200:
            data = response.json()
            results.assert_test(
                "menage" in data.get("services", []),
                "Provider Services Check",
                f"Expected menage in services, got {data.get('services')}"
            )
            results.assert_test(
                data.get("hourly_rate", {}).get("menage") == 80.0,
                "Provider Hourly Rate Check",
                f"Expected 80.0 for menage, got {data.get('hourly_rate', {}).get('menage')}"
            )
            
            global provider_profile_id
            provider_profile_id = data.get("id")
            
    except Exception as e:
        results.assert_test(False, "Provider Profile Creation", f"Request error: {str(e)}")
    
    # Test provider profile retrieval
    try:
        response = requests.get(f"{BASE_URL}/provider/profile", headers=headers, timeout=10)
        results.assert_test(
            response.status_code == 200,
            "Provider Profile Retrieval",
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        )
    except Exception as e:
        results.assert_test(False, "Provider Profile Retrieval", f"Request error: {str(e)}")

def test_provider_discovery():
    """Test provider discovery functionality"""
    print(f"\n{'='*60}")
    print("TESTING: Provider Discovery System")
    print(f"{'='*60}")
    
    try:
        # Test getting all providers
        response = requests.get(f"{BASE_URL}/providers", timeout=10)
        results.assert_test(
            response.status_code == 200,
            "Provider Discovery",
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        )
        
        if response.status_code == 200:
            data = response.json()
            results.assert_test(
                isinstance(data, list),
                "Provider List Format",
                f"Expected list, got {type(data)}"
            )
            
            # Test filtering by service
            response = requests.get(f"{BASE_URL}/providers?service=menage", timeout=10)
            results.assert_test(
                response.status_code == 200,
                "Provider Service Filter",
                f"Expected 200, got {response.status_code}"
            )
            
    except Exception as e:
        results.assert_test(False, "Provider Discovery", f"Request error: {str(e)}")

def test_booking_system():
    """Test booking creation and management"""
    print(f"\n{'='*60}")
    print("TESTING: Booking System")
    print(f"{'='*60}")
    
    if 'client_token' not in globals() or 'provider_user_id' not in globals():
        results.assert_test(False, "Booking System Test", "Missing client token or provider ID")
        return
    
    headers = {"Authorization": f"Bearer {client_token}"}
    
    # Test booking creation
    booking_data = {
        "provider_id": provider_user_id,
        "service_category": "menage",
        "scheduled_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "duration_hours": 3,
        "address": "789 Boulevard Zerktouni, Casablanca",
        "notes": "Nettoyage complet de l'appartement, cuisine et salle de bain incluses"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/bookings", json=booking_data, headers=headers, timeout=10)
        results.assert_test(
            response.status_code == 200,
            "Booking Creation",
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        )
        
        if response.status_code == 200:
            data = response.json()
            results.assert_test(
                data.get("service_category") == "menage",
                "Booking Service Category",
                f"Expected menage, got {data.get('service_category')}"
            )
            results.assert_test(
                data.get("status") == "pending",
                "Booking Initial Status",
                f"Expected pending, got {data.get('status')}"
            )
            results.assert_test(
                data.get("total_price") > 0,
                "Booking Price Calculation",
                f"Expected price > 0, got {data.get('total_price')}"
            )
            
            global booking_id
            booking_id = data.get("id")
            
    except Exception as e:
        results.assert_test(False, "Booking Creation", f"Request error: {str(e)}")
    
    # Test booking retrieval
    try:
        response = requests.get(f"{BASE_URL}/bookings", headers=headers, timeout=10)
        results.assert_test(
            response.status_code == 200,
            "Booking Retrieval",
            f"Expected 200, got {response.status_code}. Response: {response.text}"
        )
        
        if response.status_code == 200:
            data = response.json()
            results.assert_test(
                isinstance(data, list),
                "Booking List Format",
                f"Expected list, got {type(data)}"
            )
            
    except Exception as e:
        results.assert_test(False, "Booking Retrieval", f"Request error: {str(e)}")

def test_service_categories():
    """Test service category validation"""
    print(f"\n{'='*60}")
    print("TESTING: Service Categories")
    print(f"{'='*60}")
    
    if 'provider_token' not in globals():
        results.assert_test(False, "Service Categories Test", "No provider token available")
        return
    
    headers = {"Authorization": f"Bearer {provider_token}"}
    
    # Test valid service categories
    valid_services = ["menage", "garde_enfants", "bricolage", "jardinage", "soutien_scolaire", "aide_seniors"]
    
    for service in valid_services:
        profile_data = {
            "services": [service],
            "hourly_rate": {service: 100.0},
            "experience_years": 3,
            "description": f"Expert en {service}",
            "availability": {"monday": ["09:00", "10:00"]}
        }
        
        # Create a new provider for each test to avoid conflicts
        provider_email = f"test_provider_{service}_{uuid.uuid4().hex[:8]}@familydom.ma"
        new_provider_data = {
            "email": provider_email,
            "password": "SecurePass123!",
            "full_name": f"Provider {service}",
            "phone": "+212663456789",
            "user_type": "provider",
            "city": "Marrakech",
            "address": "Test Address"
        }
        
        try:
            # Register new provider
            reg_response = requests.post(f"{BASE_URL}/auth/register", json=new_provider_data, timeout=10)
            if reg_response.status_code == 200:
                new_token = reg_response.json()["access_token"]
                new_headers = {"Authorization": f"Bearer {new_token}"}
                
                # Test profile creation with this service
                response = requests.post(f"{BASE_URL}/provider/profile", json=profile_data, headers=new_headers, timeout=10)
                results.assert_test(
                    response.status_code == 200,
                    f"Service Category: {service}",
                    f"Expected 200, got {response.status_code} for service {service}"
                )
        except Exception as e:
            results.assert_test(False, f"Service Category: {service}", f"Request error: {str(e)}")

def test_moroccan_cities():
    """Test with Moroccan cities"""
    print(f"\n{'='*60}")
    print("TESTING: Moroccan Cities Integration")
    print(f"{'='*60}")
    
    moroccan_cities = ["Casablanca", "Rabat", "Marrakech", "Fès", "Tanger", "Agadir", "Meknès", "Oujda"]
    
    for city in moroccan_cities:
        user_data = {
            "email": f"user_{city.lower()}_{uuid.uuid4().hex[:8]}@familydom.ma",
            "password": "SecurePass123!",
            "full_name": f"User from {city}",
            "phone": "+212664567890",
            "user_type": "client",
            "city": city,
            "address": f"Test Address, {city}"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/auth/register", json=user_data, timeout=10)
            results.assert_test(
                response.status_code == 200,
                f"Registration in {city}",
                f"Expected 200, got {response.status_code} for city {city}"
            )
            
            if response.status_code == 200:
                data = response.json()
                results.assert_test(
                    data.get("user", {}).get("city") == city,
                    f"City Data for {city}",
                    f"Expected {city}, got {data.get('user', {}).get('city')}"
                )
        except Exception as e:
            results.assert_test(False, f"Registration in {city}", f"Request error: {str(e)}")

def test_error_handling():
    """Test error handling for invalid inputs"""
    print(f"\n{'='*60}")
    print("TESTING: Error Handling & Data Validation")
    print(f"{'='*60}")
    
    # Test duplicate email registration
    duplicate_data = {
        "email": "duplicate@familydom.ma",
        "password": "SecurePass123!",
        "full_name": "First User",
        "phone": "+212665678901",
        "user_type": "client",
        "city": "Casablanca",
        "address": "Test Address"
    }
    
    try:
        # Register first user
        response1 = requests.post(f"{BASE_URL}/auth/register", json=duplicate_data, timeout=10)
        # Try to register same email again
        response2 = requests.post(f"{BASE_URL}/auth/register", json=duplicate_data, timeout=10)
        
        results.assert_test(
            response2.status_code == 400,
            "Duplicate Email Rejection",
            f"Expected 400, got {response2.status_code}"
        )
    except Exception as e:
        results.assert_test(False, "Duplicate Email Test", f"Request error: {str(e)}")
    
    # Test invalid email format
    invalid_email_data = {
        "email": "invalid-email-format",
        "password": "SecurePass123!",
        "full_name": "Test User",
        "phone": "+212666789012",
        "user_type": "client",
        "city": "Rabat",
        "address": "Test Address"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=invalid_email_data, timeout=10)
        results.assert_test(
            response.status_code == 422,
            "Invalid Email Format Rejection",
            f"Expected 422, got {response.status_code}"
        )
    except Exception as e:
        results.assert_test(False, "Invalid Email Test", f"Request error: {str(e)}")

def run_all_tests():
    """Run all backend tests"""
    print("🚀 Starting Family Dom Maroc Backend API Tests")
    print(f"Backend URL: {BASE_URL}")
    
    # Initialize global variables
    global client_token, provider_token, client_user_id, provider_user_id
    client_token = None
    provider_token = None
    client_user_id = None
    provider_user_id = None
    
    # Run tests in order
    test_health_check()
    test_user_registration()
    test_user_login()
    test_profile_access()
    test_provider_profile_system()
    test_provider_discovery()
    test_booking_system()
    test_service_categories()
    test_moroccan_cities()
    test_error_handling()
    
    # Print final results
    results.print_summary()
    
    return results.failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
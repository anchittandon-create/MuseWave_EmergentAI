#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
import time

class MuzifyAPITester:
    def __init__(self, base_url="https://muzify-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.test_user = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details="", endpoint=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test_name": name,
            "success": success,
            "endpoint": endpoint,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if details:
            print(f"    Details: {details}")
        print()

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            details = f"Status: {response.status_code}, Expected: {expected_status}"
            
            if success:
                try:
                    response_data = response.json()
                    details += f", Response: {json.dumps(response_data, indent=2)[:200]}..."
                    self.log_test(name, True, details, endpoint)
                    return True, response_data
                except:
                    details += f", Response: {response.text[:200]}..."
                    self.log_test(name, True, details, endpoint)
                    return True, {}
            else:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data}"
                except:
                    details += f", Error: {response.text[:200]}..."
                self.log_test(name, False, details, endpoint)
                return False, {}

        except Exception as e:
            self.log_test(name, False, f"Exception: {str(e)}", endpoint)
            return False, {}

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("🔍 Testing Health Endpoints...")
        
        # Test root endpoint
        self.run_test("API Root", "GET", "", 200)
        
        # Test health endpoint
        self.run_test("Health Check", "GET", "health", 200)

    def test_auth_flow(self):
        """Test authentication endpoints"""
        print("🔍 Testing Authentication Flow...")
        
        # Generate unique mobile number for testing
        timestamp = int(time.time())
        test_mobile = f"9876543{timestamp % 1000:03d}"
        test_name = f"Test User {timestamp % 1000}"
        
        # Test signup
        signup_data = {
            "name": test_name,
            "mobile": test_mobile
        }
        success, response = self.run_test("User Signup", "POST", "auth/signup", 200, signup_data)
        
        if success and 'id' in response:
            self.test_user = response
            print(f"    Created test user: {test_name} ({test_mobile})")
        
        # Test duplicate signup (should fail)
        self.run_test("Duplicate Signup", "POST", "auth/signup", 400, signup_data)
        
        # Test login with existing mobile
        login_data = {"mobile": test_mobile}
        success, response = self.run_test("User Login", "POST", "auth/login", 200, login_data)
        
        # Test login with non-existent mobile
        fake_login_data = {"mobile": "0000000000"}
        self.run_test("Login Non-existent User", "POST", "auth/login", 404, fake_login_data)

    def test_options_endpoints(self):
        """Test genre and language options"""
        print("🔍 Testing Options Endpoints...")
        
        # Test genres endpoint
        success, genres_data = self.run_test("Get Genres", "GET", "genres", 200)
        if success and 'genres' in genres_data:
            print(f"    Found {len(genres_data['genres'])} genres")
        
        # Test languages endpoint
        success, langs_data = self.run_test("Get Languages", "GET", "languages", 200)
        if success and 'languages' in langs_data:
            print(f"    Found {len(langs_data['languages'])} languages")

    def test_ai_suggestions(self):
        """Test AI suggestion endpoint"""
        print("🔍 Testing AI Suggestions...")
        
        # Test music prompt suggestion
        suggest_data = {
            "field": "music_prompt",
            "current_value": "upbeat electronic",
            "context": {
                "genres": ["Electronic", "Pop"],
                "lyrics": "energetic dance track"
            }
        }
        success, response = self.run_test("AI Suggest Music Prompt", "POST", "suggest", 200, suggest_data)
        
        if success and 'suggestion' in response:
            print(f"    AI Suggestion: {response['suggestion'][:100]}...")
        
        # Test title suggestion
        title_suggest_data = {
            "field": "title",
            "current_value": "",
            "context": {"music_prompt": "dreamy ambient soundscape"}
        }
        self.run_test("AI Suggest Title", "POST", "suggest", 200, title_suggest_data)

    def test_song_creation(self):
        """Test song creation and retrieval"""
        print("🔍 Testing Song Creation...")
        
        if not self.test_user:
            print("❌ No test user available for song creation")
            return None
        
        # Test single song creation
        song_data = {
            "title": "Test Song",
            "music_prompt": "A dreamy, atmospheric track with soft synths and gentle percussion",
            "genres": ["Electronic", "Ambient"],
            "duration_seconds": 180,
            "vocal_languages": ["Instrumental"],
            "lyrics": "Peaceful and serene",
            "artist_inspiration": "Brian Eno, Boards of Canada",
            "generate_video": False,
            "video_style": "",
            "mode": "single",
            "user_id": self.test_user['id']
        }
        
        success, song_response = self.run_test("Create Single Song", "POST", "songs/create", 200, song_data)
        
        if success and 'id' in song_response:
            song_id = song_response['id']
            print(f"    Created song: {song_response.get('title', 'Unknown')} (ID: {song_id})")
            
            # Test get user songs
            self.run_test("Get User Songs", "GET", f"songs/user/{self.test_user['id']}", 200)
            
            return song_id
        
        return None

    def test_album_creation(self):
        """Test album creation and retrieval"""
        print("🔍 Testing Album Creation...")
        
        if not self.test_user:
            print("❌ No test user available for album creation")
            return None
        
        # Test album creation
        album_data = {
            "title": "Test Album",
            "music_prompt": "A cohesive collection of electronic ambient tracks",
            "genres": ["Electronic", "Ambient"],
            "vocal_languages": ["Instrumental"],
            "lyrics": "Atmospheric and contemplative",
            "artist_inspiration": "Aphex Twin, Autechre",
            "generate_video": False,
            "video_style": "",
            "num_songs": 3,
            "user_id": self.test_user['id']
        }
        
        success, album_response = self.run_test("Create Album", "POST", "albums/create", 200, album_data)
        
        if success and 'id' in album_response:
            album_id = album_response['id']
            print(f"    Created album: {album_response.get('title', 'Unknown')} (ID: {album_id})")
            print(f"    Album contains {len(album_response.get('songs', []))} songs")
            
            # Test get user albums
            self.run_test("Get User Albums", "GET", f"albums/user/{self.test_user['id']}", 200)
            
            return album_id
        
        return None

    def test_dashboard(self):
        """Test dashboard endpoint"""
        print("🔍 Testing Dashboard...")
        
        if not self.test_user:
            print("❌ No test user available for dashboard test")
            return
        
        success, dashboard_data = self.run_test("Get Dashboard", "GET", f"dashboard/{self.test_user['id']}", 200)
        
        if success:
            songs_count = len(dashboard_data.get('songs', []))
            albums_count = len(dashboard_data.get('albums', []))
            print(f"    Dashboard shows {songs_count} songs and {albums_count} albums")

    def test_error_cases(self):
        """Test various error scenarios"""
        print("🔍 Testing Error Cases...")
        
        # Test song creation without required fields
        invalid_song_data = {
            "music_prompt": "",  # Empty required field
            "user_id": "invalid-user-id"
        }
        self.run_test("Create Song - Invalid Data", "POST", "songs/create", 422, invalid_song_data)
        
        # Test invalid endpoints
        self.run_test("Invalid Endpoint", "GET", "nonexistent", 404)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Muzify API Tests")
        print("=" * 50)
        
        start_time = time.time()
        
        # Run test suites
        self.test_health_endpoints()
        self.test_auth_flow()
        self.test_options_endpoints()
        self.test_ai_suggestions()
        self.test_song_creation()
        self.test_album_creation()
        self.test_dashboard()
        self.test_error_cases()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        print("=" * 50)
        print("🏁 Test Summary")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100):.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        if self.test_user:
            print(f"Test User: {self.test_user['name']} ({self.test_user['mobile']})")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = MuzifyAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test execution failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
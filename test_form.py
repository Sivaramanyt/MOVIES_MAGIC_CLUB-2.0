# test_form.py

import requests

# Test data - replace with your actual server URL
data = {
    "title": "TEST MOVIE DEBUG",
    "year": "2024",
    "quality": "HD",
    "category": "Action",
    "languages": ["Tamil"],
    "description": "Testing quality links",
    "quality_480p_watch": "https://example.com/watch-480p-test",
    "quality_480p_download": "https://example.com/download-480p-test",
    "quality_720p_watch": "https://example.com/watch-720p-test",
    "quality_720p_download": "https://example.com/download-720p-test",
}

# Send POST request to your admin endpoint
response = requests.post("http://localhost:8000/admin/movies", data=data)

print("Status Code:", response.status_code)
print("Redirected to:", response.url)
print("\nCheck your server logs - did it print the debug messages?")
print("Check MongoDB - did it save the qualities field?")

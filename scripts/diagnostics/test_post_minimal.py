#!/usr/bin/env python
"""Test minimal POST endpoint."""

import requests

try:
    response = requests.post("http://localhost:8000/api/v1/tasks/test-post-minimal", timeout=5)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

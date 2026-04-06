import os
import requests

# Configuration
URL = "https://api.spctek.ai:8000/deploy"


def trigger_deploy():
    # Fetch the password from the environment variable 'DEPLOY_PASSWORD'
    password = os.getenv("DEPLOY_PASSWORD")

    if not password:
        print("❌ Error: 'DEPLOY_PASSWORD' environment variable is not set.")
        return

    payload = {"password": password}

    try:
        print(f"🚀 Triggering deployment at {URL}...")
        response = requests.post(URL, json=payload, timeout=60)

        if response.status_code == 200:
            print("✅ Success!")
            print("Server Response:", response.json())
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            print("Error:", response.text)

    except Exception as e:
        print(f"⚠️ An error occurred: {e}")


if __name__ == "__main__":
    trigger_deploy()

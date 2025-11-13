import os

import requests

ACCOUNT_ID = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
API_TOKEN = os.environ.get("CLOUDFLARE_API_TOKEN")

url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/workers/scripts"
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

resp = requests.get(url, headers=headers)
if resp.status_code == 200:
    for script in resp.json().get('result', []):
        print(f"Name: {script['id']}, Last Modified: {script['modified_on']}, Size: {script['size']} bytes")
    print(f"Total Workers: {len(resp.json().get('result', []))}")
else:
    print(f"Error: {resp.status_code} - {resp.text}")

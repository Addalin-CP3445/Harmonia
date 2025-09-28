import os, json, requests
from dotenv import load_dotenv
load_dotenv()

# Nuke proxies in this process
for k in ["HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy","ALL_PROXY","all_proxy","NO_PROXY","no_proxy"]:
    os.environ.pop(k, None)

cid = os.getenv("SPOTIFY_CLIENT_ID")
sec = os.getenv("SPOTIFY_CLIENT_SECRET")
assert cid and sec, "Missing CLIENT ID/SECRET"

# 1) get client-credentials token
r = requests.post(
    "https://accounts.spotify.com/api/token",
    data={"grant_type":"client_credentials"},
    auth=(cid, sec),
    timeout=15
)
print("token status:", r.status_code)
print("token body:", r.text[:200])
r.raise_for_status()
tok = r.json()["access_token"]

# 2) call the seeds endpoint directly
h = {"Authorization": f"Bearer {tok}"}
u = "https://api.spotify.com/v1/recommendations/available-genre-seeds"
r2 = requests.get(u, headers=h, timeout=15)
print("seeds status:", r2.status_code)
print("seeds body (first 400 chars):\n", r2.text[:400])

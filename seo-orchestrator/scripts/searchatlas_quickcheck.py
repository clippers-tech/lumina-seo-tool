import json, os, sys, time
from datetime import datetime, timezone
import urllib.request

API_KEY = "6d64cc823eccbb9865cfa2d0b45aa3e5"

URLS = {
  "rank_tracker_luminaclippers": "https://keyword.searchatlas.com/api/v1/projects/70664/keywords/?searchatlas_api_key="+API_KEY,
  "rank_tracker_luminaweb3": "https://keyword.searchatlas.com/api/v1/projects/69275/keywords/?searchatlas_api_key="+API_KEY,
  "otto_luminaclippers": "https://sa.searchatlas.com/api/v2/otto-projects/6bef1a80-9a02-4969-b84b-42def0a6f238/",
  "otto_luminaweb3": "https://sa.searchatlas.com/api/v2/otto-projects/b3ba4228-c4fe-46ef-bceb-d4dd769faa85/",
  "press_releases": "https://ca.searchatlas.com/api/cg/v1/press-release/",
  "cloud_stacks": "https://ca.searchatlas.com/api/cg/v1/cloud-stack-contents/",
}


def fetch(url, headers=None):
  req = urllib.request.Request(url, headers=headers or {})
  try:
    with urllib.request.urlopen(req, timeout=30) as resp:
      body = resp.read()
      ct = resp.headers.get('content-type','')
      return {"ok": True, "status": resp.status, "content_type": ct, "body": body.decode('utf-8', errors='replace')}
  except Exception as e:
    return {"ok": False, "error": str(e)}


def main():
  out = {"observed_at_utc": datetime.now(timezone.utc).isoformat().replace('+00:00','Z')}
  # rank tracker (no headers)
  out["rank_tracker"] = {}
  for k in ["rank_tracker_luminaclippers","rank_tracker_luminaweb3"]:
    out["rank_tracker"][k] = fetch(URLS[k])
  # otto + cg need x-api-key
  headers = {"x-api-key": API_KEY, "accept":"application/json"}
  out["otto"] = {
    "luminaclippers": fetch(URLS["otto_luminaclippers"], headers=headers),
    "luminaweb3": fetch(URLS["otto_luminaweb3"], headers=headers),
  }
  out["authority_assets"] = {
    "press_releases": fetch(URLS["press_releases"], headers=headers),
    "cloud_stacks": fetch(URLS["cloud_stacks"], headers=headers),
  }
  print(json.dumps(out))

if __name__ == "__main__":
  main()

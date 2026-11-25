def upsert_jobs(jobs: list[dict]) -> None:
    if not jobs:
        return
    parsed = urllib.parse.urlparse(SUPABASE_URL)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    endpoint = f"{base_url}/rest/v1/job_drops?on_conflict=dedupe_key"
    print(f"Target Supabase host: {parsed.netloc}")
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    resp = requests.post(endpoint, headers=headers, json=jobs, timeout=20)
    if not resp.ok:
        print(f"Supabase error {resp.status_code}: {resp.text}")
    resp.raise_for_status()

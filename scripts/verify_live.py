#!/usr/bin/env python3
"""Wait finitely for the approved Pages deployment, then verify its exact files."""
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
import json
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
BASE = 'https://ksloenglish.github.io/tie-261013/'
DEADLINE = 480
start = time.monotonic()
last_progress = start
expected = (SITE/'index.html').read_bytes()

def fetch(path: str) -> bytes:
    url = BASE + quote(path, safe='/-_.~')
    request = Request(url,headers={'User-Agent':'WorkshopSiteVerification/1.0','Cache-Control':'no-cache'})
    with urlopen(request, timeout=30) as response:
        assert response.status == 200, (path,response.status)
        return response.read()

while True:
    elapsed = time.monotonic()-start
    try:
        actual = fetch('index.html')
        if actual == expected:
            print(f'Published homepage matches the approved site after {elapsed:.0f}s.',flush=True)
            break
        state = 'homepage not yet the expected version'
    except Exception as error:
        state = type(error).__name__ + ': ' + str(error)[:120]
    print(f'GitHub Pages: {state}; elapsed {elapsed:.0f}s; last progress {time.monotonic()-last_progress:.0f}s ago.',flush=True)
    if elapsed >= DEADLINE:
        raise SystemExit('Deployment verification timed out. Publication must not be reported as successful.')
    time.sleep(15)

paths = [str(p.relative_to(SITE)) for p in SITE.rglob('index.html')]
paths += ['assets/app.js','assets/styles.css','assets/gemini-notebook-logo.svg','assets/task-force-logo.png',
          'assets/studio.png','assets/explore-blueprint.png','assets/explore-digital-education.png',
          'downloads/DigitalEducationBlueprint(Chinese).pdf','downloads/DigitalEducationBlueprint(English).pdf',
          'downloads/Gemini-Notebook-Workshop.pptx','downloads/teacher-prompt-handout.md','downloads/hong-kong-prompt-examples.md']

def check(path: str) -> dict:
    remote = fetch(path)
    local = (SITE/path).read_bytes()
    assert sha256(remote).digest() == sha256(local).digest(), 'Published bytes differ: '+path
    return {'path':path,'status':200,'bytes':len(remote),'sha256':sha256(remote).hexdigest()}

with ThreadPoolExecutor(max_workers=6) as pool:
    results = list(pool.map(check,paths))
report = {'base_url':BASE,'verified_files':len(results),'slide_pages':19,'bilingual_prompt_pages':10,'results':results}
(ROOT/'qa').mkdir(exist_ok=True)
(ROOT/'qa/published-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(f'LIVE VERIFIED: {BASE} — {len(results)} pages/assets/downloads exactly match the approved local files.',flush=True)

#!/usr/bin/env python3
"""Read-only checks for content parity, downloads and subpath-safe links."""
from pathlib import Path
from urllib.parse import urlsplit, unquote
from hashlib import sha256
from zipfile import ZipFile
import json
import re
from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
texts = json.loads((ROOT / 'content/prompt-texts.json').read_text())['prompts']
slides = json.loads((ROOT / 'content/slides.json').read_text())
pages = list(SITE.rglob('index.html'))
assert len(pages) == 30, len(pages)


def required(soup: BeautifulSoup, selector: str) -> Tag:
    element = soup.select_one(selector)
    assert isinstance(element, Tag), selector
    return element


def normal(text: str) -> str:
    return ' '.join(text.split())


for path in pages:
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    assert required(soup, 'html').get('lang') == 'en'
    assert soup.find('meta', attrs={'name':'viewport'})
    assert len(soup.find_all('h1')) == 1
    required(soup, 'main#main')
    ids = [str(e['id']) for e in soup.select('[id]')]
    assert len(ids) == len(set(ids)), f'Duplicate IDs: {path}'
    for image in soup.find_all('img'):
        assert image.has_attr('alt'), f'Missing image alt: {path}'
    for element in soup.select('[href], [src]'):
        raw = str(element.get('href') or element.get('src') or '')
        if raw.startswith('#'):
            assert soup.find(id=raw[1:]), (path,raw)
            continue
        parts = urlsplit(raw)
        if parts.scheme:
            assert parts.scheme == 'https', (path,raw)
            assert not any(x in parts.netloc for x in ('localhost','127.0.0.1','manus.computer'))
            continue
        assert not raw.startswith('/'), f'Non-relative path: {path}: {raw}'
        dest = (path.parent / unquote(parts.path)).resolve()
        assert dest.is_relative_to(SITE.resolve()), (path,raw)
        if dest.is_dir(): dest = dest / 'index.html'
        assert dest.is_file(), f'Broken link: {path}: {raw}'
    for copy in soup.select('[data-copy]'):
        assert soup.find(id=str(copy['data-copy'])), f'Invalid clipboard target: {path}'
    required(soup, 'a[data-page-next]')
    required(soup, 'a[data-page-previous]')

for slide in slides:
    n = slide['number']
    path = SITE / ('index.html' if n == 1 else f'pages/{n:02d}/index.html')
    soup = BeautifulSoup(path.read_text(), 'html.parser')
    main_text = normal(required(soup, 'main').get_text(' ',strip=True))
    for point in slide.get('points', []):
        assert normal(point) in main_text, (n,point)
    for note in slide.get('notes', []):
        assert normal(note) in main_text, (n,note)

for n, text in enumerate(texts, 1):
    soup = BeautifulSoup((SITE / f'prompts/{n:02d}/index.html').read_text(), 'html.parser')
    for key, suffix in [('example_en','en'),('example_zh','zh-Hant'),('template_en','en-template'),('template_zh','zh-Hant-template')]:
        assert required(soup,'#prompt-'+suffix).get_text() == text[key], (n,key)
        assert not re.search(r'\b20\d{2}\b',text[key]), (n,key,'fixed year')
    assert text['example_en'].endswith('Write in English.')
    assert text['example_zh'].endswith('請以繁體中文回答。')
    all_text = required(soup,'main').get_text(' ',strip=True)
    assert 'Situation' in all_text and 'Sources to add to Notebook' in all_text

for filename in ['DigitalEducationBlueprint(Chinese).pdf','DigitalEducationBlueprint(English).pdf']:
    uploaded = Path('/home/ubuntu/upload') / filename
    assert sha256(uploaded.read_bytes()).digest() == sha256((SITE/'downloads'/filename).read_bytes()).digest()

with ZipFile(SITE/'downloads/Gemini-Notebook-Workshop.pptx') as z:
    assert z.testzip() is None
    assert len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]) == 19

manifest = json.loads((SITE/'manus-routes.json').read_text())
assert len(manifest['routes']) == 30
for route in manifest['routes']:
    assert (SITE / (route['path'].lstrip('/')+'index.html')).is_file(), route

soup15 = BeautifulSoup((SITE/'pages/15/index.html').read_text(),'html.parser')
assert len(soup15.select('#prompt-index li a')) == 10
soup12 = BeautifulSoup((SITE/'pages/12/index.html').read_text(),'html.parser')
assert len(soup12.select('table th')) == 4
assert 'Write in English' not in required(soup12,'main').get_text()
soup10 = BeautifulSoup((SITE/'pages/10/index.html').read_text(),'html.parser')
assert required(soup10,'h1').get_text(' ',strip=True).startswith('Try Explore. Find more relevant sources.')
assert '探索' not in required(soup10,'h1').get_text()
soup13 = BeautifulSoup((SITE/'pages/13/index.html').read_text(),'html.parser')
assert 'Check one important claim' not in required(soup13,'main').get_text()
print('PASS: 19 faithful slide pages, 10 bilingual prompt pages, resources, all internal links, copy targets, original PDF bytes and downloadable PPT verified.')

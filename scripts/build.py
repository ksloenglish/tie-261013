#!/usr/bin/env python3
"""Generate the dependency-free, subpath-safe workshop companion."""
from __future__ import annotations

import html
from hashlib import sha256
import json
import posixpath
import re
import shutil
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'site'
SLIDES = json.loads((ROOT / 'content/slides.json').read_text())
PROMPT_TEXTS = json.loads((ROOT / 'content/prompt-texts.json').read_text())['prompts']
EXAMPLES = (ROOT / 'content/prompt-examples-source.md').read_text()
SCHOOL_URL = 'https://kslo.tech/nb-teachers'
EDB_URL = 'https://www.edb.gov.hk/en/edu-system/primary-secondary/applicable-to-primary-secondary/it-in-edu/debp.html'
ENGLISH_URL = 'https://www.edb.gov.hk/en/curriculum-development/kla/eng-edu/curriculum-documents.html'
HKEAA_URL = 'https://www.hkeaa.edu.hk/en/hkdse/assessment/assessment_framework/'
PADLET_URL = 'https://padlet.com/thehkmakslocollege/tech-in-ed-gemini-notebook-workshop-intermediate-level-13-oc-s024b3yqp5avekkd7yhd'
TITLE = 'Gemini Notebook Workshop (Intermediate Level)'
PROMPT_TITLES = [
    'Check materials against HKDSE requirements',
    'Turn an HKEAA briefing into revision-teaching notes',
    'Plan an HKDSE lesson with an exit ticket',
    'Support different levels—keep the same learning goal',
    'Draft HKDSE-style practice and a separate answer key',
    'Turn fictional errors into feedback and reteaching',
    'Audit a teaching or assessment draft before use',
    'Turn a long EDB document into a staff briefing',
    'Extract actions, dates and unanswered questions',
    'Compare official documents: updates or contradictions?',
]
SUBJECTS = ['English · S6', 'History · S6', 'Biology · S4', 'Economics · S5',
            'Mathematics · S6', 'English · fictional response', 'Biology · draft audit',
            'EDB · Digital Education Blueprint', 'EDB · AI teaching guide', 'EDB · document comparison']


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def md_inline(value: str) -> str:
    """Render trusted local prose with a small, safe Markdown subset."""
    text = esc(value)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    return text


def slide_path(number: int) -> str:
    return 'index.html' if number == 1 else f'pages/{number:02d}/index.html'


def prompt_path(number: int) -> str:
    return f'prompts/{number:02d}/index.html'


def href(current: str, target: str) -> str:
    directory = posixpath.dirname(current) or '.'
    path = posixpath.relpath(target, directory)
    if path.endswith('/index.html'):
        path = path[:-10]
    elif path == 'index.html':
        path = './'
    return quote(path, safe='/.-_~')


def ext_link(url: str, label: str, css: str = '') -> str:
    return f'<a class="{esc(css)}" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{label}<span aria-hidden="true"> ↗</span></a>'


def button(current: str, target: str, label: str, external: bool = False, secondary: bool = False, download: bool = False) -> str:
    classes = 'button secondary' if secondary else 'button'
    if external:
        return ext_link(target, esc(label), classes)
    attr = ' download' if download else ''
    return f'<a class="{classes}" href="{href(current, target)}"{attr}>{esc(label)}<span class="arrow" aria-hidden="true">{("↓" if download else "→")}</span></a>'


def list_numbered(points: list[str], special_apps: bool = False) -> str:
    rows = []
    for n, text in enumerate(points, 1):
        value = esc(text)
        if special_apps:
            value = value.replace('apps', '<strong>apps</strong>')
        rows.append(f'<li><span class="step-number" aria-hidden="true">{n:02d}</span><span class="step-text">{value}</span></li>')
    return '<ol class="numbered">' + ''.join(rows) + '</ol>'


def notes(slide: dict) -> str:
    text = []
    if slide.get('note'):
        text.append(f'<p>{esc(slide["note"])}</p>')
    if slide.get('label'):
        text.append(f'<p><strong>{esc(slide["label"])}</strong></p>')
    for note in slide.get('notes', []):
        text.append(f'<p>{esc(note)}</p>')
    return '<aside class="note">' + ''.join(text) + '</aside>' if text else ''


def shot(current: str, filename: str, alt: str) -> str:
    src = href(current, 'assets/' + filename)
    return f'<figure style="margin:0"><a class="shot" href="{src}" target="_blank" rel="noopener noreferrer" aria-label="Open full-size screenshot: {esc(alt)}"><img src="{src}" alt="{esc(alt)}" loading="lazy"></a><figcaption class="image-hint">Click or tap the screenshot to view it full size.</figcaption></figure>'


def resource(current: str, title: str, filename: str, label: str | None = None) -> str:
    return f'<a class="resource-link" href="{href(current, "downloads/" + filename)}" download><span><span class="resource-title">{esc(title)}</span><span class="resource-file">{esc(label or filename)}</span></span><span class="resource-arrow" aria-hidden="true">↓</span></a>'


def prompt_box(current: str, text: str, chinese: bool = False, suffix: str = '') -> str:
    language = '繁體中文提示詞' if chinese else 'English prompt'
    lang = 'zh-Hant' if chinese else 'en'
    code_id = f'prompt-{lang}{suffix}'
    copy_label = 'Copy Traditional Chinese prompt' if chinese else 'Copy English prompt'
    return f'''<section class="prompt-box" aria-labelledby="label-{code_id}">
<div class="prompt-toolbar"><h2 id="label-{code_id}" lang="{lang}">{language}<span class="box-subtitle" lang="en">Markdown / plain-text prompt</span></h2><button type="button" class="copy-button" data-copy="{code_id}" data-copy-label="{copy_label}" aria-label="{copy_label}">Copy prompt</button></div>
<pre lang="{lang}"><code id="{code_id}">{esc(text)}</code></pre>
</section>'''


def parse_prompt_metadata() -> list[dict]:
    chunks = re.split(r'^## Example (\d+) — ', EXAMPLES, flags=re.M)
    results = []
    for index in range(1, len(chunks), 2):
        number = int(chunks[index])
        block = chunks[index + 1]
        heading = block.split('\n', 1)[0]
        zh_title = heading.split('｜', 1)[1] if '｜' in heading else ''
        situation = re.search(r'\*\*Situation:\*\* (.+)', block)
        sources = re.search(r'\*\*Sources to select:\*\* (.+)', block)
        assert situation and sources, f'Missing metadata for prompt {number}'
        after_sources = block[sources.end():].split('**English version', 1)[0].strip()
        extra = '\n\n'.join(line for line in after_sources.split('\n\n') if line.strip())
        results.append({
            'number': number,
            'title': PROMPT_TITLES[number - 1],
            'zh_title': zh_title,
            'example_title': heading.split('｜', 1)[0],
            'situation': situation.group(1),
            'sources': sources.group(1),
            'extra': extra,
            'subject': SUBJECTS[number - 1],
            **PROMPT_TEXTS[number - 1],
        })
    assert len(results) == 10
    return results


PROMPTS = parse_prompt_metadata()


def prompt_index(current: str) -> str:
    rows = []
    for prompt in PROMPTS:
        number = prompt['number']
        search = ' '.join([prompt['title'], prompt['zh_title'], prompt['example_title'], prompt['subject']])
        rows.append(f'''<li data-search-item data-search="{esc(search)}"><a href="{href(current, prompt_path(number))}"><span class="prompt-number">{number:02d}</span><span><span class="prompt-name">{esc(prompt['title'])}</span><span class="prompt-subject">{esc(prompt['subject'])}</span></span></a></li>''')
    return f'''<div class="prompt-search"><label for="prompt-search">Find a teaching task</label><input id="prompt-search" class="nav-search" type="search" placeholder="Search tasks, subjects or 中文…" data-filter="prompt-index" autocomplete="off"></div><ul class="prompt-index" id="prompt-index">{''.join(rows)}</ul><p class="no-results" hidden data-empty-for="prompt-index" role="status">No matching prompts. Try another subject or task.</p>'''


def slide_body(slide: dict, current: str) -> str:
    kind = slide['kind']
    if kind == 'cover':
        return '<p class="hero-tag">Beyond “Generate”</p><hr class="section-rule">' + list_numbered(slide['points'])
    if kind == 'numbered':
        return list_numbered(slide['points']) + notes(slide)
    if kind == 'bullets':
        return '<ul class="large-bullets">' + ''.join(f'<li>{esc(p)}</li>' for p in slide['points']) + '</ul>' + notes(slide)
    if kind == 'studio':
        groups = ''.join(f'<section class="studio-group"><h2>{esc(g["title"])}</h2><p>{esc(g["text"])}</p></section>' for g in slide['groups'])
        return '<div class="split"><div class="studio-groups">' + groups + '</div>' + shot(current, slide['image'], 'Eight Studio tools available in the school Enterprise account') + '</div>'
    if kind == 'access':
        return f'''<p><a class="access-url" href="{SCHOOL_URL}" target="_blank" rel="noopener noreferrer">kslo.tech/nb-teachers</a></p>{list_numbered(slide['points'], True)}<div class="button-row">{button(current,SCHOOL_URL,'Open the school access page',external=True)}</div>'''
    if kind == 'setup':
        links = ''.join(resource(current, item['title'], item['file']) for item in slide['downloads'])
        return list_numbered(slide['points']) + f'<section class="resource-list workshop-downloads" aria-label="Workshop document downloads">{links}</section>'
    if kind == 'explore-activity':
        return '<div class="split"><div>' + list_numbered(slide['points']) + '</div>' + shot(current, slide['image'], 'The Explore (探索) button in the Blueprint notebook’s Sources panel') + '</div>'
    if kind == 'comparison':
        specific = esc(slide['specific']).replace('Hong Kong', '<strong class="hong-kong">Hong Kong</strong>')
        return f'''<div class="split"><div class="comparison"><p class="label">Too broad</p><p class="query">{esc(slide['broad'])}</p><p class="label specific">More specific</p><p class="query">{specific}</p></div>{shot(current,slide['image'],'Explore sources dialog in the Digital Education Blueprint notebook')}</div>'''
    if kind == 'format':
        columns = ''.join(f'<th scope="col">{esc(col)}</th>' for col in slide['columns'])
        return f'''<p class="resource-intro">{esc(slide['note'])}</p><hr class="section-rule"><div class="format-example vague"><p><strong>Vague:</strong> “{esc(slide['vague'])}”</p></div><div class="format-example"><p><span class="format-label">Clear:</span> {esc(slide['clear'])}</p></div><div class="table-wrap" role="region" aria-label="Four-column table headings" tabindex="0"><table class="format-table"><thead><tr>{columns}</tr></thead></table></div>'''
    if kind == 'practice':
        steps = ''.join(f'<section class="practice-step"><div class="big-step" aria-hidden="true">{i:02d}</div><h2>{esc(step["title"])}</h2>' + ''.join(f'<p>{esc(line)}</p>' for line in step['lines']) + '</section>' for i, step in enumerate(slide['steps'], 1))
        return '<div class="practice-steps">' + steps + '</div>' + notes(slide)
    if kind == 'padlet':
        points = '<ul class="large-bullets">' + ''.join(f'<li>{esc(p)}</li>' for p in slide['points']) + '</ul>'
        qr = f'<div class="qr-area"><a href="{PADLET_URL}" target="_blank" rel="noopener noreferrer" aria-label="Open workshop Padlet"><img src="{href(current,"assets/padlet-qr.png")}" alt="QR code for the workshop Padlet"></a><p class="image-hint">Scan with another device, or use the button.</p></div>'
        return f'<div class="split"><div>{points}<div class="button-row">{button(current,PADLET_URL,"Open workshop Padlet",external=True)}</div></div>{qr}</div>'
    if kind == 'prompt-index':
        return prompt_index(current)
    if kind == 'context':
        sources = ''.join(f'<li>{esc(source)}</li>' for source in slide['sources'])
        return f'''<section class="context-section"><h2>Situation</h2><p>{esc(slide['situation'])}</p></section><section class="context-section"><h2>Sources to add to Notebook</h2><ul class="source-items">{sources}</ul><div class="source-links">{ext_link(ENGLISH_URL,'EDB curriculum documents')}{ext_link(HKEAA_URL,'HKEAA assessment frameworks')}</div></section><div class="button-row">{button(current,prompt_path(1),'Open the complete bilingual example')}</div>'''
    if kind in ('english-example', 'chinese-example'):
        chinese = kind == 'chinese-example'
        text = PROMPTS[0]['example_zh' if chinese else 'example_en']
        return prompt_box(current, text, chinese) + f'<div class="button-row">{button(current,prompt_path(1),"Situation, sources & both languages",secondary=True)}</div>'
    raise ValueError(f'Unknown slide kind: {kind}')


def navigation_list(current: str, current_number: int | None, ident: str) -> str:
    items = []
    for slide in SLIDES:
        num = slide['number']
        active = ' aria-current="page"' if num == current_number else ''
        items.append(f'<li data-search-item><a href="{href(current, slide_path(num))}"{active}><span class="nav-number">{num:02d}</span><span>{esc(slide["nav"])}</span></a></li>')
    return f'<ul class="nav-list" id="{ident}">' + ''.join(items) + '</ul>'


def utility_links(current: str) -> str:
    return f'''<a class="utility-link" href="{href(current, slide_path(15))}">Ten bilingual prompts →</a><a class="utility-link" href="{href(current,'resources/index.html')}">Workshop downloads & links →</a><a class="utility-link" href="{href(current,'downloads/Gemini-Notebook-Workshop.pptx')}" download>Download PowerPoint ↓</a>'''


def page_navigation(current: str, number: int | None = None, prompt_number: int | None = None) -> str:
    if number:
        previous = SLIDES[number - 2] if number > 1 else None
        following = SLIDES[number] if number < 19 else None
        if previous:
            left_url, left_title = slide_path(previous['number']), previous['nav']
        else:
            left_url, left_title = 'resources/index.html', 'Workshop downloads & links'
        if following:
            right_url, right_title = slide_path(following['number']), following['nav']
        else:
            right_url, right_title = slide_path(15), 'Explore the ten prompts'
    elif prompt_number:
        left_url = prompt_path(prompt_number - 1) if prompt_number > 1 else slide_path(15)
        left_title = PROMPT_TITLES[prompt_number - 2] if prompt_number > 1 else 'All ten prompts'
        right_url = prompt_path(prompt_number + 1) if prompt_number < 10 else slide_path(15)
        right_title = PROMPT_TITLES[prompt_number] if prompt_number < 10 else 'Back to all prompts'
    else:
        left_url, left_title = slide_path(1), 'Workshop overview'
        right_url, right_title = slide_path(8), 'Create your Blueprint notebook'
    left_icon = '<span class="nav-arrow-badge" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none" focusable="false"><path d="M27 16H5M14 6L4 16l10 10" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg></span>'
    right_icon = '<span class="nav-arrow-badge" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none" focusable="false"><path d="M5 16h22M18 6l10 10-10 10" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/></svg></span>'
    return f'''<nav class="page-nav" aria-label="Page navigation"><a class="page-nav-button page-nav-previous" href="{href(current,left_url)}" data-page-previous>{left_icon}<span class="nav-copy"><span class="nav-direction">Previous</span><span class="nav-title">{esc(left_title)}</span></span></a><a class="page-nav-button page-nav-next" href="{href(current,right_url)}" data-page-next><span class="nav-copy"><span class="nav-direction">Next</span><span class="nav-title">{esc(right_title)}</span></span>{right_icon}</a></nav>'''


def layout(current: str, title: str, content: str, number: int | None = None, prompt_number: int | None = None, detail: bool = False) -> str:
    css_version = sha256((ROOT / 'src/styles.css').read_bytes()).hexdigest()[:12]
    section = 'Prompt library' if prompt_number else 'Participant companion'
    count = f'Prompt {prompt_number:02d} / 10' if prompt_number else f'Slide {number:02d} / 19' if number else 'Workshop resources'
    description = f'{title} — participant reference for the Gemini Notebook Workshop, HKMA K S Lo College Tech in Ed Task Force.'
    sidebar_nav = navigation_list(current, number, 'sidebar-nav')
    dialog_nav = navigation_list(current, number, 'dialog-nav')
    nojs_nav = '<noscript><nav class="nojs-contents" aria-label="Workshop page links"><details><summary>Workshop contents</summary>' + navigation_list(current, number, 'nojs-nav') + utility_links(current) + '</details></nav></noscript>'
    content = content.replace('<div class="table-wrap"', '<p class="table-hint">Swipe the table to view all four column headings →</p><div class="table-wrap"')
    content = nojs_nav + content
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="{esc(description)}"><meta name="theme-color" content="#f8faf7"><title>{esc(title)} | Gemini Notebook Workshop</title><link rel="icon" type="image/png" href="{href(current,'assets/task-force-logo.png')}"><link rel="stylesheet" href="{href(current,'assets/styles.css')}?v={css_version}"><script src="{href(current,'assets/app.js')}" defer></script></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<header class="topbar"><a class="brand" href="{href(current,slide_path(1))}" aria-label="Workshop overview"><img src="{href(current,'assets/task-force-logo.png')}" alt="Tech in Ed Task Force logo" width="34" height="34"><span class="brand-text">HKMA K S Lo College<span>Tech in Ed Task Force</span></span></a><span class="header-divider" aria-hidden="true"></span><a href="{href(current,slide_path(1))}" aria-label="Gemini Notebook Workshop overview"><img class="wordmark" src="{href(current,'assets/gemini-notebook-logo.svg')}" alt="Gemini Notebook" width="210" height="18"></a><div class="topbar-right"><span class="header-date">13 Oct 2026</span><button type="button" class="menu-button" data-open-menu aria-controls="contents-dialog" aria-expanded="false"><span class="menu-icon" aria-hidden="true"></span>Contents</button></div></header>
<aside class="sidebar" aria-label="Workshop contents"><p class="eyebrow"><span class="orange-square" aria-hidden="true"></span>Workshop pages</p><label for="sidebar-search" class="skip-link">Search workshop pages</label><input id="sidebar-search" class="nav-search" type="search" data-filter="sidebar-nav" placeholder="Find a page…" aria-label="Search workshop pages">{sidebar_nav}{utility_links(current)}</aside>
<div class="main-shell"><main id="main" class="main{' prompt-detail' if detail else ''}" tabindex="-1"><div class="page-meta"><p class="eyebrow"><span class="orange-square" aria-hidden="true"></span>{section}</p><span class="page-count">{count}</span></div>{content}{page_navigation(current,number,prompt_number)}<footer class="site-footer"><span>HKMA K S Lo College Tech in Ed Task Force<br>Gemini Notebook Workshop (Intermediate Level) · 13 Oct 2026</span><span><a href="{href(current,'resources/index.html')}">Downloads & links</a> · <button type="button" class="print-page" data-print>Print this page</button></span></footer></main></div>
<dialog class="contents-dialog" id="contents-dialog" aria-labelledby="contents-title"><div class="dialog-header"><h2 id="contents-title">Workshop contents</h2><button class="close-button" type="button" data-close-menu aria-label="Close contents">×</button></div><input class="nav-search" id="dialog-search" type="search" data-filter="dialog-nav" placeholder="Find a page…" aria-label="Search contents">{dialog_nav}{utility_links(current)}</dialog><div class="toast" id="toast" role="status" aria-live="polite" hidden></div>
</body></html>'''


def render_slide(slide: dict) -> str:
    current = slide_path(slide['number'])
    cover = slide['kind'] == 'cover'
    accent_class = 'subtitle' if cover else 'accent'
    chinese = ' lang="zh-Hant"' if slide['kind'] == 'chinese-example' else ''
    title = f'''<div class="page-heading">{'<p class="eyebrow">Continuing professional development</p>' if cover else ''}<h1>{esc(slide['title'])}<span class="{accent_class}"{chinese}>{esc(slide['accent'])}</span></h1></div>'''
    return layout(current, slide['nav'], title + '<div class="content">' + slide_body(slide, current) + '</div>', slide['number'])


def source_links(current: str, number: int) -> str:
    if number >= 8:
        links = ext_link(EDB_URL, 'EDB Blueprint & supplement resources')
        if number in (8, 10):
            links += f'<a href="{href(current,"downloads/DigitalEducationBlueprint(English).pdf")}" download>English Blueprint PDF ↓</a>'
            links += f'<a href="{href(current,"downloads/DigitalEducationBlueprint(Chinese).pdf")}" download>Chinese Blueprint PDF ↓</a>'
        return '<div class="source-links">' + links + '</div>'
    if number == 1:
        return '<div class="source-links">' + ext_link(ENGLISH_URL, 'EDB English curriculum documents') + ext_link(HKEAA_URL, 'HKEAA assessment frameworks') + '</div>'
    if number in (2, 3, 5):
        return '<div class="source-links">' + ext_link(HKEAA_URL, 'Applicable HKEAA assessment frameworks') + '</div>'
    return ''


def render_prompt(prompt: dict) -> str:
    number = prompt['number']
    current = prompt_path(number)
    breadcrumbs = f'<nav class="breadcrumbs" aria-label="Breadcrumb"> <a href="{href(current,slide_path(1))}">Workshop</a><span aria-hidden="true">/</span><a href="{href(current,slide_path(15))}">Ten prompts</a><span aria-hidden="true">/</span><span>{number:02d}</span></nav>'
    heading = f'<div class="page-heading"><h1>{esc(prompt["title"])}</h1><p class="chinese-title" lang="zh-Hant">{esc(prompt["zh_title"])}</p></div>'
    situation = f'<section class="context-section"><h2>Situation</h2><p>{esc(prompt["situation"])}</p></section>'
    sources = f'<section class="context-section"><h2>Sources to add to Notebook</h2><p>{md_inline(prompt["sources"])}</p>{source_links(current,number)}</section>'
    if prompt['extra']:
        extra = ''.join(f'<p>{md_inline(paragraph)}</p>' for paragraph in prompt['extra'].split('\n\n') if paragraph)
        sources += '<aside class="note">' + extra + '</aside>'
    if number in (8, 9, 10):
        sources += '<p class="example-caption">Add the actual publication PDF, not just its landing page. The Blueprint and Supplement II are separate documents.</p>'
    elif number in (1, 2, 3, 5):
        sources += '<p class="example-caption">Use the official documents applicable to your cohort. Add your own authorised teaching notes; they are not supplied by this website.</p>'
    labels = '<p class="example-caption">Use one language version at a time. These are worked examples: adapt the source names to match your notebook.</p>'
    boxes = prompt_box(current, prompt['example_en']) + prompt_box(current, prompt['example_zh'], True)
    templates = '<details class="template-details"><summary>Adapt this task: show the reusable templates</summary>' + prompt_box(current,prompt['template_en'],suffix='-template') + prompt_box(current,prompt['template_zh'],True,suffix='-template') + '</details>'
    caution = '<aside class="note"><p>Notebook grounds answers in selected sources, but grounding is not an accuracy guarantee. These prompts are workshop adaptations, not official EDB/HKEAA instructions. Check important claims against their cited passages.</p></aside>'
    return layout(current,prompt['title'],breadcrumbs + heading + situation + sources + labels + boxes + templates + caution,prompt_number=number,detail=True)


def render_resources() -> str:
    current = 'resources/index.html'
    heading = '<div class="page-heading"><h1>Workshop downloads<span class="accent">& useful links.</span></h1></div><p class="resource-intro">Keep the documents, presentation and prompts close at hand while you follow the workshop.</p>'
    documents = '<section class="resource-group"><h2>Digital Education Blueprint</h2><div class="resource-list">' + resource(current,'Chinese Blueprint','DigitalEducationBlueprint(Chinese).pdf') + resource(current,'English Blueprint','DigitalEducationBlueprint(English).pdf') + '</div></section>'
    handouts = '<section class="resource-group"><h2>Presentation & prompt resources</h2><div class="resource-list">' + resource(current,'Workshop PowerPoint','Gemini-Notebook-Workshop.pptx','Editable PowerPoint · 19 slides') + resource(current,'Ten bilingual templates and examples','teacher-prompt-handout.md','Markdown handout · English & Traditional Chinese') + resource(current,'Ten worked examples','hong-kong-prompt-examples.md','Markdown examples companion') + '</div></section>'
    links = '<section class="resource-group"><h2>Workshop links</h2><div class="button-row">' + button(current,SCHOOL_URL,'School Notebook access',external=True) + button(current,PADLET_URL,'Workshop Padlet',external=True,secondary=True) + '</div><div class="source-links">' + ext_link(EDB_URL,'EDB Blueprint & supplement resource page') + ext_link(HKEAA_URL,'HKDSE assessment framework index') + ext_link(ENGLISH_URL,'EDB English curriculum documents') + ext_link('https://www.youtube.com/playlist?list=PLrxXwTbpDwrfb8_F7laoFdAUHrMbZf3ru','Desmond EdTech teacher playlist') + '</div></section>'
    return layout(current,'Workshop downloads & useful links',heading + documents + handouts + links)


def write_page(path: str, value: str) -> None:
    destination = SITE / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(value + '\n', encoding='utf-8')


def main() -> None:
    SITE.mkdir(exist_ok=True)
    shutil.copytree(ROOT / 'public', SITE, dirs_exist_ok=True)
    shutil.copy2(ROOT / 'src/styles.css', SITE / 'assets/styles.css')
    shutil.copy2(ROOT / 'src/app.js', SITE / 'assets/app.js')
    for slide in SLIDES:
        write_page(slide_path(slide['number']), render_slide(slide))
    for prompt in PROMPTS:
        write_page(prompt_path(prompt['number']), render_prompt(prompt))
    write_page('resources/index.html', render_resources())
    routes = [{'path':'/' if s['number'] == 1 else f'/pages/{s["number"]:02d}/','title':s['nav']} for s in SLIDES]
    routes += [{'path':f'/prompts/{p["number"]:02d}/','title':p['title']} for p in PROMPTS]
    routes.append({'path':'/resources/','title':'Workshop downloads & links'})
    (SITE / 'manus-routes.json').write_text(json.dumps({'routes':routes},ensure_ascii=False,indent=2)+'\n')
    (SITE / '.nojekyll').touch()
    print(f'Built {len(SLIDES)} slide pages + {len(PROMPTS)} bilingual prompt pages + 1 resource page into {SITE}')


if __name__ == '__main__':
    main()

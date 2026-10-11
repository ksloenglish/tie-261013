# Gemini Notebook Workshop — Participant Companion

Participant reference for HKMA K S Lo College Tech in Ed Task Force, 13 Oct 2026. The site follows the latest 19-slide PowerPoint and adds ten bilingual prompt detail pages.

## Structure

- `content/slides.json`: faithful, structured slide-page content.
- `content/prompt-texts.json`: latest concise bilingual examples and reusable templates.
- `content/prompt-examples-source.md`: situations and source-selection guidance for all ten examples.
- `src/styles.css` and `src/app.js`: responsive Swiss Minimal design and progressive enhancements.
- `scripts/build.py`: dependency-free static HTML generator, producing `site/`.
- `public/assets/`: supplied logos and screenshots.
- `public/downloads/`: supplied Blueprint PDFs, presentation and bilingual prompt handouts.

## Build and preview

```sh
python3 scripts/build.py
python3 -m http.server 3000 --bind 0.0.0.0 --directory site
```

Python 3.10+ is sufficient. No Node packages, database, AI service or login are needed. Page contents are delivered as static HTML and remain readable without JavaScript. JavaScript enhances the contents dialog, filtering, copying, keyboard shortcuts and printing.

## GitHub Pages

The destination is `https://ksloenglish.github.io/tie-261013/`. Source code lives on `main`; GitHub Pages serves the static-only `gh-pages` branch from its root. Every internal link and asset reference is relative, so nested pages work at `/tie-261013` without a client-side fallback or rewriting rules. `.nojekyll` is supplied. No custom GitHub Actions workflow is required.

After reviewing source changes, rebuild and run the checks, commit them on `main`, and push `main`. Then update the publishing branch without rewriting history:

```sh
git subtree split --prefix=site -b gh-pages
git push origin gh-pages:refs/heads/gh-pages
python3 scripts/verify_live.py
```

The public site includes only the approved workshop content and supplied public documents, not a private Notebook link, student work or sign-in credentials. Official reference links direct participants to the applicable documents; teachers must add their own subject notes where indicated.

The original PPT is not modified by this project. Prompt examples are source-aware workshop adaptations, not official EDB or HKEAA instructions or a guarantee of AI accuracy.

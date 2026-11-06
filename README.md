# The Migrating Nurse: free 30-day NCLEX-RN® study plan

The source of the free study-plan website: a one-page plan with daily ticks (saved only in your own
browser), a privacy page, and an email sign-up that is switched off until it opens.

- `index.html`, `privacy.html`, `style.css`, `app.js`, `assets/logo.svg`: the whole site. Nothing is loaded
  from another site: no fonts, analytics, trackers, cookies or third-party forms.
- `tools/check_site.py`: the checks. Links must go to published files only, nothing may point off the site
  (pages, CSS, JS and SVG), the full footer must be on every page, NCLEX® must carry its mark
  (title included), and every email-form control must stay switched off and unnamed, with a consent box.
  Tests: `python3 -m unittest discover -s tools -v`.
- `.github/workflows/checks.yml` runs both on every pull request. `.github/workflows/pages.yml` publishes
  to GitHub Pages on a merge to `main`. It copies exactly the files the check approved.

Look at it locally: run `python3 -m http.server` in this folder, then open http://localhost:8000.

## Repository settings (a repository admin sets these once)

- **Settings → Pages → Source: GitHub Actions.** Without this, the deploy job fails and nothing is published.
- **Branch protection on `main`:** require a pull request with an approving review, and require the
  `checks` job to pass. This is what makes "nothing goes live before approval" true. A direct push to
  `main` would otherwise deploy at once.
- Keep the `github-pages` environment limited to `main`, which is the default.

## Before the email sign-up opens

Update `privacy.html` first: name the email service, say what is sent and how often, and give an email
address for privacy requests. Then switch the form on, in its own pull request.

Educational use only. Not affiliated with or endorsed by NCSBN. NCLEX® and NCLEX-RN® are registered
trademarks of the National Council of State Boards of Nursing, Inc.

© 2026 The Migrating Nurse. All rights reserved.

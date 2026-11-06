#!/usr/bin/env python3
"""Site checks, standard library only.

  python3 tools/check_site.py              check every published file
  python3 tools/check_site.py --copy DIR   check, then copy exactly those files to DIR (the Pages build)

Published files are everything except .git, .github, tools and README.md. Every page must load
nothing from another site. Only privacy.html may link to the exact approved GitHub privacy
notice via an anchor href; all other links must be published files. Pages carry the full footer and write NCLEX® with
the mark (title and description included), never state exam status or pass claims, and keep the
email form fully switched off with a consent checkbox. CSS, JS and SVG files must not reach the network.
"""
import html.parser, os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOT_PUBLISHED = {".git", ".github", "tools", "README.md"}
FOOTER = ("Educational use only. Not affiliated with or endorsed by NCSBN. NCLEX® and NCLEX-RN® are "
          "registered trademarks of the National Council of State Boards of Nursing, Inc.")
NOT_SAID = [r"\bpreparing for\b", r"\bpass(?:ed|ing)\b", r"\bguarantee", r"\bpass rates?\b"]
URL_ATTRS = {"src", "href", "action", "formaction", "srcset", "poster", "data", "xlink:href", "background", "ping"}
NETWORK = re.compile(r"(?i)\bhttps?:|(?<![:\w])//[a-z0-9-]+\.|@import|url\(\s*['\"]?(?:https?:)?//|"
                     r"\bfetch\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource")
PRIVACY_LINK = "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement"
CONTROLS = {"input", "button", "select", "textarea"}


def published(root=ROOT):
    """Relative paths of every file the Pages build publishes."""
    found = []
    for d, dirs, files in os.walk(root):
        rel_d = os.path.relpath(d, root)
        dirs[:] = sorted(x for x in dirs if rel_d != "." or x not in NOT_PUBLISHED)
        for f in sorted(files):
            rel = os.path.normpath(os.path.join(rel_d, f))
            if rel not in NOT_PUBLISHED:
                found.append(rel)
    return found


class Page(html.parser.HTMLParser):
    """Collects URLs, visible text (title and description included), footer text and form controls."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls, self.text, self.footer, self.controls = [], [], [], []
        self.skip = 0          # inside <script> or <style>
        self.in_footer = 0
        self.form = 0          # inside <form>
        self.off = []          # stack: is each open <fieldset> disabled
        self.consent = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for k, v in attrs:
            if k in URL_ATTRS and v is not None:
                self.urls += [(tag, k, u.strip().split(" ")[0]) for u in v.split(",")] if k == "srcset" else [(tag, k, v.strip())]
        if tag in ("script", "style"):
            self.skip += 1
        elif tag == "footer":
            self.in_footer += 1
        elif tag == "form":
            self.form += 1
        elif tag == "fieldset" and self.form:
            self.off.append("disabled" in a)
        elif tag == "meta" and a.get("name") == "description":
            self.text.append(a.get("content") or "")
        if tag in CONTROLS and self.form:
            self.controls.append((tag, a, "disabled" in a or any(self.off)))
            if tag == "input" and a.get("type") == "checkbox":
                self.consent = True
        if tag in ("p", "div", "li", "h1", "h2", "h3", "br", "label", "section", "td", "title", "footer"):
            self.text.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        elif tag == "footer":
            self.in_footer = max(0, self.in_footer - 1)
        elif tag == "form":
            self.form = max(0, self.form - 1)
        elif tag == "fieldset" and self.off:
            self.off.pop()
        self.text.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)
            if self.in_footer:
                self.footer.append(data)


def norm(parts):
    return re.sub(r"\s+", " ", "".join(parts)).strip()


def check_url(name, url, root, files):
    if re.match(r"(?i)^(?:[a-z][a-z0-9+.-]*:|//)", url):
        return [f"{name}: {url!r} points off the site"]
    path = url.split("#")[0].split("?")[0]
    if not path:
        return []
    target = os.path.normpath(os.path.join(os.path.dirname(name), path.lstrip("/") if path.startswith("/") else path))
    if target.startswith("..") or target not in files:
        return [f"{name}: link {url!r} is not a published file"]
    return []


def check_page(name, page, root, files):
    p = Page()
    p.feed(page)
    p.close()
    errors = []
    for tag, attr, url in p.urls:
        if name == "privacy.html" and tag == "a" and attr == "href" and url == PRIVACY_LINK:
            continue  # Approved navigation link; never an asset or form endpoint.
        errors += check_url(name, url, root, files)
    if NETWORK.search(" ".join(re.findall(r"(?is)<style\b.*?</style>|\bstyle\s*=\s*(\"[^\"]*\"|'[^']*')", page))):
        errors.append(f"{name}: inline style reaches the network")
    if FOOTER not in norm(p.footer):
        errors.append(f"{name}: footer missing or changed")
    text = norm(p.text)
    for m in re.finditer(r"NCLEX(?!®|-RN®)", text):
        errors.append(f"{name}: NCLEX without ® near {text[max(0, m.start() - 20):m.end() + 20]!r}")
    claim_text = text.replace("They are not passing-score weights.", "", 1) if name == "index.html" else text
    for pat in NOT_SAID:
        for m in re.finditer(pat, claim_text, re.I):
            errors.append(f"{name}: {m.group(0)!r} (no exam status or pass claims)")
    for tag, a, off in p.controls:
        if not off:
            errors.append(f"{name}: form {tag} {a.get('id') or a.get('type') or ''} is not switched off")
        if a.get("name"):
            errors.append(f"{name}: form {tag} has name={a['name']!r}; leave controls unnamed until sign-up opens")
    if p.controls and not p.consent:
        errors.append(f"{name}: sign-up form has no consent checkbox")
    return errors


def check(root=ROOT):
    files = set(published(root))
    errors = []
    for rel in sorted(files):
        path = os.path.join(root, rel)
        ext = os.path.splitext(rel)[1].lower()
        if ext in (".html", ".htm"):
            with open(path, encoding="utf-8") as fh:
                errors += check_page(rel, fh.read(), root, files)
        elif ext in (".css", ".js", ".svg"):
            with open(path, encoding="utf-8") as fh:
                text = re.sub(r"""\bxmlns(?::\w+)?\s*=\s*["'][^"']*["']""", "", fh.read())
            if NETWORK.search(text) or re.search(r"(?i)\bhref\s*=\s*['\"](?:https?:)?//", text):
                errors.append(f"{rel}: reaches the network")
    return sorted(files), errors


def main(argv):
    files, errors = check()
    for e in errors:
        print("FAIL " + e)
    print(f"{len(files)} published files, {len(errors)} problems")
    if errors:
        return 1
    if argv[:1] == ["--copy"] and len(argv) == 2:
        for rel in files:
            os.makedirs(os.path.join(argv[1], os.path.dirname(rel)), exist_ok=True)
            shutil.copy2(os.path.join(ROOT, rel), os.path.join(argv[1], rel))
        print(f"copied to {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

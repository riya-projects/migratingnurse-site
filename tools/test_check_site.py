#!/usr/bin/env python3
"""Tests for check_site.py: python3 -m unittest discover -s tools -v

Each test copies the real site to a temporary folder, breaks one rule, and expects the check to fail.
"""
import os, shutil, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)


class SiteCheck(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sitecheck-")
        self.addCleanup(shutil.rmtree, self.root, True)
        for rel in ("index.html", "privacy.html", "style.css", "app.js", "assets/logo.svg", ".nojekyll", "tools/check_site.py"):
            os.makedirs(os.path.join(self.root, os.path.dirname(rel)), exist_ok=True)
            shutil.copy(os.path.join(SITE, rel), os.path.join(self.root, rel))

    def edit(self, rel, old, new):
        path = os.path.join(self.root, rel)
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn(old, text)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(old, new, 1))

    def run_check(self):
        r = subprocess.run([sys.executable, "-I", "tools/check_site.py"], cwd=self.root, capture_output=True, text=True)
        return r.returncode, r.stdout

    def assertFails(self, needle):
        code, out = self.run_check()
        self.assertEqual(code, 1, out)
        self.assertIn(needle, out)

    def test_real_site_passes(self):
        code, out = self.run_check()
        self.assertEqual(code, 0, out)

    def test_third_party_script_any_quoting(self):
        self.edit("index.html", '<script src="app.js">', "<script src='https://cdn.example.com/x.js'>")
        self.assertFails("points off the site")

    def test_link_outside_the_site(self):
        self.edit("index.html", '<a href="privacy.html">Privacy</a>', '<a href="/etc/passwd">Privacy</a>')
        self.assertFails("is not a published file")

    def test_title_needs_the_mark_and_no_exam_status(self):
        self.edit("index.html", "<title>Free 30-Day NCLEX-RN&reg;", "<title>Preparing for NCLEX-RN")
        code, out = self.run_check()
        self.assertIn("NCLEX without ®", out)
        self.assertIn("'Preparing for'", out)

    def test_footer_must_be_exact(self):
        self.edit("privacy.html", "Not affiliated with or endorsed by NCSBN.", "Not affiliated with NCSBN.")
        self.assertFails("privacy.html: footer missing or changed")

    def test_email_form_must_stay_off(self):
        self.edit("index.html", "<fieldset disabled>", "<fieldset>")
        self.edit("index.html", 'autocomplete="off" disabled>', 'autocomplete="off">')
        self.assertFails("form input email is not switched off")

    def test_named_controls_and_missing_consent(self):
        self.edit("index.html", '<input type="checkbox" disabled>', '')
        self.edit("index.html", 'id="email"', 'id="email" name="email"')
        code, out = self.run_check()
        self.assertIn("has name='email'", out)
        self.assertIn("no consent checkbox", out)

    def test_privacy_navigation_is_not_an_asset_exception(self):
        url = "https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement"
        self.edit("privacy.html", '<a href="' + url + '">', '<script src="' + url + '"></script><a href="' + url + '">')
        self.assertFails("points off the site")

    def test_only_exact_privacy_url_is_allowed(self):
        self.edit("privacy.html", 'github-general-privacy-statement">', 'github-general-privacy-statement?extra=1">')
        self.assertFails("points off the site")

    def test_positive_passing_claim_remains_blocked(self):
        self.edit("index.html", "They are not passing-score weights.", "These guarantee passing.")
        self.assertFails("no exam status or pass claims")

    def test_approved_link_is_only_for_privacy_page(self):
        self.edit("index.html", '<a href="privacy.html">Privacy</a>', '<a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">Privacy</a>')
        self.assertFails("points off the site")

    def test_tracking_ping_on_privacy_link_is_blocked(self):
        self.edit("privacy.html", "<a href=", '<a ping="https://tracker.example/collect" href=')
        self.assertFails("points off the site")

    def test_claim_beside_negative_disclaimer_is_blocked(self):
        self.edit("index.html", "They are not passing-score weights.", "They are not passing-score weights. Guaranteed passing.")
        self.assertFails("no exam status or pass claims")

    def test_assets_and_scripts_cannot_reach_the_network(self):
        self.edit("assets/logo.svg", "</svg>", '<image href="https://x.example/p.png"/></svg>')
        self.edit("app.js", "window.print()", "fetch('/x');window.print()")
        code, out = self.run_check()
        self.assertIn("assets/logo.svg: reaches the network", out)
        self.assertIn("app.js: reaches the network", out)


if __name__ == "__main__":
    unittest.main()

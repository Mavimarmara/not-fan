import tempfile
import unittest
import zipfile
from pathlib import Path

from not_fan import (
    ExportOwnerMismatchError,
    extract_usernames,
    load_follows_report,
    username_from_profile_link,
)

FOLLOWERS_HTML = """<html><body><h1>Seguidores</h1>
<aside>Gerado por alice em <time>x</time></aside>
<main>
<div class="pam"><div><div><a target="_blank" href="https://www.instagram.com/bob">bob</a></div><div>nov 16</div></div></div>
<div class="pam"><div><div><a target="_blank" href="https://www.instagram.com/carol">carol</a></div><div>nov 15</div></div></div>
</main></body></html>"""

FOLLOWING_HTML = """<html><body><h1>Seguindo</h1>
<aside>Gerado por alice em <time>x</time></aside>
<main>
<div class="pam"><h2>bob</h2><div><div><a target="_blank" href="https://www.instagram.com/_u/bob">https://www.instagram.com/_u/bob</a></div></div></div>
<div class="pam"><h2>dave</h2><div><div><a target="_blank" href="https://www.instagram.com/_u/dave">https://www.instagram.com/_u/dave</a></div></div></div>
</main></body></html>"""

EXPORT_FILES = {
    "connections/followers_and_following/followers_1.html": FOLLOWERS_HTML,
    "connections/followers_and_following/following.html": FOLLOWING_HTML,
}


def write_export_as_folder(root: Path) -> Path:
    for entry, content in EXPORT_FILES.items():
        target = root / entry
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return root


def write_export_as_zip(zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path, "w") as archive:
        for entry, content in EXPORT_FILES.items():
            archive.writestr(entry, content)
    return zip_path


class UsernameFromProfileLinkTest(unittest.TestCase):
    def test_extracts_username_from_full_url(self):
        self.assertEqual(username_from_profile_link("https://www.instagram.com/Alice/"), "alice")

    def test_accepts_link_without_scheme_and_with_query(self):
        self.assertEqual(username_from_profile_link("instagram.com/alice?hl=pt"), "alice")

    def test_rejects_non_instagram_host(self):
        with self.assertRaises(ValueError):
            username_from_profile_link("https://example.com/alice")

    def test_rejects_link_without_username(self):
        with self.assertRaises(ValueError):
            username_from_profile_link("https://www.instagram.com/")


class ExtractUsernamesTest(unittest.TestCase):
    def test_reads_profile_links_in_order_from_following_page(self):
        self.assertEqual(extract_usernames(FOLLOWING_HTML), ["bob", "dave"])

    def test_ignores_non_profile_links(self):
        page = '<a href="https://www.instagram.com/p/abc123/">post</a>'
        self.assertEqual(extract_usernames(page), [])


class LoadFollowsReportTest(unittest.TestCase):
    def assert_report_matches_fixture(self, export_path: Path):
        report = load_follows_report(export_path, "alice")

        self.assertEqual(report.owner, "alice")
        self.assertEqual(report.followers, ("bob", "carol"))
        self.assertEqual(report.following, ("bob", "dave"))
        self.assertEqual(report.not_following_back, ["dave"])
        self.assertEqual(report.not_followed_back, ["carol"])

    def test_reads_extracted_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = write_export_as_folder(Path(temp_dir))
            self.assert_report_matches_fixture(export_path)

    def test_reads_zip_without_extracting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = write_export_as_zip(Path(temp_dir) / "export.zip")
            self.assert_report_matches_fixture(export_path)

    def test_rejects_export_from_another_account(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = write_export_as_zip(Path(temp_dir) / "export.zip")
            with self.assertRaises(ExportOwnerMismatchError):
                load_follows_report(export_path, "someone_else")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

# Só as páginas de contas: `following_hashtags.html` lista hashtags e não entra aqui.
FOLLOWERS_ENTRY = re.compile(r"(^|/)connections/followers_and_following/followers(_\d+)?\.html$")
FOLLOWING_ENTRY = re.compile(r"(^|/)connections/followers_and_following/following(_\d+)?\.html$")
PROFILE_HREF = re.compile(r"^https?://(?:www\.)?instagram\.com/(?:_u/)?([A-Za-z0-9._]+)/?$")
EXPORT_OWNER = re.compile(r"Gerado por\s+([A-Za-z0-9._]+)\s+em\b")
INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com"}


class ExportOwnerMismatchError(ValueError):
    pass


@dataclass(frozen=True)
class FollowsReport:
    owner: str
    followers: tuple[str, ...]
    following: tuple[str, ...]

    @property
    def not_following_back(self) -> list[str]:
        followers = set(self.followers)
        return [username for username in self.following if username not in followers]

    @property
    def not_followed_back(self) -> list[str]:
        following = set(self.following)
        return [username for username in self.followers if username not in following]


def username_from_profile_link(link: str) -> str:
    normalized_link = link.strip()
    if "://" not in normalized_link:
        normalized_link = f"https://{normalized_link}"

    parsed_link = urlparse(normalized_link)
    if parsed_link.hostname not in INSTAGRAM_HOSTS:
        raise ValueError(f"Link não é do Instagram: {link}")

    path_segments = [segment for segment in parsed_link.path.split("/") if segment]
    if not path_segments:
        raise ValueError(f"Link não tem nome de usuário: {link}")
    return path_segments[0].lower()


class _ProfileLinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.usernames: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        match = PROFILE_HREF.match(href)
        if match:
            self.usernames.append(match.group(1).lower())


def extract_usernames(page_html: str) -> list[str]:
    collector = _ProfileLinkCollector()
    collector.feed(page_html)
    return collector.usernames


def list_entries(export_path: Path) -> list[str]:
    if export_path.is_dir():
        return [
            path.relative_to(export_path).as_posix()
            for path in export_path.rglob("*")
            if path.is_file()
        ]
    with zipfile.ZipFile(export_path) as archive:
        return archive.namelist()


def read_entry(export_path: Path, entry: str) -> str:
    if export_path.is_dir():
        return (export_path / entry).read_text(encoding="utf-8")
    with zipfile.ZipFile(export_path) as archive:
        return archive.read(entry).decode("utf-8")


def _owner_from_page(page_html: str) -> str | None:
    match = EXPORT_OWNER.search(page_html)
    return match.group(1).lower() if match else None


def read_section(
    export_path: Path, entry_pattern: re.Pattern[str]
) -> tuple[list[str], str | None]:
    usernames: list[str] = []
    owner: str | None = None
    for entry in sorted(list_entries(export_path)):
        if not entry_pattern.search(entry):
            continue
        page_html = read_entry(export_path, entry)
        owner = owner or _owner_from_page(page_html)
        usernames.extend(extract_usernames(page_html))
    return list(dict.fromkeys(usernames)), owner


def load_follows_report(export_path: Path, profile_username: str) -> FollowsReport:
    followers, followers_owner = read_section(export_path, FOLLOWERS_ENTRY)
    following, following_owner = read_section(export_path, FOLLOWING_ENTRY)

    owner = followers_owner or following_owner
    if owner is None:
        raise FileNotFoundError(
            f"Não encontrei as seções de seguidores/seguindo em {export_path}"
        )
    if owner != profile_username:
        raise ExportOwnerMismatchError(
            f"O export é da conta '{owner}', não de '{profile_username}'."
        )
    return FollowsReport(owner=owner, followers=tuple(followers), following=tuple(following))


def _format_section(title: str, usernames: list[str]) -> str:
    body_lines = [f"- @{username}" for username in usernames] or ["  (ninguém)"]
    return "\n".join([f"{title} ({len(usernames)}):", *body_lines])


def format_report(report: FollowsReport) -> str:
    return "\n".join(
        [
            f"Conta: @{report.owner}",
            f"Seguidores: {len(report.followers)}",
            f"Seguindo: {len(report.following)}",
            "",
            _format_section("Você segue e não te segue de volta", report.not_following_back),
            "",
            _format_section("Te seguem e você não segue de volta", report.not_followed_back),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compara seguidores e seguindo a partir do export de dados do Instagram."
    )
    parser.add_argument("profile_link", help="Link do perfil, ex.: https://www.instagram.com/usuario/")
    parser.add_argument(
        "export",
        type=Path,
        help="Pasta extraída ou arquivo .zip do export de dados do Instagram",
    )
    args = parser.parse_args(argv)

    try:
        report = load_follows_report(args.export, username_from_profile_link(args.profile_link))
    except (ValueError, FileNotFoundError, zipfile.BadZipFile) as error:
        print(f"Erro: {error}", file=sys.stderr)
        return 1

    print(format_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

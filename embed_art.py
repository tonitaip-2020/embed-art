#!/usr/bin/env python3
from __future__ import annotations

# run with py embed_art.py "D:\Music"

import argparse
import mimetypes
from pathlib import Path

from mutagen.id3 import APIC, ID3, ID3NoHeaderError, PictureType


COVER_NAMES = (
    "cover.jpg", "cover.jpeg", "cover.png",
    "folder.jpg", "folder.jpeg", "folder.png",
    "front.jpg", "front.jpeg", "front.png",
)


def find_cover(directory: Path) -> Path | None:
    files = {
        path.name.casefold(): path
        for path in directory.iterdir()
        if path.is_file()
    }

    # Prefer conventional cover filenames, as before.
    for name in COVER_NAMES:
        if name in files:
            return files[name]

    # Example: "2025 - Walking On Phantom Ice" -> "Walking On Phantom Ice.jpg".
    # Only strip the prefix when it is a four-digit year followed by " - ".
    folder_name = directory.name
    album_name = folder_name[7:] if (
        len(folder_name) > 7
        and folder_name[:4].isdigit()
        and folder_name[4:7] == " - "
    ) else folder_name

    for extension in (".jpg", ".jpeg", ".png"):
        match = files.get((album_name + extension).casefold())
        if match is not None:
            return match
    return None


def load_tags(mp3_path: Path) -> ID3:
    try:
        return ID3(mp3_path)
    except ID3NoHeaderError:
        return ID3()


def has_embedded_artwork(tags: ID3) -> bool:
    # Do not replace any existing embedded artwork, regardless of its type.
    return any(key.startswith("APIC:") for key in tags)


def embed_cover(mp3_path: Path, cover_path: Path, *, dry_run: bool) -> str:
    tags = load_tags(mp3_path)

    if has_embedded_artwork(tags):
        return "skipped"

    if dry_run:
        return "would embed"

    mime, _ = mimetypes.guess_type(cover_path.name)
    if mime not in {"image/jpeg", "image/png"}:
        raise ValueError(f"Unsupported cover type: {cover_path.name}")

    tags.add(
        APIC(
            encoding=3,
            mime=mime,
            type=PictureType.COVER_FRONT,
            desc="Front cover",
            data=cover_path.read_bytes(),
        )
    )
    # ID3v2.3 maximizes compatibility with older players and sync tools.
    tags.save(mp3_path, v2_version=3)
    return "embedded"


def process_album(directory: Path, *, dry_run: bool) -> bool:
    mp3s = sorted(directory.glob("*.mp3"))
    if not mp3s:
        return False

    cover = find_cover(directory)
    if cover is None:
        # Check every MP3: an album is missing artwork only if none has APIC.
        has_art = False
        errors = []
        for mp3 in mp3s:
            try:
                if has_embedded_artwork(load_tags(mp3)):
                    has_art = True
                    break
            except Exception as exc:
                errors.append(f"{mp3.name}: {exc}")
        print(f"{directory}: no folder cover found")
        for error in errors:
            print(f"  ERROR: {error}")
        # Do not classify unreadable albums as definitely lacking artwork.
        return not has_art and not errors

    results: list[str] = []
    errors: list[str] = []

    for mp3 in mp3s:
        try:
            results.append(embed_cover(mp3, cover, dry_run=dry_run))
        except Exception as exc:
            errors.append(f"{mp3.name}: {exc}")

    embedded = results.count("embedded")
    skipped = results.count("skipped")
    would_embed = results.count("would embed")

    if errors:
        status = f"errors ({len(errors)})"
    elif embedded:
        status = f"embedded ({embedded}/{len(mp3s)} tracks)"
    elif would_embed:
        status = f"would embed ({would_embed}/{len(mp3s)} tracks)"
    elif skipped == len(mp3s):
        status = "found embedded cover, skipped"
    else:
        status = f"embedded {embedded}; skipped {skipped}"

    print(f"{directory}: {status}")

    for error in errors:
        print(f"  ERROR: {error}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed album-folder artwork into MP3 files that lack embedded artwork."
    )
    parser.add_argument("root", type=Path, help="Music root, e.g. D:\\Music")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report intended changes without modifying files.",
    )
    args = parser.parse_args()

    if not args.root.is_dir():
        parser.error(f"Not a directory: {args.root}")

    album_folders = sorted({mp3.parent for mp3 in args.root.rglob("*.mp3")})
    missing_artwork = []
    for album_folder in album_folders:
        if process_album(album_folder, dry_run=args.dry_run):
            missing_artwork.append(album_folder)

    print("\n=== Albums with no embedded artwork and no folder image ===")
    if missing_artwork:
        for folder in missing_artwork:
            print(folder)
        print(f"Total: {len(missing_artwork)} album(s)")
    else:
        print("None found.")


if __name__ == "__main__":
    main()
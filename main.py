#!/usr/bin/env python3
"""MangaMoins scan -> PDF.

Usage:
    python main.py OP1188
    python main.py https://mangamoins.com/scan/OP1188 -o one-piece-1188.pdf
    python main.py OP1188 --use-playwright
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from mangamoins_scraper.pdf_builder import build_pdf
from mangamoins_scraper.scraper import MangaMoinsScraper, ScraperError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MangaMoins scan -> PDF")
    parser.add_argument("target", help="Slug de chapitre (ex: OP1188) ou URL complète")
    parser.add_argument("-o", "--output", help="Fichier PDF de sortie")
    parser.add_argument(
        "--use-playwright",
        action="store_true",
        help="Forcer l'utilisation d'un navigateur headless dès le départ",
    )
    parser.add_argument("--verbose", action="store_true", help="Logs détaillés")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    scraper = MangaMoinsScraper()

    try:
        chapter = scraper.get_chapter_pages(args.target, force_playwright=args.use_playwright)
    except ScraperError as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1

    output_path = Path(args.output) if args.output else Path(f"{chapter.slug}.pdf")

    print(f"Chapitre : {chapter.slug} (source: {chapter.source})")
    print(f"{len(chapter.image_urls)} page(s) trouvée(s)")

    images: list[bytes] = []
    for i, url in enumerate(chapter.image_urls, start=1):
        print(f"  [{i}/{len(chapter.image_urls)}] {url}")
        try:
            images.append(scraper.download_image(url, chapter.referer))
        except Exception as exc:  # noqa: BLE001
            print(f"    Erreur de téléchargement : {exc}", file=sys.stderr)

    if not images:
        print("Erreur : aucune image téléchargée", file=sys.stderr)
        return 1

    print(f"Génération du PDF -> {output_path}")
    build_pdf(images, output_path)
    print(f"Terminé : {len(images)} page(s) -> {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

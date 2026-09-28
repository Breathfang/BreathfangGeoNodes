import logging
import sys
import zipfile
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE = Path("_NodepackZipGenerator.log")
LOG_MAX_BYTES = 1_000_000
LOG_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

SOURCE_DIR = Path("DragonGraph's Project")
BLEND_SUFFIX = ".blend"
CATEGORIES_FILE = SOURCE_DIR / "blender_assets.cats.txt"
READ_ME_FILE = SOURCE_DIR / "Read Before Use Nodes.txt"
READ_ME_ARCNAME = "READ THIS BEFORE USE NODES.txt"

PACK_NAME_TEMPLATE = "DragonGraph's Toolset Pack {node_version}"
OUTPUT_DIR = Path("Generated Nodepacks")
OUTPUT_NAME_TEMPLATE = "{pack_name} - Asset Library.zip"

COMPRESSION_LEVEL = 9

PAUSE_PROMPT = "Press enter to exit..."


@dataclass(frozen=True)
class ArchiveEntry:
    source: Path
    arcname: str

    def exists(self) -> bool:
        return self.source.is_file()


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def prompt_node_version() -> str:
    version = input("Node Version: (example: v1.1.0-alpha): ").strip()
    if not version:
        raise ValueError("Node version cannot be empty.")
    return version


def collect_blend_files() -> list[ArchiveEntry]:
    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(f"Source directory not found: {SOURCE_DIR}")

    # .blend files ship flat at the root of the archive, not nested
    return [
        ArchiveEntry(source=blend, arcname=blend.name)
        for blend in sorted(SOURCE_DIR.glob(f"*{BLEND_SUFFIX}"))
        if blend.is_file()
    ]


def collect_entries() -> list[ArchiveEntry]:
    static_entries = [
        ArchiveEntry(source=READ_ME_FILE, arcname=READ_ME_ARCNAME),
        ArchiveEntry(source=CATEGORIES_FILE, arcname=CATEGORIES_FILE.as_posix()),
    ]
    return static_entries + collect_blend_files()


def ensure_entries_exist(entries: list[ArchiveEntry], logger: logging.Logger) -> None:
    missing = [entry.source for entry in entries if not entry.exists()]
    if not missing:
        return
    for source in missing:
        logger.error("Missing source file: %s", source)
    raise FileNotFoundError(f"{len(missing)} source file(s) are missing.")


def build_archive(entries: list[ArchiveEntry], output_path: Path, logger: logging.Logger) -> None:
    with zipfile.ZipFile(
        output_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=COMPRESSION_LEVEL,
    ) as zipf:
        for entry in entries:
            zipf.write(entry.source, arcname=entry.arcname)
            logger.info("Inserted %s into zip as %s", entry.source, entry.arcname)


def main(logger: logging.Logger) -> int:
    pack_name = PACK_NAME_TEMPLATE.format(node_version=prompt_node_version())
    entries = collect_entries()
    ensure_entries_exist(entries, logger)

    logger.info("Collected %d source file(s).", len(entries))

    OUTPUT_DIR.mkdir(exist_ok=True)
    output_path = OUTPUT_DIR / OUTPUT_NAME_TEMPLATE.format(pack_name=pack_name)
    build_archive(entries, output_path, logger)

    logger.info("Wrote %s", output_path)
    logger.info("Done!")
    return 0


def run() -> int:
    logger = setup_logging()
    try:
        exit_code = main(logger)
    except Exception as error:
        logger.error("Error: %s", error, exc_info=True)
        exit_code = 1

    if sys.stdin.isatty():
        input(PAUSE_PROMPT)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(run())

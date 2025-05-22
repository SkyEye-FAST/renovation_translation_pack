# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Renovation Translation Resource Pack Generator

A script to generate a Minecraft resource pack for the Renovation Translation Project.
This script creates a zip file containing the necessary translation files for different
Minecraft versions and languages.
"""

import time
import zipfile as z
from concurrent.futures import ProcessPoolExecutor

from base import CURRENT_PATH, DATA_DIR, OUTPUT_DIR, VERSION_CONFIG


def process_version(version_data: tuple[str, dict]) -> tuple[str, float]:
    """Create a zip resource pack for a given version.

    Args:
        version_data (tuple[str, dict]): (version, config).

    Returns:
        tuple[str, float]: Processed version and elapsed time.
    """
    version, version_info = version_data
    start_time = time.time()
    version_dir = DATA_DIR / version
    output_dir = OUTPUT_DIR / version
    lang_format = version_info["format"]
    pack_dir = output_dir / f"renovation_translation_pack_{version}.zip"

    with z.ZipFile(pack_dir, "w", compression=z.ZIP_DEFLATED, compresslevel=6) as f:
        f.write(version_dir / "pack.mcmeta", arcname="pack.mcmeta")
        f.write(CURRENT_PATH / "pack.png", arcname="pack.png")

        files_to_add = []
        for file in version_info["variants"]:
            lang_file = output_dir / f"{file}.{lang_format}"
            if lang_file.exists():
                files_to_add.append((lang_file, f"assets/minecraft/lang/{file}.{lang_format}"))

        for lang_file, arcname in files_to_add:
            f.write(lang_file, arcname=arcname)

    elapsed_time = time.time() - start_time
    print(f"Version {version} processing completed in {elapsed_time:.2f} seconds.")
    return version, elapsed_time


if __name__ == "__main__":
    print("Starting resource pack generation...")
    total_start = time.time()

    with ProcessPoolExecutor() as executor:
        versions = list(VERSION_CONFIG.items())
        results = list(executor.map(process_version, versions))

    total_duration = time.time() - total_start
    print(f"\nAll processing completed in {total_duration:.2f} seconds.")

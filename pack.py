# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Renovation Translation Resource Pack Generator.

This script generates Minecraft resource packs for the Renovation Translation Project.
It creates a zip file containing the necessary translation files for different
Minecraft versions and languages.
"""

import time
import zipfile as z
from concurrent.futures import ProcessPoolExecutor

from base import CURRENT_PATH, DATA_DIR, OUTPUT_DIR, VERSION_CONFIG


def process_version(version_data: tuple[str, dict]) -> tuple[str, float]:
    """Create a zip resource pack for a given Minecraft version.

    Args:
        version_data (tuple[str, dict]): Tuple of (version, config).

    Returns:
        tuple[str, float]: Processed version and elapsed time in seconds.
    """
    version, version_info = version_data
    start_time = time.time()
    version_data_dir = DATA_DIR / version
    version_output_dir = OUTPUT_DIR / version
    lang_format = version_info["format"]
    zip_path = version_output_dir / f"renovation_translation_pack_{version}.zip"

    # Create the zip file and add required files
    with z.ZipFile(zip_path, "w", compression=z.ZIP_DEFLATED, compresslevel=6) as zipf:
        zipf.write(version_data_dir / "pack.mcmeta", arcname="pack.mcmeta")
        zipf.write(CURRENT_PATH / "pack.png", arcname="pack.png")

        # Collect translation files to add
        files_to_add = []
        variants = version_info["variants"] + version_info["extra_variants"]
        for variant in variants:
            lang_file = version_output_dir / f"{variant}.{lang_format}"
            if lang_file.exists():
                arcname = f"assets/minecraft/lang/{variant}.{lang_format}"
                files_to_add.append((lang_file, arcname))

        # Add translation files to the zip
        for lang_file, arcname in files_to_add:
            zipf.write(lang_file, arcname=arcname)

    elapsed_time = time.time() - start_time
    print(f"Version {version} processing completed in {elapsed_time:.2f} seconds.")
    return version, elapsed_time


if __name__ == "__main__":
    print("Starting resource pack generation...")
    total_start_time = time.time()

    with ProcessPoolExecutor() as executor:
        version_items = list(VERSION_CONFIG.items())
        results = list(executor.map(process_version, version_items))

    total_duration = time.time() - total_start_time
    print(f"\nAll processing completed in {total_duration:.2f} seconds.")

# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Renovation Translation Resource Pack Generator

A script to generate a Minecraft resource pack for the Renovation Translation Project.
This script creates a zip file containing the necessary translation files for different
Minecraft versions and languages.
"""

import zipfile as z

from base import DATA_DIR, OUTPUT_DIR, VERSION_CONFIG, P

print("Starting resource pack generation...")
for version in VERSION_CONFIG:
    print(f"\nGenerating resource pack for version {version}...")
    version_dir = DATA_DIR / version
    output_dir = OUTPUT_DIR / version
    version_info = VERSION_CONFIG[version]
    lang_format = version_info["format"]
    pack_dir = output_dir / f"renovation_translation_pack_{version}.zip"
    with z.ZipFile(pack_dir, "w", compression=z.ZIP_DEFLATED, compresslevel=9) as f:
        f.write(version_dir / "pack.mcmeta", arcname="pack.mcmeta")
        f.write(P / "pack.png", arcname="pack.png")
        for file in version_info["variants"]:
            lang_file = output_dir / f"{file}.{lang_format}"
            if lang_file.exists():
                print(f"Adding {file}.{lang_format} to the pack...")
                f.write(
                    lang_file,
                    arcname=f"assets/minecraft/lang/{file}.{lang_format}",
                )

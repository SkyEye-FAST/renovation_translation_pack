# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Renovation Translation Mapping Tool for Minecraft.

This script provides tools for mapping newer Minecraft translations back to older versions.
It supports both .lang and .json formats, handling translation key mappings
and updates between different Minecraft versions and languages.
"""

import asyncio
import time
from pathlib import Path

import aiofiles
import orjson as json

from base import CURRENT_PATH, DATA_DIR, OUTPUT_DIR, VERSION_CONFIG, LanguageData, LanguageMap

# List of prefix mapping rules for translation key compatibility between versions
PREFIX_MAP: list[tuple[str, str | tuple[str, ...]]] = [
    ("item.minecraft.lingering_potion.effect.", "lingering_potion.effect."),
    ("item.minecraft.splash_potion.effect.", "splash_potion.effect."),
    ("item.minecraft.potion.effect.", "potion.effect."),
    ("effect.minecraft.", "effect."),
    ("entity.minecraft.", "entity."),
    ("block.minecraft.", ("tile.", "item.")),
    ("item.minecraft.", ("tile.", "item.")),
    ("enchantment.minecraft.", "enchantment."),
]

mappings = json.loads((DATA_DIR / "mapping.json").read_text(encoding="utf-8"))


async def load_lang_file(file_paths: list[Path]) -> list[LanguageData]:
    """Load multiple .json or .lang files into dictionaries asynchronously.

    Args:
        file_paths (list[Path]): List of file paths to load.

    Returns:
        list[LanguageData]: List of loaded translation dictionaries.
    """

    async def _load_single_file(path: Path) -> LanguageData:
        path = CURRENT_PATH / path
        try:
            async with aiofiles.open(path, encoding="utf-8") as f:
                content = await f.read()
                if path.suffix == ".json":
                    return json.loads(content.encode())
                elif path.suffix == ".lang":
                    data: LanguageData = {}
                    for line in (
                        line.strip()
                        for line in content.splitlines()
                        if line.strip() and not line.startswith("#")
                    ):
                        if (sep_idx := line.find("=")) != -1:
                            data[line[:sep_idx].strip()] = line[sep_idx + 1 :].strip()
                    return data
        except Exception as e:
            print(f"Error loading {path}: {e}")
        return {}

    # Limit concurrent file loads to avoid overwhelming the system
    sem = asyncio.Semaphore(5)

    async def _load_with_semaphore(path: Path) -> LanguageData:
        async with sem:
            return await _load_single_file(path)

    return await asyncio.gather(*[_load_with_semaphore(path) for path in file_paths])


def map_new_to_old_keys(
    sources: tuple[LanguageData, LanguageData], format_type: str
) -> tuple[LanguageMap, LanguageMap]:
    """Map new translation keys to old ones, split by whether the original text matches.

    Args:
        sources (tuple[LanguageData, LanguageData]): Tuple containing new and old translation data.
        format_type (str): Format of the translation files, either "json" or "lang".

    Returns:
        (same_map, diff_map):
            same_map: Mapping of keys where the original text is the same.
            diff_map: Mapping of keys where the original text is different.
    """
    new_source, old_source = sources

    same_map: LanguageMap = {}
    diff_map: LanguageMap = {}

    if format_type == "json":
        for new_key, new_val in new_source.items():
            if new_key in old_source:
                if old_source[new_key] == new_val:
                    same_map.setdefault(new_key, []).append(new_key)
                else:
                    diff_map.setdefault(new_key, []).append(new_key)
        return same_map, diff_map

    # 1. Direct mapping
    for old_key, new_key in mappings.items():
        if new_key in new_source and old_key in old_source:
            if new_source[new_key] == old_source[old_key]:
                same_map.setdefault(new_key, []).append(old_key)
            else:
                diff_map.setdefault(new_key, []).append(old_key)

    # 2. Prefix-related mappings
    for new_key, new_val in new_source.items():
        for old_key, old_val in old_source.items():
            if new_val == old_val:
                for new_prefix, old_prefix in PREFIX_MAP:
                    if new_key.startswith(new_prefix):
                        if isinstance(old_prefix, str):
                            if old_key.startswith(old_prefix):
                                same_map.setdefault(new_key, []).append(old_key)
                        else:
                            if any(old_key.startswith(p) for p in old_prefix):
                                same_map.setdefault(new_key, []).append(old_key)
                if new_key == old_key:
                    same_map.setdefault(new_key, []).append(old_key)
    return same_map, diff_map


async def find_changed_translations(
    source: tuple[Path, Path],
    target: tuple[Path, Path],
    manually_check_path: Path | None = None,
    summary_path: Path | None = None,
) -> LanguageData:
    """Find translations that changed between versions asynchronously.

    Args:
        source (tuple[Path, Path]): Paths to (new_source, old_source) translation files.
        target (tuple[Path, Path]): Paths to (new_target, old_target) translation files.
        manually_check_path (Path | None): Path to save entries that require manual checking,
            or None to skip saving.
        summary_path (Path | None): Path to save summary entries (original text same but
            translation different), or None to skip saving.

    Returns:
        LanguageData: Dictionary of old keys and their updated translations.
    """
    new_source_path, old_source_path = source
    new_target_path, old_target_path = target

    all_files = [new_source_path, new_target_path, old_source_path, old_target_path]
    new_source, new_target, old_source, old_target = await load_lang_file(all_files)

    old_format = "lang" if old_source_path.suffix == ".lang" else "json"
    same_map, diff_map = map_new_to_old_keys((new_source, old_source), old_format)
    result: LanguageData = {}
    manually_check: list = []
    summary: list = []

    # Original text same
    for new_key, old_keys in same_map.items():
        new_translation = new_target.get(new_key)
        new_en_us = new_source.get(new_key)
        for old_key in old_keys:
            old_translation = old_target.get(old_key)
            if (
                new_translation is not None
                and old_translation is not None
                and new_translation != old_translation
            ):
                summary.append(
                    {
                        "old_key": old_key,
                        "old_value": old_translation,
                        "new_key": new_key,
                        "new_value": new_translation,
                        "en_us": new_en_us,
                    }
                )
                result[old_key] = new_translation

    # Original text different
    for new_key, old_keys in diff_map.items():
        new_translation = new_target.get(new_key)
        new_en_us = new_source.get(new_key)
        for old_key in old_keys:
            old_translation = old_target.get(old_key)
            old_en_us = old_source.get(old_key)
            if (
                new_translation is not None
                and old_translation is not None
                and new_translation != old_translation
            ):
                manually_check.append(
                    {
                        "old_key": old_key,
                        "old_value": old_translation,
                        "old_en_us": old_en_us,
                        "new_key": new_key,
                        "new_value": new_translation,
                        "new_en_us": new_en_us,
                    }
                )
                result[old_key] = new_translation

    if manually_check_path is not None and manually_check:
        async with aiofiles.open(manually_check_path, "w", encoding="utf-8", newline="\n") as f:
            content = json.dumps(
                manually_check,
                option=json.OPT_INDENT_2,
            ).decode("utf-8")
            await f.write(content)
    if summary_path is not None and summary:
        async with aiofiles.open(summary_path, "w", encoding="utf-8", newline="\n") as f:
            content = json.dumps(
                summary,
                option=json.OPT_INDENT_2,
            ).decode("utf-8")
            await f.write(content)
    return result


async def save_lang_file(data: LanguageData, file_path: Path) -> None:
    """Save dictionary to a .lang file with sorted keys asynchronously.

    Args:
        data (LanguageData): Dictionary of translation key-value pairs.
        file_path (Path): Path where the .lang file should be saved.
    """
    path = CURRENT_PATH / file_path
    async with aiofiles.open(path, "w", encoding="utf-8", newline="\n") as f:
        for k in sorted(data):
            await f.write(f"{k}={data[k]}\n")


async def save_json_file(data: LanguageData, file_path: Path) -> None:
    """Save dictionary to a .json file with sorted keys asynchronously.

    Args:
        data (LanguageData): Dictionary of translation key-value pairs.
        file_path (Path): Path where the .json file should be saved.
    """
    async with aiofiles.open(file_path, "w", encoding="utf-8", newline="\n") as f:
        content = json.dumps(
            dict(sorted(data.items())),
            option=json.OPT_INDENT_2 | json.OPT_SORT_KEYS,
        ).decode("utf-8")
        await f.write(content)


async def process_version(version: str) -> None:
    """Process all language variants for a specific version asynchronously.

    Args:
        version (str): Minecraft version string to process.
    """
    start_time = time.time()
    config = VERSION_CONFIG[version]
    format_suffix = f".{config['format']}"

    version_data_dir = DATA_DIR / version
    version_data_dir.mkdir(parents=True, exist_ok=True)
    version_output_dir = OUTPUT_DIR / version
    version_output_dir.mkdir(parents=True, exist_ok=True)

    common_files = {
        "en_us": Path("mc_lang/full/en_us.json"),
        "source": Path(f"{version_data_dir}/{config['source']}{format_suffix}"),
    }

    tasks = []
    for variant in config["variants"]:
        variant_lower = variant.lower()
        files = [
            common_files["en_us"],
            common_files["source"],
            Path(f"mc_lang/full/{variant_lower}.json"),
            Path(f"{version_data_dir}/{variant}{format_suffix}"),
        ]

        output_path = version_output_dir / f"{variant}{format_suffix}"
        manually_check_dir = version_output_dir / "manually_check"
        manually_check_dir.mkdir(parents=True, exist_ok=True)
        manually_check_path = manually_check_dir / f"{variant}.json"
        summary_dir = version_output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_path = summary_dir / f"{variant}.json"

        changed = await find_changed_translations(
            source=(files[0], files[1]),
            target=(files[2], files[3]),
            manually_check_path=manually_check_path,
            summary_path=summary_path,
        )
        if format_suffix == ".lang":
            tasks.append(asyncio.create_task(save_lang_file(changed, output_path)))
        else:
            tasks.append(asyncio.create_task(save_json_file(changed, output_path)))

    await asyncio.gather(*tasks)
    elapsed_time = time.time() - start_time
    print(f"Version {version} processing completed in {elapsed_time:.2f} seconds.")


async def async_main() -> None:
    """Process translation updates for all configured versions asynchronously."""
    total_start = time.time()
    print("Starting processing...")
    print("Supported versions:")
    for version in VERSION_CONFIG:
        print(f" - {version}")

    tasks = [process_version(version) for version in VERSION_CONFIG]
    await asyncio.gather(*tasks)

    total_duration = time.time() - total_start
    print(f"\nAll processing completed in {total_duration:.2f} seconds.")


def main() -> None:
    """Entry point for the script."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Base module for the Renovation Translation Pack Project.

This module defines constants, type aliases, and configuration
used throughout the Renovation Translation Pack Project.
"""

import asyncio
import time
from pathlib import Path
from typing import Final, cast

import aiofiles
import orjson as json

from base import (
    CURRENT_PATH,
    DATA_DIR,
    OUTPUT_DIR,
    VERSION_CONFIG,
    LanguageData,
    LanguageMap,
    VersionConfigEntry,
)

# Prefix mapping rules for key compatibility
PREFIX_MAP: Final[list[tuple[str, str | tuple[str, ...]]]] = [
    ("item.minecraft.lingering_potion.effect.", "lingering_potion.effect."),
    ("item.minecraft.splash_potion.effect.", "splash_potion.effect."),
    ("item.minecraft.potion.effect.", "potion.effect."),
    ("effect.minecraft.", "effect."),
    ("entity.minecraft.", "entity."),
    ("block.minecraft.", ("tile.", "item.")),
    ("item.minecraft.", ("tile.", "item.")),
    ("enchantment.minecraft.", "enchantment."),
]

# Load direct mappings from data file
DIRECT_MAPPINGS: Final[LanguageMap] = json.loads(
    (DATA_DIR / "mapping.json").read_text(encoding="utf-8")
)


class LanguageFileLoader:
    """Handles asynchronous loading of .json and .lang translation files.

    This class provides methods to load single or multiple translation files
    asynchronously, supporting both JSON and .lang file formats. It uses a
    semaphore to limit concurrent file operations.
    """

    def __init__(self, current_path: Path, semaphore_limit: int = 5):
        """Initialize the loader with a path and semaphore limit.

        Args:
            current_path (Path): The base path from which to resolve file paths.
            semaphore_limit (int): The maximum number of concurrent file loading operations.
        """
        self._current_path = current_path
        self._semaphore = asyncio.Semaphore(semaphore_limit)

    async def _load_single_file(self, path: Path) -> LanguageData:
        """Loads a single .json or .lang file.

        Args:
            path (Path): The relative path to the translation file.

        Returns:
            LanguageData: A dictionary containing the translation data, or an empty
                        dictionary if an error occurs during loading.
        """
        absolute_path = self._current_path / path
        try:
            async with aiofiles.open(absolute_path, encoding="utf-8") as f:
                content = await f.read()
                if absolute_path.suffix == ".json":
                    return json.loads(content.encode())
                elif absolute_path.suffix == ".lang":
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
            print(f"Error loading {absolute_path}: {e}")
        return {}

    async def load_files(self, file_paths: list[Path]) -> list[LanguageData]:
        """Load multiple .json or .lang files into dictionaries asynchronously.

        Args:
            file_paths (list[Path]): A list of relative paths to the translation files.

        Returns:
            list[LanguageData]: A list of dictionaries, each containing translation data
                                for a corresponding file.
        """

        async def _load_with_semaphore(path: Path) -> LanguageData:
            async with self._semaphore:
                return await self._load_single_file(path)

        return await asyncio.gather(*[_load_with_semaphore(path) for path in file_paths])


def map_new_to_old_keys(
    new_source: LanguageData, old_source: LanguageData, format_type: str
) -> tuple[LanguageMap, LanguageMap]:
    """Map new translation keys to old ones, split by whether the original text matches.

    This function attempts to find corresponding old keys for new translation keys
    based on direct mappings from `DIRECT_MAPPINGS`, prefix-based rules from
    `PREFIX_MAP`, and direct key matches.

    Args:
        new_source (LanguageData): New English (source) translation data.
        old_source (LanguageData): Old English (source) translation data.
        format_type (str): Format of the translation files, either "json" or "lang".

    Returns:
        (same_map, diff_map):
            same_map: Mapping of keys where the original text is the same.
            diff_map: Mapping of keys where the original text is different.
    """
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

    # For .lang files, apply direct and prefix-related mappings
    # 1. Direct mapping from `DIRECT_MAPPINGS`
    for old_key, new_key_list_or_str in DIRECT_MAPPINGS.items():
        new_keys_list = (
            [new_key_list_or_str] if isinstance(new_key_list_or_str, str) else new_key_list_or_str
        )
        for single_new_key in new_keys_list:
            if single_new_key in new_source and old_key in old_source:
                if new_source[single_new_key] == old_source[old_key]:
                    same_map.setdefault(single_new_key, []).append(old_key)
                else:
                    diff_map.setdefault(single_new_key, []).append(old_key)

    # 2. Prefix-related mappings and direct key matches (if not already handled by direct mapping)
    for new_key, new_val in new_source.items():
        for old_key, old_val in old_source.items():
            if new_val == old_val:
                # Ensure direct mappings and earlier prefix matches take precedence
                if new_key in same_map or new_key in diff_map:
                    continue

                found_prefix_match = False
                for new_prefix, old_prefix_spec in PREFIX_MAP:
                    if new_key.startswith(new_prefix):
                        if isinstance(old_prefix_spec, str):
                            if old_key.startswith(old_prefix_spec):
                                same_map.setdefault(new_key, []).append(old_key)
                                found_prefix_match = True
                                break
                        else:  # old_prefix_spec is a tuple
                            if any(old_key.startswith(p) for p in old_prefix_spec):
                                same_map.setdefault(new_key, []).append(old_key)
                                found_prefix_match = True
                                break
                if not found_prefix_match and new_key == old_key:
                    same_map.setdefault(new_key, []).append(old_key)

    return same_map, diff_map


async def find_changed_translations(
    new_source: LanguageData,
    old_source: LanguageData,
    new_target: LanguageData,
    old_target: LanguageData,
    old_format: str,
    manually_check_path: Path | None = None,
    summary_path: Path | None = None,
) -> LanguageData:
    """Find translations that changed between versions asynchronously.

    This function identifies translation changes by comparing new and old source
    (English) and target language data. It also handles the special case of
    "extra_variants" where old target files might not exist, in which case
    it performs a full mapping from the new target.

    Args:
        new_source (LanguageData): New English (source) translation data.
        old_source (LanguageData): Old English (source) translation data.
        new_target (LanguageData): New target language translation data.
        old_target (LanguageData): Old target language translation data.
        old_format (str): Format of the old translation files, either "json" or "lang".
        manually_check_path (Path | None): Path to save entries that require manual checking,
            or None to skip saving. These are entries where English text changed, but
            target translation also changed.
        summary_path (Path | None): Path to save summary entries, or None to skip saving.
            These are entries where English text is the same, but target translation changed.

    Returns:
        LanguageData: Dictionary of old keys and their updated translations.
    """
    same_map, diff_map = map_new_to_old_keys(new_source, old_source, old_format)
    result: LanguageData = {}
    manually_check_entries: list[dict] = []
    summary_entries: list[dict] = []

    # If old_target is empty, it means this is an "extra_variant" that didn't exist before.
    # In this case, we want to map all relevant new_target translations to their old_keys.
    if not old_target:
        for new_key, old_keys in same_map.items():
            if new_key in new_target:
                for old_key in old_keys:
                    result[old_key] = new_target[new_key]
        for new_key, old_keys in diff_map.items():
            if new_key in new_target:
                for old_key in old_keys:
                    result[old_key] = new_target[new_key]
    else:  # Compare existing translations
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
                    summary_entries.append(
                        {
                            "old_key": old_key,
                            "old_value": old_translation,
                            "new_key": new_key,
                            "new_value": new_translation,
                            "en_us": new_en_us,
                        }
                    )
                    result[old_key] = new_translation

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
                    manually_check_entries.append(
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

    await _save_json_report(manually_check_path, manually_check_entries)
    await _save_json_report(summary_path, summary_entries)

    return result


async def _save_json_report(file_path: Path | None, data: list[dict]) -> None:
    """Helper to save a list of dictionaries to a JSON file.

    Args:
        file_path (Path | None): The path to the JSON file to create or overwrite.
        data (list[dict]): The list of dictionaries to save.
    """
    if file_path is not None and data:
        async with aiofiles.open(file_path, "w", encoding="utf-8", newline="\n") as f:
            content = json.dumps(
                data,
                option=json.OPT_INDENT_2,
            ).decode("utf-8")
            await f.write(content)


async def save_lang_file(data: LanguageData, file_path: Path) -> None:
    """Save dictionary to a .lang file with sorted keys asynchronously.

    Args:
        data (LanguageData): The dictionary of translation data to save.
        file_path (Path): The path to the .lang file to create or overwrite.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(file_path, "w", encoding="utf-8", newline="\n") as f:
        for k in sorted(data):
            await f.write(f"{k}={data[k]}\n")


async def save_json_file(data: LanguageData, file_path: Path) -> None:
    """Save dictionary to a .json file with sorted keys asynchronously.

    Args:
        data (LanguageData): The dictionary of translation data to save.
        file_path (Path): The path to the .json file to create or overwrite.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(file_path, "w", encoding="utf-8", newline="\n") as f:
        content = json.dumps(
            dict(sorted(data.items())),
            option=json.OPT_INDENT_2 | json.OPT_SORT_KEYS,
        ).decode("utf-8")
        await f.write(content)


async def process_version(version: str, loader: LanguageFileLoader) -> dict:
    """Process all language variants for a specific Minecraft version asynchronously.

    This function orchestrates the loading of source and target language files,
    finds changed translations, and saves the results for a given Minecraft version.
    It handles both regular and "extra" language variants.

    Args:
        version (str): Minecraft version string to process.
        loader (LanguageFileLoader): An instance of LanguageFileLoader for file operations.

    Returns:
        dict: A dictionary containing version, elapsed time, and changed translation counts
            per variant.
    """
    start_time = time.time()
    config = cast(VersionConfigEntry, VERSION_CONFIG[version])
    format_suffix = f".{config['format']}"

    version_data_dir = DATA_DIR / version
    version_output_dir = OUTPUT_DIR / version
    version_output_dir.mkdir(parents=True, exist_ok=True)

    new_source_path = Path("mc_lang/full/en_us.json")
    old_source_path = version_data_dir / f"{config['source']}{format_suffix}"

    tasks = []
    variant_changed_counts: dict[str, int] = {}

    all_variants_to_process = config["variants"] + config["extra_variants"]

    for variant in all_variants_to_process:
        variant_lower = variant.lower()
        new_target_path = Path(f"mc_lang/full/{variant_lower}.json")
        old_target_path = version_data_dir / f"{variant}{format_suffix}"

        base_files_to_load = [new_source_path, new_target_path, old_source_path]
        new_source, new_target, old_source = await loader.load_files(base_files_to_load)

        old_target: LanguageData = {}
        if variant in config["variants"] and old_target_path.exists():
            [loaded_old_target] = await loader.load_files([old_target_path])
            old_target = loaded_old_target

        manually_check_dir = version_output_dir / "manually_check"
        manually_check_dir.mkdir(parents=True, exist_ok=True)
        manually_check_path = manually_check_dir / f"{variant}.json"

        summary_dir = version_output_dir / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        summary_path = summary_dir / f"{variant}.json"

        output_path = version_output_dir / f"{variant}{format_suffix}"

        changed_translations = await find_changed_translations(
            new_source=new_source,
            old_source=old_source,
            new_target=new_target,
            old_target=old_target,
            old_format=config["format"],
            manually_check_path=manually_check_path,
            summary_path=summary_path,
        )
        variant_changed_counts[variant] = len(changed_translations)

        if format_suffix == ".lang":
            tasks.append(asyncio.create_task(save_lang_file(changed_translations, output_path)))
        else:
            tasks.append(asyncio.create_task(save_json_file(changed_translations, output_path)))

    await asyncio.gather(*tasks)
    elapsed_time = time.time() - start_time

    return {
        "version": version,
        "elapsed_time": elapsed_time,
        "changed_counts": variant_changed_counts,
    }


async def async_main() -> None:
    """Process translation updates for all configured versions asynchronously.

    This is the main asynchronous entry point for the script. It initializes
    the file loader, processes each configured Minecraft version concurrently,
    and prints a summary of the processing results.
    """
    total_start = time.time()
    print("Starting processing...")
    print("Supported versions:")
    for version in VERSION_CONFIG:
        print(f" - {version}")

    loader = LanguageFileLoader(CURRENT_PATH)

    version_tasks = [process_version(version, loader) for version in VERSION_CONFIG]
    results = await asyncio.gather(*version_tasks)
    total_duration = time.time() - total_start

    print("\n--- Processing Summary ---")
    results_map = {result["version"]: result for result in results}
    for version in VERSION_CONFIG:
        result = results_map.get(version)
        if result:
            print(f"\nVersion {result['version']}:")
            print(f"  Processing time: {result['elapsed_time']:.2f} seconds.")
            print("  Translation counts per variant:")
            for variant in VERSION_CONFIG[version]["variants"]:
                count = result["changed_counts"].get(variant, 0)
                print(f"    - {variant}: {count} strings updated")
            for variant in VERSION_CONFIG[version]["extra_variants"]:
                count = result["changed_counts"].get(variant, 0)
                print(f"    - {variant} (extra): {count} strings added")

    print(f"\nAll processing completed in {total_duration:.2f} seconds.")


def main() -> None:
    """Entry point for the script.

    This function serves as the synchronous entry point, which runs the
    asynchronous main function using asyncio.
    """
    asyncio.run(async_main())


if __name__ == "__main__":
    main()

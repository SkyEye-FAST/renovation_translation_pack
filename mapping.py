# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Renovation Translation Mapping Tool for Minecraft

A script for mapping newer Minecraft translations back to older versions.
Supports both .lang and .json formats, handling translation key mappings
and updates between different Minecraft versions and languages.
"""

import asyncio
import time
from pathlib import Path

import aiofiles
import ujson as json

from base import CURRENT_PATH, DATA_DIR, OUTPUT_DIR, VERSION_CONFIG, language_data, language_map

PREFIX_MAP: list[tuple[str, str | tuple[str, str]]] = [
    ("item.minecraft.lingering_potion.effect.", "lingering_potion.effect."),
    ("item.minecraft.splash_potion.effect.", "splash_potion.effect."),
    ("item.minecraft.potion.effect.", "potion.effect."),
    ("effect.minecraft.", "effect."),
    ("entity.minecraft.", "entity."),
    ("block.minecraft.", ("tile.", "item.")),
    ("item.minecraft.", "item."),
    ("enchantment.minecraft.", "enchantment."),
]


async def load_lang_file(file_paths: list[Path]) -> list[language_data]:
    """Load multiple .json or .lang files into dictionaries asynchronously."""

    async def _load_single_file(path: Path) -> language_data:
        path = CURRENT_PATH / path
        try:
            async with aiofiles.open(path, encoding="utf-8") as f:
                content = await f.read()
                if path.suffix == ".json":
                    return json.loads(content)
                elif path.suffix == ".lang":
                    data: language_data = {}
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

    sem = asyncio.Semaphore(5)

    async def _load_with_semaphore(path: Path) -> language_data:
        async with sem:
            return await _load_single_file(path)

    return await asyncio.gather(*[_load_with_semaphore(path) for path in file_paths])


def map_new_to_old_keys(
    source: tuple[language_data, language_data], format_type: str
) -> language_map:
    """Map new translation keys to old ones based on identical source language values.

    Args:
        source (tuple[Ldata, Ldata]): Tuple of (new_source, old_source) translations
        format_type (str): Format of old translation file (`lang` or `json`)

    Returns:
        Lmap: A dictionary mapping new keys to lists of corresponding old keys
    """
    new_source, old_source = source

    def check_key_format(new_key: str, old_key: str) -> bool:
        """Check if the new translation key and old translation key are compatible in format.

        Args:
            new_key (str): The translation key from the new version.
            old_key (str): The translation key from the old version.

        Returns:
            bool: True if the keys are considered format-compatible, False otherwise.
        """
        if format_type == "json":
            return new_key == old_key

        return (
            any(
                new_key.startswith(new_prefix)
                and (
                    old_key.startswith(old_prefix)
                    if isinstance(old_prefix, str)
                    else any(old_key.startswith(p) for p in old_prefix)
                )
                for new_prefix, old_prefix in PREFIX_MAP
            )
            or new_key == old_key
        )

    value_to_old_key: language_map = {}
    for k, v in old_source.items():
        value_to_old_key.setdefault(v, []).append(k)

    mapping: language_map = {}
    value_set = set(value_to_old_key.keys())

    for new_key, new_val in new_source.items():
        if new_val in value_set:
            for old_key in value_to_old_key[new_val]:
                if check_key_format(new_key, old_key):
                    mapping.setdefault(new_key, []).append(old_key)
    return mapping


async def find_changed_translations(
    source: tuple[Path, Path], target: tuple[Path, Path]
) -> language_data:
    """Find translations that changed between versions asynchronously.

    Args:
        source (tuple[Path, Path]): Paths to (new_source, old_source) translation files
        target (tuple[Path, Path]): Paths to (new_target, old_target) translation files

    Returns:
        Dictionary of old keys and their updated translations
    """
    new_source_path, old_source_path = source
    new_target_path, old_target_path = target

    all_files = [new_source_path, new_target_path, old_source_path, old_target_path]
    new_source, new_target, old_source, old_target = await load_lang_file(all_files)

    old_format = "lang" if old_source_path.suffix == ".lang" else "json"
    mapping = map_new_to_old_keys((new_source, old_source), old_format)
    result: language_data = {}
    for new_key, old_keys in mapping.items():
        new_translation = new_target.get(new_key)
        for old_key in old_keys:
            old_translation = old_target.get(old_key)
            if (
                new_translation is not None
                and old_translation is not None
                and new_translation != old_translation
            ):
                result[old_key] = new_translation
    return result


async def save_lang_file(data: language_data, file_path: Path) -> None:
    """Save dictionary to a .lang file with sorted keys asynchronously.

    Args:
        data (Ldata): Dictionary of translation key-value pairs
        file_path (Path): Path where the .lang file should be saved
    """
    path = CURRENT_PATH / file_path
    async with aiofiles.open(path, "w", encoding="utf-8", newline="\n") as f:
        for k in sorted(data):
            await f.write(f"{k}={data[k]}\n")


async def save_json_file(data: language_data, file_path: Path) -> None:
    """Save dictionary to a .json file with sorted keys asynchronously.

    Args:
        data (Ldata): Dictionary of translation key-value pairs
        file_path (Path): Path where the .json file should be saved
    """
    async with aiofiles.open(file_path, "w", encoding="utf-8", newline="\n") as f:
        content = json.dumps(dict(sorted(data.items())), ensure_ascii=False, indent=2)
        await f.write(content)


async def process_version(version: str) -> None:
    """Process all language variants for a specific version asynchronously.

    Args:
        version (str): Minecraft version string to process
    """
    start_time = time.time()
    config = VERSION_CONFIG[version]
    format_suffix = f".{config['format']}"

    version_dir = DATA_DIR / version
    version_dir.mkdir(parents=True, exist_ok=True)
    output_dir = OUTPUT_DIR / version
    output_dir.mkdir(parents=True, exist_ok=True)

    common_files = {
        "en_us": Path("mc_lang/full/en_us.json"),
        "source": Path(f"{version_dir}/{config['source']}{format_suffix}"),
    }

    tasks = []
    for variant in config["variants"]:
        variant_lower = variant.lower()
        files = [
            common_files["en_us"],
            common_files["source"],
            Path(f"mc_lang/full/{variant_lower}.json"),
            Path(f"{version_dir}/{variant}{format_suffix}"),
        ]

        changed = await find_changed_translations(
            source=(files[0], files[1]), target=(files[2], files[3])
        )

        output_path = output_dir / f"{variant}{format_suffix}"
        if format_suffix == ".lang":
            tasks.append(save_lang_file(changed, output_path))
        else:
            tasks.append(save_json_file(changed, output_path))

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

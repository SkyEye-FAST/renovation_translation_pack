# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Renovation Translation Mapping Tool for Minecraft

A script for mapping newer Minecraft translations back to older versions.
Supports both .lang and .json formats, handling translation key mappings
and updates between different Minecraft versions and languages.
"""

import json
from pathlib import Path
from typing import Final, TypeAlias

Ldata: TypeAlias = dict[str, str]
Lmap: TypeAlias = dict[str, list[str]]
P: Final[Path] = Path(__file__).resolve().parent


def load_lang_file(file_path: str) -> Ldata:
    """Load a .json or .lang file into a dictionary.

    Args:
        file_path (str): Path to the .json or .lang file

    Returns:
        Ldata: A dictionary containing the translation key-value pairs
    """
    path = P / Path(file_path)
    data: Ldata = {}
    if path.suffix == ".json":
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    elif path.suffix == ".lang":
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
    return data


def map_new_to_old_keys(new_en: Ldata, old_en: Ldata) -> Lmap:
    """Map new translation keys to old ones based on identical English values.

    Args:
        new_en (Ldata): Dictionary containing new version's English translations
        old_en (Ldata): Dictionary containing old version's English translations

    Returns:
        Lmap: A dictionary mapping new keys to lists of corresponding old keys
    """

    def check_key_format(new_key: str, old_key: str) -> bool:
        """Check format compatibility between new and old keys."""
        if new_key.startswith("item.minecraft.lingering_potion.effect."):
            return old_key.startswith("lingering_potion.effect.")
        if new_key.startswith("item.minecraft.splash_potion.effect."):
            return old_key.startswith("splash_potion.effect.")
        if new_key.startswith("item.minecraft.potion.effect."):
            return old_key.startswith("potion.effect.")
        if new_key.startswith("effect.minecraft."):
            return old_key.startswith("effect.")
        if new_key.startswith("entity.minecraft."):
            return old_key.startswith("entity.")
        if new_key.startswith("block.minecraft."):
            return old_key.startswith("tile.")

        return new_key == old_key

    value_to_old_key: Lmap = {}
    for k, v in old_en.items():
        value_to_old_key.setdefault(v, []).append(k)

    mapping: Lmap = {}
    for new_key, new_val in new_en.items():
        if new_val in value_to_old_key:
            for old_key in value_to_old_key[new_val]:
                if check_key_format(new_key, old_key):
                    mapping.setdefault(new_key, []).append(old_key)
    return mapping


def find_changed_translations(
    new_en_path: str, new_zh_path: str, old_en_path: str, old_zh_path: str
) -> Ldata:
    """Find Chinese translations that changed between versions.

    Args:
        new_en_path (str): Path to new version English translation file
        new_zh_path (str): Path to new version Chinese translation file
        old_en_path (str): Path to old version English translation file
        old_zh_path (str): Path to old version Chinese translation file

    Returns:
        Dictionary of old keys and their updated translations
    """
    new_en = load_lang_file(new_en_path)
    new_zh = load_lang_file(new_zh_path)
    old_en = load_lang_file(old_en_path)
    old_zh = load_lang_file(old_zh_path)

    mapping = map_new_to_old_keys(new_en, old_en)
    result: Ldata = {}
    for new_key, old_keys in mapping.items():
        new_cn = new_zh.get(new_key)
        for old_key in old_keys:
            old_cn = old_zh.get(old_key)
            if new_cn is not None and old_cn is not None and new_cn != old_cn:
                result[old_key] = new_cn
    return result


def save_lang_file(data: Ldata, file_path: str) -> None:
    """Save dictionary to a .lang file with sorted keys.

    Args:
        data (Ldata): Dictionary of translation key-value pairs
        file_path (str): Path where the .lang file should be saved
    """
    path = P / Path(file_path)
    with path.open("w", encoding="utf-8") as f:
        for k in sorted(data):
            f.write(f"{k}={data[k]}\n")


def save_json_file(data: Ldata, file_path: Path) -> None:
    """Save dictionary to a .json file with sorted keys.

    Args:
        data (Ldata): Dictionary of translation key-value pairs
        file_path (Path): Path where the .json file should be saved
    """
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(dict(sorted(data.items())), f, ensure_ascii=False, indent=2)


VERSION_CONFIGS = {
    "1.12.2": {"format": "lang", "variants": ["zh_cn", "zh_tw"]},
    "1.13.2": {"format": "json", "variants": ["zh_cn", "zh_tw"]},
    "1.14.4": {"format": "json", "variants": ["zh_cn", "zh_tw"]},
    "1.15.2": {"format": "json", "variants": ["zh_cn", "zh_tw", "zh_hk"]},
    "1.16.5": {"format": "json", "variants": ["zh_cn", "zh_tw", "zh_hk"]},
    "1.17.1": {"format": "json", "variants": ["zh_cn", "zh_tw", "zh_hk"]},
    "1.18.2": {"format": "json", "variants": ["zh_cn", "zh_tw", "zh_hk"]},
    "1.19.2": {"format": "json", "variants": ["zh_cn", "zh_tw", "zh_hk"]},
}


def process_version(version: str) -> None:
    """Process all language variants for a specific version.

    Args:
        version (str): Minecraft version string to process
    """
    config = VERSION_CONFIGS[version]
    format_suffix = f".{config['format']}"
    version_path = f"lang/{version}"

    output_dir = P / "output" / version
    output_dir.mkdir(parents=True, exist_ok=True)

    for variant in config["variants"]:
        changed_translations = find_changed_translations(
            new_en_path="mc_lang/full/en_us.json",
            new_zh_path=f"mc_lang/full/{variant}.json",
            old_en_path=f"{version_path}/en_us{format_suffix}",
            old_zh_path=f"{version_path}/{variant}{format_suffix}",
        )

        output_path = output_dir / f"{variant}{format_suffix}"

        if format_suffix == ".lang":
            save_lang_file(changed_translations, output_path)
        else:
            save_json_file(changed_translations, output_path)

        print(f"Saved renovated {variant} translations ({len(changed_translations)} entries).")


def main() -> None:
    """Process translation updates for all configured versions."""
    print("Starting processing...")
    print("Supported versions:")
    for version in VERSION_CONFIGS:
        print(f" - {version}")
    for version in VERSION_CONFIGS:
        print(f"\nProcessing Minecraft version {version}...")
        process_version(version)


if __name__ == "__main__":
    main()

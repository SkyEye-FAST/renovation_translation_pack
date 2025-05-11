# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Renovation Translation Mapping Tool for Minecraft

A script for mapping newer Minecraft translations back to older versions.
Supports both .lang and .json formats, handling translation key mappings
and updates between different Minecraft versions and languages.
"""

from pathlib import Path

import ujson as json

from base import DATA_DIR, OUTPUT_DIR, VERSION_CONFIG, Ldata, Lmap, P


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


def map_new_to_old_keys(new_en: Ldata, old_en: Ldata, old_format: str) -> Lmap:
    """Map new translation keys to old ones based on identical English values.

    Args:
        new_en (Ldata): Dictionary containing new version's English translations
        old_en (Ldata): Dictionary containing old version's English translations
        old_format (str): Format of old translation file ("lang" or "json")

    Returns:
        Lmap: A dictionary mapping new keys to lists of corresponding old keys
    """

    def check_key_format(new_key: str, old_key: str) -> bool:
        """Check if the new translation key and old translation key are compatible in format.

        Args:
            new_key (str): The translation key from the new version.
            old_key (str): The translation key from the old version.

        Returns:
            bool: True if the keys are considered format-compatible, False otherwise.
        """
        if old_format == "json":
            return new_key == old_key

        prefix_map = [
            ("item.minecraft.lingering_potion.effect.", "lingering_potion.effect."),
            ("item.minecraft.splash_potion.effect.", "splash_potion.effect."),
            ("item.minecraft.potion.effect.", "potion.effect."),
            ("effect.minecraft.", "effect."),
            ("entity.minecraft.", "entity."),
            ("block.minecraft.", ("tile.", "item.")),
            ("item.minecraft.", "item."),
            ("enchantment.minecraft.", "enchantment."),
        ]

        for new_prefix, old_prefix in prefix_map:
            if new_key.startswith(new_prefix):
                if isinstance(old_prefix, tuple):
                    return any(old_key.startswith(p) for p in old_prefix)
                return old_key.startswith(old_prefix)

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

    old_format = "lang" if Path(old_en_path).suffix == ".lang" else "json"
    mapping = map_new_to_old_keys(new_en, old_en, old_format)
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


def process_version(version: str) -> None:
    """Process all language variants for a specific version.

    Args:
        version (str): Minecraft version string to process
    """
    config = VERSION_CONFIG[version]
    format_suffix = f".{config['format']}"

    output_dir = OUTPUT_DIR / version
    output_dir.mkdir(parents=True, exist_ok=True)

    for variant in config["variants"]:
        changed_translations = find_changed_translations(
            old_en_path=f"{DATA_DIR}/{version}/en_us{format_suffix}",
            old_zh_path=f"{DATA_DIR}/{version}/{variant}{format_suffix}",
            new_en_path="mc_lang/full/en_us.json",
            new_zh_path=f"mc_lang/full/{variant.lower()}.json",
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
    for version in VERSION_CONFIG:
        print(f" - {version}")
    for version in VERSION_CONFIG:
        print(f"\nProcessing Minecraft version {version}...")
        process_version(version)


if __name__ == "__main__":
    main()

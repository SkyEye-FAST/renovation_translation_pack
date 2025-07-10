# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Base module for the Renovation Translation Pack Project.

This module defines constants, type aliases, and configuration
used throughout the Renovation Translation Pack Project.
"""

from pathlib import Path
from typing import Final, TypedDict

# Type alias for a dictionary mapping translation keys to their values
type LanguageData = dict[str, str]
# Type alias for a dictionary mapping translation keys to a list of keys
type LanguageMap = dict[str, list[str]]


# Type definition for a single version's configuration
class VersionConfigEntry(TypedDict):
    """Configuration for a specific Minecraft version's translation format and variants."""

    format: str
    source: str
    variants: list[str]
    extra_variants: list[str]


# The current directory of this script
CURRENT_PATH: Final[Path] = Path(__file__).resolve().parent
# Directory containing translation data files
DATA_DIR: Final[Path] = CURRENT_PATH / "data"
# Directory for output files
OUTPUT_DIR: Final[Path] = CURRENT_PATH / "output"

# Configuration for supported Minecraft versions, their translation formats, and language variants
VERSION_CONFIG: Final[dict[str, VersionConfigEntry]] = {
    "1.7.10": {
        "format": "lang",
        "source": "en_US",
        "variants": ["zh_CN", "zh_TW"],
        "extra_variants": ["zh_HK", "lzh"],
    },
    "1.8.9": {
        "format": "lang",
        "source": "en_US",
        "variants": ["zh_CN", "zh_TW"],
        "extra_variants": ["zh_HK", "lzh"],
    },
    "1.9.4": {
        "format": "lang",
        "source": "en_US",
        "variants": ["zh_CN", "zh_TW"],
        "extra_variants": ["zh_HK", "lzh"],
    },
    "1.10.2": {
        "format": "lang",
        "source": "en_US",
        "variants": ["zh_CN", "zh_TW"],
        "extra_variants": ["zh_HK", "lzh"],
    },
    "1.11.2": {
        "format": "lang",
        "source": "en_us",
        "variants": ["zh_cn", "zh_tw"],
        "extra_variants": ["zh_hk", "lzh"],
    },
    "1.12.2": {
        "format": "lang",
        "source": "en_us",
        "variants": ["zh_cn", "zh_tw"],
        "extra_variants": ["zh_hk", "lzh"],
    },
    "1.13.2": {
        "format": "json",
        "source": "en_us",
        "variants": ["zh_cn", "zh_tw"],
        "extra_variants": ["zh_hk", "lzh"],
    },
    "1.14.4": {
        "format": "json",
        "source": "en_us",
        "variants": ["zh_cn", "zh_tw"],
        "extra_variants": ["zh_hk", "lzh"],
    },
    "1.15.2": {
        "format": "json",
        "source": "en_us",
        "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"],
        "extra_variants": [],
    },
    "1.16.5": {
        "format": "json",
        "source": "en_us",
        "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"],
        "extra_variants": [],
    },
    "1.17.1": {
        "format": "json",
        "source": "en_us",
        "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"],
        "extra_variants": [],
    },
    "1.18.2": {
        "format": "json",
        "source": "en_us",
        "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"],
        "extra_variants": [],
    },
    "1.19.2": {
        "format": "json",
        "source": "en_us",
        "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"],
        "extra_variants": [],
    },
}

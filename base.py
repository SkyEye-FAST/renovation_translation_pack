# @Author: SkyEye_FAST <skyeyefast@foxmail.com>
# @Copyright: Copyright (C) 2025 SkyEye_FAST
"""Base module for the Renovation Translation Pack Project."""

from pathlib import Path
from typing import Final

type Ldata = dict[str, str]
type Lmap = dict[str, list[str]]
P: Final[Path] = Path(__file__).resolve().parent
DATA_DIR: Final[Path] = P / "data"
OUTPUT_DIR: Final[Path] = P / "output"

VERSION_CONFIG = {
    "1.7.10": {"format": "lang", "source": "en_US", "variants": ["zh_CN", "zh_TW"]},
    "1.8.9": {"format": "lang", "source": "en_US", "variants": ["zh_CN", "zh_TW"]},
    "1.9.4": {"format": "lang", "source": "en_US", "variants": ["zh_CN", "zh_TW"]},
    "1.10.2": {"format": "lang", "source": "en_US", "variants": ["zh_CN", "zh_TW"]},
    "1.11.2": {"format": "lang", "source": "en_us", "variants": ["zh_cn", "zh_tw"]},
    "1.12.2": {"format": "lang", "source": "en_us", "variants": ["zh_cn", "zh_tw"]},
    "1.13.2": {"format": "json", "source": "en_us", "variants": ["zh_cn", "zh_tw"]},
    "1.14.4": {"format": "json", "source": "en_us", "variants": ["zh_cn", "zh_tw"]},
    "1.15.2": {"format": "json", "source": "en_us", "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"]},
    "1.16.5": {"format": "json", "source": "en_us", "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"]},
    "1.17.1": {"format": "json", "source": "en_us", "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"]},
    "1.18.2": {"format": "json", "source": "en_us", "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"]},
    "1.19.2": {"format": "json", "source": "en_us", "variants": ["zh_cn", "zh_hk", "zh_tw", "lzh"]},
}

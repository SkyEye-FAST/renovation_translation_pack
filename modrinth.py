"""Plan release-only Modrinth uploads and repair existing project versions."""

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from base import VERSION_CONFIG

PROJECT_ID = "AO8iY7f9"
API_URL = "https://api.modrinth.com/v2"
MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
USER_AGENT = "SkyEye-FAST/renovation_translation_pack (Modrinth publishing)"


def request_json(url, *, method="GET", data=None, token=None):
    """Request JSON, failing on HTTP errors instead of assuming missing versions."""
    headers = {"User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = token
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(
        url,
        data=json.dumps(data).encode() if data is not None else None,
        headers=headers,
        method=method,
    )
    for attempt in range(4):
        try:
            with urlopen(request, timeout=60) as response:
                content = response.read()
                if response.headers.get("X-Ratelimit-Remaining") == "0":
                    time.sleep(float(response.headers.get("X-Ratelimit-Reset", "60")) + 1)
            break
        except HTTPError as error:
            if error.code != 429 or attempt == 3:
                raise
            delay = float(error.headers.get("X-Ratelimit-Reset", "60")) + 1
            print(f"Rate limited; retrying in {delay}s", flush=True)
            time.sleep(delay)
    return json.loads(content) if content else None


def version_name(source, target):
    """Distinguish supported Minecraft versions from the translation source."""
    return f"Minecraft {target} - Translations from {source}"


def release_types():
    """Read authoritative source-version types from Mojang."""
    return {version["id"]: version["type"] for version in request_json(MANIFEST_URL)["versions"]}


def project_versions(token=None):
    """Read the project's complete version inventory."""
    query = f"?check={time.time_ns()}"
    return request_json(f"{API_URL}/project/{PROJECT_ID}/version{query}", token=token)


def upload_matrix(source, types, versions):
    """Include only missing target builds of an official Minecraft release."""
    if source not in types:
        raise ValueError(f"Unknown Minecraft source version: {source}")
    if types[source] != "release":
        return {"include": []}
    existing = {version["version_number"] for version in versions}
    entries = []
    for target in VERSION_CONFIG:
        number = f"{source}-{target}"
        if number in existing:
            continue
        if target == "1.7.10":
            game_versions = [target]
        elif target == "1.19.2":
            game_versions = ["1.19", "1.19.1", "1.19.2"]
        else:
            game_versions = [f"{target.rsplit('.', 1)[0]}.x"]
        entries.append(
            {
                "mcversion": target,
                "game_versions": game_versions,
                "version": number,
                "name": version_name(source, target),
            }
        )
    return {"include": entries}


def repair_plan(types, versions):
    """Validate the complete inventory before proposing any mutations."""
    changes = []
    for version in versions:
        source, separator, target = version["version_number"].rpartition("-")
        if not separator or target not in VERSION_CONFIG or source not in types:
            raise ValueError(f"Unrecognized project version: {version['version_number']}")
        if version["project_id"] != PROJECT_ID:
            raise ValueError(f"Unexpected project for version {version['id']}")
        if types[source] != "release":
            changes.append({"id": version["id"], "method": "DELETE", "data": None})
        elif version["name"] != version_name(source, target):
            changes.append(
                {
                    "id": version["id"],
                    "method": "PATCH",
                    "data": {"name": version_name(source, target)},
                }
            )
    return changes


def main():
    """Prepare uploads or preview/apply a historical version repair."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare")
    prepare.add_argument("source")
    repair = commands.add_parser("repair")
    repair.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    types = release_types()

    if args.command == "prepare":
        versions = project_versions() if types.get(args.source) == "release" else []
        matrix = upload_matrix(args.source, types, versions)
        output = (
            f"matrix={json.dumps(matrix)}\npublish={'true' if matrix['include'] else 'false'}\n"
        )
        print(output, end="")
        if output_path := os.environ.get("GITHUB_OUTPUT"):
            with Path(output_path).open("a", encoding="utf-8") as stream:
                stream.write(output)
        return

    token = os.environ.get("MODRINTH_TOKEN")
    if args.apply and not token:
        parser.error("--apply requires MODRINTH_TOKEN")
    versions = project_versions(token)
    changes = repair_plan(types, versions)
    # Preserve the exact inventory and proposed changes before deleting anything.
    Path("modrinth-repair.json").write_text(
        json.dumps({"versions": versions, "changes": changes}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for method in ("DELETE", "PATCH"):
        print(f"{method}: {sum(change['method'] == method for change in changes)}")
    if not args.apply:
        print("Preview only. Use --apply to execute modrinth-repair.json changes.")
        return

    def apply_change(change):
        request_json(
            f"{API_URL}/version/{change['id']}",
            method=change["method"],
            data=change["data"],
            token=token,
        )
        return change

    # Bound in-flight work so an error stops the repair after the current batch.
    with ThreadPoolExecutor(max_workers=8) as executor:
        for start in range(0, len(changes), 8):
            batch = changes[start : start + 8]
            for index, change in enumerate(executor.map(apply_change, batch), start + 1):
                print(f"{index}/{len(changes)} {change['method']} {change['id']}", flush=True)
    remaining = repair_plan(types, project_versions(token))
    if remaining:
        raise RuntimeError(f"Repair incomplete: {len(remaining)} changes remain")
    print("Verified: all remaining versions use release sources and corrected names.")


if __name__ == "__main__":
    main()

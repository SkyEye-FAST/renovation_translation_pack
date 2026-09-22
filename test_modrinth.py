"""Regression tests for release gating and historical version deletion."""

import unittest

from base import VERSION_CONFIG
from modrinth import PROJECT_ID, repair_plan, upload_matrix, version_name

TYPES = {
    "1.21.8": "release",
    "26.3": "release",
    "25w21a": "snapshot",
    "26.3-snapshot-1": "snapshot",
    "26.3-pre-1": "snapshot",
    "26.3-rc-1": "snapshot",
}


def version(source, target="1.19.2", name=None):
    """Build an inventory entry matching the old publisher's metadata."""
    return {
        "id": f"id-{source}",
        "project_id": PROJECT_ID,
        "version_number": f"{source}-{target}",
        "version_type": "release",
        "name": name or f"{source} to {target}",
    }


class ModrinthTests(unittest.TestCase):
    """Check publication and deletion against the source's actual release type."""

    def test_non_releases_never_publish(self):
        """Reject weekly snapshots, named snapshots, pre-releases and RCs."""
        for source, kind in TYPES.items():
            if kind != "release":
                with self.subTest(source=source):
                    self.assertEqual(upload_matrix(source, TYPES, []), {"include": []})

    def test_only_missing_targets_publish(self):
        """An existing target must not suppress other builds or publish again."""
        matrix = upload_matrix("26.3", TYPES, [version("26.3")])["include"]
        self.assertEqual(len(matrix), len(VERSION_CONFIG) - 1)
        self.assertNotIn("1.19.2", [entry["mcversion"] for entry in matrix])
        self.assertEqual(
            upload_matrix("26.3", TYPES, [version("26.3", t) for t in VERSION_CONFIG]),
            {"include": []},
        )

    def test_unknown_source_fails_closed(self):
        """Missing metadata must never authorize publishing or deletion."""
        with self.assertRaises(ValueError):
            upload_matrix("unknown", TYPES, [])
        with self.assertRaises(ValueError):
            repair_plan(TYPES, [version("unknown")])

    def test_repair_ignores_incorrect_modrinth_release_label(self):
        """Delete only non-release sources even if Modrinth calls them releases."""
        changes = repair_plan(TYPES, [version(source) for source in TYPES])
        deleted = {c["id"] for c in changes if c["method"] == "DELETE"}
        self.assertEqual(deleted, {f"id-{s}" for s in TYPES if TYPES[s] != "release"})
        renamed = [c for c in changes if c["method"] == "PATCH"]
        self.assertEqual(len(renamed), 2)
        self.assertEqual(renamed[1]["data"], {"name": "Minecraft 1.19.2 - Translations from 26.3"})

    def test_repaired_inventory_needs_no_changes(self):
        """A rerun must leave already corrected releases alone."""
        self.assertEqual(
            repair_plan(TYPES, [version("26.3", name=version_name("26.3", "1.19.2"))]),
            [],
        )

    def test_unknown_target_or_wrong_project_aborts(self):
        """Never mutate versions outside the expected project and target set."""
        with self.assertRaises(ValueError):
            repair_plan(TYPES, [version("25w21a", "1.99")])
        wrong_project = version("25w21a") | {"project_id": "another-project"}
        with self.assertRaises(ValueError):
            repair_plan(TYPES, [wrong_project])


if __name__ == "__main__":
    unittest.main()

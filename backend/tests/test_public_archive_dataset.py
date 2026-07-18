from __future__ import annotations

import unittest

from app.public_archive import load_public_archive_entries, validate_public_archive_entries


class PublicArchiveDatasetTests(unittest.TestCase):
    def test_public_archive_dataset_is_valid_and_sized_for_cold_start(self) -> None:
        entries = load_public_archive_entries()
        validate_public_archive_entries(entries)

        self.assertGreaterEqual(len(entries), 300)
        self.assertLessEqual(len(entries), 500)
        self.assertTrue(all(entry.author for entry in entries))
        self.assertTrue(all(entry.rights_status for entry in entries))
        self.assertTrue(
            all(
                entry.source_url is not None
                and any(
                    domain in str(entry.source_url)
                    for domain in ("gutenberg.org", "wikisource.org", "loc.gov", "archive.org")
                )
                for entry in entries
            )
        )


if __name__ == "__main__":
    unittest.main()

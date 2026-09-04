"""Guard against committing installation-specific private IP addresses."""

from __future__ import annotations

import re
import unittest
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[1]
TEXT_SUFFIXES = {".js", ".json", ".md", ".py", ".yaml", ".yml"}
IPV4_PATTERN = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
DOCUMENTATION_NETWORKS = (
    IPv4Network("192.0.2.0/24"),
    IPv4Network("198.51.100.0/24"),
    IPv4Network("203.0.113.0/24"),
)
PRIVATE_NETWORKS = (
    IPv4Network((IPv4Address(bytes((10, 0, 0, 0))), 8)),
    IPv4Network((IPv4Address(bytes((172, 16, 0, 0))), 12)),
    IPv4Network((IPv4Address(bytes((192, 168, 0, 0))), 16)),
)


class RepositoryPrivacyTest(unittest.TestCase):
    """Ensure examples cannot disclose a contributor's local network."""

    def test_no_private_ipv4_literals(self) -> None:
        """Tracked source and documentation use only TEST-NET examples."""
        findings: list[str] = []
        for path in REPOSITORY_ROOT.rglob("*"):
            relative_path = path.relative_to(REPOSITORY_ROOT)
            if (
                not path.is_file()
                or path.suffix not in TEXT_SUFFIXES
                or any(part in {".git", ".venv"} for part in relative_path.parts)
            ):
                continue
            text = path.read_text(encoding="utf-8")
            for match in IPV4_PATTERN.findall(text):
                address = IPv4Address(match)
                if any(address in network for network in DOCUMENTATION_NETWORKS):
                    continue
                if any(address in network for network in PRIVATE_NETWORKS):
                    findings.append(f"{relative_path}: {match}")

        self.assertEqual(findings, [], "\n".join(findings))


if __name__ == "__main__":
    unittest.main()

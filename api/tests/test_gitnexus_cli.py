import unittest

from api.gitnexus_cli import (
    build_gitnexus_analyze_commands,
    build_gitnexus_base_command,
)


class GitNexusCliTests(unittest.TestCase):
    def test_builds_global_gitnexus_command(self) -> None:
        self.assertEqual(build_gitnexus_base_command("gitnexus"), ["gitnexus"])

    def test_builds_npx_gitnexus_command(self) -> None:
        self.assertEqual(
            build_gitnexus_base_command("npx"),
            ["npx", "-y", "gitnexus"],
        )

    def test_analyze_command_tries_full_index_then_fallback_to_skip_embeddings(self) -> None:
        self.assertEqual(
            build_gitnexus_analyze_commands("gitnexus"),
            [
                ["gitnexus", "analyze"],
                ["gitnexus", "analyze", "--skip-embeddings"],
            ],
        )


if __name__ == "__main__":
    unittest.main()

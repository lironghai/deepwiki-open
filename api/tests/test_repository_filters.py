import tempfile
import unittest
from pathlib import Path

from api.config import DEFAULT_EXCLUDED_DIRS, DEFAULT_EXCLUDED_FILES
from api.code_analyzer import CodeAnalyzer, analyze_repository


class RepositoryFilterDefaultsTests(unittest.TestCase):
    def test_pipeline_defaults_exclude_ai_helper_directories(self) -> None:
        self.assertIn("./.claude/", DEFAULT_EXCLUDED_DIRS)
        self.assertIn("./.gitnexus/", DEFAULT_EXCLUDED_DIRS)

    def test_pipeline_defaults_exclude_ai_helper_files(self) -> None:
        self.assertIn("AGENTS.md", DEFAULT_EXCLUDED_FILES)
        self.assertIn("CLAUDE.md", DEFAULT_EXCLUDED_FILES)

    def test_code_analyzer_excludes_ai_helper_artifacts(self) -> None:
        self.assertIn(".claude", CodeAnalyzer.DEFAULT_EXCLUDED_DIRS)
        self.assertIn(".gitnexus", CodeAnalyzer.DEFAULT_EXCLUDED_DIRS)
        self.assertIn("AGENTS.md", CodeAnalyzer.DEFAULT_EXCLUDED_FILES)
        self.assertIn("CLAUDE.md", CodeAnalyzer.DEFAULT_EXCLUDED_FILES)

    def test_code_analyzer_skips_helper_files_during_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# demo\n", encoding="utf-8")
            (root / "AGENTS.md").write_text("agent helper\n", encoding="utf-8")
            (root / "CLAUDE.md").write_text("claude helper\n", encoding="utf-8")
            (root / ".claude").mkdir()
            (root / ".claude" / "SKILL.md").write_text("skill\n", encoding="utf-8")
            (root / ".gitnexus").mkdir()
            (root / ".gitnexus" / "meta.json").write_text("{}", encoding="utf-8")

            codemap = analyze_repository(str(root))
            analyzed_paths = {node.get("path") for node in codemap["nodes"]}

            self.assertIn("README.md", analyzed_paths)
            self.assertNotIn("AGENTS.md", analyzed_paths)
            self.assertNotIn("CLAUDE.md", analyzed_paths)
            self.assertFalse(any(path and ".claude" in path for path in analyzed_paths))
            self.assertFalse(any(path and ".gitnexus" in path for path in analyzed_paths))


if __name__ == "__main__":
    unittest.main()

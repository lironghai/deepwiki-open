import logging
import platform
import shutil
import subprocess
from typing import List

logger = logging.getLogger(__name__)


def resolve_gitnexus_command() -> str:
    gitnexus_cmd = "gitnexus" if shutil.which("gitnexus") else "npx"
    if platform.system() == "Windows":
        gitnexus_cmd = "gitnexus.cmd" if shutil.which("gitnexus.cmd") else "npx.cmd"
    return gitnexus_cmd


def build_gitnexus_base_command(gitnexus_cmd: str | None = None) -> List[str]:
    cmd = [gitnexus_cmd or resolve_gitnexus_command()]
    if "npx" in cmd[0]:
        cmd.extend(["-y", "gitnexus"])
    return cmd


def build_gitnexus_analyze_commands(gitnexus_cmd: str | None = None) -> List[List[str]]:
    base_cmd = build_gitnexus_base_command(gitnexus_cmd)
    return [
        [*base_cmd, "analyze"],
        [*base_cmd, "analyze", "--skip-embeddings"],
    ]


def run_gitnexus_analyze(repo_dir: str) -> bool:
    """
    Run GitNexus analyze in the given repository directory.
    Used after wiki generation so the graph is built from the final repo state.
    Returns True if any command succeeded, False otherwise.
    """
    commands = build_gitnexus_analyze_commands()
    last_error = None
    for index, cmd in enumerate(commands):
        try:
            subprocess.run(
                cmd,
                cwd=repo_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            logger.info("GitNexus analysis completed in %s using command: %s", repo_dir, " ".join(cmd))
            return True
        except subprocess.CalledProcessError as e:
            last_error = e
            stderr_text = (e.stderr or "").strip()
            has_fallback = index < len(commands) - 1
            if has_fallback:
                logger.warning(
                    "GitNexus command failed, retrying with fallback command. command=%s, error=%s",
                    " ".join(cmd),
                    stderr_text,
                )
                continue
            logger.error("GitNexus analysis failed (command: %s): %s", " ".join(cmd), stderr_text)
            break
        except FileNotFoundError:
            logger.error("GitNexus CLI not found (npm install -g gitnexus)")
            return False
    if last_error:
        logger.error("GitNexus analysis did not complete for %s", repo_dir)
    return False

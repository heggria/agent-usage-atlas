#!/usr/bin/env python3
"""
Generate a Homebrew formula for agent-usage-atlas.

Reads version from pyproject.toml, computes SHA256 of the sdist tarball,
and writes Formula/agent-usage-atlas.rb.

Usage:
  python -m build --sdist       # build the tarball first
  python scripts/generate_formula.py
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent

    # Read version from pyproject.toml
    pyproject = (repo_root / "pyproject.toml").read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', pyproject)
    if not match:
        raise SystemExit("Could not find version in pyproject.toml")
    version = match.group(1)

    # Find sdist tarball
    dist_dir = repo_root / "dist"
    tarballs = sorted(dist_dir.glob(f"agent*usage*atlas*{version}*.tar.gz"))
    if not tarballs:
        raise SystemExit(f"No sdist tarball found in {dist_dir} for version {version}")
    tarball = tarballs[-1]

    # Compute SHA256
    sha256 = hashlib.sha256(tarball.read_bytes()).hexdigest()

    # GitHub release URL
    url = f"https://github.com/heggria/agent-usage-atlas/releases/download/v{version}/{tarball.name}"

    formula = f'''\
class AgentUsageAtlas < Formula
  include Language::Python::Virtualenv

  desc "Interactive dashboard for AI coding agent usage analytics"
  homepage "https://github.com/heggria/agent-usage-atlas"
  url "{url}"
  sha256 "{sha256}"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "usage", shell_output("#{{bin}}/agent-usage-atlas --help")
  end
end
'''

    formula_dir = repo_root / "Formula"
    formula_dir.mkdir(exist_ok=True)
    out = formula_dir / "agent-usage-atlas.rb"
    out.write_text(formula)
    print(f"[ok] Formula written: {out}")
    print(f"     version: {version}")
    print(f"     sha256:  {sha256}")
    print(f"     url:     {url}")


if __name__ == "__main__":
    main()

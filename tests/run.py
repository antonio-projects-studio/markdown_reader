from __future__ import annotations
from pathlib import Path
import sys

sys.path.append(Path(__file__).parent.parent.as_posix())
from pathlib import Path
from markdown_reader import MarkdownParser


if __name__ == "__main__":
    result = MarkdownParser(Path(__file__).parent / "test.md")
    print(result.file.sections)

    result.save()

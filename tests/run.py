from __future__ import annotations
from pathlib import Path
import sys

sys.path.append(Path(__file__).parent.parent.as_posix())
from pathlib import Path
from markdown_reader import MarkdownFile
from PrettyPrint import PrettyPrintTree

pt = PrettyPrintTree(lambda x: list(x.children.values()), lambda x: x.name)  # type: ignore


# TODO do more tests
if __name__ == "__main__":

    result = MarkdownFile(Path(__file__).parent / "test.md")
    pt(result.header)  # type: ignore
    print("Test1")
    assert [section.level for section in result.header.children.values()] == [2, 2, 2]
    print("Test2")
    assert result.all_sections["Default Prompts"].level == 2
    print("Test3")
    assert list(result.all_sections["Default Prompts"].children.keys()) == [
        "Create Agent"
    ]

    print("Test4")
    assert (
        result.all_sections["Create Agent"].path
        == "test/Cache/Default Prompts/Create Agent"
    )

    # print(list(result.header.includes["default_prompts"].includes.values())[0].content)
    result.header.name = "Cache"
    # result.header.content += "\n - LOL"
    result.save()

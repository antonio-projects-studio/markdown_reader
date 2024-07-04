from __future__ import annotations

__all__ = ["MarkdownSection", "MarkdownFile"]

import frontmatter
from pathlib import Path
from frontmatter import Post
from functools import cached_property
from dataclasses import dataclass, field


@dataclass
class MarkdownSection:
    name: str
    level: int
    root: MarkdownFile
    parent: MarkdownSection | None = field(init=False)
    content: str = ""
    children: dict[str, MarkdownSection] = field(default_factory=dict)

    @cached_property
    def path(self) -> str:
        if self.parent is None:
            return self.root.name + "/" + self.name
        return self.parent.path + "/" + self.name


class MarkdownFile:
    name: str
    frontmatter: Post
    header: MarkdownSection
    all_sections: dict[str, MarkdownSection] = {}
    current_section: MarkdownSection

    def __init__(self, markdown_path: Path) -> None:
        assert markdown_path.suffix == ".md", "There must be a .md extension file"
        self.markdown_path = markdown_path
        self.name = self.markdown_path.stem
        self.refresh()


    def level_and_name(self, row: str) -> tuple[int, str]:
        row.strip()
        level = 0
        name = ""
        for sb in row:
            if sb == "#":
                level += 1
                continue
            name = row.replace("#", "").strip().lower().replace(" ", "_")
            break

        return level, name

    def process_section(self, section_row: str) -> None:

        level, name = self.level_and_name(section_row)

        new_section = MarkdownSection(name=name, level=level, root=self)

        if level == 1:
            assert getattr(self, "current_section", None) is None, "There should be only one header"

            new_section.parent = None

            self.current_section = new_section
            self.header = self.current_section
            self.all_sections[self.current_section.name] = self.current_section
            return

        if new_section.level > self.current_section.level:
            assert self.current_section.level + 1 == new_section.level, "Incorrect nesting order"
            new_section.parent = self.current_section
            self.current_section.children[new_section.name] = new_section
        else:
            parent_section = self.current_section

            while parent_section.level + 1 != new_section.level:
                parent_section = parent_section.parent
                assert parent_section is not None, "Incorrect nesting order"

            new_section.parent = parent_section
            parent_section.children[new_section.name] = new_section

        self.current_section = new_section
        self.all_sections[self.current_section.name] = self.current_section

    def refresh(self) -> None:
        self.file = open(self.markdown_path, "r", encoding="utf-8")

        self.frontmatter = frontmatter.load(self.markdown_path.as_posix())

        content = ""
        for row in self.file:
            if row.startswith("#"):
                if getattr(self, "current_section", None) is not None:
                    self.current_section.content = content.strip()

                self.process_section(row)
                content = ""
                continue

            content += row.replace("\\\n", "\n")

        self.current_section.content = content.strip()

        self.file.close()

        
    def save(self) -> None:
        section_content = ""
        
        def content(section: MarkdownSection) -> None:
            nonlocal section_content
            
            section_content += f"{'#' * section.level} {section.name.replace("_",  " ").title()}{"\n\n" + section.content.replace("\n", "\\\n").replace("\\\n-", "\n-").replace("-->\\\n", "-->\n") if section.content != "" else ""}\n\n" 
            
            for section in section.children.values():
                content(section)
                
        content(self.header)
        
        self.frontmatter.content = section_content
        
        with open(self.markdown_path, "w") as f:
            f.write(frontmatter.dumps(self.frontmatter))

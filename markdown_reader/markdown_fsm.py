from __future__ import annotations
from functools import cached_property
from pathlib import Path
from pathlib import Path
import frontmatter
from frontmatter import Post
from dataclasses import dataclass, field
from fsm import BaseFSM, State, state_decorator


@dataclass
class MarkdownFile:
    name: str
    frontmatter: Post
    content: str = field(init=False)
    sections: dict[str, SectionInfo] = field(default_factory=dict)
    all_sections: dict[str, SectionInfo] = field(default_factory=dict)


@dataclass
class SectionInfo:
    name: str
    level: int
    root: MarkdownFile
    parent: SectionInfo | None = field(init=False)
    content: str = ""
    includes: dict[str, SectionInfo] = field(default_factory=dict)

    @cached_property
    def path(self) -> str:
        if self.parent is None:
            return self.root.name + "/" + self.name
        return self.parent.path + "/" + self.name


class MarkdownFSM(BaseFSM):
    INIT_MARKDOWN = State()
    NEW_SECTION = State()

    def __init__(self, markdown_path: Path) -> None:
        self.file = open(markdown_path, "r", encoding="utf-8")
        self.markdown_path = markdown_path
        self.cnt = 0
        self.root: MarkdownFile
        self.current_section: SectionInfo
        self.result: MarkdownFile

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

    def _enter_state(self, new_state: State) -> None:
        match new_state:
            case self.INIT_MARKDOWN:
                for row in self.file:
                    if row.strip().startswith("#"):
                        self.section_row = row
                        break

                level, name = self.level_and_name(self.section_row)
                assert level == 1

                fm = frontmatter.load(self.markdown_path.as_posix())
                self.root = MarkdownFile(name=name, frontmatter=fm)
                self.result = self.root

            case self.NEW_SECTION:
                level, name = self.level_and_name(self.section_row)
                assert level != 1

                new_section = SectionInfo(name=name, level=level, root=self.root)

                if level == 2:
                    new_section.parent = None
                    self.current_section = new_section
                    self.root.sections[self.current_section.name] = self.current_section
                    self.root.all_sections[self.current_section.name] = (
                        self.current_section
                    )
                    return
                else:
                    if new_section.level > self.current_section.level:
                        assert (
                            self.current_section.level + 1 == new_section.level
                        ), "Wrong"
                        new_section.parent = self.current_section
                        self.current_section.includes[new_section.name] = new_section
                    else:
                        parent_section = self.current_section

                        while parent_section.level + 1 != new_section.level:
                            parent_section = parent_section.parent
                            assert parent_section is not None, "Wrong"

                        new_section.parent = parent_section
                        parent_section.includes[new_section.name] = new_section

                self.current_section = new_section
                self.root.all_sections[self.current_section.name] = self.current_section

    @state_decorator([INIT_MARKDOWN, NEW_SECTION])
    def new_section(self) -> None:
        content = ""

        def save_content():
            if self.current_state == self.INIT_MARKDOWN:
                self.root.content = content.strip()
            else:
                self.current_section.content = content.strip()

        for row in self.file:
            if row.startswith("#"):
                save_content()
                self.section_row = row
                self._set_state(self.NEW_SECTION)
                return

            content += row.replace("\\\n", "\n")

        save_content()
        self.file.close()
        self._set_state(self.RETURN)

    def run(self) -> MarkdownFile:
        return self._run(self.INIT_MARKDOWN)

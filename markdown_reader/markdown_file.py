from __future__ import annotations

__all__ = ["MarkdownSection", "MarkdownFile"]

import re
import pypandoc
import frontmatter
from copy import copy
from pathlib import Path
from frontmatter import Post
from typing import Literal, overload
from functools import cached_property
from dataclasses import dataclass, field


LINK_PATTERN = r"\!\[.*?\]\((.*?)\)"


@dataclass
class MarkdownSection:
    name: str
    level: int
    file: MarkdownFile
    parent: MarkdownSection | None = field(init=False)
    content: str = ""
    children: dict[str, MarkdownSection] = field(default_factory=dict)

    @property
    def images(self) -> list[str]:

        links = []
        for line in self.content.splitlines():
            match = re.search(LINK_PATTERN, line)
            if match:
                url = match.group(1)
                url = url.strip("<>")
                links.append(url)

        return links

    @property
    def text(self) -> str:

        lines = []
        for line in self.content.splitlines():
            match = re.search(LINK_PATTERN, line)
            if not match:
                lines.append(line)

        return "\n".join(lines).strip("\n").strip()

    @cached_property
    def path(self) -> str:
        if self.parent is None:
            return self.file.name + "/" + self.name
        return self.parent.path + "/" + self.name

    def add_section(
        self,
        name: str,
        content: str = "",
        replace_if_exist: bool = False,
        remove_subsections: bool = False,
    ) -> None:

        lines: list[str] = []

        if remove_subsections:
            code = False
            for line in content.splitlines():
                if line.startswith("```"):
                    code = not code
                if line.startswith("#") and not code:
                    _, sub_section_name = self.file.level_and_name(line)
                    lines.append(f"***{sub_section_name}***")
                else:
                    lines.append(line)
            content = "\n".join(lines)

        assert name not in self.file.all_sections.keys() or replace_if_exist

        if name not in self.file.all_sections.keys():
            assert name.lower() not in map(
                lambda x: x.lower(), self.file.all_sections.keys()
            )

        section = MarkdownSection(
            name=name, level=self.level + 1, file=self.file, content=content
        )

        section.parent = self

        self.children.pop(name, None)
        self.children[name] = section

        self.file.update()


class MarkdownFile:
    name: str
    frontmatter: Post
    header: MarkdownSection
    all_sections: dict[str, MarkdownSection] = {}
    current_section: MarkdownSection

    def __init__(
        self,
        markdown_path: Path,
        table_of_content_name: str = "Content",
        replace: bool = False,
    ) -> None:
        assert markdown_path.suffix == ".md", "There must be a .md extension file"
        self.markdown_path = markdown_path
        self.name = self.markdown_path.stem
        self.table_of_content = table_of_content_name
        self.replace = replace
        self.refresh_from_file()

    def delete_section(self, name: str) -> None:
        if name not in self.all_sections.keys():
            return None

        assert self.all_sections[name].parent
        parent = self.all_sections[name].parent

        if parent is not None:
            parent.children.pop(name)

        self.update()

    @overload
    def get_template(self, template: Literal["llm"]) -> None:
        pass

    @overload
    def get_template(
        self, template: Literal["llm"], *, replace_if_exist: Literal[True]
    ) -> None:
        pass

    @overload
    def get_template(self, template: Literal["llm"], *, clear: Literal[True]) -> None:
        pass

    def get_template(
        self,
        template: Literal["llm"],
        *,
        replace_if_exist: bool = False,
        clear: bool = False,
    ) -> None:

        match template:
            case "llm":
                try:
                    if clear:
                        self.header.children = {}

                    if not self.header.content:
                        self.header.content = "***Тут пишите ваш запрос***"

                    self.header.add_section(
                        "System Prompt",
                        content="Отвечай в формате Markdown",
                        replace_if_exist=replace_if_exist,
                    )
                    self.header.add_section(
                        "History", replace_if_exist=replace_if_exist
                    )
                    self.save()
                except:
                    pass

    def level_and_name(self, row: str) -> tuple[int, str]:
        row.strip()
        level = 0
        name = ""
        for sb in row:
            if sb == "#":
                level += 1
                continue
            name = row.replace("#", "").strip()
            break

        return level, name

    def process_section(self, section_row: str) -> None:

        level, name = self.level_and_name(section_row)

        new_section = MarkdownSection(name=name, level=level, file=self)

        if level == 1:
            assert (
                getattr(self, "current_section", None) is None
            ), "There should be only one header"

            new_section.parent = None

            self.current_section = new_section
            self.header = self.current_section
            self.all_sections[self.current_section.name] = self.current_section
            return

        if new_section.level > self.current_section.level:
            assert (
                self.current_section.level + 1 == new_section.level
            ), "Incorrect nesting order"
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

    def _refresh_tree(self) -> None:

        attr = "current_section"
        self.all_sections = {}

        if hasattr(self, attr):
            delattr(self, attr)

        content = ""
        code = False

        for row in self.frontmatter.content.splitlines(keepends=True):
            if row.startswith("```"):
                code = not code
            if row.startswith("#") and not code:
                if getattr(self, attr, None) is not None:
                    self.current_section.content = content.strip()

                self.process_section(row)
                content = ""
                continue

            if self.replace:
                content += row.replace("\\\n", "\n")
            else:
                content += row

        try:
            self.current_section.content = content.strip()
        except:
            self.header = MarkdownSection(name=self.name.title(), level=1, file=self)
            self.save()

    def refresh_from_file(self) -> None:
        self.file = open(self.markdown_path, "r", encoding="utf-8")

        self.frontmatter = frontmatter.load(self.markdown_path.as_posix())

        self._refresh_tree()

        self.file.close()

    def _refresh_formatter(self):

        section_content = ""

        def make_content(section: MarkdownSection) -> None:
            nonlocal section_content

            code = False
            lines: list[str] = []
            section_lines = section.content.split("\n")
            if self.replace:
                for ind, line in enumerate(section_lines):

                    if ind == len(section_lines) - 1:
                        lines.append(line)
                        continue

                    if not line:
                        lines.append(f"\n")
                        try:
                            lines[ind - 1] = lines[ind - 1].replace("\\\n", "\n")
                        except:
                            pass

                        continue

                    if line.strip().startswith("-"):
                        lines.append(f"{line}\n")
                        try:
                            lines[ind - 1] = lines[ind - 1].replace("\\\n", "\n")
                        except:
                            pass
                        continue

                    if line.startswith("```"):
                        code = not code

                    if not code:
                        lines.append(f"{line}\\\n")
                    else:
                        lines.append(f"{line}\n")

                content = "".join(lines)

                section_content += f"{'#' * section.level} {section.name}{"\n\n" + content.replace("\\\n-", "\n-").replace("-->\\\n", "-->\n") if section.content != "" else ""}\n\n"

            else:
                section_content += f"{'#' * section.level} {section.name}{("\n\n" + section.content) if section.content else ""}\n\n"

            for section in section.children.values():
                make_content(section)

        make_content(self.header)

        formatter = copy(self.frontmatter)
        formatter.content = section_content

        return formatter

    def update(self) -> None:

        self.frontmatter = self._refresh_formatter()
        self._refresh_tree()

    def save(self, add_table_of_content: bool = False) -> None:
        if add_table_of_content:
            self.delete_section(self.table_of_content)
            table_of_content = ""

            def _add_level(sub_section: MarkdownSection):
                nonlocal table_of_content

                table_of_content += f"\n{" " * (sub_section.level - 1) * 2}- [{sub_section.name}](#{sub_section.name.lower().replace(" ", "-")})"

                for child in sub_section.children.values():
                    _add_level(child)

            _add_level(self.header)

            children = self.header.children
            self.header.children = {}

            self.header.add_section(self.table_of_content, table_of_content)
            self.header.children.update(children)

        self.update()
        with open(self.markdown_path, "w") as f:
            f.write(frontmatter.dumps(self.frontmatter) + "\n")

    def export(
        self,
        output_file: Path | None = None,
        to: Literal["pdf"] = "pdf",
        extra_args: list[str] = [
            "--pdf-engine=xelatex",
            "-V",
            "header-includes=\\usepackage{textcomp}",
            "-V",
            "header-includes=\\usepackage{amsmath}",
            "-V",
            "header-includes=\\usepackage{babel}",
            "-V",
            "mainfont=Arial",
            "-V",
            "geometry:margin=2cm",
            "-V",
            "colorlinks=true",
            "-V",
            "linkcolor=blue",
            "-V",
            "urlcolor=blue",
        ],
    ):

        if output_file is None:
            output_file = self.markdown_path.parent / f"{self.markdown_path}.{to}"

        pypandoc.convert_file(
            source_file=self.markdown_path.as_posix(),
            to=to,
            outputfile=output_file.as_posix(),
            extra_args=extra_args,
        )

from pathlib import Path

import frontmatter
from markdown_reader.markdown_fsm import MarkdownFSM, SectionInfo


class MarkdownParser:

    def __init__(self, file_path: Path) -> None:
        assert file_path.suffix == ".md"
        self.file_path = file_path
        self.file = MarkdownFSM(self.file_path).run()

    def refresh(self) -> None:
        self.file = MarkdownFSM(self.file_path).run()

    def save(self) -> None:
        header = f"# {self.file.name.replace("_", " ").title()}{"\n\n" + self.file.content.replace("\n", "\\\n") if self.file.content != "" else ""}\n\n"
        section_content = ""
        
        def content(includes: dict[str, SectionInfo]) -> None:
            nonlocal section_content
            for section in includes.values():
                section_content += f"{'#' * section.level} {section.name.replace("_",  " ").title()}{"\n\n" + section.content.replace("\n", "\\\n").replace("\\\n-", "\n-").replace("-->\\\n", "-->\n") if section.content != "" else ""}\n\n" 
                content(section.includes)
                
        content(self.file.sections)
        
        self.file.frontmatter.content = header + section_content
        
        with open(self.file_path, "w") as f:
            f.write(frontmatter.dumps(self.file.frontmatter))
                

from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as f:
    more_description = f.read()


setup(
    name="markdown_reader",
    version="0.0.1",
    author="Antonio Rodrigues",
    author_email="antonio.projects.studio@gmail.com",
    description="Library to work with markdown",
    long_description=more_description,
    long_description_content_type="text/markdown",
    url="https://github.com/antonio-projects-studio/markdown_reader",
    packages=find_packages(),
    install_requires=[
        "PyYAML",
        "python-frontmatter",
        "git+https://github.com/antonio-projects-studio/fsm.git@2cdf4f9296e7af4321f56f55167c1d0115679e9a",
    ],
)

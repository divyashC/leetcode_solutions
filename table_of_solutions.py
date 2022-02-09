#!/usr/bin/env python3.8
# -*- coding: UTF-8 -*-

# 生成用于README.md文件的解法文件目录
# 通过扫描src的子文件夹，解析文件名，生成Markdown规范的文件

import abc
import datetime
import enum
import hashlib
import re
import sys
from contextlib import contextmanager
from typing import *

import git


def info(message, *args):
    print(message % args, file=sys.stdout)


def warn(message, *args):
    print(message % args, file=sys.stderr)


def error(message, *args):
    print(message % args, file=sys.stderr)


class Language(enum.Enum):
    """ 代表解法使用的编程语言 """
    Kotlin = enum.auto()
    Java = enum.auto()
    Python = enum.auto()
    MySQL = enum.auto()
    Bash = enum.auto()


class Metadata:
    """ 代表LeetCode API获取的一道题目的元信息

    :type id: int
    :type frontend_id: str
    :type title: str
    :type slug: str
    :type difficulty: int
    :type site_url: str
    """

    def __init__(self, metadata):
        self.id = metadata[0]
        """ 题号 """
        self.frontend_id = metadata[1]
        """ 界面上展示的题号 """
        self.title = metadata[2]
        """ 题目名字 """
        self.slug = metadata[3]
        """ 用于URL中的英文名 """
        self.difficulty = metadata[4]
        """ 题目难度 """
        self.site_url = f"https://leetcode-cn.com/problems/{self.slug}/"
        """ 问题的网址 """

    def __repr__(self) -> str:
        return f"Id.{self.id}: [{self.slug}] {self.title} {'★' * self.difficulty}"


class Solution:
    """ 代表一道题目的一个解法

    :type problem_no: int
    :type category: Language
    :type solution: str
    :type last_upd: datetime.datetime
    """

    def __init__(self, metadata_):
        self.problem_no = metadata_[0]
        """ 所解的题目 """
        self.category = metadata_[1]
        """ 使用语言 """
        self.solution = metadata_[2]
        """ 文件在项目中的相对路径 """
        self.last_upd = metadata_[3]
        """ 文件最后更新时间 """

    def __repr__(self) -> str:
        return f"No.{self.problem_no}: [{self.category}] {self.solution} @ {self.last_upd}"


class Problem:
    """ 代表一道LeetCode题目

    :type ordinal: int
    :type display: str
    :type solutions: list of Solution
    :type metadata: Metadata or None
    """

    def __init__(self, metadata_):
        self.ordinal = metadata_[0]
        """ 真实序号 """
        self.display = metadata_[1]
        """ 题目名字 """
        self.solutions = []
        """ 已实现的解法 """
        self.metadata = None
        """ 题目关联的元信息 """

    @property
    def site_url(self) -> Optional[str]:
        """ 题目的网址 """
        if self.metadata:
            return self.metadata.site_url
        else:
            return None

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, self.__class__):
            return False
        return self.ordinal == o.ordinal

    def __hash__(self) -> int:
        return self.ordinal

    def __repr__(self) -> str:
        return f"No.{self.ordinal}: {self.display} ({len(self.solutions)})"

    def __lt__(self, o: object) -> bool:
        if not isinstance(o, Problem):
            return False
        return self.ordinal < o.ordinal


def scan_for_problems():
    solutions: Dict[int, Problem] = {}
    # [question, problem]

    repo = git.Repo('.')

    def scan_for_solutions_internal(root_tree, what_todo):
        """
        :type root_tree: git.Tree
        :type what_todo: (git.Blob) -> None
        """
        for blob in root_tree:
            if not blob.name.startswith('.'):
                what_todo(blob)

    def scan_language_dir(tree):
        """
        :type tree: git.Blob | git.Tree
        """
        if not isinstance(tree, git.Tree):
            return

        if search := re.search(r"#(\d+) (.+)", tree.name):
            ordinal = int(search.group(1))
            problem = search.group(2)
        else:
            return

        if ordinal not in solutions:
            problem = solutions[ordinal] = Problem((ordinal, problem,))

            scan_for_solutions_internal(
                tree, lambda p: scan_solution_file(problem, p))

    def scan_solution_file(problem, blob):
        """
        :type problem: Problem
        :type blob: git.Blob | git.Tree
        """
        if not isinstance(blob, git.Blob):
            return

        commit = next(repo.iter_commits(paths=blob.path, max_count=1))
        category = resolve_language(blob.name)
        filepath = blob.path
        last_upd = commit.authored_datetime

        if category is None:
            warn("Cannot resolve language category for %s", filepath)
            return

        solution = Solution((problem.ordinal, category, filepath, last_upd))
        problem.solutions.append(solution)

    def resolve_language(file_name: str):
        return next(iter([v for k, v in {
            '.java'     : Language.Java,
            '.kt'       : Language.Kotlin,
            '.py'       : Language.Python,
            '.bash.sh'  : Language.Bash,
            '.mysql.sql': Language.MySQL,
        }.items() if file_name.endswith(k)]), None)

    @contextmanager
    def fetch_metadata_from_remote():
        import threading

        metadata: Dict[int, Metadata] = {}

        def thread_function(sink: Dict[int, Metadata]):
            import requests
            resp = requests.get("https://leetcode-cn.com/api/problems/all")
            for stat_obj in resp.json()["stat_status_pairs"]:
                stat = stat_obj["stat"]
                diff = stat_obj["difficulty"]
                sink[stat["question_id"]] = Metadata((
                    stat["question_id"],
                    stat["frontend_question_id"],
                    stat["question__title"],
                    stat["question__title_slug"],
                    diff["level"],
                ))

        future = threading.Thread(target=thread_function, args=(metadata,))
        future.start()
        yield
        future.join()

        for problem in solutions.values():
            if (data := metadata.get(problem.ordinal, None)) is not None:
                problem.metadata = data
            else:
                error("could not found metadata for %s", problem)

    with fetch_metadata_from_remote():
        scan_for_solutions_internal(repo.tree() / 'solution', scan_language_dir)
    return sorted(solutions.values())


class MarkdownTableGenerator:
    """
    Markdown Table Generator

    :type table: MarkdownTableGenerator.ElasticTable
    :type links: list of MarkdownTableGenerator.MarkdownLink
    """

    def __init__(self, problems: Iterable[Problem]):
        self.table = self.ElasticTable(
            ("No.", "Id.", "Name", "Solutions", "Last Update"))
        self.links = list()

        self.pad_column = True
        """ 在元素左右两边添加一个空格 """

        for problem in problems:

            if not problem.solutions:
                error("No solution found for %s", problem.display)
                continue

            def for_frontend(p: Problem):
                """ 生成 No. 这列的文本 """

                if p.metadata is None:
                    return "-"

                ordinal = p.metadata.frontend_id
                link = self.OrdinalLink(
                    problem=p,
                    text=ordinal,
                    label=f"p{ordinal}",
                    href=p.site_url, )
                self.links.append(link)
                return link.render_in_table()

            def for_ordinal(p: Problem):
                """ 生成 Id. 这列的文本 """

                if p.metadata is None :
                    return str(p.ordinal)
                else:
                    return str(p.metadata.id)

            def for_problem(p: Problem):
                """ 生成 Name 这列的文本 """
                return p.display

            def for_solution(s: Solution):
                """ 生成 Solutions 这列的文本 """
                link = self.SolutionLink(
                    solution=s,
                    text=s.category.name,
                    label=f"#{s.problem_no} {s.category.name.lower()}",
                    href=s.solution, )
                self.links.append(link)
                return link.render_in_table()

            # some string conversions.
            self.table.add_row((
                for_frontend(problem),
                for_ordinal(problem),
                for_problem(problem),
                "<br/>".join(map(for_solution, problem.solutions)),
                max([s.last_upd for s in problem.solutions]).strftime(
                    "%Y-%m-%d %H:%M"),
            ))

    class ElasticTable:
        """ 可自适应宽度的表格

        :type header: tuple[str]
        :type column: int
        :type widths: tuple[int]
        :type bodies: list[tuple[str]]
        """

        def __init__(self, header):
            self.header = header
            """ 表格标题 """
            self.column = len(header)
            """ 列数 """
            self.widths = tuple(len(s) for s in self.header)
            """ 各列的宽度 """
            self.bodies = list()
            """ 表格的内容 不包括标题、分隔行 """

        def add_row(self, row: Tuple[str, ...]):
            assert len(row) == self.column
            width_calculator = len
            self.widths = tuple(
                max(old, width_calculator(new)) for old, new in
                zip(self.widths, row))
            self.bodies.append(row)

        def __repr__(self) -> str:
            return f"{dict(zip(self.header, self.widths))}({len(self.bodies)})"

    class MarkdownLink(abc.ABC):
        """ Markdown Link reference ::

            [text][label]
            [label]: destination

        https://github.github.com/gfm/#link-reference-definition

        :type text: str
        :type label: str
        :type destination: str
        """

        def __init__(self, *, text, label, href):
            self.text = text
            """ 可见文字 """
            self.label = label
            """ 内部标志 """
            self.destination = href
            """ 目标地址 """

        def render_in_table(self):
            return f"[{self.text}][{self.label}]"

        def render_in_footer(self):
            import urllib.parse
            return f"[{self.label}]: {urllib.parse.quote(self.destination)}"

        def __repr__(self) -> str:
            return self.destination

        def __str__(self) -> str:
            return f"[{self.text}][{self.label}]: {self.destination}"

    class SolutionLink(MarkdownLink):
        """ Solution Link reference

        :type solution: Solution
        """

        def __init__(self, solution, *, text, label, href):
            super().__init__(text=text, label=label, href=href)
            self.solution = solution
            """ 指向的解法对象 """

    class ProblemLink(MarkdownLink):
        """ Problem Link reference

        deprecated, 不在题目名上放链接，放在序号上

        :type problem: Problem
        """

        def __init__(self, problem, *, text, label, href):
            super().__init__(text=text, label=label, href=href)
            self.problem = problem
            """ 指向的解法对象 """

        def render_in_footer(self):
            return f"[{self.label}]: {self.destination}"

    class OrdinalLink(MarkdownLink):
        """ Ordinal Link reference

        :type problem: Problem
        """

        def __init__(self, problem, *, text, label, href):
            super().__init__(text=text, label=label, href=href)
            self.problem = problem
            """ 指向的解法对象 """

        def render_in_footer(self):
            return f"[{self.label}]: {self.destination}"

    def generate(self):
        lines = []
        links = []
        pad = 2 if self.pad_column else 0

        def p_fix_join(s: Iterable[str]):
            """ Append prefix and postfix to string """
            return "|".join(('', *s, ''))

        def print_header():
            lines.append(p_fix_join(
                col.center(max(w, w + pad))
                for col, w in zip(self.table.header, self.table.widths)))

        def print_separator():
            lines.append(p_fix_join(
                "-" * max(w, w + pad)
                for w in self.table.widths))

        def print_rows():
            lines.extend(p_fix_join(
                col.ljust(w).center(max(w, w + pad))
                for col, w in zip(row, self.table.widths))
                         for row in self.table.bodies)

        def print_links():

            def link_sorter_key(link: 'MarkdownTableGenerator.MarkdownLink'):
                if isinstance(link, self.OrdinalLink):
                    return 0, link.problem.ordinal
                if isinstance(link, self.ProblemLink):
                    return 0, link.problem.ordinal
                if isinstance(link, self.SolutionLink):
                    return link.solution.category.value, \
                           link.solution.problem_no

            sorted_links = sorted(self.links, key=link_sorter_key)
            links.extend(
                link.render_in_footer()
                for link in sorted_links)

        print_header()
        print_separator()
        print_rows()
        print_links()
        return lines, links


def inplace_replace_readme_file(generator) -> bool:
    """ 按需更新README.md文件

    :type generator: ()-> tuple[list[str], list[str]]
    :return 实际更新了没
    """

    file_hash = content_hasher()
    gens_hash = content_hasher()

    start_mark = '<!-- table of solutions -->'
    end_mark = '<!-- end of table of solutions -->'
    with open('README.md', 'r') as reader:
        processing = False
        processed = False
        file_lines = []
        for line in reader:
            file_hash += line
            if start_mark in line and line.startswith('<'):
                processing = True
            elif not processing:
                file_lines.append(line)
            elif end_mark in line:
                processing = False
                processed = True
                (lines, links) = generator()

                def new_line(s):
                    return s + "\n"

                file_lines.append(new_line(start_mark))
                file_lines.extend(map(new_line, lines))
                file_lines.append("\n")
                file_lines.extend(map(new_line, links))
                file_lines.append(new_line(end_mark))
        else:
            if not processed:
                error("No %s found in README.md", start_mark)
                exit(1)
            if processing:
                error("No %s found in README.md", end_mark)
                exit(1)

            gens_hash += file_lines

    if file_hash == gens_hash:
        info("File content not changed, no writing is preformed.")
        return False

    with open('README.md', 'w') as writer:
        writer.writelines(file_lines)
        return True


# noinspection PyPep8Naming
class content_hasher:

    def __init__(self) -> None:
        self._md5 = hashlib.md5()

    def __iadd__(self, other):
        if isinstance(other, bytes):
            self._md5.update(other)
        if isinstance(other, str):
            self._md5.update(other.encode())
        elif isinstance(other, Iterable):
            for element in other:
                self.__iadd__(element)
        return self

    def __eq__(self, other):
        return isinstance(other, content_hasher) and \
               self._md5.digest() == other._md5.digest()

    def __hash__(self) -> int:
        return hash(self._md5.digest())


def main():
    """ Main entry point.
    Other file could import and call this function."""
    inplace_replace_readme_file(
        lambda: MarkdownTableGenerator(scan_for_problems()).generate())


if __name__ == '__main__':
    main()
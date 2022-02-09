#!/usr/bin/env python3.8
# -*- coding: UTF-8 -*-

# 生成用于README.md文件的解法文件目录
# 通过扫描src的子文件夹，解析文件名，生成Markdown规范的文件

"""
-------------------------------------------------------------------------
Code from: enihsyou
Link to code: https://github.com/enihsyou/LeetCode/blob/master/table_of_solutions.py
"""

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
    Kotlin = enum.auto()
    Java = enum.auto()
    Python = enum.auto()
    MySQL = enum.auto()
    Bash = enum.auto()


class Metadata:

    def __init__(self, metadata):
        self.id = metadata[0]
        self.frontend_id = metadata[1]
        self.title = metadata[2]
        self.slug = metadata[3]
        self.difficulty = metadata[4]
        self.site_url = f"https://leetcode.com/problems/{self.slug}/"

    def __repr__(self) -> str:
        return f"Id.{self.id}: [{self.slug}] {self.title} {'★' * self.difficulty}"


class Solution:

    def __init__(self, metadata_):
        self.problem_no = metadata_[0]
        self.category = metadata_[1]
        self.solution = metadata_[2]
        self.last_upd = metadata_[3]

    def __repr__(self) -> str:
        return f"No.{self.problem_no}: [{self.category}] {self.solution} @ {self.last_upd}"


class Problem:

    def __init__(self, metadata_):
        self.ordinal = metadata_[0]
        self.display = metadata_[1]
        self.solutions = []
        self.metadata = None

    @property
    def site_url(self) -> Optional[str]:
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

    repo = git.Repo('.')

    def scan_for_solutions_internal(root_tree, what_todo):

        for blob in root_tree:
            if not blob.name.startswith('.'):
                what_todo(blob)

    def scan_language_dir(tree):

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
            resp = requests.get("https://leetcode.com/api/problems/all")
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

    def __init__(self, problems: Iterable[Problem]):
        self.table = self.ElasticTable(
            ("Question No.", "Id.", "Name", "Solutions", "Last Update"))
        self.links = list()

        self.pad_column = True

        for problem in problems:

            if not problem.solutions:
                error("No solution found for %s", problem.display)
                continue

            def for_frontend(p: Problem):

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

                if p.metadata is None :
                    return str(p.ordinal)
                else:
                    return str(p.metadata.id)

            def for_problem(p: Problem):
                return p.display

            def for_solution(s: Solution):
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

        def __init__(self, header):
            self.header = header
            self.column = len(header)
            self.widths = tuple(len(s) for s in self.header)
            self.bodies = list()

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

        def __init__(self, *, text, label, href):
            self.text = text
            self.label = label
            self.destination = href

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

        def __init__(self, solution, *, text, label, href):
            super().__init__(text=text, label=label, href=href)
            self.solution = solution

    class ProblemLink(MarkdownLink):

        def __init__(self, problem, *, text, label, href):
            super().__init__(text=text, label=label, href=href)
            self.problem = problem

        def render_in_footer(self):
            return f"[{self.label}]: {self.destination}"

    class OrdinalLink(MarkdownLink):

        def __init__(self, problem, *, text, label, href):
            super().__init__(text=text, label=label, href=href)
            self.problem = problem

        def render_in_footer(self):
            return f"[{self.label}]: {self.destination}"

    def generate(self):
        lines = []
        links = []
        pad = 2 if self.pad_column else 0

        def p_fix_join(s: Iterable[str]):
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
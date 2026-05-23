from __future__ import annotations

from pathlib import Path

import duckdb


SQL_PATH = Path("queries.sql")


def title_from_comments(comments: list[str], fallback: str) -> str:
    for comment in reversed(comments):
        text = comment.removeprefix("--").strip()
        if text:
            return text.rstrip(".")
    return fallback


def iter_statements(sql: str):
    comments: list[str] = []
    statement_lines: list[str] = []

    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("--") and not statement_lines:
            comments.append(stripped)
            continue

        statement_lines.append(line)

        if stripped.endswith(";"):
            statement = "\n".join(statement_lines).strip().rstrip(";")
            yield title_from_comments(comments, "SQL statement"), statement
            comments = []
            statement_lines = []

    if statement_lines:
        statement = "\n".join(statement_lines).strip()
        yield title_from_comments(comments, "SQL statement"), statement


def is_result_query(statement: str) -> bool:
    first_word = statement.lstrip().split(maxsplit=1)[0].upper()
    return first_word in {"SELECT", "WITH", "DESCRIBE", "SUMMARIZE", "EXPLAIN"}


def print_result(con: duckdb.DuckDBPyConnection, title: str, statement: str) -> None:
    print(f"\n{title}")
    print("=" * len(title))

    result = con.execute(statement)
    if is_result_query(statement):
        print(result.df().to_string(index=False))
    else:
        print("OK")


def main() -> None:
    con = duckdb.connect()
    for title, statement in iter_statements(SQL_PATH.read_text()):
        print_result(con, title, statement)


if __name__ == "__main__":
    main()

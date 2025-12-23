from __future__ import annotations

from typing import Any, Dict, List, Optional
import json
import os
import sqlite3

from langchain_core.tools import tool


def _sqlite_path_from_env() -> Optional[str]:
    uri = (os.getenv("SQL_DB_URI") or "").strip()
    if uri:
        if uri.startswith("sqlite:///"):
            return uri[len("sqlite:///") :]
        if uri.startswith("sqlite://"):
            return uri[len("sqlite://") :]
        return uri
    path = (os.getenv("SQL_DB_PATH") or "").strip()
    return path or None


class SQLiteClient:
    def __init__(self, db_path: str):
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def list_tables(self) -> List[str]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            return [r[0] for r in cur.fetchall()]

    def get_schema(self, tables: List[str]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        with self._connect() as conn:
            for t in tables:
                t = (t or "").strip()
                if not t:
                    continue
                cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
                out[t] = [
                    {
                        "cid": int(c[0]),
                        "name": str(c[1]),
                        "type": str(c[2]),
                        "notnull": int(c[3]),
                        "dflt_value": c[4],
                        "pk": int(c[5]),
                    }
                    for c in cols
                ]
        return out

    def run_query(self, query: str) -> Dict[str, Any]:
        q = (query or "").strip()
        with self._connect() as conn:
            cur = conn.execute(q)
            rows = cur.fetchall()
            cols = [d[0] for d in (cur.description or [])]
        return {"columns": cols, "rows": rows}


def _get_db_client() -> tuple[Optional[SQLiteClient], Optional[str]]:
    path = _sqlite_path_from_env()
    if not path:
        return None, "未配置数据库。请设置环境变量 SQL_DB_PATH 或 SQL_DB_URI（sqlite）。"
    if not os.path.exists(path):
        return None, f"数据库文件不存在：{path}"
    return SQLiteClient(path), None


def _check_query(query: str) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query 为空"}
    lowered = q.lower()
    banned = ["drop ", "alter ", "truncate ", "delete ", "update ", "insert ", "attach ", "detach ", "pragma "]
    if any(b in lowered for b in banned):
        return {"ok": False, "error": "仅允许只读查询（SELECT/WITH），检测到潜在写入/危险语句"}
    if ";" in q.strip().rstrip(";"):
        return {"ok": False, "error": "不允许多语句查询"}
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return {"ok": False, "error": "仅允许 SELECT 或 WITH 开头的查询"}
    return {"ok": True}


def build_sql_tools():
    @tool("sql_db_list_tables")
    def sql_db_list_tables(input: str = "") -> str:
        """列出数据库中所有可用表名。"""
        db, err = _get_db_client()
        if err:
            return err
        return json.dumps({"tables": db.list_tables()}, ensure_ascii=False, indent=2)

    @tool("sql_db_schema")
    def sql_db_schema(tables: str) -> str:
        """获取指定表的 schema（使用逗号分隔的表名列表）。"""
        db, err = _get_db_client()
        if err:
            return err
        ts = [t.strip() for t in (tables or "").split(",") if t.strip()]
        return json.dumps({"schema": db.get_schema(ts)}, ensure_ascii=False, indent=2)

    @tool("sql_db_query_checker")
    def sql_db_query_checker(query: str) -> str:
        """检查查询是否为只读 SQL（SELECT/WITH）、是否包含多语句或危险关键词。"""
        return json.dumps(_check_query(query), ensure_ascii=False, indent=2)

    @tool("sql_db_query")
    def sql_db_query(query: str) -> str:
        """执行只读 SQL 查询并返回列名与行数据。"""
        check = _check_query(query)
        if not check.get("ok"):
            return json.dumps(check, ensure_ascii=False, indent=2)
        db, err = _get_db_client()
        if err:
            return err
        try:
            result = db.run_query(query)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False, indent=2)

    return [sql_db_list_tables, sql_db_schema, sql_db_query_checker, sql_db_query]

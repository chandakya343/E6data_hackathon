"""
SQL Server data collector for the DB Observability system.
Collects execution plans, runtime stats, schema info, and server configs.
"""

import re
import time
from typing import Dict, List, Optional, Tuple

import pyodbc


class SqlServerCollector:
    """
    Collects SQL Server diagnostics and context for a given SQL query.
    Returns a dict compatible with the existing LLM pipeline keys:
    {"query", "explain", "logs", "schema", "stats", "config", "system"}
    """

    def __init__(
        self,
        server: str,
        database: str,
        username: str,
        password: str,
        driver: str = "ODBC Driver 18 for SQL Server",
        encrypt: bool = True,
        trust_server_cert: bool = True,
        timeout_seconds: int = 30,
    ) -> None:
        self.server = server
        self.database = database
        self.username = username
        self.password = password
        self.driver = driver
        self.encrypt = encrypt
        self.trust_server_cert = trust_server_cert
        self.timeout_seconds = timeout_seconds

    def _connect(self) -> pyodbc.Connection:
        encrypt_opt = "yes" if self.encrypt else "no"
        trust_opt = "yes" if self.trust_server_cert else "no"
        conn_str = (
            f"DRIVER={{{self.driver}}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};PWD={self.password};"
            f"Encrypt={encrypt_opt};TrustServerCertificate={trust_opt};"
            f"Connection Timeout={self.timeout_seconds}"
        )
        return pyodbc.connect(conn_str, autocommit=False)

    def test_connection(self) -> bool:
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    cur.fetchone()
            return True
        except Exception:
            return False

    def collect_for_query(self, sql: str, estimated_plan_only: bool = True) -> Dict[str, str]:
        """
        Collect diagnostics for a query. If estimated_plan_only is True, we do not execute the query.
        """
        logs: List[str] = []
        plan_xml: str = ""
        runtime_log: str = ""
        result_preview: str = ""

        tables = self._extract_table_identifiers(sql)
        try:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    if estimated_plan_only:
                        logs.append("Collecting estimated plan (SET SHOWPLAN_XML ON)")
                        cur.execute("SET SHOWPLAN_XML ON;")
                        t0 = time.time()
                        cur.execute(sql)
                        # SHOWPLAN returns a single-row, single-XML-column resultset
                        row = cur.fetchone()
                        t1 = time.time()
                        if row is not None and len(row) >= 1 and row[0] is not None:
                            plan_xml = str(row[0])
                        logs.append(f"Estimated plan retrieval took {round((t1 - t0)*1000, 2)} ms")
                        cur.execute("SET SHOWPLAN_XML OFF;")
                    else:
                        logs.append("Executing query with STATISTICS XML/IO/TIME ON")
                        cur.execute("SET STATISTICS XML ON;")
                        cur.execute("SET STATISTICS IO ON;")
                        cur.execute("SET STATISTICS TIME ON;")
                        t0 = time.time()
                        try:
                            cur.execute(sql)
                            # Preview small result set if this is a SELECT
                            try:
                                sql_upper = sql.strip().upper()
                                if sql_upper.startswith("SELECT"):
                                    # Fetch preview rows
                                    preview_rows = cur.fetchmany(50)
                                    headers = [d[0] for d in cur.description] if cur.description else []
                                    preview_lines = []
                                    if headers:
                                        preview_lines.append(" | ".join(str(h) for h in headers))
                                        preview_lines.append("-" * min(120, sum(len(str(h)) for h in headers) + (3 * max(0, len(headers) - 1))))
                                    for r in preview_rows:
                                        preview_lines.append(" | ".join(str(col) for col in r))
                                    result_preview = "\n".join(preview_lines)
                                # Drain remaining result sets
                                while True:
                                    try:
                                        cur.fetchall()
                                    except Exception:
                                        pass
                                    if not cur.nextset():
                                        break
                            except Exception:
                                pass
                            t1 = time.time()
                            elapsed_ms = round((t1 - t0) * 1000, 2)
                            logs.append(f"Execution elapsed: {elapsed_ms} ms")
                        except Exception as exec_err:
                            t1 = time.time()
                            elapsed_ms = round((t1 - t0) * 1000, 2)
                            logs.append(f"Query failed after {elapsed_ms} ms: {repr(exec_err)}")

                        # Look for plan XML in subsequent resultsets (STATISTICS XML)
                        try:
                            # STATISTICS XML may return a resultset with an XML column after execution
                            # Re-run a light query to fetch the last plan if needed
                            # Fallback: leave plan_xml empty if not accessible
                            pass
                        except Exception:
                            pass

                        # Capture driver messages if available
                        try:
                            msg_list = getattr(cur, "messages", None) or []
                            for _code, message in msg_list:
                                logs.append(f"MSG: {message}")
                        except Exception:
                            pass

                        # Turn off stats
                        try:
                            cur.execute("SET STATISTICS TIME OFF;")
                            cur.execute("SET STATISTICS IO OFF;")
                            cur.execute("SET STATISTICS XML OFF;")
                        except Exception:
                            pass

                    # Schema, stats, config, system
                    schema_text = self._collect_schema_snapshot(cur, tables)
                    stats_text = self._collect_stats_snapshot(cur, tables)
                    config_text = self._collect_config_snapshot(cur)
                    system_text = self._collect_system_snapshot(cur)

        except Exception as e:
            logs.append(f"Collector error: {repr(e)}")
            schema_text = ""
            stats_text = ""
            config_text = ""
            system_text = ""

        return {
            "query": sql,
            "explain": plan_xml or "",
            "logs": "\n".join(logs).strip(),
            "schema": schema_text.strip(),
            "stats": stats_text.strip(),
            "config": config_text.strip(),
            "system": system_text.strip(),
            "result_preview": result_preview.strip(),
        }

    def _extract_table_identifiers(self, sql: str) -> List[str]:
        # Naive extraction: find tokens after FROM or JOIN
        pattern = r"\b(?:FROM|JOIN)\s+([\[\]A-Za-z0-9_.]+)"
        matches = re.findall(pattern, sql, flags=re.IGNORECASE)
        cleaned: List[str] = []
        for m in matches:
            t = m.strip().strip("[]")
            # remove alias if present: schema.table AS t
            t = t.split()[0]
            # keep only final object name part
            parts = t.split(".")
            if len(parts) >= 2:
                cleaned.append(parts[-1])
            else:
                cleaned.append(parts[0])
        # de-dup while preserving order
        seen = set()
        result = []
        for t in cleaned:
            if t not in seen:
                seen.add(t)
                result.append(t)
        return result[:8]

    def _collect_schema_snapshot(self, cur: pyodbc.Cursor, tables: List[str]) -> str:
        lines: List[str] = []
        if not tables:
            return ""
        try:
            placeholder = ",".join(["?"] * len(tables))
            # Columns
            cur.execute(
                f"""
                SELECT t.name AS table_name,
                       c.name AS column_name,
                       ty.name AS type_name,
                       c.max_length,
                       c.is_nullable
                FROM sys.tables t
                JOIN sys.columns c ON c.object_id = t.object_id
                JOIN sys.types ty ON ty.user_type_id = c.user_type_id
                WHERE t.name IN ({placeholder})
                ORDER BY t.name, c.column_id
                """,
                tables,
            )
            rows = cur.fetchall()
            if rows:
                lines.append("Columns:")
                for r in rows:
                    lines.append(
                        f"  {r.table_name}.{r.column_name} {r.type_name}({r.max_length}) NULLABLE={bool(r.is_nullable)}"
                    )
        except Exception:
            pass
        try:
            placeholder = ",".join(["?"] * len(tables))
            # Indexes
            cur.execute(
                f"""
                SELECT t.name AS table_name,
                       i.name AS index_name,
                       i.is_unique,
                       ic.key_ordinal,
                       col.name AS column_name
                FROM sys.tables t
                JOIN sys.indexes i ON i.object_id = t.object_id AND i.index_id > 0
                JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id
                JOIN sys.columns col ON col.object_id = ic.object_id AND col.column_id = ic.column_id
                WHERE t.name IN ({placeholder})
                ORDER BY t.name, i.name, ic.key_ordinal
                """,
                tables,
            )
            rows = cur.fetchall()
            if rows:
                lines.append("Indexes:")
                for r in rows:
                    lines.append(
                        f"  {r.table_name}.{r.index_name} (#{r.key_ordinal}) {r.column_name} UNIQUE={bool(r.is_unique)}"
                    )
        except Exception:
            pass
        return "\n".join(lines)

    def _collect_stats_snapshot(self, cur: pyodbc.Cursor, tables: List[str]) -> str:
        lines: List[str] = []
        if not tables:
            return ""
        try:
            placeholder = ",".join(["?"] * len(tables))
            # Row counts
            cur.execute(
                f"""
                SELECT t.name AS table_name,
                       SUM(ps.row_count) AS row_count
                FROM sys.tables t
                JOIN sys.partitions ps ON ps.object_id = t.object_id AND ps.index_id IN (0,1)
                WHERE t.name IN ({placeholder})
                GROUP BY t.name
                ORDER BY t.name
                """,
                tables,
            )
            for r in cur.fetchall():
                lines.append(f"Rows: {r.table_name} = {r.row_count}")
        except Exception:
            pass
        try:
            placeholder = ",".join(["?"] * len(tables))
            # Stats properties (last updated)
            cur.execute(
                f"""
                SELECT t.name AS table_name,
                       s.name AS stats_name,
                       p.last_updated
                FROM sys.tables t
                JOIN sys.stats s ON s.object_id = t.object_id
                CROSS APPLY sys.dm_db_stats_properties(s.object_id, s.stats_id) p
                WHERE t.name IN ({placeholder})
                ORDER BY t.name, p.last_updated DESC
                """,
                tables,
            )
            rows = cur.fetchall()
            if rows:
                lines.append("Statistics:")
                for r in rows[:50]:
                    lines.append(f"  {r.table_name}.{r.stats_name} last_updated={r.last_updated}")
        except Exception:
            pass
        return "\n".join(lines)

    def _collect_config_snapshot(self, cur: pyodbc.Cursor) -> str:
        lines: List[str] = []
        try:
            cur.execute(
                """
                SELECT name, value_in_use
                FROM sys.configurations
                WHERE name IN (
                    'cost threshold for parallelism',
                    'max degree of parallelism',
                    'optimize for ad hoc workloads'
                )
                ORDER BY name
                """
            )
            for r in cur.fetchall():
                lines.append(f"{r.name}: {r.value_in_use}")
        except Exception:
            pass
        return "\n".join(lines)

    def _collect_system_snapshot(self, cur: pyodbc.Cursor) -> str:
        lines: List[str] = []
        try:
            cur.execute(
                """
                SELECT cpu_count, scheduler_count, hyperthread_ratio
                FROM sys.dm_os_sys_info
                """
            )
            r = cur.fetchone()
            if r:
                lines.append(
                    f"CPU Count={r.cpu_count}, Schedulers={r.scheduler_count}, HT Ratio={r.hyperthread_ratio}"
                )
        except Exception:
            pass
        try:
            cur.execute(
                """
                SELECT physical_memory_kb/1024 AS memory_mb
                FROM sys.dm_os_sys_memory
                """
            )
            r = cur.fetchone()
            if r:
                lines.append(f"Memory MB={r.memory_mb}")
        except Exception:
            pass
        return "\n".join(lines)



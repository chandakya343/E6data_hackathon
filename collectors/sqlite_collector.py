"""
SQLite data collector for the DB Observability system.
Collects execution plans, runtime stats, schema info for SQLite databases.
"""

import sqlite3
import time
import re
from typing import Dict, List, Optional


class SqliteCollector:
    """
    Collects SQLite diagnostics and context for a given SQL query.
    Returns a dict compatible with the existing LLM pipeline keys:
    {"query", "explain", "logs", "schema", "stats", "config", "system"}
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn

    def test_connection(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def collect_for_query(self, sql: str, estimated_plan_only: bool = True) -> Dict[str, str]:
        """
        Collect diagnostics for a query. If estimated_plan_only is True, we get query plan without execution.
        """
        logs: List[str] = []
        plan_text: str = ""
        result_preview: str = ""
        
        tables = self._extract_table_identifiers(sql)
        
        try:
            with self._connect() as conn:
                # Get query plan
                try:
                    plan_query = f"EXPLAIN QUERY PLAN {sql}"
                    cursor = conn.execute(plan_query)
                    plan_rows = cursor.fetchall()
                    plan_lines = []
                    for row in plan_rows:
                        # SQLite EXPLAIN QUERY PLAN returns: id, parent, notused, detail
                        plan_lines.append(f"{row[0]}|{row[1]}|{row[2]}|{row[3]}")
                    plan_text = "\n".join(plan_lines)
                    logs.append("Query plan collected successfully")
                except Exception as e:
                    logs.append(f"Error getting query plan: {e}")

                # Execute query and measure time if not estimated_plan_only
                if not estimated_plan_only:
                    logs.append("Executing query with timing...")
                    start_time = time.time()
                    try:
                        cursor = conn.execute(sql)
                        # Fetch a small preview to avoid heavy memory usage
                        preview_rows = cursor.fetchmany(50)
                        end_time = time.time()
                        elapsed_ms = round((end_time - start_time) * 1000, 2)
                        logs.append(f"Execution elapsed: {elapsed_ms} ms")
                        # Build preview text with headers
                        headers = [d[0] for d in cursor.description] if cursor.description else []
                        lines = []
                        if headers:
                            lines.append(" | ".join(str(h) for h in headers))
                            lines.append("-" * min(120, sum(len(str(h)) for h in headers) + (3 * max(0, len(headers) - 1))))
                        for row in preview_rows:
                            lines.append(" | ".join(str(row[h]) if isinstance(row, sqlite3.Row) else str(col) for h, col in zip(headers, row)))
                        result_preview = "\n".join(lines)
                        logs.append(f"Rows previewed: {len(preview_rows)}")
                    except Exception as e:
                        end_time = time.time()
                        elapsed_ms = round((end_time - start_time) * 1000, 2)
                        logs.append(f"Query failed after {elapsed_ms} ms: {e}")

                # Collect schema, stats, etc.
                schema_text = self._collect_schema_snapshot(conn, tables)
                stats_text = self._collect_stats_snapshot(conn, tables)
                config_text = self._collect_config_snapshot(conn)
                system_text = self._collect_system_snapshot()

        except Exception as e:
            logs.append(f"Collector error: {repr(e)}")
            schema_text = ""
            stats_text = ""
            config_text = ""
            system_text = ""

        return {
            "query": sql,
            "explain": plan_text,
            "logs": "\n".join(logs).strip(),
            "schema": schema_text.strip(),
            "stats": stats_text.strip(),
            "config": config_text.strip(),
            "system": system_text.strip(),
            "result_preview": result_preview.strip(),
        }

    def _extract_table_identifiers(self, sql: str) -> List[str]:
        """Extract table names from SQL query."""
        pattern = r"\b(?:FROM|JOIN)\s+([\w]+)"
        matches = re.findall(pattern, sql, flags=re.IGNORECASE)
        return list(set(matches))  # Remove duplicates

    def _collect_schema_snapshot(self, conn: sqlite3.Connection, tables: List[str]) -> str:
        """Collect table schema information."""
        lines: List[str] = []
        
        for table in tables:
            try:
                # Get table schema
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                if columns:
                    lines.append(f"Table: {table}")
                    for col in columns:
                        lines.append(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'} {'PRIMARY KEY' if col[5] else ''}")
                
                # Get indexes
                cursor = conn.execute(f"PRAGMA index_list({table})")
                indexes = cursor.fetchall()
                if indexes:
                    lines.append(f"Indexes for {table}:")
                    for idx in indexes:
                        lines.append(f"  {idx[1]} {'UNIQUE' if idx[2] else ''}")
            except Exception as e:
                lines.append(f"Error getting schema for {table}: {e}")
        
        return "\n".join(lines)

    def _collect_stats_snapshot(self, conn: sqlite3.Connection, tables: List[str]) -> str:
        """Collect table statistics."""
        lines: List[str] = []
        
        for table in tables:
            try:
                # Row count
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                lines.append(f"{table}: {count:,} rows")
                
                # Check if ANALYZE has been run
                cursor = conn.execute("SELECT name FROM sqlite_stat1 WHERE tbl=?", (table,))
                stats = cursor.fetchall()
                if stats:
                    lines.append(f"  Statistics available for {table}")
                else:
                    lines.append(f"  No statistics for {table} (run ANALYZE)")
            except Exception as e:
                lines.append(f"Error getting stats for {table}: {e}")
        
        return "\n".join(lines)

    def _collect_config_snapshot(self, conn: sqlite3.Connection) -> str:
        """Collect SQLite configuration."""
        lines: List[str] = []
        
        config_pragmas = [
            "cache_size", "page_size", "journal_mode", "synchronous", 
            "temp_store", "mmap_size"
        ]
        
        for pragma in config_pragmas:
            try:
                cursor = conn.execute(f"PRAGMA {pragma}")
                value = cursor.fetchone()[0]
                lines.append(f"{pragma}: {value}")
            except Exception:
                pass
        
        return "\n".join(lines)

    def _collect_system_snapshot(self) -> str:
        """Collect system information."""
        import os
        import platform
        
        lines = [
            f"Database: SQLite",
            f"Database file: {self.db_path}",
            f"File size: {os.path.getsize(self.db_path) / 1024 / 1024:.1f} MB",
            f"Platform: {platform.system()} {platform.release()}"
        ]
        
        return "\n".join(lines)

# -*- coding: utf-8 -*-
"""
岗位智能筛选可视化管理系统 V1.0 - 数据持久层
自主设计 5 张核心数据表，配套自研 SQL 增删改查封装方法。
表结构：
  1. user            用户表（账号、加密密码、角色、创建时间）
  2. job             岗位主表
  3. label           福利标签关联表
  4. archive         数据归档表（归档月份、岗位快照、备份时间）
  5. operation_log   操作日志表
"""
import os
import sqlite3
import json
import threading
from contextlib import contextmanager
from config import SQLITE_PATH, MYSQL_CONFIG, DB_TYPE

_lock = threading.Lock()


def _connect():
    """获取数据库连接（单机 SQLite / 云端 MySQL 双架构适配）。"""
    if DB_TYPE == "mysql":
        try:
            import pymysql  # 云端部署时安装
            return pymysql.connect(
                host=MYSQL_CONFIG["host"],
                port=MYSQL_CONFIG["port"],
                user=MYSQL_CONFIG["user"],
                password=MYSQL_CONFIG["password"],
                database=MYSQL_CONFIG["database"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
        except ImportError:
            # 云端依赖未安装时回退到 SQLite（保证单机版零依赖运行）
            return sqlite3.connect(SQLITE_PATH)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row  # 返回字典风格行
    return conn


@contextmanager
def get_conn():
    """数据库连接上下文管理器，统一事务提交与资源释放。"""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def dict_row(row):
    """统一将行对象转为字典（兼容 SQLite Row 与 MySQL DictCursor）。"""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    if isinstance(row, sqlite3.Row):
        return dict(row)
    # 兜底
    return dict(row)


# ====== 建表 DDL（5 张核心表） ======
SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS user (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        username    VARCHAR(50)  NOT NULL UNIQUE,
        password    VARCHAR(64)  NOT NULL,
        role        VARCHAR(20)  NOT NULL,
        create_time VARCHAR(20)  NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS job (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        company          VARCHAR(100) NOT NULL,
        contact          VARCHAR(50),
        phone            VARCHAR(30),
        job_name         VARCHAR(100) NOT NULL,
        recruit_num      INTEGER DEFAULT 0,
        is_caring        INTEGER DEFAULT 0,
        min_salary       INTEGER DEFAULT 0,
        max_salary       INTEGER DEFAULT 0,
        salary_text      VARCHAR(50),
        education        VARCHAR(20),
        edu_level        INTEGER DEFAULT 0,
        region           VARCHAR(20),
        industry         VARCHAR(40),
        shift            VARCHAR(20),
        has_cert_priority INTEGER DEFAULT 0,
        cert_text        VARCHAR(100),
        job_duty         TEXT,
        welfare_text     TEXT,
        status           VARCHAR(20) DEFAULT 'active',
        archive_month    VARCHAR(10),
        create_time      VARCHAR(20) NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS label (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id  INTEGER NOT NULL,
        label   VARCHAR(40) NOT NULL,
        FOREIGN KEY(job_id) REFERENCES job(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS archive (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        archive_month VARCHAR(10) NOT NULL,
        snapshot      TEXT,
        backup_time   VARCHAR(20) NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS operation_log (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        operator   VARCHAR(50),
        op_type    VARCHAR(30),
        detail     TEXT,
        op_time    VARCHAR(20) NOT NULL
    );
    """,
]


def init_schema():
    """初始化数据库表结构（若不存在则创建）。"""
    with get_conn() as conn:
        cur = conn.cursor()
        for ddl in SCHEMA_SQL:
            cur.execute(ddl)
        conn.commit()


# ====== 通用 CRUD 封装（自研 SQL 查询封装方法） ======
def query_all(sql, args=()):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, args)
        return [dict_row(r) for r in cur.fetchall()]


def query_one(sql, args=()):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, args)
        return dict_row(cur.fetchone())


def execute(sql, args=()):
    """执行写操作，返回 lastrowid。"""
    with _lock, get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, args)
        conn.commit()
        return cur.lastrowid


def execute_many(sql, args_list):
    with _lock, get_conn() as conn:
        cur = conn.cursor()
        cur.executemany(sql, args_list)
        conn.commit()
        return cur.rowcount

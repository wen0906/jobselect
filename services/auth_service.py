# -*- coding: utf-8 -*-
"""
模块五：用户权限管理模块
子功能：账号登录、身份校验、功能访问拦截、操作日志记录
核心自研逻辑：角色权限匹配拦截器、用户密码 MD5 加密存储
"""
import hashlib
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
import models
from config import ROLE_ADMIN, ROLE_COMMISSIONER, ROLE_VISITOR


def md5_password(pwd):
    """用户密码 MD5 加密存储（加盐）。"""
    salt = "job-screen-2026"
    return hashlib.md5((pwd + salt).encode("utf-8")).hexdigest()


def create_user(username, password, role):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        uid = models.execute(
            "INSERT INTO user(username,password,role,create_time) VALUES(?,?,?,?)",
            (username, md5_password(password), role, now),
        )
        return uid
    except Exception:
        return None


def verify_user(username, password):
    """账号登录身份校验：返回用户字典或 None。"""
    user = models.query_one(
        "SELECT * FROM user WHERE username=? AND password=?",
        (username, md5_password(password)),
    )
    return user


def current_user():
    return session.get("user")


def login_user(user):
    session.permanent = True
    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
    }


def logout_user():
    session.pop("user", None)


# ====== 角色权限匹配拦截器（自研权限校验装饰器） ======
def require_role(*roles):
    """功能访问拦截：仅允许指定角色访问。"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            u = current_user()
            if not u:
                # 未登录：API 返回 JSON，页面重定向登录
                if request.path.startswith("/api/"):
                    return jsonify({"code": 401, "msg": "请先登录"}), 401
                return redirect(url_for("login"))
            if roles and u["role"] not in roles:
                if request.path.startswith("/api/"):
                    return jsonify({"code": 403, "msg": "权限不足"}), 403
                return ("权限不足：当前角色无法访问该功能", 403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# 各角色权限矩阵
def can_import(user):
    return user and user["role"] == ROLE_ADMIN

def can_edit(user):
    return user and user["role"] == ROLE_ADMIN

def can_export(user):
    return user and user["role"] in (ROLE_ADMIN, ROLE_COMMISSIONER)

def can_view_admin(user):
    return user and user["role"] == ROLE_ADMIN


def list_users():
    return models.query_all("SELECT id,username,role,create_time FROM user ORDER BY id")

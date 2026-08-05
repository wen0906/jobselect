# -*- coding: utf-8 -*-
"""
岗位智能筛选可视化管理系统 V1.0 - Flask 主应用
路由分组：
  /auth/*       登录登出（模块五）
  /             可视化大屏首页（模块三）
  /jobs         筛选列表页 + 筛选 API（模块二）
  /jobs/<id>    岗位详情页（模块四）
  /api/*        数据接口（筛选/统计/导出/详情生成）
  /admin/*      后台数据管理（模块一）
"""
import os
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, jsonify,
    send_file, session, g, abort,
)
import models
from config import (
    REGIONS, EDU_OPTIONS, INDUSTRY_OPTIONS, SHIFT_OPTIONS,
    ROLE_ADMIN, ROLE_COMMISSIONER, ROLE_VISITOR, UPLOAD_DIR,
    WELFARE_KEYWORDS,
)
from services import auth_service, data_service, filter_service, viz_service, output_service, excel_service
from services.data_service import log as op_log

app = Flask(__name__)
app.config.from_object("config")


# ====== 请求级钩子：注入当前用户到 g ======
@app.before_request
def _load_user():
    g.user = session.get("user")


# ====== 模板上下文注入 ======
@app.context_processor
def _ctx():
    from config import EDU_LEVEL_MAP
    def role_name(role):
        return {"admin": "管理员", "staff": "就业专员", "visitor": "访客"}.get(role, role)
    def edu_level(name):
        return EDU_LEVEL_MAP.get(name, 0)
    return {
        "current_user": g.get("user") if hasattr(g, "user") else None,
        "REGIONS": REGIONS,
        "EDU_OPTIONS": EDU_OPTIONS,
        "INDUSTRY_OPTIONS": INDUSTRY_OPTIONS,
        "SHIFT_OPTIONS": SHIFT_OPTIONS,
        "WELFARE_KEYWORDS": WELFARE_KEYWORDS,
        "role_name": role_name,
        "edu_level": edu_level,
    }


# ====================================================================
# 模块五：登录 / 登出
# ====================================================================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = auth_service.verify_user(username, password)
        if not user:
            return render_template("login.html", error="账号或密码错误")
        auth_service.login_user(user)
        op_log(user["username"], "login", "登录系统")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/auth/login_quick")
def login_quick():
    """快捷演示登录：?role=admin|staff|visitor"""
    role = request.args.get("role", "visitor")
    mapping = {
        "admin": ("admin", "admin123"),
        "staff": ("zhuanyuan", "yuan123"),
        "visitor": ("guest", "guest123"),
    }
    if role not in mapping:
        abort(404)
    u, p = mapping[role]
    user = auth_service.verify_user(u, p)
    if user:
        auth_service.login_user(user)
        op_log(user["username"], "login", "快捷演示登录")
    return redirect(url_for("dashboard"))


@app.route("/logout")
def logout():
    u = g.get("user") if hasattr(g, "user") else None
    if u:
        op_log(u["username"], "logout", "退出登录")
    auth_service.logout_user()
    return redirect(url_for("login"))


# ====================================================================
# 模块三：可视化大屏首页
# ====================================================================
@app.route("/dashboard")
@auth_service.require_role(ROLE_ADMIN, ROLE_COMMISSIONER, ROLE_VISITOR)
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/stats")
@auth_service.require_role(ROLE_ADMIN, ROLE_COMMISSIONER, ROLE_VISITOR)
def api_stats():
    """可视化图表数据接口（筛选联动刷新）。"""
    filters = _extract_filters()
    payload = viz_service.build_dashboard_payload(filters)
    return jsonify({"code": 0, "data": payload})


# ====================================================================
# 模块二：筛选列表页 + 筛选 API
# ====================================================================
@app.route("/jobs")
@auth_service.require_role(ROLE_ADMIN, ROLE_COMMISSIONER, ROLE_VISITOR)
def jobs_list():
    return render_template("list.html")


@app.route("/api/jobs")
@auth_service.require_role(ROLE_ADMIN, ROLE_COMMISSIONER, ROLE_VISITOR)
def api_jobs():
    """多条件复合筛选主接口：返回分页岗位 + 统计数据。"""
    filters = _extract_filters()
    page = request.args.get("page", 1)
    page_size = request.args.get("page_size", 12)
    rows, total, total_pages = filter_service.filter_jobs(filters, page, page_size)
    # 同时回传统计数据（筛选与可视化联动）
    stats = viz_service.build_dashboard_payload(filters)
    return jsonify({
        "code": 0,
        "data": {
            "list": rows,
            "total": total,
            "total_pages": total_pages,
            "page": int(page) if str(page).isdigit() else 1,
            "stats": stats,
        },
    })


@app.route("/api/labels")
def api_labels():
    return jsonify({"code": 0, "data": filter_service.all_labels()})


def _extract_filters():
    """从 request.args 提取筛选条件（多条件接收）。"""
    f = {}
    for k in ("region", "is_caring", "edu_level", "salary_min", "keyword",
              "industry", "shift", "has_cert", "label"):
        v = request.args.get(k)
        if v not in (None, "", "all"):
            f[k] = v
    return f


# ====================================================================
# 模块四：岗位详情页 / 详情页生成 / 导出
# ====================================================================
@app.route("/jobs/<int:job_id>")
@auth_service.require_role(ROLE_ADMIN, ROLE_COMMISSIONER, ROLE_VISITOR)
def job_detail(job_id):
    job = models.query_one("SELECT * FROM job WHERE id=?", (job_id,))
    if not job:
        abort(404)
    job["labels"] = data_service.get_job_labels(job_id)
    return render_template("detail.html", job=job)


@app.route("/api/detail_page/<int:job_id>")
@auth_service.require_role(ROLE_ADMIN, ROLE_COMMISSIONER, ROLE_VISITOR)
def api_gen_detail_page(job_id):
    """单岗位独立静态详情网页生成。"""
    path = output_service.generate_detail_page(job_id)
    if not path:
        return jsonify({"code": 1, "msg": "岗位不存在"}), 404
    op_log(g.user["username"], "gen_detail", f"生成岗位详情页 id={job_id}")
    return jsonify({"code": 0, "data": {"path": os.path.basename(path),
                                         "download_url": url_for("download_detail_page", filename=os.path.basename(path))}})


@app.route("/detail_pages/<path:filename>")
def download_detail_page(filename):
    """下载/访问生成的静态详情页 HTML（支持手机转发打开）。"""
    return send_file(os.path.join("data", "detail_pages", filename), as_attachment=False)


@app.route("/api/export_excel")
@auth_service.require_role(ROLE_ADMIN, ROLE_COMMISSIONER)
def api_export_excel():
    """标准化劳务对接 Excel 报表导出。"""
    filters = _extract_filters()
    path = output_service.export_jobs_excel(filters)
    op_log(g.user["username"], "export_excel", f"导出报表 {os.path.basename(path)}")
    return send_file(path, as_attachment=True,
                     download_name=os.path.basename(path))


@app.route("/api/export_contacts")
@auth_service.require_role(ROLE_ADMIN, ROLE_COMMISSIONER)
def api_export_contacts():
    """批量导出企业联系人、联系电话。"""
    filters = _extract_filters()
    path = output_service.export_contacts_excel(filters)
    op_log(g.user["username"], "export_contacts", f"导出联系人 {os.path.basename(path)}")
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


# ====================================================================
# 模块一：后台数据管理（管理员）
# ====================================================================
@app.route("/admin")
@auth_service.require_role(ROLE_ADMIN)
def admin():
    return render_template("admin.html")


@app.route("/api/admin/jobs")
@auth_service.require_role(ROLE_ADMIN)
def admin_jobs_list():
    """后台岗位管理列表（支持分页+搜索，含已下架）。"""
    keyword = request.args.get("keyword", "")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 15))
    where = "1=1"
    params = []
    if keyword:
        where += " AND (company LIKE ? OR job_name LIKE ? OR region LIKE ?)"
        kw = f"%{keyword}%"
        params += [kw, kw, kw]
    total_row = models.query_one(f"SELECT COUNT(*) AS c FROM job WHERE {where}", params)
    total = total_row["c"]
    offset = (page - 1) * page_size
    rows = models.query_all(
        f"SELECT * FROM job WHERE {where} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [page_size, offset],
    )
    for r in rows:
        r["labels"] = data_service.get_job_labels(r["id"])
    return jsonify({
        "code": 0,
        "data": {"list": rows, "total": total,
                 "total_pages": (total + page_size - 1) // page_size, "page": page},
    })


@app.route("/api/admin/job/<int:job_id>", methods=["GET", "POST", "DELETE"])
@auth_service.require_role(ROLE_ADMIN)
def admin_job_op(job_id):
    if request.method == "GET":
        job = models.query_one("SELECT * FROM job WHERE id=?", (job_id,))
        if not job:
            return jsonify({"code": 1, "msg": "不存在"}), 404
        job["labels"] = data_service.get_job_labels(job_id)
        return jsonify({"code": 0, "data": job})
    if request.method == "DELETE":
        data_service.delete_job(job_id, g.user["username"])
        return jsonify({"code": 0})
    # POST 编辑
    data = request.get_json(force=True) or request.form
    job = data_service.clean_job_row(dict(data))
    data_service.update_job(job_id, job, g.user["username"])
    return jsonify({"code": 0})


@app.route("/api/admin/job/add", methods=["POST"])
@auth_service.require_role(ROLE_ADMIN)
def admin_job_add():
    data = request.get_json(force=True) or request.form
    job = data_service.clean_job_row(dict(data))
    if not data_service.is_valid_job(job):
        return jsonify({"code": 1, "msg": "企业名或岗位名不能为空"}), 400
    jid = data_service.insert_job(job, g.user["username"])
    return jsonify({"code": 0, "data": {"id": jid}})


@app.route("/api/admin/job/<int:job_id>/status", methods=["POST"])
@auth_service.require_role(ROLE_ADMIN)
def admin_job_status(job_id):
    status = (request.get_json(force=True) or {}).get("status", "active")
    data_service.set_job_status(job_id, status, g.user["username"])
    return jsonify({"code": 0})


@app.route("/api/admin/excel_preview", methods=["POST"])
@auth_service.require_role(ROLE_ADMIN)
def admin_excel_preview():
    """Excel 预解析预览：分析表头结构、展示字段映射、预览数据样例。"""
    f = request.files.get("file")
    if not f:
        return jsonify({"code": 1, "msg": "未选择文件"}), 400
    if not f.filename.lower().endswith((".xlsx", ".xls")):
        return jsonify({"code": 1, "msg": "仅支持 .xlsx / .xls 格式"}), 400
    save_path = os.path.join(UPLOAD_DIR, f.filename)
    f.save(save_path)
    try:
        result = excel_service.preview_excel(save_path)
        result["data"]["file_path"] = save_path
        result["data"]["file_name"] = f.filename
        return jsonify(result)
    except Exception as e:
        return jsonify({"code": 1, "msg": f"解析失败：{str(e)}"}), 500


@app.route("/api/admin/import_excel", methods=["POST"])
@auth_service.require_role(ROLE_ADMIN)
def admin_import_excel():
    """Excel 批量导入（支持带映射的确认导入）。"""
    body = request.get_json(silent=True) or {}
    file_path = body.get("file_path")
    custom_mapping = body.get("mapping")

    if not file_path or not os.path.exists(file_path):
        # 兜底：从上传文件直接导入
        f = request.files.get("file")
        if not f:
            return jsonify({"code": 1, "msg": "未选择文件"}), 400
        file_path = os.path.join(UPLOAD_DIR, f.filename)
        f.save(file_path)

    try:
        success, skip, errors = excel_service.import_excel_with_mapping(
            file_path, g.user["username"], custom_mapping
        )
        op_log(g.user["username"], "import_excel",
               f"导入 {os.path.basename(file_path)} 成功{success} 跳过{skip}")
        return jsonify({"code": 0, "data": {
            "success": success, "skip": skip, "errors": errors[:20],
        }})
    except Exception as e:
        return jsonify({"code": 1, "msg": f"导入失败：{str(e)}"}), 500


@app.route("/api/admin/archive", methods=["POST"])
@auth_service.require_role(ROLE_ADMIN)
def admin_archive():
    month = (request.get_json(force=True) or {}).get("month")
    aid = data_service.archive_month(month, g.user["username"])
    return jsonify({"code": 0, "data": {"id": aid}})


@app.route("/api/admin/archives")
@auth_service.require_role(ROLE_ADMIN)
def admin_archives():
    return jsonify({"code": 0, "data": data_service.list_archives()})


@app.route("/api/admin/restore/<int:archive_id>", methods=["POST"])
@auth_service.require_role(ROLE_ADMIN)
def admin_restore(archive_id):
    cnt = data_service.restore_archive(archive_id, g.user["username"])
    return jsonify({"code": 0, "data": {"restored": cnt}})


@app.route("/api/admin/logs")
@auth_service.require_role(ROLE_ADMIN)
def admin_logs():
    return jsonify({"code": 0, "data": data_service.list_logs()})


@app.route("/api/admin/users")
@auth_service.require_role(ROLE_ADMIN)
def admin_users():
    return jsonify({"code": 0, "data": auth_service.list_users()})


# ====== 启动 ======
def init_app():
    """初始化数据库 + 默认账号 + 样例数据。"""
    from init_db import seed_default_data
    models.init_schema()
    seed_default_data()


if __name__ == "__main__":
    init_app()
    print("=" * 60)
    print("岗位智能筛选可视化管理系统 V1.0 启动中...")
    print("访问地址：http://127.0.0.1:5000")
    print("默认账号：admin/admin123  zhuanyuan/yuan123  guest/guest123")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)

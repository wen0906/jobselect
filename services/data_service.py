# -*- coding: utf-8 -*-
"""
模块一：数据管理模块 - 自研岗位数据智能清洗算法
子功能：
  - Excel 文本解析
  - 原始薪资 / 学历 / 福利文本分词、标签拆分函数
  - 空值与无效数据过滤
  - 两地岗位分区标识
  - 岗位 CRUD、按月归档、数据备份
核心自研逻辑：全部文本解析与标准化规则独立编写，未引用第三方成套数据处理工具。
"""
import re
import json
from datetime import datetime
from config import EDU_LEVEL_MAP, WELFARE_KEYWORDS
import models


# ============ 1. 薪资文本解析（提取上下限） ============
def parse_salary(text):
    """
    自研薪资清洗算法：从杂乱薪资文本中提取最低/最高月薪（元/月）。
    支持：5000-7000、5k-7k、5000~7000、5000元/月、面议 等。
    返回 (min_salary, max_salary, salary_text)
    """
    if not text:
        return 0, 0, "面议"
    s = str(text).strip().replace("，", ",").replace("～", "~").replace("—", "-")
    # 面议 / 不限
    if any(k in s for k in ("面议", "不限", "协商")):
        return 0, 0, "面议"

    # k/K 单位换算为元
    def _to_yuan(v):
        v = v.lower().replace("k", "000").replace(",", "")
        try:
            return int(float(v))
        except Exception:
            return 0

    # 区间：5000-7000 / 5k-7k / 5000~7000
    m = re.search(r"(\d[\d,.]*k?)\s*[-~]\s*(\d[\d,.]*k?)", s, re.I)
    if m:
        lo = _to_yuan(m.group(1))
        hi = _to_yuan(m.group(2))
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi, f"{lo}-{hi}元/月"

    # 单值：5000 / 5k / 5000元/月
    m = re.search(r"(\d[\d,.]*k?)", s, re.I)
    if m:
        val = _to_yuan(m.group(1))
        return val, val, f"{val}元/月"

    return 0, 0, str(text)


# ============ 2. 学历文本标准化（统一学历分级） ============
def parse_education(text):
    """
    自研学历清洗算法：将杂乱学历文本统一映射为标准等级 + 标准名称。
    返回 (标准名称, 等级数字 0-7)
    """
    if not text:
        return "不限", 0
    s = str(text).strip()
    # 完全匹配
    if s in EDU_LEVEL_MAP:
        return s, EDU_LEVEL_MAP[s]
    # 模糊包含匹配（如"大专及以上"）
    for key, lvl in sorted(EDU_LEVEL_MAP.items(), key=lambda x: -len(x[0])):
        if key != "不限" and key in s:
            return key, lvl
    if any(k in s for k in ("不限", "无", "学历不限")):
        return "不限", 0
    return s, 0


# ============ 3. 福利文本拆分（自动拆分福利标签） ============
def parse_welfare(text):
    """
    自研福利标签拆分算法：从原始福利文本中识别标准化标签。
    返回 标签列表，例如 ["五险一金","包吃住","双休"]
    """
    if not text:
        return []
    s = str(text)
    labels = []
    # 优先按关键词字典匹配（保证标签标准化）
    for kw in WELFARE_KEYWORDS:
        if kw in s and kw not in labels:
            labels.append(kw)
    # 兜底：按常见分隔符切分，补充未命中字典的额外文本标签
    extra_parts = re.split(r"[、,，;；/ \n\t]+", s)
    for p in extra_parts:
        p = p.strip()
        if p and p not in labels and len(p) <= 12 and not p.isdigit():
            labels.append(p)
    # 去除纯描述性长句
    labels = [l for l in labels if len(l) <= 12]
    return labels


# ============ 4. 爱心岗位标记（标记爱心帮扶岗位） ============
def detect_caring(text):
    """
    自研爱心岗位识别：含'爱心''帮扶''大龄''残疾''困难'等关键词标记为爱心岗位。
    """
    if not text:
        return 0
    s = str(text)
    keywords = ["爱心", "帮扶", "大龄", "残疾", "困难", "脱贫", "低保", "扶贫"]
    return 1 if any(k in s for k in keywords) else 0


# ============ 5. 持证优先识别 ============
def detect_cert_priority(text):
    if not text:
        return 0, ""
    s = str(text)
    if any(k in s for k in ("持证", "证书优先", "资格证", "操作证", "上岗证", "健康证")):
        m = re.search(r"(持证[^、,，;；。\n]*|.{0,15}证)", s)
        return 1, m.group(1) if m else "持证优先"
    return 0, ""


# ============ 6. 招聘人数解析 ============
def parse_recruit_num(text):
    if not text:
        return 0
    s = str(text)
    m = re.search(r"\d+", s)
    return int(m.group()) if m else 0


# ============ 7. 单行岗位标准化清洗（核心入口） ============
def clean_job_row(row):
    """
    对原始 Excel 行字典执行完整清洗，返回标准化 job 字典。
    row: dict，键为 Excel 列名（兼容多种命名）
    """
    def _get(*keys):
        """精确匹配 + 模糊子串匹配双重保险。"""
        # 第一轮：精确匹配
        for k in keys:
            if k in row and row[k] not in (None, ""):
                return row[k]
        # 第二轮：模糊子串匹配（表头名包含关键字即命中）
        for k in sorted(keys, key=len, reverse=True):
            if not k:
                continue
            for col_key, val in row.items():
                if k in str(col_key) and val not in (None, ""):
                    return val
        return ""

    company = _get("企业名称", "公司名称", "企业", "单位名称", "招聘单位", "用人单位")
    contact = _get("联系人", "招聘联系人", "联系人员", "招聘人")
    phone = _get("联系电话", "电话", "联系方式", "手机", "手机号码", "联系手机")
    job_name = _get("岗位名称", "岗位", "工种", "职位名称", "招聘岗位", "招聘职位", "岗位工种")
    recruit_num = parse_recruit_num(_get("招聘人数", "人数", "需求人数", "招聘数量"))
    salary_raw = _get("薪资", "薪资待遇", "月薪", "工资", "薪酬", "收入", "薪资水平", "月收入")
    edu_raw = _get("学历要求", "学历", "文化程度", "学历文化", "学历要求文化")
    region = _get("地区", "所属地区", "工作地区", "城市", "工作地点", "单位地址", "招聘地区")
    industry = _get("行业", "行业类型", "所属行业", "岗位行业")
    shift = _get("班次", "工作班次", "上班班次", "工作时间")
    duty = _get("岗位职责", "岗位描述", "工作内容", "职责", "招聘要求", "岗位要求", "工作要求")
    welfare_raw = _get("福利待遇", "福利", "福利说明", "福利待遇说明")
    remark = _get("备注", "说明", "其他", "备注说明")

    min_s, max_s, salary_text = parse_salary(salary_raw)
    edu_name, edu_level = parse_education(edu_raw)
    labels = parse_welfare(welfare_raw)

    # 是否爱心岗位：专属列优先识别（支持"是/否""爱心/非""1/0"等多种值）
    caring_col = _get("是否爱心岗位", "爱心岗位", "是否爱心", "爱心")
    if caring_col:
        caring_str = str(caring_col).strip()
        if caring_str in ("是", "爱心", "1", "Y", "y", "True", "true", "√", "√"):
            is_caring = 1
        elif caring_str in ("否", "非", "0", "N", "n", "False", "false", "×", "×"):
            is_caring = 0
        else:
            is_caring = detect_caring(f"{caring_str} {welfare_raw} {remark} {job_name}")
    else:
        is_caring = detect_caring(f"{welfare_raw} {remark} {job_name}")
    has_cert, cert_text = detect_cert_priority(f"{duty} {remark} {welfare_raw}")

    # 两地分区标识校验
    if region and region not in ("杭州", "惠州"):
        # 尝试从企业名称或备注识别
        for r in ("杭州", "惠州"):
            if r in str(company) or r in str(remark) or r in str(region):
                region = r
                break

    return {
        "company": str(company).strip(),
        "contact": str(contact).strip(),
        "phone": str(phone).strip(),
        "job_name": str(job_name).strip(),
        "recruit_num": recruit_num,
        "is_caring": is_caring,
        "min_salary": min_s,
        "max_salary": max_s,
        "salary_text": salary_text,
        "education": edu_name,
        "edu_level": edu_level,
        "region": region.strip() if region else "",
        "industry": str(industry).strip() or "其他",
        "shift": str(shift).strip() or "长白班",
        "has_cert_priority": has_cert,
        "cert_text": cert_text,
        "job_duty": str(duty).strip(),
        "welfare_text": str(welfare_raw).strip(),
        "labels": labels,
    }


def is_valid_job(job):
    """空值与无效数据过滤规则：企业名与岗位名至少一项非空。"""
    return bool(job.get("company")) or bool(job.get("job_name"))


# ============ 8. 数据库写入（含标签关联表） ============
def insert_job(job, operator="system"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    labels = job.pop("labels", [])
    job_id = models.execute(
        """INSERT INTO job(company,contact,phone,job_name,recruit_num,is_caring,
           min_salary,max_salary,salary_text,education,edu_level,region,industry,
           shift,has_cert_priority,cert_text,job_duty,welfare_text,status,create_time)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (job["company"], job["contact"], job["phone"], job["job_name"],
         job["recruit_num"], job["is_caring"], job["min_salary"], job["max_salary"],
         job["salary_text"], job["education"], job["edu_level"], job["region"],
         job["industry"], job["shift"], job["has_cert_priority"], job["cert_text"],
         job["job_duty"], job["welfare_text"], "active", now),
    )
    # 写入福利标签关联表
    if labels:
        models.execute_many(
            "INSERT INTO label(job_id,label) VALUES(?,?)",
            [(job_id, l) for l in labels],
        )
    log(operator, "import_job", f"新增岗位 id={job_id} {job['company']}-{job['job_name']}")
    return job_id


def get_job_labels(job_id):
    rows = models.query_all("SELECT label FROM label WHERE job_id=?", (job_id,))
    return [r["label"] for r in rows]


def update_job(job_id, job, operator="system"):
    labels = job.pop("labels", [])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    models.execute(
        """UPDATE job SET company=?,contact=?,phone=?,job_name=?,recruit_num=?,
           is_caring=?,min_salary=?,max_salary=?,salary_text=?,education=?,edu_level=?,
           region=?,industry=?,shift=?,has_cert_priority=?,cert_text=?,job_duty=?,
           welfare_text=? WHERE id=?""",
        (job["company"], job["contact"], job["phone"], job["job_name"],
         job["recruit_num"], job["is_caring"], job["min_salary"], job["max_salary"],
         job["salary_text"], job["education"], job["edu_level"], job["region"],
         job["industry"], job["shift"], job["has_cert_priority"], job["cert_text"],
         job["job_duty"], job["welfare_text"], job_id),
    )
    models.execute("DELETE FROM label WHERE job_id=?", (job_id,))
    if labels:
        models.execute_many(
            "INSERT INTO label(job_id,label) VALUES(?,?)",
            [(job_id, l) for l in labels],
        )
    log(operator, "edit_job", f"编辑岗位 id={job_id}")


def delete_job(job_id, operator="system"):
    models.execute("DELETE FROM label WHERE job_id=?", (job_id,))
    models.execute("DELETE FROM job WHERE id=?", (job_id,))
    log(operator, "delete_job", f"删除岗位 id={job_id}")


def set_job_status(job_id, status, operator="system"):
    models.execute("UPDATE job SET status=? WHERE id=?", (status, job_id))
    log(operator, "set_status", f"岗位 id={job_id} 状态->{status}")


# ============ 9. 按月归档与备份恢复 ============
def archive_month(month_str=None, operator="system"):
    """按月归档：生成岗位快照写入 archive 表。"""
    now = datetime.now()
    month_str = month_str or now.strftime("%Y-%m")
    jobs = models.query_all("SELECT * FROM job WHERE status='active'")
    snapshot = json.dumps(jobs, ensure_ascii=False)
    aid = models.execute(
        "INSERT INTO archive(archive_month,snapshot,backup_time) VALUES(?,?,?)",
        (month_str, snapshot, now.strftime("%Y-%m-%d %H:%M:%S")),
    )
    models.execute("UPDATE job SET archive_month=? WHERE status='active'", (month_str,))
    log(operator, "archive", f"归档 {month_str} 共 {len(jobs)} 条岗位 id={aid}")
    return aid


def list_archives():
    return models.query_all("SELECT id,archive_month,backup_time FROM archive ORDER BY id DESC")


def restore_archive(archive_id, operator="system"):
    """从归档快照恢复岗位数据。"""
    row = models.query_one("SELECT * FROM archive WHERE id=?", (archive_id,))
    if not row:
        return 0
    jobs = json.loads(row["snapshot"] or "[]")
    # 清空当前 active 岗位后回填
    models.execute("DELETE FROM label")
    models.execute("DELETE FROM job WHERE status='active'")
    cnt = 0
    for j in jobs:
        labels = j.pop("labels", []) if "labels" in j else []
        j.pop("id", None)
        j.pop("archive_month", None)
        cols = list(j.keys())
        placeholders = ",".join(["?"] * len(cols))
        jid = models.execute(
            f"INSERT INTO job({','.join(cols)}) VALUES({placeholders})",
            [j[c] for c in cols],
        )
        if labels:
            models.execute_many(
                "INSERT INTO label(job_id,label) VALUES(?,?)",
                [(jid, l) for l in labels],
            )
        cnt += 1
    log(operator, "restore", f"恢复归档 id={archive_id} 共 {cnt} 条")
    return cnt


# ============ 10. 操作日志 ============
def log(operator, op_type, detail=""):
    models.execute(
        "INSERT INTO operation_log(operator,op_type,detail,op_time) VALUES(?,?,?,?)",
        (operator or "system", op_type, detail,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )


def list_logs(limit=200):
    return models.query_all(
        "SELECT * FROM operation_log ORDER BY id DESC LIMIT ?", (limit,)
    )

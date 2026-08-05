# -*- coding: utf-8 -*-
"""
模块二：智能筛选引擎模块（软件核心创新点）
子功能：多条件接收、条件解析、动态 SQL 组装、分页查询、统计数据回传
核心自研逻辑：多条件 AND 联合查询算法、爱心岗位专属过滤分支、
             薪资区间数值比对、筛选后全量数据实时聚合函数。
"""
import models
from config import PAGE_SIZE


def _build_where(filters):
    """
    多维度条件组装 SQL 动态查询语句（自研 AND 联合查询算法）。
    filters: dict，键为筛选维度
    返回 (where_sql, params, having_sql, having_params)
    """
    where = ["j.status = 'active'"]
    params = []

    # 地区
    region = filters.get("region")
    if region:
        where.append("j.region = ?")
        params.append(region)

    # 爱心岗位专属过滤分支
    if filters.get("is_caring") in ("1", 1, True):
        where.append("j.is_caring = 1")

    # 学历（按等级筛选：要求等级 <= 岗位等级视为可胜任）
    edu_level = filters.get("edu_level")
    if edu_level not in (None, "", "0", 0):
        try:
            where.append("j.edu_level <= ?")
            params.append(int(edu_level))
        except (ValueError, TypeError):
            pass

    # 薪资区间数值比对
    salary_min = filters.get("salary_min")
    if salary_min not in (None, ""):
        try:
            # 岗位最高薪资 >= 用户期望最低薪资
            where.append("j.max_salary >= ?")
            params.append(int(salary_min))
        except (ValueError, TypeError):
            pass

    # 岗位工种 / 岗位名称模糊
    keyword = filters.get("keyword")
    if keyword:
        where.append("(j.job_name LIKE ? OR j.company LIKE ?)")
        kw = f"%{keyword}%"
        params.extend([kw, kw])

    # 行业类型
    industry = filters.get("industry")
    if industry:
        where.append("j.industry = ?")
        params.append(industry)

    # 班次
    shift = filters.get("shift")
    if shift:
        where.append("j.shift = ?")
        params.append(shift)

    # 持证优先岗位
    if filters.get("has_cert") in ("1", 1, True):
        where.append("j.has_cert_priority = 1")

    # 福利标签（子查询关联 label 表）
    label = filters.get("label")
    if label:
        where.append(
            "EXISTS(SELECT 1 FROM label l WHERE l.job_id=j.id AND l.label=?)"
        )
        params.append(label)

    where_sql = " AND ".join(where)
    return where_sql, params


def filter_jobs(filters, page=1, page_size=PAGE_SIZE):
    """
    复合筛选主入口：返回 (岗位列表, 总数, 总页数)。
    自动拼接福利标签到每条岗位。
    """
    where_sql, params = _build_where(filters)

    # 总数
    count_sql = f"SELECT COUNT(*) AS c FROM job j WHERE {where_sql}"
    total_row = models.query_one(count_sql, params)
    total = total_row["c"] if total_row else 0

    # 分页
    try:
        page = max(1, int(page))
        page_size = max(1, int(page_size))
    except (ValueError, TypeError):
        page, page_size = 1, PAGE_SIZE
    offset = (page - 1) * page_size

    list_sql = (
        f"SELECT j.* FROM job j WHERE {where_sql} "
        f"ORDER BY j.is_caring DESC, j.max_salary DESC, j.id DESC "
        f"LIMIT ? OFFSET ?"
    )
    rows = models.query_all(list_sql, params + [page_size, offset])

    # 拼接福利标签
    for r in rows:
        r["labels"] = models.query_all(
            "SELECT label FROM label WHERE job_id=?", (r["id"],)
        )
        r["labels"] = [x["label"] for x in r["labels"]]

    total_pages = (total + page_size - 1) // page_size
    return rows, total, total_pages


def aggregate_stats(filters):
    """
    筛选后全量数据实时聚合函数（驱动可视化联动刷新）。
    返回指标卡片 + 行业柱状图 + 学历饼图 + 薪资饼图 数据。
    """
    where_sql, params = _build_where(filters)
    base = f"FROM job j WHERE {where_sql}"

    # ---- 指标卡片 ----
    total_row = models.query_one(f"SELECT COUNT(*) AS c {base}", params)
    total = total_row["c"] if total_row else 0

    caring_row = models.query_one(
        f"SELECT COUNT(*) AS c {base} AND j.is_caring=1", params
    )
    caring = caring_row["c"] if caring_row else 0

    high_salary_row = models.query_one(
        f"SELECT COUNT(*) AS c {base} AND j.max_salary>=8000", params
    )
    high_salary = high_salary_row["c"] if high_salary_row else 0

    # 包食宿：通过 label 关联表统计
    food_row = models.query_one(
        f"""SELECT COUNT(*) AS c {base}
            AND EXISTS(SELECT 1 FROM label l WHERE l.job_id=j.id
                       AND (l.label LIKE '%包吃%' OR l.label LIKE '%包住%'
                            OR l.label LIKE '%包食宿%'))""",
        params,
    )
    food_shelter = food_row["c"] if food_row else 0

    # ---- 行业柱状图 ----
    industry_rows = models.query_all(
        f"""SELECT j.industry AS name, COUNT(*) AS value {base}
            GROUP BY j.industry ORDER BY value DESC""",
        params,
    )

    # ---- 学历饼图 ----
    edu_rows = models.query_all(
        f"""SELECT j.education AS name, COUNT(*) AS value {base}
            GROUP BY j.education ORDER BY value DESC""",
        params,
    )

    # ---- 薪资区间饼图 ----
    salary_rows = models.query_all(
        f"""SELECT
              CASE
                WHEN j.max_salary=0 THEN '面议'
                WHEN j.max_salary<4000 THEN '4000以下'
                WHEN j.max_salary<6000 THEN '4000-6000'
                WHEN j.max_salary<8000 THEN '6000-8000'
                WHEN j.max_salary<10000 THEN '8000-10000'
                ELSE '10000以上'
              END AS name,
              COUNT(*) AS value
            {base}
            GROUP BY name ORDER BY name""",
        params,
    )

    return {
        "cards": {
            "total": total,
            "caring": caring,
            "high_salary": high_salary,
            "food_shelter": food_shelter,
        },
        "industry_bar": [{"name": r["name"] or "其他", "value": r["value"]} for r in industry_rows],
        "edu_pie": [{"name": r["name"] or "不限", "value": r["value"]} for r in edu_rows],
        "salary_pie": [{"name": r["name"], "value": r["value"]} for r in salary_rows],
    }


def all_labels():
    """获取全部已用福利标签（用于筛选下拉）。"""
    return models.query_all(
        "SELECT DISTINCT label AS name, COUNT(*) AS cnt FROM label GROUP BY label ORDER BY cnt DESC"
    )

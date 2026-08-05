# -*- coding: utf-8 -*-
"""
岗位智能筛选可视化管理系统 V1.0 - 全局配置
软件全称：岗位智能筛选可视化管理系统 V1.0
架构：三层架构（数据持久层 / 业务逻辑层 / 前端展示层）
部署：本地单机 SQLite（默认）/ 云端 MySQL（可切换）
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ===== 数据库配置（本地单机版采用 SQLite，云端版可切换 MySQL）=====
# 单机版：SQLite 嵌入式本地数据库
DB_TYPE = os.environ.get("JOB_DB_TYPE", "sqlite")  # sqlite | mysql
SQLITE_PATH = os.path.join(BASE_DIR, "data", "jobscreen.db")

# 云端版 MySQL 配置（仅当 DB_TYPE=mysql 时启用）
MYSQL_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "jobscreen",
}

# ===== 会话与安全 =====
SECRET_KEY = "job-screen-viz-2026-杭州惠州-劳务协作"
SESSION_COOKIE_HTTPONLY = True
PERMANENT_SESSION_LIFETIME = 3600 * 8  # 8 小时

# ===== 业务常量 =====
# 地区（两地分区存储）
REGIONS = ["杭州", "惠州"]

# 学历分级映射（自研清洗规则：统一学历分级）
EDU_LEVEL_MAP = {
    "不限": 0,
    "无": 0,
    "无学历要求": 0,
    "小学": 1,
    "初中": 2,
    "高中": 3,
    "中专": 3,
    "中技": 3,
    "职高": 3,
    "大专": 4,
    "本科": 5,
    "硕士": 6,
    "博士": 7,
}
# 学历筛选可选项（按等级由低到高）
EDU_OPTIONS = ["不限", "小学", "初中", "高中", "大专", "本科", "硕士", "博士"]

# 标准化福利标签字典（自研清洗规则：自动拆分福利标签）
WELFARE_KEYWORDS = [
    "五险一金", "五险", "公积金", "包吃", "包住", "包食宿", "双休",
    "高温补贴", "加班费", "年终奖", "带薪年假", "节日福利", "免费培训",
    "交通补贴", "餐补", "住房补贴", "健康体检", "弹性工作", "全勤奖",
]

# 行业类型枚举
INDUSTRY_OPTIONS = [
    "制造业", "电子科技", "纺织服装", "食品加工", "建筑建材",
    "物流仓储", "家政服务", "餐饮服务", "商贸零售", "机械装备",
    "汽车制造", "新能源", "物业管理", "农林牧渔", "其他",
]

# 班次
SHIFT_OPTIONS = ["长白班", "两班倒", "三班倒", "弹性班次"]

# 角色
ROLE_ADMIN = "admin"          # 管理员：全部功能
ROLE_COMMISSIONER = "staff"   # 就业专员：筛选/可视化/导出
ROLE_VISITOR = "visitor"      # 访客/求职者：仅浏览

# 分页
PAGE_SIZE = 12

# 上传目录
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
# 导出目录
EXPORT_DIR = os.path.join(BASE_DIR, "data", "exports")
# 单岗位静态详情页输出目录
DETAIL_PAGE_DIR = os.path.join(BASE_DIR, "data", "detail_pages")

for _d in (os.path.join(BASE_DIR, "data"), UPLOAD_DIR, EXPORT_DIR, DETAIL_PAGE_DIR):
    os.makedirs(_d, exist_ok=True)

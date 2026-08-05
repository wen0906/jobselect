# -*- coding: utf-8 -*-
"""
模块三：可视化统计模块
子功能：指标计算、图表数据集组装、筛选联动刷新、图表渲染接口
核心自研逻辑：行业分组统计、学历分层计数、薪资区间归类算法、
             条件变更自动重绘逻辑。

本模块对外暴露组装 ECharts option 的纯函数（前端二次封装数据转换逻辑），
实际渲染由前端 ECharts 完成；服务端负责聚合数据 + option 模板生成。
"""
from services import filter_service


def build_dashboard_payload(filters):
    """
    组装可视化大屏所需全部数据：
      - 指标卡片
      - 行业柱状图 option
      - 学历饼图 option
      - 薪资饼图 option
    筛选条件变更后调用本函数即可实现联动刷新。
    """
    stats = filter_service.aggregate_stats(filters)
    cards = stats["cards"]

    # 柱状图：各行业岗位数量对比
    industry_bar_option = {
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": [d["name"] for d in stats["industry_bar"]],
            "axisLabel": {"rotate": 30, "color": "#4a5568"},
        },
        "yAxis": {"type": "value", "axisLabel": {"color": "#4a5568"}},
        "series": [{
            "name": "岗位数量",
            "type": "bar",
            "data": [d["value"] for d in stats["industry_bar"]],
            "itemStyle": {
                "color": "#3b82f6",
                "borderRadius": [6, 6, 0, 0],
            },
            "barMaxWidth": 40,
        }],
    }

    # 饼图：学历分布占比
    edu_pie_option = {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"bottom": 0, "textStyle": {"color": "#4a5568"}},
        "series": [{
            "name": "学历分布",
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["50%", "45%"],
            "avoidLabelOverlap": True,
            "itemStyle": {"borderColor": "#fff", "borderWidth": 2},
            "label": {"show": True, "formatter": "{b}\n{d}%"},
            "data": stats["edu_pie"],
        }],
        "color": ["#3b82f6", "#10b981", "#f59e0b", "#ef4444",
                  "#8b5cf6", "#ec4899", "#14b8a6", "#6366f1"],
    }

    # 饼图：薪资区间分布占比
    salary_pie_option = {
        "tooltip": {"trigger": "item", "formatter": "{b}: {c} ({d}%)"},
        "legend": {"bottom": 0, "textStyle": {"color": "#4a5568"}},
        "series": [{
            "name": "薪资区间",
            "type": "pie",
            "radius": "65%",
            "center": ["50%", "45%"],
            "label": {"formatter": "{b}\n{c}个" },
            "data": stats["salary_pie"],
        }],
        "color": ["#94a3b8", "#fbbf24", "#60a5fa", "#34d399",
                  "#f87171", "#a78bfa"],
    }

    return {
        "cards": cards,
        "industry_bar_option": industry_bar_option,
        "edu_pie_option": edu_pie_option,
        "salary_pie_option": salary_pie_option,
    }

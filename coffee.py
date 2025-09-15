import streamlit as st
import pandas as pd
from streamlit_echarts import st_echarts
from pyecharts.charts import Map
from pyecharts import options as opts
from pyecharts.globals import ThemeType
from streamlit.components.v1 import html
import json

# ------------------------
# 1️⃣ 页面配置
# ------------------------
st.set_page_config(page_title="Global Coffee Health ECharts", layout="wide")
st.title("☕ Global Coffee Health 数据分析可视化")
st.markdown("分析咖啡消费对睡眠、压力和健康的影响")

# ------------------------
# 2️⃣ 数据加载
# ------------------------
@st.cache_data(ttl=600)
def load_data():
    df = pd.read_csv("synthetic_coffee_health_10000.csv")
    df = df[df['Gender'].isin(['Male','Female'])].copy()
    return df

data = load_data()

# ------------------------
# 3️⃣ 侧边栏筛选
# ------------------------
st.sidebar.header("筛选条件")
countries = st.sidebar.multiselect("选择国家", options=data['Country'].unique(), default=data['Country'].unique())
genders = st.sidebar.multiselect("选择性别", options=data['Gender'].unique(), default=data['Gender'].unique())
age_range = st.sidebar.slider("选择年龄范围", int(data['Age'].min()), int(data['Age'].max()), (20, 60))

filtered_data = data[(data['Country'].isin(countries)) &
                     (data['Gender'].isin(genders)) &
                     (data['Age'] >= age_range[0]) &
                     (data['Age'] <= age_range[1])]

if filtered_data.empty:
    st.warning("⚠️ 当前筛选条件下没有数据，请调整条件。")
    st.stop()

# 添加压力指数映射
stress_mapping = {'Low':1,'Medium':2,'High':3}
filtered_data['Stress_Index'] = filtered_data['Stress_Level'].map(stress_mapping)

# ------------------------
# 4️⃣ 标签页
# ------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 KPI 概览", "🔍 健康分析", "🌍 全球地图", "📦 分类分析", "📈 深度探索"])

# ------------------------
# KPI 概览
# ------------------------
with tab1:
    st.subheader("关键指标 (KPI)")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("平均咖啡摄入量 (cups/day)", round(filtered_data['Coffee_Intake'].mean(),2))
    col2.metric("平均睡眠时长 (hours/day)", round(filtered_data['Sleep_Hours'].mean(),2))
    col3.metric("平均压力指数", round(filtered_data['Stress_Index'].mean(),2))
    col4.metric("平均 BMI", round(filtered_data['BMI'].mean(),2))

# ------------------------
# 健康分析（散点图）
# ------------------------
with tab2:
    st.subheader("咖啡摄入 vs 健康指标")
    health_metric = st.selectbox("选择健康指标", ['Sleep_Hours','Stress_Index','Heart_Rate','BMI'])

    scatter_data = [
        {
            "value": [row['Coffee_Intake'], row[health_metric]],
            "name": f"{row['Country']} / {row['Occupation']}",
            "symbolSize": max(5, row['Age']/5),
            "itemStyle": {"color": "#FF5722" if row['Gender']=="Male" else "#2196F3"}
        }
        for _, row in filtered_data.iterrows()
    ]

    option_scatter = {
        "tooltip": {"formatter": "{b}<br/>咖啡: {c[0]}<br/>指标: {c[1]}"},
        "xAxis": {"name":"每日咖啡摄入量 (cups/day)"},
        "yAxis": {"name":health_metric},
        "series":[{"type":"scatter","data":scatter_data}]
    }

    st_echarts(options=option_scatter, height="600px")

# ------------------------
# 全球地图（pyecharts版）
# ------------------------
with tab3:
    st.subheader("全球平均咖啡消费热力图（pyecharts版）")

    country_avg = filtered_data.groupby('Country')['Coffee_Intake'].mean().reset_index()

    # 国家名映射
    country_name_map = {
        "USA": "United States",
        "UK": "United Kingdom",
        "South Korea": "Korea, Rep."
    }

    data_list = [
        (country_name_map.get(row['Country'], row['Country']),
         round(row['Coffee_Intake'], 2))
        for _, row in country_avg.iterrows()
    ]

    m = Map(init_opts=opts.InitOpts(theme=ThemeType.LIGHT, width="1000px", height="600px"))

    with open("world.json", "r", encoding="utf-8") as f:
        world_json = json.load(f)

    m.add_js_funcs(f"echarts.registerMap('worldMap', {json.dumps(world_json)});")

    m.add(
        "平均咖啡摄入量",
        data_list,
        maptype="worldMap",
        is_map_symbol_show=False,
        label_opts=opts.LabelOpts(is_show=False)  # 不显示国家名称
    )

    min_val = float(country_avg['Coffee_Intake'].min() or 0)
    max_val = float(country_avg['Coffee_Intake'].max() or 1)

    m.set_global_opts(
       visualmap_opts=opts.VisualMapOpts(
        min_=min_val,
        max_=max_val,
        is_calculable=True,
        range_text=["Low", "High"],
        in_range={"color": ["#FFE0B2", "#FF5722"]}  # 渐变颜色
    ),
    tooltip_opts=opts.TooltipOpts(trigger="item")
)


    html(m.render_embed(), height=600)

# ------------------------
# 分类分析
# ------------------------
with tab4:
    st.subheader("职业与咖啡摄入对比")
    occupation_avg = filtered_data.groupby(['Occupation','Gender'])['Coffee_Intake'].mean().reset_index()
    data_bar = [{"name":f"{row['Occupation']} ({row['Gender']})","value":round(row['Coffee_Intake'],2)}
                for _, row in occupation_avg.iterrows()]
    option_bar = {
        "tooltip":{"trigger":"axis"},
        "xAxis":{"type":"category","data":[d["name"] for d in data_bar]},
        "yAxis":{"type":"value","name":"平均每日咖啡摄入量 (cups/day)"},
        "series":[{"type":"bar","data":[d["value"] for d in data_bar]}]
    }
    st_echarts(options=option_bar, height="500px")

    st.subheader("咖啡与生活习惯分析")
    habit = st.selectbox("选择生活习惯指标", ['Smoking','Alcohol_Consumption','Physical_Activity_Hours'])
    if habit=='Physical_Activity_Hours':
        filtered_data['Activity_Bins'] = pd.cut(filtered_data['Physical_Activity_Hours'], bins=[0,2,4,6,24], labels=["0-2h","2-4h","4-6h","6h+"])
        x_var='Activity_Bins'
    else:
        x_var=habit

    habits = filtered_data.groupby([x_var,'Gender'])['Coffee_Intake'].apply(list).reset_index()
    option_box = {
        "tooltip":{"trigger":"item"},
        "xAxis":{"type":"category","data":[f"{row[x_var]} ({row['Gender']})" for _,row in habits.iterrows()]},
        "yAxis":{"type":"value","name":"每日咖啡摄入量 (cups/day)"},
        "series":[{"type":"boxplot","data":[row['Coffee_Intake'] for _,row in habits.iterrows()]}]
    }
    st_echarts(options=option_box, height="500px")

# ------------------------
# 深度探索
# ------------------------
with tab5:
    st.subheader("不同年龄段咖啡摄入与睡眠趋势")
    age_trend = filtered_data.groupby('Age')[['Coffee_Intake','Sleep_Hours']].mean().reset_index()
    option_line = {
        "tooltip":{"trigger":"axis"},
        "legend":{"data":["Coffee_Intake","Sleep_Hours"]},
        "xAxis":{"type":"category","data":age_trend['Age'].tolist()},
        "yAxis":{"type":"value"},
        "series":[
            {"name":"Coffee_Intake","type":"line","data":age_trend['Coffee_Intake'].round(2).tolist()},
            {"name":"Sleep_Hours","type":"line","data":age_trend['Sleep_Hours'].round(2).tolist()}
        ]
    }
    st_echarts(options=option_line, height="500px")

import streamlit as st
import os
from supabase import create_client, Client
import pandas as pd
import itertools
from dotenv import load_dotenv

# --- 0. 載入環境變數 ---
load_dotenv()

# --- 1. Supabase 初始化 ---
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ 錯誤：環境變數缺失。請在 Zeabur 的 Variables 設定 SUPABASE_URL 與 SUPABASE_KEY")
    st.stop()

@st.cache_resource
def init_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase_client()

# --- 2. 品牌視覺與 CSS (強制修正文字顏色) ---
def apply_branding():
    st.markdown("""
        <style>
        /* 強制全局背景與文字顏色，解決 502/Zeabur 顯示問題 */
        .stApp { background-color: #ffffff; }
        
        /* 強制所有標題與正文顏色為深灰色，避免「文字消失」 */
        h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {
            color: #333333 !important;
        }
        
        /* 品牌黃色按鈕 */
        .stButton>button { 
            background-color: #f7d302 !important; 
            border-radius: 20px !important; 
            border: none !important; 
            color: #333 !important; 
            font-weight: bold !important;
            width: 100%;
        }
        .stButton>button:hover { background-color: #e5c302 !important; }
        
        /* 卡片容器樣式 */
        [data-testid="stExpander"], .stContainer {
            background-color: #f9f9f9 !important;
            border-radius: 12px !important;
            padding: 10px !important;
        }
        
        /* 修正 Metric 顯示 */
        [data-testid="stMetricValue"] {
            color: #d32f2f !important;
            font-weight: bold !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 3. 飲品資料初始化 ---
initial_drinks_data = [
    {"name": "柚香覺醒 307", "description": "葡萄柚與307烏龍的極致平衡", "price": 65, "category": "招牌系列", "image_url": "https://picsum.photos/400/300?random=10"},
    {"name": "八曜和茶", "description": "十多種穀物焙煎，無咖啡因", "price": 45, "category": "經典系列", "image_url": "https://picsum.photos/400/300?random=11"},
    {"name": "究極 308", "description": "輕焙火茶香，回甘生津", "price": 55, "category": "經典系列", "image_url": "https://picsum.photos/400/300?random=12"},
    {"name": "22K 檸檬茶", "description": "新鮮檸檬，微酸清甜", "price": 50, "category": "經典系列", "image_url": "https://picsum.photos/400/300?random=13"},
    {"name": "炙燒濃乳 307", "description": "重烘焙香氣與厚實鮮乳", "price": 75, "category": "厚奶系列", "image_url": "https://picsum.photos/400/300?random=14"}
]

def initialize_supabase_data():
    try:
        response = supabase.from_('drinks').select('id').limit(1).execute()
        if not response.data:
            for drink in initial_drinks_data:
                supabase.from_('drinks').insert(drink).execute()
            st.rerun()
    except Exception as e:
        st.error(f"資料初始化失敗: {e}")

# --- 4. 狀態管理 ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page' not in st.session_state: st.session_state.page = 'menu'

# --- 5. UI 介面實作 ---
st.set_page_config(page_title="八曜和茶點餐", page_icon="🥤", layout="centered")
apply_branding()
initialize_supabase_data()

# 側邊欄導航
with st.sidebar:
    st.title("🥤 八曜和茶")
    if st.button("🥤 開始點餐"): st.session_state.page = 'menu'
    if st.button("🛒 購物車"): st.session_state.page = 'cart'
    st.divider()
    st.caption("版本：v1.2 (修正文字顯示問題)")

# 頁面路由
if st.session_state.page == 'menu':
    st.header("🥤 點餐菜單")
    res = supabase.from_('drinks').select('*').order('category').execute()
    drinks = res.data if res.data else []
    
    if drinks:
        categories = sorted(list(set([d['category'] for d in drinks])))
        for cat in categories:
            with st.expander(f"📦 {cat}", expanded=True):
                cat_drinks = [d for d in drinks if d['category'] == cat]
                cols = st.columns(2)
                for idx, drink in enumerate(cat_drinks):
                    with cols[idx % 2]:
                        with st.container(border=True):
                            # 已修正：使用 use_container_width 避免警告
                            st.image(drink['image_url'], use_container_width=True)
                            st.subheader(drink['name'])
                            st.write(f"**NT$ {drink['price']}**")
                            st.caption(drink['description'])
                            
                            with st.popover("選擇口味", use_container_width=True):
                                s = st.select_slider("甜度", options=["無糖", "微糖", "半糖", "正常"], key=f"s_{drink['id']}")
                                i = st.select_slider("冰塊", options=["去冰", "微冰", "少冰", "正常"], key=f"i_{drink['id']}")
                                q = st.number_input("數量", 1, 10, 1, key=f"q_{drink['id']}")
                                if st.button("加入購物車", key=f"btn_{drink['id']}"):
                                    st.session_state.cart.append({
                                        'id': drink['id'], 'name': drink['name'], 
                                        'price': drink['price'], 'sugar': s, 'ice': i, 'qty': q
                                    })
                                    st.toast(f"✅ 已加入: {drink['name']}")

elif st.session_state.page == 'cart':
    st.header("🛒 您的購物車")
    if not st.session_state.cart:
        st.info("目前購物車是空的")
    else:
        total = 0
        for idx, item in enumerate(st.session_state.cart):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                col1.write(f"**{item['name']}** x {item['qty']}")
                col1.write(f"客製化：{item['sugar']} / {item['ice']}")
                col2.write(f"NT$ {item['price'] * item['qty']}")
                if col2.button("🗑️", key=f"del_{idx}"):
                    st.session_state.cart.pop(idx)
                    st.rerun()
                total += item['price'] * item['qty']
        
        st.divider()
        st.metric("總計金額", f"NT$ {total}")
        name = st.text_input("訂購人姓名")
        if st.button("✅ 確認結帳", type="primary"):
            if name and st.session_state.cart:
                st.success(f"感謝 {name}，訂單已送出！")
                st.balloons()
                st.session_state.cart = []
            else:
                st.error("請輸入姓名並確認購物車不為空")

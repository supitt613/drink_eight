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
    st.error("❌ 錯誤：請在 Zeabur 或 .env 中設定 SUPABASE_URL 與 SUPABASE_KEY")
    st.stop()

@st.cache_resource
def init_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase_client()

# --- 2. 品牌視覺與 CSS 優化 ---
def apply_branding():
    st.markdown("""
        <style>
        .stApp { background-color: #fcfcfc; }
        .stButton>button { 
            background-color: #f7d302; border-radius: 20px; border: none; color: #333; font-weight: bold;
        }
        .stButton>button:hover { background-color: #e5c302; color: #000; }
        [data-testid="stExpander"] { background-color: #ffffff; border-radius: 10px; border: 1px solid #eee; }
        .stMetric { background-color: #f1f8e9; padding: 10px; border-radius: 10px; }
        </style>
    """, unsafe_allow_html=True)

# --- 3. 飲品資料庫初始化 (修正圖片與名稱) ---
initial_drinks_data = [
    {"name": "柚香覺醒 307", "description": "葡萄柚與307烏龍的極致平衡", "price": 65, "category": "招牌系列", "image_url": "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png"}, # 建議替換為真實URL
    {"name": "八曜和茶", "description": "十多種穀物焙煎，無咖啡因", "price": 45, "category": "經典系列", "image_url": "https://picsum.photos/400/300?random=1"},
    {"name": "究極 308", "description": "輕焙火茶香，回甘生津", "price": 55, "category": "經典系列", "image_url": "https://picsum.photos/400/300?random=2"},
    {"name": "22K 檸檬茶", "description": "新鮮檸檬，微酸清甜", "price": 50, "category": "经典系列", "image_url": "https://picsum.photos/400/300?random=3"},
    {"name": "炙燒濃乳 307", "description": "重烘焙香氣與厚實鮮乳", "price": 75, "category": "厚奶系列", "image_url": "https://picsum.photos/400/300?random=4"},
    {"name": "和風茶乳", "description": "穀物香氣與奶香的完美結合", "price": 60, "category": "厚奶系列", "image_url": "https://picsum.photos/400/300?random=5"}
]

def initialize_supabase_data():
    try:
        response = supabase.from_('drinks').select('id').limit(1).execute()
        if not response.data:
            st.info("📦 正在初始化品牌菜單...")
            for drink in initial_drinks_data:
                supabase.from_('drinks').insert(drink).execute()
            st.rerun()
    except Exception as e:
        st.error(f"資料初始化失敗: {e}")

# --- 4. 核心功能函式 ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'page' not in st.session_state: st.session_state.page = 'menu'

@st.cache_data(ttl=600)
def get_drinks():
    res = supabase.from_('drinks').select('*').order('category').execute()
    return res.data if res.data else []

def add_to_cart(drink_id, name, price, sugar, ice, qty):
    st.session_state.cart.append({
        'drink_id': drink_id, 'name': name, 'price': price, 
        'sugar': sugar, 'ice': ice, 'quantity': qty
    })
    st.toast(f"✅ 已加入: {name}")

def place_order(customer_name):
    if not customer_name:
        st.error("ℹ️ 請輸入姓名後下單")
        return
    total = sum(i['price'] * i['quantity'] for i in st.session_state.cart)
    try:
        order_res = supabase.from_('orders').insert({
            'customer_name': customer_name, 'total_amount': total
        }).execute()
        if order_res.data:
            o_id = order_res.data[0]['id']
            items = []
            for i in st.session_state.cart:
                items.append({
                    'order_id': o_id, 'drink_id': i['drink_id'], 
                    'quantity': i['quantity'], 'price_at_order': i['price'],
                    'sugar_level': i['sugar'], 'ice_level': i['ice']
                })
            supabase.from_('order_items').insert(items).execute()
            st.session_state.cart = []
            st.success("🎉 訂單已送出！")
            st.balloons()
    except Exception as e:
        st.error(f"下單失敗: {e}")

# --- 5. UI 介面 ---
st.set_page_config(page_title="八曜和茶", page_icon="🥤", layout="centered")
apply_branding()
initialize_supabase_data()

# 側邊導航
with st.sidebar:
    st.image("https://www.8teatw.com/wp-content/uploads/2021/08/ba-yao-logo.png", width=150) # Logo
    if st.button("🥤 開始點餐", use_container_width=True): st.session_state.page = 'menu'
    if st.button("🛒 購物車", use_container_width=True): st.session_state.page = 'cart'
    st.divider()
    st.caption("Ba Yao He Cha Digital Ordering")

if st.session_state.page == 'menu':
    st.title("🥤 八曜和茶點餐")
    drinks = get_drinks()
    # 按照類別分組
    categories = sorted(list(set([d['category'] for d in drinks])))
    for cat in categories:
        st.subheader(f"🏷️ {cat}")
        cat_drinks = [d for d in drinks if d['category'] == cat]
        cols = st.columns(2)
        for idx, drink in enumerate(cat_drinks):
            with cols[idx % 2]:
                with st.container(border=True):
                    # 修正警告: 使用 use_container_width 代替 use_column_width
                    st.image(drink['image_url'], use_container_width=True)
                    st.write(f"**{drink['name']}**")
                    st.caption(drink['description'])
                    st.write(f"NT$ {drink['price']}")
                    
                    with st.popover("選擇口味", use_container_width=True):
                        s = st.select_slider("甜度", options=["無糖", "微糖", "半糖", "正常"], key=f"s_{drink['id']}")
                        i = st.select_slider("冰塊", options=["去冰", "微冰", "少冰", "正常"], key=f"i_{drink['id']}")
                        q = st.number_input("數量", 1, 10, 1, key=f"q_{drink['id']}")
                        if st.button("🛒 加入", key=f"add_{drink['id']}", use_container_width=True):
                            add_to_cart(drink['id'], drink['name'], drink['price'], s, i, q)

elif st.session_state.page == 'cart':
    st.title("🛒 您的購物車")
    if not st.session_state.cart:
        st.info("購物車目前是空的")
    else:
        total = 0
        for idx, item in enumerate(st.session_state.cart):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{item['name']}** x {item['quantity']}")
                c1.caption(f"{item['sugar']} | {item['ice']}")
                c2.write(f"${item['price'] * item['quantity']}")
                if c2.button("🗑️", key=f"del_{idx}"):
                    st.session_state.cart.pop(idx)
                    st.rerun()
                total += item['price'] * item['quantity']
        
        st.divider()
        st.metric("總計金額", f"NT$ {total}")
        name = st.text_input("訂購人姓名", placeholder="請輸入姓名")
        if st.button("✅ 確認結帳", use_container_width=True, type="primary"):
            place_order(name)

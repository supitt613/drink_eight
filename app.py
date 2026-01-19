import streamlit as st
import os
from supabase import create_client, Client
import pandas as pd
import itertools

# --- Supabase Client Initialization ---
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("請在環境變數中設定 SUPABASE_URL 和 SUPABASE_KEY。")
    st.stop()

@st.cache_resource
def init_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase_client()

# --- Initial Data for Drinks (if table is empty) ---
initial_drinks_data = [
    {"name": "八曜和茶", "description": "招牌經典，清爽回甘", "price": 45, "category": "經典系列", "image_url": "https://picsum.photos/id/237/200/150"},
    {"name": "22K 檸檬茶", "description": "酸甜檸檬與紅茶的完美結合", "price": 50, "category": "經典系列", "image_url": "https://picsum.photos/id/238/200/150"},
    {"name": "柚香覺醒 307", "description": "清新的柚子香氣，獨特風味", "price": 60, "category": "經典系列", "image_url": "https://picsum.photos/id/239/200/150"},
    {"name": "紅顏 Q 奶茶", "description": "香醇奶茶搭配Q彈珍珠", "price": 55, "category": "經典系列", "image_url": "https://picsum.photos/id/240/200/150"},
    {"name": "檸檬芭樂", "description": "新鮮檸檬與芭樂的酸甜滋味", "price": 65, "category": "特調系列", "image_url": "https://picsum.photos/id/241/200/150"},
    {"name": "柳橙綠", "description": "香甜柳橙與清爽綠茶的絕配", "price": 60, "category": "特調系列", "image_url": "https://picsum.photos/id/242/200/150"},
    {"name": "金鑽鳳梨", "description": "濃郁鳳梨香氣，熱帶風情", "price": 70, "category": "特調系列", "image_url": "https://picsum.photos/id/243/200/150"},
]

def initialize_supabase_data():
    try:
        response = supabase.from_('drinks').select('id').limit(1).execute()
        if not response.data:
            st.info("首次啟動，正在初始化飲品資料...")
            for drink in initial_drinks_data:
                supabase.from_('drinks').insert(drink).execute()
            st.success("飲品資料初始化完成！")
            st.rerun() # Rerun to display the menu with new data
    except Exception as e:
        st.error(f"初始化資料失敗: {e}")

# --- Session State Initialization ---
if 'cart' not in st.session_state:
    st.session_state.cart = [] # [{'drink_id': uuid, 'name': str, 'price': float, 'quantity': int, 'sugar': str, 'ice': str, 'notes': str, 'image_url': str}]
if 'page' not in st.session_state:
    st.session_state.page = 'menu'
if 'customer_name_history' not in st.session_state:
    st.session_state.customer_name_history = ''

# --- Helper Functions ---
@st.cache_data(ttl=3600) # Cache drinks for 1 hour
def get_drinks():
    try:
        response = supabase.from_('drinks').select('*').order('category', desc=False).order('name', desc=False).execute()
        if response.data:
            return response.data
        return []
    except Exception as e:
        st.error(f"無法載入飲品資料: {e}")
        return []

def add_to_cart(drink_id, name, price, image_url, quantity, sugar, ice, notes):
    # Check if item with same options already exists in cart
    for item in st.session_state.cart:
        if item['drink_id'] == drink_id and item['sugar'] == sugar and item['ice'] == ice and item['notes'] == notes:
            item['quantity'] += quantity
            st.success(f"已更新購物車中 {name} 的數量！")
            return
    
    st.session_state.cart.append({
        'drink_id': drink_id,
        'name': name,
        'price': price,
        'image_url': image_url,
        'quantity': quantity,
        'sugar': sugar,
        'ice': ice,
        'notes': notes
    })
    st.success(f"已將 {name} 加入購物車！")

def remove_from_cart(index):
    del st.session_state.cart[index]
    st.success("商品已從購物車移除！")

def update_cart_item(index, quantity=None, sugar=None, ice=None, notes=None):
    if quantity is not None:
        st.session_state.cart[index]['quantity'] = quantity
    if sugar is not None:
        st.session_state.cart[index]['sugar'] = sugar
    if ice is not None:
        st.session_state.cart[index]['ice'] = ice
    if notes is not None:
        st.session_state.cart[index]['notes'] = notes

def place_order(customer_name, cart_items):
    if not customer_name:
        st.error("請輸入您的姓名以完成訂單。")
        return False
    if not cart_items:
        st.error("購物車是空的，無法下訂單。")
        return False

    total_amount = sum(item['price'] * item['quantity'] for item in cart_items)

    try:
        # Insert into orders table
        order_response = supabase.from_('orders').insert({
            'customer_name': customer_name,
            'total_amount': total_amount
        }).execute()
        
        if order_response.data:
            order_id = order_response.data[0]['id']
            
            # Prepare order items for batch insert
            order_items_data = []
            for item in cart_items:
                order_items_data.append({
                    'order_id': order_id,
                    'drink_id': item['drink_id'],
                    'quantity': item['quantity'],
                    'price_at_order': item['price'],
                    'sugar_level': item['sugar'],
                    'ice_level': item['ice'],
                    'notes': item['notes']
                })
            
            # Insert into order_items table
            supabase.from_('order_items').insert(order_items_data).execute()
            
            st.session_state.cart = [] # Clear cart
            st.success(f"訂單 {order_id[:8]}... 已成功送出！總金額: NT${total_amount:.0f}")
            st.session_state.page = 'history' # Redirect to history
            st.session_state.customer_name_history = customer_name # Pre-fill history name
            st.rerun()
            return True
        else:
            st.error("下訂單失敗，請稍後再試。")
            return False
    except Exception as e:
        st.error(f"下訂單時發生錯誤: {e}")
        return False

@st.cache_data(ttl=60) # Cache orders for 1 minute
def get_orders(customer_name):
    try:
        if customer_name:
            response = supabase.from_('orders').select('*').eq('customer_name', customer_name).order('order_date', desc=True).execute()
        else:
            response = supabase.from_('orders').select('*').order('order_date', desc=True).limit(10).execute() # Show recent 10 if no name
        
        if response.data:
            return response.data
        return []
    except Exception as e:
        st.error(f"無法載入訂單紀錄: {e}")
        return []

@st.cache_data(ttl=60) # Cache order items for 1 minute
def get_order_items(order_id):
    try:
        response = supabase.from_('order_items').select('*, drinks(name, price)').eq('order_id', order_id).execute()
        if response.data:
            return response.data
        return []
    except Exception as e:
        st.error(f"無法載入訂單細項: {e}")
        return []

# --- UI Components ---
def display_menu():
    st.header("🥤 點餐菜單")
    st.write("選擇您喜愛的飲品，加入購物車！")

    drinks = get_drinks()
    if not drinks:
        st.warning("目前沒有可用的飲品，請稍後再試或聯繫管理員。")
        return

    # Group drinks by category
    drinks_by_category = {k: list(g) for k, g in itertools.groupby(drinks, lambda x: x['category'])}

    for category, category_drinks in drinks_by_category.items():
        with st.expander(f"**{category}**", expanded=True):
            cols = st.columns(3)
            for i, drink in enumerate(category_drinks):
                with cols[i % 3]:
                    with st.container(border=True):
                        if drink['image_url']:
                            st.image(drink['image_url'], caption=drink['name'], use_column_width='always')
                        else:
                            st.image("https://via.placeholder.com/200x150?text=No+Image", caption=drink['name'], use_column_width='always')
                        
                        st.subheader(drink['name'])
                        st.write(f"NT$ {drink['price']:.0f}")
                        st.caption(drink['description'])

                        with st.popover("加入購物車", use_container_width=True):
                            st.write(f"**{drink['name']}**")
                            quantity = st.number_input("數量", min_value=1, value=1, key=f"qty_{drink['id']}")
                            sugar_level = st.selectbox("甜度", ['正常糖', '七分糖', '半糖', '微糖', '無糖'], key=f"sugar_{drink['id']}")
                            ice_level = st.selectbox("冰塊", ['正常冰', '少冰', '微冰', '去冰', '熱'], key=f"ice_{drink['id']}")
                            notes = st.text_input("備註 (例如：加珍珠)", key=f"notes_{drink['id']}")
                            if st.button("確認加入", key=f"add_{drink['id']}"):
                                add_to_cart(drink['id'], drink['name'], drink['price'], drink['image_url'], quantity, sugar_level, ice_level, notes)
                                st.rerun()

def display_cart():
    st.header("🛒 購物車")

    if not st.session_state.cart:
        st.info("您的購物車是空的，快去點餐吧！")
        return

    total_amount = 0
    for i, item in enumerate(st.session_state.cart):
        item_total = item['price'] * item['quantity']
        total_amount += item_total
        
        with st.container(border=True):
            col1, col2, col3 = st.columns([0.2, 0.6, 0.2])
            with col1:
                if item['image_url']:
                    st.image(item['image_url'], width=80)
                else:
                    st.image("https://via.placeholder.com/80x60?text=No+Image", width=80)
            with col2:
                st.subheader(item['name'])
                st.write(f"單價: NT${item['price']:.0f}")
                st.write(f"甜度: {item['sugar']} | 冰塊: {item['ice']}")
                if item['notes']:
                    st.write(f"備註: {item['notes']}")
            with col3:
                st.metric(label="小計", value=f"NT${item_total:.0f}")
                
                # Quantity controls
                qty_col1, qty_col2, qty_col3 = st.columns([0.3, 0.4, 0.3])
                with qty_col1:
                    if st.button("-", key=f"minus_{i}", use_container_width=True):
                        if item['quantity'] > 1:
                            update_cart_item(i, quantity=item['quantity'] - 1)
                            st.rerun()
                with qty_col2:
                    st.markdown(f"<h3 style='text-align: center; margin:0;'>{item['quantity']}</h3>", unsafe_allow_html=True)
                with qty_col3:
                    if st.button("+", key=f"plus_{i}", use_container_width=True):
                        update_cart_item(i, quantity=item['quantity'] + 1)
                        st.rerun()
                
                if st.button("移除", key=f"remove_{i}", type="secondary", use_container_width=True):
                    remove_from_cart(i)
                    st.rerun()

    st.markdown("--- ")
    st.metric(label="總金額", value=f"NT${total_amount:.0f}")

    st.subheader("訂購人資訊")
    customer_name = st.text_input("您的姓名", value=st.session_state.customer_name_history, key="customer_name_input")

    if st.button("確認下訂單", type="primary", use_container_width=True):
        st.session_state.customer_name_history = customer_name # Remember name for next time
        place_order(customer_name, st.session_state.cart)

def display_order_history():
    st.header("📝 訂單紀錄")

    st.session_state.customer_name_history = st.text_input("輸入姓名查詢訂單", value=st.session_state.customer_name_history, key="history_name_input")
    
    if st.session_state.customer_name_history:
        st.info(f"正在顯示 {st.session_state.customer_name_history} 的訂單紀錄。")
        orders = get_orders(st.session_state.customer_name_history)
    else:
        st.info("請輸入姓名以查詢您的訂單，或查看最近的訂單。")
        orders = get_orders(None) # Show recent orders if no name is entered

    if not orders:
        st.warning("沒有找到任何訂單紀錄。")
        return

    for order in orders:
        with st.expander(f"訂單號碼: {order['id'][:8]}... | 總金額: NT${order['total_amount']:.0f} | 日期: {pd.to_datetime(order['order_date']).strftime('%Y-%m-%d %H:%M')}"):
            st.write(f"**訂單狀態**: {order['status']}")
            st.write(f"**訂購人**: {order['customer_name']}")
            st.subheader("訂單細項")
            order_items = get_order_items(order['id'])
            if order_items:
                items_df = pd.DataFrame([
                    {
                        '品項': item['drinks']['name'],
                        '單價': item['price_at_order'],
                        '數量': item['quantity'],
                        '甜度': item['sugar_level'],
                        '冰塊': item['ice_level'],
                        '備註': item['notes'] if item['notes'] else ''
                    }
                    for item in order_items
                ])
                st.dataframe(items_df, use_container_width=True, hide_index=True)
            else:
                st.info("此訂單沒有細項。")

# --- Main App Layout ---
st.set_page_config(page_title="八曜和茶訂購 App", page_icon="🥤", layout="centered")

# Run initial data population once
initialize_supabase_data()

st.sidebar.title("八曜和茶訂購")
st.sidebar.markdown("--- ")

if st.sidebar.button("🥤 點餐", use_container_width=True):
    st.session_state.page = 'menu'
if st.sidebar.button("🛒 購物車", use_container_width=True):
    st.session_state.page = 'cart'
if st.sidebar.button("📝 訂單紀錄", use_container_width=True):
    st.session_state.page = 'history'

st.sidebar.markdown("--- ")
st.sidebar.info("由 Streamlit & Supabase 驅動")

# Render main content based on page state
if st.session_state.page == 'menu':
    display_menu()
elif st.session_state.page == 'cart':
    display_cart()
elif st.session_state.page == 'history':
    display_order_history()

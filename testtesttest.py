import streamlit as st
from collections import deque
from typing import Optional, List
from streamlit_autorefresh import st_autorefresh # <<< ADDED FOR POLLING

# =========================
# THEME COLORS 
# =========================
PRIMARY_RED = "#D43C2C"
WARM_YELLOW = "#F4C542"
ACCENT_ORANGE = "#E67E22"
OFF_WHITE = "#FBF7F2"
CARD_WHITE = "#FFFFFF"
TEXT_DARK = "#2E2E2E"

st.set_page_config(page_title="FoodHub Pro Max", layout="wide")

class Item:
    def __init__(self, item_id: str, name: str, price: float, available: bool=True):
        self.item_id = item_id
        self.name = name
        self.price = price
        self.available = available
        self.next = None

class Menu:
    def __init__(self):
        self.head: Optional[Item] = None

    def insert(self, node: Item):
        if not self.head:
            self.head = node
            return
        cur = self.head
        while cur.next:
            cur = cur.next
        cur.next = node

    def delete(self, item_id: str) -> bool:
        prev = None
        cur = self.head
        while cur:
            if cur.item_id == item_id:
                if prev:
                    prev.next = cur.next
                else:
                    self.head = cur.next
                return True
            prev = cur
            cur = cur.next
        return False

    def find(self, item_id: str) -> Optional[Item]:
        cur = self.head
        while cur:
            if cur.item_id == item_id:
                return cur
            cur = cur.next
        return None

    def to_list(self) -> List[Item]:
        out = []
        cur = self.head
        while cur:
            out.append(cur)
            cur = cur.next
        return out


class Category:
    def __init__(self, name: str):
        self.name = name
        self.children = {}
        self.items_list = Menu()

    def add_child(self, child_name: str):
        if child_name not in self.children:
            self.children[child_name] = Category(child_name)
        return self.children[child_name]

    def get_child(self, child_name: str) -> Optional['Category']:
        return self.children.get(child_name)

    def traverse_preorder(self):
        stack = [(self, 0)]
        while stack:
            node, depth = stack.pop()
            yield node, depth
            for child_name in sorted(node.children.keys(), reverse=True):
                stack.append((node.children[child_name], depth+1))


RECENT_LIMIT = 5

class RecentUpdates:
    def __init__(self, limit=RECENT_LIMIT):
        self.q = deque(maxlen=limit)

    def enqueue(self, text: str):
        self.q.append(text)

    def get(self):
        return list(self.q)


class Shop:
    def __init__(self, shop_id: str, name: str, password: str):
        self.shop_id = shop_id
        self.name = name
        self.password = password
        self.status = "Closed"
        self.menu_tree = Category(name)
        self.recent_updates = RecentUpdates()

    def add_category(self, category_name: str):
        self.menu_tree.add_child(category_name)
        self.recent_updates.enqueue(f"Category '{category_name}' added")

    def add_item(self, category_name: str, item_id: str, item_name: str, price: float):
        cat = self.menu_tree.get_child(category_name)
        if not cat:
            cat = self.menu_tree.add_child(category_name)
        node = Item(item_id, item_name, price, available=True)
        cat.items_list.insert(node)
        self.recent_updates.enqueue(f"Added item '{item_name}' to {category_name}")

    def remove_item(self, category_name: str, item_id: str):
        cat = self.menu_tree.get_child(category_name)
        if not cat:
            return False
        success = cat.items_list.delete(item_id)
        if success:
            self.recent_updates.enqueue(f"Removed item {item_id} from {category_name}")
        return success

    def find_item(self, item_id: str):
        for node, _ in self.menu_tree.traverse_preorder():
            found = node.items_list.find(item_id)
            if found:
                return node, found
        return None, None

    def toggle_availability(self, category_name: str, item_id: str, available: bool):
        cat = self.menu_tree.get_child(category_name)
        if not cat:
            return False
        found = cat.items_list.find(item_id)
        if not found:
            return False
        found.available = available
        state = "Available" if available else "Sold Out"
        self.recent_updates.enqueue(f"Item '{found.name}' marked {state}")
        return True


if 'shops' not in st.session_state:
    st.session_state.shops = {}

    s1 = Shop('s1', 'Tito Jims Grill', 'hesoyam')
    s1.status = 'Open'
    s1.add_category('Meals')
    s1.add_item('Meals', 'm1', 'Chicken BBQ', 120.0)
    s1.add_item('Meals', 'm2', 'Pork Sisig', 80.0)
    s1.add_category('Drinks')
    s1.add_item('Drinks', 'd1', 'Iced Tea', 25.0)

    s2 = Shop('s2', 'Sweet Bites', 'stinglikeabee')
    s2.add_category('Desserts')
    s2.add_item('Desserts', 'ds1', 'Chocolate Cake', 60.0)

    st.session_state.shops[s1.shop_id] = s1
    st.session_state.shops[s2.shop_id] = s2

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'shops'
if 'show_logout_confirm' not in st.session_state:
    st.session_state.show_logout_confirm = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'search_shop_results' not in st.session_state:
    st.session_state.search_shop_results = []
if 'search_item_results' not in st.session_state:
    st.session_state.search_item_results = {}



def authenticate_shop(shop_id: str, password: str) -> Optional[Shop]:
    shop = st.session_state.shops.get(shop_id)
    if shop and shop.password == password:
        return shop
    return None

def list_shops():
    return list(st.session_state.shops.values())

def perform_search(query):
    shop_results = []
    item_results = {}

    if not query:
        st.session_state.search_shop_results = []
        st.session_state.search_item_results = {}
        return

    for shop in list_shops():
        if query.lower() in shop.name.lower() or query.lower() in shop.shop_id.lower():
            shop_results.append(shop)

        for node, _ in shop.menu_tree.traverse_preorder():
            for it in node.items_list.to_list():
                if query.lower() in it.name.lower() or query.lower() in it.item_id.lower():
                    if shop.shop_id not in item_results:
                        item_results[shop.shop_id] = []
                    item_results[shop.shop_id].append((node.name, it))
    
    st.session_state.search_shop_results = shop_results
    st.session_state.search_item_results = item_results


#dto nyu edit ui
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {OFF_WHITE};
        color: {TEXT_DARK};
    }}

    .main [data-testid="stVerticalBlock"] {{
        padding-top: 0px !important;
        margin-top: 0px !important;
    }}

    [data-testid="stAppViewContainer"] > div:first-child {{
        padding-top: 0 !important;
        margin-top: 0 !important;
    }}

    [data-testid="stAppViewContainer"] > div:first-child > div:first-child {{
        margin-top: 0 !important;
        padding-top: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }}

    .main-header-card {{
        background: linear-gradient(180deg, rgba(255,255,255,0.98), {CARD_WHITE});
        border-radius: 14px;
        padding: 16px 22px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.07);
        margin-bottom: 18px;
        border: 1px solid rgba(0,0,0,0.04);
    }}

    .big-title {{
        font-size: 6.2rem !important;
        line-height: 0.92 !important;
        font-weight: 900 !important;
        margin: 0 !important;
        padding: 0 !important;
        background: linear-gradient(135deg, {PRIMARY_RED}, {ACCENT_ORANGE});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
    }}

    .sub-text {{
        color: #555;
        font-size: 1.05rem;
        margin-top: 6px;
        margin-bottom: 8px;
    }}

    .stButton>button {{
        border-radius: 10px !important;
        padding: .6rem 0.9rem !important;
        font-weight: 700 !important;
        background-color: {PRIMARY_RED} !important;
        color: white !important;
        box-shadow: 0 6px 18px rgba(0,0,0,0.06) !important;
    }}

    .secondary-btn > button {{
        background: transparent !important;
        border: 1px solid rgba(0,0,0,0.08) !important;
        color: {TEXT_DARK} !important;
    }}

    .shop-card {{
        background: {CARD_WHITE};
        border-radius: 12px;
        padding: 14px;
        border: 1px solid rgba(0,0,0,0.04);
        box-shadow: 0 8px 30px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }}

    .shop-detail-card {{
        background: linear-gradient(180deg, #fff, #fff);
        border-radius: 12px;
        padding: 18px;
        border: 1px solid rgba(0,0,0,0.04);
        box-shadow: 0 8px 30px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }}

    .accent-strip {{
        width:6px;
        height:36px;
        background: {PRIMARY_RED};
        display:inline-block;
        vertical-align: middle;
        margin-right:10px;
        border-radius:4px;
    }}

    .section-title {{
        color: {PRIMARY_RED};
        font-weight:800;
        font-size:1.25rem;
        display:inline-block;
        vertical-align: middle;
    }}

    .muted {{
        color: #666;
        font-size: 0.95rem;
    }}

    .login-wrap {{
        display:flex;
        justify-content:center;
        align-items:center;
    }}
    </style>
    """,
    unsafe_allow_html=True
)



def show_login_page():
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    left, center, right = st.columns([1, 2.4, 1])
    with center:
        st.markdown('<div class="main-header-card">', unsafe_allow_html=True)
        st.markdown('<p class="big-title">🍔 FoodHub Pro Max</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-text">is it ok if i call you mine</p>', unsafe_allow_html=True)

        st.markdown('<div style="max-width:520px; margin-top: 6px;">', unsafe_allow_html=True)
        role = st.radio("I am a:", ['Customer', 'Vendor / Shop Owner'], key="role_radio")
        st.markdown('</div>', unsafe_allow_html=True)

        if role == 'Vendor / Shop Owner':
            st.markdown('<div style="margin-top:10px">', unsafe_allow_html=True)
            shop_id = st.selectbox('Select Shop ID', options=[s.shop_id for s in list_shops()], key="vendor_select")
            pwd = st.text_input('Password', type='password', key="vendor_pwd")
            if st.button('Login as Vendor', key='vendor_login_btn_v3', use_container_width=True):
                shop = authenticate_shop(shop_id, pwd)
                if shop:
                    st.session_state.authenticated = True
                    st.session_state.current_shop = shop.shop_id
                    st.session_state.role = 'vendor'
                    st.session_state.view_mode = 'vendor_dashboard'
                    st.session_state.show_logout_confirm = False
                    st.rerun()
                else:
                    st.error('Invalid credentials')
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="margin-top:14px">', unsafe_allow_html=True)
            if st.button('Continue as Customer', key='continue_customer_btn_v3', use_container_width=True):
                st.session_state.authenticated = True
                st.session_state.role = 'customer'
                st.session_state.view_mode = 'shops'
                st.session_state.show_logout_confirm = False
                if 'current_shop' in st.session_state:
                    del st.session_state['current_shop']
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)



def show_home_page():
    st_autorefresh(interval=5000, key="data_refresher_v4")

    with st.container():
        st.markdown('<div class="main-header-card">', unsafe_allow_html=True)
        if st.session_state.get('role') == 'vendor' and st.session_state.get('authenticated'):
            cols = st.columns([3.0, 0.9, 0.9, 0.9, 0.9])
        else:
            cols = st.columns([3.6, 1.1, 1.1, 1.1])

        with cols[0]:
            st.markdown('<p class="big-title">🍔 FoodHub Pro Max</p>', unsafe_allow_html=True)
            st.markdown('<p class="sub-text">just for a time</p>', unsafe_allow_html=True)

        if st.session_state.get('role') == 'vendor' and st.session_state.get('authenticated'):
            with cols[1]:
                if st.button('Dashboard', key='nav_dashboard_v3', use_container_width=True):
                    if 'current_shop' not in st.session_state:
                        shops = list_shops()
                        if shops:
                            st.session_state.current_shop = shops[0].shop_id
                    st.session_state.view_mode = 'vendor_dashboard'
                    st.rerun()
            nav_offset = 2
        else:
            nav_offset = 1

        shops_col_index = nav_offset
        search_col_index = nav_offset + 1
        logout_col_index = nav_offset + 2

        with cols[shops_col_index]:
            if st.button('Shops', key='nav_shops_v3', use_container_width=True):
                st.session_state.view_mode = 'shops'
                if 'current_shop' in st.session_state:
                    del st.session_state['current_shop']
                st.session_state.search_shop_results = []
                st.session_state.search_item_results = []
                st.rerun()
        with cols[search_col_index]:
            if st.button('Search', key='nav_search_v3', use_container_width=True):
                st.session_state.view_mode = 'search'
                st.rerun()
        with cols[logout_col_index]:
            if st.button('Logout', key='nav_logout_v3', use_container_width=True):
                st.session_state.show_logout_confirm = True

            if st.session_state.get('show_logout_confirm', False):
                st.warning("Are you sure you want to logout?", icon="⚠️")
                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button("Yes, logout", key="confirm_logout_v3"):
                        shops = st.session_state.get('shops', {})
                        st.session_state.clear()
                        st.session_state.shops = shops
                        st.session_state.authenticated = False
                        st.session_state.view_mode = 'shops'
                        st.session_state.show_logout_confirm = False
                        st.session_state.role = None
                        st.rerun()
                with c2:
                    if st.button("Cancel", key="cancel_logout_v3"):
                        st.session_state.show_logout_confirm = False
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    st.markdown("---")

    if st.session_state.view_mode == 'search':
        st.subheader("Search Shops & Items")
        search_col1, search_col2 = st.columns([5, 1])
        with search_col1:
            query = st.text_input('Search', placeholder='Search for shops or items...', label_visibility='collapsed', key='search_input_v3')
        with search_col2:
            st.button('Search', key='search_main_btn_v3', use_container_width=True, on_click=perform_search, args=(query,))

        shop_results = st.session_state.search_shop_results
        item_results = st.session_state.search_item_results
        
        if shop_results or item_results or query:
            
            if shop_results:
                st.markdown("### Shops")
                for shop in shop_results:
                    c = st.container()
                    with c:
                        st.markdown(
                            f"<div class='shop-card'><div style='display:flex; align-items:center; gap:12px;'>"
                            f"<div class='accent-strip'></div><div><strong style='font-size:1.05rem'>{shop.name}</strong>"
                            f"<div class='muted'>Status: {shop.status} — ID: {shop.shop_id}</div></div></div></div>",
                            unsafe_allow_html=True)
                        if st.button("View Shop", key=f"search_shop_v3_{shop.shop_id}", use_container_width=True):
                            st.session_state.current_shop = shop.shop_id
                            st.session_state.view_mode = 'shop_detail'
                            st.rerun()

            if item_results:
                st.markdown("### Items Found")
                for shop_id, items in item_results.items():
                    shop = st.session_state.shops[shop_id]
                    with st.expander(f"{shop.name} — {len(items)} item(s)"):
                        for cat_name, it in items:
                            row_container = st.container()
                            with row_container:
                                row_c1, row_c2 = st.columns([3, 1])
                                with row_c1:
                                    st.write(f"**{it.name}** — ₱{it.price:.2f}")
                                    st.caption(f"Category: {cat_name} | ID: {it.item_id} | {'Available' if it.available else 'Sold Out'}")
                                with row_c2:
                                    if st.button("View Shop", key=f"search_item_v3_{shop_id}_{it.item_id}", use_container_width=True):
                                        st.session_state.current_shop = shop_id
                                        st.session_state.view_mode = 'shop_detail'
                                        st.rerun()

            if not shop_results and not item_results and query:
                st.info("No results found.")

    elif st.session_state.view_mode == 'shops':
        st.session_state.search_shop_results = []
        st.session_state.search_item_results = []

        st.subheader('Available Shops')
        shops = list_shops()
        for shop in shops:
            c = st.container()
            with c:
                st.markdown(
                    f"<div class='shop-card'><div style='display:flex; justify-content:space-between; align-items:center; gap:16px;'>"
                    f"<div style='display:flex; align-items:center; gap:12px;'><div class='accent-strip'></div>"
                    f"<div><strong style='font-size:1.05rem'>{shop.name}</strong><div class='muted'>Status: {shop.status} • ID: {shop.shop_id}</div></div>"
                    f"</div></div></div>",
                    unsafe_allow_html=True)
                if st.button("View Details", key=f"open_v3_{shop.shop_id}", use_container_width=True):
                    st.session_state.current_shop = shop.shop_id
                    st.session_state.view_mode = 'shop_detail'
                    st.rerun()
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    elif st.session_state.view_mode == 'shop_detail' and st.session_state.get('current_shop'):
        st.session_state.search_shop_results = []
        st.session_state.search_item_results = []
        
        shop = st.session_state.shops[st.session_state.current_shop]

        st.markdown(
            f"<div class='shop-detail-card' style='display:flex; justify-content:space-between; align-items:center; gap:12px;'>"
            f"<div style='display:flex; align-items:center; gap:12px;'><div class='accent-strip'></div>"
            f"<div><h2 style='margin:0; padding:0;'>{shop.name}</h2><div class='muted'>Status: {shop.status}</div></div></div>"
            f"<div>{''}</div></div>",
            unsafe_allow_html=True)

        back_cols = st.columns([1,1,6])
        with back_cols[0]:
            if st.button('Back to Shops', key='back_to_shops_v3', use_container_width=True):
                st.session_state.view_mode = 'shops'
                if 'current_shop' in st.session_state:
                    del st.session_state['current_shop']
                st.rerun()
        with back_cols[1]:
            if st.session_state.get('role') == 'vendor' and st.session_state.get('authenticated'):
                if st.button('Go to Dashboard', key='goto_dashboard_v3', use_container_width=True):
                    st.session_state.view_mode = 'vendor_dashboard'
                    st.rerun()

        st.markdown("---")
        st.markdown(f"<div style='display:flex; align-items:center; gap:10px; margin-bottom:8px;'>"
                    f"<div class='accent-strip'></div><div class='section-title'>Menu</div></div>", unsafe_allow_html=True)

        for node, depth in shop.menu_tree.traverse_preorder():
            if node is shop.menu_tree:
                continue
            st.markdown(f"**{node.name}**")
            items = node.items_list.to_list()
            if not items:
                st.write(f"- (no items)")
            else:
                for it in items:
                    status = 'Available' if it.available else 'Sold Out'
                    st.markdown(
                        f"<div style='background:{OFF_WHITE}; padding:10px 12px; border-radius:10px; margin-bottom:8px; "
                        f"display:flex; justify-content:space-between; align-items:center;'>"
                        f"<div><strong>{it.name}</strong><div class='muted'>ID: {it.item_id} • {status}</div></div>"
                        f"<div style='min-width:110px; text-align:right;'>₱{it.price:.2f}</div></div>",
                        unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f"<div style='display:flex; align-items:center; gap:10px; margin-bottom:8px;'>"
                    f"<div class='accent-strip'></div><div class='section-title'>Recent Updates</div></div>", unsafe_allow_html=True)
        updates = shop.recent_updates.get()
        if updates:
            for u in reversed(updates):
                st.write('- ' + u)
        else:
            st.write('No updates yet')

    elif st.session_state.view_mode == 'vendor_dashboard' and st.session_state.get('current_shop'):
        shop = st.session_state.shops[st.session_state.current_shop]
        st.subheader(f"Vendor Dashboard — {shop.name}")

        new_status = st.selectbox('Shop Status', ['Open', 'Closed', 'Preparing'], key=f'vendor_status_v3',
                                 index=['Open','Closed','Preparing'].index(shop.status) if shop.status in ['Open','Closed','Preparing'] else 1)
        if st.button('Update Status', key=f'update_status_v3_{shop.shop_id}', use_container_width=False):
            if new_status != shop.status:
                shop.status = new_status
                shop.recent_updates.enqueue(f"Shop status changed to {new_status}")
                st.success('Status updated')
                st.rerun()

        st.markdown('---')
        st.markdown('### Menu Management')

        with st.expander('Add Category'):
            all_cats_keys = list(shop.menu_tree.children.keys())
            cat_name = st.text_input('Category Name', key=f'new_cat_v3_{shop.shop_id}')
            if st.button('Add Category', key=f'add_cat_btn_v3_{shop.shop_id}'):
                if cat_name.strip():
                    if cat_name.strip() not in all_cats_keys:
                        shop.add_category(cat_name.strip())
                        st.success(f"Category '{cat_name}' added")
                        st.rerun()
                    else:
                        st.error(f"Category '{cat_name}' already exists.")
                else:
                    st.error('Provide a category name')

        with st.expander('Add Item'):
            all_cats = list(shop.menu_tree.children.keys())
            if not all_cats:
                st.info('No categories yet. Add a category first.')
            else:
                cat = st.selectbox('Category', options=all_cats, key=f'add_item_cat_v3_{shop.shop_id}')
                item_id = st.text_input('Item ID (unique)', key=f'item_id_v3_{shop.shop_id}')
                item_name = st.text_input('Item Name', key=f'item_name_v3_{shop.shop_id}')
                price = st.number_input('Price', min_value=0.0, format='%.2f', key=f'item_price_v3_{shop.shop_id}')
                if st.button('Add Item', key=f'add_item_btn_v3_{shop.shop_id}'):
                    if not item_id.strip() or not item_name.strip():
                        st.error('Provide item id and name')
                    else:
                        _, found = shop.find_item(item_id)
                        if found:
                            st.error('Item ID already exists')
                        else:
                            shop.add_item(cat, item_id.strip(), item_name.strip(), float(price))
                            st.success(f"Item '{item_name}' added to {cat}")
                            st.rerun()

        with st.expander('Edit / Remove Items'):
            for cat_name, cat_node in shop.menu_tree.children.items():
                st.markdown(f"**Category: {cat_name}**")
                items = cat_node.items_list.to_list()
                if not items:
                    st.info('No items in this category')
                    continue
                for it in items:
                    cols = st.columns([2,1,1,1])
                    cols[0].write(f"{it.item_id} — {it.name}")
                    cols[1].write(f"₱{it.price:.2f}")
                    avail = 'Available' if it.available else 'Sold Out'
                    cols[2].write(avail)
                    
                    if cols[3].button('Toggle', key=f"tog_v3_{shop.shop_id}_{it.item_id}", use_container_width=True):
                        shop.toggle_availability(cat_name, it.item_id, not it.available)
                        st.rerun()

                    if cols[3].button('Remove', key=f"rem_v3_{shop.shop_id}_{it.item_id}", use_container_width=True):
                        shop.remove_item(cat_name, it.item_id)
                        st.rerun()

        st.markdown('---')
        st.subheader('Recent Updates')
        updates = shop.recent_updates.get()
        if updates:
            for u in reversed(updates):
                st.write('- ' + u)
        else:
            st.write('No updates yet')


if not st.session_state.authenticated:
    show_login_page()
else:
    show_home_page()
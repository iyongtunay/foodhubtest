import streamlit as st
from collections import deque
from typing import Optional, List

st.set_page_config(page_title="FoodHub Pro Max", layout="wide")


class LinkedListNode:
    def __init__(self, item_id: str, name: str, price: float, available: bool=True):
        self.item_id = item_id
        self.name = name
        self.price = price
        self.available = available
        self.next = None

class LinkedList:
    """Singly linked list for menu items."""
    def __init__(self):
        self.head: Optional[LinkedListNode] = None

    def insert(self, node: LinkedListNode):
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

    def find(self, item_id: str) -> Optional[LinkedListNode]:
        cur = self.head
        while cur:
            if cur.item_id == item_id:
                return cur
            cur = cur.next
        return None

    def to_list(self) -> List[LinkedListNode]:
        out = []
        cur = self.head
        while cur:
            out.append(cur)
            cur = cur.next
        return out


class TreeNode:
    def __init__(self, name: str):
        self.name = name
        self.children = {}  
        self.items_list = LinkedList()

    def add_child(self, child_name: str):
        if child_name not in self.children:
            self.children[child_name] = TreeNode(child_name)
        return self.children[child_name]

    def get_child(self, child_name: str) -> Optional['TreeNode']:
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
        self.menu_tree = TreeNode(name)
        self.recent_updates = RecentUpdates()

    def add_category(self, category_name: str):
        self.menu_tree.add_child(category_name)
        self.recent_updates.enqueue(f"Category '{category_name}' added")

    def add_item(self, category_name: str, item_id: str, item_name: str, price: float):
        cat = self.menu_tree.get_child(category_name)
        if not cat:
            cat = self.menu_tree.add_child(category_name)
        node = LinkedListNode(item_id, item_name, price, available=True)
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


def authenticate_shop(shop_id: str, password: str) -> Optional[Shop]:
    shop = st.session_state.shops.get(shop_id)
    if shop and shop.password == password:
        return shop
    return None


def list_shops():
    return list(st.session_state.shops.values())


st.title("FoodHub Pro Max")
st.write("is it ok if i call you mine?")

col1, col2 = st.columns([1, 2])
with col1:
    st.header("Login / Access")
    role = st.radio("I am a:", ['Customer', 'Vendor / Shop Owner'])

    if role == 'Vendor / Shop Owner':
        shop_id = st.selectbox('Select Shop ID', options=[s.shop_id for s in list_shops()])
        pwd = st.text_input('Password', type='password')
        if st.button('Login as Vendor'):
            shop = authenticate_shop(shop_id, pwd)
            if shop:
                st.success(f"Logged in as {shop.name}")
                st.session_state.current_shop = shop.shop_id
                st.session_state.role = 'vendor'
            else:
                st.error('Invalid credentials')

    else:
        if st.button('Continue as Customer'):
            st.session_state.role = 'customer'
            if 'current_shop' in st.session_state:
                del st.session_state['current_shop']


with col2:
    if st.session_state.get('role') == 'customer':
        st.subheader('Available Shops')
        shops = list_shops()
        for shop in shops:
            st.markdown(f"**{shop.name}**  — Status: *{shop.status}*  \n ID: `{shop.shop_id}`")
            if st.button(f"Open {shop.shop_id}", key=f"open_{shop.shop_id}"):
                st.session_state.current_shop = shop.shop_id

    elif st.session_state.get('role') == 'vendor' and st.session_state.get('current_shop'):
        shop = st.session_state.shops[st.session_state.current_shop]
        st.subheader(f"Vendor Dashboard — {shop.name}")

        new_status = st.selectbox('Shop Status', ['Open', 'Closed', 'Preparing'], index=['Open','Closed','Preparing'].index(shop.status) if shop.status in ['Open','Closed','Preparing'] else 1)
        if new_status != shop.status:
            shop.status = new_status
            shop.recent_updates.enqueue(f"Shop status changed to {new_status}")
            st.success('Status updated')

        st.markdown('---')
        st.markdown('### Menu Management')
        with st.expander('Add Category'):
            cat_name = st.text_input('Category Name', key='new_cat')
            if st.button('Add Category', key='add_cat_btn'):
                if cat_name.strip():
                    shop.add_category(cat_name.strip())
                    st.success(f"Category '{cat_name}' added")
                else:
                    st.error('Provide a category name')

        with st.expander('Add Item'):
            all_cats = list(shop.menu_tree.children.keys())
            if not all_cats:
                st.info('No categories yet. Add a category first.')
            else:
                cat = st.selectbox('Category', options=all_cats, key='add_item_cat')
                item_id = st.text_input('Item ID (unique)', key='item_id')
                item_name = st.text_input('Item Name', key='item_name')
                price = st.number_input('Price', min_value=0.0, format='%.2f', key='item_price')
                if st.button('Add Item', key='add_item_btn'):
                    if not item_id.strip() or not item_name.strip():
                        st.error('Provide item id and name')
                    else:
                        _, found = shop.find_item(item_id)
                        if found:
                            st.error('Item ID already exists')
                        else:
                            shop.add_item(cat, item_id.strip(), item_name.strip(), float(price))
                            st.success(f"Item '{item_name}' added to {cat}")

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
                    if cols[3].button('Toggle Availability', key=f"tog_{shop.shop_id}_{it.item_id}"):
                        shop.toggle_availability(cat_name, it.item_id, not it.available)
                        st.experimental_rerun()
                    if cols[3].button('Remove', key=f"rem_{shop.shop_id}_{it.item_id}"):
                        shop.remove_item(cat_name, it.item_id)
                        st.experimental_rerun()

        st.markdown('---')
        st.subheader('Recent Updates')
        updates = shop.recent_updates.get()
        if updates:
            for u in reversed(updates):
                st.write('- ' + u)
        else:
            st.write('No updates yet')

    else:
        st.subheader('Shop Details')
        if st.session_state.get('current_shop'):
            shop = st.session_state.shops[st.session_state.current_shop]
            st.markdown(f"### {shop.name} — Status: *{shop.status}*")
            for node, depth in shop.menu_tree.traverse_preorder():
                if node is shop.menu_tree:
                    continue
                indent = ' ' * (depth*4)
                st.markdown(f"{indent}**{node.name}**")
                items = node.items_list.to_list()
                if not items:
                    st.write(f"{indent}- (no items)")
                else:
                    for it in items:
                        badge = '/' if it.available else 'X'
                        st.write(f"{indent}- {it.item_id} | {it.name} — ₱{it.price:.2f} {badge}")

            st.markdown('---')
            st.subheader('Recent Updates')
            for u in reversed(shop.recent_updates.get()):
                st.write('- ' + u)
        else:
            st.info('Select a role on the left and continue. Customers can view shops; Vendors log in to manage their shop.')


st.sidebar.title('Search')
query = st.sidebar.text_input('Search shop or item by name or id')
if st.sidebar.button('Search'):
    results = []
    for shop in list_shops():
        if query.lower() in shop.name.lower() or query.lower() in shop.shop_id.lower():
            results.append((shop, None))
        else:
            for node, _ in shop.menu_tree.traverse_preorder():
                for it in node.items_list.to_list():
                    if query.lower() in it.name.lower() or query.lower() in it.item_id.lower():
                        results.append((shop, it))
    if not results:
        st.sidebar.write('No results')
    else:
        for shop, it in results:
            if it is None:
                st.sidebar.write(f"Shop: {shop.name} (ID: {shop.shop_id}) — {shop.status}")
            else:
                st.sidebar.write(f"{shop.name} — {it.item_id} | {it.name} — ₱{it.price:.2f} — {'Available' if it.available else 'Sold Out'}")




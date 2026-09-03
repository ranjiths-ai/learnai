import streamlit as st
import json
import os
import pandas as pd
from datetime import date

# --- CONFIGURATION ---
st.set_page_config(page_title="Nexus Library Pro", layout="wide", page_icon="🏛️")

DB_FILE = 'library_v3_db.json'

# --- THEME ADAPTIVE CSS (UI/UX PRO MAX) ---
st.markdown("""
    <style>
    /* Theme-aware Sidebar Text & Background */
    [data-testid="stSidebar"] {
        background-image: linear-gradient(180deg, #2b32b2 0%, #1488cc 100%);
        border-right: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Make Sidebar Radio Labels Pop */
    [data-testid="stSidebar"] .stRadio label {
        color: white !important;
        font-weight: 600 !important;
        font-size: 18px !important;
        padding: 10px;
        background: rgba(255,255,255,0.1);
        border-radius: 8px;
        margin-bottom: 5px;
        display: block;
    }

    /* High Visibility for Dark/Light modes on Main Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        font-weight: bold;
        padding: 0.6rem;
    }
    
    /* Stats Cards */
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        text-align: center;
        color: #333;
    }
    </style>
    """, unsafe_allow_html=True)

# --- DATABASE ENGINE ---
def load_db():
    if not os.path.exists(DB_FILE):
        default_db = {
            "users": {"admin": {"password": "admin", "role": "admin", "status": "Active", "name": "Super User"}},
            "books": {}, 
            "transactions": [],
            "metadata": {"last_isbn": 1000}
        }
        save_db(default_db)
        return default_db
    with open(DB_FILE, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# --- SESSION INITIALIZATION ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'login'
if 'user' not in st.session_state: st.session_state.user = None

# --- AUTHENTICATION SCREENS ---
def main_auth_page():
    st.title("📚 Nexus Library Management System")
    st.markdown("### Welcome to the Pro Library Portal")
    
    # Header Buttons
    c1, c2, c3 = st.columns(3)
    if c1.button("🔑 Login", use_container_width=True): st.session_state.auth_mode = 'login'
    if c2.button("📝 Sign Up", use_container_width=True): st.session_state.auth_mode = 'signup'
    if c3.button("🔄 Reset Form", use_container_width=True): st.rerun()

    st.divider()

    db = load_db()

    # --- LOGIN OVERWRITE LOGIC ---
    if st.session_state.auth_mode == 'login':
        st.subheader("Account Login")
        with st.container(border=True):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.button("Enter System"):
                if u in db['users'] and db['users'][u]['password'] == p:
                    if db['users'][u]['status'] == "Blocked":
                        st.error("Access Denied: Account Blocked.")
                    else:
                        st.session_state.logged_in = True
                        st.session_state.user = u
                        st.session_state.role = db['users'][u]['role']
                        st.success("Login Successful!")
                        st.rerun()
                else:
                    st.error("Invalid Username or Password")

    # --- SIGNUP OVERWRITE LOGIC ---
    elif st.session_state.auth_mode == 'signup':
        st.subheader("Create New Account")
        with st.container(border=True):
            new_u = st.text_input("Choose Username")
            new_p = st.text_input("Choose Password", type="password")
            full_name = st.text_input("Full Name")
            if st.button("Register Now"):
                if new_u and new_p:
                    if new_u in db['users']:
                        st.warning("Username already taken.")
                    else:
                        db['users'][new_u] = {
                            "password": new_p, "role": "user", 
                            "status": "Active", "name": full_name
                        }
                        save_db(db)
                        st.success("Registration Complete! Redirecting to Login...")
                        st.session_state.auth_mode = 'login'
                        st.rerun()
                else:
                    st.error("All fields are required.")

# --- ADMIN FUNCTIONS ---
def admin_panel():
    db = load_db()
    tab1, tab2, tab3 = st.tabs(["📚 Catalog Control", "👥 User Access", "✅ Return Approvals"])
    
    with tab1:
        st.write("### Add Book (Auto-Increment ISBN)")
        with st.form("add_book", clear_on_submit=True):
            t = st.text_input("Book Title")
            a = st.text_input("Author")
            c = st.selectbox("Category", ["Tech", "History", "Fiction", "Science"])
            if st.form_submit_button("Add Book"):
                new_isbn = db['metadata']['last_isbn'] + 1
                db['books'][str(new_isbn)] = {"title": t, "author": a, "cat": c, "status": "Available"}
                db['metadata']['last_isbn'] = new_isbn
                save_db(db)
                st.success(f"Added ISBN: {new_isbn}")

    with tab2:
        st.write("### Block/Unblock Users")
        users_df = pd.DataFrame([{"User": k, **v} for k, v in db['users'].items() if k != 'admin'])
        if not users_df.empty:
            st.dataframe(users_df[['User', 'name', 'status']], use_container_width=True)
            target = st.selectbox("Select User", users_df['User'])
            if st.button("Toggle Block Status"):
                db['users'][target]['status'] = "Blocked" if db['users'][target]['status'] == "Active" else "Active"
                save_db(db)
                st.rerun()

    with tab3:
        st.write("### Pending Return Approvals")
        pending = [t for t in db['transactions'] if t['status'] == "Pending Approval"]
        if pending:
            for pt in pending:
                col_a, col_b = st.columns([3, 1])
                col_a.info(f"User: {pt['user']} | Book: {pt['title']} (ID: {pt['bid']})")
                if col_b.button("Approve Return", key=f"app_{pt['bid']}"):
                    # Update transaction status
                    for t_record in db['transactions']:
                        if t_record['bid'] == pt['bid'] and t_record['status'] == "Pending Approval":
                            t_record['status'] = "Returned"
                    # Make book available
                    db['books'][pt['bid']]['status'] = "Available"
                    save_db(db)
                    st.rerun()
        else:
            st.write("No returns pending approval.")

# --- USER FUNCTIONS ---
def user_catalog():
    db = load_db()
    st.header("📖 Library Catalog")
    
    # Active Borrowed Count
    borrowed_count = len([t for t in db['transactions'] if t['user'] == st.session_state.user and t['status'] != 'Returned'])
    st.info(f"You have borrowed **{borrowed_count}/3** books.")

    books_list = []
    for bid, info in db['books'].items():
        books_list.append({"ISBN": bid, **info})
    
    if books_list:
        df = pd.DataFrame(books_list)
        st.dataframe(df, use_container_width=True)
        
        target_isbn = st.selectbox("Select ISBN to Borrow", df[df['status'] == 'Available']['ISBN'] if 'Available' in df['status'].values else ["None"])
        
        if st.button("Borrow / Reserve Book"):
            if target_isbn == "None":
                st.error("No books available.")
            elif borrowed_count >= 3:
                st.error("Limit Exceeded! Max 3 books allowed.")
            else:
                db['books'][target_isbn]['status'] = "Checked Out"
                db['transactions'].append({
                    "user": st.session_state.user, "bid": target_isbn, 
                    "title": db['books'][target_isbn]['title'], "status": "Borrowed"
                })
                save_db(db)
                st.success("Book issued!")
                st.rerun()

def my_shelf():
    db = load_db()
    st.header("📦 My Shelf")
    my_books = [t for t in db['transactions'] if t['user'] == st.session_state.user and t['status'] != 'Returned']
    
    if not my_books:
        st.write("Your shelf is empty.")
    else:
        for b in my_books:
            with st.container(border=True):
                st.write(f"**{b['title']}** (ISBN: {b['bid']})")
                st.write(f"Status: `{b['status']}`")
                if b['status'] == "Borrowed":
                    if st.button(f"Request Return for {b['bid']}", key=f"ret_{b['bid']}"):
                        for tr in db['transactions']:
                            if tr['bid'] == b['bid'] and tr['user'] == st.session_state.user:
                                tr['status'] = "Pending Approval"
                        save_db(db)
                        st.rerun()

# --- MAIN NAVIGATION ROUTER ---
if not st.session_state.logged_in:
    main_auth_page()
else:
    # RICH SIDEBAR
    with st.sidebar:
        st.markdown(f"### 🛡️ {st.session_state.user}")
        st.caption(f"Access Level: {st.session_state.role.upper()}")
        st.divider()
        
        nav_options = ["🏠 Dashboard", "📚 Book Catalog", "📦 My Shelf"]
        if st.session_state.role == 'admin':
            nav_options += ["🛠️ Admin Workspace"]
        
        choice = st.radio("MAIN MENU", nav_options)
        
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        if st.button("🚪 LOGOUT", type="secondary"):
            st.session_state.logged_in = False
            st.rerun()

    # CONTENT ROUTING
    try:
        if "Dashboard" in choice:
            st.title("System Overview")
            db = load_db()
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(f"<div class='metric-card'><h4>Books</h4><h2>{len(db['books'])}</h2></div>", unsafe_allow_html=True)
            with c2: st.markdown(f"<div class='metric-card'><h4>Users</h4><h2>{len(db['users'])}</h2></div>", unsafe_allow_html=True)
            with c3: st.markdown(f"<div class='metric-card'><h4>Transactions</h4><h2>{len(db['transactions'])}</h2></div>", unsafe_allow_html=True)
            st.image("https://images.unsplash.com/photo-1507842217343-583bb7270b66?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80", use_container_width=True)

        elif "Catalog" in choice:
            user_catalog()
        elif "Shelf" in choice:
            my_shelf()
        elif "Workspace" in choice:
            admin_panel()
            
    except Exception as e:
        st.error(f"System Exception: {e}")
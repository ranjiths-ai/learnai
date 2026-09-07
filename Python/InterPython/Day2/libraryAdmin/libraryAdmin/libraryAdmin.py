import streamlit as st
import json, os, pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# --- 1. CORE ENGINE & AI LOGIC ---
class LibraryOS:
    FILE = "library_db.json"
    
    def __init__(self):
        if not os.path.exists(self.FILE):
            self.data = {
                "books": [], 
                "members": [{"id":"M1","name":"admin","pass":"admin","books":[],"is_admin":True}]
            }
            self.save()
        else:
            with open(self.FILE, 'r') as f: self.data = json.load(f)

    def save(self):
        with open(self.FILE, 'w') as f: json.dump(self.data, f, indent=2)

    def get_member(self, name):
        return next((m for m in self.data['members'] if m['name'].lower() == name.lower()), None)

    def get_next_book_id(self):
        """Calculates the next auto-increment ID (BK-1, BK-2...)"""
        if not self.data['books']: return "BK-1"
        # Extract numeric parts from IDs like 'BK-10' -> 10
        ids = [int(b['id'].split('-')[-1]) for b in self.data['books'] if '-' in b['id']]
        return f"BK-{max(ids) + 1}" if ids else f"BK-{len(self.data['books']) + 1}"

    def ai_assistant(self, query):
        query = query.lower()
        books = self.data['books']
        if "how many" in query:
            return f"Total Books: {len(books)} | Available: {len([b for b in books if b['status']=='Available'])}"
        if "who has" in query:
            title = query.split("who has")[-1].strip()
            book = next((b for b in books if title in b['title'].lower()), None)
            if book and book['is_borrowed']:
                user = next(m['name'] for m in self.data['members'] if book['id'] in m['books'])
                return f"'{book['title']}' is currently with {user}."
        return "Ask me: 'How many books?' or 'Who has [title]?'"

# --- 2. PRO UI STYLING ---
def apply_3d_style():
    st.markdown("""
        <style>
        .stApp { background: #e0e5ec; }
        .card {
            border-radius: 15px; background: #e0e5ec;
            box-shadow: 8px 8px 15px #bebebe, -8px -8px 15px #ffffff;
            padding: 20px; margin-bottom: 20px;
        }
        .stButton>button {
            border-radius: 10px; background: #e0e5ec;
            box-shadow: 4px 4px 8px #bebebe, -4px -4px 8px #ffffff;
            transition: 0.2s; border: none;
        }
        .stButton>button:hover { transform: translateY(-2px); box-shadow: 6px 6px 12px #bebebe, -6px -6px 12px #ffffff; }
        </style>
    """, unsafe_allow_html=True)

# --- 3. APP INITIALIZATION ---
lib = LibraryOS()
apply_3d_style()

if 'user' not in st.session_state: st.session_state.user = None

# --- SIDEBAR: AUTHENTICATION ---
with st.sidebar:
    st.title("🛡️ Access Control")
    mode = st.radio("Mode", ["Sign In", "New Account"])
    u_name = st.text_input("Username").strip()
    u_pass = st.text_input("Password", type="password")
    
    if mode == "New Account":
        if u_name and lib.get_member(u_name): st.error("User exists")
        if st.button("Register") and u_name and not lib.get_member(u_name):
            lib.data['members'].append({"id": f"M{len(lib.data['members'])+1}", "name": u_name, "pass": u_pass, "books": [], "is_admin": False})
            lib.save(); st.success("Created! Please Login.")
    else:
        if st.button("Login"):
            user = lib.get_member(u_name)
            if user and user['pass'] == u_pass:
                st.session_state.user = user
                st.rerun()
            else: st.error("Fail")

    if st.session_state.user:
        if st.button("Logout"): 
            st.session_state.user = None
            st.rerun()

# --- MAIN DASHBOARD ---
if st.session_state.user:
    u = st.session_state.user
    is_admin = u.get('is_admin', False)

    # AI Section
    with st.expander("🤖 Smart AI Assistant", expanded=True):
        aq = st.text_input("Ask about inventory:", placeholder="e.g. How many books?")
        if aq: st.info(lib.ai_assistant(aq))

    t1, t2, t3 = st.tabs(["📊 Inventory", "🎒 My Shelf", "⚙️ Admin"] if is_admin else ["📊 Inventory", "🎒 My Shelf", "🔒 Restricted"])

    # TAB 1: INVENTORY & CHART
    with t1:
        if lib.data['books']:
            df = pd.DataFrame(lib.data['books'])
            c1, c2 = st.columns([1, 2])
            c1.metric("Books", len(df))
            with c2:
                fig = px.pie(df, names='status', hole=0.5, height=200)
                fig.update_layout(margin=dict(l=0,r=0,b=0,t=0), paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig, use_container_width=True)
            
            st.subheader("Available Collection")
            avail = [b for b in lib.data['books'] if b['status'] == "Available"]
            if avail:
                st.dataframe(pd.DataFrame(avail)[['id', 'title', 'author']], hide_index=True, use_container_width=True)
                sel_id = st.selectbox("Borrow Book ID", [b['id'] for b in avail])
                if st.button("Confirm Borrow"):
                    m_ref = next(m for m in lib.data['members'] if m['id'] == u['id'])
                    if len(m_ref['books']) < 3:
                        b_ref = next(b for b in lib.data['books'] if b['id'] == sel_id)
                        b_ref.update({"status": "Borrowed", "is_borrowed": True, "due": (datetime.now()+timedelta(days=21)).strftime('%Y-%m-%d')})
                        m_ref['books'].append(sel_id)
                        lib.save(); st.success("Borrowed!"); st.rerun()
                    else: st.error("Limit Reached")
        else: st.info("No books in library.")

    # TAB 2: USER SHELF
    with t2:
        m_ref = next(m for m in lib.data['members'] if m['id'] == u['id'])
        my_books = [b for b in lib.data['books'] if b['id'] in m_ref['books']]
        if my_books:
            for b in my_books:
                st.markdown(f"<div class='card'><b>{b['title']}</b><br>ID: {b['id']} | Status: {b['status']}</div>", unsafe_allow_html=True)
                if b['status'] == "Borrowed":
                    if st.button(f"Return {b['id']}", key=f"r{b['id']}"):
                        b['status'] = "Pending Approval"
                        lib.save(); st.rerun()
        else: st.write("Empty shelf")

    # TAB 3: ADMIN (Auto-Increment logic here)
    if is_admin:
        with t3:
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("📥 Return Approvals")
                pending = [b for b in lib.data['books'] if b['status'] == "Pending Approval"]
                for p in pending:
                    if st.button(f"Approve {p['id']}"):
                        owner = next(m for m in lib.data['members'] if p['id'] in m['books'])
                        owner['books'].remove(p['id'])
                        p.update({"status":"Available", "is_borrowed": False, "due": None})
                        lib.save(); st.rerun()
            
            with col_b:
                st.subheader("➕ Register Book")
                next_id = lib.get_next_book_id()
                st.info(f"Assigning ID: **{next_id}**") # Auto-increment displayed
                nt = st.text_input("Title")
                na = st.text_input("Author")
                if st.button("Save Book") and nt:
                    lib.data['books'].append({
                        "id": next_id, "title": nt, "author": na, 
                        "status": "Available", "is_borrowed": False
                    })
                    lib.save(); st.success(f"Book {next_id} Registered!"); st.rerun()
            
            st.divider()
            if st.button("💾 Export Inventory"):
                csv = pd.DataFrame(lib.data['books']).to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "library.csv", "text/csv")
else:
    st.markdown("<div class='card' style='text-align:center;'><h1>Welcome to Library OS</h1><p>Please use the sidebar to access your account.</p></div>", unsafe_allow_html=True)
"""
Streamlit Front-End for Library Management System
Includes pre-login registration, password authentication, input field resets, and role-based navigation.
"""

import streamlit as st
import requests
import pandas as pd
from typing import Optional, Dict, Any

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Library Management System",
    page_icon="📚",
    layout="wide"
)

# Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user" not in st.session_state:
    st.session_state["user"] = None

# Initialize form field state keys
defaults = {
    "login_uid": "",
    "login_pwd": "",
    "reg_name": "",
    "reg_email": "",
    "reg_pwd": "",
    "reg_confirm": "",
    "reg_phone": "",
    "reg_role": "patron",
    "book_isbn": "",
    "book_title": "",
    "book_author": "",
    "book_copies": 1,
    "book_category": "General",
    "book_year": 2024,
    "book_tags": "",
    "chk_uid": "",
    "chk_isbn": "",
    "ret_lid": "",
    "res_uid": "",
    "res_isbn": ""
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


def apply_pending_form_resets():
    pending_resets = {
        "reset_register_form_pending": reset_register_form,
        "reset_book_form_pending": reset_book_form,
        "reset_circulation_forms_pending": reset_circulation_forms,
    }
    for key, reset_callback in pending_resets.items():
        if st.session_state.pop(key, False):
            reset_callback()


# =====================================================================
# RESET CALLBACKS
# =====================================================================

def reset_login_form():
    st.session_state["login_uid"] = ""
    st.session_state["login_pwd"] = ""

def reset_register_form():
    st.session_state["reg_name"] = ""
    st.session_state["reg_email"] = ""
    st.session_state["reg_pwd"] = ""
    st.session_state["reg_confirm"] = ""
    st.session_state["reg_phone"] = ""
    st.session_state["reg_role"] = "patron"

def reset_book_form():
    st.session_state["book_isbn"] = ""
    st.session_state["book_title"] = ""
    st.session_state["book_author"] = ""
    st.session_state["book_copies"] = 1
    st.session_state["book_category"] = "General"
    st.session_state["book_year"] = 2024
    st.session_state["book_tags"] = ""

def reset_circulation_forms():
    st.session_state["chk_uid"] = ""
    st.session_state["chk_isbn"] = ""
    st.session_state["ret_lid"] = ""
    st.session_state["res_uid"] = ""
    st.session_state["res_isbn"] = ""


apply_pending_form_resets()


# =====================================================================
# API CALL WRAPPERS
# =====================================================================

def api_get(endpoint: str, params: Optional[Dict[str, Any]] = None):
    try:
        res = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=5)
        if res.status_code == 200:
            return res.json(), None
        return None, res.json().get("detail", res.text)
    except Exception as e:
        return None, f"Connection error: {e}"

def api_post(endpoint: str, payload: Dict[str, Any]):
    try:
        res = requests.post(f"{API_BASE}{endpoint}", json=payload, timeout=5)
        if res.status_code in (200, 201):
            return res.json(), None
        return None, res.json().get("detail", res.text)
    except Exception as e:
        return None, f"Connection error: {e}"

def api_patch(endpoint: str, payload: Dict[str, Any]):
    try:
        res = requests.patch(f"{API_BASE}{endpoint}", json=payload, timeout=5)
        if res.status_code == 200:
            return res.json(), None
        return None, res.json().get("detail", res.text)
    except Exception as e:
        return None, f"Connection error: {e}"


# =====================================================================
# PRE-LOGIN GATEWAY (LOGIN & REGISTRATION ONLY)
# =====================================================================

if not st.session_state["authenticated"]:
    # Sidebar is intentionally not rendered here
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>📚 Library Management System</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Sign in or register a new user account below.</p>", unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Register New User"])

        # --- TAB 1: LOGIN ---
        with tab_login:
            st.text_input("User ID or Registered Email", key="login_uid")
            st.text_input("Password", type="password", key="login_pwd")

            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                login_btn = st.button("Sign In", type="primary", width="stretch")
            with btn_col2:
                st.button("Reset Fields 🔄", on_click=reset_login_form, width="stretch")

            if login_btn:
                uid = st.session_state["login_uid"].strip()
                pwd = st.session_state["login_pwd"]
                if not uid or not pwd:
                    st.error("Please enter both User ID/Email and Password.")
                else:
                    data, err = api_post("/auth/login", {"user_id": uid, "password": pwd})
                    if err:
                        st.error(f"Sign In Failed: {err}")
                    else:
                        st.session_state["authenticated"] = True
                        st.session_state["user"] = data
                        st.success(f"Welcome, {data['name']}!")
                        st.rerun()

            st.markdown("---")
            st.info("💡 **Pre-seeded Demo Credentials**:\n- **Admin:** `A001` (Password: `admin123`)\n- **Patron:** `U0001` (Password: `patron123`)")

        # --- TAB 2: REGISTER NEW USER ---
        with tab_register:
            st.subheader("Create a New Account")
            st.text_input("Full Name", key="reg_name")
            st.text_input("Email Address", key="reg_email")
            st.text_input("Password", type="password", key="reg_pwd")
            st.text_input("Confirm Password", type="password", key="reg_confirm")
            st.text_input("Phone (Optional)", key="reg_phone")
            st.selectbox("Account Role", ["patron", "admin"], key="reg_role")

            reg_col1, reg_col2 = st.columns(2)
            with reg_col1:
                register_btn = st.button("Register User", type="primary", width="stretch")
            with reg_col2:
                st.button("Reset Registration 🔄", on_click=reset_register_form, width="stretch")

            if register_btn:
                name = st.session_state["reg_name"].strip()
                email = st.session_state["reg_email"].strip()
                pwd = st.session_state["reg_pwd"]
                confirm = st.session_state["reg_confirm"]
                phone = st.session_state["reg_phone"].strip() or None
                role = st.session_state["reg_role"]

                if not name or not email or not pwd:
                    st.error("Name, Email, and Password are required.")
                elif pwd != confirm:
                    st.error("Passwords do not match.")
                else:
                    payload = {
                        "name": name,
                        "email": email,
                        "password": pwd,
                        "role": role,
                        "phone": phone
                    }
                    data, err = api_post("/users", payload)
                    if err:
                        st.error(f"Registration Error: {err}")
                    else:
                        st.success(f"Account created successfully! Assigned User ID: **{data['user_id']}**")
                        st.info("You can now switch to the 'Sign In' tab to log in.")
                        st.session_state["reset_register_form_pending"] = True
                        st.rerun()

    # Strict boundary: stop execution so no sidebar/menu is rendered without login
    st.stop()


# =====================================================================
# POST-LOGIN: SIDEBAR NAVIGATION & APPLICATION WORKSPACES
# =====================================================================

user = st.session_state["user"]
is_admin = user.get("role") == "admin"

st.sidebar.markdown(f"### 👤 {user['name']}")
role_badge = "🛡️ Administrator" if is_admin else "📖 Patron"
st.sidebar.markdown(f"**ID:** `{user['user_id']}` | **Role:** {role_badge}")

if st.sidebar.button("Log Out", width="stretch"):
    st.session_state["authenticated"] = False
    st.session_state["user"] = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### Navigation Menu")

menu_options = ["User & Account Management", "Catalog & Inventory", "Circulation (Checkout & Hold)"]

if is_admin:
    menu_options.extend([
        "Admin Return Inspection & Fines",
        "System Reports & Analytics",
        "Backup System State"
    ])
else:
    menu_options.append("My Notifications & Holds")

selected_menu = st.sidebar.radio("Go to:", menu_options)


# =====================================================================
# 1. USER & ACCOUNT MANAGEMENT
# =====================================================================

if selected_menu == "User & Account Management":
    st.title("👥 User & Account Management")

    if is_admin:
        tab1, tab2, tab3 = st.tabs(["Register User", "Block/Unblock Patron", "Directory"])

        with tab1:
            st.subheader("Register New User (Admin Console)")
            st.text_input("Full Name", key="reg_name")
            st.text_input("Email Address", key="reg_email")
            st.text_input("Password", type="password", key="reg_pwd")
            st.text_input("Phone (Optional)", key="reg_phone")
            st.selectbox("Role", ["patron", "admin"], key="reg_role")

            c1, c2 = st.columns(2)
            with c1:
                btn_create = st.button("Create Account", type="primary", width="stretch")
            with c2:
                st.button("Reset Form 🔄", on_click=reset_register_form, width="stretch")

            if btn_create:
                payload = {
                    "name": st.session_state["reg_name"],
                    "email": st.session_state["reg_email"],
                    "password": st.session_state["reg_pwd"],
                    "role": st.session_state["reg_role"],
                    "phone": st.session_state["reg_phone"] or None
                }
                res, err = api_post("/users", payload)
                if err:
                    st.error(err)
                else:
                    st.success(f"User created: {res['name']} (ID: {res['user_id']})")
                    st.session_state["reset_register_form_pending"] = True
                    st.rerun()

        with tab2:
            st.subheader("Manage Patron Block Status")
            target_uid = st.text_input("Target User ID (e.g. U0001)")
            blocked_status = st.radio("Status", [False, True], format_func=lambda x: "Blocked" if x else "Active")
            if st.button("Update Account Status"):
                res, err = api_patch(f"/users/{target_uid}/block", {
                    "admin_user_id": user["user_id"],
                    "blocked": blocked_status
                })
                if err:
                    st.error(err)
                else:
                    st.success(f"Status for {res['user_id']} updated to: {'BLOCKED' if res['is_blocked'] else 'ACTIVE'}")

        with tab3:
            st.subheader("Registered Users Directory")
            users, err = api_get("/users")
            if users:
                df = pd.DataFrame(users)[["user_id", "role", "name", "email", "phone", "is_blocked"]]
                st.dataframe(df, width="stretch")
            elif err:
                st.error(err)
    else:
        st.subheader("My Profile Information")
        st.write(f"**User ID:** `{user['user_id']}`")
        st.write(f"**Name:** {user['name']}")
        st.write(f"**Email:** {user['email']}")
        st.write(f"**Role:** {user['role'].capitalize()}")
        st.write(f"**Status:** {'Blocked' if user.get('is_blocked') else 'Active'}")


# =====================================================================
# 2. CATALOG & INVENTORY MANAGEMENT
# =====================================================================

elif selected_menu == "Catalog & Inventory":
    st.title("📚 Catalog & Inventory Management")

    if is_admin:
        tab1, tab2, tab3 = st.tabs(["Catalog Inventory", "Add New Book", "Stock Copies"])

        with tab1:
            books, err = api_get("/books")
            if books:
                df = pd.DataFrame(books)[["isbn", "title", "author", "available_copies", "total_copies", "category", "published_year"]]
                st.dataframe(df, width="stretch")
            elif err:
                st.error(err)

        with tab2:
            st.subheader("Add Book to Catalog")
            st.text_input("ISBN (10 or 13 digits)", key="book_isbn")
            st.text_input("Book Title", key="book_title")
            st.text_input("Author", key="book_author")
            st.number_input("Total Copies", min_value=1, key="book_copies")
            st.text_input("Category / Genre", key="book_category")
            st.number_input("Published Year", min_value=1000, max_value=2026, key="book_year")
            st.text_input("Tags (comma separated)", key="book_tags")

            c1, c2 = st.columns(2)
            with c1:
                btn_book = st.button("Catalog Book", type="primary", width="stretch")
            with c2:
                st.button("Reset Fields 🔄", on_click=reset_book_form, width="stretch")

            if btn_book:
                tags = [t.strip() for t in st.session_state["book_tags"].split(",") if t.strip()]
                payload = {
                    "admin_user_id": user["user_id"],
                    "isbn": st.session_state["book_isbn"],
                    "title": st.session_state["book_title"],
                    "author": st.session_state["book_author"],
                    "total_copies": int(st.session_state["book_copies"]),
                    "category": st.session_state["book_category"],
                    "published_year": int(st.session_state["book_year"]),
                    "tags": tags
                }
                res, err = api_post("/books", payload)
                if err:
                    st.error(err)
                else:
                    st.success(f"Added '{res['title']}' (ISBN: {res['isbn']})!")
                    st.session_state["reset_book_form_pending"] = True
                    st.rerun()

        with tab3:
            st.subheader("Update Inventory Stock")
            target_isbn = st.text_input("Book ISBN", key="update_isbn")
            adjust_copies = st.number_input("Additional Copies (+ add / - reduce)", value=1, step=1)
            if st.button("Apply Stock Adjustment"):
                res, err = api_patch(f"/books/{target_isbn}/copies", {
                    "admin_user_id": user["user_id"],
                    "additional_copies": int(adjust_copies)
                })
                if err:
                    st.error(err)
                else:
                    st.success(f"Updated '{res['title']}'! Now available: {res['available_copies']}/{res['total_copies']}")
    else:
        st.subheader("Library Catalog")
        books, err = api_get("/books")
        if books:
            df = pd.DataFrame(books)[["isbn", "title", "author", "available_copies", "category", "published_year"]]
            st.dataframe(df, width="stretch")
        elif err:
            st.error(err)


# =====================================================================
# 3. CIRCULATION: CHECKOUT & RESERVATIONS
# =====================================================================

elif selected_menu == "Circulation (Checkout & Hold)":
    st.title("🔄 Circulation: Checkout, Return & Holds")

    tab1, tab2, tab3, tab4 = st.tabs(["Checkout Book", "Request Return", "Place Hold / Reservation", "Status Queue"])

    with tab1:
        st.subheader("Book Checkout (< 60 Days Duration)")
        chk_uid = user["user_id"] if not is_admin else st.text_input("Patron User ID", key="chk_uid")
        st.text_input("Book ISBN", key="chk_isbn")
        loan_days = st.slider("Duration (Days)", min_value=1, max_value=59, value=14)

        c1, c2 = st.columns(2)
        with c1:
            btn_chk = st.button("Complete Checkout", type="primary", width="stretch")
        with c2:
            st.button("Reset 🔄", on_click=reset_circulation_forms, width="stretch")

        if btn_chk:
            res, err = api_post("/loans", {
                "user_id": chk_uid or user["user_id"],
                "isbn": st.session_state["chk_isbn"],
                "loan_days": loan_days
            })
            if err:
                st.error(err)
            else:
                st.success(f"Success! Loan ID: {res['loan_id']} | Due Date: {res['due_date']}")
                st.session_state["reset_circulation_forms_pending"] = True
                st.rerun()

    with tab2:
        st.subheader("Request Book Return")
        st.text_input("Loan ID (e.g. LN-00001)", key="ret_lid")
        
        c1, c2 = st.columns(2)
        with c1:
            btn_ret = st.button("Submit Return for Review", type="primary", width="stretch")
        with c2:
            st.button("Reset Loan ID 🔄", on_click=reset_circulation_forms, width="stretch")

        if btn_ret:
            res, err = api_post(f"/loans/{st.session_state['ret_lid']}/return", {})
            if err:
                st.error(err)
            else:
                st.success(f"Return submitted for Loan '{res['loan_id']}' (Status: PENDING_APPROVAL)")
                st.session_state["reset_circulation_forms_pending"] = True
                st.rerun()

    with tab3:
        st.subheader("Place Reservation on Out-of-Stock Books")
        res_uid = user["user_id"] if not is_admin else st.text_input("Patron User ID", key="res_uid")
        st.text_input("Out-of-Stock Book ISBN", key="res_isbn")

        c1, c2 = st.columns(2)
        with c1:
            btn_res = st.button("Place Reservation", type="primary", width="stretch")
        with c2:
            st.button("Reset Hold Fields 🔄", on_click=reset_circulation_forms, width="stretch")

        if btn_res:
            res, err = api_post("/reservations", {
                "user_id": res_uid or user["user_id"],
                "isbn": st.session_state["res_isbn"]
            })
            if err:
                st.error(err)
            else:
                st.success(f"Reservation confirmed! Hold ID: {res['reservation_id']}")
                st.session_state["reset_circulation_forms_pending"] = True
                st.rerun()

    with tab4:
        st.subheader("Circulation Status")
        loans_param = None if is_admin else {"user_id": user["user_id"]}
        loans, _ = api_get("/loans", params=loans_param)
        if loans:
            st.markdown("#### Loans")
            st.dataframe(pd.DataFrame(loans), width="stretch")

        resvs, _ = api_get("/reservations", params=loans_param)
        if resvs:
            st.markdown("#### Holds / Reservations")
            st.dataframe(pd.DataFrame(resvs), width="stretch")


# =====================================================================
# 4. ADMIN RETURN INSPECTION & FINES (ADMIN ONLY)
# =====================================================================

elif selected_menu == "Admin Return Inspection & Fines":
    st.title("🛡️ Admin Return Inspection & Fine Assessment")

    loans, _ = api_get("/loans")
    pending = [l for l in (loans or []) if l.get("return_status") == "PENDING_APPROVAL"]

    if not pending:
        st.info("No returns currently pending inspection.")
    else:
        st.subheader(f"Pending Inspection Queue ({len(pending)})")
        st.dataframe(pd.DataFrame(pending), width="stretch")

        selected_loan_id = st.selectbox("Select Loan ID to Approve", [l["loan_id"] for l in pending])
        is_damaged = st.checkbox("Book is Damaged")
        damage_fee = st.number_input("Damage Assessment Fee ($)", min_value=0.0, value=0.0, step=1.0)
        
        if st.button("Finalize and Approve Return", type="primary"):
            payload = {
                "admin_user_id": user["user_id"],
                "damaged": is_damaged,
                "damage_fee": damage_fee
            }
            res, err = api_post(f"/loans/{selected_loan_id}/approve", payload)
            if err:
                st.error(err)
            else:
                st.success(f"Return approved for Loan {res['loan_id']}! Total Fine Assessed: ${res['fine_amount']:.2f}")


# =====================================================================
# 5. SYSTEM REPORTS & ANALYTICS
# =====================================================================

elif selected_menu == "System Reports & Analytics":
    st.title("📊 System Reports & Analytics")

    report, err = api_get("/reports/latest")
    if err:
        st.error(err)
    elif report:
        st.caption(f"Generated At: {report['generated_at']} (Report ID: {report['report_id']})")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Users", report["total_users"])
        m2.metric("Catalog Titles", report["total_titles"])
        m3.metric("Physical Copies", report["total_copies"])
        m4.metric("Active Loans", report["active_loans"])

        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Pending Returns", report["pending_returns"])
        m6.metric("Overdue Loans", report["overdue_loans"])
        m7.metric("Active Holds", report["active_reservations"])
        m8.metric("Total Fines", f"${report['total_fines_assessed']:.2f}")


# =====================================================================
# 6. BACKUP SYSTEM STATE (ADMIN ONLY)
# =====================================================================

elif selected_menu == "Backup System State":
    st.title("💾 System State Backup")
    st.write("Export full in-memory system catalog, users, loans, and auto-increment sequences to JSON.")

    if st.button("Trigger Snapshot Backup", type="primary"):
        res, err = api_post("/backup", {"admin_user_id": user["user_id"]})
        if err:
            st.error(err)
        else:
            st.success(f"System state successfully saved to `{res['path']}`!")


# =====================================================================
# 7. NOTIFICATIONS (PATRON ONLY)
# =====================================================================

elif selected_menu == "My Notifications & Holds":
    st.title("🔔 Notifications & Holds")
    
    current_user_data, _ = api_get(f"/users/{user['user_id']}")
    notifications = current_user_data.get("notifications", []) if current_user_data else []

    if notifications:
        for notif in reversed(notifications):
            st.info(notif)
    else:
        st.write("No notifications at this time.")
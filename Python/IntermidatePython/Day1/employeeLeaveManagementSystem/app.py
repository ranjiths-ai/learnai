import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

# Configuration
JSON_FILE = 'employees.json'

def load_data():
    if not os.path.exists(JSON_FILE):
        # Seed with initial structure if empty
        with open(JSON_FILE, 'w') as f:
            json.dump({"employees": [], "leave_requests": []}, f, indent=4)
    try:
        with open(JSON_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"employees": [], "leave_requests": []}

def save_data(data):
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# Initialize application data
data = load_data()

st.set_page_config(page_title="Employee Leave Management System", layout="wide")
st.title("💼 Employee Leave Management System")

# Navigation Menu - left sidebar, modern icon-based layout
menu = [
    ("📝 Employee Register", "register"),
    ("👥 View Employees", "view_employees"),
    ("🔎 Search Employees", "search_employees"),
    ("📅 Apply Leave", "apply_leave"),
    ("📊 Check Leave Balance", "check_leave_balance"),
    ("🛡️ View Leave Requests", "view_leave_requests"),
    ("📈 Interactive Dashboard", "dashboard"),
    ("🤖 Chatbot Assistant UI", "chatbot"),
    ("🚀 Demo Deployment Guide", "deployment_guide"),
]

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "register"

st.sidebar.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;
        justify-content: flex-start;
        padding: 0.7rem 0.9rem;
        border-radius: 10px;
        border: 1px solid rgba(148, 163, 184, 0.2);
        background: rgba(15, 23, 42, 0.25);
        color: #e2e8f0;
        margin: 0.25rem 0;
        font-weight: 600;
        font-size: 0.96rem;
        transition: 0.2s ease;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        border-color: rgba(96, 165, 250, 0.8);
        background: rgba(30, 41, 59, 0.9);
        transform: translateX(2px);
    }
    [data-testid="stSidebar"] .stButton > button:focus {
        box-shadow: 0 0 0 0.2rem rgba(96, 165, 250, 0.25);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("## Navigation")
for label, key in menu:
    if st.sidebar.button(label, key=f"nav_{key}", use_container_width=True):
        st.session_state.selected_page = key

choice = st.session_state.selected_page

# Helper to clear registration session state
def reset_registration_form():
    st.session_state['reg_first_name'] = ""
    st.session_state['reg_last_name'] = ""
    st.session_state['reg_phone'] = ""
    st.session_state['reg_address'] = ""
    st.session_state['reg_leaves'] = 20
    if 'reg_dob' in st.session_state:
        st.session_state['reg_dob'] = datetime(1995, 1, 1)
    if 'reg_doj' in st.session_state:
        st.session_state['reg_doj'] = datetime.today()
    
    st.text_input("First Name", key="reg_first_name")

# ----------------- a) Employee Register -----------------
if choice == "register":
    st.header("📋 Enter Employee Details")

    # Auto-increment calculation
    next_id = max([emp['employeeid'] for emp in data['employees']], default=1000) + 1
    st.info(f"Generated Employee ID: **{next_id}**")

    # Form layout
    with st.form("registration_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name", key="reg_first_name")
            last_name = st.text_input("Last Name", key="reg_last_name")
            dob = st.date_input("Date of Birth", value=datetime(1995, 1, 1), key="reg_dob")
        with col2:
            phone = st.text_input("Phone Number", key="reg_phone")
            doj = st.date_input("Date of Joining", value=datetime.today(), key="reg_doj")
            total_leaves = st.number_input("Total Eligible Leaves", min_value=0, value=20, key="reg_leaves")

        address = st.text_area("Address", key="reg_address")

        button_col1, button_col2 = st.columns(2)
        with button_col1:
            submit_btn = st.form_submit_button("Submit", use_container_width=True)
        with button_col2:
            reset_btn = st.form_submit_button("Reset Form Fields", use_container_width=True)

    if reset_btn:
        reset_registration_form()
        st.rerun()

    if submit_btn:
        if not first_name or not last_name:
            st.error("First and Last name are required fields.")
        else:
            new_emp = {
                "employeeid": next_id,
                "first_name": first_name,
                "last_name": last_name,
                "dob": str(dob),
                "phone_number": phone,
                "dateof_join": str(doj),
                "total_leaves": total_leaves,
                "pending_leaves": total_leaves,
                "address": address,
            }
            data['employees'].append(new_emp)
            save_data(data)
            st.success(f"Successfully registered {first_name} {last_name}!")

# ----------------- b) View Employees -----------------
elif choice == "view_employees":
    st.header("👥 View Registered Employees")
    if data['employees']:
        df = pd.DataFrame(data['employees'])
        st.dataframe(df, use_container_width=True)
        
        # CSV Export functionality
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Employees to CSV",
            data=csv,
            file_name='employees_export.csv',
            mime='text/csv',
        )
    else:
        st.warning("No employee profiles found in the record.")

# ----------------- c) Search Employees -----------------
elif choice == "search_employees":
    st.header("🔍 Search Employee Profiles")
    
    search_query = st.text_input("Search by First Name, Last Name, or Employee ID")
    search_btn = st.button("Search")
    
    if search_query or search_btn:
        results = []
        for emp in data['employees']:
            if (search_query.lower() in emp['first_name'].lower() or 
                search_query.lower() in emp['last_name'].lower() or 
                search_query == str(emp['employeeid'])):
                results.append(emp)
                
        if results:
            for match in results:
                st.write("---")
                st.markdown(f"### Employee Profile: {match['first_name']} {match['last_name']} (ID: {match['employeeid']})")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**DOB:** {match['dob']}")
                    st.write(f"**Phone:** {match['phone_number']}")
                    st.write(f"**Address:** {match['address']}")
                with col2:
                    st.write(f"**Date of Join:** {match['dateof_join']}")
                    st.write(f"**Total Leaves:** {match['total_leaves']}")
                    st.write(f"**Pending Balance:** {match['pending_leaves']}")
                
                # Context transition button
                if st.button(f"Apply Leave for ID {match['employeeid']}", key=f"apply_{match['employeeid']}"):
                    st.session_state['searched_emp_id'] = match['employeeid']
                    st.session_state.selected_page = "apply_leave"
                    st.success("Redirecting to the leave request module...")
                    st.rerun()
        else:
            st.error("No employee profiles match your search criteria.")

# ----------------- d) Apply Leave -----------------
elif choice == "apply_leave":
    st.header("📅 File Leave Request")
    
    # Pre-populate search query if passed from search screen
    default_search = str(st.session_state.get('searched_emp_id', ''))
    target_id = st.text_input("Enter Target Employee ID to Fetch Balance", value=default_search)
    
    if target_id:
        emp_match = next((emp for emp in data['employees'] if str(emp['employeeid']) == target_id), None)
        
        if emp_match:
            st.markdown(f"#### Account Details: {emp_match['first_name']} {emp_match['last_name']}")
            st.info(f"**Total Allocation:** {emp_match['total_leaves']} days | **Remaining Balance:** {emp_match['pending_leaves']} days")
            
            with st.form("leave_submission_form"):
                leave_days = st.number_input("Requested Leave Units", min_value=1, max_value=100, value=1)
                reason = st.text_input("Reason / Justification")
                submit_leave = st.form_submit_button("Submit Request")
                
            if submit_leave:
                if leave_days > emp_match['pending_leaves']:
                    st.error(f"Transaction Denied: Leave volume exceeds current balance allocation ({emp_match['pending_leaves']}).")
                else:
                    new_request = {
                        "request_id": len(data.get('leave_requests', [])) + 1,
                        "employeeid": emp_match['employeeid'],
                        "name": f"{emp_match['first_name']} {emp_match['last_name']}",
                        "requested_days": leave_days,
                        "reason": reason,
                        "status": "Pending"
                    }
                    if 'leave_requests' not in data:
                        data['leave_requests'] = []
                    data['leave_requests'].append(new_request)
                    save_data(data)
                    st.success("Your request has been queued for admin verification.")
        else:
            st.error("Target Employee identification identifier not verified.")

# ----------------- e) Check Leave Balance -----------------
elif choice == "check_leave_balance":
    st.header("📊 Complete Fleet Leave Balances")
    if data['employees']:
        df = pd.DataFrame(data['employees'])
        balance_df = df[['employeeid', 'first_name', 'last_name', 'total_leaves', 'pending_leaves']]
        st.dataframe(balance_df, use_container_width=True)
    else:
        st.warning("No allocation matrices exist. Populate database files first.")

# ----------------- f) View Leave Requests -----------------
elif choice == "view_leave_requests":
    st.header("🛡️ Administrative Leave Verification Portal")
    requests = data.get('leave_requests', [])
    
    if not requests:
        st.info("No actionable or archived leave requests exist currently.")
    else:
        for idx, req in enumerate(requests):
            if req['status'] == "Pending":
                st.write("---")
                st.markdown(f"##### Action Required: Request ID #{req['request_id']} — {req['name']}")
                st.write(f"**Requested Units:** {req['requested_days']} days | **Context:** {req['reason']}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve", key=f"app_{idx}"):
                        # Find employee and deduct allocation
                        emp = next((e for e in data['employees'] if e['employeeid'] == req['employeeid']), None)
                        if emp:
                            if emp['pending_leaves'] >= req['requested_days']:
                                emp['pending_leaves'] -= req['requested_days']
                                req['status'] = "Approved"
                                save_data(data)
                                st.success("Approved and balances compiled!")
                                st.rerun()
                            else:
                                st.error("Insufficient leaf account balance at execution window.")
                with col2:
                    if st.button("Reject", key=f"rej_{idx}"):
                        req['status'] = "Rejected"
                        save_data(data)
                        st.warning("Request rejected.")
                        st.rerun()
                        
        st.write("---")
        st.subheader("Archived Metrics Logs")
        df_req = pd.DataFrame(requests)
        st.dataframe(df_req[df_req['status'] != "Pending"], use_container_width=True)

# ----------------- Interactive Dashboard -----------------
elif choice == "dashboard":
    st.header("📊 Analytical Metrics Dashboard")
    if data['employees']:
        df = pd.DataFrame(data['employees'])
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Allocated vs Remaining Metrics")
            st.bar_chart(df.set_index('first_name')[['total_leaves', 'pending_leaves']])
        with col2:
            st.subheader("Fleet Aggregations")
            st.metric("Total Workforce Matched", len(df))
            st.metric("Aggregate Outstanding Balances", int(df['pending_leaves'].sum()))
    else:
        st.warning("Populate fields to initialize visualization data elements.")

# ----------------- Chatbot UI -----------------
elif choice == "chatbot":
    st.header("🤖 Human Resources Automated Concierge")
    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I assist you with leave rules or checking system criteria today?"}]
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    if prompt := st.chat_input("Ask about company leave tracking updates..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
        # Simulating localized intelligent parsing
        response = f"I've logged your observation about '{prompt}'. To pull records directly, navigate to the targeted tracking tabs in the left sidebar menu matrix panels."
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.write(response)

# ----------------- Demo Deployment Guide -----------------
elif choice == "deployment_guide":
    st.header("🚀 Deploying a Quick Demonstration Instance")
    st.markdown('''
    ### Production Environments & Prototyping
    To publish this application into a live demo for team staging:
    
    1. **GitHub Repository Structure**
       Ensure your folder features exactly these files:
       ```text
       ├── app.py              # This source application file
       ├── requirements.txt    # Library packages manifest
       └── employees.json      # Structured persistent system storage
       ```
    2. **Write your requirements.txt dependency file:**
       ```text
       streamlit>=1.30.0
       pandas>=2.0.0
       ```
    3. **Cloud Service Staging Deployment**
       * Connect your cloud account onto the **Streamlit Community Cloud** orchestration portal.
       * Select your code repository path and press **Deploy App**.
       * Your workflow runs interactively over a secure accessible web url link!
    ''')
# ====================================================
# 📦 Imports
# ====================================================
import streamlit as st
import pymongo
from datetime import datetime
import pandas as pd
import plotly.express as px


# ====================================================
# 🌐 MongoDB Connection
# ====================================================
MONGO_URI = "mongodb+srv://praveenkumar97213_db_user:Praveen%402005@user.bqzpob3.mongodb.net/Telecomdb?retryWrites=true&w=majority&appName=User"

client = pymongo.MongoClient(MONGO_URI)
db = client["BroadbandDB"]

users_collection = db["users"]
plans_collection = db["plans"]
customers_collection = db["CustomerPlans"]


# ====================================================
# 👑 Default Admin Creation
# ====================================================
def create_default_admin():
    if not users_collection.find_one({"email": "admin@portal.com"}):
        users_collection.insert_one({
            "name": "Super Admin",
            "email": "admin@portal.com",
            "password": "admin@123",   # ⚠ In real apps, hash passwords!
            "role": "admin",
            "approved": True,
            "created_at": datetime.now()
        })


create_default_admin()


# ====================================================
# 🗂️ Session State Initialization
# ====================================================
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "auth"  # 'auth' OR 'dashboard'

# Flash message storage
if "flash" not in st.session_state:
    st.session_state.flash = None


# ====================================================
# 🔑 Authentication Functions (Signup & Login)
# ====================================================
def signup(name, email, password):
    """Register a new customer"""
    if users_collection.find_one({"email": email}):
        return False, "⚠ Email already registered!"
    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": password,   # ⚠ Should hash in real apps
        "role": "customer",
        "approved": False,
        "created_at": datetime.now()
    })
    return True, "✅ Signup successful! Wait for admin approval."


def login(email, password):
    """Check login credentials"""
    user = users_collection.find_one({"email": email, "password": password})
    if not user:
        return None, "❌ Invalid email or password!"
    if user["role"] == "customer" and not user.get("approved", False):
        return None, "⏳ Waiting for admin approval."
    return user, f"✅ Welcome {user['name']}!"


# ====================================================
# 🔔 Flash Message Helpers
# ====================================================
def set_flash(msg, level="success"):
    st.session_state.flash = {"msg": msg, "level": level}


def show_flash():
    if st.session_state.flash:
        msg = st.session_state.flash["msg"]
        level = st.session_state.flash["level"]
        if level == "success":
            st.success(msg)
        elif level == "error":
            st.error(msg)
        elif level == "warning":
            st.warning(msg)
        else:
            st.info(msg)
        st.session_state.flash = None


# ====================================================
# 📝 Authentication Page (Login / Signup UI)
# ====================================================
def auth_page():
    st.markdown("<h1 style='text-align:center; color:#0ea5e9;'>🌐 Broadband Subscription Portal</h1>",
                unsafe_allow_html=True)
    menu = ["Login", "Signup"]
    choice = st.sidebar.selectbox("🔽 Menu", menu)

    # --------- Signup ---------
    if choice == "Signup":
        st.subheader("📝 Customer Signup")
        name = st.text_input("Full Name", key="signup_name")
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Password", type="password", key="signup_pass")

        if st.button("Signup", use_container_width=True, key="signup_btn"):
            if name and email and password:
                success, msg = signup(name, email, password)
                if success:
                    st.success(msg)
                    # trigger rerun, fields will be cleared
                    st.session_state.page = "auth"
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠ Please fill all fields.")

    # --------- Login ---------
    elif choice == "Login":
        st.subheader("🔑 Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")

        if st.button("Login", use_container_width=True, key="login_btn"):
            if email and password:
                user, msg = login(email, password)
                if user:
                    st.session_state.user = user
                    st.session_state.page = "dashboard"
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠ Please enter email and password.")


# ====================================================
# 👑 Admin Dashboard
# ====================================================
def admin_dashboard(user):

    # Welcome header
    st.markdown(f"### 👑 Welcome, {user['name']} (Admin)")

    # ---------- Mini Dashboard Metrics (custom cards with hover) ----------
    # compute metrics as before
    total_users = users_collection.count_documents({})
    total_customers = users_collection.count_documents({"role": "customer"})
    total_subscriptions = customers_collection.count_documents({})

    # Revenue calculations
    total_revenue = 0
    active_revenue = 0
    for sub in customers_collection.find():
        plan = plans_collection.find_one({"name": sub.get("plan_name")})
        if plan:
            total_revenue += plan.get("price", 0)
            if sub.get("status") == "active":
                active_revenue += plan.get("price", 0)

    # format numbers safely
    def fmt(n):
        try:
            return f"{int(n):,}"
        except Exception:
            try:
                return f"{float(n):,.2f}"
            except Exception:
                return str(n)

    total_users_f = fmt(total_users)
    total_customers_f = fmt(total_customers)
    total_subscriptions_f = fmt(total_subscriptions)
    active_revenue_f = f"₹{fmt(active_revenue)}"
    total_revenue_f = f"₹{fmt(total_revenue)}"

    # CSS + HTML grid of metric cards
    st.markdown(
        """
        <style>
        /* Grid wrapper */
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
            margin-bottom: 16px;
            align-items: stretch;
        }

        /* Individual card */
        .metric-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 16px 18px;
            border: 1px solid rgba(14, 165, 233, 0.06);
            box-shadow: 0 4px 10px rgba(2,6,23,0.04);
            transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
            text-align: left;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 72px;
        }

        /* Hover highlight */
        .metric-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 10px 24px rgba(2,6,23,0.12);
            background: linear-gradient(90deg, rgba(240,249,255,0.9), #ffffff);
            border-color: rgba(14,165,233,0.18);
        }

        .metric-label {
            font-size: 13px;
            color: #374151;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
            line-height: 1;
        }
        .metric-sub {
            font-size: 12px;
            color: #6b7280;
            margin-top: 6px;
        }

        /* Responsive */
        @media (max-width: 1100px) {
            .metric-grid { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 700px) {
            .metric-grid { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 420px) {
            .metric-grid { grid-template-columns: 1fr; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    html = f"""
    <div class="metric-grid">
    <div class="metric-card">
        <div class="metric-label">👥 Total Users</div>
        <div class="metric-value">{total_users_f}</div>
        <div class="metric-sub">All registered users</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">🙋 Total Customers</div>
        <div class="metric-value">{total_customers_f}</div>
        <div class="metric-sub">Users with customer role</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">📋 Subscriptions</div>
        <div class="metric-value">{total_subscriptions_f}</div>
        <div class="metric-sub">All user subscriptions</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">⚡ Active Revenue</div>
        <div class="metric-value">{active_revenue_f}</div>
        <div class="metric-sub">From active subscriptions</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">💰 Total Revenue</div>
        <div class="metric-value">{total_revenue_f}</div>
        <div class="metric-sub">All-time (from plans)</div>
    </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


    # Dynamic CSS for button-like fixed tabs
    st.markdown(
        """
        <style>
        /* Make the tab bar sticky at the top */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            position: sticky;
            top: 0;
            z-index: 999;
            background-color: #ffffff;
            padding: 10px 0;
            margin-bottom: 15px;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 500;
            color: #333;
            border: 1px solid #ddd;
            box-shadow: 0px 1px 3px rgba(0,0,0,0.05);
            transition: all 0.25s ease-in-out;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #f9ffea;
            border: 1px solid #d6e9b5;
            color: #222;
            transform: translateY(-2px);
            box-shadow: 0px 3px 8px rgba(0,0,0,0.08);
        }
        .stTabs [aria-selected="true"] {
            background: #f9ffea !important;
            color: #1a1a1a !important;
            font-weight: 600 !important;
            border: 1px solid #a3e6c6 !important;
            box-shadow: 0px 2px 10px rgba(100, 220, 180, 0.6) !important;
            transform: translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Tabs styled as dynamic buttons
    tabs = st.tabs([
        "👥 Users",
        "📦 Plans",
        "📊 Analytics",
        "📋 Subscriptions",
        "➕ Add User",
        "➕ Add Plan"
    ])

    # ---------- USERS TAB ----------
    with tabs[0]:
        st.subheader("👥 Manage Users")

        all_users = list(users_collection.find())

        if all_users:
            # Check if current admin is super admin
            is_super_admin = st.session_state.user['email'] == "admin@portal.com"

            # ---------- Filter Users Based on Admin Role ----------
            if is_super_admin:
                admins = [u for u in all_users if u['role'] == 'admin']
                customers = [u for u in all_users if u['role'] == 'customer']
            else:
                admins = [u for u in all_users if u['role'] == "admin" and u['email'] != "admin@portal.com"]
                customers = [u for u in all_users if u['role'] == 'customer']

            # ---------- Helper Function to Render User Cards ----------
            def render_user_card(user, allow_verify=False):
                col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                with col1:
                    st.markdown(f"**{user['name']}**")
                    st.caption(user['email'])
                with col2:
                    st.markdown(f"Role: `{user['role'].capitalize()}`")
                    status = "✅ Approved" if user.get("approved", False) else "⏳ Pending"
                    st.markdown(f"**Status:** {status}")
                with col3:
                    if allow_verify and not user.get("approved", False):
                        if st.button("✔ Verify", key=f"verify_{user['_id']}"):
                            users_collection.update_one(
                                {"_id": user["_id"]}, {"$set": {"approved": True}}
                            )
                            st.success(f"User {user['name']} verified!")
                            st.rerun()
                with col4:
                    if is_super_admin:
                        if st.button("📝 Edit", key=f"edit_{user['_id']}"):
                            st.session_state["edit_user"] = user
                        if st.button("🗑 Delete", key=f"delete_{user['_id']}"):
                            users_collection.delete_one({"_id": user["_id"]})
                            st.error(f"User {user['name']} deleted!")
                            st.rerun()
                    else:
                        if user['role'] == "customer":
                            if st.button("📝 Edit", key=f"edit_{user['_id']}"):
                                st.session_state["edit_user"] = user
                            if st.button("🗑 Delete", key=f"delete_{user['_id']}"):
                                users_collection.delete_one({"_id": user["_id"]})
                                st.error(f"User {user['name']} deleted!")
                                st.rerun()
                st.markdown("---")

            # ---------- Admins Section ----------
            if admins:
                st.markdown("### 👑 Admins")
                for admin in admins:
                    render_user_card(admin, allow_verify=True)
            else:
                st.info("No Admins found.")

            # ---------- Customers Section ----------
            if customers:
                st.markdown("### 🙋 Customers")
                cust_tabs = st.tabs(["Approved Customers", "Pending Approvals"])

                # Customers Tab → Only approved customers
                with cust_tabs[0]:
                    approved_customers = [c for c in customers if c.get("approved", False)]
                    if approved_customers:
                        for customer in approved_customers:
                            render_user_card(customer, allow_verify=False)
                    else:
                        st.info("No approved customers yet.")

                # Permissions Tab → Customers waiting for approval
                with cust_tabs[1]:
                    pending_customers = [c for c in customers if not c.get("approved", False)]
                    if pending_customers:
                        for customer in pending_customers:
                            render_user_card(customer, allow_verify=True)
                    else:
                        st.info("No pending approvals.")
            else:
                st.info("No Customers found.")

            # ---------- Edit User Modal ----------
            if "edit_user" in st.session_state:
                edit_user = st.session_state["edit_user"]
                st.markdown("## ✏ Edit User")
                new_name = st.text_input("Full Name", value=edit_user['name'])
                new_email = st.text_input("Email", value=edit_user['email'])
                new_role = st.selectbox("Role", ["customer", "admin"],
                                        index=0 if edit_user['role'] == "customer" else 1)

                if not is_super_admin and new_role == "admin" and edit_user['role'] != "admin":
                    st.warning("❌ Only Super Admin can assign admin role.")
                else:
                    if st.button("💾 Save Changes"):
                        users_collection.update_one(
                            {"_id": edit_user["_id"]},
                            {"$set": {
                                "name": new_name,
                                "email": new_email,
                                "role": new_role if is_super_admin else edit_user['role']
                            }}
                        )
                        st.success(f"User {new_name} updated!")
                        del st.session_state["edit_user"]
                        st.rerun()

                if st.button("❌ Cancel Edit"):
                    del st.session_state["edit_user"]
                    st.rerun()

        else:
            st.info("No users found.")

    # ---------- PLANS TAB ----------
    with tabs[1]:
        st.subheader("📦 All Broadband Plans")

        all_plans = list(plans_collection.find())

        if all_plans:
            # Custom CSS for better UI
            st.markdown(
                """
                <style>
                .plan-card {
                    border-radius: 16px;
                    padding: 22px;
                    margin-bottom: 22px;
                    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
                    transition: all 0.25s ease-in-out;
                    border: 1px solid #e5e7eb;
                    background: #ffffff;
                }
                .plan-card:hover {
                    transform: translateY(-4px);
                    box-shadow: 0 6px 18px rgba(0,0,0,0.1);
                }
                /* Offer Plan - Premium Pink Theme */
                .offer-card {
                    background: linear-gradient(135deg, #fdf2f8, #fce7f3);
                    border-left: 6px solid #db2777;
                }
                /* Normal Plan - Clean Gray Theme */
                .normal-card {
                    background: linear-gradient(135deg, #f3f4f6, #e5e7eb);
                    border-left: 6px solid #374151;
                }
                .plan-title {
                    font-size: 22px;
                    font-weight: 700;
                    color: #111827;
                    margin-bottom: 10px;
                }
                .plan-price {
                    font-size: 20px;
                    font-weight: 600;
                    color: #2563eb;
                    margin-bottom: 12px;
                }
                .plan-details {
                    color: #374151;
                    font-size: 15px;
                    margin-bottom: 14px;
                    line-height: 1.5;
                }
                .plan-desc {
                    color: #4b5563;
                    font-size: 13px;
                    font-style: italic;
                    margin-bottom: 16px;
                }
                /* Buttons */
                div[data-testid="stButton"] button:has(span:contains("Edit")) {
                    background-color: #2563eb !important;
                    color: white !important;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 14px;
                }
                div[data-testid="stButton"] button:has(span:contains("Edit")):hover {
                    background-color: #1d4ed8 !important;
                    box-shadow: 0 4px 10px rgba(37, 99, 235, 0.35);
                }
                div[data-testid="stButton"] button:has(span:contains("Delete")) {
                    background-color: #ef4444 !important;
                    color: white !important;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 14px;
                }
                div[data-testid="stButton"] button:has(span:contains("Delete")):hover {
                    background-color: #dc2626 !important;
                    box-shadow: 0 4px 10px rgba(239, 68, 68, 0.35);
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            # Helper function to render plan cards
            def render_plan_card(plan):
                card_class = "offer-card" if plan.get(
                    "plan_type") == "Offer" else "normal-card"

                st.markdown(
                    f"""
                    <div class="plan-card {card_class}">
                        <div class="plan-title">{plan['name']}</div>
                        <div class="plan-price">₹{plan['price']} / {plan['validity_days']} days</div>
                        <div class="plan-details">
                            <b>📊 Data:</b> {plan['valid_data']} GB <br>
                            <b>⚡ Speed:</b> {plan['speed']} <br>
                            <b>🏷 Type:</b> {plan.get('plan_type', 'Normal')}
                        </div>
                        <div class="plan-desc">{plan.get('description', '')}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col1, col2 = st.columns([1, 1])
                with col1:
                    if st.button("✏ Edit", key=f"edit_plan_{plan['_id']}"):
                        st.session_state["edit_plan"] = plan
                with col2:
                    if st.button("🗑 Delete", key=f"delete_plan_{plan['_id']}"):
                        plans_collection.delete_one({"_id": plan["_id"]})
                        st.success(f"Plan {plan['name']} deleted!")
                        st.rerun()

            # ---------- Subtabs ----------
            duration_tabs = st.tabs(["📅 Monthly", "📆 Quarterly", "📈 Yearly"])

            for i, duration in enumerate(["Monthly", "Quarterly", "Yearly"]):
                with duration_tabs[i]:
                    st.markdown(f"### {duration} Plans")

                    offer_plans = [p for p in all_plans if p.get(
                        "duration_type") == duration and p.get("plan_type") == "Offer"]
                    normal_plans = [p for p in all_plans if p.get(
                        "duration_type") == duration and p.get("plan_type") == "Normal"]

                    # Show Offer Plans first
                    if offer_plans:
                        st.markdown("#### 🎁 Offer Plans")
                        for plan in offer_plans:
                            render_plan_card(plan)
                    else:
                        st.info("No offer plans yet.")

                    # Show Normal Plans
                    if normal_plans:
                        st.markdown("#### 🟢 Normal Plans")
                        for plan in normal_plans:
                            render_plan_card(plan)
                    else:
                        st.info("No normal plans yet.")

            # ---------- Edit Plan Modal ----------
            if "edit_plan" in st.session_state:
                edit_plan = st.session_state["edit_plan"]
                st.markdown("## ✏ Edit Plan")
                new_name = st.text_input("Plan Name", value=edit_plan['name'])
                new_price = st.number_input(
                    "Price (₹)", value=edit_plan['price'], min_value=0, step=10)
                new_data = st.number_input(
                    "Data Limit (GB)", value=edit_plan['valid_data'], min_value=0, step=1)
                new_speed = st.text_input("Speed", value=edit_plan['speed'])
                new_validity = st.number_input(
                    "Validity (Days)", value=edit_plan['validity_days'], min_value=1, step=1)
                new_desc = st.text_area(
                    "Description", value=edit_plan.get('description', ''))
                new_duration = st.selectbox("Duration Type", ["Monthly", "Quarterly", "Yearly"],
                                            index=["Monthly", "Quarterly", "Yearly"].index(edit_plan.get("duration_type", "Monthly")))
                new_plan_type = st.selectbox("Plan Type", ["Normal", "Offer"],
                                             index=["Normal", "Offer"].index(edit_plan.get("plan_type", "Normal")))

                if st.button("💾 Save Changes"):
                    plans_collection.update_one(
                        {"_id": edit_plan["_id"]},
                        {"$set": {
                            "name": new_name,
                            "price": new_price,
                            "valid_data": new_data,
                            "speed": new_speed,
                            "validity_days": new_validity,
                            "description": new_desc,
                            "duration_type": new_duration,
                            "plan_type": new_plan_type
                        }}
                    )
                    st.success(f"Plan {new_name} updated!")
                    del st.session_state["edit_plan"]
                    st.rerun()

                if st.button("❌ Cancel Edit"):
                    del st.session_state["edit_plan"]
                    st.rerun()

        else:
            st.info("No plans added yet.")

    # ---------- ANALYTICS TAB ----------
    with tabs[2]:
        st.subheader("📊 Broadband Analytics")

        all_plans = list(plans_collection.find())
        all_subs = list(customers_collection.find())

        if all_plans and all_subs:

            # ---------- Prepare analytics data ----------
            analytics_data = []
            total_subscriptions = len(all_subs)
            total_revenue = 0

            for plan in all_plans:
                plan_name = plan['name']
                subscribers = [
                    sub for sub in all_subs if sub['plan_name'] == plan_name]

                # Split active vs inactive
                active_customers = [
                    sub for sub in subscribers if sub["status"] == "active"]
                inactive_customers = [
                    sub for sub in subscribers if sub["status"] != "active"]

                num_active = len(active_customers)
                num_inactive = len(inactive_customers)
                num_total = num_active + num_inactive
                # revenue only from active
                revenue = num_active * plan['price']
                total_revenue += revenue

                analytics_data.append({
                    "Plan Name": plan_name,
                    "Active Subscribers": num_active,
                    "Inactive Subscribers": num_inactive,
                    "Total Subscribers": num_total,
                    "Revenue (₹)": revenue
                })

            df_analytics = pd.DataFrame(analytics_data)

            # ---------- Subtabs for Different Analytics ----------
            analytics_tabs = st.tabs(
                ["📋 Active vs Inactive", "📊 Revenue Chart",
                    "🥧 Customers Distribution", "📈 Active vs Inactive Chart"]
            )

            # ---------- 1️⃣ Active vs Inactive Table (Cards) ----------
            with analytics_tabs[0]:
                st.markdown("### Active vs Inactive Subscribers (Per Plan)")
                for plan in analytics_data:
                    st.markdown(
                        f"""
                        <div style="
                            border:1px solid #ddd; 
                            border-radius:12px; 
                            padding:20px; 
                            margin-bottom:12px; 
                            background:linear-gradient(90deg, #f1f8e9, #ffffff);
                            box-shadow: 2px 4px 10px rgba(0,0,0,0.08);
                        ">
                            <h4 style="color:#2e7d32; margin-bottom:5px;">{plan['Plan Name']}</h4>
                            <p style="font-size:16px; margin:2px;"><b>Active Subscribers:</b> ✅ {plan['Active Subscribers']}</p>
                            <p style="font-size:16px; margin:2px;"><b>Inactive Subscribers:</b> ⏳ {plan['Inactive Subscribers']}</p>
                            <p style="font-size:16px; margin:2px;"><b>Total Subscribers:</b> 👥 {plan['Total Subscribers']}</p>
                            <p style="font-size:16px; margin:2px;"><b>Active Revenue:</b> 💰 ₹{plan['Revenue (₹)']:,}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

            # ---------- 2️⃣ Revenue per Plan (Bar Chart) ----------
            with analytics_tabs[1]:
                st.markdown("### Revenue per Plan")

                # Dropdowns for filtering
                duration_filter = st.selectbox(
                    "🔍 Filter by Plan Duration",
                    ["All", "Monthly", "Quarterly", "Yearly"],
                    key="bar_duration"
                )
                type_filter = st.selectbox(
                    "🎯 Filter by Plan Type",
                    ["All", "Normal", "Offer"],
                    key="bar_type"
                )

                # Apply filters
                filtered_plans = analytics_data
                if duration_filter != "All":
                    filtered_plans = [
                        plan for plan in filtered_plans if plan["Plan Name"].lower().startswith(duration_filter.lower())
                    ]
                if type_filter != "All":
                    filtered_plans = [
                        plan for plan in filtered_plans if plan.get("Plan Type", "Normal") == type_filter
                    ]

                df_filtered = pd.DataFrame(filtered_plans)

                if not df_filtered.empty:
                    # Calculate average revenue for arrow symbols
                    avg_revenue = df_filtered["Revenue (₹)"].mean()

                    # Add arrow symbols to Plan Name
                    df_filtered["Plan Label"] = df_filtered.apply(
                        lambda row: f"{row['Plan Name']} {'📈' if row['Revenue (₹)'] >= avg_revenue else '📉'}",
                        axis=1
                    )

                    # Distinct colors per plan
                    color_palette = px.colors.qualitative.Set2
                    color_sequence = color_palette * \
                        (len(df_filtered) // len(color_palette) + 1)
                    color_sequence = color_sequence[:len(df_filtered)]

                    fig1 = px.bar(
                        df_filtered,
                        x="Plan Label",
                        y="Revenue (₹)",
                        text="Active Subscribers",
                        color="Plan Label",
                        color_discrete_sequence=color_sequence,
                        title=f"Revenue per Plan ({duration_filter}, {type_filter})"
                    )

                    fig1.update_layout(
                        yaxis_title="Revenue (₹)",
                        xaxis_title="Plan",
                        plot_bgcolor="#f9f9f9",
                        paper_bgcolor="#f9f9f9",
                        showlegend=False,
                        width=900,
                        height=600,
                        margin=dict(l=50, r=50, t=80, b=50)
                    )
                    fig1.update_traces(textposition="outside")

                    st.plotly_chart(fig1, use_container_width=True)

                else:
                    st.info("No plans available for the selected filters.")

            # ---------- 3️⃣ Pie Chart View ----------
            with analytics_tabs[2]:
                st.markdown("### Customers Distribution per Plan")

                # Dropdown filters
                duration_filter_pie = st.selectbox(
                    "🔍 Filter by Plan Duration",
                    ["All", "Monthly", "Quarterly", "Yearly"],
                    key="pie_duration"
                )
                type_filter_pie = st.selectbox(
                    "🎯 Filter by Plan Type",
                    ["All", "Normal", "Offer"],
                    key="pie_type"
                )

                # Apply filters
                filtered_analytics = analytics_data
                if duration_filter_pie != "All":
                    filtered_analytics = [
                        plan for plan in filtered_analytics if plan["Plan Name"].lower().startswith(duration_filter_pie.lower())
                    ]
                if type_filter_pie != "All":
                    filtered_analytics = [
                        plan for plan in filtered_analytics if plan.get("Plan Type", "Normal") == type_filter_pie
                    ]

                df_filtered_pie = pd.DataFrame(filtered_analytics)

                if not df_filtered_pie.empty:
                    # Color palette
                    colors = px.colors.qualitative.Bold
                    color_sequence = colors * \
                        (len(df_filtered_pie) // len(colors) + 1)
                    color_sequence = color_sequence[:len(df_filtered_pie)]

                    fig2 = px.pie(
                        df_filtered_pie,
                        names="Plan Name",
                        values="Total Subscribers",
                        color="Plan Name",
                        color_discrete_sequence=color_sequence,
                        title="Customer Distribution"
                    )

                    # Increase chart size
                    fig2.update_layout(
                        width=900,
                        height=700,
                        margin=dict(l=50, r=50, t=80, b=50)
                    )

                    fig2.update_traces(textposition='inside',
                                       textinfo='percent+label')
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info("No plans match the selected filters.")

            # ---------- 4️⃣ Active vs Inactive Stacked Bar ----------
            with analytics_tabs[3]:
                st.markdown("### Active vs Inactive Subscribers per Plan")

                # Dropdown filters
                duration_filter_stack = st.selectbox(
                    "🔍 Filter by Plan Duration",
                    ["All", "Monthly", "Quarterly", "Yearly"],
                    key="stack_duration"
                )
                type_filter_stack = st.selectbox(
                    "🎯 Filter by Plan Type",
                    ["All", "Normal", "Offer"],
                    key="stack_type"
                )

                # Apply filters
                filtered_stack = analytics_data
                if duration_filter_stack != "All":
                    filtered_stack = [
                        plan for plan in filtered_stack if plan["Plan Name"].lower().startswith(duration_filter_stack.lower())
                    ]
                if type_filter_stack != "All":
                    filtered_stack = [
                        plan for plan in filtered_stack if plan.get("Plan Type", "Normal") == type_filter_stack
                    ]

                df_stack = pd.DataFrame(filtered_stack)

                if not df_stack.empty:
                    fig3 = px.bar(
                        df_stack,
                        x="Plan Name",
                        y=["Active Subscribers", "Inactive Subscribers"],
                        title=f"Active vs Inactive Subscribers ({duration_filter_stack}, {type_filter_stack})",
                        barmode="stack",
                        text_auto=True,
                        color_discrete_map={
                            "Active Subscribers": "#4caf50",
                            "Inactive Subscribers": "#ef5350"
                        }
                    )
                    fig3.update_layout(
                        yaxis_title="Subscribers",
                        xaxis_title="Plan",
                        plot_bgcolor="#f9f9f9",
                        paper_bgcolor="#f9f9f9",
                        width=900,
                        height=600,
                        margin=dict(l=50, r=50, t=80, b=50)
                    )
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.info("No plans match the selected filters.")

    # ---------- SUBSCRIPTIONS TAB ----------
    with tabs[3]:
        st.subheader("📋 User Subscriptions & Revenue")

        all_plans = list(plans_collection.find())
        all_subs = list(customers_collection.find())

        if all_plans and all_subs:

            # Create subtabs for plan durations
            duration_tabs = st.tabs(["📅 Monthly", "📆 Quarterly", "📈 Yearly"])
            for i, duration in enumerate(["Monthly", "Quarterly", "Yearly"]):
                with duration_tabs[i]:
                    st.markdown(f"### {duration} Plans")

                    # Dropdown to filter plan type
                    plan_type_filter = st.selectbox(
                        "🎯 Filter by Plan Type",
                        ["All", "Normal", "Offer"],
                        key=f"{duration}_filter"
                    )

                    # Dropdown to filter subscription status
                    status_filter = st.selectbox(
                        "🟢 Filter by Subscription Status",
                        ["All", "Active", "Inactive"],
                        key=f"{duration}_status_filter"
                    )

                    # Filter plans by duration and type
                    filtered_plans = [
                        plan for plan in all_plans if plan.get("duration_type") == duration
                    ]
                    if plan_type_filter != "All":
                        filtered_plans = [
                            plan for plan in filtered_plans if plan.get("plan_type", "Normal") == plan_type_filter
                        ]

                    total_revenue_duration = 0

                    if filtered_plans:
                        for plan in filtered_plans:
                            plan_name = plan['name']
                            subscribers = [
                                sub for sub in all_subs if sub['plan_name'] == plan_name
                            ]

                            # Apply status filter
                            if status_filter != "All":
                                subscribers = [
                                    sub for sub in subscribers if sub.get("status", "active").capitalize() == status_filter
                                ]

                            num_subs = len(subscribers)
                            revenue = num_subs * plan['price']
                            total_revenue_duration += revenue

                            # Plan Card Header
                            st.markdown(
                                f"""
                                <div style="
                                    background: linear-gradient(90deg, #e0f7fa, #b2ebf2);
                                    padding: 15px;
                                    border-radius: 12px;
                                    margin-bottom: 10px;
                                    box-shadow: 0px 4px 8px rgba(0,0,0,0.1);
                                    border-left: 6px solid #00acc1;
                                ">
                                    <h4 style="margin:0; color:#006064;">📦 {plan_name}</h4>
                                    <p style="margin:2px 0; color:#004d40;">
                                        Subscribers: <b>{num_subs}</b> | Revenue: <b>₹{revenue:,}</b>
                                    </p>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

                            # Subscriber Cards
                            if subscribers:
                                for sub in subscribers:
                                    user_info = users_collection.find_one(
                                        {"email": sub["user_email"]})
                                    if user_info:
                                        st.markdown(
                                            f"""
                                            <div style="
                                                border:1px solid #b2ebf2;
                                                border-radius:10px;
                                                padding:12px;
                                                margin-bottom:8px;
                                                background: #e0f2f1;
                                                box-shadow: 0px 2px 6px rgba(0,0,0,0.05);
                                            ">
                                                <b>User:</b> {user_info['name']}<br>
                                                <b>Email:</b> {user_info['email']}<br>
                                                <b>Usage:</b> {sub.get('usage_gb', 0)} GB<br>
                                                <b>Status:</b> {sub.get("status", "Active").capitalize()}
                                            </div>
                                            """,
                                            unsafe_allow_html=True
                                        )
                            else:
                                st.info(
                                    "No subscribers for this plan with selected filters.")

                        # Total Revenue Card for this duration
                        st.markdown(
                            f"""
                            <div style="
                                background:#ffe0b2;
                                padding:15px;
                                border-radius:12px;
                                text-align:center;
                                font-weight:bold;
                                font-size:18px;
                                margin-top:15px;
                            ">
                                💰 Total Revenue ({duration}): ₹{total_revenue_duration:,}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                    else:
                        st.info("No plans available for the selected filters.")

        else:
            st.info("No subscriptions or plans available.")

    
    # ---------- ADD USER TAB ----------
    with tabs[4]:
        st.subheader("Add New User")

        # Get logged-in user details correctly
        current_user = st.session_state.get("user", {})
        current_email = current_user.get("email", "")
        current_role = current_user.get("role", "customer")

        name = st.text_input("Full Name", key="add_user_name")
        email = st.text_input("Email", key="add_user_email")
        password = st.text_input("Password", type="password", key="add_user_pass")

        # Role selectbox logic
        if current_email == "admin@portal.com":
            # Only super admin (fixed email) can add admins
            role = st.selectbox("Role", ["customer", "admin"], key="add_user_role")
        else:
            role = "customer"  # Force customer creation
            st.info("⚠️ Only Super Admin can create Admin users. You can add customers.")

        if st.button("Add User", key="add_user_btn"):
            if name and email and password:
                if users_collection.find_one({"email": email}):
                    st.error("Email already exists!")
                else:
                    users_collection.insert_one({
                        "name": name,
                        "email": email,
                        "password": password,  # ⚠️ hash in production
                        "role": role,
                        "approved": True if role == "admin" else False,
                        "created_at": datetime.now()
                    })
                    st.success(f"✅ User {name} added as {role}!")
                    st.rerun()
            else:
                st.warning("Please fill all fields.")
    # ---------- ADD PLAN TAB ----------
    with tabs[5]:
        st.subheader("Add New Plan")

        # Input fields for plan
        plan_name = st.text_input("Plan Name", key="add_plan_name")
        price = st.number_input("Price (₹)", min_value=0, key="add_plan_price")
        valid_data = st.number_input("Total Data (GB)", min_value=0, key="add_plan_data")
        speed = st.text_input("Speed (e.g., 30 Mbps)", key="add_plan_speed")
        validity_days = st.number_input("Validity (Days)", min_value=1, key="add_plan_validity")
        description = st.text_area("Description", key="add_plan_desc")

        # Duration type selection
        duration_type = st.selectbox("Duration Type", ["Monthly", "Quarterly", "Yearly"], key="add_plan_duration")

        # Plan type selection
        plan_type = st.selectbox("Plan Type", ["Normal", "Offer"], key="add_plan_type")

        if st.button("Add Plan", key="add_plan_btn"):
            # Validate inputs
            if plan_name and price >= 0 and valid_data >= 0 and speed and validity_days > 0:
                # Check if plan with same name exists
                if plans_collection.find_one({"name": plan_name}):
                    st.error("A plan with this name already exists!")
                else:
                    plans_collection.insert_one({
                        "name": plan_name,
                        "price": price,
                        "valid_data": valid_data,
                        "speed": speed,
                        "validity_days": validity_days,
                        "description": description,
                        "duration_type": duration_type,
                        "plan_type": plan_type,
                        "createdAt": datetime.now()
                    })
                    st.success(f"✅ Plan '{plan_name}' added successfully!")
                    st.rerun()
            else:
                st.warning("Please fill all fields correctly.")


# ========================
# 🙋 Customer Dashboard
# ========================
def customer_dashboard(user):

    # ---------- Welcome Header ----------
    st.markdown(f"### 🙋 Welcome, {user['name']} (Customer)")

    # ---------- Mini Dashboard Metrics (Customer) ----------
    user_subs = list(customers_collection.find({"user_email": user["email"]}))

    # Count plans
    active_subs = len([s for s in user_subs if s.get("status") in ["active", "stopped"]])
    previous_subs = len([s for s in user_subs if s.get("status") == "previous"])
    total_subs = len(user_subs)

    # Revenue calculations (only active and total)
    active_revenue = sum(
        plans_collection.find_one({"name": s["plan_name"]})["price"]
        for s in user_subs
        if s.get("status") == "active" and plans_collection.find_one({"name": s["plan_name"]})
    )
    total_revenue = sum(
        plans_collection.find_one({"name": s["plan_name"]})["price"]
        for s in user_subs
        if plans_collection.find_one({"name": s["plan_name"]})
    )

    # format helper
    def fmt(n):
        try:
            return f"{int(n):,}"
        except Exception:
            try:
                return f"{float(n):,.2f}"
            except Exception:
                return str(n)

    active_subs_f = fmt(active_subs)
    previous_subs_f = fmt(previous_subs)
    total_subs_f = fmt(total_subs)
    active_revenue_f = f"₹{fmt(active_revenue)}"
    total_revenue_f = f"₹{fmt(total_revenue)}"

    # ---------- CSS (paste once globally at the top if you want to reuse) ----------
    st.markdown(
        """
        <style>
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 12px;
            margin-bottom: 16px;
            align-items: stretch;
        }
        .metric-card {
            background: #ffffff;
            border-radius: 12px;
            padding: 16px 18px;
            border: 1px solid rgba(14, 165, 233, 0.06);
            box-shadow: 0 4px 10px rgba(2,6,23,0.04);
            transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
            text-align: left;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 72px;
        }
        .metric-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 10px 24px rgba(2,6,23,0.12);
            background: linear-gradient(90deg, rgba(240,249,255,0.9), #ffffff);
            border-color: rgba(14,165,233,0.18);
        }
        .metric-label {
            font-size: 13px;
            color: #374151;
            margin-bottom: 6px;
        }
        .metric-value {
            font-size: 20px;
            font-weight: 700;
            color: #0f172a;
            line-height: 1;
        }
        .metric-sub {
            font-size: 12px;
            color: #6b7280;
            margin-top: 6px;
        }
        @media (max-width: 1100px) { .metric-grid { grid-template-columns: repeat(3, 1fr); } }
        @media (max-width: 700px) { .metric-grid { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 420px) { .metric-grid { grid-template-columns: 1fr; } }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------- Customer Metrics HTML ----------
    html_customer = f"""
    <div class="metric-grid">
    <div class="metric-card">
        <div class="metric-label">🟢 Active Plans</div>
        <div class="metric-value">{active_subs_f}</div>
        <div class="metric-sub">Currently active or stopped</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">⏳ Previous Plans</div>
        <div class="metric-value">{previous_subs_f}</div>
        <div class="metric-sub">Expired or old subscriptions</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">📋 All Subscriptions</div>
        <div class="metric-value">{total_subs_f}</div>
        <div class="metric-sub">Your subscription history</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">⚡ Current Plan Cost</div>
        <div class="metric-value">{active_revenue_f}</div>
        <div class="metric-sub">Ongoing active plan</div>
    </div>

    <div class="metric-card">
        <div class="metric-label">💰 Total Spent</div>
        <div class="metric-value">{total_revenue_f}</div>
        <div class="metric-sub">All plans combined</div>
    </div>
    </div>
    """

    st.markdown(html_customer, unsafe_allow_html=True)

    # ---------- Dynamic Tabs Styling ----------
    st.markdown(
        """
        <style>
        /* Make the tab bar sticky at the top */
        .stTabs [data-baseweb="tab-list"] {
            gap: 12px;
            position: sticky;
            top: 0;
            z-index: 999;
            background-color: #ffffff;
            padding: 10px 0;
            margin-bottom: 15px;
        }

        .stTabs [data-baseweb="tab"] {
            background-color: #ffffff;
            padding: 10px 18px;
            border-radius: 8px;
            font-weight: 500;
            color: #333;
            border: 1px solid #ddd;
            box-shadow: 0px 1px 3px rgba(0,0,0,0.05);
            transition: all 0.25s ease-in-out;
        }

        .stTabs [data-baseweb="tab"]:hover {
            background-color: #f9ffea;
            border: 1px solid #d6e9b5;
            color: #222;
            transform: translateY(-2px);
            box-shadow: 0px 3px 8px rgba(0,0,0,0.08);
        }

        .stTabs [aria-selected="true"] {
            background: #f9ffea !important;
            color: #1a1a1a !important;
            font-weight: 600 !important;
            border: 1px solid #a3e6c6 !important;
            box-shadow: 0px 2px 10px rgba(100, 220, 180, 0.6) !important;
            transform: translateY(-1px);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ---------- Main Tabs ----------
    tabs = st.tabs([
        "📊 My Plans",
        "📦 Available Plans",
        "🕒 Previous Plans",
        "📈 My Analytics",
        "👤 Profile"
    ])

    # ---------- Fetch User Subscriptions ----------
    user_subs = list(customers_collection.find({"user_email": user["email"]}))

    # ---------- MY PLANS ----------
    with tabs[0]:
        st.subheader("Your Plans")

        # Filter plans that are active or stopped (exclude previous)
        display_plans = [p for p in user_subs if p.get("status") in ["active", "stopped"]]

        if display_plans:
            for i, p in enumerate(display_plans):
                plan_info = plans_collection.find_one({"name": p.get("plan_name")})
                if plan_info:
                    plan_key = f"plan_{plan_info['_id']}_{i}_status"
                    if plan_key not in st.session_state:
                        st.session_state[plan_key] = p.get("status", "active")
                    
                    status_text = st.session_state[plan_key].capitalize()
                    usage_gb = p.get("usage_gb", 0)
                    usage_percent = int((usage_gb / plan_info.get("valid_data", 1)) * 100)
                    usage_percent = min(100, usage_percent)

                    # Plan card HTML
                    st.markdown(f"""
                    <div style="
                        border-radius:16px;
                        padding:20px;
                        margin-bottom:15px;
                        background: linear-gradient(135deg, #e0f7fa, #ffffff);
                        box-shadow: 0 4px 14px rgba(0,0,0,0.1);
                        border-left: 6px solid #0ea5e9;
                    ">
                        <h4 style="color:#0ea5e9; margin-bottom:8px;">{plan_info.get('name')}</h4>
                        <p>💰 <b>Price:</b> ₹{plan_info.get('price', 0)} | ⏱ <b>{plan_info.get('validity_days', 0)}</b> days | ⚡ <b>{plan_info.get('speed', 'N/A')}</b></p>
                        <p>📊 <b>Usage:</b> {usage_gb:.2f} / {plan_info.get('valid_data', 0)} GB</p>
                        <div style="
                            background:#ddd;
                            border-radius:8px;
                            width:100%;
                            height:16px;
                            overflow:hidden;
                        ">
                            <div style="
                                background:#0ea5e9;
                                width:{usage_percent}%;
                                height:100%;
                                border-radius:8px;
                            "></div>
                        </div>
                        <p style="text-align:right; margin-top:5px;">Status: <b>{status_text}</b></p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Buttons
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        toggle_label = "⏸ Pause" if st.session_state[plan_key] == "active" else "▶ Resume"
                        if st.button(toggle_label, key=f"btn_toggle_{plan_info['_id']}_{i}"):
                            new_status = "stopped" if st.session_state[plan_key] == "active" else "active"
                            customers_collection.update_one(
                                {"user_email": user["email"], "plan_name": plan_info["name"]},
                                {"$set": {"status": new_status}}
                            )
                            st.session_state[plan_key] = new_status
                            st.rerun()

                    with col2:
                        if st.button("❌ Cancel", key=f"btn_cancel_{plan_info['_id']}_{i}"):
                            customers_collection.update_one(
                                {"user_email": user["email"], "plan_name": plan_info["name"]},
                                {"$set": {"status": "previous"}}
                            )
                            st.session_state[plan_key] = "previous"
                            st.rerun()
        else:
            st.info("You have no active or stopped plans.")


    # ---------- AVAILABLE PLANS ----------
    with tabs[1]:
        st.subheader("Available Plans")

        # Tabs for plan durations
        plan_tabs = st.tabs(["Monthly", "Quarterly", "Yearly"])
        durations = ["Monthly", "Quarterly", "Yearly"]

        # Colors for durations
        duration_base_colors = {
            "Monthly": ("#d1fae5", "#a7f3d0"),   # Green gradient
            "Quarterly": ("#dbeafe", "#bfdbfe"),  # Blue gradient
            "Yearly": ("#f3e8ff", "#e9d5ff")      # Purple gradient
        }
        border_colors = {
            "Monthly": "#10b981",
            "Quarterly": "#3b82f6",
            "Yearly": "#8b5cf6"
        }
        plan_type_text_colors = {
            "Normal": "#065f46",
            "Offer": "#12cde2",
            "All": "#065f46"
        }

        for idx, duration in enumerate(durations):
            with plan_tabs[idx]:
                # Dropdown to filter plan type
                plan_type = st.selectbox(
                    "Filter by Type",
                    options=["All", "Normal", "Offer"],
                    key=f"filter_{duration}"
                )

                # Fetch and filter plans
                filtered_plans = list(plans_collection.find({"duration_type": duration}))
                if plan_type != "All":
                    filtered_plans = [p for p in filtered_plans if p.get("plan_type") == plan_type]

                if filtered_plans:
                    for plan in filtered_plans:
                        bg_start, bg_end = duration_base_colors[duration]
                        border_color = border_colors[duration]
                        text_color = plan_type_text_colors.get(plan.get("plan_type", "Normal"), "#065f46")

                        # Add offer icon if plan type is "Offer"
                        offer_badge = ""
                        if plan.get("plan_type") == "Offer":
                            offer_badge = '<span style="color:#b91c1c; font-weight:bold; margin-left:10px;">🔥 Offer</span>'

                        st.markdown(f"""
                        <div style='
                            border-radius:16px;
                            padding:18px;
                            margin-bottom:15px;
                            background: linear-gradient(135deg, {bg_start}, {bg_end});
                            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                            border-left: 6px solid {border_color};
                            transition: transform 0.2s;
                        '>
                            <h4 style="color:{text_color}; margin-bottom:5px;">{plan['name']}{offer_badge}</h4>
                            <p>💰 ₹{plan['price']} | ⏱ {plan['validity_days']} days | 📶 {plan['valid_data']} GB | ⚡ {plan['speed']}</p>
                            <p style="color:{text_color}; font-weight:bold;">Type: {plan['plan_type']}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        if st.button(f"Subscribe", key=f"sub_{plan['_id']}"):
                            # Check only active or stopped subscriptions
                            existing = customers_collection.find_one({
                                "user_email": user["email"],
                                "plan_name": plan["name"],
                                "status": {"$in": ["active", "stopped"]}
                            })
                            if existing:
                                st.warning("⚠ You are already subscribed to this plan.")
                            else:
                                customers_collection.insert_one({
                                    "user_email": user["email"],
                                    "plan_name": plan["name"],
                                    "usage_gb": 0,
                                    "subscribed_on": datetime.now(),
                                    "status": "active"
                                })
                                st.success(f"✅ Subscribed to {plan['name']} successfully!")
                                st.rerun()  # Refresh dashboard immediately

                else:
                    st.info("No plans available for this filter.")

    # ---------- PREVIOUS / INACTIVE PLANS ----------
    with tabs[2]:
        st.subheader("Previous / Inactive Plans")

        # Duration tabs
        prev_tabs = st.tabs(["Monthly", "Quarterly", "Yearly"])
        durations = ["Monthly", "Quarterly", "Yearly"]

        for idx, duration in enumerate(durations):
            with prev_tabs[idx]:
                # Dropdown to filter plan type
                plan_type = st.selectbox(
                    "Filter by Type",
                    options=["All", "Normal", "Offer"],
                    key=f"prev_filter_{duration}"
                )

                # Fetch previous/inactive plans for this user
                prev_plans = list(customers_collection.find({
                    "user_email": user["email"],
                    "status": {"$in": ["previous", "stopped"]}
                }))

                # Filter plans by duration and type
                filtered_prev_plans = []
                for p in prev_plans:
                    plan_info = plans_collection.find_one({"name": p["plan_name"], "duration_type": duration})
                    if plan_info:
                        if plan_type == "All" or plan_info.get("plan_type") == plan_type:
                            filtered_prev_plans.append((p, plan_info))

                if filtered_prev_plans:
                    for p, plan_info in filtered_prev_plans:
                        usage_gb = p.get("usage_gb", 0)
                        usage_percent = int((usage_gb / plan_info.get("valid_data", 1)) * 100)
                        usage_percent = min(100, usage_percent)

                        st.markdown(f"""
                        <div style='
                            border-radius:16px;
                            padding:20px;
                            margin-bottom:15px;
                            background: linear-gradient(135deg, #fef3f3, #fde2e2);
                            box-shadow: 0 4px 14px rgba(0,0,0,0.1);
                            border-left: 6px solid #ef4444;
                            transition: transform 0.2s;
                        '>
                            <h4 style='color:#b91c1c; margin-bottom:8px;'>{plan_info['name']}</h4>
                            <p>💰 <b>Price:</b> ₹{plan_info['price']} | ⏱ <b>{plan_info['validity_days']}</b> days | ⚡ <b>{plan_info['speed']}</b></p>
                            <p>📊 <b>Usage:</b> {usage_gb:.2f} / {plan_info['valid_data']} GB</p>
                            <div style='background:#f3f3f3; border-radius:8px; width:100%; height:16px;'>
                                <div style='background:#ef4444; width:{usage_percent}%; height:100%; border-radius:8px;'></div>
                            </div>
                            <p style='text-align:right; margin-top:5px;'>Status: <b>{p.get("status", "previous").capitalize()}</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No previous or inactive plans found for this filter.")

    # ---------- MY ANALYTICS ----------
    with tabs[3]:
        st.subheader("📈 My Analytics")

        # Create subtabs for analytics
        analytics_tabs = st.tabs(["Usage Trends", "Cost & Spending", "Compare Plans"])

        # Fetch all user subscriptions
        user_subs = list(customers_collection.find({"user_email": user["email"]}))

        # Prepare dataframe for analytics
        analytics_data = []
        for sub in user_subs:
            plan_info = plans_collection.find_one({"name": sub.get("plan_name")})
            if plan_info:
                analytics_data.append({
                    "Plan": plan_info.get("name", ""),
                    "Price": plan_info.get("price", 0),
                    "Validity": plan_info.get("validity_days", 0),
                    "Duration": plan_info.get("duration_type", "N/A"),
                    "Plan Type": plan_info.get("plan_type", "Normal"),
                    "Speed": plan_info.get("speed", "N/A"),
                    "Total Data (GB)": plan_info.get("valid_data", 0),
                    "Used Data (GB)": sub.get("usage_gb", 0),
                    "Status": sub.get("status", "active")
                })

        df = pd.DataFrame(analytics_data)

        # ---------- Subtab 1: Usage Trends ----------
        with analytics_tabs[0]:
            st.subheader("Usage Trends")
            if not df.empty and "Plan" in df.columns:
                duration_options = ["All", "Monthly", "Quarterly", "Yearly"]
                type_options = ["All", "Normal", "Offer"]

                selected_duration = st.selectbox("Filter by Duration", duration_options, key="usage_duration")
                selected_type = st.selectbox("Filter by Type", type_options, key="usage_type")

                filtered_df = df.copy()
                if selected_duration != "All":
                    filtered_df = filtered_df[filtered_df["Duration"] == selected_duration]
                if selected_type != "All":
                    filtered_df = filtered_df[filtered_df["Plan Type"] == selected_type]

                if not filtered_df.empty:
                    fig = px.line(filtered_df, x="Plan", y="Used Data (GB)", markers=True, title="Data Usage per Plan")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No usage data available for the selected filters.")
            else:
                st.info("No usage data available.")

        # ---------- Subtab 2: Cost & Spending ----------
        with analytics_tabs[1]:
            st.subheader("Cost & Spending")
            if not df.empty and "Plan" in df.columns:
                duration_options = ["All", "Monthly", "Quarterly", "Yearly"]
                type_options = ["All", "Normal", "Offer"]

                selected_duration = st.selectbox("Filter by Duration", duration_options, key="cost_duration")
                selected_type = st.selectbox("Filter by Type", type_options, key="cost_type")

                filtered_df = df.copy()
                if selected_duration != "All":
                    filtered_df = filtered_df[filtered_df["Duration"] == selected_duration]
                if selected_type != "All":
                    filtered_df = filtered_df[filtered_df["Plan Type"] == selected_type]

                if not filtered_df.empty:
                    fig = px.bar(filtered_df, x="Plan", y="Price", color="Status", title="Cost per Plan")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No cost data available for the selected filters.")
            else:
                st.info("No cost data available.")

        # ---------- Subtab 3: Compare Plans ----------
        with analytics_tabs[2]:
            st.subheader("Compare Two Plans")
            if not df.empty and "Plan" in df.columns:
                plans_list = df["Plan"].tolist()
                if len(plans_list) >= 2:
                    plan1 = st.selectbox("Select First Plan", plans_list, key="compare1")
                    plan2 = st.selectbox("Select Second Plan", plans_list, key="compare2")

                    compare_df = df[df["Plan"].isin([plan1, plan2])].set_index("Plan")
                    st.write(compare_df[["Price", "Validity", "Speed", "Total Data (GB)", "Used Data (GB)"]])

                    fig = px.bar(compare_df.reset_index(), x="Plan",
                                y=["Price", "Total Data (GB)", "Used Data (GB)"],
                                barmode="group",
                                title=f"Comparison: {plan1} vs {plan2}")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Need at least two plans to compare.")
            else:
                st.info("You have no subscriptions to compare.")

    # ---------- PROFILE ----------
    with tabs[4]:
        user_info = users_collection.find_one({"email": user['email']})

        if "edit_mode" not in st.session_state:
            st.session_state.edit_mode = False

        def toggle_edit():
            st.session_state.edit_mode = not st.session_state.edit_mode

        # PROFILE CARD
        profile_card_html = f"""
        <div style='max-width:500px; margin:auto; border-radius:16px; padding:25px 30px;
                    background: linear-gradient(135deg,#e0f7fa,#ffffff); border: 1px solid #e0e0e0;
                    box-shadow: 0 6px 18px rgba(0,0,0,0.08); font-family: Arial, sans-serif;'>
            <h3 style='color:#0ea5e9;'>👤 Profile Information</h3>
            <p><strong>Full Name:</strong> {user_info.get('name', '')}</p>
            <p>📧 <strong>Email:</strong> {user_info.get('email', '')}</p>
            <p>📞 <strong>Phone:</strong> {user_info.get('phone', 'Not added')}</p>
            <p>🏠 <strong>Address:</strong> {user_info.get('address', 'Not added')}</p>
        </div>
        """
        st.markdown(profile_card_html, unsafe_allow_html=True)
        st.button("✏️ Edit Profile", on_click=toggle_edit)

        if st.session_state.edit_mode:
            phone = st.text_input("📞 Phone", value=user_info.get("phone", ""), key="profile_phone")
            address = st.text_input("🏠 Address", value=user_info.get("address", ""), key="profile_address")
            new_password = st.text_input("🔒 New Password", type="password", key="profile_password")

            if st.button("💾 Save Changes", key="save_profile"):
                update_data = {"phone": phone, "address": address}
                if new_password.strip():
                    update_data["password"] = new_password
                users_collection.update_one({"email": user_info["email"]}, {"$set": update_data})
                st.success("✅ Profile updated successfully!")
                st.session_state.edit_mode = False
                st.rerun()

# ====================================================
# 🚀 Main Entry Point
# ====================================================


def main():
    if st.session_state.get("user") and st.session_state.page == "dashboard":
        # Sidebar logout (always visible)
        st.sidebar.markdown("### ⚙ Account")
        if st.sidebar.button("🚪 Logout"):
            st.session_state.user = None
            st.session_state.page = "auth"
            st.rerun()

        # Render dashboards
        user = st.session_state.user
        if user:  # make sure user is not None
            if user.get("role") == "admin":
                admin_dashboard(user)
            else:
                customer_dashboard(user)
        else:
            st.session_state.page = "auth"
            st.rerun()
    else:
        auth_page()


if __name__ == "__main__":
    main()



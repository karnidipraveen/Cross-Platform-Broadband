# app.py

import streamlit as st
from pymongo import MongoClient
from bson import ObjectId
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import hashlib
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
import json
import io

# =========================================
# CONFIG & CONSTANTS
# =========================================
MONGO_URI = "mongodb+srv://22h41a4506lavanya:Lavanya06@cluster0.n9z73p0.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "broadband_portal"
SESSION_TIMEOUT_MIN = 30

# Updated background image - modern broadband/network themed
BACKGROUND_IMAGE_URL = "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?q=80&w=1920&auto=format&fit=crop"
PRIMARY_ACCENT = "#6366f1"  # Indigo
SECONDARY_ACCENT = "#8b5cf6"  # Purple
SUCCESS_COLOR = "#10b981"  # Emerald
WARNING_COLOR = "#f59e0b"  # Amber
RUPEE = "₹"

# Language support
LANGUAGES = {
    "en": {
        "welcome": "Welcome",
        "login": "Login",
        "dashboard": "Dashboard",
        "marketplace": "Marketplace",
        "analytics": "Analytics",
        "subscription": "Subscription",
        "usage": "Usage",
        "plans": "Plans",
        "admin": "Admin",
        "logout": "Logout"
    },
    "hi": {
        "welcome": "स्वागत",
        "login": "लॉगिन",
        "dashboard": "डैशबोर्ड",
        "marketplace": "मार्केटप्लेस",
        "analytics": "विश्लेषण",
        "subscription": "सब्स्क्रिप्शन",
        "usage": "उपयोग",
        "plans": "योजनाएं",
        "admin": "व्यवस्थापक",
        "logout": "लॉगआउट"
    }
}

# =========================================
# STREAMLIT PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="Broadband Subscription Portal", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://example.com/help',
        'Report a bug': "https://example.com/bug",
        'About': "Modern Broadband Portal v2.0"
    }
)

# =========================================
# THEME & LANGUAGE STATE
# =========================================
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "language" not in st.session_state:
    st.session_state.language = "en"
if "badges" not in st.session_state:
    st.session_state.badges = {}

# =========================================
# DB CONNECTION
# =========================================
@st.cache_resource
def get_db():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]

db = get_db()

# =========================================
# UTILITIES
# =========================================
def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def today_date_str() -> str:
    return now_utc().date().isoformat()

def first_day_of_current_month() -> pd.Timestamp:
    d = datetime.now(timezone.utc).date().replace(day=1)
    return pd.to_datetime(d)

def inr(x: float) -> str:
    try:
        return f"{RUPEE}{float(x):,.2f}"
    except Exception:
        return f"{RUPEE}{x}"

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()

def safe_objectid(oid) -> ObjectId | None:
    try:
        return ObjectId(oid) if not isinstance(oid, ObjectId) else oid
    except Exception:
        return None

def get_text(key: str) -> str:
    """Get localized text"""
    return LANGUAGES[st.session_state.language].get(key, key)

def calculate_user_score(user_id) -> int:
    """Calculate gamification score"""
    active_sub = get_active_subscription(user_id)
    usage_logs = get_usage_logs(user_id)
    score = 0
    
    # Base score for having subscription
    if active_sub:
        score += 100
    
    # Usage consistency bonus
    if len(usage_logs) > 30:
        score += 50
    
    # Loyalty bonus (subscription duration)
    if active_sub:
        start_date = datetime.fromisoformat(active_sub["start_date"]).date()
        days_active = (now_utc().date() - start_date).days
        score += min(days_active * 2, 200)
    
    return score

def get_user_badges(user_id) -> list:
    """Get user achievement badges"""
    badges = []
    score = calculate_user_score(user_id)
    active_sub = get_active_subscription(user_id)
    
    if score >= 300:
        badges.append({"name": "🏆 Gold Member", "description": "High engagement score"})
    elif score >= 200:
        badges.append({"name": "🥈 Silver Member", "description": "Good engagement score"})
    elif score >= 100:
        badges.append({"name": "🥉 Bronze Member", "description": "Active subscriber"})
    
    if active_sub:
        badges.append({"name": "📶 Connected", "description": "Active subscription"})
    
    return badges

# =========================================
# AUTH & ADMIN SETUP
# =========================================
def ensure_admin_exists():
    if not db.users.find_one({"email": "admin@portal.com"}):
        db.users.insert_one({
            "email": "admin@portal.com",
            "name": "Administrator",
            "password_hash": hash_pw("admin123"),
            "role": "admin",
            "created_at": now_utc().isoformat(),
            "vacation_mode": False,
            "budget_limit": 2000.0,
            "notification_preferences": {
                "email": True,
                "sms": True,
                "push": True
            }
        })

def create_user(email: str, name: str, password: str, role: str = "user") -> bool:
    email_l = email.strip().lower()
    if not email_l or not name.strip() or not password:
        return False
    if db.users.find_one({"email": email_l}):
        return False
    db.users.insert_one({
        "email": email_l,
        "name": name.strip(),
        "password_hash": hash_pw(password),
        "role": role,
        "created_at": now_utc().isoformat(),
        "vacation_mode": False,
        "budget_limit": 1500.0,
        "notification_preferences": {
            "email": True,
            "sms": False,
            "push": True
        }
    })
    return True

def check_login(email: str, pw: str):
    email_l = email.strip().lower()
    user = db.users.find_one({"email": email_l})
    if user and user.get("password_hash") == hash_pw(pw):
        return user
    return None

def check_session_timeout():
    if "login_time" in st.session_state:
        elapsed = (datetime.now(timezone.utc).timestamp() - st.session_state["login_time"]) / 60.0
        if elapsed > SESSION_TIMEOUT_MIN:
            st.session_state.clear()
            st.warning("Session expired. Please log in again.")
            st.rerun()

# =========================================
# ENHANCED CSS WITH DARK MODE
# =========================================
def inject_global_css():
    dark_mode = st.session_state.dark_mode
    
    if dark_mode:
        bg_color = "#1a1a1a"
        text_color = "#ffffff"
        card_bg = "rgba(45, 45, 45, 0.9)"
        border_color = "rgba(255,255,255,0.1)"
    else:
        bg_color = "#f8fafc"
        text_color = "#1e293b"
        card_bg = "rgba(255, 255, 255, 0.9)"
        border_color = "rgba(0,0,0,0.1)"
    
    st.markdown(
        f"""
        <style>
        .stApp {{
            position: relative;
            min-height: 100vh;
            color: {text_color};
        }}

        .bg-cover:before {{
            content: "";
            position: fixed;
            inset: 0;
            background-image: url('{BACKGROUND_IMAGE_URL}');
            background-size: cover;
            background-position: center;
            filter: brightness(0.4) blur(1px);
            z-index: -1;
        }}

        /* Enhanced glass cards */
        .glass {{
            background: {card_bg};
            -webkit-backdrop-filter: blur(12px);
            backdrop-filter: blur(12px);
            border-radius: 20px;
            padding: 1.5rem;
            border: 1px solid {border_color};
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }}

        .glass-mini {{
            background: {card_bg};
            -webkit-backdrop-filter: blur(8px);
            backdrop-filter: blur(8px);
            border-radius: 12px;
            padding: 1rem;
            border: 1px solid {border_color};
            margin: 0.5rem 0;
        }}

        .section-title {{
            font-weight: 700;
            color: {text_color};
            margin: 0.4rem 0 0.8rem 0;
            font-size: 1.4rem;
        }}

        .accent {{
            color: {PRIMARY_ACCENT};
        }}

        .badge {{
            display: inline-block;
            padding: 0.3rem 0.8rem;
            border-radius: 999px;
            background: linear-gradient(135deg, {PRIMARY_ACCENT}, {SECONDARY_ACCENT});
            color: white;
            font-size: 0.8rem;
            font-weight: 600;
            margin: 0.2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}

        .metric-card {{
            background: {card_bg};
            padding: 1.5rem;
            border-radius: 16px;
            border: 1px solid {border_color};
            text-align: center;
            transition: transform 0.2s;
        }}

        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.15);
        }}

        .plan-card {{
            background: {card_bg};
            border-radius: 16px;
            padding: 1.5rem;
            border: 2px solid {border_color};
            transition: all 0.3s ease;
            margin: 1rem 0;
        }}

        .plan-card:hover {{
            border-color: {PRIMARY_ACCENT};
            transform: translateY(-4px);
            box-shadow: 0 16px 32px rgba(0,0,0,0.2);
        }}

        .price-tag {{
            font-size: 2rem;
            font-weight: 800;
            background: linear-gradient(135deg, {PRIMARY_ACCENT}, {SECONDARY_ACCENT});
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .progress-ring {{
            display: inline-block;
            vertical-align: middle;
        }}

        .notification {{
            background: linear-gradient(135deg, {WARNING_COLOR}, #fb923c);
            color: white;
            padding: 1rem;
            border-radius: 12px;
            margin: 0.5rem 0;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.8; }}
        }}

        /* Mobile responsive */
        @media (max-width: 768px) {{
            .glass {{
                padding: 1rem;
                margin: 0.5rem 0;
            }}
            .section-title {{
                font-size: 1.2rem;
            }}
        }}

        /* Chatbot styles */
        .chat-container {{
            max-height: 300px;
            overflow-y: auto;
            padding: 1rem;
            background: {card_bg};
            border-radius: 12px;
            border: 1px solid {border_color};
        }}

        .chat-message {{
            padding: 0.5rem 1rem;
            margin: 0.5rem 0;
            border-radius: 18px;
        }}

        .chat-user {{
            background: {PRIMARY_ACCENT};
            color: white;
            text-align: right;
            margin-left: 2rem;
        }}

        .chat-bot {{
            background: {card_bg};
            border: 1px solid {border_color};
            margin-right: 2rem;
        }}

        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<div class='bg-cover'></div>", unsafe_allow_html=True)

# =========================================
# CHATBOT FUNCTIONALITY
# =========================================
def process_chat_message(message: str) -> str:
    """Simple rule-based chatbot"""
    message = message.lower()
    
    if any(word in message for word in ["plan", "subscription", "package"]):
        return "I can help you find the perfect plan! Check out our marketplace or I can recommend based on your usage. What's your typical monthly data usage?"
    
    elif any(word in message for word in ["cancel", "stop", "end"]):
        return "You can cancel your subscription from your dashboard. Note that cancellation is only allowed after your current plan validity ends."
    
    elif any(word in message for word in ["price", "cost", "cheap", "expensive"]):
        return "Our plans range from ₹399 to ₹1999. The Starter 50 plan at ₹399 is great for basic usage, while Pro plans offer better value for heavy users."
    
    elif any(word in message for word in ["speed", "fast", "slow"]):
        return "We offer speeds from 50 Mbps to 1000 Mbps. For 4K streaming, I recommend at least 200 Mbps. For gaming, 500+ Mbps is ideal."
    
    elif any(word in message for word in ["usage", "data", "limit"]):
        return "Check your usage analytics in the dashboard. We provide daily and weekly breakdowns to help you track consumption."
    
    elif any(word in message for word in ["help", "support", "contact"]):
        return "I'm here to help! You can ask about plans, pricing, usage, or technical issues. For urgent issues, contact support at support@broadband.com"
    
    elif any(word in message for word in ["hello", "hi", "hey"]):
        return "Hello! 👋 Welcome to our broadband portal. How can I assist you today?"
    
    else:
        return "I'm still learning! For detailed help, please contact our support team or browse the FAQ section. Is there something specific about plans or usage I can help with?"

# =========================================
# ENHANCED PLANS FUNCTIONALITY
# =========================================
def add_plan(name: str, price, speed, cap, desc: str, category: str = "residential"):
    if not name or not price or not speed or cap is None:
        return False
    db.plans.insert_one({
        "name": name.strip(),
        "price": float(price),
        "speed_mbps": int(speed),
        "data_cap_gb": float(cap),
        "description": (desc or "").strip(),
        "category": category,
        "active": True,
        "created_at": now_utc().isoformat(),
        "features": [],
        "popularity_score": 0
    })
    return True

def get_plans(active_only=True, category=None):
    query = {}
    if active_only:
        query["active"] = True
    if category:
        query["category"] = category
    return list(db.plans.find(query))

def seed_enhanced_plans():
    enhanced_defaults = [
        {
            "name": "Starter 50", "price": 399, "speed_mbps": 50, "data_cap_gb": 150,
            "description": "Perfect for basic browsing & SD streaming", "category": "residential",
            "features": ["Basic support", "Email notifications", "Fair usage policy"]
        },
        {
            "name": "Family 100", "price": 699, "speed_mbps": 100, "data_cap_gb": 300,
            "description": "Ideal for families - HD streaming & video calls", "category": "residential",
            "features": ["Priority support", "Parental controls", "Multiple device support"]
        },
        {
            "name": "Pro 200", "price": 999, "speed_mbps": 200, "data_cap_gb": 600,
            "description": "Work-from-home + 4K streaming", "category": "professional",
            "features": ["24/7 support", "Static IP option", "Enhanced security"]
        },
        {
            "name": "Gamer 500", "price": 1299, "speed_mbps": 500, "data_cap_gb": 1000,
            "description": "Low latency gaming & streaming", "category": "gaming",
            "features": ["Gaming optimization", "DDoS protection", "Priority bandwidth"]
        },
        {
            "name": "Business 1000", "price": 1999, "speed_mbps": 1000, "data_cap_gb": 2000,
            "description": "Enterprise-grade connectivity", "category": "business",
            "features": ["SLA guarantee", "Dedicated support", "Custom configurations"]
        }
    ]
    
    existing = {p["name"] for p in db.plans.find({}, {"name": 1})}
    to_add = [p for p in enhanced_defaults if p["name"] not in existing]
    
    if to_add:
        for p in to_add:
            p["active"] = True
            p["created_at"] = now_utc().isoformat()
            p["popularity_score"] = 0
        db.plans.insert_many(to_add)
    return len(to_add)

# =========================================
# ENHANCED SUBSCRIPTIONS
# =========================================
def get_active_subscription(user_id):
    return db.subscriptions.find_one({"user_id": user_id, "status": "active"})

def get_subscription_history(user_id):
    return list(db.subscriptions.find({"user_id": user_id}).sort("created_at", -1))

def subscribe(user_id, plan_id):
    # Cancel existing active subscriptions
    db.subscriptions.update_many(
        {"user_id": user_id, "status": "active"}, 
        {"$set": {"status": "canceled", "canceled_at": now_utc().isoformat()}}
    )
    
    start = now_utc().date()
    end = start + timedelta(days=30)
    
    # Create new subscription
    db.subscriptions.insert_one({
        "user_id": user_id,
        "plan_id": plan_id,
        "status": "active",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "created_at": now_utc().isoformat(),
        "auto_renewal": True,
        "payment_method": "auto"
    })
    
    # Update plan popularity
    db.plans.update_one({"_id": plan_id}, {"$inc": {"popularity_score": 1}})

def upgrade_downgrade_plan(user_id, new_plan_id):
    """Handle plan upgrades/downgrades"""
    active_sub = get_active_subscription(user_id)
    if not active_sub:
        return False, "No active subscription found"
    
    old_plan = db.plans.find_one({"_id": active_sub["plan_id"]})
    new_plan = db.plans.find_one({"_id": new_plan_id})
    
    if not old_plan or not new_plan:
        return False, "Plan not found"
    
    # Calculate prorated pricing (simplified)
    days_remaining = (datetime.fromisoformat(active_sub["end_date"]).date() - now_utc().date()).days
    proration = (new_plan["price"] - old_plan["price"]) * (days_remaining / 30.0)
    
    # Update existing subscription
    db.subscriptions.update_one(
        {"_id": active_sub["_id"]},
        {"$set": {
            "plan_id": new_plan_id,
            "upgraded_at": now_utc().isoformat(),
            "proration_amount": proration
        }}
    )
    
    return True, f"Plan updated. Adjustment: {inr(proration)}"

# =========================================
# ENHANCED USAGE & ANALYTICS
# =========================================
def get_usage_logs(user_id):
    return list(db.usage_logs.find({"user_id": user_id}))

def seed_realistic_usage(user_id):
    """Create more realistic usage patterns"""
    if db.usage_logs.count_documents({"user_id": user_id}) > 0:
        return
    
    today = now_utc().date()
    base_usage = np.random.randint(5, 12)  # Base daily usage
    
    for i in range(90):  # 3 months of data
        day = today - timedelta(days=i)
        
        # Weekend usage spike
        if day.weekday() >= 5:  # Weekend
            usage = base_usage * np.random.uniform(1.5, 2.0)
        else:  # Weekday
            usage = base_usage * np.random.uniform(0.8, 1.2)
        
        # Add some random spikes for special events
        if np.random.random() < 0.1:  # 10% chance of spike
            usage *= np.random.uniform(2.0, 3.0)
        
        db.usage_logs.insert_one({
            "user_id": user_id,
            "date": day.isoformat(),
            "gb_used": round(float(usage), 2),
            "peak_hours": np.random.choice(["morning", "evening", "night"]),
            "device_count": np.random.randint(2, 6)
        })

def predict_future_usage(user_id, days_ahead=30):
    """Simple linear regression for usage prediction"""
    logs = get_usage_logs(user_id)
    if len(logs) < 7:
        return None
    
    df = pd.DataFrame(logs)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    df["day_number"] = (df["date"] - df["date"].min()).dt.days
    
    # Fit linear regression
    X = df["day_number"].values.reshape(-1, 1)
    y = df["gb_used"].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # Predict future
    last_day = df["day_number"].max()
    future_days = np.arange(last_day + 1, last_day + days_ahead + 1).reshape(-1, 1)
    predictions = model.predict(future_days)
    
    return {
        "total_predicted": float(np.sum(predictions)),
        "daily_average": float(np.mean(predictions)),
        "trend": "increasing" if model.coef_[0] > 0 else "decreasing"
    }

# =========================================
# SMART NOTIFICATIONS
# =========================================
def get_user_notifications(user_id):
    """Generate smart notifications based on usage and subscription"""
    notifications = []
    
    active_sub = get_active_subscription(user_id)
    if not active_sub:
        notifications.append({
            "type": "warning",
            "title": "No Active Plan",
            "message": "Subscribe to a plan to start using our services!",
            "action": "subscribe"
        })
        return notifications
    
    # Usage-based notifications
    usage_logs = get_usage_logs(user_id)
    if usage_logs:
        df = pd.DataFrame(usage_logs)
        df["date"] = pd.to_datetime(df["date"])
        
        # Current month usage
        current_month = df[df["date"] >= first_day_of_current_month()]
        if not current_month.empty:
            monthly_usage = current_month["gb_used"].sum()
            plan = db.plans.find_one({"_id": active_sub["plan_id"]})
            
            if plan and monthly_usage > plan["data_cap_gb"] * 0.8:
                notifications.append({
                    "type": "warning",
                    "title": "High Usage Alert",
                    "message": f"You've used {monthly_usage:.1f}GB of your {plan['data_cap_gb']}GB limit",
                    "action": "upgrade"
                })
            
            # Predict if user will exceed limit
            prediction = predict_future_usage(user_id)
            if prediction and plan:
                days_remaining = (datetime.fromisoformat(active_sub["end_date"]).date() - now_utc().date()).days
                predicted_total = monthly_usage + (prediction["daily_average"] * days_remaining)
                
                if predicted_total > plan["data_cap_gb"]:
                    notifications.append({
                        "type": "info",
                        "title": "Usage Prediction",
                        "message": f"You may exceed your data limit by {predicted_total - plan['data_cap_gb']:.1f}GB",
                        "action": "upgrade"
                    })
    
    # Subscription expiry notification
    end_date = datetime.fromisoformat(active_sub["end_date"]).date()
    days_left = (end_date - now_utc().date()).days
    
    if days_left <= 3:
        notifications.append({
            "type": "warning",
            "title": "Subscription Expiring",
            "message": f"Your subscription expires in {days_left} days",
            "action": "renew"
        })
    
    return notifications

# =========================================
# ENHANCED USER DASHBOARD
# =========================================
def enhanced_user_dashboard(user):
    seed_realistic_usage(user["_id"])
    
    # Language and theme controls
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        if st.button("🌓 Toggle Dark Mode"):
            st.session_state.dark_mode = not st.session_state.dark_mode
            st.rerun()
    
    with col2:
        lang = st.selectbox("🌐", ["en", "hi"], index=0 if st.session_state.language == "en" else 1)
        if lang != st.session_state.language:
            st.session_state.language = lang
            st.rerun()
    
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown(f"<h2 class='section-title'>👋 {get_text('welcome')}, {user['name']}</h2>", unsafe_allow_html=True)
    
    # User score and badges
    score = calculate_user_score(user["_id"])
    badges = get_user_badges(user["_id"])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>🏆 User Score</h3>
            <div style='font-size: 2rem; font-weight: bold; color: {PRIMARY_ACCENT};'>{score}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        active_sub = get_active_subscription(user["_id"])
        status = "🟢 Active" if active_sub else "🔴 Inactive"
        st.markdown(f"""
        <div class='metric-card'>
            <h3>📶 Status</h3>
            <div style='font-size: 1.2rem; font-weight: bold;'>{status}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class='metric-card'>
            <h3>🏅 Badges</h3>
            <div>{len(badges)} earned</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Display badges
    if badges:
        st.markdown("**Your Achievements:**")
        for badge in badges:
            st.markdown(f"<span class='badge'>{badge['name']}</span>", unsafe_allow_html=True)
    
    st.divider()
    
    # Smart notifications
    notifications = get_user_notifications(user["_id"])
    if notifications:
        st.markdown("### 🔔 Smart Notifications")
        for notif in notifications:
            if notif["type"] == "warning":
                st.warning(f"**{notif['title']}**: {notif['message']}")
            else:
                st.info(f"**{notif['title']}**: {notif['message']}")
    
    st.divider()
    
    # Current subscription with enhanced details
    st.markdown("### 📦 Current Subscription")
    if active_sub:
        plan = db.plans.find_one({"_id": active_sub["plan_id"]})
        if plan:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"""
                <div class='plan-card'>
                    <h3>{plan['name']}</h3>
                    <div class='price-tag'>{inr(plan['price'])}</div>
                    <p><strong>Speed:</strong> {plan['speed_mbps']} Mbps</p>
                    <p><strong>Data Cap:</strong> {plan['data_cap_gb']} GB</p>
                    <p><strong>Valid Until:</strong> {active_sub['end_date']}</p>
                    <p><strong>Features:</strong></p>
                    <ul>
                        {''.join([f"<li>{feature}</li>" for feature in plan.get('features', [])])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("**Quick Actions:**")
                if st.button("🔄 Upgrade Plan", use_container_width=True):
                    st.session_state["action"] = "upgrade"
                    st.rerun()
                
                if st.button("⏸️ Vacation Mode", use_container_width=True):
                    st.session_state["action"] = "vacation"
                    st.rerun()
                
                # Cancellation logic
                end_date = datetime.fromisoformat(active_sub["end_date"]).date()
                days_left = (end_date - now_utc().date()).days
                
                if days_left <= 0:
                    if st.button("❌ Cancel Subscription", type="secondary", use_container_width=True):
                        cancel_subscription_if_allowed(user["_id"])
                        st.success("Subscription canceled!")
                        st.rerun()
                else:
                    st.caption(f"Cancel available in {days_left} days")
    else:
        st.warning("No active subscription. Browse our marketplace to get started!")
        if st.button("🛒 Browse Plans", type="primary"):
            st.session_state["menu"] = "Marketplace"
            st.rerun()
    
    st.divider()
    
    # Enhanced Analytics with predictions
    st.markdown("### 📊 Usage Analytics & Predictions")
    
    usage_logs = get_usage_logs(user["_id"])
    if usage_logs:
        df = pd.DataFrame(usage_logs)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
        
        # Current month usage
        current_month = df[df["date"] >= first_day_of_current_month()]
        
        if not current_month.empty:
            # Usage metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                total_usage = current_month["gb_used"].sum()
                st.metric("📈 This Month", f"{total_usage:.1f} GB")
            
            with col2:
                daily_avg = current_month["gb_used"].mean()
                st.metric("📅 Daily Average", f"{daily_avg:.1f} GB")
            
            with col3:
                if active_sub and plan:
                    remaining = max(0, plan["data_cap_gb"] - total_usage)
                    st.metric("💾 Remaining", f"{remaining:.1f} GB")
            
            with col4:
                prediction = predict_future_usage(user["_id"])
                if prediction:
                    st.metric("🔮 Predicted (30d)", f"{prediction['daily_average']:.1f} GB/day")
            
            # Interactive charts
            tab1, tab2, tab3 = st.tabs(["📈 Daily Usage", "📊 Weekly Trends", "🎯 Usage Patterns"])
            
            with tab1:
                fig = px.line(current_month, x="date", y="gb_used", 
                            title="Daily Usage This Month",
                            color_discrete_sequence=[PRIMARY_ACCENT])
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                weekly = current_month.copy()
                weekly["week"] = weekly["date"].dt.isocalendar().week
                weekly_agg = weekly.groupby("week")["gb_used"].sum().reset_index()
                
                fig = px.bar(weekly_agg, x="week", y="gb_used",
                           title="Weekly Usage Comparison",
                           color="gb_used",
                           color_continuous_scale="viridis")
                st.plotly_chart(fig, use_container_width=True)
            
            with tab3:
                if "peak_hours" in df.columns:
                    peak_hours = df["peak_hours"].value_counts()
                    fig = px.pie(names=peak_hours.index, values=peak_hours.values,
                               title="Peak Usage Hours Distribution")
                    st.plotly_chart(fig, use_container_width=True)
                
                # Device usage if available
                if "device_count" in df.columns:
                    avg_devices = df["device_count"].mean()
                    st.info(f"📱 Average devices connected: {avg_devices:.1f}")
    
    # AI Recommendations
    st.divider()
    st.markdown("### 🤖 AI-Powered Recommendations")
    
    rec_plan_id = recommend_plan_for_user(user["_id"])
    if rec_plan_id and rec_plan_id != str(active_sub["plan_id"]) if active_sub else True:
        rec_plan = db.plans.find_one({"_id": safe_objectid(rec_plan_id)})
        if rec_plan:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.success(f"""
                **Recommended:** {rec_plan['name']} - {inr(rec_plan['price'])}
                
                Based on your usage patterns, this plan offers better value with {rec_plan['speed_mbps']} Mbps 
                and {rec_plan['data_cap_gb']} GB data cap.
                """)
            with col2:
                if st.button("✨ Switch to Recommended", type="primary"):
                    if active_sub:
                        success, message = upgrade_downgrade_plan(user["_id"], rec_plan["_id"])
                        if success:
                            st.success(f"Plan updated! {message}")
                        else:
                            st.error(message)
                    else:
                        subscribe(user["_id"], rec_plan["_id"])
                        st.success("Subscribed to recommended plan!")
                    st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Chatbot section
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("### 🤖 AI Assistant")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    # Chat interface
    with st.container():
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        for msg in st.session_state.chat_history[-5:]:  # Show last 5 messages
            if msg["role"] == "user":
                st.markdown(f"<div class='chat-message chat-user'>{msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='chat-message chat-bot'>🤖 {msg['content']}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Chat input
    chat_input = st.text_input("Ask me anything about plans, usage, or technical support:", 
                              placeholder="e.g., 'Which plan is best for gaming?'")
    
    if chat_input:
        st.session_state.chat_history.append({"role": "user", "content": chat_input})
        bot_response = process_chat_message(chat_input)
        st.session_state.chat_history.append({"role": "bot", "content": bot_response})
        st.rerun()
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# Handle special actions
def handle_user_actions(user):
    if "action" in st.session_state:
        action = st.session_state["action"]
        
        if action == "upgrade":
            st.markdown("### 🚀 Upgrade Your Plan")
            current_sub = get_active_subscription(user["_id"])
            if current_sub:
                current_plan = db.plans.find_one({"_id": current_sub["plan_id"]})
                better_plans = [p for p in get_plans() if p["price"] > current_plan["price"]]
                
                if better_plans:
                    selected_plan = st.selectbox("Choose a better plan:", 
                                               [p["name"] for p in better_plans])
                    selected_plan_obj = next(p for p in better_plans if p["name"] == selected_plan)
                    
                    st.info(f"Upgrade to {selected_plan} for {inr(selected_plan_obj['price'])}")
                    
                    if st.button("Confirm Upgrade"):
                        success, message = upgrade_downgrade_plan(user["_id"], selected_plan_obj["_id"])
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                        del st.session_state["action"]
                        st.rerun()
        
        elif action == "vacation":
            st.markdown("### 🏖️ Vacation Mode")
            st.info("Vacation mode will pause your subscription and reduce charges.")
            
            vacation_days = st.slider("Vacation duration (days):", 1, 30, 7)
            
            if st.button("Enable Vacation Mode"):
                db.users.update_one(
                    {"_id": user["_id"]}, 
                    {"$set": {"vacation_mode": True, "vacation_days": vacation_days}}
                )
                st.success(f"Vacation mode enabled for {vacation_days} days!")
                del st.session_state["action"]
                st.rerun()
        
        if st.button("← Back to Dashboard"):
            del st.session_state["action"]
            st.rerun()

# =========================================
# ENHANCED MARKETPLACE
# =========================================
def enhanced_marketplace(user):
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("### 🛒 Plan Marketplace")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        category_filter = st.selectbox("Category:", 
                                     ["All", "residential", "professional", "gaming", "business"])
    with col2:
        price_range = st.slider("Price Range (₹):", 0, 2500, (0, 2500))
    with col3:
        sort_by = st.selectbox("Sort by:", ["Price", "Speed", "Popularity"])
    
    # Get and filter plans
    plans = get_plans(active_only=True)
    if category_filter != "All":
        plans = [p for p in plans if p.get("category") == category_filter]
    
    plans = [p for p in plans if price_range[0] <= p["price"] <= price_range[1]]
    
    # Sort plans
    if sort_by == "Price":
        plans.sort(key=lambda x: x["price"])
    elif sort_by == "Speed":
        plans.sort(key=lambda x: x["speed_mbps"], reverse=True)
    elif sort_by == "Popularity":
        plans.sort(key=lambda x: x.get("popularity_score", 0), reverse=True)
    
    # Display plans in a grid
    if plans:
        for i in range(0, len(plans), 3):
            cols = st.columns(3)
            for j, plan in enumerate(plans[i:i+3]):
                with cols[j]:
                    # Check if this is user's current plan
                    current_sub = get_active_subscription(user["_id"])
                    is_current = current_sub and current_sub["plan_id"] == plan["_id"]
                    
                    card_style = "border: 3px solid #10b981;" if is_current else ""
                    
                    st.markdown(f"""
                    <div class='plan-card' style='{card_style}'>
                        <h3>{plan['name']}</h3>
                        {f"<span class='badge'>Current Plan</span>" if is_current else ""}
                        <div class='price-tag'>{inr(plan['price'])}</div>
                        <p><strong>Speed:</strong> {plan['speed_mbps']} Mbps</p>
                        <p><strong>Data:</strong> {plan['data_cap_gb']} GB</p>
                        <p><strong>Category:</strong> {plan.get('category', 'residential').title()}</p>
                        <p>{plan.get('description', '')}</p>
                        <p><strong>Features:</strong></p>
                        <ul>
                            {''.join([f"<li>{feature}</li>" for feature in plan.get('features', [])])}
                        </ul>
                        <p><small>🔥 {plan.get('popularity_score', 0)} users chose this</small></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if not is_current:
                        if st.button(f"Subscribe to {plan['name']}", 
                                   key=f"sub_{plan['_id']}", 
                                   use_container_width=True,
                                   type="primary"):
                            if current_sub:
                                # This is an upgrade/downgrade
                                success, message = upgrade_downgrade_plan(user["_id"], plan["_id"])
                                if success:
                                    st.success(f"Plan changed! {message}")
                                else:
                                    st.error(message)
                            else:
                                # New subscription
                                subscribe(user["_id"], plan["_id"])
                                st.success(f"Subscribed to {plan['name']}!")
                            st.rerun()
                    else:
                        st.success("✅ Your Current Plan")
    else:
        st.info("No plans match your filters. Try adjusting the criteria.")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Plan comparison tool
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("### ⚖️ Plan Comparison")
    
    all_plans = get_plans(active_only=True)
    if len(all_plans) >= 2:
        selected_plans = st.multiselect("Select plans to compare:", 
                                      [p["name"] for p in all_plans],
                                      max_selections=3)
        
        if len(selected_plans) >= 2:
            comparison_data = []
            for plan_name in selected_plans:
                plan = next(p for p in all_plans if p["name"] == plan_name)
                comparison_data.append({
                    "Plan": plan["name"],
                    "Price (₹)": plan["price"],
                    "Speed (Mbps)": plan["speed_mbps"],
                    "Data (GB)": plan["data_cap_gb"],
                    "Value Score": round(plan["speed_mbps"] / plan["price"] * 100, 2)
                })
            
            df_comparison = pd.DataFrame(comparison_data)
            st.dataframe(df_comparison, use_container_width=True)
            
            # Comparison chart
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Price (₹)', x=df_comparison['Plan'], y=df_comparison['Price (₹)']))
            fig.add_trace(go.Bar(name='Speed (Mbps)', x=df_comparison['Plan'], y=df_comparison['Speed (Mbps)']))
            fig.update_layout(title="Plan Comparison", barmode='group')
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# ENHANCED ADMIN DASHBOARD
# =========================================
def enhanced_admin_dashboard():
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("### 🛠️ Admin Dashboard")
    
    # Quick stats
    total_users = db.users.count_documents({})
    active_subs = db.subscriptions.count_documents({"status": "active"})
    total_revenue = sum([p["price"] for p in db.plans.find({}) 
                        for _ in range(db.subscriptions.count_documents({"plan_id": p["_id"]}))])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("👥 Total Users", total_users)
    with col2:
        st.metric("📶 Active Subscriptions", active_subs)
    with col3:
        st.metric("💰 Revenue", inr(total_revenue))
    with col4:
        churn_rate = (db.subscriptions.count_documents({"status": "canceled"}) / 
                     max(1, db.subscriptions.count_documents({}))) * 100
        st.metric("📉 Churn Rate", f"{churn_rate:.1f}%")
    
    st.divider()
    
    # Admin actions
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🌱 Seed Enhanced Plans", use_container_width=True):
            added = seed_enhanced_plans()
            if added > 0:
                st.success(f"Added {added} enhanced plans!")
            else:
                st.info("All plans already exist.")
            st.rerun()
    
    with col2:
        if st.button("📊 Generate Report", use_container_width=True):
            st.session_state["admin_action"] = "report"
            st.rerun()
    
    with col3:
        if st.button("👥 User Management", use_container_width=True):
            st.session_state["admin_action"] = "users"
            st.rerun()
    
    # Handle admin actions
    if "admin_action" in st.session_state:
        action = st.session_state["admin_action"]
        
        if action == "report":
            st.markdown("### 📈 Analytics Report")
            
            # Subscription trends
            all_subs = list(db.subscriptions.find({}))
            if all_subs:
                df_subs = pd.DataFrame(all_subs)
                df_subs["created_at"] = pd.to_datetime(df_subs["created_at"])
                
                # Monthly subscription trends
                monthly_subs = df_subs.groupby(df_subs["created_at"].dt.to_period("M")).size()
                fig = px.line(x=monthly_subs.index.astype(str), y=monthly_subs.values,
                            title="Monthly Subscription Trends")
                st.plotly_chart(fig, use_container_width=True)
                
                # Plan popularity
                plan_counts = {}
                for sub in all_subs:
                    plan = db.plans.find_one({"_id": sub["plan_id"]})
                    if plan:
                        plan_counts[plan["name"]] = plan_counts.get(plan["name"], 0) + 1
                
                if plan_counts:
                    fig = px.pie(names=list(plan_counts.keys()), values=list(plan_counts.values()),
                               title="Plan Popularity Distribution")
                    st.plotly_chart(fig, use_container_width=True)
            
            # Export functionality
            if st.button("📥 Export Report as CSV"):
                report_data = {
                    "metric": ["Total Users", "Active Subscriptions", "Total Revenue", "Churn Rate"],
                    "value": [total_users, active_subs, total_revenue, f"{churn_rate:.1f}%"]
                }
                df_report = pd.DataFrame(report_data)
                csv = df_report.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name="admin_report.csv",
                    mime="text/csv"
                )
        
        elif action == "users":
            st.markdown("### 👥 User Management")
            
            users = list(db.users.find({"role": "user"}))
            if users:
                user_data = []
                for u in users:
                    active_sub = get_active_subscription(u["_id"])
                    plan_name = "None"
                    if active_sub:
                        plan = db.plans.find_one({"_id": active_sub["plan_id"]})
                        if plan:
                            plan_name = plan["name"]
                    
                    user_data.append({
                        "Name": u["name"],
                        "Email": u["email"],
                        "Current Plan": plan_name,
                        "User Score": calculate_user_score(u["_id"]),
                        "Joined": u["created_at"][:10] if "created_at" in u else "Unknown"
                    })
                
                df_users = pd.DataFrame(user_data)
                st.dataframe(df_users, use_container_width=True)
                
                # User analytics
                fig = px.histogram(df_users, x="User Score", nbins=20, 
                                 title="User Score Distribution")
                st.plotly_chart(fig, use_container_width=True)
        
        if st.button("← Back to Admin Dashboard"):
            del st.session_state["admin_action"]
            st.rerun()
    
    st.divider()
    
    # Plan management (simplified version)
    st.markdown("### 📦 Quick Plan Management")
    
    with st.expander("➕ Add New Plan"):
        col1, col2 = st.columns(2)
        with col1:
            plan_name = st.text_input("Plan Name")
            plan_price = st.number_input("Price (₹)", min_value=1.0, step=1.0)
            plan_speed = st.number_input("Speed (Mbps)", min_value=1, step=1)
        with col2:
            plan_data = st.number_input("Data Cap (GB)", min_value=1.0, step=1.0)
            plan_category = st.selectbox("Category", 
                                       ["residential", "professional", "gaming", "business"])
            plan_desc = st.text_area("Description")
        
        if st.button("Add Plan"):
            if add_plan(plan_name, plan_price, plan_speed, plan_data, plan_desc, plan_category):
                st.success(f"Plan '{plan_name}' added successfully!")
                st.rerun()
            else:
                st.error("Please fill all required fields.")
    
    # Active plans overview
    plans = get_plans(active_only=False)
    if plans:
        plan_data = [{
            "Name": p["name"],
            "Price": inr(p["price"]),
            "Speed": f"{p['speed_mbps']} Mbps",
            "Data": f"{p['data_cap_gb']} GB",
            "Category": p.get("category", "residential").title(),
            "Active": "✅" if p["active"] else "❌",
            "Popularity": p.get("popularity_score", 0)
        } for p in plans]
        
        df_plans = pd.DataFrame(plan_data)
        st.dataframe(df_plans, use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# NAVIGATION & MAIN APP
# =========================================
def sidebar_nav(user):
    st.sidebar.markdown(f"### 👤 {user['name']}")
    st.sidebar.markdown(f"**Role:** {user['role'].title()}")
    
    if user["role"] == "admin":
        menu_items = ["Admin Dashboard", "Analytics", "Logout"]
    else:
        menu_items = ["Dashboard", "Marketplace", "Analytics", "Profile", "Logout"]
    
    menu = st.sidebar.selectbox("🧭 Navigate", menu_items)
    
    # Quick stats in sidebar
    if user["role"] == "user":
        active_sub = get_active_subscription(user["_id"])
        if active_sub:
            plan = db.plans.find_one({"_id": active_sub["plan_id"]})
            if plan:
                st.sidebar.markdown("---")
                st.sidebar.markdown("**Current Plan:**")
                st.sidebar.info(f"📦 {plan['name']}\n💰 {inr(plan['price'])}")
        
        # User score
        score = calculate_user_score(user["_id"])
        st.sidebar.markdown(f"**🏆 Score:** {score}")
    
    return menu

def user_profile_page(user):
    """Enhanced user profile management"""
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("### 👤 User Profile")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("#### Account Info")
        st.text_input("Name", value=user["name"], disabled=True)
        st.text_input("Email", value=user["email"], disabled=True)
        st.text_input("Role", value=user["role"].title(), disabled=True)
        
        # User preferences
        st.markdown("#### Preferences")
        budget_limit = st.number_input("Monthly Budget Limit (₹)", 
                                     value=user.get("budget_limit", 1500.0), 
                                     min_value=100.0, step=50.0)
        
        vacation_mode = st.checkbox("Vacation Mode", 
                                  value=user.get("vacation_mode", False))
        
        if st.button("💾 Save Preferences"):
            db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "budget_limit": budget_limit,
                    "vacation_mode": vacation_mode
                }}
            )
            st.success("Preferences updated!")
            st.rerun()
    
    with col2:
        st.markdown("#### Notification Settings")
        notif_prefs = user.get("notification_preferences", {})
        
        email_notif = st.checkbox("📧 Email Notifications", 
                                value=notif_prefs.get("email", True))
        sms_notif = st.checkbox("📱 SMS Notifications", 
                              value=notif_prefs.get("sms", False))
        push_notif = st.checkbox("🔔 Push Notifications", 
                               value=notif_prefs.get("push", True))
        
        if st.button("🔔 Update Notifications"):
            db.users.update_one(
                {"_id": user["_id"]},
                {"$set": {
                    "notification_preferences": {
                        "email": email_notif,
                        "sms": sms_notif,
                        "push": push_notif
                    }
                }}
            )
            st.success("Notification preferences updated!")
        
        st.markdown("#### Account Actions")
        if st.button("🗑️ Delete My Data", type="secondary"):
            st.warning("This will delete all your usage data but keep your account.")
            if st.button("⚠️ Confirm Delete Data"):
                db.usage_logs.delete_many({"user_id": user["_id"]})
                st.success("Usage data deleted successfully!")
                st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

def analytics_page(user):
    """Dedicated analytics page"""
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("### 📊 Advanced Analytics")
    
    if user["role"] == "admin":
        # Admin analytics
        st.markdown("#### System-wide Analytics")
        
        # Market trends
        all_subs = list(db.subscriptions.find({}))
        if all_subs:
            df_subs = pd.DataFrame(all_subs)
            df_subs["created_at"] = pd.to_datetime(df_subs["created_at"])
            
            # Growth trend
            daily_subs = df_subs.groupby(df_subs["created_at"].dt.date).size().cumsum()
            fig = px.line(x=daily_subs.index, y=daily_subs.values,
                        title="Cumulative Subscriptions Growth")
            st.plotly_chart(fig, use_container_width=True)
        
        # Revenue forecasting (simple)
        st.markdown("#### Revenue Forecasting")
        if all_subs and len(all_subs) > 10:
            # Simple linear projection
            recent_revenue = []
            for i in range(30):  # Last 30 days
                day = (datetime.now() - timedelta(days=i)).date()
                day_subs = [s for s in all_subs 
                           if datetime.fromisoformat(s["created_at"]).date() == day]
                day_revenue = sum([db.plans.find_one({"_id": s["plan_id"]})["price"] 
                                 for s in day_subs 
                                 if db.plans.find_one({"_id": s["plan_id"]})])
                recent_revenue.append(day_revenue)
            
            # Project next 30 days
            avg_daily_revenue = np.mean(recent_revenue)
            projected_monthly = avg_daily_revenue * 30
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("📈 Avg Daily Revenue", inr(avg_daily_revenue))
            with col2:
                st.metric("🎯 Projected Monthly", inr(projected_monthly))
    
    else:
        # User analytics
        st.markdown("#### Personal Usage Analytics")
        
        usage_logs = get_usage_logs(user["_id"])
        if usage_logs:
            df = pd.DataFrame(usage_logs)
            df["date"] = pd.to_datetime(df["date"])
            
            # Usage patterns
            df["day_of_week"] = df["date"].dt.day_name()
            df["hour"] = df["date"].dt.hour if "hour" in df.columns else 12  # Mock hour
            
            # Weekly pattern
            weekly_pattern = df.groupby("day_of_week")["gb_used"].mean().reindex([
                "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
            ])
            
            fig = px.bar(x=weekly_pattern.index, y=weekly_pattern.values,
                       title="Average Usage by Day of Week")
            st.plotly_chart(fig, use_container_width=True)
            
            # Usage efficiency score
            active_sub = get_active_subscription(user["_id"])
            if active_sub:
                plan = db.plans.find_one({"_id": active_sub["plan_id"]})
                if plan:
                    current_month = df[df["date"] >= first_day_of_current_month()]
                    if not current_month.empty:
                        usage_ratio = current_month["gb_used"].sum() / plan["data_cap_gb"]
                        efficiency_score = min(100, usage_ratio * 100)
                        
                        st.metric("📊 Plan Efficiency", f"{efficiency_score:.1f}%")
                        
                        if efficiency_score < 50:
                            st.info("💡 You might save money with a smaller plan!")
                        elif efficiency_score > 90:
                            st.warning("⚠️ Consider upgrading to avoid overage!")
    
    st.markdown("</div>", unsafe_allow_html=True)

def login_page():
    """Enhanced login page with better UX"""
    inject_global_css()
    
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown("<h2 class='section-title'>🔐 Welcome to <span class='accent'>Broadband Portal</span></h2>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Login", "📝 Sign Up"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("📧 Email")
            password = st.text_input("🔒 Password", type="password")
            remember_me = st.checkbox("Remember me")
            
            col1, col2 = st.columns(2)
            with col1:
                login_btn = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")
            with col2:
                demo_btn = st.form_submit_button("👤 Demo User", use_container_width=True)
            
            if login_btn:
                user = check_login(email, password)
                if user:
                    st.session_state.user = user
                    st.session_state["login_time"] = datetime.now(timezone.utc).timestamp()
                    if remember_me:
                        st.session_state["remember_login"] = True
                    st.success(f"Welcome back, {user['name']}! 🎉")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials. Please try again.")
            
            if demo_btn:
                # Create or login as demo user
                demo_email = "demo@user.com"
                demo_user = db.users.find_one({"email": demo_email})
                if not demo_user:
                    create_user(demo_email, "Demo User", "demo123", "user")
                    demo_user = db.users.find_one({"email": demo_email})
                
                st.session_state.user = demo_user
                st.session_state["login_time"] = datetime.now(timezone.utc).timestamp()
                st.success("🎯 Logged in as Demo User!")
                st.rerun()
    
    with tab2:
        with st.form("register_form"):
            name = st.text_input("👤 Full Name")
            email = st.text_input("📧 Email Address") 
            password = st.text_input("🔒 Create Password", type="password")
            confirm_password = st.text_input("🔒 Confirm Password", type="password")
            
            terms = st.checkbox("I agree to Terms & Conditions")
            newsletter = st.checkbox("Subscribe to newsletter (optional)")
            
            signup_btn = st.form_submit_button("✨ Create Account", use_container_width=True, type="primary")
            
            if signup_btn:
                if not terms:
                    st.error("❌ Please accept Terms & Conditions")
                elif password != confirm_password:
                    st.error("❌ Passwords don't match")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                else:
                    success = create_user(email, name, password, "user")
                    if success:
                        st.success("🎉 Account created successfully! Please login.")
                        # Auto-switch to login tab would be nice, but Streamlit limitation
                    else:
                        st.error("❌ Email already exists or invalid input")
    
    # Quick demo info
    st.markdown("---")
    st.markdown("**🎯 Quick Demo Access:**")
    col1, col2 = st.columns(2)
    with col1:
        st.info("**Demo User**\n📧 demo@user.com\n🔒 demo123")
    with col2:
        st.info("**Admin Access**\n📧 admin@portal.com\n🔒 admin123")
    
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# MAIN APPLICATION LOGIC
# =========================================
def main():
    ensure_admin_exists()
    check_session_timeout()
    inject_global_css()
    
    user = st.session_state.get("user")
    if not user:
        login_page()
        return
    
    # Main navigation
    menu = sidebar_nav(user)
    
    # Handle special user actions first
    if "action" in st.session_state:
        handle_user_actions(user)
        return
    
    # Route to appropriate page based on menu selection
    if user["role"] == "admin":
        if menu == "Admin Dashboard":
            enhanced_admin_dashboard()
        elif menu == "Analytics":
            analytics_page(user)
        elif menu == "Logout":
            st.session_state.clear()
            st.success("👋 Logged out successfully!")
            st.rerun()
    else:
        if menu == "Dashboard":
            enhanced_user_dashboard(user)
        elif menu == "Marketplace":
            enhanced_marketplace(user)
        elif menu == "Analytics":
            analytics_page(user)
        elif menu == "Profile":
            user_profile_page(user)
        elif menu == "Logout":
            st.session_state.clear()
            st.success("👋 Thanks for using our portal!")
            st.rerun()

# =========================================
# ENHANCED UTILITIES & FEATURES
# =========================================
def cancel_subscription_if_allowed(user_id) -> tuple[bool, str]:
    """Enhanced cancellation logic"""
    active = get_active_subscription(user_id)
    if not active:
        return False, "No active subscription found."
    
    end_date = datetime.fromisoformat(active["end_date"]).date()
    today = now_utc().date()
    
    if today >= end_date:
        db.subscriptions.update_many(
            {"user_id": user_id, "status": "active"}, 
            {"$set": {
                "status": "canceled",
                "canceled_at": now_utc().isoformat(),
                "cancellation_reason": "user_request"
            }}
        )
        return True, "✅ Subscription canceled successfully!"
    else:
        days_remaining = (end_date - today).days
        return False, f"❌ Cancellation available in {days_remaining} days (after plan validity ends)"

def recommend_plan_for_user(user_id) -> str | None:
    """Enhanced AI recommendation system"""
    plans = get_plans(active_only=True)
    if not plans:
        return None
    
    usage_logs = get_usage_logs(user_id)
    user = db.users.find_one({"_id": user_id})
    
    if not usage_logs:
        # New user - recommend based on budget
        budget = user.get("budget_limit", 1500.0) if user else 1500.0
        suitable_plans = [p for p in plans if p["price"] <= budget]
        if suitable_plans:
            # Best value for budget
            best_plan = max(suitable_plans, key=lambda x: x["speed_mbps"] / x["price"])
            return str(best_plan["_id"])
        return str(plans[0]["_id"])  # Fallback to first plan
    
    # Analyze usage patterns
    df = pd.DataFrame(usage_logs)
    df["date"] = pd.to_datetime(df["date"])
    
    # Recent usage (last 30 days)
    recent = df[df["date"] >= (datetime.now() - timedelta(days=30))]
    if recent.empty:
        recent = df.tail(30)  # Fallback to last 30 records
    
    avg_daily = recent["gb_used"].mean()
    peak_usage = recent["gb_used"].quantile(0.95)  # 95th percentile
    monthly_projection = avg_daily * 30
    
    # Score plans based on usage patterns
    plan_scores = []
    for plan in plans:
        # Data adequacy score (prefer 20% buffer)
        data_score = 1.0 if plan["data_cap_gb"] >= monthly_projection * 1.2 else 0.5
        
        # Speed adequacy (heuristic: 1 Mbps per 2GB monthly usage)
        recommended_speed = max(50, monthly_projection * 0.5)
        speed_score = min(1.0, plan["speed_mbps"] / recommended_speed)
        
        # Price efficiency
        price_score = 1.0 / (1.0 + (plan["price"] - 500) / 1000)  # Normalize around ₹500
        
        # Budget fit
        budget = user.get("budget_limit", 2000.0) if user else 2000.0
        budget_score = 1.0 if plan["price"] <= budget else 0.3
        
        # Popularity bonus
        popularity_score = min(0.3, plan.get("popularity_score", 0) / 100.0)
        
        total_score = (data_score * 0.3 + speed_score * 0.25 + 
                      price_score * 0.2 + budget_score * 0.2 + popularity_score * 0.05)
        
        plan_scores.append((plan["_id"], total_score))
    
    # Return best scoring plan
    best_plan_id = max(plan_scores, key=lambda x: x[1])[0]
    return str(best_plan_id)

# Add mobile responsiveness helper
def is_mobile():
    """Detect if user is on mobile (simple heuristic)"""
    # This is a simplified approach - in real apps, use JavaScript detection
    return False  # Streamlit doesn't have built-in mobile detection

# =========================================
# ADDITIONAL FEATURES
# =========================================

# Leaderboard functionality
def get_leaderboard():
    """Get top users by score for gamification"""
    users = list(db.users.find({"role": "user"}))
    user_scores = []
    
    for user in users:
        score = calculate_user_score(user["_id"])
        user_scores.append({
            "name": user["name"],
            "score": score,
            "badges": len(get_user_badges(user["_id"]))
        })
    
    return sorted(user_scores, key=lambda x: x["score"], reverse=True)[:10]

# Add leaderboard to sidebar for users
def show_leaderboard_sidebar():
    """Show mini leaderboard in sidebar"""
    with st.sidebar.expander("🏆 Top Users"):
        leaderboard = get_leaderboard()
        for i, user_data in enumerate(leaderboard[:5], 1):
            emoji = ["🥇", "🥈", "🥉", "🏅", "🏅"][i-1] if i <= 5 else "🏅"
            st.write(f"{emoji} {user_data['name'][:15]}... ({user_data['score']})")

# =========================================
# RUN THE APPLICATION
# =========================================
if __name__ == "__main__":
    main()
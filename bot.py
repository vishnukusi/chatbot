import streamlit as st
from openai import OpenAI
import os
from pymongo import MongoClient

# ---------- CONFIG ----------
st.set_page_config(page_title="AI Goal Tracker", layout="wide")

# ---------- ENV ----------

MONGO_URI = os.getenv("mongodb://localhost:27017/")  # e.g. mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME = os.getenv("MONGO_DB", "ai_goal_tracker")
USER_ID = os.getenv("vishnu", "default_user")
GROQ_API_KEY = "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"

st.write("DEBUG KEY:", GROQ_API_KEY)  # temporary

if GROQ_API_KEY is None or GROQ_API_KEY.strip() == "":
    st.error("Set GROQ_API_KEY env var")
    st.stop()
if not MONGO_URI:
    st.error("Set MONGO_URI env var"); st.stop()

# ---------- CLIENTS ----------
client_ai = OpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
mongo = MongoClient(MONGO_URI)
db = mongo[DB_NAME]
goals_col = db["goals"]
chat_col = db["chats"]

# ---------- HELPERS ----------
def load_goals():
    doc = goals_col.find_one({"user": USER_ID})
    return doc["goals"] if doc else []

def save_goals(goals):
    goals_col.update_one({"user": USER_ID}, {"$set": {"goals": goals}}, upsert=True)


def load_messages():
    doc = chat_col.find_one({"user": USER_ID})
    if doc:
        return doc["messages"]
    return [{"role": "system", "content": "You are a motivational personality development coach. Help the user improve daily, be concise and actionable."}]


def save_messages(messages):
    chat_col.update_one({"user": USER_ID}, {"$set": {"messages": messages}}, upsert=True)

# ---------- STATE ----------
if "goals" not in st.session_state:
    st.session_state.goals = load_goals()

if "messages" not in st.session_state:
    st.session_state.messages = load_messages()

# ---------- UI ----------
st.title("🧠 Personality Development AI")
st.caption("Daily goals + AI coach (MongoDB persistence)")

# ---------- SIDEBAR: GOALS ----------
st.sidebar.header("➕ Add Daily Goals")
new_goal = st.sidebar.text_input("Enter a goal")

col_add, col_clear = st.sidebar.columns(2)
with col_add:
    if st.button("Add Goal") and new_goal.strip():
        st.session_state.goals.append({"task": new_goal.strip(), "done": False})
        save_goals(st.session_state.goals)

with col_clear:
    if st.button("Clear All"):
        st.session_state.goals = []
        save_goals(st.session_state.goals)

st.sidebar.header("📋 Your Goals")
updated_goals = []
for i, g in enumerate(st.session_state.goals):
    done = st.sidebar.checkbox(g["task"], value=g.get("done", False), key=f"goal_{i}")
    updated_goals.append({"task": g["task"], "done": done})

# Persist any checkbox changes
if updated_goals != st.session_state.goals:
    st.session_state.goals = updated_goals
    save_goals(st.session_state.goals)

# ---------- PROGRESS ----------
completed = sum(1 for g in st.session_state.goals if g.get("done"))
total = len(st.session_state.goals)
if total > 0:
    st.sidebar.progress(completed / total)
    st.sidebar.write(f"Progress: {completed}/{total}")

# ---------- MAIN: CHAT ----------
st.header("💬 Chat with your AI Coach")

user_input = st.text_input("You:")

col_send, col_reset = st.columns(2)
with col_send:
    send_clicked = st.button("Send")
with col_reset:
    if st.button("Reset Chat"):
        st.session_state.messages = [{"role": "system", "content": "You are a motivational personality development coach. Help the user improve daily, be concise and actionable."}]
        save_messages(st.session_state.messages)

if send_clicked and user_input.strip():
    st.session_state.messages.append({"role": "user", "content": user_input.strip()})

    resp = client_ai.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=st.session_state.messages,
        temperature=0.7
    )

    reply = resp.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": reply})
    save_messages(st.session_state.messages)

# ---------- DISPLAY CHAT ----------
for m in st.session_state.messages[1:]:
    if m["role"] == "user":
        st.markdown(f"**You:** {m['content']}")
    else:
        st.markdown(f"**AI Coach:** {m['content']}")

# ---------- FOOTER ----------
st.divider()
st.caption("Tips: set MONGO_URI, GROQ_API_KEY, USER_ID as env vars. Data persists in MongoDB.")

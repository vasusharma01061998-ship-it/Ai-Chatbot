from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, RedirectResponse, HTMLResponse
from pydantic import BaseModel
import os, sqlite3, hashlib, secrets
from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
app = FastAPI()

# Database banao
def get_db():
    conn = sqlite3.connect("chatbot.db")
    conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, username TEXT, role TEXT, text TEXT)")
    return conn

sessions = {} # login yaad rakhne ke liye

class Msg(BaseModel):
    message: str

@app.get("/")
def home(request: Request):
    token = request.cookies.get("session")
    if token in sessions:
        return FileResponse("chat.html")
    return FileResponse("login.html")

@app.post("/signup")
def signup(username: str = Form(...), password: str = Form(...)):
    pw = hashlib.sha256(password.encode()).hexdigest()
    try:
        db = get_db()
        db.execute("INSERT INTO users VALUES (NULL, ?, ?)", (username, pw))
        db.commit()
        return RedirectResponse("/login-page", status_code=303)
    except:
        return HTMLResponse("<h3>Ye username pehle se hai! <a href='/'>Wapas jao</a></h3>")

@app.get("/login-page")
def login_page():
    return FileResponse("login.html")

@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    pw = hashlib.sha256(password.encode()).hexdigest()
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, pw)).fetchone()
    if user:
        token = secrets.token_hex(16)
        sessions[token] = username
        res = RedirectResponse("/", status_code=303)
        res.set_cookie("session", token)
        return res
    return HTMLResponse("<h3>Galat username/password! <a href='/'>Wapas jao</a></h3>")

@app.post("/chat")
def chat(data: Msg, request: Request):
    token = request.cookies.get("session")
    username = sessions.get(token, "guest")
    response = client.models.generate_content(model="gemini-2.5-flash", contents=data.message)
    db = get_db()
    db.execute("INSERT INTO chats VALUES (NULL, ?, ?, ?)", (username, "user", data.message))
    db.execute("INSERT INTO chats VALUES (NULL, ?, ?, ?)", (username, "ai", response.text))
    db.commit()
    return {"reply": response.text}

@app.get("/history")
def history(request: Request):
    token = request.cookies.get("session")
    username = sessions.get(token, "guest")
    db = get_db()
    rows = db.execute("SELECT role, text FROM chats WHERE username=?", (username,)).fetchall()
    return {"history": rows}

@app.get("/logout")
def logout(request: Request):
    token = request.cookies.get("session")
    if token in sessions: del sessions[token]
    res = RedirectResponse("/", status_code=303)
    res.delete_cookie("session")
    return res
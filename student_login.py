import streamlit as st
import mysql.connector
from mysql.connector import Error
from time import sleep
import hashlib

# ========================================
# ฟังก์ชันสร้างการเชื่อมต่อฐานข้อมูล
def create_connection():
    config = {
        'user': st.secrets["mysql"]["user"],
        'password': st.secrets["mysql"]["password"],
        'host': st.secrets["mysql"]["host"],
        'port': st.secrets["mysql"]["port"],
        'database': st.secrets["mysql"]["database"]
    }
    try:
        conn = mysql.connector.connect(**config)
        if conn.is_connected():
            return conn
    except Error as e:
        st.error(f"Error connecting to MySQL: {e}")
        return None

def close_connection(conn):
    if conn and conn.is_connected():
        conn.close()

# ========================================
# ฟังก์ชันสำหรับ Hash Password
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ฟังก์ชันสำหรับตรวจสอบการเข้าสู่ระบบ
def try_login(input_username, input_password):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM student_login WHERE student_id = %s", (input_username,))
            result = cursor.fetchone()
            if result:
                stored_hashed_password = result[0]
                if stored_hashed_password == hash_password(input_password):
                    st.success("Logged in!")
                    sleep(1)
                    st.session_state["logged_in"] = True  # กำหนดสถานะการเข้าสู่ระบบ
                    st.experimental_rerun()  # โหลดหน้าใหม่
                else:
                    st.error("Your username or password is incorrect.")
            else:
                st.error("Your username or password is incorrect.")
        except Error as e:
            st.error(f"Error querying the database: {e}")
        finally:
            cursor.close()
            close_connection(conn)
    else:
        st.error("Unable to connect to the database.")

# ========================================
# หน้าแสดงผลหลังเข้าสู่ระบบ (Home Page)
def home_page():
    st.title("Home")
    st.write("Welcome to the Home page!")
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.experimental_rerun()

# หน้าแสดงผลล็อกอิน
def login_page():
    st.title("Student Login")
    input_username = st.text_input("Username", placeholder="Enter your Student ID")
    input_password = st.text_input("Password", type="password", placeholder="Enter your password")

    if st.button("Login"):
        try_login(input_username, input_password)

# โปรแกรมหลัก
def main():
    # ตรวจสอบสถานะการล็อกอิน
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    # เลือกหน้าแสดงผลตามสถานะการล็อกอิน
    if st.session_state["logged_in"]:
        home_page()
    else:
        login_page()

if __name__ == "__main__":
    main()

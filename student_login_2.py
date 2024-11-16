import streamlit as st
import mysql.connector
from mysql.connector import Error

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
# ฟังก์ชันสำหรับตรวจสอบการเข้าสู่ระบบ
def try_login(input_username, input_password):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM student_login WHERE student_id = %s", (input_username,))
            result = cursor.fetchone()
            if result:
                stored_password = result[0]  # รหัสผ่านที่เก็บในฐานข้อมูล (plain text)
                if stored_password.strip() == input_password:
                    st.session_state["logged_in"] = True  # กำหนดสถานะการเข้าสู่ระบบ
                    st.session_state["username"] = input_username  # บันทึก username
                else:
                    st.error("Incorrect password. Please try again.")
            else:
                st.error(f"Username '{input_username}' not found. Please enter a valid Student ID.")
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
    st.write(f"Welcome to the Home page, {st.session_state['username']}!")
    st.write("You have successfully logged in.")
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state.pop("username", None)  # ลบ username ออกจาก session state

# หน้าแสดงผลล็อกอิน
def login_page():
    st.title("Student Login")
    st.write("Please log in using your Student ID and password.")
    input_username = st.text_input("Username (Student ID)", placeholder="Enter your Student ID")
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

import streamlit as st
import mysql.connector
from mysql.connector import Error
from time import sleep
import hashlib

#========================================
#(1) Test Connection

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
#========================================
#2 Login
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def try_login(input_username,input_password):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM student_login WHERE student_id = %s ",(input_username,))
    result = cursor.fetchone()
    if result:
        store_password = hash_password(result[0])
        if store_password == hash_password(input_password):
            st.success("Logged in!")
            sleep(1)
            st.switch_page("pages/home.py")
        else:
            st.error("Your username or password is incorrect")
    else:
        st.error("Your username or password is incorrect")


    cursor.close()
    conn.close()

#========================================

st.title("Student login")
input_username = st.text_input("Username", key="username",placeholder="Student's ID")
input_password = st.text_input("Password", key="password", type="password")
if st.button("Login"):
    try_login(input_username, input_password)

#========================================

st.write("TEST Connection") 
conn = create_connection()
if conn:
    st.write("Connected to MySQL database")
    cursor = conn.cursor()
else:
    st.error("Failed to connect to the database.")
close_connection(conn)

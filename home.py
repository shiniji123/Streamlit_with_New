import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd

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
            # st.write("Connected to MySQL database")
            return conn
    except Error as e:
        st.error(f"Error connecting to MySQL: {e}")
        return None
def close_connection(conn):
    if conn and conn.is_connected():
        conn.close()
        # st.write("Connection closed")

#1 ShowColumn
def showColumn(table_name):
    try:
        conn = create_connection()
        cursor = conn.cursor()
    
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()

        # Print only the column names
        List_column_name = [column[0] for column in columns]
        return List_column_name
        # return st.write(List_column_name)

    except mysql.connector.Error as err:
        print(f"Error: {err}")

    finally:
        close_connection(conn)

#2 Add DATA
def insert_data(table_name,values):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        columns = showColumn(table_name)
        # print(columns)
        columns_str = ','.join(columns)
        placeholders = ','.join(['%s'] * len(values))
        
        # Execute the query with the provided values
        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        cursor.execute(query, values)
        conn.commit()

        print(f"1 record inserted successfully into {table_name}")

    except mysql.connector.Error as error:
        print(f"Failed to insert data into MySQL table {table_name}: {error}")

    finally:
        close_connection(conn)

def insert_data_student(student_id,first_name,last_name,email,contact_number,address,register_date):
    insert_data("student",[student_id,first_name,last_name,email,contact_number,address,register_date])

def insert_data_enrollment(enrollment_id,student_id,course_id,semester,year,grade,enrollment_date):
    insert_data("enrollment",[enrollment_id,student_id,course_id,semester,year,grade,enrollment_date])

def insert_data_instructor(instructor_id,first_name,last_name,department_id,email,contact_number):
    insert_data("instructor",[instructor_id,first_name,last_name,department_id,email,contact_number])

def insert_data_course(course_id,course_name,credits,department_id,instructor_id):
    insert_data("course",[course_id,course_name,credits,department_id,instructor_id])

def insert_data_department(department_id,department_name):
    insert_data("department",[department_id,department_name])

#3 Del DATA
def delete_data(table_name, condition):
    try:
        # Establish connection to the database
        conn = create_connection()
        cursor = conn.cursor()

        # Create the delete query
        query = f"DELETE FROM {table_name} WHERE {condition}"
        
        # Execute the delete query
        cursor.execute(query)

        conn.commit()

        print(f"Record(s) deleted successfully from {table_name} where {condition}")

    except mysql.connector.Error as error:
        print(f"Failed to delete data from MySQL table {table_name}: {error}")

    finally:
        close_connection(conn)

#4 Show DATA
def show_table(table_name,column):
    try:
        conn = create_connection()
        cursor = conn.cursor()

        query = f"SELECT {column} FROM {table_name}" 
        cursor.execute(query)
        
        # Fetch data and convert it into a DataFrame
        columns = showColumn(table_name)  # Get column names
        data = cursor.fetchall()
        
        if data:
            df = pd.DataFrame(data, columns=columns)
            # df['student_id'] = df['student_id'].astype(str)
            # df['year'] = df['year'].astype(str)
            st.dataframe(df)  # Display the DataFrame as an interactive table
        else:
            st.write("No data available.")
    except mysql.connector.Error as error:
        print(f"Failed to delete data from MySQL table {table_name}: {error}")
    finally:
        close_connection(conn)

# =======================================================================

st.title("Home")
conn = create_connection()
cursor = conn.cursor()

show_table("student","*")



close_connection(conn)

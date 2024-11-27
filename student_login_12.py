import streamlit as st
import mysql.connector
from mysql.connector import Error
import requests
import pandas as pd
from datetime import datetime
import time
from streamlit_option_menu import option_menu
from PIL import Image, ImageDraw, ImageOps
from io import BytesIO

# ========================================
# Function to create a database connection
def create_connection():
    config = {
        'user': st.secrets["mysql"]["user"],
        'password': st.secrets["mysql"]["password"],
        'host': st.secrets["mysql"]["host"],
        'port': st.secrets["mysql"]["port"],
        'database': st.secrets["mysql"]["database"],
    }
    try:
        conn = mysql.connector.connect(**config)
        if conn.is_connected():
            return conn
    except Error as e:
        st.error(f"Unable to connect to MySQL database: {e}")
    return None

def close_connection(conn):
    if conn and conn.is_connected():
        conn.close()

# ========================================
# Function to get courses not yet enrolled
def get_unenrolled_courses(student_id):
    conn = create_connection()
    if conn:
        try:
            query = """
                SELECT c.course_id, c.course_name, c.credits
                FROM course c
                WHERE c.course_id NOT IN (
                    SELECT e.course_id
                    FROM enrollment e
                    WHERE e.student_id = %s
                )
            """
            df = pd.read_sql(query, conn, params=(student_id,))
            return df
        except Error as e:
            st.error(f"Error fetching unenrolled courses: {e}")
            return pd.DataFrame()
        finally:
            close_connection(conn)
    else:
        return pd.DataFrame()

# Function to get courses already enrolled
def get_enrolled_courses(student_id):
    conn = create_connection()
    if conn:
        try:
            query = """
                SELECT c.course_id, c.course_name, c.credits
                FROM course c
                INNER JOIN enrollment e ON c.course_id = e.course_id
                WHERE e.student_id = %s
            """
            df = pd.read_sql(query, conn, params=(student_id,))
            return df
        except Error as e:
            st.error(f"Error fetching enrolled courses: {e}")
            return pd.DataFrame()
        finally:
            close_connection(conn)
    else:
        return pd.DataFrame()

# ========================================
# Function to add courses to enrollment
def add_courses_to_enrollment(student_id, course_ids, semester=1, year=datetime.now().year):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            enrollment_date = datetime.now().strftime('%Y-%m-%d')
            for course_id in course_ids:
                query = """
                    INSERT INTO enrollment (student_id, course_id, semester, year, enrollment_date)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (student_id, course_id, semester, year, enrollment_date))
            conn.commit()

        except Error as e:
            st.error(f"Error adding courses: {e}")
        finally:
            close_connection(conn)

# Function to drop courses from enrollment
def drop_courses_from_enrollment(student_id, course_ids):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            for course_id in course_ids:
                query = """
                    DELETE FROM enrollment
                    WHERE student_id = %s AND course_id = %s
                """
                cursor.execute(query, (student_id, course_id))
            conn.commit()

        except Error as e:
            st.error(f"Error dropping courses: {e}")
        finally:
            close_connection(conn)

# Function to withdraw courses (update grade to 'W')
def withdraw_courses(student_id, course_ids):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            for course_id in course_ids:
                query = """
                    UPDATE enrollment
                    SET grade = 'W'
                    WHERE student_id = %s AND course_id = %s
                """
                cursor.execute(query, (student_id, course_id))
            conn.commit()

        except Error as e:
            st.error(f"Error withdrawing courses: {e}")
        finally:
            close_connection(conn)

# ========================================
# Function to display course selection page
def course_selection_page(
    title, instruction, courses_df, action_button_text, confirm_action, back_action
):
    st.title(title)
    st.write(instruction)

    if not courses_df.empty:
        selected_courses = st.multiselect(
            "Please select courses",
            options=courses_df['course_id'],
            format_func=lambda x: f"{x}: {courses_df.loc[courses_df['course_id'] == x, 'course_name'].values[0]}"
        )
        if st.button(action_button_text):
            if selected_courses:
                st.session_state['selected_courses'] = selected_courses
                st.session_state['confirmation_step'] = True
            else:
                st.warning("Please select at least one course.")
        if st.session_state.get('confirmation_step', False):
            st.write("**Confirm your selection**")
            for course_id in st.session_state['selected_courses']:
                course_name = courses_df.loc[courses_df['course_id'] == course_id, 'course_name'].values[0]
                st.write(f"- {course_id}: {course_name}")
            col1, col2 = st.columns(2)
            with col1:
                st.button("Confirm", on_click=confirm_action)
            with col2:
                st.button("Cancel", on_click=handle_cancel)
    else:
        st.info("No courses available.")
    st.button("Back", on_click=back_action)

def handle_cancel():
    st.session_state['confirmation_step'] = False
    st.session_state['rerun_needed'] = True


# ========================================
# Add Course Page
def add_course_page():
    student_id = st.session_state.get("username", None)
    if student_id:
        unenrolled_courses = get_unenrolled_courses(student_id)
        course_selection_page(
            title="Add Course",
            instruction="Select courses you want to add:",
            courses_df=unenrolled_courses,
            action_button_text="Add Course",
            confirm_action=handle_confirm_add_course,
            back_action=go_to_main_menu
        )
    else:
        st.error("Student ID not found.")

def handle_confirm_add_course():
    student_id = st.session_state.get("username", None)
    if student_id:
        add_courses_to_enrollment(student_id, st.session_state['selected_courses'])
        st.session_state['selected_courses'] = []
        st.session_state['confirmation_step'] = False
        st.success("Courses added successfully.")
        st.session_state['current_page'] = "Student Registration System"
        time.sleep(1)
        st.session_state["rerun_needed"] = True  # Add this line to navigate back
    else:
        st.error("Student ID not found.")

# Drop Course Page
def drop_course_page():
    student_id = st.session_state.get("username", None)
    if student_id:
        enrolled_courses = get_enrolled_courses(student_id)
        course_selection_page(
            title="Drop Course",
            instruction="Select courses you want to drop:",
            courses_df=enrolled_courses,
            action_button_text="Drop Course",
            confirm_action=handle_confirm_drop_course,
            back_action=go_to_main_menu
        )
    else:
        st.error("Student ID not found.")

# Similarly update handle_confirm_drop_course and handle_confirm_withdraw_course
def handle_confirm_drop_course():
    student_id = st.session_state.get("username", None)
    if student_id:
        drop_courses_from_enrollment(student_id, st.session_state['selected_courses'])
        st.session_state['selected_courses'] = []
        st.session_state['confirmation_step'] = False
        st.success("Courses dropped successfully.")
        st.session_state['current_page'] = "Student Registration System"
        time.sleep(1)
        st.session_state["rerun_needed"] = True
    else:
        st.error("Student ID not found.")

# Withdraw Course Page
def withdraw_course_page():
    student_id = st.session_state.get("username", None)
    if student_id:
        conn = create_connection()
        if conn:
            try:
                query = """
                    SELECT c.course_id, c.course_name, c.credits
                    FROM course c
                    INNER JOIN enrollment e ON c.course_id = e.course_id
                    WHERE e.student_id = %s AND (e.grade IS NULL OR e.grade NOT IN ('W'))
                """
                enrolled_courses = pd.read_sql(query, conn, params=(student_id,))
            except Error as e:
                st.error(f"Error fetching data: {e}")
                enrolled_courses = pd.DataFrame()
            finally:
                close_connection(conn)
        else:
            enrolled_courses = pd.DataFrame()

        course_selection_page(
            title="Withdraw Course",
            instruction="Select courses you want to withdraw:",
            courses_df=enrolled_courses,
            action_button_text="Withdraw Course",
            confirm_action=handle_confirm_withdraw_course,
            back_action=go_to_main_menu
        )
    else:
        st.error("Student ID not found.")

def handle_confirm_withdraw_course():
    student_id = st.session_state.get("username", None)
    if student_id:
        withdraw_courses(student_id, st.session_state['selected_courses'])
        st.session_state['selected_courses'] = []
        st.session_state['confirmation_step'] = False
        st.success("Courses withdrawn successfully.")
        st.session_state['current_page'] = "Student Registration System"
        time.sleep(1)
        st.session_state["rerun_needed"] = True
    else:
        st.error("Student ID not found.")

# ========================================
# Registration Status Page
def registration_status_page():
    st.title("Registration Status")

    student_id = st.session_state.get("username", None)
    if student_id:
        conn = create_connection()
        if conn:
            try:
                student_query = """
                    SELECT student_id, first_name, last_name
                    FROM student
                    WHERE student_id = %s
                """
                student_data = pd.read_sql(student_query, conn, params=(student_id,))

                if not student_data.empty:
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        profile_image = get_profile_image(student_id)
                        st.image(profile_image, width=150)
                    with col2:
                        st.write(f"**Student ID:** {student_data['student_id'].iloc[0]}")
                        st.write(f"**Name:** {student_data['first_name'].iloc[0]} {student_data['last_name'].iloc[0]}")

                    enrollment_query = """
                        SELECT c.course_id, c.course_name, c.credits, e.grade
                        FROM enrollment e
                        INNER JOIN course c ON e.course_id = c.course_id
                        WHERE e.student_id = %s
                    """
                    enrollment_data = pd.read_sql(enrollment_query, conn, params=(student_id,))

                    if not enrollment_data.empty:
                        st.write("### Enrolled Courses")
                        enrollment_data['course_id'] = enrollment_data['course_id'].astype(str)
                        st.dataframe(enrollment_data)

                        grade_to_gpa = {'A': 4.0, 'B+': 3.5, 'B': 3.0, 'C+': 2.5, 'C': 2.0, 'D+': 1.5, 'D': 1.0, 'F': 0.0}
                        valid_courses = enrollment_data[
                            enrollment_data['grade'].isin(grade_to_gpa.keys())
                        ]
                        valid_courses['gpa'] = valid_courses['grade'].map(grade_to_gpa)
                        valid_courses['weighted_gpa'] = valid_courses['gpa'] * valid_courses['credits']
                        total_credits = valid_courses['credits'].sum()
                        total_weighted_gpa = valid_courses['weighted_gpa'].sum()

                        gpax = total_weighted_gpa / total_credits if total_credits > 0 else 0.0
                        st.metric("GPAX", f"{gpax:.2f}")
                    else:
                        st.info("No courses enrolled yet.")
                else:
                    st.error("Student information not found.")
            except Error as e:
                st.error(f"Error fetching data: {e}")
            finally:
                close_connection(conn)
        else:
            st.error("Unable to connect to the database.")
    else:
        st.error("Student ID not found.")
    if st.button("Back"):
        go_to_main_menu()

# ========================================
# Function to navigate back to the main menu
def go_to_main_menu():
    st.session_state['current_page'] = "Student Registration System"

# ========================================
# Main menu page
# Student Registration System Page
def student_registration_system_page():
    st.title("Student Registration System")
    student_id = st.session_state.get("username", None)
    if student_id:
        profile_image = get_profile_image(student_id)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"Welcome, **{student_id}**!")
            st.write("Select an option below:")
        with col2:
            st.image(profile_image, width=100)

        col1, col2 = st.columns(2)
        col3, col4 = st.columns(2)

        with col1:
            st.button("Add Course", on_click=go_to_add_course)
        with col2:
            st.button("Drop Course", on_click=go_to_drop_course)
        with col3:
            st.button("Withdraw Course", on_click=go_to_withdraw_course)
        with col4:
            st.button("Registration Status", on_click=go_to_registration_status)

        st.button("Logout", on_click=logout)

def go_to_add_course():
    st.session_state["current_page"] = "Add Course"
    #st.session_state["rerun_needed"] = True

def go_to_drop_course():
    st.session_state["current_page"] = "Drop Course"
    #st.session_state["rerun_needed"] = True

def go_to_withdraw_course():
    st.session_state["current_page"] = "Withdraw Course"
    #st.session_state["rerun_needed"] = True

def go_to_registration_status():
    st.session_state["current_page"] = "Registration Status"
    #st.session_state["rerun_needed"] = True

def logout():
    st.session_state["logged_in"] = False
    st.session_state["username"] = None
    st.session_state["current_page"] = "Login"
    st.session_state["rerun_needed"] = False

# ========================================
# Login page
def login_page():
    st.title("Student Login")
    st.write("Please log in using your Student ID and password.")

    input_username = st.text_input("Student ID")
    input_password = st.text_input("Password", type="password")

    if st.button("Login"):
        try_login(input_username, input_password)

# Function to authenticate user
def try_login(input_username, input_password):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            query = """
                SELECT password
                FROM student_login
                WHERE student_id = %s
            """
            cursor.execute(query, (input_username,))
            result = cursor.fetchone()
            if result:
                stored_password = result[0]
                if stored_password == input_password:
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = input_username
                    st.session_state['current_page'] = "Student Registration System"
                    st.success("Login successful.")
                    st.rerun()  # Rerun the app to update the state
                else:
                    st.error("Incorrect password.")
            else:
                st.error("Student ID not found.")
        except Error as e:
            st.error(f"Error during authentication: {e}")
        finally:
            cursor.close()
            close_connection(conn)
    else:
        st.error("Unable to connect to the database.")

# ========================================
# Function to get profile image
def get_profile_image(student_id):
    base_url = "https://raw.githubusercontent.com/shiniji123/Streamlit_with_New/main/image/"
    default_image = f"{base_url}default_profile.jpg"
    profile_image = f"{base_url}profile_{student_id}.jpg"

    try:
        response = requests.head(profile_image)
        if response.status_code == 200:
            return profile_image
        else:
            return default_image
    except:
        return default_image


def show_styled_profile_image(profile_image):
    # ดึงรูปภาพจาก URL
    response = requests.get(profile_image)
    img = Image.open(BytesIO(response.content))

    # ทำให้มุมของรูปภาพโค้ง
    img = make_rounded_corners(img, radius=20)

    # เพิ่มกรอบให้กับรูปภาพ
    img = add_border(img, border_color=(0, 255, 0), border_width=10)

    # แสดงรูปภาพใน Streamlit
    st.image(img, use_column_width=True)


def make_rounded_corners(image, radius=20):
    """ ฟังก์ชันในการทำมุมโค้งของรูปภาพ """
    circle = Image.new('L', (radius * 2, radius * 2), 0)
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radius * 2, radius * 2), fill=255)

    alpha = image.convert('RGBA').split()[3]
    image.putalpha(alpha)

    rounded_image = image.copy()
    rounded_image.paste(circle, (0, 0), mask=circle)

    return rounded_image


def add_border(image, border_color=(255, 0, 0), border_width=10):
    """ ฟังก์ชันในการเพิ่มกรอบให้กับรูปภาพ """
    width, height = image.size
    bordered_image = Image.new("RGB", (width + 2 * border_width, height + 2 * border_width), border_color)
    bordered_image.paste(image, (border_width, border_width))
    return bordered_image

def get_student_name(student_id):
    conn = create_connection()
    if conn:
        try:
            query = """
                SELECT first_name, last_name
                FROM student
                WHERE student_id = %s
            """
            student_data = pd.read_sql(query, conn, params=(student_id,))
            if not student_data.empty:
                return f"{student_data['first_name'].iloc[0]} {student_data['last_name'].iloc[0]}"
            else:
                return None
        except Error as e:
            st.error(f"Error fetching student data: {e}")
            return None
        finally:
            close_connection(conn)
    else:
        return None
# ========================================
# Main program
def main():
    if "logged_in" not in st.session_state:
        st.session_state['logged_in'] = False

    if "current_page" not in st.session_state:
        st.session_state['current_page'] = "Login"

    if st.session_state.get("rerun_needed", False):
        st.session_state["rerun_needed"] = False
        st.rerun()

    if st.session_state['logged_in']:
        student_id = st.session_state.get("username", None)
        student_name = get_student_name(student_id)
        with st.sidebar:
            selected_option = option_menu(
                menu_title=f"{student_name}",
                options=["Student Registration System", "Add Course", "Drop Course", "Withdraw Course", "Registration Status", "Logout"],
                icons=["house", "book", "trash", "x-circle", "info-circle", "box-arrow-left"],
                menu_icon="cast",
                default_index=0,
            )
            if selected_option == "Logout":
                st.session_state["logged_in"] = False
                st.session_state["username"] = None
                st.session_state["current_page"] = "Login"
                st.session_state["rerun_needed"] = False

        # Render the selected page
        if st.session_state["current_page"] == "Student Registration System":
            student_registration_system_page()
        elif st.session_state["current_page"] == "Add Course":
            add_course_page()
        elif st.session_state["current_page"] == "Drop Course":
            drop_course_page()
        elif st.session_state["current_page"] == "Withdraw Course":
            withdraw_course_page()
        elif st.session_state["current_page"] == "Registration Status":  # เพิ่มเงื่อนไขนี้
            registration_status_page()

    else:
        login_page()

if __name__ == "__main__":
    main()



import streamlit as st
import mysql.connector
from mysql.connector import Error
import requests
import pandas as pd
from datetime import datetime
import time
from streamlit_option_menu import option_menu
import bcrypt
import base64
import hashlib

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



#if __name__ == "__main__":
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
                AND c.course_id NOT IN (
                    SELECT course_id FROM old_course
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
                AND c.course_id NOT IN (
                    SELECT course_id FROM old_course
                )
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



# ========================================
# Function to display course selection page
def course_selection_page(
    title, instruction, courses_df, action_button_text, confirm_action, back_action):
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
        enrolled_courses = get_enrolled_courses_for_withdraw(student_id)
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
        st.session_state["rerun_needed"] = True
    else:
        st.error("Student ID not found.")

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
    else:
        st.error("Unable to connect to the database.")

def get_enrolled_courses_for_withdraw(student_id):
    conn = create_connection()
    if conn:
        try:
            query = """
                SELECT c.course_id, c.course_name, c.credits
                FROM course c
                INNER JOIN enrollment e ON c.course_id = e.course_id
                WHERE e.student_id = %s
                AND c.course_id NOT IN (
                    SELECT course_id FROM old_course
                )
                AND (e.grade IS NULL OR e.grade != 'W')
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
# Function to navigate back to the main menu
def go_to_main_menu():
    st.session_state['current_page'] = "Student Registration System"

# ========================================
# Registration Status Page
def registration_status_page():
    st.title("Registration Status")

    student_id = st.session_state.get("username", None)
    if student_id:
        conn = create_connection()
        if conn:
            try:
                # ดึงข้อมูลนักศึกษา
                student_query = '''
                    SELECT student_id, first_name, last_name, faculty_name
                    FROM student
                    WHERE student_id = %s
                '''
                student_data = pd.read_sql(student_query, conn, params=(student_id,))

                if not student_data.empty:
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        profile_image_bytes = get_profile_image(student_id)
                        display_image_with_frame(profile_image_bytes, width=150)
                    with col2:
                        st.write(f"**Student ID:** {student_data['student_id'].iloc[0]}")
                        st.write(f"**Name:** {student_data['first_name'].iloc[0]} {student_data['last_name'].iloc[0]}")
                        st.write(f"**Faculty:** {student_data['faculty_name'].iloc[0]}")

                    # ปรับปรุงคำสั่ง SQL เพื่อดึง semester และ year
                    enrollment_query = '''
                        SELECT c.course_id, c.course_name, c.credits, e.semester, e.year, e.grade
                        FROM enrollment e
                        INNER JOIN course c ON e.course_id = c.course_id
                        WHERE e.student_id = %s
                        ORDER BY e.year DESC, e.semester DESC
                    '''
                    enrollment_data = pd.read_sql(enrollment_query, conn, params=(student_id,))

                    if not enrollment_data.empty:
                        st.write("### Enrolled Courses")
                        enrollment_data['course_id'] = enrollment_data['course_id'].astype(str)
                        st.dataframe(enrollment_data)

                        # การคำนวณ GPAX
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
            profile_image_bytes = get_profile_image(student_id)
            display_image_with_frame(profile_image_bytes, width=150)
            if st.button("My Profile"):
                st.session_state["current_page"] = "My Profile"
                st.rerun()

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


def my_profile_page():
    st.title("My Profile")
    student_id = st.session_state.get("username", None)
    if student_id:
        conn = create_connection()
        if conn:
            try:
                # ดึงข้อมูลจากตาราง student
                student_query = """
                    SELECT s.student_id, s.first_name, s.last_name, s.faculty_name, s.contact_number, s.register_date
                    FROM student s
                    WHERE s.student_id = %s
                """
                student_data = pd.read_sql(student_query, conn, params=(student_id,))

                # ดึงรหัสผ่านจากตาราง student_login
                password_query = """
                    SELECT password
                    FROM student_login
                    WHERE student_id = %s
                """
                cursor = conn.cursor()
                cursor.execute(password_query, (student_id,))
                password_result = cursor.fetchone()
                password = password_result[0] if password_result else "N/A"

                if not student_data.empty:
                    profile_image_bytes = get_profile_image(student_id)
                    display_image_with_frame(profile_image_bytes, width=150)

                    st.write("")

                    st.write(f"**Student ID:** {student_data['student_id'].iloc[0]}")
                    st.write(f"**Name:** {student_data['first_name'].iloc[0]} {student_data['last_name'].iloc[0]}")
                    st.write(f"**Faculty:** {student_data['faculty_name'].iloc[0]}")
                    st.write(f"**Contact Number:** {student_data['contact_number'].iloc[0]}")
                    st.write(f"**Register Date:** {student_data['register_date'].iloc[0]}")
                    st.write(f"**Password:** {password}")

                    if st.button("New Password"):
                        st.session_state['current_page'] = "Change Password"
                        st.rerun()
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
        st.rerun()



def change_password_page():
    st.title("Change Password")
    student_id = st.session_state.get("username", None)
    if student_id:
        old_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_new_password = st.text_input("Confirm New Password", type="password")

        if st.button("Submit"):
            if new_password != confirm_new_password:
                st.error("New passwords do not match.")
            else:
                conn = create_connection()
                if conn:
                    try:
                        cursor = conn.cursor()
                        # Fetch the stored hashed password
                        password_query = """
                            SELECT password
                            FROM student_login
                            WHERE student_id = %s
                        """
                        cursor.execute(password_query, (student_id,))
                        result = cursor.fetchone()
                        if result:
                            stored_password = result[0]
                            # Verify the current password
                            if bcrypt.checkpw(old_password.encode('utf-8'), stored_password.encode('utf-8')):
                                # Check if the new password is different from the current password
                                if bcrypt.checkpw(new_password.encode('utf-8'), stored_password.encode('utf-8')):
                                    st.error("New password cannot be the same as the current password.")
                                else:
                                    # Hash the new password
                                    hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                                    # Update the password in the database
                                    update_query = """
                                        UPDATE student_login
                                        SET password = %s
                                        WHERE student_id = %s
                                    """
                                    cursor.execute(update_query, (hashed_new_password.decode('utf-8'), student_id))
                                    conn.commit()
                                    st.success("Password changed successfully.")
                                    st.session_state['current_page'] = "My Profile"
                                    st.rerun()
                            else:
                                st.error("Incorrect current password.")
                        else:
                            st.error("Student not found.")
                    except Error as e:
                        st.error(f"Error updating password: {e}")
                    finally:
                        close_connection(conn)
                else:
                    st.error("Unable to connect to the database.")
    else:
        st.error("Student ID not found.")
    if st.button("Back"):
        st.session_state['current_page'] = "My Profile"
        st.rerun()



def go_to_add_course():
    st.session_state["current_page"] = "Add Course"
    #st.rerun()
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
                try:
                    # Check if stored password is a valid bcrypt hash
                    if bcrypt.checkpw(input_password.encode('utf-8'), stored_password.encode('utf-8')):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = input_username
                        st.session_state['current_page'] = "Student Registration System"
                        st.success("Login successful.")
                        st.rerun()
                    else:
                        st.error("Incorrect password.")
                except ValueError as ve:
                    st.error("An error occurred during password verification. Please contact support.")
                    print(f"ValueError: {ve}")
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
    default_image_url = f"{base_url}default_profile.jpg"
    profile_image_url = f"{base_url}profile_{student_id}.jpg"

    # ตรวจสอบว่า URL ของรูปภาพมีอยู่หรือไม่
    try:
        response = requests.head(profile_image_url)
        if response.status_code == 200:
            image_url = profile_image_url
        else:
            image_url = default_image_url
    except:
        image_url = default_image_url

    # ดาวน์โหลดรูปภาพและคืนค่าเป็นไบต์
    try:
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            image_bytes = image_response.content
            return image_bytes
        else:
            return None
    except:
        return None

def display_image_with_frame(image_bytes, width=125):
    if image_bytes:
        encoded_image = base64.b64encode(image_bytes).decode()

        image_html = f'''
        <div style="text-align: center;">
            <img src="data:image/jpeg;base64,{encoded_image}" style="
                width: {width}px;
                border: 5px solid #1a458a;
                /* border-radius: 50%; */  /* เอาบรรทัดนี้ออกหรือคอมเมนต์ไว้ */
                box-shadow: 5px 5px 15px rgba(0,0,0,0.5);
            ">
        </div>
        '''
        st.markdown(image_html, unsafe_allow_html=True)
    else:
        st.error("Unable to load image.")


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
        st.session_state['current_page'] = "Student Registration System"

    if st.session_state.get("rerun_needed", False):
        st.session_state["rerun_needed"] = False
        st.rerun()

    if st.session_state['logged_in']:
        student_id = st.session_state.get("username", None)
        student_name = get_student_name(student_id)
        # Define menu options and icons
        menu_options = ["Student Registration System", "Add Course", "Drop Course", "Withdraw Course", "Registration Status", "My Profile", "Logout"]
        menu_icons = ["house", "book", "trash", "x-circle", "info-circle", "person", "box-arrow-left"]

        current_page = st.session_state.get('current_page', 'Student Registration System')

        # Determine default index for the sidebar menu
        if current_page in menu_options:
            default_index = menu_options.index(current_page)
        else:
            default_index = 0  # Default to the first option if current_page not in menu

        # Include the sidebar menu
        with st.sidebar:
            selected_option = option_menu(
                menu_title=f"{student_name}",
                options=menu_options,
                icons=menu_icons,
                menu_icon="person-circle",
                default_index=default_index,
            )

            if selected_option == "Logout":
                st.session_state.clear()
                st.session_state['current_page'] = "Login"
                st.rerun()
            else:
                # Update current_page only if current_page is in menu_options
                if st.session_state['current_page'] in menu_options and selected_option != st.session_state['current_page']:
                    st.session_state['current_page'] = selected_option
                    st.rerun()
                # If current_page is not in menu_options (e.g., "Change Password"), do not update it

        # Render the selected page
        if st.session_state["current_page"] == "Student Registration System":
            student_registration_system_page()
        elif st.session_state["current_page"] == "Add Course":
            add_course_page()
        elif st.session_state["current_page"] == "Drop Course":
            drop_course_page()
        elif st.session_state["current_page"] == "Withdraw Course":
            withdraw_course_page()
        elif st.session_state["current_page"] == "Registration Status":
            registration_status_page()
        elif st.session_state["current_page"] == "My Profile":
            my_profile_page()
        elif st.session_state["current_page"] == "Change Password":
            change_password_page()
    else:
        login_page()



if __name__ == "__main__":
    main()




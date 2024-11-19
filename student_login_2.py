import streamlit as st
import mysql.connector
from mysql.connector import Error
import requests
import pandas as pd

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
def get_unenrolled_courses(student_id):
    conn = create_connection()
    if conn:
        try:
            # SQL Query ดึงข้อมูลวิชาที่ยังไม่ได้ลงทะเบียน
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
            return pd.DataFrame()  # คืน DataFrame ว่างหากมีข้อผิดพลาด
        finally:
            close_connection(conn)
    else:
        return pd.DataFrame()


# ฟังก์ชันสำหรับดึงข้อมูลรายวิชาที่นักศึกษาลงทะเบียนแล้ว
def get_enrolled_courses(student_id):
    conn = create_connection()
    if conn:
        try:
            # SQL Query ดึงข้อมูลวิชาที่ลงทะเบียนแล้ว
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
            return pd.DataFrame()  # คืน DataFrame ว่างหากมีข้อผิดพลาด
        finally:
            close_connection(conn)
    else:
        return pd.DataFrame()

# ========================================
# ฟังก์ชันสำหรับเพิ่มข้อมูลลงทะเบียน
from datetime import datetime  # เพิ่มการ import datetime

def add_courses_to_enrollment(student_id, course_ids, semester=1, year=2024):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            enrollment_date = datetime.now().strftime('%Y-%m-%d')  # วันที่ปัจจุบัน
            for course_id in course_ids:
                query = "INSERT INTO enrollment (student_id, course_id, semester, year, enrollment_date) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (student_id, course_id, semester, year, enrollment_date))
            conn.commit()
            st.success("Courses successfully added to your enrollment.")
        except Error as e:
            st.error(f"Error adding courses: {e}")
        finally:
            close_connection(conn)





# ========================================
# หน้าแสดงผลสำหรับ Add Course
def add_course_page():
    st.title("Add Course")
    st.write("Below is the list of courses you have not yet enrolled in:")

    # ดึง student_id จาก session
    student_id = st.session_state.get("username", None)
    if student_id:
        unenrolled_courses = get_unenrolled_courses(student_id)

        if not unenrolled_courses.empty:
            # สร้างช่องเลือกสำหรับรายวิชา
            course_selection = {}
            for index, row in unenrolled_courses.iterrows():
                course_selection[row['course_id']] = {
                    "checkbox": st.checkbox(
                        f"{row['course_name']} ({row['credits']} credits)", key=f"course_{row['course_id']}"
                    ),
                    "course_name": row['course_name']  # เก็บ course_name ไว้สำหรับแสดงผล
                }

            # เช็คสถานะว่ากำลังอยู่ในขั้นตอนการยืนยัน
            if "confirmation_step" not in st.session_state:
                st.session_state["confirmation_step"] = False

            # หากยังไม่ได้อยู่ในขั้นตอนยืนยัน
            if not st.session_state["confirmation_step"]:
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                with col4:
                    if st.button("Submit"):
                        # ตรวจสอบรายวิชาที่เลือก
                        selected_courses = [
                            {"course_id": course_id, "course_name": data["course_name"]}
                            for course_id, data in course_selection.items() if data["checkbox"]
                        ]
                        if selected_courses:
                            # ตั้งสถานะให้เข้าสู่ขั้นตอนยืนยัน
                            st.session_state["confirmation_step"] = True
                            st.session_state["selected_courses"] = selected_courses
                        else:
                            st.warning("Please select at least one course to add.")
            else:
                # แสดงข้อความยืนยัน
                st.warning("Are you sure you want to add these courses?")
                st.write("Selected courses:")
                for course in st.session_state["selected_courses"]:
                    st.write(f"- {course['course_id']}: {course['course_name']}")

                # ปุ่มยืนยันและยกเลิก
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirm"):
                        add_courses_to_enrollment(
                            student_id, [course["course_id"] for course in st.session_state["selected_courses"]]
                        )
                        # รีเซ็ตสถานะการยืนยัน
                        st.session_state["confirmation_step"] = False
                        st.session_state.pop("selected_courses", None)

                with col2:
                    if st.button("Cancel"):
                        # ยกเลิกการยืนยันและรีเซ็ตสถานะ
                        st.session_state["confirmation_step"] = False
                        st.session_state.pop("selected_courses", None)
        else:
            st.info("You have already enrolled in all available courses.")
    else:
        st.error("Student ID not found. Please log in again.")

    # ปุ่มกลับไปหน้า Student Registration System
    if st.button("Back"):
        st.session_state["current_page"] = "Student Registration System"




# ========================================
def drop_courses_from_enrollment(student_id, course_ids):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            for course_id in course_ids:
                query = "DELETE FROM enrollment WHERE student_id = %s AND course_id = %s"
                cursor.execute(query, (student_id, course_id))
            conn.commit()
            st.success("Courses successfully dropped.")
        except Error as e:
            st.error(f"Error dropping courses: {e}")
        finally:
            close_connection(conn)


# หน้าแสดงผลสำหรับ Drop Course
def drop_course_page():
    st.title("Drop Course")
    st.write("Below is the list of courses you have enrolled in:")

    # ดึง student_id จาก session
    student_id = st.session_state.get("username", None)
    if student_id:
        enrolled_courses = get_enrolled_courses(student_id)

        if not enrolled_courses.empty:
            # สร้างช่องเลือกสำหรับรายวิชา
            course_selection = {}
            for index, row in enrolled_courses.iterrows():
                course_selection[row['course_id']] = {
                    "checkbox": st.checkbox(
                        f"{row['course_name']} ({row['credits']} credits)", key=f"course_{row['course_id']}"
                    ),
                    "course_name": row['course_name']
                }

            # เช็คสถานะว่ากำลังอยู่ในขั้นตอนการยืนยัน
            if "confirmation_step" not in st.session_state:
                st.session_state["confirmation_step"] = False

            # หากยังไม่ได้อยู่ในขั้นตอนยืนยัน
            if not st.session_state["confirmation_step"]:
                col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                with col4:
                    if st.button("Submit"):
                        # ตรวจสอบรายวิชาที่เลือก
                        selected_courses = [
                            {"course_id": course_id, "course_name": data["course_name"]}
                            for course_id, data in course_selection.items() if data["checkbox"]
                        ]
                        if selected_courses:
                            # ตั้งสถานะให้เข้าสู่ขั้นตอนยืนยัน
                            st.session_state["confirmation_step"] = True
                            st.session_state["selected_courses"] = selected_courses
                        else:
                            st.warning("Please select at least one course to drop.")
            else:
                # แสดงข้อความยืนยัน
                st.warning("Are you sure you want to drop these courses?")
                st.write("Selected courses:")
                for course in st.session_state["selected_courses"]:
                    st.write(f"- {course['course_id']}: {course['course_name']}")

                # ปุ่มยืนยันและยกเลิก
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirm"):
                        drop_courses_from_enrollment(
                            student_id,
                            [course["course_id"] for course in st.session_state["selected_courses"]]
                        )
                        # รีเซ็ตสถานะการยืนยัน
                        st.session_state["confirmation_step"] = False
                        st.session_state.pop("selected_courses", None)

                with col2:
                    if st.button("Cancel"):
                        # ยกเลิกการยืนยันและรีเซ็ตสถานะ
                        st.session_state["confirmation_step"] = False
                        st.session_state.pop("selected_courses", None)
        else:
            st.info("You have not enrolled in any courses.")
    else:
        st.error("Student ID not found. Please log in again.")

    # ปุ่มกลับไปหน้า Student Registration System
    if st.button("Back"):
        st.session_state["current_page"] = "Student Registration System"


# ========================================
# หน้าแสดงผลสำหรับ Withdraw Course
def withdraw_course_page():
    st.title("Withdraw Course")
    st.write("Below is the list of courses you have enrolled in:")

    # ดึง student_id จาก session
    student_id = st.session_state.get("username", None)
    if student_id:
        # ดึงข้อมูลรายวิชาที่ลงทะเบียนแล้ว (ไม่รวมวิชาที่เกรดเป็น W)
        conn = create_connection()
        if conn:
            query = """
                SELECT c.course_id, c.course_name, c.credits
                FROM course c
                INNER JOIN enrollment e ON c.course_id = e.course_id
                WHERE e.student_id = %s AND (e.grade IS NULL OR e.grade NOT IN ('W'))
            """
            enrolled_courses = pd.read_sql(query, conn, params=(student_id,))
            close_connection(conn)

            if not enrolled_courses.empty:
                # สร้างช่องเลือกสำหรับรายวิชา
                course_selection = {}
                for index, row in enrolled_courses.iterrows():
                    course_selection[row['course_id']] = {
                        "checkbox": st.checkbox(
                            f"{row['course_name']} ({row['credits']} credits)", key=f"withdraw_{row['course_id']}"
                        ),
                        "course_name": row['course_name']
                    }

                # เช็คสถานะว่ากำลังอยู่ในขั้นตอนการยืนยัน
                if "confirmation_step" not in st.session_state:
                    st.session_state["confirmation_step"] = False

                # หากยังไม่ได้อยู่ในขั้นตอนยืนยัน
                if not st.session_state["confirmation_step"]:
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                    with col4:
                        if st.button("Submit"):
                            # ตรวจสอบรายวิชาที่เลือก
                            selected_courses = [
                                {"course_id": course_id, "course_name": data["course_name"]}
                                for course_id, data in course_selection.items() if data["checkbox"]
                            ]
                            if selected_courses:
                                # ตั้งสถานะให้เข้าสู่ขั้นตอนยืนยัน
                                st.session_state["confirmation_step"] = True
                                st.session_state["selected_courses"] = selected_courses
                            else:
                                st.warning("Please select at least one course to withdraw.")
                else:
                    # แสดงข้อความยืนยัน
                    st.warning("Are you sure you want to withdraw these courses?")
                    st.write("Selected courses:")
                    for course in st.session_state["selected_courses"]:
                        st.write(f"- {course['course_id']}: {course['course_name']}")

                    # ปุ่มยืนยันและยกเลิก
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Confirm"):
                            withdraw_courses(
                                student_id,
                                [course["course_id"] for course in st.session_state["selected_courses"]]
                            )
                            # รีเซ็ตสถานะการยืนยันและอัปเดตตาราง
                            st.session_state["confirmation_step"] = False
                            st.session_state.pop("selected_courses", None)
                            st.experimental_rerun()

                    with col2:
                        if st.button("Cancel"):
                            # ยกเลิกการยืนยันและรีเซ็ตสถานะ
                            st.session_state["confirmation_step"] = False
                            st.session_state.pop("selected_courses", None)
            else:
                st.info("You have no enrolled courses available for withdrawal.")
        else:
            st.error("Unable to connect to the database.")
    else:
        st.error("Student ID not found. Please log in again.")

    # ปุ่มกลับไปหน้า Student Registration System
    if st.button("Back"):
        st.session_state["current_page"] = "Student Registration System"


def withdraw_courses(student_id, course_ids):
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            for course_id in course_ids:
                # อัปเดตเกรดในตาราง enrollment เป็น "W"
                query = """
                    UPDATE enrollment
                    SET grade = 'W'
                    WHERE student_id = %s AND course_id = %s
                """
                cursor.execute(query, (student_id, course_id))
            conn.commit()
            st.success("Courses successfully withdrawn.")
        except Error as e:
            st.error(f"Error withdrawing courses: {e}")
        finally:
            close_connection(conn)


# ========================================
# หน้าแสดงผล Student Registration System
def student_registration_system_page():
    st.title("Student Registration System")

    # ดึง student_id จาก session
    student_id = st.session_state.get("username", None)
    if student_id:
        # ดึง URL รูปภาพโปรไฟล์
        profile_image = get_profile_image(student_id)

        # Layout: ส่วนหัวของหน้า (ข้อความและรูปภาพ)
        col1, col2 = st.columns([3, 1])  # สร้าง 2 คอลัมน์ (ข้อความ 3 ส่วน, รูปภาพ 1 ส่วน)
        with col1:
            st.write(f"Welcome, **{student_id}**!")
            st.write("Select an option below:")
        with col2:
            st.image(profile_image, width=100)  # แสดงรูปภาพด้านขวา

    # Layout สำหรับปุ่มต่างๆ
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        if st.button("Add Course"):
            st.session_state["current_page"] = "Add Course"

    with col2:
        if st.button("Drop Course"):
            st.session_state["current_page"] = "Drop Course"

    with col3:
        if st.button("Withdraw Course"):
            st.session_state["current_page"] = "Withdraw Course"

    with col4:
        if st.button("Registration Status"):
            st.session_state["current_page"] = "Registration Status"

    # Logout Button
    if st.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state.pop("username", None)  # ลบ username ออกจาก session state
  # ลบ username ออกจาก session state

# ========================================
# หน้าแสดงผลล็อกอิน
def login_page():
    st.title("Student Login")
    st.write("Please log in using your Student ID and password.")
    input_username = st.text_input("Username (Student ID)", placeholder="Enter your Student ID")
    input_password = st.text_input("Password", type="password", placeholder="Enter your password")


    if st.button("Login"):
        try_login(input_username, input_password)


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

def registration_status_page():
    st.title("Registration Status")

    student_id = st.session_state.get("username", None)
    if student_id:
        conn = create_connection()
        if conn:
            try:
                # ดึงข้อมูลนักศึกษาจากตาราง student
                student_query = """
                    SELECT student_id, first_name, last_name
                    FROM student
                    WHERE student_id = %s
                """
                student_data = pd.read_sql(student_query, conn, params=(student_id,))

                if not student_data.empty:
                    # แสดงข้อมูลนักศึกษาและรูปภาพ
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        profile_image = get_profile_image(student_id)
                        st.image(profile_image, width=150)
                    with col2:
                        st.write(f"**Student ID:** {student_data['student_id'].iloc[0]}")
                        st.write(f"**Name:** {student_data['first_name'].iloc[0]} {student_data['last_name'].iloc[0]}")

                    # ดึงข้อมูลรายวิชา
                    enrollment_query = """
                        SELECT c.course_id, c.course_name, c.credits, e.grade
                        FROM enrollment e
                        INNER JOIN course c ON e.course_id = c.course_id
                        WHERE e.student_id = %s
                    """
                    enrollment_data = pd.read_sql(enrollment_query, conn, params=(student_id,))

                    if not enrollment_data.empty:
                        st.write("### Courses Enrolled")
                        st.dataframe(enrollment_data)

                        # คำนวณ GPAX
                        grade_to_gpa = {'A': 4.0, 'B': 3.0, 'C': 2.0, 'D': 1.0, 'F': 0.0}
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
                st.error(f"Error retrieving data: {e}")
            finally:
                close_connection(conn)
    else:
        st.error("Student ID not found. Please log in again.")

    # ปุ่มกลับไปหน้า Student Registration System
    if st.button("Back"):
        st.session_state["current_page"] = "Student Registration System"

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
                stored_password = result[0]
                if stored_password.strip() == input_password:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = input_username
                    st.session_state["current_page"] = "Student Registration System"
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
# โปรแกรมหลัก
def main():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "Login"

    if st.session_state["logged_in"]:
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

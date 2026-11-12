import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Radiology QC System", layout="wide")
st.title("ระบบบันทึกและวิเคราะห์คุณภาพเครื่องเอกซเรย์ (QC)")
st.caption("อ้างอิงเกณฑ์มาตรฐานกรมวิทยาศาสตร์การแพทย์")

# สร้างตัวแปรเก็บข้อมูลชั่วคราวใน Session (และรองรับการอัปโหลดไฟล์ CSV)
if "qc_data" not in st.session_state:
    st.session_state.qc_data = pd.DataFrame(columns=[
        "วันที่", "ห้องตรวจ", "kVp_ตั้งค่า", "kVp_วัดได้", "kVp_Error(%)", "สถานะ_kVp", "Output_mGy_mAs"
    ])

# --- ส่วนที่ 1: แถบด้านข้างสำหรับอัปโหลด/ดาวน์โหลดข้อมูล ---
st.sidebar.header("จัดการฐานข้อมูล (CSV)")
uploaded_file = st.sidebar.file_uploader("อัปโหลดไฟล์ประวัติ QC เดิม (.csv)", type=["csv"])
if uploaded_file is not None:
    st.session_state.qc_data = pd.read_csv(uploaded_file)
    st.sidebar.success("โหลดข้อมูลสำเร็จ!")

# --- ส่วนที่ 2: ฟอร์มบันทึกผล QC ---
st.subheader("1. บันทึกผลการทดสอบประจำรอบ")
col1, col2, col3, col4 = st.columns(4)

with col1:
    test_date = st.date_input("วันที่ทดสอบ", date.today())
    room = st.selectbox("เลือกห้องตรวจ", ["Room 1 (General DR)", "Room 2 (General CR)", "Room 3 (Fluoroscopy)"])
with col2:
    set_kvp = st.number_input("ค่า kVp ที่ตั้ง (kVp)", min_value=40.0, max_value=150.0, value=80.0, step=1.0)
with col3:
    meas_kvp = st.number_input("ค่า kVp ที่วัดได้จริง (kVp)", min_value=30.0, max_value=160.0, value=81.5, step=0.1)
with col4:
    output_val = st.number_input("ค่า Radiation Output (mGy/mAs)", min_value=0.0, max_value=10.0, value=0.055, step=0.001, format="%.3f")

# คำนวณ % Error ตามสูตรฟิสิกส์รังสี: |(Measured - Set) / Set| * 100
kvp_error = abs((meas_kvp - set_kvp) / set_kvp) * 100
# เกณฑ์มาตรฐานกรมวิทย์ฯ สำหรับ kVp Accuracy คือไม่เกิน ±5% (หรือ ±10% ขึ้นกับรุ่นเครื่อง)
status_kvp = "ผ่าน (Pass)" if kvp_error <= 5.0 else "ไม่ผ่าน (Fail)"

st.info(f"**ผลการคำนวณเบื้องต้น:** ค่าความคลาดเคลื่อน kVp = **{kvp_error:.2f}%** | สถานะ: **{status_kvp}**")

if st.button("บันทึกข้อมูลลงตาราง", type="primary"):
    new_row = pd.DataFrame([{
        "วันที่": str(test_date),
        "ห้องตรวจ": room,
        "kVp_ตั้งค่า": set_kvp,
        "kVp_วัดได้": meas_kvp,
        "kVp_Error(%)": round(kvp_error, 2),
        "สถานะ_kVp": status_kvp,
        "Output_mGy_mAs": output_val
    }])
    st.session_state.qc_data = pd.concat([st.session_state.qc_data, new_row], ignore_index=True)
    st.success("บันทึกข้อมูลเรียบร้อยแล้ว!")

st.divider()

# --- ส่วนที่ 3: ตารางข้อมูลและการวิเคราะห์ทางสถิติ ---
st.subheader("2. ประวัติการบันทึกและการวิเคราะห์แนวโน้มทางสถิติ")

df = st.session_state.qc_data

if not df.empty:
    # แสดงตารางข้อมูล
    st.dataframe(df, use_container_width=True)
    
    # ปุ่มดาวน์โหลดเป็นไฟล์ CSV เก็บลง iPad / คอมพิวเตอร์แผนก
    csv_data = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="ดาวน์โหลดข้อมูลทั้งหมดเป็นไฟล์ Excel/CSV",
        data=csv_data,
        file_name=f"QC_Report_{date.today()}.csv",
        mime="text/csv"
    )

    # คำนวณค่าสถิติพื้นฐาน
    st.markdown("#### สรุปค่าสถิติ (Statistical Summary)")
    stat_col1, stat_col2, stat_col3 = st.columns(3)
    mean_err = df["kVp_Error(%)"].mean()
    sd_err = df["kVp_Error(%)"].std() if len(df) > 1 else 0.0
    mean_out = df["Output_mGy_mAs"].mean()
    
    stat_col1.metric("ค่าเฉลี่ย % kVp Error", f"{mean_err:.2f}%")
    stat_col2.metric("ส่วนเบี่ยงเบนมาตรฐาน (SD)", f"{sd_err:.2f}")
    stat_col3.metric("ค่าเฉลี่ย Output (mGy/mAs)", f"{mean_out:.4f}")

    # กราฟวิเคราะห์แนวโน้ม (Control Chart)
    fig = px.line(
        df, x="วันที่", y="kVp_Error(%)", color="ห้องตรวจ", markers=True,
        title="กราฟติดตามแนวโน้มความคลาดเคลื่อนของค่า kVp (% Error)"
    )
    # เพิ่มเส้นเกณฑ์มาตรฐาน 5%
    fig.add_hline(y=5.0, line_dash="dash", line_color="red", annotation_text="เกณฑ์มาตรฐานกรมวิทย์ฯ (5%)")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("ยังไม่มีข้อมูลในระบบ กรุณากดบันทึกข้อมูลด้านบน หรืออัปโหลดไฟล์ CSV จากแถบด้านซ้าย")

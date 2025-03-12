import gradio as gr
import requests
import base64

# ====================== CUSTOM CSS ======================
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@300..700&display=swap');

.gradio-container, .gradio-container * {
    font-family: 'Fredoka', sans-serif !important;
}

.gradio-container {
    background-color: #fff8da !important;
}

select {
    background-color: #F4A7A3 !important;
    color: white !important;
    font-size: 16px !important;
    padding: 10px !important;
    border-radius: 8px !important;
    border: none !important;
    width: 200px !important;
    text-align: center !important;
}

#submit-btn {
    background-color: black !important;
    color: white !important;
    border-radius: 8px !important;
    width: 100% !important;
}


.gradio-tabs {
    background-color: #ffdddd !important;
}

.gradio-tab {
    background-color: #ffdddd !important;
    color: white !important;
    padding: 10px 20px !important;
}

.gradio-tab:hover {
    background-color: #d2d5d8 !important;
    color: white !important;
}

#result-box {
    border: 2px solid #F4A7A3 !important;
    border-radius: 10px !important;
    min-height: 400px;
}

.chat_message {
    padding: 15px !important;
    margin: 10px !important;
    border-radius: 15px !important;
    max-width: 80%;
}

.user {
    background: #FFE5E5 !important;
    border-color: #F4A7A3 !important;
    margin-left: auto !important;
}

.bot {
    background: #FFFFFF !important;
    border-color: #5E4744 !important;
    margin-right: auto !important;
}

.info-panel {
    background: #fff3f3 !important;
    padding: 20px !important;
    border-radius: 15px !important;
}
.chat-input {
        flex: 1;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #ccc;
        font-size: 16px;
        background: #fff;
    }

    .chat-send {
        background-color: black;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        border: none;
        cursor: pointer;
        font-weight: bold;
        transition: background-color 0.3s ease;
    }

    .chat-send:hover {
        background-color: #8d6e63;
    }

    .upload-box {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border: 2px dashed #ccc;
        padding: 20px;
        border-radius: 12px;
        background: #fafafa;
    }
"""

js_func = """
function refresh() {
    const url = new URL(window.location);

    if (url.searchParams.get('__theme') !== 'light') {
        url.searchParams.set('__theme', 'light');
        window.location.href = url.href;
    }
}
"""

# ====================== FUNCTION ZONE ======================
def submit_form(name, breed, symptom_photo):
    # ตรวจสอบข้อมูลที่จำเป็นก่อนส่ง (เช่น ชื่อสัตว์เลี้ยงและภาพอาการ)
    
    try:
        with open(symptom_photo, 'rb') as f:
            response = requests.post(
                "http://34.143.163.207:8100/predict/",
                files={'file': f}
            )
        
        if response.status_code == 200:
            result_data = response.json()
            predicted_class = result_data.get('predicted_class', 'ไม่ทราบสาเหตุ')
            scores = result_data.get('scores', {})
            
            diagnosis_result = f"ผลการวินิจฉัย: {predicted_class}"
            scores_text = "ความมั่นใจในการวินิจฉัย:\n" + "\n".join(
                [f"{disease}: {score*100:.2f}%" for disease, score in scores.items()]
            )
            
            return diagnosis_result, symptom_photo, scores_text, predicted_class
        else:
            return f"[เตือน] กรุณาอัพโหลดรูปภาพ", None, None, None
        
    except Exception as e:
        return f"[เตือน] กรุณาอัพโหลดรูปภาพ", None, None, None



def init_chat(name, breed, diagnosis, symptom_img):
    # ตรวจสอบว่าผู้ใช้ใส่ข้อมูลครบหรือไม่
    if not symptom_img and not diagnosis:
        return [("", "กรุณาอัปโหลดภาพและใส่ผลวินิจฉัยก่อนเริ่มแชท")], None
    elif not symptom_img:
        return [("", "กรุณาอัปโหลดภาพก่อนเริ่มแชท")], None
    elif not diagnosis:
        return [("", "กรุณาระบุผลวินิจฉัยก่อนเริ่มแชท")], None

    # ส่งคำสั่ง reset ก่อน
    try:
        requests.post("http://34.143.163.207:8100/chat/", data={"reset": 1})
    except Exception as e:
        return [(f"เกิดข้อผิดพลาดในการรีเซ็ตแชท: {str(e)}", ""), symptom_img]

    # สร้างข้อความเริ่มต้น
    initial_prompt = (
        f"สัตว์เลี้ยงชื่อ: {name}\n"
        f"พันธุ์: {breed}\n"
        f"ผลการวินิจฉัย: {diagnosis}\n"
        "กรุณาให้คำแนะนำการดูแล"
    )

    # ตรวจสอบว่าอัปโหลดรูปหรือไม่
    try:
        with open(symptom_img.name, "rb") as f:
            response = requests.post(
                "http://34.143.163.207:8100/chat/",
                files={"file": f},
                data={"text": initial_prompt}
            ).json()
    except Exception as e:
        response = {"response": f"เกิดข้อผิดพลาด: {str(e)}"}

    # ดึง response จาก API หรือแจ้งข้อผิดพลาด
    chat_response = response.get("response", "ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้")

    return [(initial_prompt, chat_response)], symptom_img

result = None


def chat_response(message, history, file, diagnosis):
    # ตรวจสอบว่าไม่มีข้อความและไม่มีไฟล์ => แจ้งเตือน
    if not diagnosis:
        return [("", "กรุณาวินิจฉัยอาการก่อนเริ่มแชท")], "", None
    if not message.strip() and file is None:
        history.append(("", "[เตือน] กรุณาใส่ข้อความ หรือแนบรูปภาพพร้อมข้อความ"))
        return history, "", None
    if result is None:
        history.append(("", "[เตือน] กรุณาใส่ข้อมูลและวินิจฉัยอาการน้องหมาของคุณ"))
        return history, "", None


    response = ""

    # กรณีมีไฟล์แนบ ให้แนบรูปภาพไปด้วย
    if file is not None:
        try:
            with open(file.name, 'rb') as f:
                res = requests.post(
                    "http://34.143.163.207:8100/chat/",
                    files={'file': f},
                    data={'text': message, 'reset': 0}  # ✅ ใช้ `data` แทน `json`
                )
                response = res.json().get("response", "ไม่สามารถประมวลผลได้")
            with open(file.name, 'rb') as f:
                img_bytes = f.read()
            img_b64 = base64.b64encode(img_bytes).decode('utf-8')
            message += f"\n\n![รูปที่ส่ง](data:image/png;base64,{img_b64})"
        except Exception as e:
            response = f"เกิดข้อผิดพลาด: {str(e)}"

    # กรณีมีข้อความแต่ไม่มีไฟล์
    else:
        try:
            res = requests.post(
                "http://34.143.163.207:8100/chat/",
                data={'text': message, 'reset': 0}  # ✅ ใช้ `data` แทน `json`
            )
            response = res.json().get("response", "ไม่สามารถประมวลผลได้")
        except Exception as e:
            response = f"เกิดข้อผิดพลาด: {str(e)}"

    history.append((message, response))
    return history, "", None

def show_disease():
    return [
        "https://bowwowinsurance.com.au/wp-content/uploads/2018/12/dog-with-dermatitis-in-ear-thumb-700x700.jpg",
        "https://todaysveterinarypractice.com/wp-content/uploads/sites/4/2016/12/T1701C07Fig04.jpg",
        "https://www.kingsdale.com/wp-content/uploads/2022/03/dog-allergic-reaction-1.jpg",
        "https://envisioneyevet.com/wp-content/uploads/2023/11/shutterstock_1099340411.jpg",
        "https://d12fifzdy7ujh4.cloudfront.net/files/blog/110/large/ringworm.jpg",
    ]

# ====================== GRADIO APP ======================
with gr.Blocks(css=custom_css, title="PawClinic", js=js_func) as demo:
    diagnosis_state = gr.State()
    # ---------- LOGO & HEADER ----------
    gr.HTML("""
    <div style="display: flex; align-items: center; justify-content: center; padding: 20px;">
        <img src="https://media.discordapp.net/attachments/1131626340706173001/1348854942542331985/logo.png?ex=67d0fa8e&is=67cfa90e&hm=90d9ecd8efff5554ac5fa5b400de89a9f9410136fa7f5b3d582d1efd0cae3ce1&=&format=webp&quality=lossless&width=1140&height=988" 
             alt="Logo" style="width: 80px; margin-right: 10px;">
        <h1 style="font-family: sans-serif; color: #5E4744; font-size: 60px; margin: 0;">
            <span style="color: #F4A7A3;">P</span><span style="color: #5E4744;">aw</span>
            <span style="color: #F4A7A3;">C</span><span style="color: #5E4744;">linic</span>
        </h1>
    </div>
    """)

    # ---------- TABS ----------
    with gr.Tabs() as tabs:

        # ========== TAB 1: YOUR PET DETAIL ==========
        with gr.Tab("Your Pet Detail"):
            with gr.Row():
                with gr.Column(scale=1):
                    name = gr.Textbox(label="Pet's name", interactive=True)
                    breed = gr.Dropdown(
                        ["Australian Shepherd", "Golden Retriever", "Pug", "Cocker Spaniel", 
                         "Labrador Retriever", "German Shepherd", "Bulldog", "Beagle", "Chihuahua"],
                        label="Breed",
                        interactive=True
                    )
                    # pet_photo = gr.File(label="Upload photo of your pet (optional)", interactive=True)
                    symptom_photo = gr.File(label="Upload photo of pet symptoms", interactive=True)
                    submit_btn = gr.Button("Submit Diagnosis", elem_id="submit-btn")
                    
                    result = gr.Textbox(label="Diagnosis Result", interactive=False)
                    result_img = gr.Image(label="Symptom Image Preview", interactive=False)
                    common_health = gr.Textbox(label="Confidence Scores", interactive=False)

                with gr.Column(scale=2):
                    with gr.Group():
                        gr.Markdown("## Chat with PawClinic AI", elem_classes=["info-panel"])
                        chatbot = gr.Chatbot(elem_id="result-box", height=500)
                        
                        with gr.Row(elem_classes="chat-container"):
                            chat_input = gr.Textbox(placeholder="Type your question...", elem_classes="chat-input", show_label=False)
                            chat_btn = gr.Button("Send", elem_classes="chat-send")

                        with gr.Row():
                            chat_upload = gr.File(label="Upload Image", elem_classes="upload-box")

                    
                    # ตาม requirement ให้ลบกล่อง "## Pet Information" ออก จึงไม่แสดงข้อมูลสัตว์เลี้ยงที่นี่
            
            
            # submit_btn.click(
            #     submit_form,
            #     inputs=[name, breed, symptom_photo],
            #     outputs=[result, result_img, common_health, result]
            # )
            
            submit_btn.click(
                submit_form,
                inputs=[name, breed, symptom_photo],
                outputs=[result, result_img, common_health, diagnosis_state]
            ).then(
                init_chat,
                inputs=[name, breed, result, symptom_photo],
                outputs=[chatbot, result_img]  # ใช้ result_img เป็นตัวแสดงภาพอาการถ้าต้องการ
            )

            chat_btn.click(
                chat_response,
                inputs=[chat_input, chatbot, chat_upload, diagnosis_state],  # เพิ่ม diagnosis_state
                outputs=[chatbot, chat_input, chat_upload]
            )
            chat_input.submit(
                chat_response,
                inputs=[chat_input, chatbot, chat_upload, diagnosis_state],
                outputs=[chatbot, chat_input, chat_upload]
            )

        # ========== TAB 2: BROWSE PET DISEASES ==========
        with gr.Tab("Browse Pet Diseases"):
            with gr.Row():
                card1_img = gr.Image(label="Dermatitis", interactive=False, height=300)
                card2_img = gr.Image(label="Demodicosis", interactive=False, height=300)
                card3_img = gr.Image(label="Hypersensitivity", interactive=False, height=300)
            
            with gr.Row():
                card4_img = gr.Image(label="Fungal infections", interactive=False, height=300)
                card5_img = gr.Image(label="Ringworm", interactive=False, height=300)

            tabs.select(
                fn=show_disease,
                inputs=None,
                outputs=[card1_img, card2_img, card3_img, card4_img, card5_img]
            )

# ====================== LAUNCH ======================
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=8085)

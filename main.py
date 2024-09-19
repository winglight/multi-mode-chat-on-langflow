import gradio as gr
import requests
import json
import base64
import os
import ssl

os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'

# 禁用 SSL 验证（仅用于测试，不建议在生产环境中使用）
ssl._create_default_https_context = ssl._create_unverified_context

# 其他导入和代码保持不变...

# 在 demo.launch() 之前添加以下代码
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 加载 Langflow Endpoints
def load_endpoints():
    if os.path.exists("langflow_endpoints.json"):
        with open("langflow_endpoints.json", "r") as f:
            return json.load(f)
    return {
        "Default": {
            "host_url": "https://ai.broyustudio.com",
            "flow_id": "215e8762-45c7-45ff-b0e3-913324d15",
            "api_key": "sk-C77dfkdLDLFdse73kJkkjF732iWWCbWPqg"
        }
    }

# 保存 Langflow Endpoints
def save_endpoints(endpoints):
    with open("langflow_endpoints.json", "w") as f:
        json.dump(endpoints, f)

LANGFLOW_ENDPOINTS = load_endpoints()

def load_chat_history():
    if os.path.exists("chat_history.json"):
        with open("chat_history.json", "r") as f:
            return json.load(f)
    return {}

def save_chat_history(history):
    with open("chat_history.json", "w") as f:
        json.dump(history, f)

chat_history = load_chat_history()
current_chat_id = None

def process_message(message, files, audio, selected_endpoint, chat_id):
    global current_chat_id
    current_chat_id = chat_id
    
    if chat_id not in chat_history:
        chat_history[chat_id] = []
    
    # 处理文本消息
    if message:
        chat_history[chat_id].append(("Human", message))
    
    # 处理文件
    if files:
        for file in files:
            if file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                chat_history[chat_id].append(("Human", f"<img src='data:image/png;base64,{base64.b64encode(file.read()).decode()}' style='max-width:300px'>"))
            else:
                chat_history[chat_id].append(("Human", f"Uploaded file: {file.name}"))
    
    # 处理音频
    if audio:
        chat_history[chat_id].append(("Human", f"<audio controls><source src='data:audio/wav;base64,{base64.b64encode(audio).decode()}' type='audio/wav'></audio>"))
    
    # 调用 Langflow API
    try:
        endpoint_config = LANGFLOW_ENDPOINTS[selected_endpoint]
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {endpoint_config['api_key']}"
        }
        payload = {
            "message": message,
            "flow_id": endpoint_config['flow_id']
        }
        response = requests.post(f"{endpoint_config['host_url']}/api/v1/process", 
                                 headers=headers, 
                                 json=payload)
        ai_response = response.json()["output"]
    except Exception as e:
        ai_response = f"Error: {str(e)}"
    
    chat_history[chat_id].append(("AI", ai_response))
    save_chat_history(chat_history)
    
    return chat_history[chat_id]

def start_new_chat():
    global current_chat_id
    current_chat_id = str(len(chat_history) + 1)
    chat_history[current_chat_id] = []
    save_chat_history(chat_history)
    return gr.Dropdown.update(choices=list(chat_history.keys()), value=current_chat_id), []

def load_selected_chat(chat_id):
    global current_chat_id
    current_chat_id = chat_id
    return chat_history[chat_id]

def load_endpoint_details(name):
    if name in LANGFLOW_ENDPOINTS:
        endpoint = LANGFLOW_ENDPOINTS[name]
        return name, endpoint['host_url'], endpoint['flow_id'], endpoint['api_key']
    return "", "", ""

def add_or_update_endpoint(name, host_url, flow_id, api_key):
    if name and host_url and flow_id and api_key:
        LANGFLOW_ENDPOINTS[name] = {
            "host_url": host_url,
            "flow_id": flow_id,
            "api_key": api_key
        }
        save_endpoints(LANGFLOW_ENDPOINTS)
        return list(LANGFLOW_ENDPOINTS.keys()), f"Endpoint '{name}' added/updated successfully."
    return None, "Please fill all fields."

def delete_endpoint(name):
    if name in LANGFLOW_ENDPOINTS:
        del LANGFLOW_ENDPOINTS[name]
        save_endpoints(LANGFLOW_ENDPOINTS)
        return list(LANGFLOW_ENDPOINTS.keys()), f"Endpoint '{name}' deleted successfully."
    return None, "Endpoint not found."

with gr.Blocks() as demo:
    gr.Markdown("# Langflow Chat Interface")
    
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot([], elem_id="chatbot", height=600)
        with gr.Column(scale=1):
            chat_list = gr.Dropdown(choices=list(chat_history.keys()), label="Chat History")
    
    with gr.Row():
        message = gr.Textbox(placeholder="Type your message here...")
        submit = gr.Button("Send")
    
    with gr.Row():
        file_output = gr.File(file_count="multiple", label="Upload Files")
        audio = gr.Audio(sources=["microphone"], type="numpy", label="Record Audio")
    
    with gr.Row():
        endpoint_dropdown = gr.Dropdown(choices=list(LANGFLOW_ENDPOINTS.keys()), value="Default", label="Select Langflow Endpoint")
        new_chat_btn = gr.Button("New Chat")
    
    with gr.Accordion("Manage Endpoints", open=False):
        with gr.Row():
            endpoint_name = gr.Textbox(label="Endpoint Name")
            host_url = gr.Textbox(label="Host URL")
            flow_id = gr.Textbox(label="Flow ID")
            api_key = gr.Textbox(label="API Key")
        with gr.Row():
            add_update_btn = gr.Button("Add/Update Endpoint")
            delete_endpoint_btn = gr.Button("Delete Selected Endpoint")
            load_endpoint_btn = gr.Button("Load Selected Endpoint")
        endpoint_status = gr.Textbox(label="Status", interactive=False)
    
    # Event handlers
    submit.click(process_message, inputs=[message, file_output, audio, endpoint_dropdown, chat_list], outputs=chatbot)
    message.submit(process_message, inputs=[message, file_output, audio, endpoint_dropdown, chat_list], outputs=chatbot)
    new_chat_btn.click(start_new_chat, outputs=[chat_list, chatbot])
    chat_list.change(load_selected_chat, inputs=[chat_list], outputs=chatbot)
    
    # Event handlers for managing endpoints
    add_update_btn.click(add_or_update_endpoint, 
                         inputs=[endpoint_name, host_url, flow_id, api_key], 
                         outputs=[endpoint_dropdown, endpoint_status])
    delete_endpoint_btn.click(delete_endpoint, 
                              inputs=[endpoint_dropdown], 
                              outputs=[endpoint_dropdown, endpoint_status])
    load_endpoint_btn.click(load_endpoint_details, 
                            inputs=[endpoint_dropdown], 
                            outputs=[endpoint_name, host_url, flow_id, api_key])
    endpoint_dropdown.change(load_endpoint_details, 
                             inputs=[endpoint_dropdown], 
                             outputs=[endpoint_name, host_url, flow_id, api_key])

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    # share=True
)
import flet as ft
import logging
from logging.handlers import RotatingFileHandler
import os
import flet_sherpa_onnx as fso
import time
import asyncio

logging.basicConfig(level=logging.DEBUG)
# 设置基础日志配置（在main函数外）
app_data_path = os.getenv("FLET_APP_STORAGE_DATA")
log_file_path = os.path.join(app_data_path, "app.log")
file_handler = RotatingFileHandler(
    log_file_path, maxBytes=1024 * 1024, backupCount=2, encoding="utf-8"  # 1MB
)
file_handler.setLevel(logging.DEBUG)
os.environ["FLET_SECRET_KEY"] = "DEFAULT_SECRET_KEY_CHANGE_IN_PRODUCTION"

# 创建formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# 将formatter添加到handler
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)

async def main(page: ft.Page):
    console_log_filename = await ft.StoragePaths().get_console_log_filename()
    logging.info("test")
    logging.info(f"Console log file: {console_log_filename}")
    logging.info("test")
    
    # 原有的页面设置代码
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.appbar = ft.AppBar(title=ft.Text("flet sherpa onnx"), center_title=True)
    fso_service = fso.FletSherpaOnnx()
    page._services.append(fso_service)
    
    # 创建对话框
    dlg = ft.AlertDialog(
        title=ft.Text("语音识别结果"),
        on_dismiss=lambda e: print("Dialog dismissed!")
    )
    
    # 简化的录音状态管理
    recording_mode = None  # None, "normal", "vad"
    current_recognizer = "Whisper"  # 默认使用Whisper
    # use_vad equals fso_service.useVad
    use_vad = False  # 是否使用VAD
    
    # VAD录音相关变量
    vad_data_text = ft.Text("VAD数据将显示在这里", size=14, selectable=True)

    async def is_recording_status(timeout: float | None = 5.0) -> bool:
        """检查当前是否正在录音"""
        try:
            return await fso_service.IsRecording(timeout=timeout)
        except Exception as ex:
            logging.error(f"检查录音状态时出错: {ex}")
            return False

    async def start_recording(mode):
        """开始录音的通用逻辑
        
        Args:
            mode: 录音模式 ("normal" 或 "vad")
        """
        nonlocal recording_mode
        
        logging.info(f"开始{mode}录音，使用识别器: {current_recognizer}")
        
        # 设置录音状态
        recording_mode = mode
        
        # 更新UI状态
        if mode == "vad":
            vad_record_btn.content = ft.Text("停止VAD录音")
            vad_record_btn.icon = ft.Icons.STOP
            vad_record_btn.style = ft.ButtonStyle(color=ft.Colors.RED)
            vad_status_text.value = "VAD录音中... 正在监听语音活动"
            vad_data_text.value = "等待语音数据..."
        else:
            record_btn.content = ft.Text("停止录音")
            record_btn.icon = ft.Icons.STOP
            record_btn.style = ft.ButtonStyle(color=ft.Colors.RED)
            status_text.value = f"录音中... ({current_recognizer}{' + VAD' if use_vad else ''})"
        
        # 禁用控件
        recognizer_dropdown.disabled = True
        if mode == "vad":
            record_btn.disabled = True
            vad_checkbox.disabled = True
        else:
            vad_checkbox.disabled = True
        
        page.update()
        
        # 初始化识别器
        try:
            recognizer_config = {}
            
            if current_recognizer == "Whisper":
                recognizer_config.update({
                    "recognizer": "Whisper",
                    "encoder": app_data_path+"/base-encoder.onnx",
                    "decoder": app_data_path+"/base-decoder.onnx",
                    "tokens": app_data_path+"/base-tokens.txt"
                })
            elif current_recognizer == "senseVoice":
                recognizer_config.update({
                    "recognizer": "senseVoice",
                    "model": app_data_path+"/model.int8.onnx",
                    "tokens": app_data_path+"/tokens.txt"
                })
            
            # 如果使用VAD或VAD模式，添加VAD配置
            if use_vad or mode == "vad":
                recognizer_config["silerovad"] = app_data_path+"/silero_vad.onnx"
            
            value = await fso_service.CreateRecognizer(**recognizer_config)
            logging.info(f"识别器创建结果: {value}")
            
            # 开始录音
            await fso_service.StartRecording()
            logging.info("录音已开始")
            
            # 如果是VAD模式，启动VAD数据监听
            if mode == "vad":
                page.run_task(_vad_result)
            
        except Exception as ex:
            logging.error(f"开始录音时出错: {ex}")
            if mode == "vad":
                vad_status_text.value = f"错误: {ex}"
            else:
                status_text.value = f"错误: {ex}"
            await reset_recording_state()
            page.update()

    async def stop_recording():
        """停止录音的通用逻辑"""
        if not recording_mode:
            return
            
        current_mode = recording_mode
        logging.info(f"停止{current_mode}录音")
        
        # 更新状态文本
        if current_mode == "normal":
            status_text.value = "处理中..."
        page.update()
        
        try:
            # 停止录音并获取结果
            result = await fso_service.StopRecording()
            logging.info(f"识别结果: {result}")
            
            # 根据不同模式处理结果
            if current_mode == "normal":
                # 普通模式：显示对话框和状态文本
                dlg.content = ft.Text(f"识别结果 ({current_recognizer}{' + VAD' if use_vad else ''}): {result}")
                page.dialog = dlg
                dlg.open = True
                status_text.value = result
            else:  # vad模式
                # VAD模式：在VAD数据区域显示结果
                vad_data_text.value = result
                vad_status_text.value = "VAD录音已停止"
            
            await reset_recording_state()
            page.update()
            
        except Exception as ex:
            logging.error(f"停止录音时出错: {ex}")
            if current_mode == "normal":
                status_text.value = f"错误: {ex}"
            else:
                vad_status_text.value = f"错误: {ex}"
            await reset_recording_state()
            page.update()

    async def toggle_recording(e):
        """切换普通录音状态"""
        if recording_mode == "normal":
            await stop_recording()
        else:
            await start_recording("normal")

    async def toggle_vad_recording(e):
        """切换VAD录音状态"""
        if recording_mode == "vad":
            await stop_recording()
        else:
            await start_recording("vad")

    async def reset_recording_state():
        """重置录音状态"""
        nonlocal recording_mode
        
        if recording_mode == "vad":
            vad_record_btn.content = ft.Text("开始VAD录音")
            vad_record_btn.icon = ft.Icons.MIC
            vad_record_btn.style = ft.ButtonStyle(color=ft.Colors.GREEN)
            record_btn.disabled = False
        elif recording_mode == "normal":
            record_btn.content = ft.Text("开始录音")
            record_btn.icon = ft.Icons.MIC
            record_btn.style = ft.ButtonStyle(color=ft.Colors.BLUE)
        
        # 重新启用所有控件
        recognizer_dropdown.disabled = False
        vad_checkbox.disabled = False
        record_btn.disabled = False
        
        recording_mode = None

    async def _vad_result():
        """VAD数据监听循环"""
        while recording_mode == "vad":
            await asyncio.sleep(10)
            if recording_mode != "vad":
                return
            vad_data = await fso_service.GetVADData()
            if isinstance(vad_data, (list, tuple)):
                formatted_data = "\n".join(str(item) for item in vad_data)
            else:
                formatted_data = str(vad_data)
            vad_data_text.value = formatted_data
            page.update()

    async def switch_recognizer(e):
        nonlocal current_recognizer
        if e.control.value:
            current_recognizer = e.control.value
            status_text.value = f"已切换到: {current_recognizer}"
            logging.info(f"切换到识别器: {current_recognizer}")
            console_log_filename = await ft.StoragePaths().get_console_log_filename()
            logging.info("test")
            logging.info(f"Console log file: {console_log_filename}")
            logging.info("test")
            page.update()

    def toggle_vad(e):
        nonlocal use_vad
        use_vad = e.control.value
        status_text.value = f"VAD: {'启用' if use_vad else '禁用'}"
        logging.info(f"VAD状态: {use_vad}")
        page.update()

    # 创建录音切换按钮
    record_btn = ft.Button(
        content=ft.Text("开始录音"),
        icon=ft.Icons.MIC,
        on_click=toggle_recording,
        style=ft.ButtonStyle(color=ft.Colors.BLUE)
    )
    
    status_text = ft.Text("就绪", size=16)
    
    # VAD录音按钮
    vad_record_btn = ft.Button(
        content=ft.Text("开始VAD录音"),
        icon=ft.Icons.MIC,
        on_click=toggle_vad_recording,
        style=ft.ButtonStyle(color=ft.Colors.GREEN)
    )
    
    vad_status_text = ft.Text("VAD录音就绪", size=14)
    
    # 识别器选择下拉菜单
    recognizer_dropdown = ft.Dropdown(
        label="选择识别器",
        options=[
            ft.dropdown.Option("Whisper"),
            ft.dropdown.Option("senseVoice"),
        ],
        value="Whisper",
        on_change=switch_recognizer,
        width=200
    )
    
    # VAD复选框
    vad_checkbox = ft.Checkbox(
        label="启用VAD (Voice Activity Detection)",
        value=False,
        on_change=toggle_vad
    )

    page.add(
        ft.Column([
            ft.Row([recognizer_dropdown], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([vad_checkbox], alignment=ft.MainAxisAlignment.CENTER),
            
            # 普通录音区域
            ft.Container(
                content=ft.Column([
                    ft.Text("普通录音模式", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([record_btn], alignment=ft.MainAxisAlignment.CENTER),
                    status_text,
                ]),
                padding=10,
                border=ft.Border.all(1, ft.Colors.BLUE),
                border_radius=5,
                margin=5
            ),
            
            # VAD录音区域
            ft.Container(
                content=ft.Column([
                    ft.Text("VAD实时录音模式", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([vad_record_btn], alignment=ft.MainAxisAlignment.CENTER),
                    vad_status_text,
                    ft.Container(
                        content=vad_data_text,
                        width=400,
                        height=100,
                        padding=10,
                        border=ft.Border.all(1, ft.Colors.GREY),
                        border_radius=5
                    )
                ]),
                padding=10,
                border=ft.Border.all(1, ft.Colors.GREEN),
                border_radius=5,
                margin=5
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.ADAPTIVE)
    )

ft.run(main)
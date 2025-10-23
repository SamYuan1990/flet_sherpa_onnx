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
    #os.environ["FLET_APP_STORAGE_TEMP"] = "/tmp/test"
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
    
    # 录音状态标志
    is_recording = False
    current_recognizer = "Whisper"  # 默认使用Whisper
    use_vad = False  # 是否使用VAD
    
    # VAD录音相关变量
    is_vad_recording = False
    vad_data_text = ft.Text("VAD数据将显示在这里", size=14, selectable=True)

    async def is_recording_status(timeout: float | None = 5.0) -> bool:
        """检查当前是否正在录音。
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            bool: 是否正在录音
        """
        try:
            return await fso_service.IsRecording(timeout=timeout)
        except Exception as ex:
            logging.error(f"检查录音状态时出错: {ex}")
            return False

    async def toggle_recording(e):
        """切换录音状态：开始录音或停止录音"""
        nonlocal is_recording
        
        if not is_recording:
            # 开始录音
            await start_recording_logic()
        else:
            # 停止录音
            await stop_recording_logic()

    async def start_recording_logic():
        """开始录音的逻辑"""
        nonlocal is_recording
        
        logging.info(f"开始录音，使用识别器: {current_recognizer}, VAD: {use_vad}")
        is_recording = True
        record_btn.content = ft.Text("停止录音")
        record_btn.icon = ft.Icons.STOP
        record_btn.style = ft.ButtonStyle(color=ft.Colors.RED)
        status_text.value = f"录音中... ({current_recognizer}{' + VAD' if use_vad else ''})"
        recognizer_dropdown.disabled = True  # 录音时禁用识别器切换
        vad_checkbox.disabled = True  # 录音时禁用VAD切换
        page.update()
        
        # 初始化识别器
        try:
            if current_recognizer == "Whisper":
                if use_vad:
                    # 使用VAD+Whisper
                    value = await fso_service.CreateRecognizer(
                        recognizer="Whisper",
                        encoder=app_data_path+"/base-encoder.onnx",
                        decoder=app_data_path+"/base-decoder.onnx",
                        tokens=app_data_path+"/base-tokens.txt",
                        silerovad=app_data_path+"/silero_vad.onnx"  # VAD模型文件
                    )
                else:
                    # 普通Whisper
                    value = await fso_service.CreateRecognizer(
                        recognizer="Whisper",
                        encoder=app_data_path+"/base-encoder.onnx",
                        decoder=app_data_path+"/base-decoder.onnx",
                        tokens=app_data_path+"/base-tokens.txt"
                    )
            elif current_recognizer == "senseVoice":
                if use_vad:
                    # 使用VAD+senseVoice
                    value = await fso_service.CreateRecognizer(
                        recognizer="senseVoice",
                        model=app_data_path+"/model.int8.onnx",
                        tokens=app_data_path+"/tokens.txt",
                        silerovad=app_data_path+"/silero_vad.onnx"  # VAD模型文件
                    )
                else:
                    # 普通senseVoice
                    value = await fso_service.CreateRecognizer(
                        recognizer="senseVoice",
                        model=app_data_path+"/model.int8.onnx",
                        tokens=app_data_path+"/tokens.txt"
                    )
            
            logging.info(f"识别器创建结果: {value}")
            # 开始录音
            await fso_service.StartRecording()
            logging.info("录音已开始")
            
        except Exception as ex:
            logging.error(f"开始录音时出错: {ex}")
            status_text.value = f"错误: {ex}"
            await reset_recording_state()
            page.update()

    async def stop_recording_logic():
        """停止录音的逻辑"""
        nonlocal is_recording
        
        logging.info("停止录音")
        status_text.value = "处理中..."
        page.update()
        try:
            # 停止录音并获取结果
            result = await fso_service.StopRecording()
            logging.info(f"识别结果: {result}")
            
            # 显示结果
            dlg.content = ft.Text(f"识别结果 ({current_recognizer}{' + VAD' if use_vad else ''}): {result}")
            page.dialog = dlg
            dlg.open = True
            
            status_text.value = result
            await reset_recording_state()
            page.update()
            
        except Exception as ex:
            logging.error(f"停止录音时出错: {ex}")
            status_text.value = f"错误: {ex}"
            await reset_recording_state()
            page.update()

    async def reset_recording_state():
        """重置录音状态"""
        nonlocal is_recording
        is_recording = False
        record_btn.content = ft.Text("开始录音")
        record_btn.icon = ft.Icons.MIC
        record_btn.style = ft.ButtonStyle(color=ft.Colors.BLUE)
        recognizer_dropdown.disabled = False  # 重新启用识别器切换
        vad_checkbox.disabled = False  # 重新启用VAD切换

    async def toggle_vad_recording(e):
        """切换VAD录音状态：开始或停止VAD录音"""
        nonlocal is_vad_recording
        
        if not is_vad_recording:
            # 开始VAD录音
            await start_vad_recording(e)
        else:
            # 停止VAD录音
            await stop_vad_recording(e)

    async def start_vad_recording(e=None):
        """开始VAD录音"""
        nonlocal is_vad_recording
        
        if is_vad_recording:
            return
            
        logging.info(f"开始VAD录音，使用识别器: {current_recognizer}")
        
        try:
            # 初始化识别器
            if current_recognizer == "Whisper":
                value = await fso_service.CreateRecognizer(
                    recognizer="Whisper",
                    encoder=app_data_path+"/base-encoder.onnx",
                    decoder=app_data_path+"/base-decoder.onnx",
                    tokens=app_data_path+"/base-tokens.txt",
                    silerovad=app_data_path+"/silero_vad.onnx"  # VAD模型文件
                )
            elif current_recognizer == "senseVoice":
                value = await fso_service.CreateRecognizer(
                    recognizer="senseVoice",
                    model=app_data_path+"/model.int8.onnx",
                    tokens=app_data_path+"/tokens.txt",
                    silerovad=app_data_path+"/silero_vad.onnx"  # VAD模型文件
                )
            
            logging.info(f"VAD录音识别器创建结果: {value}")
            
            # 开始VAD录音
            await fso_service.StartRecordingWithVAD()
            is_vad_recording = True            
            # 更新UI
            vad_record_btn.content = ft.Text("停止VAD录音")
            vad_record_btn.icon = ft.Icons.STOP
            vad_record_btn.style = ft.ButtonStyle(color=ft.Colors.RED)
            vad_status_text.value = "VAD录音中... 正在监听语音活动"
            vad_data_text.value = "等待语音数据..."
            recognizer_dropdown.disabled = True
            record_btn.disabled = True
            page.update()
            
            logging.info("VAD录音已开始")
            page.run_thread(sync_wrapper)
            
        except Exception as ex:
            logging.error(f"开始VAD录音时出错: {ex}")
            vad_status_text.value = f"错误: {ex}"
            page.update()

    # 如果你有一个异步函数，可以这样包装
    async def _vad_result():
        nonlocal is_vad_recording
        while is_vad_recording:
            await asyncio.sleep(10)
            if not is_vad_recording:
                return
            vad_data = await fso_service.GetVADData()
            vad_data_text.value = vad_data
            page.update()

    # 包装成同步函数
    def sync_wrapper():
        # 在当前线程的事件循环中运行
        asyncio.create_task(_vad_result())

    async def stop_vad_recording(e=None):
        """停止VAD录音并获取最终结果"""
        nonlocal is_vad_recording
        
        if not is_vad_recording:
            return
            
        logging.info("停止VAD录音")
        
        try:            
            # 停止VAD录音并获取最终结果
            final_result = await fso_service.StopRecordingWithVAD()
            is_vad_recording = False
            
            # 更新UI
            vad_record_btn.content = ft.Text("开始VAD录音")
            vad_record_btn.icon = ft.Icons.MIC
            vad_record_btn.style = ft.ButtonStyle(color=ft.Colors.GREEN)
            vad_status_text.value = "VAD录音已停止"
            recognizer_dropdown.disabled = False
            record_btn.disabled = False
            
            # 显示最终结果
            #dlg.content = ft.Text(f"VAD录音最终结果 ({current_recognizer}): {final_result}")
            #page.dialog = dlg
            #dlg.open = True
            vad_data_text.value = final_result
            page.update()
            logging.info(f"VAD录音最终结果: {final_result}")
            
        except Exception as ex:
            logging.error(f"停止VAD录音时出错: {ex}")
            vad_status_text.value = f"错误: {ex}"
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
    
    # VAD录音按钮 - 修改为使用切换函数
    vad_record_btn = ft.Button(
        content=ft.Text("开始VAD录音"),
        icon=ft.Icons.MIC,
        on_click=toggle_vad_recording,  # 改为使用切换函数
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
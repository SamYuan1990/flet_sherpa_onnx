import flet as ft
import logging
from logging.handlers import RotatingFileHandler
import os
import flet_sherpa_onnx as fso
import asyncio
logging.basicConfig(level=logging.INFO)

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

def main(page: ft.Page):
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
    
    async def start_recording(e):
        nonlocal is_recording
        if not is_recording:
            logging.info(f"开始录音，使用识别器: {current_recognizer}")
            is_recording = True
            start_btn.disabled = True
            stop_btn.disabled = False
            status_text.value = f"录音中... ({current_recognizer})"
            page.update()
            
            # 初始化识别器
            try:
                if current_recognizer == "Whisper":
                    value = await fso_service.CreateRecognizer(
                        recognizer="Whisper",
                        encoder=app_data_path+"/base-encoder.onnx",
                        # https://hf-mirror.com/csukuangfj/sherpa-onnx-whisper-base/resolve/main/base-encoder.onnx?download=true
                        decoder=app_data_path+"/base-decoder.onnx",
                        # https://hf-mirror.com/csukuangfj/sherpa-onnx-whisper-base/resolve/main/base-decoder.onnx?download=true
                        tokens=app_data_path+"/base-tokens.txt"
                        # https://hf-mirror.com/csukuangfj/sherpa-onnx-whisper-base/resolve/main/base-tokens.txt?download=true
                    )
                elif current_recognizer == "senseVoice":
                    value = await fso_service.CreateRecognizer(
                        recognizer="senseVoice",
                        model=app_data_path+"/model.int8.onnx",
                        # https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09/resolve/main/model.int8.onnx?download=true
                        tokens=app_data_path+"/tokens.txt"
                        # https://hf-mirror.com/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2025-09-09/resolve/main/tokens.txt?download=true
                    )
                
                logging.info(f"识别器创建结果: {value}")
                # 开始录音
                await fso_service.StartRecording()
                logging.info("录音已开始")
            except Exception as ex:
                logging.error(f"开始录音时出错: {ex}")
                status_text.value = f"错误: {ex}"
                is_recording = False
                start_btn.disabled = False
                stop_btn.disabled = True
                page.update()

    async def stop_recording(e):
        nonlocal is_recording
        if is_recording:
            logging.info("停止录音")
            is_recording = False
            stop_btn.disabled = True
            status_text.value = "处理中..."
            page.update()
            
            try:
                # 停止录音并获取结果
                result = await fso_service.StopRecording()
                logging.info(f"识别结果: {result}")
                
                # 显示结果
                dlg.content = ft.Text(f"识别结果 ({current_recognizer}): {result}")
                page.dialog = dlg
                dlg.open = True
                
                status_text.value = "就绪"
                start_btn.disabled = False
                page.update()
                
            except Exception as ex:
                logging.error(f"停止录音时出错: {ex}")
                status_text.value = f"错误: {ex}"
                start_btn.disabled = False
                page.update()

    async def test_whisper(e):
        logging.info("测试Whisper识别器")
        try:
            value = await fso_service.CreateRecognizer(
                Recognizer="Whisper",
                encoder=app_data_path+"/base-encoder.onnx",
                decoder=app_data_path+"/base-decoder.onnx",
                tokens=app_data_path+"/base-tokens.txt"
            )
            logging.info(f"Whisper识别器创建结果: {value}")
            dlg.content = ft.Text(f"Whisper测试成功: {value}")
            page.dialog = dlg
            dlg.open = True
            page.update()
        except Exception as ex:
            logging.error(f"测试Whisper时出错: {ex}")
            dlg.content = ft.Text(f"Whisper测试失败: {ex}")
            page.dialog = dlg
            dlg.open = True
            page.update()

    async def test_sense_voice(e):
        logging.info("测试senseVoice识别器")
        try:
            value = await fso_service.CreateRecognizer(
                Recognizer="senseVoice",
                model=app_data_path+"/model.int8.onnx",
                tokens=app_data_path+"/tokens.txt"
            )
            logging.info(f"senseVoice识别器创建结果: {value}")
            dlg.content = ft.Text(f"senseVoice测试成功: {value}")
            page.dialog = dlg
            dlg.open = True
            page.update()
        except Exception as ex:
            logging.error(f"测试senseVoice时出错: {ex}")
            dlg.content = ft.Text(f"senseVoice测试失败: {ex}")
            page.dialog = dlg
            dlg.open = True
            page.update()

    async def switch_recognizer(e):
        nonlocal current_recognizer
        if e.control.value:
            current_recognizer = e.control.value
            status_text.value = f"已切换到: {current_recognizer}"
            logging.info(f"切换到识别器: {current_recognizer}")
            page.update()

    # 创建按钮和状态文本
    start_btn = ft.Button(
        content="开始录音",
        icon=ft.Icons.MIC,
        on_click=start_recording
    )
    
    stop_btn = ft.Button(
        content="停止录音",
        icon=ft.Icons.STOP,
        on_click=stop_recording,
        disabled=True
    )
    
    status_text = ft.Text("就绪", size=16)
    
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

    page.add(
        ft.Column([
            ft.Row([recognizer_dropdown], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([start_btn, stop_btn], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
            ft.Row([
                ft.Button(content="测试Whisper", on_click=test_whisper),
                ft.Button(content="测试senseVoice", on_click=test_sense_voice),
            ], alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

ft.app(main)
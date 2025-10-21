# flet-sherpa-onnx

[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/SamYuan1990/flet_sherpa_onnx)

FletSherpaOnnx control for Flet

## A flet componment which supports STT
For now, supports whisper and senseVoice.
todo:
- [ ] vad with non streaming asr

## Installation

Add dependency to `pyproject.toml` of your Flet app:

* **Git dependency**

Link to git repository:

```
dependencies = [
  "flet-sherpa-onnx @ git+https://github.com/SamYuan1990/flet-sherpa-onnx",
  "flet>=0.28.3",
]
```

* **PyPi dependency**  

If the package is published on pypi.org:

```
dependencies = [
  "flet-sherpa-onnx @ git+https://github.com/SamYuan1990/flet-sherpa-onnx",
  "flet>=0.28.3",
]
```

Build your app, please ref
[CI](.github/workflows/release.yml)

## Usage
```python
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
        
        logging.info(f"开始录音，使用识别器: {current_recognizer}")
        is_recording = True
        record_btn.content = ft.Text("停止录音")
        record_btn.icon = ft.Icons.STOP
        record_btn.style = ft.ButtonStyle(color=ft.Colors.RED)
        status_text.value = f"录音中... ({current_recognizer})"
        recognizer_dropdown.disabled = True  # 录音时禁用识别器切换
        page.update()
        
        # 初始化识别器
        # to do add test for new parameter silerovad= app_data_path+"/silero_vad_v5.onnx"
        try:
            if current_recognizer == "Whisper":
                value = await fso_service.CreateRecognizer(
                    recognizer="Whisper",
                    encoder=app_data_path+"/base-encoder.onnx",
                    decoder=app_data_path+"/base-decoder.onnx",
                    tokens=app_data_path+"/base-tokens.txt"
                )
            elif current_recognizer == "senseVoice":
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
            dlg.content = ft.Text(f"识别结果 ({current_recognizer}): {result}")
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

    async def test_whisper(e):
        logging.info("测试Whisper识别器")
        try:
            value = await fso_service.CreateRecognizer(
                recognizer="Whisper",
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
                recognizer="senseVoice",
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

    # 创建录音切换按钮
    record_btn = ft.Button(
        content=ft.Text("开始录音"),
        icon=ft.Icons.MIC,
        on_click=toggle_recording,
        style=ft.ButtonStyle(color=ft.Colors.BLUE)
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
            ft.Row([record_btn], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
            ft.Row([
                ft.Button(content="测试Whisper", on_click=test_whisper),
                ft.Button(content="测试senseVoice", on_click=test_sense_voice),
            ], alignment=ft.MainAxisAlignment.CENTER),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

ft.app(main)
```
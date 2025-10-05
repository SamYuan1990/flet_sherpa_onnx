# flet-sherpa-onnx

[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/SamYuan1990/flet_sherpa_onnx)

FletSherpaOnnx control for Flet

## A flet componment which supports STT
For now, supports whisper.

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
    
    async def start_recording(e):
        nonlocal is_recording
        if not is_recording:
            logging.info("开始录音")
            is_recording = True
            start_btn.disabled = True
            stop_btn.disabled = False
            status_text.value = "录音中..."
            page.update()
            
            # 初始化识别器（如果尚未初始化）
            try:
                value = await fso_service.CreateRecognizer(
                    # whisper encoder
                    encoder=app_data_path+"/base-encoder.onnx",
                    # whisper decoder
                    decoder=app_data_path+"/base-decoder.onnx",
                    # whisper tokens
                    tokens=app_data_path+"/base-tokens.txt"
                )
                logging.info(f"识别器创建结果: {value}")
                # 开始录音
                logging.info(type(fso_service))
                logging.info(hasattr(fso_service, 'StartRecording'))
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
                logging.info(type(fso_service))
                logging.info(hasattr(fso_service, 'StopRecording'))
                result = await fso_service.StopRecording()
                logging.info(f"识别结果: {result}")
                
                # 显示结果
                dlg.content = ft.Text(f"识别结果: {result}")
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

    async def test(e: ft.Event[ft.Button]):
        logging.info("test")
        value = await fso_service.test()
        logging.info(value)
        logging.info("test complete")

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

    page.add(
        ft.Column([
            ft.Row([start_btn, stop_btn], alignment=ft.MainAxisAlignment.CENTER),
            status_text,
            ft.Button(content="WAV Encoder Support", on_click=test),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

ft.app(main)
```

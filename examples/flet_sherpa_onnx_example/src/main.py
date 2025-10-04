import flet as ft
import logging
from logging.handlers import RotatingFileHandler
import os
import flet_sherpa_onnx as fso
logging.basicConfig(level=logging.DEBUG)

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
    flet_sherpa_onnx = fso.FletSherpaOnnx()
    page._services.append(flet_sherpa_onnx)
    
    # 创建对话框
    dlg = ft.AlertDialog(
        title=ft.Text("语音识别结果"),
        on_dismiss=lambda e: print("Dialog dismissed!")
    )
    
    async def test(e: ft.Event[ft.Button]):
        logging.info("test")
        value = await flet_sherpa_onnx.test()
        logging.info(value)
        logging.info("test complete")
        logging.info(app_data_path+"/base-encoder.onnx")
        logging.info(app_data_path+"/base-decoder.onnx")
        logging.info(app_data_path+"/base-tokens.txt")
        value = await flet_sherpa_onnx.CreateRecognizer(
            encoder=app_data_path+"/base-encoder.onnx",
            decoder=app_data_path+"/base-decoder.onnx",
            tokens=app_data_path+"/base-tokens.txt"
        )
        logging.info(value)
        logging.info("CreateRecognizer complete")
        logging.info(app_data_path+"/test-audio-file.wav")
        logging.info("STT start")
        value = await flet_sherpa_onnx.STT(
            inputWav=app_data_path+"/test-audio-file.wav"
        )
        logging.info(value)
        logging.info("STT complete")
        
        # 显示弹出窗口
        dlg.content = ft.Text(f"识别结果: {value}")
        page.dialog = dlg
        dlg.open = True
        page.update()

    page.add(
        ft.Button(content="WAV Encoder Support", on_click=test),
    )

ft.run(main)
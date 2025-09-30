import flet as ft
import logging
import flet_sherpa_onnx as fso
logging.basicConfig(level=logging.DEBUG)

def main(page: ft.Page):
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.appbar = ft.AppBar(title=ft.Text("flet sherpa onnx"), center_title=True)
    flet_sherpa_onnx = fso.FletSherpaOnnx()
    page._services.append(flet_sherpa_onnx)
    app_data_path = os.getenv("FLET_APP_STORAGE_DATA")
    
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
        value = await flet_sherpa_onnx.STT(
            inputWav=app_data_path+"/test-audio-file.wav"
        )
        logging.info(value)
        logging.info("CreateRecognizer complete")


    page.add(
        ft.Button(content="WAV Encoder Support", on_click=test),
    )

ft.run(main)


import flet as ft
import logging
import flet_sherpa_onnx as fso
logging.basicConfig(level=logging.DEBUG)

def main(page: ft.Page):
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.appbar = ft.AppBar(title=ft.Text("flet sherpa onnx"), center_title=True)
    flet_sherpa_onnx = fso.FletSherpaOnnx()
    page._services.append(flet_sherpa_onnx)
    
    async def test(e: ft.Event[ft.Button]):
        logging.info("test")
        value = await flet_sherpa_onnx.test()
        logging.info(value)
        logging.info("test complete")


    page.add(
        ft.Button(content="WAV Encoder Support", on_click=test),
    )

ft.run(main)


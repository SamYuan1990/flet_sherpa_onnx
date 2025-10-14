import flet as ft
import logging
from logging.handlers import RotatingFileHandler
import os
import flet_sherpa_onnx as fso
import threading
import time
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
    use_vad = False  # 是否使用VAD
    
    # VAD录音相关变量
    is_vad_recording = False
    vad_thread = None
    vad_stop_event = threading.Event()
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

    # ====== VAD录音相关函数 ======
    def vad_data_polling():
        """VAD数据轮询线程函数"""
        start_time = time.time()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        while not vad_stop_event.is_set():
            try:
                # 使用异步方式获取VAD数据
                vad_data = loop.run_until_complete(fso_service.GetVADData())
                
                if vad_data and vad_data.strip():
                    # 更新VAD数据显示
                    current_time = time.time() - start_time
                    # 使用page.add()来安全地更新UI
                    page.add(ft.Text(f"[{current_time:.1f}s] {vad_data}", visible=False))
                    vad_data_text.value = f"[{current_time:.1f}s] {vad_data}"
                    page.update()
                    logging.info(f"获取到VAD数据: {vad_data}")
                
                # 每隔0.5秒获取一次
                time.sleep(0.5)
                
            except Exception as ex:
                logging.error(f"获取VAD数据时出错: {ex}")
                if is_vad_recording:
                    # 安全地更新状态文本
                    page.add(ft.Text(f"获取VAD数据错误: {ex}", visible=False))
                    vad_status_text.value = f"获取VAD数据错误: {ex}"
                    page.update()
                break
        
        loop.close()

    async def start_vad_recording(e):
        """开始VAD录音"""
        nonlocal is_vad_recording, vad_thread
        
        if is_vad_recording:
            return
            
        logging.info(f"开始VAD录音，使用识别器: {current_recognizer}")
        
        try:
            # 重置停止事件
            vad_stop_event.clear()
            
            # 初始化识别器
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
            
            logging.info(f"VAD录音识别器创建结果: {value}")
            
            # 开始VAD录音
            await fso_service.StartRecordingWithVAD()
            is_vad_recording = True
            
            # 启动VAD数据轮询线程
            vad_thread = threading.Thread(target=vad_data_polling, daemon=True)
            vad_thread.start()
            
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
            
        except Exception as ex:
            logging.error(f"开始VAD录音时出错: {ex}")
            vad_status_text.value = f"错误: {ex}"
            page.update()

    async def stop_vad_recording(e):
        """停止VAD录音并获取最终结果"""
        nonlocal is_vad_recording, vad_thread
        
        if not is_vad_recording:
            return
            
        logging.info("停止VAD录音")
        
        try:
            # 设置停止事件，停止轮询线程
            vad_stop_event.set()
            
            # 等待线程结束（最多等待2秒）
            if vad_thread and vad_thread.is_alive():
                vad_thread.join(timeout=2.0)
            
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
            dlg.content = ft.Text(f"VAD录音最终结果 ({current_recognizer}): {final_result}")
            page.dialog = dlg
            dlg.open = True
            
            page.update()
            logging.info(f"VAD录音最终结果: {final_result}")
            
        except Exception as ex:
            logging.error(f"停止VAD录音时出错: {ex}")
            vad_status_text.value = f"错误: {ex}"
            page.update()

    async def test_vad_functions(e):
        """测试VAD相关功能"""
        logging.info("测试VAD相关功能")
        
        try:
            # 先创建识别器
            if current_recognizer == "Whisper":
                await fso_service.CreateRecognizer(
                    recognizer="Whisper",
                    encoder=app_data_path+"/base-encoder.onnx",
                    decoder=app_data_path+"/base-decoder.onnx",
                    tokens=app_data_path+"/base-tokens.txt"
                )
            elif current_recognizer == "senseVoice":
                await fso_service.CreateRecognizer(
                    recognizer="senseVoice",
                    model=app_data_path+"/model.int8.onnx",
                    tokens=app_data_path+"/tokens.txt"
                )
            
            # 测试StartRecordingWithVAD
            await fso_service.StartRecordingWithVAD()
            test_status = "StartRecordingWithVAD - 成功"
            logging.info("StartRecordingWithVAD测试成功")
            
            # 等待一下然后获取VAD数据
            await asyncio.sleep(1)
            vad_data = await fso_service.GetVADData()
            test_status += f"\nGetVADData - 成功: '{vad_data}'"
            logging.info(f"GetVADData测试成功: {vad_data}")
            
            # 停止录音
            final_result = await fso_service.StopRecordingWithVAD()
            test_status += f"\nStopRecordingWithVAD - 成功: '{final_result}'"
            logging.info(f"StopRecordingWithVAD测试成功: {final_result}")
            
            # 显示测试结果
            dlg.content = ft.Text(f"VAD功能测试成功:\n{test_status}")
            page.dialog = dlg
            dlg.open = True
            page.update()
            
        except Exception as ex:
            logging.error(f"VAD功能测试失败: {ex}")
            dlg.content = ft.Text(f"VAD功能测试失败: {ex}")
            page.dialog = dlg
            dlg.open = True
            page.update()

    # ====== 原有的测试函数 ======
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

    async def test_whisper_vad(e):
        logging.info("测试VAD+Whisper识别器")
        try:
            value = await fso_service.CreateRecognizer(
                recognizer="Whisper",
                encoder=app_data_path+"/base-encoder.onnx",
                decoder=app_data_path+"/base-decoder.onnx",
                tokens=app_data_path+"/base-tokens.txt",
                silerovad=app_data_path+"/silero_vad.onnx"  # VAD模型文件
            )
            logging.info(f"VAD+Whisper识别器创建结果: {value}")
            dlg.content = ft.Text(f"VAD+Whisper测试成功: {value}")
            page.dialog = dlg
            dlg.open = True
            page.update()
        except Exception as ex:
            logging.error(f"测试VAD+Whisper时出错: {ex}")
            dlg.content = ft.Text(f"VAD+Whisper测试失败: {ex}")
            page.dialog = dlg
            dlg.open = True
            page.update()

    async def test_sense_voice_vad(e):
        logging.info("测试VAD+senseVoice识别器")
        try:
            value = await fso_service.CreateRecognizer(
                recognizer="senseVoice",
                model=app_data_path+"/model.int8.onnx",
                tokens=app_data_path+"/tokens.txt",
                silerovad=app_data_path+"/silero_vad.onnx"  # VAD模型文件
            )
            logging.info(f"VAD+senseVoice识别器创建结果: {value}")
            dlg.content = ft.Text(f"VAD+senseVoice测试成功: {value}")
            page.dialog = dlg
            dlg.open = True
            page.update()
        except Exception as ex:
            logging.error(f"测试VAD+senseVoice时出错: {ex}")
            dlg.content = ft.Text(f"VAD+senseVoice测试失败: {ex}")
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
        on_click=start_vad_recording,
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
                border=ft.border.all(1, ft.Colors.BLUE),
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
                        border=ft.border.all(1, ft.Colors.GREY),
                        border_radius=5
                    )
                ]),
                padding=10,
                border=ft.border.all(1, ft.Colors.GREEN),
                border_radius=5,
                margin=5
            ),
            
            # 测试按钮区域
            ft.Container(
                content=ft.Column([
                    ft.Text("功能测试", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([
                        ft.Button(content="测试Whisper", on_click=test_whisper),
                        ft.Button(content="测试senseVoice", on_click=test_sense_voice),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row([
                        ft.Button(content="测试VAD+Whisper", on_click=test_whisper_vad),
                        ft.Button(content="测试VAD+senseVoice", on_click=test_sense_voice_vad),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row([
                        ft.Button(content="测试VAD功能", on_click=test_vad_functions, 
                                 style=ft.ButtonStyle(color=ft.Colors.PURPLE)),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                ]),
                padding=10,
                border=ft.border.all(1, ft.Colors.ORANGE),
                border_radius=5,
                margin=5
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.ADAPTIVE)
    )

ft.app(main)
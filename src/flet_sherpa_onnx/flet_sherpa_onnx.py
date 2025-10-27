import flet as ft
import logging
from typing import Optional, Literal

__all__ = ["FletSherpaOnnx"]

@ft.control("FletSherpaOnnx")
class FletSherpaOnnx(ft.Service):
    """
    FletSherpaOnnx Control description.
    """

    def __init__(self):
        super().__init__()
        self._useVad = False  # 内部变量，表示是否使用VAD

    @property
    def useVad(self) -> bool:
        """获取是否使用VAD的状态"""
        return self._useVad

    async def CreateRecognizer(
        self,
        recognizer: Literal["senseVoice", "Whisper"] = "Whisper",
        silerovad: Optional[str] = None,
        encoder: Optional[str] = None,
        decoder: Optional[str] = None,
        tokens: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = 10
    ) -> Optional[str]:
        """
        Create a speech recognizer.

        Args:
            recognizer: Type of recognizer, either "senseVoice" or "Whisper". Defaults to "Whisper".
            silerovad: vad model path if you want to enable vad.
            encoder: Path to encoder model file. Optional.
            decoder: Path to decoder model file. Optional.
            tokens: Path to tokens file. Optional.
            model: Path to model file. Optional.
            timeout: Method timeout in seconds. Defaults to 10.

        Returns:
            The result string or None if failed.

        Raises:
            ValueError: If recognizer is not one of the allowed values.
        """
        # Validate recognizer parameter
        if recognizer not in ["senseVoice", "Whisper"]:
            raise ValueError(f"recognizer must be 'senseVoice' or 'Whisper', got '{recognizer}'")

        # 根据silerovad参数设置useVad状态
        self._useVad = silerovad is not None and silerovad.strip() != ""

        return await self._invoke_method(
            method_name="CreateRecognizer",
            arguments={
                "recognizer": recognizer,
                "silero-vad": silerovad,
                "encoder": encoder,
                "decoder": decoder,
                "model": model,
                "tokens": tokens
            },
            timeout=timeout,
        )

    async def StartRecording(self, timeout: Optional[float] = 10) -> Optional[str]:
        return await self._invoke_method(
            method_name="StartRecording",
            timeout=timeout,
        )

    async def StopRecording(self, timeout: Optional[float] = 10) -> Optional[str]:
        return await self._invoke_method(
            method_name="StopRecording",
            timeout=timeout
        )

    async def is_recording(self, timeout: float | None = 10.0) -> bool:
        """检查是否正在录制。
        
        Args:
            timeout: 超时时间（秒），None表示无超时
            
        Returns:
            bool: 是否正在录制
            
        Raises:
            TimeoutError: 操作超时
            Other exceptions from _invoke_method
        """
        return await self._invoke_method(
            method_name="IsRecording",
            timeout=timeout
        )

    async def GetVADData(self, timeout: Optional[float] = 10) -> Optional[str]:
        logging.info("invoke GetVADData to dart code")
        return await self._invoke_method(
            method_name="GetVADData",
            timeout=timeout
        )
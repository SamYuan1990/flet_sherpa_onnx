import flet as ft
import logging
from typing import Optional

__all__ = ["FletSherpaOnnx"]
# this will mapping my python code to dart
@ft.control("FletSherpaOnnx")
class FletSherpaOnnx(ft.Service):
    """
    FletSherpaOnnx Control description.
    """

    async def test(self, timeout: Optional[float] = 10) -> Optional[str]:
        return await self._invoke_method(
            method_name="test_method",
            arguments={},
            timeout=timeout,
        )

    async def CreateRecognizer(self, encoder,decoder,tokens, timeout: Optional[float] = 10) -> Optional[str]:
        #"output_path": output_path,
        #"configuration": configuration
        return await self._invoke_method(
            method_name="CreateRecognizer",
            arguments={
                "encoder": encoder,
                "decoder": decoder,
                "tokens": tokens
            },
            timeout=timeout,
        )

    async def StartRecording(self, timeout: Optional[float] = 10) -> Optional[str]:
        return await self._invoke_method(
            method_name="start_recording",
            arguments={},
            timeout=timeout,
        )

    async def StopRecording(self, timeout: Optional[float] = 10) -> Optional[str]:
        return await self._invoke_method("stop_recording", timeout=timeout)

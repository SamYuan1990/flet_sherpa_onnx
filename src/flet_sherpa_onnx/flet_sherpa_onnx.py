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
    print("we are here")

    async def test(self, timeout: Optional[float] = 10) -> Optional[str]:
        print("method testing")
        return await self._invoke_method(
            method_name="test_method",
            arguments={},
            timeout=timeout,
        )
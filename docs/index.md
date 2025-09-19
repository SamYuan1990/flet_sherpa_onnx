# Introduction

FletSherpaOnnx for Flet.

## Examples

```
import flet as ft

from flet_sherpa_onnx import FletSherpaOnnx


def main(page: ft.Page):
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    page.add(

                ft.Container(height=150, width=300, alignment = ft.alignment.center, bgcolor=ft.Colors.PURPLE_200, content=FletSherpaOnnx(
                    tooltip="My new FletSherpaOnnx Control tooltip",
                    value = "My new FletSherpaOnnx Flet Control", 
                ),),

    )


ft.app(main)
```

## Classes

[FletSherpaOnnx](FletSherpaOnnx.md)



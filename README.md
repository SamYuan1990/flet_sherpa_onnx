# flet-sherpa-onnx

[![zread](https://img.shields.io/badge/Ask_Zread-_.svg?style=flat&color=00b0aa&labelColor=000000&logo=data%3Aimage%2Fsvg%2Bxml%3Bbase64%2CPHN2ZyB3aWR0aD0iMTYiIGhlaWdodD0iMTYiIHZpZXdCb3g9IjAgMCAxNiAxNiIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTQuOTYxNTYgMS42MDAxSDIuMjQxNTZDMS44ODgxIDEuNjAwMSAxLjYwMTU2IDEuODg2NjQgMS42MDE1NiAyLjI0MDFWNC45NjAxQzEuNjAxNTYgNS4zMTM1NiAxLjg4ODEgNS42MDAxIDIuMjQxNTYgNS42MDAxSDQuOTYxNTZDNS4zMTUwMiA1LjYwMDEgNS42MDE1NiA1LjMxMzU2IDUuNjAxNTYgNC45NjAxVjIuMjQwMUM1LjYwMTU2IDEuODg2NjQgNS4zMTUwMiAxLjYwMDEgNC45NjE1NiAxLjYwMDFaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00Ljk2MTU2IDEwLjM5OTlIMi4yNDE1NkMxLjg4ODEgMTAuMzk5OSAxLjYwMTU2IDEwLjY4NjQgMS42MDE1NiAxMS4wMzk5VjEzLjc1OTlDMS42MDE1NiAxNC4xMTM0IDEuODg4MSAxNC4zOTk5IDIuMjQxNTYgMTQuMzk5OUg0Ljk2MTU2QzUuMzE1MDIgMTQuMzk5OSA1LjYwMTU2IDE0LjExMzQgNS42MDE1NiAxMy43NTk5VjExLjAzOTlDNS42MDE1NiAxMC42ODY0IDUuMzE1MDIgMTAuMzk5OSA0Ljk2MTU2IDEwLjM5OTlaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik0xMy43NTg0IDEuNjAwMUgxMS4wMzg0QzEwLjY4NSAxLjYwMDEgMTAuMzk4NCAxLjg4NjY0IDEwLjM5ODQgMi4yNDAxVjQuOTYwMUMxMC4zOTg0IDUuMzEzNTYgMTAuNjg1IDUuNjAwMSAxMS4wMzg0IDUuNjAwMUgxMy43NTg0QzE0LjExMTkgNS42MDAxIDE0LjM5ODQgNS4zMTM1NiAxNC4zOTg0IDQuOTYwMVYyLjI0MDFDMTQuMzk4NCAxLjg4NjY0IDE0LjExMTkgMS42MDAxIDEzLjc1ODQgMS42MDAxWiIgZmlsbD0iI2ZmZiIvPgo8cGF0aCBkPSJNNCAxMkwxMiA0TDQgMTJaIiBmaWxsPSIjZmZmIi8%2BCjxwYXRoIGQ9Ik00IDEyTDEyIDQiIHN0cm9rZT0iI2ZmZiIgc3Ryb2tlLXdpZHRoPSIxLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIvPgo8L3N2Zz4K&logoColor=ffffff)](https://zread.ai/SamYuan1990/flet_sherpa_onnx)
[![Release Multi-Platform Build](https://github.com/SamYuan1990/flet_sherpa_onnx/actions/workflows/release.yml/badge.svg)](https://github.com/SamYuan1990/flet_sherpa_onnx/actions/workflows/release.yml)
[![Publish Python 🐍 distribution 📦 to PyPI and TestPyPI](https://github.com/SamYuan1990/flet_sherpa_onnx/actions/workflows/pip.yml/badge.svg)](https://github.com/SamYuan1990/flet_sherpa_onnx/actions/workflows/pip.yml)

## An ASR/STT library for flet basing on sherpa-onnx

### Release log

0.2.2 Bug Fix for vad stopping.
0.2.1 UX change in python code, clean code in dart. Better version system.
0.0.2 Support for vad + whisper and senseVoice, for real time ASR.

todo in 0.3.x
- [ ] onlinestreaming model(extend scope of model, worth a release)

todo in 0.4.x
- [ ] event support(need testing with flet, UX change worth a release)
- [ ] declarative example(waiting for flet, UX change worth a release)

## Design pattern

- To reduce cognitive load, all parameter set to default as possible.
- Platform support 1st, parakeet-tdt with 0.6 large.... for a little model, just limit language support. Hence, Small Model Multi-lanuage Support, unless new issue been created.

## Installation

[pypi](https://pypi.org/project/flet-sherpa-onnx/)

Add dependency to `pyproject.toml` of your Flet app:

```
dependencies = [
  "flet-sherpa-onnx==0.2.1",
  "flet>=0.28.3",
]
```

Build your app, please ref
[CI](.github/workflows/release.yml).

## Usage [Show me the code](examples/flet_sherpa_onnx_example/src/main.py)
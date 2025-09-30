# flet-sherpa-onnx
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
    flet_sherpa_onnx = fso.FletSherpaOnnx()
    page._services.append(flet_sherpa_onnx)
    await flet_sherpa_onnx.CreateRecognizer(
            # whisper encoder with sherpa_onnx
            encoder=app_data_path+"/base-encoder.onnx",
            # whisper decoder with sherpa_onnx
            decoder=app_data_path+"/base-decoder.onnx",
            # whisper tokens with sherpa_onnx
            tokens=app_data_path+"/base-tokens.txt"
        )
    await flet_sherpa_onnx.STT(
            inputWav=app_data_path+"/test-audio-file.wav"
        )
```

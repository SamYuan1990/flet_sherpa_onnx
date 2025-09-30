import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flet/flet.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa_onnx;

class FletSherpaOnnxService extends FletService {
  FletSherpaOnnxService({required super.control});

  // 类内共享变量
  late sherpa_onnx.OfflineRecognizer recognizer;
  late sherpa_onnx.OfflineWhisperModelConfig whisper;
  late sherpa_onnx.OfflineModelConfig modelConfig;
  late sherpa_onnx.OfflineRecognizerConfig config;

  @override
  void init() {
    super.init();
    debugPrint("FletSherpaOnnxService(${control.id}).init: ${control.properties}");
    control.addInvokeMethodListener(_invokeMethod);
  }

  @override
  void dispose() {
    debugPrint("FletSherpaOnnxService(${control.id}).dispose()");
    control.removeInvokeMethodListener(_invokeMethod);
    
    // 清理资源
    recognizer.free();
    
    super.dispose();
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    debugPrint("FletSherpaOnnxService.$name($args)");
    
    try {
      switch (name) {
        case "test_method":
          return "response from dart";
          
        case "CreateRecognizer":
          return _createRecognizer(args);
          
        case "STT":
          return _speechToText(args);
          
        default:
          throw Exception("Unknown FletSherpaOnnxService method: $name");
      }
    } catch (e) {
      debugPrint("Error in FletSherpaOnnxService.$name: $e");
      rethrow;
    }
  }

  // 创建识别器的独立方法
  String _createRecognizer(dynamic args) {
    whisper = sherpa_onnx.OfflineWhisperModelConfig(
      encoder: args["encoder"],
      decoder: args["decoder"],
    );
    
    modelConfig = sherpa_onnx.OfflineModelConfig(
      whisper: whisper,
      tokens: args["tokens"],
      modelType: 'whisper',
      debug: false,
      numThreads: 1,
    );
    
    config = sherpa_onnx.OfflineRecognizerConfig(model: modelConfig);
    recognizer = sherpa_onnx.OfflineRecognizer(config);
    
    return "Recognizer created successfully";
  }

  // 语音识别的独立方法
  String _speechToText(dynamic args) {
    // 检查识别器是否已创建
    if (recognizer == null) {
      throw Exception("Recognizer not created. Call CreateRecognizer first.");
    }

    final waveData = sherpa_onnx.readWave(args["inputWav"]);
    final stream = recognizer.createStream();
    
    try {
      stream.acceptWaveform(
        samples: waveData.samples, 
        sampleRate: waveData.sampleRate
      );
      recognizer.decode(stream);
      final result = recognizer.getResult(stream);
      return result.text;
    } finally {
      // 确保stream被释放
      stream.free();
    }
  }
}
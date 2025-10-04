import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:flet/flet.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa_onnx;
import 'package:record/record.dart';

class FletSherpaOnnxService extends FletService {
  FletSherpaOnnxService({required super.control});

  bool _isInitialized = false;
  
  // 语音识别相关变量
  late sherpa_onnx.OfflineRecognizer recognizer;
  late sherpa_onnx.OfflineWhisperModelConfig whisper;
  late sherpa_onnx.OfflineModelConfig modelConfig;
  late sherpa_onnx.OfflineRecognizerConfig config;

  // 录音相关变量
  late final AudioRecorder _audioRecorder;
  StreamSubscription<RecordState>? _recordSub;
  RecordState _recordState = RecordState.stop;
  
  // 音频流处理相关
  late sherpa_onnx.OfflineStream _stream;
  static const int _sampleRate = 16000;
  final List<int> _audioBuffer = []; // 改为存储原始字节数据

  @override
  void init() {
    super.init();
    debugPrint("FletSherpaOnnxService(${control.id}).init: ${control.properties}");
    
    // 初始化录音器
    _audioRecorder = AudioRecorder();
    
    // 监听录音状态变化
    _recordSub = _audioRecorder.onStateChanged().listen((recordState) {
      _updateRecordState(recordState);
    });
    
    sherpa_onnx.initBindings();
    _isInitialized = true;
    control.addInvokeMethodListener(_invokeMethod);
  }

  @override
  void dispose() {
    debugPrint("FletSherpaOnnxService(${control.id}).dispose()");
    control.removeInvokeMethodListener(_invokeMethod);
    
    // 清理资源
    _recordSub?.cancel();
    _audioRecorder.dispose();
    recognizer.free();
    _stream.free();
    
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
          
        case "StartRecording":
          return await _startRecording();
          
        case "StopRecording":
          return await _stopRecording();
          
        case "CancelRecording":
          return await _cancelRecording();
          
        case "IsRecording":
          return await _isRecording();
          
        case "HasPermission":
          return await _hasPermission();
          
        default:
          throw Exception("Unknown FletSherpaOnnxService method: $name");
      }
    } catch (e) {
      debugPrint("Error in FletSherpaOnnxService.$name: $e");
      rethrow;
    }
  }

  // 创建识别器
  String _createRecognizer(dynamic args) {
    if (!_isInitialized) {
      sherpa_onnx.initBindings();
      _isInitialized = true;
    }
    
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
    _stream = recognizer.createStream();
    
    return "Recognizer created successfully";
  }

  // 开始录音
  Future<bool> _startRecording() async {
    try {
      if (!await _audioRecorder.hasPermission()) {
        debugPrint("No recording permission");
        return false;
      }

      const encoder = AudioEncoder.pcm16bits;
      
      if (!await _audioRecorder.isEncoderSupported(encoder)) {
        debugPrint("Encoder not supported");
        return false;
      }

      const config = RecordConfig(
        encoder: encoder,
        sampleRate: _sampleRate,
        numChannels: 1,
      );

      // 清空音频缓冲区
      _audioBuffer.clear();

      // 开始录音流
      final audioStream = await _audioRecorder.startStream(config);

      audioStream.listen(
        (data) {
          // 直接存储原始字节数据到缓冲区
          _audioBuffer.addAll(data);
        },
        onDone: () {
          debugPrint("Audio stream completed");
        },
        onError: (error) {
          debugPrint("Audio stream error: $error");
        },
      );

      return true;
    } catch (e) {
      debugPrint("Error starting recording: $e");
      return false;
    }
  }

  // 停止录音并执行STT
  Future<String> _stopRecording() async {
    try {
      await _audioRecorder.stop();
      
      // 确保所有音频数据都已处理
      if (_audioBuffer.isNotEmpty) {
        // 将字节数据转换为 Float32List
        final float32Samples = _convertBytesToFloat32(Uint8List.fromList(_audioBuffer));
        
        // 使用缓冲区中的所有数据进行最终识别
        _stream.acceptWaveform(samples: float32Samples, sampleRate: _sampleRate);
        recognizer.decode(_stream);
        final result = recognizer.getResult(_stream);
        
        // 重置流以准备下一次识别
        _stream.free();
        _stream = recognizer.createStream();
        
        // 清空缓冲区
        _audioBuffer.clear();
        
        return result.text;
      }
      
      return "";
    } catch (e) {
      debugPrint("Error stopping recording: $e");
      return "";
    }
  }

  // 取消录音
  Future<void> _cancelRecording() async {
    await _audioRecorder.stop();
    _audioBuffer.clear();
    
    // 重置流
    _stream.free();
    _stream = recognizer.createStream();
  }

  // 检查是否正在录音
  Future<bool> _isRecording() async {
    return await _audioRecorder.isRecording();
  }

  // 检查是否有录音权限
  Future<bool> _hasPermission() async {
    return await _audioRecorder.hasPermission();
  }

  // 更新录音状态
  void _updateRecordState(RecordState recordState) {
    _recordState = recordState;
    // 可以在这里触发状态变化事件
    var stateMap = {
      RecordState.record: "recording",
      RecordState.pause: "paused", 
      RecordState.stop: "stopped",
    };
    control.triggerEvent("recording_state_change", stateMap[recordState]);
  }

  // 将字节数据转换为float32格式
  Float32List _convertBytesToFloat32(Uint8List bytes, [Endian endian = Endian.little]) {
    final values = Float32List(bytes.length ~/ 2);

    final data = ByteData.view(bytes.buffer);

    for (var i = 0; i < bytes.length; i += 2) {
      int short = data.getInt16(i, endian);
      values[i ~/ 2] = short / 32768.0;
    }

    return values;
  }
}

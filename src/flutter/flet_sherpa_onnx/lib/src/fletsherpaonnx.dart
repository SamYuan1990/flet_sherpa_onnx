import 'dart:async';
import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:flet/flet.dart';
import 'package:sherpa_onnx/sherpa_onnx.dart' as sherpa_onnx;
import 'package:record/record.dart';
import 'package:synchronized/synchronized.dart';

class FletSherpaOnnxService extends FletService {
  FletSherpaOnnxService({required super.control});

  bool _isInitialized = false;
  
  // 语音识别相关变量
  late sherpa_onnx.OfflineRecognizer recognizer;
  late sherpa_onnx.OfflineWhisperModelConfig whisper;
  late sherpa_onnx.OfflineSenseVoiceModelConfig senseVoice;
  late sherpa_onnx.OfflineModelConfig modelConfig;
  late sherpa_onnx.OfflineRecognizerConfig config;
  late sherpa_onnx.OfflineStream _stream;

  // VAD相关全局变量
  sherpa_onnx.VoiceActivityDetector? vad;
  sherpa_onnx.VadModelConfig? vadConfig;
  sherpa_onnx.CircularBuffer? _circularBuffer;
  bool _useVad = false;
  final List<String> _vadresult = [];
  int _vadWindowSize = 512;
  
  // 录音相关变量
  late final AudioRecorder _audioRecorder;
  StreamSubscription<RecordState>? _recordSub;
  RecordState _recordState = RecordState.stop;
  
  // 音频流处理相关
  static const int _sampleRate = 16000;
  final List<double> _audioBuffer = [];
  
  // 使用 synchronized 包的 Lock 替代原来的锁对象
  final _vadResultLock = Lock();
  final _audioBufferLock = Lock();

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
    
    // 使用同步锁清理资源
    _vadResultLock.synchronized(() {
      _vadresult.clear();
    });
    
    _audioBufferLock.synchronized(() {
      _audioBuffer.clear();
    });
    
    // 清理CircularBuffer
    try {
      _circularBuffer?.free();
    } catch (e) {
      debugPrint("Error freeing circular buffer: $e");
    }
    
    // 只在对象已创建的情况下释放资源
    try {
      recognizer.free();
    } catch (e) {
      debugPrint("Error freeing recognizer: $e");
    }
    
    try {
      _stream.free();
    } catch (e) {
      debugPrint("Error freeing stream: $e");
    }

    // if enable vad
    try {
      vad?.free();
    } catch (e) {
      debugPrint("Error freeing VAD: $e");
    }
    
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

        case "StartRecordingWithVAD":
          return await _startRecordingWithVAD();
          
        case "StopRecordingWithVAD":
          return await _stopRecordingWithVAD();

        case "GetVADData":
          return await _getVADData();
          
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

    // new logic for Recognizer creation loop
    // input parameter as Recognizer value in string of Whisper or senseVoice
    String recognizerType = args["recognizer"];
    
    if (recognizerType == "Whisper") {
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
    } 
    // logic for senseVoice
    else if (recognizerType == "senseVoice") {
      senseVoice = sherpa_onnx.OfflineSenseVoiceModelConfig(
        model: args["model"], 
        language: args["language"] ?? '',
        useInverseTextNormalization: args["useInverseTextNormalization"] ?? false
      );
    
      modelConfig = sherpa_onnx.OfflineModelConfig(
        senseVoice: senseVoice,
        tokens: args["tokens"],
        debug: false,
        numThreads: 1,
      );
    } else {
      throw Exception("Unsupported Recognizer type: $recognizerType. Supported types: 'Whisper' or 'senseVoice'");
    }

    // VAD配置逻辑 - 根据是否传入VAD模型路径来判断是否启用VAD
    final sileroVadModel = args["silero-vad"];
    _useVad = sileroVadModel != null && sileroVadModel.isNotEmpty;

    if (_useVad) {
      final sileroVadConfig = sherpa_onnx.SileroVadModelConfig(
        model: sileroVadModel,
        minSilenceDuration: 0.25,
        minSpeechDuration: 0.5,
        maxSpeechDuration: 5.0,
      );
      vadConfig = sherpa_onnx.VadModelConfig(
        sileroVad: sileroVadConfig,
        numThreads: 1,
        debug: false,
      );
      
      // 获取VAD窗口大小
      _vadWindowSize = vadConfig!.sileroVad.windowSize;
      
      vad = sherpa_onnx.VoiceActivityDetector(
        config: vadConfig!, 
        bufferSizeInSeconds: 10
      );
      
      debugPrint("VAD initialized with window size: $_vadWindowSize");
    }

    config = sherpa_onnx.OfflineRecognizerConfig(model: modelConfig);
    recognizer = sherpa_onnx.OfflineRecognizer(config);
    _stream = recognizer.createStream();
    
    return "Recognizer created successfully${_useVad ? ' with VAD' : ''}";
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

      // 使用同步锁清空音频缓冲区
      await _audioBufferLock.synchronized(() {
        _audioBuffer.clear();
      });

      // 开始录音流
      final audioStream = await _audioRecorder.startStream(config);

      audioStream.listen(
        (data) {
          // 直接存储原始字节数据到缓冲区（使用同步锁）
          final float32Samples = _convertBytesToFloat32(Uint8List.fromList(data));
          _audioBufferLock.synchronized(() {
            _audioBuffer.addAll(float32Samples);
          });
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
      
      // 使用同步锁确保线程安全地访问音频缓冲区
      return await _audioBufferLock.synchronized(() async {
        // 确保所有音频数据都已处理
        if (_audioBuffer.isNotEmpty) {
          // 使用缓冲区中的所有数据进行最终识别 - 转换为 Float32List
          final float32Samples = Float32List.fromList(_audioBuffer);
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
      });
    } catch (e) {
      debugPrint("Error stopping recording: $e");
      return "";
    }
  }

  // 取消录音
  Future<void> _cancelRecording() async {
    await _audioRecorder.stop();
    
    // 使用同步锁清理多个资源
    await _audioBufferLock.synchronized(() {
      _audioBuffer.clear();
    });
    
    await _vadResultLock.synchronized(() {
      _vadresult.clear();
    });
    
    // 重置流
    _stream.free();
    _stream = recognizer.createStream();
    
    // 重置VAD
    vad?.reset();
    
    // 清理CircularBuffer
    try {
      _circularBuffer?.free();
      _circularBuffer = null;
    } catch (e) {
      debugPrint("Error freeing circular buffer: $e");
    }
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

  // 开始带VAD的录音
  Future<bool> _startRecordingWithVAD() async {
    try {
      if (!await _audioRecorder.hasPermission()) {
        debugPrint("No recording permission");
        return false;
      }

      if (!_useVad || vad == null) {
        debugPrint("VAD not initialized or not enabled");
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

      // 使用同步锁清空音频缓冲区和VAD结果
      await _audioBufferLock.synchronized(() {
        _audioBuffer.clear();
      });
      
      await _vadResultLock.synchronized(() {
        _vadresult.clear();
      });
      
      vad?.reset();
      
      // 初始化CircularBuffer - 30秒容量
      _circularBuffer?.free();
      _circularBuffer = sherpa_onnx.CircularBuffer(capacity: 30 * _sampleRate);

      debugPrint("Starting VAD recording with circular buffer");

      // 开始录音流
      final audioStream = await _audioRecorder.startStream(config);

      audioStream.listen(
        (data) {
          // 将字节数据转换为float32格式
          final float32Samples = _convertBytesToFloat32(Uint8List.fromList(data));
          
          // 将数据添加到CircularBuffer
          _circularBuffer!.push(float32Samples);
          
          // 处理完整窗口的数据
          while (_circularBuffer!.size >= _vadWindowSize) {
            final samples = _circularBuffer!.get(
              startIndex: _circularBuffer!.head, 
              n: _vadWindowSize
            );
            _circularBuffer!.pop(_vadWindowSize);
              
            vad!.acceptWaveform(samples);
              
            // 处理所有检测到的语音片段
            while (!vad!.isEmpty()) {
              final segment = vad!.front();
              final segmentSamples = segment.samples;
              
              // 为每个语音片段创建独立的流进行处理
              final segmentStream = recognizer.createStream();
              segmentStream.acceptWaveform(samples: segmentSamples, sampleRate: _sampleRate);
              recognizer.decode(segmentStream);
              final result = recognizer.getResult(segmentStream);
                
              // 将识别结果添加到vadresult（使用同步锁确保线程安全）
              _vadResultLock.synchronized(() {
                _vadresult.add(result.text);
              });
                
              segmentStream.free();
              vad!.pop();
            }
          }
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
      debugPrint("Error starting recording with VAD: $e");
      return false;
    }
  }

  // 停止带VAD的录音 - 基于SenseVoice示例的完整版本
  Future<String> _stopRecordingWithVAD() async {
    try {
      await _audioRecorder.stop();
      
      String finalResult = "";
      
      if (_useVad && vad != null && _circularBuffer != null) {
        debugPrint("Flushing VAD with remaining buffer size: ${_circularBuffer!.size}");
        
        // 刷新VAD以处理剩余数据
        vad!.flush();
        
        // 处理剩余的VAD片段
        while (!vad!.isEmpty()) {
          final segment = vad!.front();
          final samples = segment.samples;          
          final segmentStream = recognizer.createStream();
          segmentStream.acceptWaveform(samples: samples, sampleRate: _sampleRate);
          recognizer.decode(segmentStream);
          final result = recognizer.getResult(segmentStream);
          finalResult = result.text;
          
          segmentStream.free();
          vad!.pop();
        }
      
        // 清理CircularBuffer
        _circularBuffer!.free();
        _circularBuffer = null;
      }
      
      return finalResult; // 只返回剩余音频的识别结果
    } catch (e) {
      debugPrint("Error stopping recording with VAD: $e");
      return "";
    }
  }

  // 获取VAD数据并重置（线程安全版本）
  Future<List<String>> _getVADData() async {
    return await _vadResultLock.synchronized(() {
      List<String> temp = List.from(_vadresult);
      _vadresult.clear();
      return temp;
    });
  }
}
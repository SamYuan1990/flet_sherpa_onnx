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
  late sherpa_onnx.OfflineSenseVoiceModelConfig senseVoice;
  late sherpa_onnx.OfflineModelConfig modelConfig;
  late sherpa_onnx.OfflineRecognizerConfig config;
  late sherpa_onnx.OfflineStream _stream;

  // VAD相关全局变量
  sherpa_onnx.VoiceActivityDetector? vad;
  sherpa_onnx.VadModelConfig? vadConfig;
  bool _useVad = false;
  final List<String> _vadresult = [];
  int _vadStartIndex = 0;
  int _vadWindowSize = 512; // 默认值，会在VAD初始化时更新
  
  // 录音相关变量
  late final AudioRecorder _audioRecorder;
  StreamSubscription<RecordState>? _recordSub;
  RecordState _recordState = RecordState.stop;
  
  // 音频流处理相关
  static const int _sampleRate = 16000;
  final List<double> _audioBuffer = [];
  
  // 用于同步访问vadresult的锁
  final _vadResultLock = Object();

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
          return _getVADData();
          
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
        bufferSizeInSeconds: 60
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

      // 清空音频缓冲区
      _audioBuffer.clear();

      // 开始录音流
      final audioStream = await _audioRecorder.startStream(config);

      audioStream.listen(
        (data) {
          // 直接存储原始字节数据到缓冲区
          final float32Samples = _convertBytesToFloat32(Uint8List.fromList(data));
          _audioBuffer.addAll(float32Samples);
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
        // 使用缓冲区中的所有数据进行最终识别
        _stream.acceptWaveform(samples: _audioBuffer, sampleRate: _sampleRate);
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
    
    // 重置VAD
    vad?.reset();
    synchronized(_vadResultLock, () {
      _vadresult.clear();
    });
    _vadStartIndex = 0;
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
  List<double> _convertBytesToFloat32(Uint8List bytes, [Endian endian = Endian.little]) {
    final values = <double>[];
    final data = ByteData.view(bytes.buffer);

    for (var i = 0; i < bytes.length; i += 2) {
      int short = data.getInt16(i, endian);
      values.add(short / 32768.0);
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

      // 清空音频缓冲区和VAD结果
      _audioBuffer.clear();
      synchronized(_vadResultLock, () {
        _vadresult.clear();
      });
      _vadStartIndex = 0;

      // 开始录音流
      final audioStream = await _audioRecorder.startStream(config);

      audioStream.listen(
        (data) {
          // 将字节数据转换为float32格式
          final float32Samples = _convertBytesToFloat32(Uint8List.fromList(data));
          _audioBuffer.addAll(float32Samples);
          
          // 检查音频缓冲区是否有足够长度处理VAD
          int numSamples = _audioBuffer.length;
          int numIter = numSamples ~/ _vadWindowSize;
          
          // 处理每个VAD窗口
          for (int i = 0; i < numIter; ++i) {
            int start = _vadStartIndex + i * _vadWindowSize;
            if (start + _vadWindowSize <= _audioBuffer.length) {
              List<double> windowSamples = _audioBuffer.sublist(start, start + _vadWindowSize);
              
              vad!.acceptWaveform(Float32List.fromList(windowSamples));
              
              while (!vad!.isEmpty()) {
                final segment = vad!.front();
                
                // 使用全局_stream而不是创建新的stream
                // 注意：需要确保_stream在当前处理完成前不被其他操作使用
                _stream.acceptWaveform(samples: segment.samples, sampleRate: _sampleRate);
                recognizer.decode(_stream);
                final result = recognizer.getResult(_stream);
                
                // 将识别结果添加到vadresult（线程安全）
                synchronized(_vadResultLock, () {
                  _vadresult.add(result.text);
                });
                
                // 重置stream以准备下一个segment
                _stream.free();
                _stream = recognizer.createStream();
                
                vad!.pop();
              }
            }
          }
          
          // 更新起始索引
          _vadStartIndex += numIter * _vadWindowSize;
          
          // 如果处理了数据，修剪音频缓冲区以避免无限增长
          if (numIter > 0 && _vadStartIndex > _vadWindowSize * 10) {
            _audioBuffer.removeRange(0, _vadStartIndex - _vadWindowSize);
            _vadStartIndex = _vadWindowSize;
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

  // 停止带VAD的录音并执行最终STT（只返回剩余音频的识别结果）
  Future<String> _stopRecordingWithVAD() async {
    try {
      await _audioRecorder.stop();
      
      String finalResult = "";
      
      // 处理剩余的未识别音频数据
      if (_audioBuffer.length > _vadStartIndex) {
        List<double> remainingSamples = _audioBuffer.sublist(_vadStartIndex);
        
        if (remainingSamples.isNotEmpty) {
          // 使用全局_stream处理剩余音频
          _stream.acceptWaveform(samples: remainingSamples, sampleRate: _sampleRate);
          recognizer.decode(_stream);
          final result = recognizer.getResult(_stream);
          finalResult = result.text;
          
          // 重置stream
          _stream.free();
          _stream = recognizer.createStream();
        }
      }
      
      // 清空缓冲区和重置索引
      _audioBuffer.clear();
      _vadStartIndex = 0;
      
      // 注意：这里不清理_vadresult，因为_getVADData还需要访问它
      
      return finalResult; // 只返回剩余音频的识别结果
    } catch (e) {
      debugPrint("Error stopping recording with VAD: $e");
      return "";
    }
  }

  // 获取VAD数据并重置（线程安全版本）
  List<String> _getVADData() {
    return synchronized(_vadResultLock, () {
      List<String> temp = List.from(_vadresult);
      _vadresult.clear();
      return temp;
    });
  }

  // 简单的同步执行辅助函数
  T synchronized<T>(Object lock, T Function() action) {
    synchronized(lock) {
      return action();
    }
  }
}
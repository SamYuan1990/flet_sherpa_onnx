// wavfileprocessor.dart

import 'dart:typed_data';
import 'dart:io';
import 'dart:math';

class WavData {
  final Float32List samples;
  final int sampleRate;

  WavData(this.samples, this.sampleRate);
}

class WavFileProcessor {
  static Future<WavData> loadWavFile(String filePath) async {
    try {
      // 首先尝试标准 WAV 解析
      return await _loadStandardWav(filePath);
    } catch (e) {
      print('标准 WAV 解析失败: $e');
      print('尝试强制转换为标准格式...');
      // 如果标准解析失败，使用强制转换
      return await _loadWithForceConversion(filePath);
    }
  }
  
  static Future<WavData> _loadStandardWav(String filePath) async {
    final file = File(filePath);
    final bytes = await file.readAsBytes();
    return _processWavData(Uint8List.fromList(bytes));
  }
  
  static WavData _processWavData(Uint8List wavData) {
    if (wavData.length < 44) {
      throw Exception('文件太小，不是有效的 WAV 文件');
    }
    
    final byteData = ByteData.view(wavData.buffer);
    
    // 检查 RIFF 头
    final riffHeader = String.fromCharCodes(wavData.sublist(0, 4));
    final waveHeader = String.fromCharCodes(wavData.sublist(8, 12));
    
    if (riffHeader != 'RIFF' || waveHeader != 'WAVE') {
      throw Exception('不是有效的 WAV 文件: RIFF=$riffHeader, WAVE=$waveHeader');
    }
    
    // 查找 fmt 块
    int fmtChunkOffset = 12;
    bool foundFmt = false;
    int audioFormat = 0;
    int numChannels = 0;
    int sampleRate = 0;
    int bitsPerSample = 0;
    int fmtChunkSize = 0;
    
    while (fmtChunkOffset + 8 < wavData.length) {
      final chunkId = String.fromCharCodes(wavData.sublist(fmtChunkOffset, fmtChunkOffset + 4));
      final chunkSize = byteData.getUint32(fmtChunkOffset + 4, Endian.little);
      
      if (chunkId == 'fmt ') {
        // 读取 WAV 文件头信息
        audioFormat = byteData.getUint16(fmtChunkOffset + 8, Endian.little);
        numChannels = byteData.getUint16(fmtChunkOffset + 10, Endian.little);
        sampleRate = byteData.getUint32(fmtChunkOffset + 12, Endian.little);
        bitsPerSample = byteData.getUint16(fmtChunkOffset + 22, Endian.little);
        fmtChunkSize = chunkSize;
        
        print('WAV 文件信息:');
        print('音频格式: $audioFormat (${audioFormat == 1 ? 'PCM' : '非PCM'})');
        print('声道数: $numChannels');
        print('采样率: $sampleRate Hz');
        print('位深度: $bitsPerSample bits');
        
        foundFmt = true;
        break;
      }
      fmtChunkOffset += 8 + chunkSize;
    }
    
    if (!foundFmt) {
      throw Exception('未找到格式块');
    }
    
    // 查找 data 块
    int dataChunkOffset = fmtChunkOffset + 8 + fmtChunkSize;
    bool foundData = false;
    int dataSize = 0;
    int dataStart = 0;
    
    while (dataChunkOffset + 8 < wavData.length) {
      final dataChunkId = String.fromCharCodes(wavData.sublist(dataChunkOffset, dataChunkOffset + 4));
      dataSize = byteData.getUint32(dataChunkOffset + 4, Endian.little);
      
      if (dataChunkId == 'data') {
        dataStart = dataChunkOffset + 8;
        foundData = true;
        break;
      }
      dataChunkOffset += 8 + dataSize;
    }
    
    if (!foundData) {
      throw Exception('未找到数据块');
    }
    
    print('数据大小: $dataSize bytes');
    
    // 提取音频数据部分
    final audioData = Uint8List.sublistView(wavData, dataStart, min(dataStart + dataSize, wavData.length));
    
    Float32List samples;
    
    // 根据位深度和格式选择不同的处理方法
    if (bitsPerSample == 16 && audioFormat == 1) {
      samples = _convertInt16ToFloat32(audioData);
    } else if (bitsPerSample == 8 && audioFormat == 1) {
      samples = _convertInt8ToFloat32(audioData);
    } else if (bitsPerSample == 32 && audioFormat == 1) { // 32-bit PCM
      samples = _convertInt32ToFloat32(audioData);
    } else if (bitsPerSample == 32 && audioFormat == 3) { // 32-bit float
      samples = _convertFloat32ToFloat32(audioData);
    } else if (audioFormat == 6) { // A-law
      samples = _convertALawToFloat32(audioData);
    } else if (audioFormat == 7) { // μ-law
      samples = _convertMuLawToFloat32(audioData);
    } else {
      throw Exception('不支持的音频格式: 格式=$audioFormat, 位深度=$bitsPerSample bits');
    }
    
    // 如果是多声道，只取第一个声道
    if (numChannels > 1) {
      samples = _convertToMono(samples, numChannels);
    }
    
    return WavData(samples, sampleRate);
  }
  
  static Future<WavData> _loadWithForceConversion(String filePath) async {
    final file = File(filePath);
    final bytes = await file.readAsBytes();
    
    print('文件总大小: ${bytes.length} bytes');
    
    // 尝试多种可能的偏移量来查找音频数据
    List<int> possibleOffsets = [0, 44, 58, 60, 128, 132, 256];
    WavData? result;
    
    for (int offset in possibleOffsets) {
      if (offset >= bytes.length) continue;
      
      try {
        print('尝试偏移量: $offset');
        result = _forceConvertToFloat32(bytes, offset);
        print('使用偏移量 $offset 成功转换');
        break;
      } catch (e) {
        print('偏移量 $offset 失败: $e');
      }
    }
    
    if (result != null) {
      return result;
    }
    
    // 如果所有固定偏移量都失败，尝试自动检测
    print('尝试自动检测音频数据起始位置...');
    final autoResult = _autoDetectAndConvert(bytes);
    if (autoResult != null) {
      return autoResult;
    }
    
    throw Exception('无法处理音频文件: 所有转换方法都失败了');
  }
  
  static WavData _forceConvertToFloat32(Uint8List bytes, int dataStart) {
    // 假设采样率为 16000 Hz（常见的语音识别采样率）
    final sampleRate = 16000;
    
    // 计算可用的音频数据长度
    final usableBytes = bytes.length - dataStart;
    if (usableBytes <= 0) {
      throw Exception('数据起始位置超出文件范围');
    }
    
    // 假设是 16-bit 小端序 PCM 数据
    final sampleCount = usableBytes ~/ 2;
    final samples = Float32List(sampleCount);
    final data = ByteData.view(bytes.buffer, bytes.offsetInBytes + dataStart);
    
    for (var i = 0; i < sampleCount; i++) {
      final short = data.getInt16(i * 2, Endian.little);
      samples[i] = short / 32768.0; // 归一化到 [-1.0, 1.0]
    }
    
    print('强制转换结果: 采样率=$sampleRate Hz, 采样点数=$sampleCount');
    
    return WavData(samples, sampleRate);
  }
  
  static WavData? _autoDetectAndConvert(Uint8List bytes) {
    // 简单的自动检测：查找可能包含音频数据的区域
    // 通过分析数据的变化模式来检测
    
    // 尝试将整个文件当作 16-bit PCM 处理
    try {
      final sampleCount = bytes.length ~/ 2;
      final samples = Float32List(sampleCount);
      final data = ByteData.view(bytes.buffer);
      
      double sum = 0;
      double maxVal = 0;
      
      for (var i = 0; i < sampleCount; i++) {
        final short = data.getInt16(i * 2, Endian.little);
        final sample = short / 32768.0;
        samples[i] = sample;
        
        sum += sample.abs();
        maxVal = max(maxVal, sample.abs());
      }
      
      final average = sum / sampleCount;
      
      // 检查数据特征，确认是否是有效的音频数据
      if (maxVal > 0.01 && average > 0.001) {
        print('自动检测成功: 平均幅度=$average, 最大幅度=$maxVal');
        return WavData(samples, 16000);
      }
    } catch (e) {
      print('自动检测失败: $e');
    }
    
    return null;
  }
  
  // 处理 16-bit PCM 数据
  static Float32List _convertInt16ToFloat32(Uint8List bytes, [Endian endian = Endian.little]) {
    final values = Float32List(bytes.length ~/ 2);
    final data = ByteData.view(bytes.buffer);
    
    for (var i = 0; i < bytes.length; i += 2) {
      int short = data.getInt16(i, endian);
      values[i ~/ 2] = short / 32768.0; // 归一化到 [-1.0, 1.0]
    }
    
    return values;
  }
  
  // 处理 8-bit PCM 数据
  static Float32List _convertInt8ToFloat32(Uint8List bytes) {
    final values = Float32List(bytes.length);
    final data = ByteData.view(bytes.buffer);
    
    for (var i = 0; i < bytes.length; i++) {
      int byte = data.getInt8(i);
      values[i] = byte / 128.0; // 归一化到 [-1.0, 1.0]
    }
    
    return values;
  }
  
  // 处理 32-bit PCM 数据
  static Float32List _convertInt32ToFloat32(Uint8List bytes, [Endian endian = Endian.little]) {
    final values = Float32List(bytes.length ~/ 4);
    final data = ByteData.view(bytes.buffer);
    
    for (var i = 0; i < bytes.length; i += 4) {
      int int32 = data.getInt32(i, endian);
      values[i ~/ 4] = int32 / 2147483648.0; // 归一化到 [-1.0, 1.0]
    }
    
    return values;
  }
  
  // 处理 32-bit float 数据
  static Float32List _convertFloat32ToFloat32(Uint8List bytes, [Endian endian = Endian.little]) {
    final values = Float32List(bytes.length ~/ 4);
    final data = ByteData.view(bytes.buffer);
    
    for (var i = 0; i < bytes.length; i += 4) {
      double floatValue = data.getFloat32(i, endian);
      values[i ~/ 4] = floatValue;
    }
    
    return values;
  }
  
  // A-law 解码（简化版）
  static Float32List _convertALawToFloat32(Uint8List bytes) {
    final values = Float32List(bytes.length);
    
    for (var i = 0; i < bytes.length; i++) {
      final compressed = bytes[i] ^ 0x55;
      final sign = compressed & 0x80;
      var exponent = (compressed >> 4) & 0x07;
      var mantissa = compressed & 0x0F;
      
      if (exponent != 0) {
        mantissa = mantissa + 16;
      }
      
      mantissa = (mantissa << 4) + 0x08;
      
      var sample = 0;
      if (exponent == 0) {
        sample = mantissa;
      } else {
        sample = (mantissa << exponent) - 0x08;
      }
      
      if (sign == 0) {
        sample = -sample;
      }
      
      values[i] = sample / 32768.0;
    }
    
    return values;
  }
  
  // μ-law 解码（简化版）
  static Float32List _convertMuLawToFloat32(Uint8List bytes) {
    final values = Float32List(bytes.length);
    final muLawBias = 33;
    
    for (var i = 0; i < bytes.length; i++) {
      final compressed = ~bytes[i];
      final sign = compressed & 0x80;
      var exponent = (compressed >> 4) & 0x07;
      var mantissa = compressed & 0x0F;
      
      var sample = ((mantissa << 3) + muLawBias) << exponent;
      sample -= muLawBias;
      
      if (sign == 0) {
        sample = -sample;
      }
      
      values[i] = sample / 32768.0;
    }
    
    return values;
  }
  
  // 将多声道转换为单声道
  static Float32List _convertToMono(Float32List samples, int numChannels) {
    final monoLength = samples.length ~/ numChannels;
    final mono = Float32List(monoLength);
    
    for (var i = 0; i < monoLength; i++) {
      double sum = 0.0;
      for (var channel = 0; channel < numChannels; channel++) {
        sum += samples[i * numChannels + channel];
      }
      mono[i] = sum / numChannels;
    }
    
    return mono;
  }
}
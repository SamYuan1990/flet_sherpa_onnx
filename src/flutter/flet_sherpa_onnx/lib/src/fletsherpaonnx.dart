import 'dart:async';

import 'package:flet/flet.dart';

class FletSherpaOnnxService extends FletService {
  FletSherpaOnnxService({required super.control});

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
    super.dispose();
  }

  Future<dynamic> _invokeMethod(String name, dynamic args) async {
    debugPrint("FletSherpaOnnxService.$name($args)");
    switch (name) {
      case "test_method":
        return "response from dart";
      default:
        throw Exception("Unknown FletSherpaOnnxService method: $name");
    }
  }
}

import 'package:flet/flet.dart';

import 'fletsherpaonnx.dart';

class Extension extends FletExtension {
  @override
  FletService? createService(Control control) {
    switch (control.type) {
      case "FletSherpaOnnx":
        return FletSherpaOnnxService(control: control);
      default:
        return null;
    }
  }
}

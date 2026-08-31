import 'package:flutter/services.dart';
import 'package:tflite_flutter/tflite_flutter.dart';

class ClassifierResult {
  final String label;
  final double confidence;
  final int inferenceMs;

  ClassifierResult({
    required this.label,
    required this.confidence,
    required this.inferenceMs,
  });
}

class ClassifierService {
  static const _modelPath = 'assets/models/best_model_quantized.tflite';
  static const _labelsPath = 'assets/labels_rice.txt';

  Interpreter? _interpreter;
  List<String> _labels = [];
  bool _isReady = false;

  bool get isReady => _isReady;

  Future<void> init() async {
    _labels = (await rootBundle.loadString(_labelsPath))
        .split('\n')
        .where((e) => e.trim().isNotEmpty)
        .toList();

    try {
      _interpreter = await Interpreter.fromAsset(_modelPath);
      _isReady = true;
    } catch (e) {
      _isReady = false;
    }
  }

  Future<ClassifierResult?> classify(Uint8List imageBytes) async {
    if (!_isReady || _interpreter == null) return null;

    final stopwatch = Stopwatch()..start();
    try {
      final inputShape = _interpreter!.getInputTensor(0).shape;
      final outputShape = _interpreter!.getOutputTensor(0).shape;
      final inputSize = inputShape[1];

      final input = List.filled(
        1 * inputSize * inputSize * 3,
        0.0,
      ).reshape([1, inputSize, inputSize, 3]);
      final output = List.filled(
        outputShape.reduce((a, b) => a * b),
        0.0,
      ).reshape([1, outputShape.last]);

      _interpreter!.run(input, output);

      stopwatch.stop();

      final scores = output[0] as List<double>;
      int maxIdx = 0;
      double maxVal = scores[0];
      for (int i = 1; i < scores.length; i++) {
        if (scores[i] > maxVal) {
          maxVal = scores[i];
          maxIdx = i;
        }
      }

      final label = maxIdx < _labels.length ? _labels[maxIdx] : 'unknown';

      return ClassifierResult(
        label: label,
        confidence: maxVal,
        inferenceMs: stopwatch.elapsedMilliseconds,
      );
    } catch (e) {
      stopwatch.stop();
      return null;
    }
  }

  void dispose() {
    _interpreter?.close();
    _interpreter = null;
    _isReady = false;
  }
}

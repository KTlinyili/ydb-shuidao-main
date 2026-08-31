import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:shared_preferences/shared_preferences.dart';

class ApiService {
  // 后端地址 — 手机上用电脑局域网IP
  // 模拟器用10.0.2.2，真机用电脑IP（如192.168.x.x）
  static const String _defaultBaseUrl = 'http://192.168.31.232:8000';
  static String baseUrl = _defaultBaseUrl;
  static const String _prefsKey = 'api_base_url';

  static Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    final saved = prefs.getString(_prefsKey);
    if (saved != null && saved.isNotEmpty) {
      baseUrl = saved;
    }
  }

  static Future<void> setBaseUrl(String url) async {
    baseUrl = url;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefsKey, url);
  }

  static Future<Map<String, dynamic>?> classifyImage(XFile image) async {
    final uri = Uri.parse('$baseUrl/api/v1/diagnosis/classify');
    final request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('image', image.path));
    final response = await request.send();
    if (response.statusCode == 200) {
      return jsonDecode(await response.stream.bytesToString());
    }
    return null;
  }

  static Future<Map<String, dynamic>?> runDiagnosis(XFile image, {String caseText = ''}) async {
    final uri = Uri.parse('$baseUrl/api/v1/diagnosis/run');
    final request = http.MultipartRequest('POST', uri)
      ..fields['problem_name'] = '水稻病虫害诊断报告'
      ..fields['case_text'] = caseText
      ..fields['stage'] = 'initial'
      ..fields['n_rounds'] = '2'
      ..files.add(await http.MultipartFile.fromPath('image', image.path));
    final response = await request.send();
    if (response.statusCode == 200) {
      return jsonDecode(await response.stream.bytesToString());
    }
    return null;
  }

  static Future<Map<String, dynamic>> fetchDiseases() async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/multimodal/text/keywords'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to load diseases: ${response.statusCode}');
  }

  static Future<Map<String, dynamic>?> textDiagnosis(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/v1/multimodal/text'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'text': text, 'crop': 'rice'}),
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    return null;
  }

  static Future<Map<String, dynamic>> fetchHistory({int limit = 20}) async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/history?limit=$limit'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to load history: ${response.statusCode}');
  }

  static Future<Map<String, dynamic>> fetchWarnings({int limit = 20}) async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/warnings?limit=$limit'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to load warnings: ${response.statusCode}');
  }

  static Future<Map<String, dynamic>> fetchEnvironment() async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/environment/current'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to load environment: ${response.statusCode}');
  }

  static Future<Map<String, dynamic>> fetchDevices() async {
    final response = await http.get(Uri.parse('$baseUrl/api/v1/environment/devices'));
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    }
    throw Exception('Failed to load devices: ${response.statusCode}');
  }

  static Future<bool> ackWarning(String id) async {
    final response = await http.post(Uri.parse('$baseUrl/api/v1/warnings/$id/ack'));
    return response.statusCode == 200;
  }

  static Future<bool> closeWarning(String id) async {
    final response = await http.post(Uri.parse('$baseUrl/api/v1/warnings/$id/close'));
    return response.statusCode == 200;
  }

  static Future<bool> checkHealth() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/health')).timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }
}

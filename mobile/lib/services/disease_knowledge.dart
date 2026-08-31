import 'dart:convert';
import 'package:flutter/services.dart' show rootBundle;

class DiseaseInfo {
  final String key;
  final String name;
  final String nameEn;
  final List<String> keywords;
  final String symptoms;
  final String treatment;
  final String prevention;
  final String riskLevel;
  final String favorableConditions;

  DiseaseInfo({
    required this.key,
    required this.name,
    required this.nameEn,
    required this.keywords,
    required this.symptoms,
    required this.treatment,
    required this.prevention,
    required this.riskLevel,
    required this.favorableConditions,
  });

  factory DiseaseInfo.fromJson(Map<String, dynamic> json) {
    return DiseaseInfo(
      key: json['key'] ?? '',
      name: json['name'] ?? '',
      nameEn: json['name_en'] ?? '',
      keywords: List<String>.from(json['keywords'] ?? []),
      symptoms: json['symptoms'] ?? '',
      treatment: json['treatment'] ?? '',
      prevention: json['prevention'] ?? '',
      riskLevel: json['risk_level'] ?? 'low',
      favorableConditions: json['favorable_conditions'] ?? '',
    );
  }
}

class DiseaseKnowledge {
  static List<DiseaseInfo>? _cache;

  static Future<List<DiseaseInfo>> load() async {
    if (_cache != null) return _cache!;
    final jsonStr = await rootBundle.loadString('assets/data/diseases_rice.json');
    final List<dynamic> jsonList = jsonDecode(jsonStr);
    _cache = jsonList.map((e) => DiseaseInfo.fromJson(e as Map<String, dynamic>)).toList();
    return _cache!;
  }

  static Future<DiseaseInfo?> findByKey(String key) async {
    final all = await load();
    for (final d in all) {
      if (d.key == key) return d;
    }
    return null;
  }

  static Future<List<DiseaseInfo>> search(String query) async {
    final all = await load();
    final lower = query.toLowerCase();
    return all.where((d) {
      if (d.name.contains(query)) return true;
      if (d.nameEn.toLowerCase().contains(lower)) return true;
      if (d.keywords.any((k) => k.contains(query) || query.contains(k))) return true;
      if (d.symptoms.contains(query)) return true;
      return false;
    }).toList();
  }
}

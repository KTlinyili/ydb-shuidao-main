import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../services/api_service.dart';
import '../services/disease_knowledge.dart';

class DiseaseDetailPage extends StatefulWidget {
  final String diseaseKey;
  const DiseaseDetailPage({super.key, required this.diseaseKey});

  @override
  State<DiseaseDetailPage> createState() => _DiseaseDetailPageState();
}

class _DiseaseDetailPageState extends State<DiseaseDetailPage> {
  Map<String, dynamic>? _disease;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadDetail();
  }

  Future<void> _loadDetail() async {
    // 直接用本地完整数据（API缺少treatment/prevention字段且key可能不一致）
    try {
      final local = await DiseaseKnowledge.findByKey(widget.diseaseKey);
      if (local != null) {
        setState(() {
          _disease = {
            'key': local.key,
            'name': local.name,
            'name_en': local.nameEn,
            'keywords': local.keywords,
            'symptoms': local.symptoms,
            'treatment': local.treatment,
            'prevention': local.prevention,
            'favorable': local.favorableConditions,
          };
          _loading = false;
        });
        return;
      }
    } catch (_) {}
    // 本地没有，尝试API
    try {
      final result = await ApiService.fetchDiseases().timeout(const Duration(seconds: 5));
      final diseases = result['diseases'] as List;
      for (final d in diseases) {
        if (d['key'] == widget.diseaseKey) {
          setState(() {
            _disease = d;
            _loading = false;
          });
          return;
        }
      }
    } catch (_) {}
    setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => context.pop(),
        ),
        title: Text(
          _disease?['name'] ?? '病害详情',
          style: const TextStyle(color: Colors.white, fontSize: 18),
        ),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF2E7D32)))
          : _disease == null
              ? const Center(child: Text('未找到该病害信息', style: TextStyle(color: Colors.white54)))
              : ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    // 标题卡片
                    Container(
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          colors: [const Color(0xFF2E7D32).withOpacity(0.15), const Color(0xFF1E1E1E)],
                          begin: Alignment.topLeft,
                          end: Alignment.bottomRight,
                        ),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 60, height: 60,
                            decoration: BoxDecoration(color: const Color(0xFF2E7D32).withOpacity(0.2), borderRadius: BorderRadius.circular(16)),
                            child: const Icon(Icons.eco, color: Color(0xFF66BB6A), size: 30),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('水稻：${_disease!['name']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white)),
                                const SizedBox(height: 4),
                                Text(_disease!['name_en'] ?? '', style: const TextStyle(fontSize: 14, color: Colors.white54)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: 20),

                    // 症状
                    _buildSection(
                      Icons.sick,
                      '症状特征',
                      _formatList(_disease!['symptoms']),
                      Colors.orangeAccent,
                    ),
                    const SizedBox(height: 16),

                    // 治疗
                    _buildSection(
                      Icons.medical_services,
                      '治疗方法',
                      _formatList(_disease!['treatment']),
                      const Color(0xFF2E7D32),
                    ),
                    const SizedBox(height: 16),

                    // 预防
                    _buildSection(
                      Icons.shield,
                      '预防措施',
                      _formatList(_disease!['prevention']),
                      Colors.lightBlueAccent,
                    ),
                    const SizedBox(height: 16),

                    // 易发条件
                    if (_disease!['favorable'] != null && _disease!['favorable'].toString().isNotEmpty) ...[
                      _buildSection(
                        Icons.wb_sunny,
                        '易发条件',
                        _disease!['favorable'].toString(),
                        Colors.amber,
                      ),
                      const SizedBox(height: 16),
                    ],

                    // 关键词
                    if (_disease!['keywords'] != null && (_disease!['keywords'] as List).isNotEmpty) ...[
                      const Text('识别关键词', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white)),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: (_disease!['keywords'] as List).map((k) => Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: const Color(0xFF2E7D32).withOpacity(0.15),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: const Color(0xFF2E7D32).withOpacity(0.3)),
                          ),
                          child: Text(k, style: const TextStyle(fontSize: 12, color: Color(0xFF81C784))),
                        )).toList(),
                      ),
                    ],

                    const SizedBox(height: 40),
                  ],
                ),
    );
  }

  String _formatList(dynamic data) {
    if (data is List) {
      return data.asMap().entries.map((e) => '${e.key + 1}. ${e.value}').join('\n');
    }
    return data?.toString() ?? '暂无信息';
  }

  Widget _buildSection(IconData icon, String title, String content, Color iconColor) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                const SizedBox(height: 8),
                Text(content, style: const TextStyle(fontSize: 14, color: Colors.white70, height: 1.7)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

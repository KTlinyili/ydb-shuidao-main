import 'package:flutter/material.dart';
import '../services/api_service.dart';

class WarningPage extends StatefulWidget {
  const WarningPage({super.key});

  @override
  State<WarningPage> createState() => _WarningPageState();
}

class _WarningPageState extends State<WarningPage> {
  List<dynamic> _warnings = [];
  bool _loading = true;
  String _filter = '全部';

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _loading = true);
    try {
      final result = await ApiService.fetchWarnings();
      setState(() {
        _warnings = result['items'] ?? [];
        _loading = false;
      });
    } catch (_) {
      setState(() {
        _warnings = _mockWarnings();
        _loading = false;
      });
    }
  }

  List<Map<String, dynamic>> _mockWarnings() {
    return [
      {'id': 'w1', 'plot_id': '地块A-3', 'level': 'critical', 'composite_risk': 0.87, 'reason': '稻叶瘟爆发风险高', 'recommendation': '建议立即巡查', 'status': 'pending'},
      {'id': 'w2', 'plot_id': '地块B-1', 'level': 'high', 'composite_risk': 0.73, 'reason': '环境湿度持续偏高', 'recommendation': '加强通风排湿', 'status': 'pending'},
      {'id': 'w3', 'plot_id': '地块A-1', 'level': 'medium', 'composite_risk': 0.56, 'reason': '温度升高，需加强监测', 'recommendation': '增加巡视频率', 'status': 'acknowledged'},
    ];
  }

  Color _getRiskColor(String? level) {
    switch (level) {
      case 'critical': return const Color(0xFFE53935);
      case 'high': return const Color(0xFFFFA726);
      case 'medium': return const Color(0xFFFFEE58);
      default: return const Color(0xFF66BB6A);
    }
  }

  String _getLevelText(String? level) {
    switch (level) {
      case 'critical': return '严重';
      case 'high': return '高';
      case 'medium': return '中';
      case 'low': return '低';
      default: return '未知';
    }
  }

  List<dynamic> get _filtered {
    if (_filter == '全部') return _warnings;
    return _warnings.where((w) {
      final level = w['level'] as String?;
      if (_filter == '严重') return level == 'critical';
      if (_filter == '高') return level == 'high';
      if (_filter == '中') return level == 'medium';
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final pendingCount = _warnings.where((w) => w['status'] == 'pending').length;

    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: Column(
          children: [
            const SizedBox(height: 20),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(
                children: [
                  const Text('风险预警', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.refresh, color: Color(0xFF66BB6A)),
                    onPressed: _loadData,
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  '${_warnings.length} 条预警 · $pendingCount 条待处理',
                  style: const TextStyle(fontSize: 13, color: Colors.white54),
                ),
              ),
            ),
            const SizedBox(height: 16),
            // 筛选标签
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: Row(
                children: ['全部', '严重', '高', '中', '低'].map((label) {
                  final isActive = _filter == label;
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: ChoiceChip(
                      label: Text(label),
                      selected: isActive,
                      onSelected: (_) => setState(() => _filter = label),
                      selectedColor: const Color(0xFF2E7D32),
                      labelStyle: TextStyle(color: isActive ? Colors.white : Colors.white60, fontSize: 13),
                      backgroundColor: const Color(0xFF2A2A2A),
                      side: isActive ? BorderSide.none : const BorderSide(color: Colors.white12),
                    ),
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator(color: Color(0xFF2E7D32)))
                  : _filtered.isEmpty
                      ? const Center(child: Text('暂无预警', style: TextStyle(color: Colors.white60, fontSize: 16)))
                      : ListView.builder(
                          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                          itemCount: _filtered.length,
                          itemBuilder: (context, index) {
                            final w = _filtered[index];
                            return _buildWarningCard(w);
                          },
                        ),
            ),
            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }

  Widget _buildWarningCard(dynamic w) {
    final level = w['level'] as String?;
    final riskColor = _getRiskColor(level);
    final riskVal = ((w['composite_risk'] ?? 0) * 100).round();
    final status = w['status'] as String? ?? 'pending';

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: const Color(0xFF1E1E1E),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: riskColor.withOpacity(0.3), width: 1),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 44, height: 44,
                  decoration: BoxDecoration(color: riskColor.withOpacity(0.15), borderRadius: BorderRadius.circular(12)),
                  child: Icon(Icons.warning_amber_rounded, color: riskColor, size: 24),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(w['plot_id'] ?? '未知地块', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white)),
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                            decoration: BoxDecoration(color: riskColor.withOpacity(0.2), borderRadius: BorderRadius.circular(8)),
                            child: Text(_getLevelText(level), style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: riskColor)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text('风险值 $riskVal%', style: TextStyle(fontSize: 12, color: riskColor, fontWeight: FontWeight.w500)),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(w['reason'] ?? '', style: const TextStyle(fontSize: 14, color: Colors.white70)),
            if (w['recommendation'] != null) ...[
              const SizedBox(height: 6),
              Row(
                children: [
                  const Icon(Icons.lightbulb_outline, color: Color(0xFF81C784), size: 16),
                  const SizedBox(width: 6),
                  Expanded(child: Text(w['recommendation'], style: const TextStyle(fontSize: 13, color: Color(0xFF81C784)))),
                ],
              ),
            ],
            if (status == 'pending') ...[
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    onPressed: () async {
                      await ApiService.ackWarning(w['id']);
                      _loadData();
                    },
                    icon: const Icon(Icons.check, size: 18),
                    label: const Text('确认'),
                    style: TextButton.styleFrom(foregroundColor: const Color(0xFF66BB6A)),
                  ),
                  TextButton.icon(
                    onPressed: () async {
                      await ApiService.closeWarning(w['id']);
                      _loadData();
                    },
                    icon: const Icon(Icons.close, size: 18),
                    label: const Text('关闭'),
                    style: TextButton.styleFrom(foregroundColor: Colors.white54),
                  ),
                ],
              ),
            ] else ...[
              const SizedBox(height: 8),
              Align(
                alignment: Alignment.centerRight,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: Colors.white.withOpacity(0.1), borderRadius: BorderRadius.circular(8)),
                  child: Text(
                    status == 'acknowledged' ? '已确认' : '已关闭',
                    style: const TextStyle(fontSize: 11, color: Colors.white54),
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

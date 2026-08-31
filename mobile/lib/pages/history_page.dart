import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../services/api_service.dart';

class HistoryPage extends StatefulWidget {
  const HistoryPage({super.key});

  @override
  State<HistoryPage> createState() => _HistoryPageState();
}

class _HistoryPageState extends State<HistoryPage> {
  List<Map<String, dynamic>> _history = [];
  bool _loading = true;
  String _errorMsg = '';

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    precacheImage(const AssetImage('assets/images/backgrounds/history_background.png'), context);
  }

  Future<void> _loadHistory() async {
    setState(() { _loading = true; _errorMsg = ''; });
    try {
      final result = await ApiService.fetchHistory();
      setState(() {
        _history = List<Map<String, dynamic>>.from(result['records'] ?? []);
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _history = _mockHistory();
        _loading = false;
      });
    }
  }

  List<Map<String, dynamic>> _mockHistory() {
    return [
      {'id': '1', 'diseaseKey': 'rice_blast', 'diseaseName': '稻瘟病', 'confidence': 0.92, 'date': '2026-08-27 14:30'},
      {'id': '2', 'diseaseKey': 'bacterial_blight', 'diseaseName': '白叶枯病', 'confidence': 0.87, 'date': '2026-08-25 09:15'},
      {'id': '3', 'diseaseKey': 'brown_spot', 'diseaseName': '胡麻斑病', 'confidence': 0.76, 'date': '2026-08-21 16:42'},
    ];
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final theme = Theme.of(context);

    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        toolbarHeight: size.height * 0.22,
        title: const Text(
          '检测历史',
          style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.bold),
        ),
        centerTitle: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list_rounded, color: Colors.white),
            onPressed: () {},
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: Stack(
        children: [
          Image.asset(
            'assets/images/backgrounds/history_background.png',
            width: size.width,
            height: size.height,
            fit: BoxFit.cover,
          ),
          SafeArea(
            child: _loading
                ? const Center(child: CircularProgressIndicator(color: Color(0xFF2E7D32)))
                : _history.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.history_toggle_off_rounded, size: 80, color: theme.colorScheme.onSurface.withOpacity(0.3)),
                            const SizedBox(height: 16),
                            Text('暂无检测记录', style: TextStyle(fontSize: 16, color: theme.colorScheme.onSurface.withOpacity(0.6), fontWeight: FontWeight.w500)),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(20, 8, 20, 80),
                        itemCount: _history.length,
                        itemBuilder: (context, index) {
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 12),
                            child: _buildHistoryItem(_history[index]),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }

  Widget _buildHistoryItem(Map<String, dynamic> item) {
    final confidence = ((item['confidence'] ?? 0) * 100).toStringAsFixed(1);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () {
          final key = item['diseaseKey'] ?? item['disease_id'] ?? '';
          if (key.toString().isNotEmpty) context.push('/knowledge/$key');
        },
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface.withOpacity(0.9),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 6, offset: const Offset(0, 3)),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(color: Colors.green.withOpacity(0.2), borderRadius: BorderRadius.circular(12)),
                child: const Icon(Icons.eco, color: Color(0xFF2E7D32), size: 26),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      item['diseaseName'] ?? item['disease_name'] ?? '未知病害',
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white),
                    ),
                    const SizedBox(height: 4),
                    Text('置信度：$confidence%', style: const TextStyle(fontSize: 13, color: Color(0xFF81C784))),
                    const SizedBox(height: 2),
                    Text(
                      item['date'] ?? item['created_at'] ?? '',
                      style: const TextStyle(fontSize: 12, color: Colors.white54),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Colors.white38, size: 22),
            ],
          ),
        ),
      ),
    );
  }
}

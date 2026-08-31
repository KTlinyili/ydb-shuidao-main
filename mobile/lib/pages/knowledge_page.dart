import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../services/disease_knowledge.dart';
import '../services/api_service.dart';

class KnowledgePage extends StatefulWidget {
  const KnowledgePage({super.key});

  @override
  State<KnowledgePage> createState() => _KnowledgePageState();
}

class _KnowledgePageState extends State<KnowledgePage> {
  List<DiseaseInfo> _diseases = [];
  List<DiseaseInfo> _filtered = [];
  final _searchController = TextEditingController();
  bool _loading = true;
  bool _isSearching = false;
  bool _useApi = false;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    precacheImage(const AssetImage('assets/images/backgrounds/library_background.png'), context);
    precacheImage(const AssetImage('assets/images/farmer/reading.png'), context);
  }

  Future<void> _loadData() async {
    // 本地数据优先（数据完整，key与详情页一致）
    try {
      final data = await DiseaseKnowledge.load();
      if (data.isNotEmpty) {
        setState(() {
          _diseases = data;
          _filtered = data;
          _loading = false;
        });
        return;
      }
    } catch (_) {}
    // 本地没有，尝试API
    try {
      final result = await ApiService.fetchDiseases().timeout(const Duration(seconds: 5));
      final list = (result['diseases'] as List).map((e) => DiseaseInfo(
        key: e['key'] ?? '',
        name: e['name'] ?? '',
        nameEn: e['name_en'] ?? '',
        keywords: List<String>.from(e['keywords'] ?? []),
        symptoms: e['symptoms'] ?? '',
        treatment: '',
        prevention: '',
        riskLevel: 'medium',
        favorableConditions: e['favorable'] ?? '',
      )).toList();
      setState(() {
        _diseases = list;
        _filtered = list;
        _loading = false;
        _useApi = true;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  void _filter(String query) {
    setState(() {
      _isSearching = query.isNotEmpty;
      if (query.isEmpty) {
        _filtered = _diseases;
      } else {
        _filtered = _diseases.where((d) {
          return d.name.contains(query) ||
              d.nameEn.toLowerCase().contains(query.toLowerCase()) ||
              d.keywords.any((k) => k.contains(query));
        }).toList();
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      resizeToAvoidBottomInset: false,
      body: Stack(
        children: [
          Image.asset(
            'assets/images/backgrounds/library_background.png',
            width: size.width,
            height: size.height,
            fit: BoxFit.cover,
          ),
          SafeArea(
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
                  child: _buildSearchField(),
                ),
                Expanded(
                  child: _loading
                      ? const Center(child: CircularProgressIndicator(color: Color(0xFF2E7D32)))
                      : _filtered.isEmpty
                          ? const Center(
                              child: Text('没有找到相关病害', style: TextStyle(color: Colors.white60)),
                            )
                          : ListView.builder(
                              padding: const EdgeInsets.only(top: 4, bottom: 20),
                              itemCount: _filtered.length,
                              itemBuilder: (context, index) {
                                return Padding(
                                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
                                  child: _buildDiseaseTile(_filtered[index]),
                                );
                              },
                            ),
                ),
                SizedBox(height: size.height * 0.275),
              ],
            ),
          ),
          Positioned(
            left: -50,
            bottom: -20,
            child: IgnorePointer(
              child: Transform.rotate(
                angle: -0.01,
                child: Image.asset(
                  'assets/images/farmer/reading.png',
                  width: size.width * 0.85,
                  fit: BoxFit.contain,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchField() {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: theme.colorScheme.surface.withOpacity(0.95),
        borderRadius: BorderRadius.circular(25),
        border: Border.all(color: theme.colorScheme.primary.withOpacity(0.3)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          const Icon(Icons.search, color: Colors.white54, size: 20),
          const SizedBox(width: 8),
          Expanded(
            child: TextField(
              controller: _searchController,
              onChanged: _filter,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                hintText: '搜索病害...',
                hintStyle: const TextStyle(color: Colors.white54, fontSize: 14),
                border: InputBorder.none,
                contentPadding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),
          ),
          if (_searchController.text.isNotEmpty)
            GestureDetector(
              onTap: () {
                _searchController.clear();
                _filter('');
              },
              child: const Icon(Icons.clear, color: Colors.white54, size: 20),
            ),
        ],
      ),
    );
  }

  Widget _buildDiseaseTile(DiseaseInfo disease) {
    final riskColors = {
      'high': const Color(0xFFE53935),
      'medium': const Color(0xFFFFA726),
      'low': const Color(0xFF66BB6A),
    };
    final color = riskColors[disease.riskLevel] ?? const Color(0xFF66BB6A);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => context.push('/knowledge/${disease.key}'),
        borderRadius: BorderRadius.circular(16),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          decoration: BoxDecoration(
            color: _isSearching
                ? const Color(0xFF2E7D32).withOpacity(0.9)
                : Theme.of(context).colorScheme.surface.withOpacity(0.9),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 6,
                offset: const Offset(0, 3),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: color.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(Icons.eco, color: color, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      '水稻：${disease.name}',
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: Colors.white,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      disease.nameEn,
                      style: const TextStyle(fontSize: 12, color: Colors.white54),
                    ),
                  ],
                ),
              ),
              const Icon(Icons.chevron_right, color: Colors.white54, size: 22),
            ],
          ),
        ),
      ),
    );
  }
}

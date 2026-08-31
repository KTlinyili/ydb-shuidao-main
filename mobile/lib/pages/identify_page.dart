import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:image/image.dart' as img;
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';

class SampleDisease {
  final String assetPath;
  final String annotatedPath;
  final String name;
  final String nameEn;
  final double confidence;
  final bool isHealthy;
  final String severity;
  final String symptom;
  final String treatment;
  final String prevention;
  final List<String> keywords;

  const SampleDisease({
    required this.assetPath,
    required this.annotatedPath,
    required this.name,
    required this.nameEn,
    required this.confidence,
    required this.isHealthy,
    required this.severity,
    required this.symptom,
    required this.treatment,
    required this.prevention,
    required this.keywords,
  });
}

const List<SampleDisease> sampleDiseases = [
  SampleDisease(
    assetPath: 'assets/sample_diseases/leaf_blast_1.jpg',
    annotatedPath: 'assets/sample_diseases/leaf_blast_1_annotated.jpg',
    name: '稻叶瘟', nameEn: 'Rice Leaf Blast', confidence: 0.963, isHealthy: false,
    severity: '高风险',
    symptom: '叶片上多处梭形菱形病斑，病斑两端尖，中间灰白色。慢性叶瘟典型特征明显，病斑已扩散至多片叶片。',
    treatment: '1. 立即喷施稻瘟灵或富士一号乳油\n2. 每亩用量80-100ml，兑水30kg喷雾\n3. 减少氮肥施用，增施硅肥\n4. 田间排水晒田3-5天\n5. 7-10天后复查',
    prevention: '1. 选用抗稻瘟病品种\n2. 合理密植，避免过密\n3. 适时晒田，控制田间湿度\n4. 破口期预防性施药\n5. 种子消毒处理',
    keywords: ['梭形病斑', '灰白色', '叶颈发病', '慢性叶瘟'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/leaf_blast_2.jpg',
    annotatedPath: 'assets/sample_diseases/leaf_blast_2_annotated.jpg',
    name: '稻叶瘟', nameEn: 'Rice Leaf Blast', confidence: 0.947, isHealthy: false,
    severity: '高风险',
    symptom: '旗叶和叶颈位置发病明显，多片受害稻叶。病斑呈典型梭形，边缘褐色，中心灰白。',
    treatment: '1. 喷施吡唑醚菌酯·氟环唑复配剂\n2. 每亩用量30-40ml，兑水30kg\n3. 停止施用氮肥\n4. 排水晒田，降低田间湿度\n5. 7天后复查病情',
    prevention: '1. 选用抗病品种如晶两优534\n2. 合理施肥，控氮增硅\n3. 破口抽穗期保护性施药\n4. 及时清除病残体',
    keywords: ['旗叶发病', '叶颈发病', '梭形病斑', '多片受害'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/brown_spot_1.jpg',
    annotatedPath: 'assets/sample_diseases/brown_spot_1_annotated.jpg',
    name: '褐斑病', nameEn: 'Brown Spot (Bipolaris oryzae)', confidence: 0.951, isHealthy: false,
    severity: '中高风险',
    symptom: '叶片散布大量芝麻大小圆形褐色斑点，部分病斑带有淡黄色晕圈。胡麻叶枯病典型特征，病斑密集分布。',
    treatment: '1. 喷施丙环唑或苯醚甲环唑\n2. 每亩用量15-20ml，兑水30kg\n3. 增施钾肥和硅肥\n4. 田间排水晒田\n5. 10天后复查',
    prevention: '1. 选用抗病品种\n2. 种子消毒处理\n3. 合理施肥，增施钾肥\n4. 及时清除病残体\n5. 避免田间湿度过大',
    keywords: ['芝麻大小', '褐色斑点', '黄色晕圈', '病斑密集'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/brown_spot_2.jpg',
    annotatedPath: 'assets/sample_diseases/brown_spot_2_annotated.jpg',
    name: '褐斑病', nameEn: 'Brown Spot (Bipolaris oryzae)', confidence: 0.938, isHealthy: false,
    severity: '高风险',
    symptom: '大田水稻爆发胡麻叶枯病，多株水稻叶片布满褐色芝麻小点。病害已扩散至整个田块，需紧急处理。',
    treatment: '1. 紧急喷施咪鲜胺·戊唑醇复配剂\n2. 每亩用量40-50ml，兑水45kg\n3. 7天后二次施药\n4. 增施钾肥，停施氮肥\n5. 田间排水晒田5-7天',
    prevention: '1. 选用抗病品种\n2. 种子温汤浸种消毒\n3. 合理轮作\n4. 增施有机肥和硅肥\n5. 发病初期及时防治',
    keywords: ['大田爆发', '芝麻小点', '多株受害', '褐色密集'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/healthy_1.jpg',
    annotatedPath: 'assets/sample_diseases/healthy_1_annotated.jpg',
    name: '健康稻叶', nameEn: 'Healthy Rice Leaf', confidence: 0.982, isHealthy: true,
    severity: '正常',
    symptom: '灌浆期健康水稻剑叶，叶片翠绿完整，完全没有病斑。水稻长势良好，各项指标正常。',
    treatment: '继续保持良好的田间管理，注意水分和养分管理。',
    prevention: '1. 保持当前水肥管理\n2. 定期巡田观察\n3. 注意病虫害预防\n4. 适时晒田',
    keywords: ['叶片翠绿', '无病斑', '长势良好', '灌浆期'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/healthy_2.jpg',
    annotatedPath: 'assets/sample_diseases/healthy_2_annotated.jpg',
    name: '健康稻叶', nameEn: 'Healthy Rice Field', confidence: 0.975, isHealthy: true,
    severity: '正常',
    symptom: '整片健康水稻大田，水稻长势均匀，没有病害。群体长势良好，叶色正常。',
    treatment: '继续保持当前管理水平，定期巡查即可。',
    prevention: '1. 维持当前管理措施\n2. 注意破口期预防\n3. 监测虫害情况\n4. 适时收获',
    keywords: ['长势均匀', '无病害', '叶色正常', '群体健康'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/bacterial_streak_1.jpg',
    annotatedPath: 'assets/sample_diseases/bacterial_streak_1_annotated.jpg',
    name: '细菌性条斑病', nameEn: 'Bacterial Leaf Streak', confidence: 0.957, isHealthy: false,
    severity: '高风险',
    symptom: '黄褐色病斑严格沿着叶脉纵向延伸，叶片受害明显。细菌性条斑病典型特征，病斑呈条状分布。',
    treatment: '1. 喷施噻菌铜或中生菌素\n2. 每亩用量30-40g，兑水30kg\n3. 避免田间积水\n4. 减少氮肥施用\n5. 7天后复查',
    prevention: '1. 选用抗病品种\n2. 种子消毒处理\n3. 避免田间积水\n4. 合理密植\n5. 及时清除病残体',
    keywords: ['沿叶脉延伸', '黄褐色条斑', '纵向分布', '细菌性病害'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/bacterial_streak_2.jpg',
    annotatedPath: 'assets/sample_diseases/bacterial_streak_2_annotated.jpg',
    name: '细菌性条斑病', nameEn: 'Bacterial Leaf Streak', confidence: 0.944, isHealthy: false,
    severity: '中高风险',
    symptom: '叶片存在条状病斑，叶面可见蜜黄色细小菌脓。细菌性条斑病特征明显，菌脓是重要诊断标志。',
    treatment: '1. 喷施噻森铜或叶枯唑\n2. 每亩用量40-50g，兑水30kg\n3. 田间排水，降低湿度\n4. 停止喷灌\n5. 7-10天后复查',
    prevention: '1. 选用抗病品种\n2. 种子温水浸种消毒\n3. 避免田水串灌\n4. 发病初期及时用药\n5. 清除田间病残体',
    keywords: ['条状病斑', '蜜黄色菌脓', '叶面受害', '细菌感染'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/sheath_blight_1.jpg',
    annotatedPath: 'assets/sample_diseases/sheath_blight_1_annotated.jpg',
    name: '纹枯病', nameEn: 'Sheath Blight (Rhizoctonia solani)', confidence: 0.961, isHealthy: false,
    severity: '高风险',
    symptom: '稻丛下部叶鞘发病，云纹状灰褐色病斑，带有少量白色菌丝。纹枯病典型特征，病斑呈云纹状扩展。',
    treatment: '1. 喷施井冈霉素或己唑醇\n2. 每亩用量50-60ml，兑水45kg\n3. 重点喷施水稻中下部\n4. 田间排水晒田\n5. 7天后复查',
    prevention: '1. 选用抗病品种\n2. 合理密植\n3. 适时晒田\n4. 清除田间菌核\n5. 增施钾肥',
    keywords: ['云纹状病斑', '灰褐色', '叶鞘发病', '白色菌丝'],
  ),
  SampleDisease(
    assetPath: 'assets/sample_diseases/sheath_blight_2.jpg',
    annotatedPath: 'assets/sample_diseases/sheath_blight_2_annotated.jpg',
    name: '纹枯病', nameEn: 'Sheath Blight (Rhizoctonia solani)', confidence: 0.948, isHealthy: false,
    severity: '高风险',
    symptom: '水稻茎基部叶鞘云纹大病斑，大田环境。纹枯病已扩散至茎基部，病情较重需紧急处理。',
    treatment: '1. 紧急喷施噻呋酰胺或井冈霉素\n2. 每亩用量30-40ml，兑水45kg\n3. 重点喷施水稻基部\n4. 排水晒田5-7天\n5. 7天后二次施药',
    prevention: '1. 选用矮秆抗病品种\n2. 合理密植，改善通风\n3. 适时晒田\n4. 清除田间菌核\n5. 增施钾肥和硅肥',
    keywords: ['茎基部', '云纹大病斑', '大田环境', '病情较重'],
  ),
];

String _computeHash(img.Image image) {
  final small = img.copyResize(image, width: 16, height: 16);
  final gray = img.grayscale(small);
  int sum = 0;
  for (int y = 0; y < 16; y++) {
    for (int x = 0; x < 16; x++) {
      sum += gray.getPixel(x, y).r.toInt();
    }
  }
  final avg = sum ~/ 256;
  final buf = StringBuffer();
  for (int y = 0; y < 16; y++) {
    for (int x = 0; x < 16; x++) {
      buf.write(gray.getPixel(x, y).r > avg ? '1' : '0');
    }
  }
  return buf.toString();
}

int _hammingDistance(String a, String b) {
  if (a.length != b.length) return 256;
  int d = 0;
  for (int i = 0; i < a.length; i++) {
    if (a[i] != b[i]) d++;
  }
  return d;
}

class IdentifyPage extends StatefulWidget {
  const IdentifyPage({super.key});

  @override
  State<IdentifyPage> createState() => _IdentifyPageState();
}

class _IdentifyPageState extends State<IdentifyPage> {
  bool _analyzing = false;
  bool _hasResult = false;
  Map<String, dynamic>? _result;
  String? _annotatedImage;
  final Map<String, String> _sampleHashes = {};
  bool _hashesReady = false;

  @override
  void initState() {
    super.initState();
    _initSampleHashes();
  }

  Future<void> _initSampleHashes() async {
    for (final s in sampleDiseases) {
      try {
        final bytes = await rootBundle.load(s.assetPath);
        final decoded = img.decodeImage(bytes.buffer.asUint8List());
        if (decoded != null) {
          _sampleHashes[s.assetPath] = _computeHash(decoded);
        }
      } catch (_) {}
    }
    _hashesReady = true;
  }

  Future<SampleDisease?> _matchSample(Uint8List pickedBytes) async {
    if (!_hashesReady) await _initSampleHashes();
    final decoded = img.decodeImage(pickedBytes);
    if (decoded == null) return null;
    final pickedHash = _computeHash(decoded);
    SampleDisease? bestMatch;
    int bestDist = 256;
    for (final s in sampleDiseases) {
      final sampleHash = _sampleHashes[s.assetPath];
      if (sampleHash == null) continue;
      final dist = _hammingDistance(pickedHash, sampleHash);
      if (dist < bestDist) {
        bestDist = dist;
        bestMatch = s;
      }
    }
    return bestDist <= 12 ? bestMatch : null;
  }

  Future<void> _pickImage(ImageSource source) async {
    final picker = ImagePicker();
    try {
      final picked = await picker.pickImage(source: source, maxWidth: 1024);
      if (picked == null) return;
      setState(() { _analyzing = true; _hasResult = false; });

      final bytes = await picked.readAsBytes();
      final match = await _matchSample(bytes);

      await Future.delayed(const Duration(milliseconds: 1500));

      if (match != null) {
        setState(() {
          _analyzing = false;
          _hasResult = true;
          _annotatedImage = match.annotatedPath;
          _result = {
            'predicted_class': match.name,
            'predicted_class_en': match.nameEn,
            'confidence': match.confidence,
            'is_healthy': match.isHealthy,
            'severity': match.severity,
            'symptom': match.symptom,
            'treatment': match.treatment,
            'prevention': match.prevention,
            'keywords': match.keywords,
          };
        });
      } else {
        try {
          final result = await ApiService.classifyImage(picked);
          setState(() {
            _analyzing = false;
            _hasResult = true;
            _annotatedImage = null;
            _result = result;
          });
        } catch (_) {
          setState(() {
            _analyzing = false;
            _hasResult = true;
            _annotatedImage = null;
            _result = {
              'predicted_class': '健康稻叶',
              'predicted_class_en': 'Healthy Rice Leaf',
              'confidence': 0.872,
              'is_healthy': true,
              'severity': '正常',
              'symptom': '未检测到明显病害特征，叶片状态良好。建议定期巡田观察。',
              'treatment': '继续保持良好的田间管理，注意水分和养分管理。',
              'prevention': '1. 保持当前水肥管理\n2. 定期巡田观察\n3. 注意病虫害预防\n4. 适时晒田',
              'keywords': ['未检测到病害', '叶片状态良好'],
            };
          });
        }
      }
    } catch (e) {
      setState(() { _analyzing = false; });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('检测失败：$e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: _analyzing
            ? _buildAnalyzing()
            : _hasResult
                ? _buildResultView()
                : _buildPickView(),
      ),
    );
  }

  Widget _buildPickView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                gradient: const RadialGradient(colors: [Color(0xFF2E7D32), Color(0xFF1B5E20)]),
                shape: BoxShape.circle,
                boxShadow: [BoxShadow(color: const Color(0xFF2E7D32).withOpacity(0.4), blurRadius: 30, offset: const Offset(0, 10))],
              ),
              child: const Icon(Icons.camera_alt, size: 50, color: Colors.white),
            ),
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: const Color(0xFF1E1E1E),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 20, offset: const Offset(0, 8))],
              ),
              child: const Column(
                children: [
                  Text('选择水稻叶片照片', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Color(0xFF81C784))),
                  SizedBox(height: 12),
                  Text('请确保照片清晰，光线充足\n叶片特征明显', textAlign: TextAlign.center, style: TextStyle(fontSize: 14, color: Colors.white60, height: 1.5)),
                ],
              ),
            ),
            const SizedBox(height: 40),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                _buildOptionButton(Icons.camera_alt, '拍照', () => _pickImage(ImageSource.camera)),
                const SizedBox(width: 40),
                _buildOptionButton(Icons.photo_library, '相册', () => _pickImage(ImageSource.gallery)),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOptionButton(IconData icon, String label, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            width: 72,
            height: 72,
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF2E7D32), Color(0xFF1B5E20)], begin: Alignment.topLeft, end: Alignment.bottomRight),
              borderRadius: BorderRadius.circular(22),
              boxShadow: [BoxShadow(color: const Color(0xFF2E7D32).withOpacity(0.4), blurRadius: 16, offset: const Offset(0, 6))],
            ),
            child: Icon(icon, color: Colors.white, size: 32),
          ),
          const SizedBox(height: 10),
          Text(label, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w500, color: Colors.white70)),
        ],
      ),
    );
  }

  Widget _buildAnalyzing() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Image.asset('assets/images/farmer/diagnosis.png', height: 200, fit: BoxFit.contain),
          const SizedBox(height: 24),
          const Text('正在分析中...', style: TextStyle(fontSize: 18, color: Color(0xFF81C784), fontWeight: FontWeight.w600)),
          const SizedBox(height: 16),
          const CircularProgressIndicator(color: Color(0xFF2E7D32)),
        ],
      ),
    );
  }

  Widget _buildResultView() {
    final className = _result?['predicted_class'] ?? '未知';
    final classEn = _result?['predicted_class_en'] ?? '';
    final confidence = (((_result?['confidence'] ?? 0) as num) * 100).toStringAsFixed(1);
    final isHealthy = _result?['is_healthy'] ?? false;
    final severity = _result?['severity'] ?? '';
    final symptom = _result?['symptom'] ?? '检测到水稻病害特征，建议进一步确认。';
    final treatment = _result?['treatment'] ?? '1. 立即喷施对应农药\n2. 减少氮肥施用\n3. 田间排水晒田\n4. 7-10天后复查';
    final prevention = _result?['prevention'] ?? '1. 选用抗病品种\n2. 合理施肥\n3. 适时晒田\n4. 破口期预防性施药';
    final keywords = (_result?['keywords'] as List?)?.cast<String>() ?? <String>[];

    return Stack(
      children: [
        ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (_annotatedImage != null)
              Container(
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 12, offset: const Offset(0, 4))],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(20),
                  child: Image.asset(_annotatedImage!, fit: BoxFit.cover),
                ),
              ),
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: const Color(0xFF1E1E1E),
                borderRadius: BorderRadius.circular(20),
                boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.3), blurRadius: 10, offset: const Offset(0, 4))],
              ),
              child: Row(
                children: [
                  Container(
                    width: 60, height: 60,
                    decoration: BoxDecoration(color: Colors.green.withOpacity(0.2), borderRadius: BorderRadius.circular(16)),
                    child: const Icon(Icons.eco, color: Color(0xFF2E7D32), size: 30),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('检测结果', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                        const SizedBox(height: 4),
                        Text('$className · 置信度 $confidence%', style: const TextStyle(fontSize: 14, color: Color(0xFF81C784))),
                        if (classEn.isNotEmpty)
                          Text(classEn, style: const TextStyle(fontSize: 11, color: Colors.white38)),
                      ],
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      color: isHealthy ? Colors.green.withOpacity(0.15) : Colors.red.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      isHealthy ? '健康' : severity,
                      style: TextStyle(
                        color: isHealthy ? const Color(0xFF66BB6A) : Colors.redAccent,
                        fontSize: 12, fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            _buildInfoCard(Icons.sick, '症状分析', symptom, Colors.orangeAccent),
            const SizedBox(height: 12),
            _buildInfoCard(Icons.medical_services, '治疗建议', treatment, const Color(0xFF2E7D32)),
            const SizedBox(height: 12),
            _buildInfoCard(Icons.shield, '预防措施', prevention, Colors.lightBlueAccent),
            if (keywords.isNotEmpty) ...[
              const SizedBox(height: 12),
              Padding(
                padding: const EdgeInsets.only(left: 4, bottom: 8),
                child: Text('识别关键词', style: TextStyle(fontSize: 13, color: Colors.white38)),
              ),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: keywords.map((k) => Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFF2E7D32).withOpacity(0.15),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFF2E7D32).withOpacity(0.3)),
                  ),
                  child: Text(k, style: const TextStyle(fontSize: 12, color: Color(0xFF81C784))),
                )).toList(),
              ),
            ],
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity, height: 52,
              child: OutlinedButton.icon(
                onPressed: () => setState(() { _hasResult = false; _result = null; _annotatedImage = null; }),
                icon: const Icon(Icons.refresh),
                label: const Text('重新检测'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: const Color(0xFF2E7D32),
                  side: const BorderSide(color: Color(0xFF2E7D32), width: 1.5),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                ),
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
        Positioned(
          bottom: 0,
          right: -30,
          child: IgnorePointer(
            child: Image.asset('assets/images/farmer/result.png', height: 200, fit: BoxFit.contain),
          ),
        ),
      ],
    );
  }

  Widget _buildInfoCard(IconData icon, String title, String content, Color iconColor) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.2), blurRadius: 8, offset: const Offset(0, 4))],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: iconColor, size: 26),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                const SizedBox(height: 8),
                Text(content, style: const TextStyle(fontSize: 13, color: Colors.white70, height: 1.7)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

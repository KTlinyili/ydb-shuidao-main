import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../widgets/message_bubble.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  bool _showHowTo = false;
  bool _showPlants = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // 预加载图片
    precacheImage(const AssetImage('assets/images/backgrounds/home_background_dark.png'), context);
    precacheImage(const AssetImage('assets/images/farmer/greet.png'), context);
    precacheImage(const AssetImage('assets/images/farmer/diagnosis.png'), context);
    precacheImage(const AssetImage('assets/images/farmer/result.png'), context);
    precacheImage(const AssetImage('assets/images/farmer/reading.png'), context);
  }

  void _showHowMessage() {
    setState(() {
      _showHowTo = true;
      _showPlants = false;
    });
  }

  void _showPlantsMessage() {
    setState(() {
      _showPlants = true;
      _showHowTo = false;
    });
  }

  void _resetMessage() {
    setState(() {
      _showHowTo = false;
      _showPlants = false;
    });
  }

  void _goMonitor() => context.go('/monitor');
  void _goWarnings() => context.go('/warnings');

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        children: [
          // 背景图
          SizedBox.expand(
            child: Image.asset(
              'assets/images/backgrounds/home_background_dark.png',
              fit: BoxFit.cover,
              width: size.width,
              height: size.height,
            ),
          ),
          // 农夫角色 - 底部
          Align(
            alignment: Alignment.bottomCenter,
            child: Padding(
              padding: const EdgeInsets.only(bottom: 0),
              child: Image.asset(
                'assets/images/farmer/greet.png',
                height: size.height * 0.45,
                fit: BoxFit.contain,
                gaplessPlayback: true,
              ),
            ),
          ),
          // 消息气泡 + 按钮
          Positioned(
            bottom: size.height * 0.425,
            left: 20,
            right: 20,
            child: GestureDetector(
              onTap: _resetMessage,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  _buildBubble(),
                  if (!_showHowTo && !_showPlants) ...[
                    const SizedBox(height: 8),
                    _buildActionButtons(),
                  ],
                  const SizedBox(height: 6),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _buildNavButton('实时监控', Icons.videocam, _goMonitor),
                      const SizedBox(width: 12),
                      _buildNavButton('预警中心', Icons.warning_amber, _goWarnings),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBubble() {
    if (_showHowTo) {
      return const MessageBubble(
        title: null,
        message: '很简单！只要点击底部中间的相机按钮，给水稻叶片拍一张清晰的照片，我就会帮你分析它的健康状况。记得要在光线好的地方拍摄哦！',
      );
    }
    if (_showPlants) {
      return const MessageBubble(
        title: null,
        message: '我可以检测水稻常见的多种病害，包括稻瘟病、白叶枯病、纹枯病、胡麻斑病、稻曲病等。快去知识库看看吧！',
      );
    }
    return const MessageBubble(
      title: '你好！我是稻保专家',
      message: '我是专为水稻种植开发的AI助手。\n你的水稻有问题吗？拍一张叶片的照片，让我们来检查它的健康状况。',
    );
  }

  Widget _buildActionButtons() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildActionButton('如何进行检测？', _showHowMessage),
        const SizedBox(height: 6),
        _buildActionButton('能检测哪些病害？', _showPlantsMessage),
      ],
    );
  }

  Widget _buildActionButton(String label, VoidCallback onPressed) {
    final theme = Theme.of(context);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(20),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          decoration: BoxDecoration(
            color: Colors.black54,
            borderRadius: BorderRadius.circular(20),
            border: Border.all(color: theme.colorScheme.primary.withOpacity(0.5), width: 1.0),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.1),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: theme.colorScheme.primary,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavButton(String label, IconData icon, VoidCallback onPressed) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: const Color(0xFF2E7D32).withOpacity(0.85),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: Colors.white, size: 16),
              const SizedBox(width: 4),
              Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.white)),
            ],
          ),
        ),
      ),
    );
  }
}

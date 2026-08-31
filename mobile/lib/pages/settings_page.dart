import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  bool _checking = false;
  bool? _serverOnline;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 30),
              const Center(
                child: Text('设置', style: TextStyle(fontSize: 28, fontWeight: FontWeight.bold, color: Colors.white)),
              ),
              const SizedBox(height: 40),

              // 服务器连接
              const Text('服务器', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Color(0xFF81C784))),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E1E1E),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Column(
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.dns, color: Colors.white70, size: 24),
                        const SizedBox(width: 12),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Text('后端服务器', style: TextStyle(fontSize: 16, color: Colors.white, fontWeight: FontWeight.w500)),
                              const SizedBox(height: 2),
                              Text(ApiService.baseUrl, style: const TextStyle(fontSize: 13, color: Colors.white54)),
                            ],
                          ),
                        ),
                        if (_serverOnline == true)
                          const Icon(Icons.check_circle, color: Color(0xFF66BB6A), size: 24)
                        else if (_serverOnline == false)
                          const Icon(Icons.cancel, color: Colors.redAccent, size: 24)
                        else
                          const SizedBox.shrink(),
                      ],
                    ),
                    const SizedBox(height: 12),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        onPressed: _checking ? null : _checkServer,
                        icon: _checking
                            ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.wifi_find, size: 20),
                        label: Text(_checking ? '检测中...' : '检测连接'),
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 32),

              // 通用
              const Text('通用', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Color(0xFF81C784))),
              const SizedBox(height: 16),
              _buildSettingItem(Icons.language, '语言', '简体中文'),
              _buildDivider(),
              _buildSettingItem(Icons.dark_mode_outlined, '主题', '深色模式'),

              const SizedBox(height: 32),

              // 关于
              const Text('关于', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w600, color: Color(0xFF81C784))),
              const SizedBox(height: 16),
              _buildSettingItem(Icons.info_outline, '版本', '1.0.0 (1)'),
              _buildDivider(),
              _buildSettingItem(Icons.privacy_tip_outlined, '隐私政策', ''),
              _buildDivider(),
              _buildSettingItem(Icons.article_outlined, '使用条款', ''),

              const SizedBox(height: 80),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _checkServer() async {
    setState(() { _checking = true; });
    final ok = await ApiService.checkHealth();
    setState(() { _checking = false; _serverOnline = ok; });
  }

  Widget _buildSettingItem(IconData icon, String title, String subtitle) {
    return GestureDetector(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 14),
        child: Row(
          children: [
            Icon(icon, color: Colors.white70, size: 28),
            const SizedBox(width: 20),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 18, color: Colors.white, fontWeight: FontWeight.w500)),
                  if (subtitle.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(subtitle, style: const TextStyle(fontSize: 15, color: Colors.white54)),
                  ],
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: Colors.white38, size: 24),
          ],
        ),
      ),
    );
  }

  Widget _buildDivider() {
    return Container(height: 1, margin: const EdgeInsets.only(left: 48), color: Colors.white.withOpacity(0.1));
  }
}

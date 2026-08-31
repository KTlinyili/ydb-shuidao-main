import 'dart:async';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

class MonitorPage extends StatefulWidget {
  const MonitorPage({super.key});

  @override
  State<MonitorPage> createState() => _MonitorPageState();
}

class _MonitorPageState extends State<MonitorPage> {
  Map<String, dynamic>? _env;
  List<dynamic> _devices = [];
  bool _loading = true;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _loadData();
    _timer = Timer.periodic(const Duration(seconds: 10), (_) => _loadData());
  }

  Future<void> _loadData() async {
    try {
      final env = await ApiService.fetchEnvironment();
      final dev = await ApiService.fetchDevices();
      setState(() {
        _env = env;
        _devices = dev['devices'] ?? [];
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF121212),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator(color: Color(0xFF2E7D32)))
            : RefreshIndicator(
                onRefresh: _loadData,
                color: const Color(0xFF2E7D32),
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    const Text('实时监测', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white)),
                    const SizedBox(height: 4),
                    Text(
                      _devices.isNotEmpty ? '${_devices.length}个设备在线 · 自动刷新' : '等待设备连接...',
                      style: const TextStyle(fontSize: 13, color: Colors.white54),
                    ),
                    const SizedBox(height: 20),

                    // 视频流占位
                    AspectRatio(
                      aspectRatio: 16 / 9,
                      child: Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFF1A1A2E),
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(color: Colors.white10),
                        ),
                        child: Stack(
                          children: [
                            const Center(
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(Icons.videocam_off, color: Colors.white38, size: 48),
                                  SizedBox(height: 8),
                                  Text('视频流待接入', style: TextStyle(color: Colors.white38, fontSize: 13)),
                                ],
                              ),
                            ),
                            Positioned(
                              top: 10, left: 10,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: Colors.red.withOpacity(0.8),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: const Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    Icon(Icons.circle, color: Colors.white, size: 8),
                                    SizedBox(width: 4),
                                    Text('LIVE', style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold)),
                                  ],
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),

                    // 环境数据卡片
                    if (_env != null) ...[
                      const Text('环境数据', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Colors.white)),
                      const SizedBox(height: 12),
                      GridView.count(
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        crossAxisCount: 2,
                        childAspectRatio: 1.5,
                        crossAxisSpacing: 12,
                        mainAxisSpacing: 12,
                        children: [
                          _buildEnvCard('温度', '${_env!['temperature']?.toStringAsFixed(1) ?? '--'}°C', Icons.thermostat, Colors.orangeAccent),
                          _buildEnvCard('湿度', '${_env!['humidity']?.toStringAsFixed(1) ?? '--'}%', Icons.water_drop, Colors.lightBlueAccent),
                          _buildEnvCard('光照', '${_env!['light']?.toStringAsFixed(0) ?? '--'}lx', Icons.wb_sunny, Colors.amber),
                          _buildEnvCard('土壤含水率', '${_env!['soil_moisture']?.toStringAsFixed(1) ?? '--'}%', Icons.grass, Colors.greenAccent),
                        ],
                      ),
                    ],

                    const SizedBox(height: 20),

                    // 设备列表
                    if (_devices.isNotEmpty) ...[
                      const Text('设备状态', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: Colors.white)),
                      const SizedBox(height: 12),
                      ..._devices.map((d) => _buildDeviceItem(d)),
                    ],

                    const SizedBox(height: 80),
                  ],
                ),
              ),
      ),
    );
  }

  Widget _buildEnvCard(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 6),
              Text(label, style: const TextStyle(fontSize: 13, color: Colors.white54)),
            ],
          ),
          Text(value, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: Colors.white)),
        ],
      ),
    );
  }

  Widget _buildDeviceItem(dynamic d) {
    final isOnline = d['status'] == 'online';
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E1E1E),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(Icons.router, color: isOnline ? const Color(0xFF66BB6A) : Colors.redAccent, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(d['name'] ?? '未知设备', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: Colors.white)),
                const SizedBox(height: 2),
                Text('ID: ${d['device_id'] ?? '--'} · ${d['plot_id'] ?? '--'}', style: const TextStyle(fontSize: 12, color: Colors.white54)),
              ],
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: isOnline ? Colors.green.withOpacity(0.15) : Colors.red.withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              isOnline ? '在线' : '离线',
              style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: isOnline ? const Color(0xFF66BB6A) : Colors.redAccent),
            ),
          ),
        ],
      ),
    );
  }
}

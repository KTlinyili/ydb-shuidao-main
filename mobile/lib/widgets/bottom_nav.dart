import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class MainShell extends StatelessWidget {
  final Widget child;
  const MainShell({super.key, required this.child});

  static const _items = [
    _NavItem(icon: Icons.home_rounded, label: '首页', path: '/home'),
    _NavItem(icon: Icons.local_florist_rounded, label: '知识', path: '/knowledge'),
    _NavItem(icon: Icons.history_rounded, label: '历史', path: '/history'),
    _NavItem(icon: Icons.settings_rounded, label: '设置', path: '/settings'),
  ];

  int _getCurrentIndex(String location) {
    for (int i = 0; i < _items.length; i++) {
      if (location.startsWith(_items[i].path)) return i;
    }
    return 0;
  }

  void _onItemTap(BuildContext context, int index) {
    context.go(_items[index].path);
  }

  void _showCameraModal(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.only(bottom: 20),
              decoration: BoxDecoration(
                color: Colors.grey[300],
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.camera_alt_rounded, color: Color(0xFF2E7D32)),
              title: const Text('拍照检测'),
              onTap: () {
                Navigator.pop(context);
                context.go('/identify');
              },
            ),
            ListTile(
              leading: const Icon(Icons.photo_library_rounded, color: Color(0xFF2E7D32)),
              title: const Text('从相册选择'),
              onTap: () {
                Navigator.pop(context);
                context.go('/identify');
              },
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    final currentIndex = _getCurrentIndex(location);

    return Scaffold(
      extendBody: true,
      body: child,
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCameraModal(context),
        backgroundColor: const Color(0xFF2E7D32),
        elevation: 8,
        shape: const CircleBorder(),
        child: const Icon(Icons.camera_alt_rounded, color: Colors.white, size: 30),
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerDocked,
      bottomNavigationBar: BottomAppBar(
        shape: const CircularNotchedRectangle(),
        notchMargin: 6.0,
        color: Theme.of(context).colorScheme.surface,
        surfaceTintColor: Colors.transparent,
        elevation: 10,
        height: 55,
        padding: EdgeInsets.zero,
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceAround,
          children: [
            _buildNavItem(context, _items[0], currentIndex == 0, 0),
            _buildNavItem(context, _items[1], currentIndex == 1, 1),
            const SizedBox(width: 48),
            _buildNavItem(context, _items[2], currentIndex == 2, 2),
            _buildNavItem(context, _items[3], currentIndex == 3, 3),
          ],
        ),
      ),
    );
  }

  Widget _buildNavItem(BuildContext context, _NavItem item, bool isSelected, int index) {
    final colorScheme = Theme.of(context).colorScheme;

    return InkWell(
      onTap: () => _onItemTap(context, index),
      customBorder: const CircleBorder(),
      child: Padding(
        padding: const EdgeInsets.all(10.0),
        child: Icon(
          item.icon,
          color: isSelected ? colorScheme.primary : colorScheme.onSurface.withOpacity(0.4),
          size: 26,
        ),
      ),
    );
  }
}

class _NavItem {
  final IconData icon;
  final String label;
  final String path;

  const _NavItem({
    required this.icon,
    required this.label,
    required this.path,
  });
}

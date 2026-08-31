import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../pages/home_page.dart';
import '../pages/identify_page.dart';
import '../pages/monitor_page.dart';
import '../pages/warning_page.dart';
import '../pages/settings_page.dart';
import '../pages/history_page.dart';
import '../pages/knowledge_page.dart';
import '../pages/disease_detail_page.dart';
import '../widgets/bottom_nav.dart';

final appRouter = GoRouter(
  initialLocation: '/home',
  routes: [
    ShellRoute(
      builder: (context, state, child) => MainShell(child: child),
      routes: [
        GoRoute(
          path: '/home',
          builder: (context, state) => const HomePage(),
        ),
        GoRoute(
          path: '/identify',
          builder: (context, state) => const IdentifyPage(),
        ),
        GoRoute(
          path: '/history',
          builder: (context, state) => const HistoryPage(),
        ),
        GoRoute(
          path: '/knowledge',
          builder: (context, state) => const KnowledgePage(),
        ),
        GoRoute(
          path: '/warnings',
          builder: (context, state) => const WarningPage(),
        ),
        GoRoute(
          path: '/monitor',
          builder: (context, state) => const MonitorPage(),
        ),
        GoRoute(
          path: '/settings',
          builder: (context, state) => const SettingsPage(),
        ),
      ],
    ),
    GoRoute(
      path: '/knowledge/:key',
      builder: (context, state) {
        final k = state.pathParameters['key'] ?? '';
        return DiseaseDetailPage(diseaseKey: k);
      },
    ),
  ],
);

import { useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  ApiOutlined,
  ApartmentOutlined,
  BellOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FundOutlined,
  HistoryOutlined,
  MonitorOutlined,
  ReadOutlined,
  ScanOutlined,
  SearchOutlined,
  SettingOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Avatar, Badge, Breadcrumb, Dropdown, Input, Layout, Menu, Tooltip, theme } from 'antd';
import { FARM_INFO } from '@/utils/constants';
import { warningRecords } from '@/mock/warnings';

const MENU_ITEMS = [
  { key: 'group-monitor', label: '监测预警', type: 'group' as const, children: [
    { key: '/dashboard', icon: <DashboardOutlined />, label: '首页概览' },
    { key: '/live', icon: <MonitorOutlined />, label: '实时监测' },
    { key: '/identify', icon: <ScanOutlined />, label: '病虫害识别' },
    { key: '/environment', icon: <FundOutlined />, label: '环境监测' },
    { key: '/warnings', icon: <ThunderboltOutlined />, label: '风险预警' },
  ]},
  { key: 'group-diag', label: '智能诊断', type: 'group' as const, children: [
    { key: '/consult', icon: <ExperimentOutlined />, label: '智能会诊' },
    { key: '/map', icon: <ApartmentOutlined />, label: '田间地图' },
    { key: '/knowledge', icon: <ReadOutlined />, label: '知识库' },
  ]},
  { key: 'group-ops', label: '运维管理', type: 'group' as const, children: [
    { key: '/devices', icon: <ApiOutlined />, label: '设备管理' },
    { key: '/history', icon: <HistoryOutlined />, label: '历史记录' },
    { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
  ]},
];

const PATH_NAMES: Record<string, string> = {
  '/dashboard': '首页概览',
  '/live': '实时监测',
  '/identify': '病虫害识别',
  '/environment': '环境监测',
  '/warnings': '风险预警',
  '/consult': '智能会诊',
  '/map': '田间地图',
  '/knowledge': '知识库',
  '/devices': '设备管理',
  '/history': '历史记录',
  '/settings': '系统设置',
};

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const { token } = theme.useToken();
  const pendingCount = useMemo(
    () => warningRecords.filter((w) => w.status === 'pending').length,
    [],
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={208}
        style={{
          borderRight: `1px solid ${token.colorBorderSecondary}`,
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
        }}
      >
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '0 16px',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <div
            style={{
              width: 30,
              height: 30,
              borderRadius: 8,
              background: '#2E8B62',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            {/* 稻穗图形标识 */}
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 21c0-6 0-9 0-11M12 10c0-2-1.5-4-4-4 0 2.5 1.5 4 4 4zm0 0c0-2 1.5-4 4-4 0 2.5-1.5 4-4 4zm0 4c0-2-1.5-4-4-4 0 2.5 1.5 4 4 4zm0 0c0-2 1.5-4 4-4 0 2.5-1.5 4-4 4z"
                stroke="#fff"
                strokeWidth="1.6"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
          {!collapsed && (
            <div style={{ lineHeight: 1.2 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: '#1F262B', letterSpacing: 0.5 }}>
                稻影知微
              </div>
              <div style={{ fontSize: 10, color: '#8B96A0', marginTop: 1 }}>
                水稻病虫害智能监测预警
              </div>
            </div>
          )}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={MENU_ITEMS}
          onClick={({ key }) => navigate(key)}
          style={{ borderInlineEnd: 'none', paddingTop: 4, paddingBottom: 24 }}
        />
      </Layout.Sider>

      <Layout style={{ marginLeft: collapsed ? 80 : 208, transition: 'margin-left .2s' }}>
        <Layout.Header
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, flex: 1, minWidth: 0 }}>
            <Breadcrumb
              items={[
                { title: '稻影知微' },
                { title: <b style={{ fontWeight: 600, color: '#2B333A' }}>{PATH_NAMES[location.pathname] ?? '首页概览'}</b> },
              ]}
              style={{ flexShrink: 0 }}
            />
            <Input
              prefix={<SearchOutlined style={{ color: '#9AA6AF' }} />}
              placeholder="搜索地块、设备、病虫害或知识条目…"
              size="middle"
              style={{ background: '#F4F6F5', maxWidth: 340 }}
              onPressEnter={(e) => {
                const v = (e.target as HTMLInputElement).value.trim();
                if (v) navigate(`/knowledge?q=${encodeURIComponent(v)}`);
              }}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
            <Tooltip title="演示数据环境 · 每日 17:42 同步">
              <span style={{ fontSize: 12, color: '#64707C' }}>
                <span className="status-dot online pulse" />
                边缘节点 2/2 在线
              </span>
            </Tooltip>
            <Badge count={pendingCount} size="small" offset={[-2, 2]}>
              <BellOutlined
                style={{ fontSize: 16, color: '#5A6570', cursor: 'pointer' }}
                onClick={() => navigate('/warnings')}
              />
            </Badge>
            <Dropdown
              menu={{
                items: [
                  { key: 'farm', label: FARM_INFO.name, disabled: true },
                  { type: 'divider' },
                  { key: 'profile', label: '个人中心' },
                  { key: 'logout', label: '退出登录' },
                ],
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <Avatar size={28} style={{ background: '#5B8D73', fontSize: 12 }}>
                  稼
                </Avatar>
                <span style={{ fontSize: 13, color: '#3D474F' }}>王稼先</span>
              </div>
            </Dropdown>
          </div>
        </Layout.Header>
        <Layout.Content style={{ padding: 16, minHeight: 'calc(100vh - 56px)' }}>
          <Outlet />
        </Layout.Content>
        <div
          style={{
            textAlign: 'center',
            padding: '10px 0 14px',
            fontSize: 11,
            color: '#A5AEB5',
          }}
        >
          稻影知微 RiceGuard · 演示版 v0.1 · 数据为模拟数据，仅用于比赛演示
        </div>
      </Layout>
    </Layout>
  );
}

import { useEffect, useMemo, useState } from 'react';
import {
  ApiOutlined,
  CameraOutlined,
  CloudOutlined,
  DesktopOutlined,
  PlusOutlined,
  ReloadOutlined,
  WifiOutlined,
} from '@ant-design/icons';
import {
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Input,
  Modal,
  Progress,
  Row,
  Segmented,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  message,
} from 'antd';
import type { Device, EdgeNodeStatus } from '@/types/domain';
import { listDevices, listEdgeStatuses } from '@/api/services';
import { DeviceStatusBadge, PageHeader } from '@/components/common';
import { fromNow } from '@/utils/format';
import { plotById } from '@/mock/farm';

const KIND_LABEL: Record<Device['kind'], { text: string; icon: React.ReactNode }> = {
  camera: { text: '摄像头', icon: <CameraOutlined /> },
  env_sensor: { text: '气象站', icon: <CloudOutlined /> },
  soil_sensor: { text: '土壤墒情仪', icon: <CloudOutlined /> },
  edge: { text: '边缘节点', icon: <DesktopOutlined /> },
  gateway: { text: '网关', icon: <WifiOutlined /> },
};

/** 设备管理页：设备台账 + 边缘节点状态。 */
export default function DevicePage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [edges, setEdges] = useState<EdgeNodeStatus[]>([]);
  const [kindFilter, setKindFilter] = useState<string>('all');
  const [search, setSearch] = useState('');
  const [active, setActive] = useState<Device | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [reloadTick, setReloadTick] = useState(0);

  useEffect(() => {
    listDevices().then(setDevices);
    listEdgeStatuses().then(setEdges);
  }, [reloadTick]);

  const filtered = useMemo(
    () =>
      devices.filter(
        (d) =>
          (kindFilter === 'all' || d.kind === kindFilter) &&
          (!search ||
            d.name.toLowerCase().includes(search.toLowerCase()) ||
            d.id.toLowerCase().includes(search.toLowerCase())),
      ),
    [devices, kindFilter, search],
  );

  const online = devices.filter((d) => d.status === 'online').length;

  return (
    <div>
      <PageHeader
        title="设备管理"
        subtitle="物联网设备台账 · 摄像头 / 气象站 / 土壤墒情仪 / 边缘节点 / 网关"
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => { setReloadTick((t) => t + 1); message.success('设备状态已刷新（模拟）'); }}>
              刷新状态
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>
              接入设备
            </Button>
          </Space>
        }
      />

      <Row gutter={[12, 12]}>
        {[
          { title: '设备总数', value: devices.length, suffix: '台' },
          { title: '在线', value: online, suffix: '台' },
          { title: '离线/故障', value: devices.length - online, suffix: '台' },
          { title: '边缘节点负载（NPU 均值）', value: edges.length ? Math.round(edges.reduce((a, b) => a + b.npuPct, 0) / edges.length) : 0, suffix: '%' },
        ].map((s) => (
          <Col key={s.title} xs={12} lg={6}>
            <Card size="small" styles={{ body: { padding: 14 } }}>
              <Statistic
                title={<span style={{ fontSize: 12, color: '#64707C' }}>{s.title}</span>}
                value={s.value}
                suffix={<span style={{ fontSize: 12, color: '#8B96A0' }}>{s.suffix}</span>}
                valueStyle={{ fontSize: 22 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      {/* 边缘节点 */}
      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        {edges.map((e) => (
          <Col key={e.id} xs={24} lg={12}>
            <Card
              size="small"
              title={
                <Space>
                  <DesktopOutlined style={{ color: '#2E8B62' }} />
                  {e.name}（{e.id}）
                </Space>
              }
              extra={<Badge status={e.status === 'online' ? 'processing' : 'error'} text={e.status === 'online' ? '推理服务运行中' : '异常'} />}
            >
              <Row gutter={12}>
                {[
                  { label: 'CPU', v: e.cpuPct },
                  { label: '内存', v: e.memPct },
                  { label: 'NPU', v: e.npuPct },
                ].map((x) => (
                  <Col key={x.label} span={6}>
                    <div style={{ fontSize: 11, color: '#8B96A0' }}>{x.label}</div>
                    <Progress percent={x.v} size="small" strokeColor={x.v > 85 ? '#C08A2E' : '#2E8B62'} format={(p) => `${p}%`} />
                  </Col>
                ))}
                <Col span={6}>
                  <div style={{ fontSize: 11, color: '#8B96A0' }}>温度</div>
                  <div className="num" style={{ fontSize: 18, fontWeight: 600, color: e.tempC > 70 ? '#C05621' : '#2B333A' }}>
                    {e.tempC}℃
                  </div>
                </Col>
              </Row>
              <Descriptions size="small" column={2} style={{ marginTop: 8 }}>
                <Descriptions.Item label="推理模型">{e.model}</Descriptions.Item>
                <Descriptions.Item label="单帧耗时">{e.inferenceMs} ms</Descriptions.Item>
                <Descriptions.Item label="检测帧率">{e.fps} fps</Descriptions.Item>
                <Descriptions.Item label="连续运行">{Math.floor(e.uptimeHours / 24)} 天 {e.uptimeHours % 24} 小时</Descriptions.Item>
              </Descriptions>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 设备台账 */}
      <Card
        size="small"
        title="设备台账"
        style={{ marginTop: 12 }}
        extra={
          <Space>
            <Input.Search
              size="small"
              placeholder="搜索设备名称/编号"
              style={{ width: 200 }}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              allowClear
            />
            <Segmented
              size="small"
              value={kindFilter}
              onChange={(v) => setKindFilter(v as string)}
              options={[
                { value: 'all', label: '全部' },
                { value: 'camera', label: '摄像头' },
                { value: 'env_sensor', label: '气象站' },
                { value: 'soil_sensor', label: '墒情仪' },
                { value: 'edge', label: '边缘' },
                { value: 'gateway', label: '网关' },
              ]}
            />
          </Space>
        }
      >
        <Table
          size="small"
          rowKey="id"
          pagination={{ pageSize: 10, size: 'small' }}
          dataSource={filtered}
          onRow={(r) => ({ onClick: () => setActive(r), style: { cursor: 'pointer' } })}
          columns={[
            {
              title: '设备',
              dataIndex: 'name',
              width: 200,
              render: (n: string, r: Device) => (
                <Space size={6} style={{ whiteSpace: 'nowrap' }}>
                  <span style={{ color: '#64707C' }}>{KIND_LABEL[r.kind].icon}</span>
                  <span style={{ fontWeight: 500 }}>{n}</span>
                </Space>
              ),
            },
            { title: '编号', dataIndex: 'id', width: 100 },
            { title: '型号', dataIndex: 'model', width: 160, ellipsis: true },
            { title: '协议', dataIndex: 'protocol', width: 130 },
            {
              title: '所属地块',
              dataIndex: 'plotId',
              width: 120,
              render: (p: string | null) => (p ? plotById(p).name : '— 全基地 —'),
            },
            {
              title: '信号',
              dataIndex: 'signal',
              width: 110,
              render: (v: number) => (
                <Progress percent={v} size="small" showInfo={false} strokeColor={v < 50 ? '#C08A2E' : '#2E8B62'} style={{ width: 70, margin: 0 }} />
              ),
            },
            {
              title: '电量',
              dataIndex: 'batteryPct',
              width: 84,
              render: (v: number | null) =>
                v === null ? <span style={{ color: '#B9C2BD' }}>市电</span> : <span className="num" style={{ color: v < 30 ? '#C05621' : undefined }}>{v}%</span>,
            },
            { title: '状态', dataIndex: 'status', width: 84, render: (s: Device['status']) => <DeviceStatusBadge status={s} /> },
            {
              title: '最近心跳',
              dataIndex: 'lastHeartbeat',
              width: 110,
              render: (t: string) => <span style={{ fontSize: 11.5, color: '#8B96A0' }}>{fromNow(t)}</span>,
            },
          ]}
        />
      </Card>

      {/* 设备详情 */}
      <Drawer
        title={active ? `${active.name}（${active.id}）` : ''}
        width={440}
        open={!!active}
        onClose={() => setActive(null)}
        extra={
          active && (
            <Space>
              <Button size="small" onClick={() => message.success('已下发远程重启指令（模拟）')}>
                远程重启
              </Button>
              <Button size="small" onClick={() => message.success('已校时（模拟）')}>
                校时
              </Button>
            </Space>
          )
        }
      >
        {active && (
          <div>
            <Descriptions size="small" column={1} bordered>
              <Descriptions.Item label="设备类型">{KIND_LABEL[active.kind].text}</Descriptions.Item>
              <Descriptions.Item label="型号">{active.model}</Descriptions.Item>
              <Descriptions.Item label="通信协议">{active.protocol}</Descriptions.Item>
              <Descriptions.Item label="固件版本">{active.firmware}</Descriptions.Item>
              <Descriptions.Item label="所属地块">
                {active.plotId ? `${plotById(active.plotId).name}（${active.plotId}）` : '全基地共用'}
              </Descriptions.Item>
              <Descriptions.Item label="运行状态"><DeviceStatusBadge status={active.status} /></Descriptions.Item>
              <Descriptions.Item label="信号强度">{active.signal}%</Descriptions.Item>
              <Descriptions.Item label="供电">{active.batteryPct === null ? '市电 / 太阳能' : `电池 ${active.batteryPct}%`}</Descriptions.Item>
              <Descriptions.Item label="最近心跳">{fromNow(active.lastHeartbeat)}</Descriptions.Item>
              {active.streamUrl && <Descriptions.Item label="流地址（预留）">{active.streamUrl}</Descriptions.Item>}
            </Descriptions>
            <Card size="small" title="近 24 小时心跳概况" style={{ marginTop: 12 }}>
              {Array.from({ length: 48 }).map((_, i) => {
                const ok = active.status === 'offline' ? i < 36 : active.status === 'fault' ? i % 7 !== 3 : true;
                return (
                  <TooltipBadge key={i} ok={ok} index={i} />
                );
              })}
              <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 8 }}>
                每 30 分钟一格 · 绿色=正常上报，灰色=缺失
              </div>
            </Card>
          </div>
        )}
      </Drawer>

      <Modal
        title="接入新设备"
        open={addOpen}
        onOk={() => {
          setAddOpen(false);
          message.success('设备登记成功，等待网关发现（模拟）');
        }}
        onCancel={() => setAddOpen(false)}
        okText="登记"
        cancelText="取消"
      >
        <Descriptions size="small" column={1} style={{ marginTop: 8 }}>
          <Descriptions.Item label="设备类型">
            <Select
              defaultValue="camera"
              style={{ width: 200 }}
              options={Object.entries(KIND_LABEL).map(([v, l]) => ({ value: v, label: l.text }))}
            />
          </Descriptions.Item>
          <Descriptions.Item label="设备名称">
            <Input placeholder="如：东区 5 号田 · 高清枪机" style={{ width: 260 }} />
          </Descriptions.Item>
          <Descriptions.Item label="安装地块">
            <Select
              defaultValue="P01"
              style={{ width: 200 }}
              options={['P01', 'P02', 'P03', 'P04', 'P05', 'P06', 'P07', 'P08'].map((p) => ({
                value: p,
                label: `${p} ${plotById(p).name}`,
              }))}
            />
          </Descriptions.Item>
          <Descriptions.Item label="接入协议">
            <Select
              defaultValue="rtsp"
              style={{ width: 200 }}
              options={[
                { value: 'rtsp', label: 'RTSP / GB28181' },
                { value: 'modbus', label: 'Modbus-RTU' },
                { value: 'lora', label: 'LoRaWAN' },
                { value: 'mqtt', label: 'MQTT' },
              ]}
            />
          </Descriptions.Item>
        </Descriptions>
      </Modal>
    </div>
  );
}

import { Tooltip } from 'antd';

function TooltipBadge({ ok, index }: { ok: boolean; index: number }) {
  return (
    <Tooltip title={`${index * 0.5} 小时前：${ok ? '正常上报' : '心跳缺失'}`}>
      <span
        style={{
          display: 'inline-block',
          width: 9,
          height: 14,
          borderRadius: 2,
          marginRight: 2,
          marginBottom: 2,
          background: ok ? '#69B584' : '#DCE3DF',
          cursor: 'pointer',
        }}
      />
    </Tooltip>
  );
}

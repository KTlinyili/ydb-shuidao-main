import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExportOutlined,
  SendOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Modal,
  Progress,
  Radio,
  Row,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Timeline,
  Typography,
  message,
} from 'antd';
import type { WarningRecord } from '@/types/domain';
import { listWarnings, getRiskSeries, getLesionAreaSeries } from '@/api/services';
import { PageHeader, PestTag, RiskTag } from '@/components/common';
import { LesionAreaChart, RiskTrendChart, riskLegendNote } from '@/components/charts';
import { RISK_LEVEL_META, PEST_META } from '@/utils/constants';
import { fmtFullTime, pestName } from '@/utils/format';
import { plotById } from '@/mock/farm';
import { WarningList } from '@/components/WarningList';

/**
 * 风险预警页：分级预警列表 + 风险构成 + 病害面积趋势 + 处置流转。
 */
export default function RiskWarningPage() {
  const [searchParams] = useSearchParams();
  const [records, setRecords] = useState<WarningRecord[]>([]);
  const [activeId, setActiveId] = useState<string | null>(searchParams.get('id'));
  const [statusFilter, setStatusFilter] = useState<'all' | WarningRecord['status']>('all');
  const [levelFilter, setLevelFilter] = useState<'all' | 'high' | 'critical'>('all');
  const [dispatchOpen, setDispatchOpen] = useState(false);
  const [timelineData, setTimelineData] = useState<Awaited<ReturnType<typeof getRiskSeries>>>([]);
  const [areaData, setAreaData] = useState<Awaited<ReturnType<typeof getLesionAreaSeries>>>([]);

  useEffect(() => {
    listWarnings().then(setRecords);
  }, []);

  const active = useMemo(
    () => records.find((w) => w.id === activeId) ?? records[0],
    [records, activeId],
  );

  useEffect(() => {
    if (active) {
      getRiskSeries('7d', active.plotId).then(setTimelineData);
      getLesionAreaSeries('7d', active.plotId).then(setAreaData);
    }
  }, [active?.id]);

  const filtered = useMemo(
    () =>
      records.filter(
        (w) =>
          (statusFilter === 'all' || w.status === statusFilter) &&
          (levelFilter === 'all' ||
            (levelFilter === 'high' && w.level === 'high') ||
            (levelFilter === 'critical' && w.level === 'critical')),
      ),
    [records, statusFilter, levelFilter],
  );

  const counts = useMemo(
    () => ({
      critical: records.filter((w) => w.level === 'critical').length,
      high: records.filter((w) => w.level === 'high').length,
      medium: records.filter((w) => w.level === 'medium').length,
      pending: records.filter((w) => w.status === 'pending').length,
      processing: records.filter((w) => w.status === 'processing').length,
      resolved: records.filter((w) => w.status === 'resolved').length,
    }),
    [records],
  );

  if (!records.length) return null;

  return (
    <div>
      <PageHeader
        title="风险预警"
        subtitle="综合风险 = 视觉 45% + 环境 35% + 趋势 20% · 分级：低 <35 · 中 35~54 · 高 55~74 · 严重 ≥75"
        extra={
          <Space>
            <Button icon={<ExportOutlined />}>导出报表</Button>
            <Button type="primary" icon={<SendOutlined />} onClick={() => setDispatchOpen(true)}>
              一键派单
            </Button>
          </Space>
        }
      />

      <Row gutter={[12, 12]}>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" styles={{ body: { padding: 14 } }}>
            <Statistic
              title={<span style={{ fontSize: 12, color: '#64707C' }}>严重风险预警</span>}
              value={counts.critical}
              suffix="起"
              valueStyle={{ color: RISK_LEVEL_META.critical.color, fontSize: 24 }}
              prefix={<ThunderboltOutlined style={{ fontSize: 16 }} />}
            />
            <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 4 }}>需立即组织防治作业</div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" styles={{ body: { padding: 14 } }}>
            <Statistic
              title={<span style={{ fontSize: 12, color: '#64707C' }}>高风险预警</span>}
              value={counts.high}
              suffix="起"
              valueStyle={{ color: RISK_LEVEL_META.high.color, fontSize: 24 }}
            />
            <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 4 }}>48 小时内完成处置</div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" styles={{ body: { padding: 14 } }}>
            <Statistic
              title={<span style={{ fontSize: 12, color: '#64707C' }}>待处理 / 处置中</span>}
              value={`${counts.pending} / ${counts.processing}`}
              valueStyle={{ fontSize: 24 }}
            />
            <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 4 }}>已解除 {counts.resolved} 起</div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small" styles={{ body: { padding: 14 } }}>
            <div style={{ fontSize: 12, color: '#64707C', marginBottom: 8 }}>预警等级说明</div>
            {riskLegendNote()}
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={16}>
          <Card
            size="small"
            title="预警记录"
            extra={
              <Space>
                <Radio.Group
                  size="small"
                  value={levelFilter}
                  onChange={(e) => setLevelFilter(e.target.value)}
                  optionType="button"
                  buttonStyle="solid"
                  options={[
                    { value: 'all', label: '全部等级' },
                    { value: 'high', label: '高风险' },
                    { value: 'critical', label: '严重' },
                  ]}
                />
                <Radio.Group
                  size="small"
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  optionType="button"
                  options={[
                    { value: 'all', label: '全部状态' },
                    { value: 'pending', label: '待处理' },
                    { value: 'processing', label: '处置中' },
                    { value: 'resolved', label: '已解除' },
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
              onRow={(r) => ({
                onClick: () => setActiveId(r.id),
                style: { cursor: 'pointer', background: r.id === active?.id ? '#F3F9F5' : undefined },
              })}
              columns={[
                { title: '预警号', dataIndex: 'id', width: 84 },
                {
                  title: '时间',
                  dataIndex: 'time',
                  width: 130,
                  render: (t: string) => <span className="num" style={{ fontSize: 12 }}>{fmtFullTime(t).slice(5)}</span>,
                },
                {
                  title: '地块',
                  dataIndex: 'plotId',
                  width: 130,
                  render: (p: string) => plotById(p).name,
                },
                { title: '对象', dataIndex: 'pest', width: 110, render: (p: WarningRecord['pest']) => <PestTag pest={p} size="small" /> },
                {
                  title: '等级',
                  dataIndex: 'level',
                  width: 130,
                  render: (l: WarningRecord['level'], r: WarningRecord) => <RiskTag level={l} score={r.compositeRisk} />,
                },
                {
                  title: '风险构成',
                  width: 180,
                  render: (_, r: WarningRecord) => (
                    <span className="num" style={{ fontSize: 11, color: '#8B96A0' }}>
                      视{r.visualRisk} / 环{r.envRisk} / 势{r.trendRisk}
                    </span>
                  ),
                },
                {
                  title: '状态',
                  dataIndex: 'status',
                  width: 90,
                  render: (s: WarningRecord['status']) => (
                    <span
                      style={{
                        fontSize: 12,
                        color: s === 'pending' ? '#B9452F' : s === 'processing' ? '#C08A2E' : '#3D8B5F',
                      }}
                    >
                      {s === 'pending' ? '● 待处理' : s === 'processing' ? '● 处置中' : '● 已解除'}
                    </span>
                  ),
                },
              ]}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {active ? (
            <Card
              size="small"
              title={`预警详情 · ${active.id}`}
              extra={
                active.status === 'pending' && (
                  <Button
                    size="small"
                    type="primary"
                    onClick={() => {
                      setDispatchOpen(true);
                    }}
                  >
                    处置派单
                  </Button>
                )
              }
            >
              <Descriptions size="small" column={1} style={{ marginBottom: 8 }}>
                <Descriptions.Item label="预警对象">
                  <PestTag pest={active.pest} /> <RiskTag level={active.level} score={active.compositeRisk} />
                </Descriptions.Item>
                <Descriptions.Item label="发生地块">
                  {plotById(active.plotId).name}（管理员 {plotById(active.plotId).manager}）
                </Descriptions.Item>
                <Descriptions.Item label="触发时间">{fmtFullTime(active.time)}</Descriptions.Item>
                <Descriptions.Item label="触发规则">
                  <span style={{ color: '#4A5560' }}>{active.trigger}</span>
                </Descriptions.Item>
              </Descriptions>

              <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
                {[
                  { label: '视觉风险', v: active.visualRisk, color: '#B85C5C' },
                  { label: '环境风险', v: active.envRisk, color: '#C08A3E' },
                  { label: '趋势风险', v: active.trendRisk, color: '#7C93AB' },
                ].map((x) => (
                  <div key={x.label} style={{ flex: 1 }}>
                    <div style={{ fontSize: 11, color: '#8B96A0' }}>{x.label}</div>
                    <Progress
                      percent={x.v}
                      size="small"
                      strokeColor={x.color}
                      format={(p) => String(p)}
                      style={{ marginTop: 2 }}
                    />
                  </div>
                ))}
              </div>

              <Tabs
                size="small"
                items={[
                  {
                    key: 'advice',
                    label: '处置建议',
                    children: (
                      <ul style={{ margin: 0, paddingLeft: 18 }}>
                        {active.advice.map((a, i) => (
                          <li key={i} style={{ fontSize: 12.5, color: '#3D474F', lineHeight: 1.9 }}>
                            {a}
                          </li>
                        ))}
                      </ul>
                    ),
                  },
                  {
                    key: 'flow',
                    label: '处置流转',
                    children: (
                      <Timeline
                        style={{ marginTop: 4 }}
                        items={[
                          { color: 'red', children: `${fmtFullTime(active.time)} 系统自动触发预警` },
                          {
                            color: active.status === 'pending' ? 'gray' : 'blue',
                            children:
                              active.status === 'pending'
                                ? '等待值班人员接单'
                                : `${active.handler ?? '值班员'} 已接单并组织处置`,
                          },
                          {
                            color: active.status === 'resolved' ? 'green' : 'gray',
                            children:
                              active.status === 'resolved'
                                ? `${active.resolvedAt ? fmtFullTime(active.resolvedAt) : ''} 复查通过，预警解除`
                                : '防治后 3~8 天复查确认',
                          },
                        ]}
                      />
                    ),
                  },
                ]}
              />
            </Card>
          ) : (
            <Card size="small">
              <Empty description="选择一条预警查看详情" />
            </Card>
          )}
        </Col>
      </Row>

      {active && (
        <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
          <Col xs={24} lg={12}>
            <Card size="small" title={`${plotById(active.plotId).name} · 近 7 天综合风险趋势`}>
              <RiskTrendChart data={timelineData} range="7d" height={250} />
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card size="small" title={`${plotById(active.plotId).name} · 近 7 天病害面积变化`}>
              <LesionAreaChart data={areaData} range="7d" height={250} />
            </Card>
          </Col>
        </Row>
      )}

      <Modal
        title="预警处置派单"
        open={dispatchOpen}
        onOk={() => {
          setDispatchOpen(false);
          message.success('派单成功：已通知地块管理员与植保服务队（模拟）');
        }}
        onCancel={() => setDispatchOpen(false)}
        okText="确认派单"
        cancelText="取消"
      >
        <Descriptions size="small" column={1} style={{ marginTop: 8 }}>
          <Descriptions.Item label="预警">{active?.id} · {pestName(active?.pest ?? 'multi')}</Descriptions.Item>
          <Descriptions.Item label="地块">{active ? plotById(active.plotId).name : '-'}</Descriptions.Item>
          <Descriptions.Item label="处置时限">
            {active?.level === 'critical' ? '24 小时内' : '48 小时内'}
          </Descriptions.Item>
          <Descriptions.Item label="派发对象">
            {active ? plotById(active.plotId).manager : '-'}（地块管理员）、植保服务队
          </Descriptions.Item>
          <Descriptions.Item label="附带材料">
            检测截图、风险构成说明、防治方案（{active?.advice.length ?? 0} 条）
          </Descriptions.Item>
        </Descriptions>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          派单后预警状态将变更为"处置中"，并在防治复查通过后自动解除。接入后端后通过企业微信/短信通道推送。
        </Typography.Text>
      </Modal>
    </div>
  );
}

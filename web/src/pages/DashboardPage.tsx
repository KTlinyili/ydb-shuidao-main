import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertOutlined,
  CameraOutlined,
  CloudOutlined,
  ExperimentOutlined,
  FieldNumberOutlined,
  RightOutlined,
  SunOutlined,
  TabletOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Button, Card, Col, Divider, List, Progress, Row, Segmented, Space, Table, Tag, Tooltip } from 'antd';
import type { DashboardStats, DetectionRecord, Plot, WarningRecord } from '@/types/domain';
import {
  getDashboardStats,
  getLatestDetections,
  getRiskSeries,
  listPlots,
  listWarnings,
} from '@/api/services';
import { PageHeader, PestTag, RiskTag, StatCards } from '@/components/common';
import { FieldMap } from '@/components/FieldMap';
import { PestBarChart, RiskTrendChart, SeverityPieChart } from '@/components/charts';
import { WarningList } from '@/components/WarningList';
import { PEST_META, PEST_ORDER, RISK_LEVEL_META, VISION_MODEL } from '@/utils/constants';
import { fmtTime, fromNow } from '@/utils/format';
import { plotById } from '@/mock/farm';

export default function DashboardPage() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [warnings, setWarnings] = useState<WarningRecord[]>([]);
  const [plots, setPlots] = useState<Plot[]>([]);
  const [latest, setLatest] = useState<DetectionRecord[]>([]);
  const [trendPlot, setTrendPlot] = useState('P01');
  const [trendData, setTrendData] = useState<Awaited<ReturnType<typeof getRiskSeries>>>([]);

  useEffect(() => {
    (async () => {
      setStats(await getDashboardStats());
      setWarnings((await listWarnings()).slice(0, 8));
      setPlots(await listPlots());
      setLatest(await getLatestDetections());
    })();
  }, []);

  useEffect(() => {
    getRiskSeries('7d', trendPlot).then(setTrendData);
  }, [trendPlot]);

  /** 今日各病虫害检出计数（按最新检测帧汇总） */
  const pestCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const d of latest) {
      for (const b of d.boxes) {
        counts.set(b.pest, (counts.get(b.pest) ?? 0) + 1);
      }
    }
    return counts;
  }, [latest]);

  /** 重点预警地块 Top3（按综合风险降序） */
  const topRiskPlots = useMemo(
    () => [...plots].sort((a, b) => b.compositeRisk - a.compositeRisk).slice(0, 3),
    [plots],
  );

  /** 实时检测动态：最新 5 条记录 */
  const liveFeed = useMemo(() => latest.slice(0, 5), [latest]);

  if (!stats) return null;

  return (
    <div>
      <PageHeader
        title="首页概览"
        subtitle="金穗智慧农场 · 一号基地 | 2026 年中稻季 | 数据更新于 08-17 17:42"
        extra={
          <Space>
            <Button icon={<ExperimentOutlined />} onClick={() => navigate('/consult')}>
              发起会诊
            </Button>
            <Button type="primary" icon={<AlertOutlined />} onClick={() => navigate('/warnings')}>
              预警中心（{stats.todayWarnings}）
            </Button>
          </Space>
        }
      />

      <StatCards
        items={[
          {
            title: '今日预警',
            value: stats.todayWarnings,
            suffix: '起',
            icon: <AlertOutlined />,
            iconBg: '#FBECEC',
            delta: stats.todayWarningsDelta,
          },
          {
            title: '高风险地块',
            value: `${stats.highRiskPlots}/${stats.totalPlots}`,
            icon: <FieldNumberOutlined />,
            iconBg: '#FBEEE5',
            footer: <span style={{ color: '#8B96A0' }}>按综合风险分级</span>,
          },
          {
            title: '今日识别',
            value: stats.todayDetections,
            suffix: '帧',
            icon: <CameraOutlined />,
            iconBg: '#E8F3ED',
            footer: <span style={{ color: '#8B96A0' }}>RK3588 NPU · 平均 38ms/帧</span>,
          },
          {
            title: '设备在线率',
            value: stats.deviceOnlineRate,
            suffix: '%',
            icon: <TabletOutlined />,
            iconBg: '#EFF3F0',
            footer: (
              <span style={{ color: '#8B96A0' }}>
                {stats.onlineDevices}/{stats.totalDevices} 台在线
              </span>
            ),
          },
          {
            title: '平均湿度',
            value: stats.avgHumidity,
            suffix: '%',
            icon: <CloudOutlined />,
            iconBg: '#EAF0F6',
            footer: <span style={{ color: '#8B96A0' }}>预警阈值 85%</span>,
          },
          {
            title: '平均温度',
            value: stats.avgTemperature,
            suffix: '℃',
            icon: <SunOutlined />,
            iconBg: '#FAF3E0',
            footer: <span style={{ color: '#8B96A0' }}>8 月中旬常值</span>,
          },
        ]}
      />

      {/* 第一排：风险趋势（大图） + 重点预警地块 */}
      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={16}>
          <Card
            size="small"
            title="近 7 天风险趋势"
            extra={
              <Segmented
                size="small"
                value={trendPlot}
                onChange={(v) => setTrendPlot(v as string)}
                options={plots.slice(0, 4).map((p) => ({ value: p.id, label: p.id }))}
              />
            }
          >
            <RiskTrendChart data={trendData} range="7d" height={318} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            size="small"
            title="重点预警地块 Top3"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/map')}>
                田间地图 <RightOutlined style={{ fontSize: 10 }} />
              </Button>
            }
          >
            {topRiskPlots.map((p, i) => (
              <div
                key={p.id}
                style={{
                  padding: '10px 12px',
                  borderRadius: 8,
                  border: `1px solid ${RISK_LEVEL_META[p.riskLevel].border}`,
                  background: RISK_LEVEL_META[p.riskLevel].bg,
                  marginBottom: i < 2 ? 10 : 12,
                  cursor: 'pointer',
                }}
                onClick={() => navigate('/map')}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: '#2B333A' }}>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 16,
                        height: 16,
                        borderRadius: 4,
                        background: RISK_LEVEL_META[p.riskLevel].color,
                        color: '#fff',
                        fontSize: 10,
                        lineHeight: '16px',
                        textAlign: 'center',
                        marginRight: 6,
                      }}
                    >
                      {i + 1}
                    </span>
                    {p.name}
                  </span>
                  <RiskTag level={p.riskLevel} score={p.compositeRisk} />
                </div>
                <div style={{ fontSize: 11.5, color: '#64707C', marginTop: 6 }}>
                  {p.variety} · {p.stage} · {p.areaMu} 亩 · 管理员 {p.manager}
                </div>
                <div style={{ display: 'flex', gap: 14, marginTop: 8, fontSize: 11 }}>
                  <span style={{ color: '#8B96A0' }}>
                    视觉 <b className="num" style={{ color: '#B85C5C' }}>{p.visualRisk}</b>
                  </span>
                  <span style={{ color: '#8B96A0' }}>
                    环境 <b className="num" style={{ color: '#C08A3E' }}>{p.envRisk}</b>
                  </span>
                  <span style={{ color: '#8B96A0' }}>
                    趋势 <b className="num" style={{ color: '#7C93AB' }}>{p.trendRisk}</b>
                  </span>
                </div>
              </div>
            ))}
            <div style={{ fontSize: 11, color: '#8B96A0', lineHeight: 1.7 }}>
              综合风险 = 视觉 ×45% + 环境 ×35% + 趋势 ×20%。高风险地块建议 48 小时内组织防治，严重风险 24 小时内。
            </div>
          </Card>
        </Col>
      </Row>

      {/* 第二排：监测点地图 + 实时检测动态 */}
      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={15}>
          <Card
            size="small"
            title="监测点分布"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/map')}>
                查看大图 <RightOutlined style={{ fontSize: 10 }} />
              </Button>
            }
          >
            <FieldMap plots={plots} height={362} showDevices />
          </Card>
        </Col>
        <Col xs={24} lg={9}>
          <Card
            size="small"
            title={
              <Space size={8}>
                实时检测动态
                <span className="status-dot online pulse" style={{ marginRight: 0 }} />
              </Space>
            }
            extra={
              <Button type="link" size="small" onClick={() => navigate('/live')}>
                实时监测 <RightOutlined style={{ fontSize: 10 }} />
              </Button>
            }
          >
            <div style={{ maxHeight: 366, overflowY: 'auto' }}>
              <List
                size="small"
                dataSource={liveFeed}
                rowKey="id"
                renderItem={(d) => {
                  const p = plotById(d.plotId);
                  return (
                    <List.Item
                      style={{ padding: '10px 6px', cursor: 'pointer' }}
                      onClick={() => navigate('/live')}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                          <span className="num" style={{ fontSize: 11.5, color: '#8B96A0' }}>
                            {fmtTime(d.time, 'HH:mm:ss')}
                          </span>
                          <span style={{ fontSize: 12.5, fontWeight: 500, color: '#2B333A' }}>
                            {p.name}
                          </span>
                          <span style={{ fontSize: 11, color: '#A5AEB5' }}>{d.cameraId}</span>
                          {d.boxes.length > 0 ? (
                            <RiskTag
                              level={
                                d.visualRisk >= 75
                                  ? 'critical'
                                  : d.visualRisk >= 55
                                    ? 'high'
                                    : d.visualRisk >= 35
                                      ? 'medium'
                                      : 'low'
                              }
                              score={d.visualRisk}
                            />
                          ) : (
                            <Tag style={{ fontSize: 10, lineHeight: '16px', paddingInline: 5 }}>无目标</Tag>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap', alignItems: 'center' }}>
                          {d.boxes.slice(0, 3).map((b) => (
                            <PestTag key={b.id} pest={b.pest} size="small" />
                          ))}
                          {d.boxes.length > 3 && (
                            <span style={{ fontSize: 11, color: '#8B96A0' }}>+{d.boxes.length - 3}</span>
                          )}
                          <span style={{ marginLeft: 'auto', fontSize: 11, color: '#A5AEB5' }} className="num">
                            {d.inferenceMs}ms · {fromNow(d.time)}
                          </span>
                        </div>
                      </div>
                    </List.Item>
                  );
                }}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* 第三排：预警列表 + 病虫害统计 + 严重程度 */}
      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={10}>
          <Card
            size="small"
            title={`最新预警（今日 ${stats.todayWarnings} 起）`}
            extra={
              <Button type="link" size="small" onClick={() => navigate('/warnings')}>
                全部 <RightOutlined style={{ fontSize: 10 }} />
              </Button>
            }
          >
            <WarningList records={warnings.slice(0, 6)} maxHeight={326} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card size="small" title="病虫害检出统计（今日）">
            <PestBarChart
              data={PEST_ORDER.map((k) => ({
                name: PEST_META[k].name,
                value: pestCounts.get(k) ?? 0,
                color: PEST_META[k].color,
              }))
                .filter((d) => d.value > 0)
                .sort((a, b) => b.value - a.value)}
              height={326}
            />
          </Card>
        </Col>
        <Col xs={24} lg={6}>
          <Card size="small" title="病斑严重程度构成">
            <SeverityPieChart
              data={[
                { name: '轻微', value: 6, color: '#5E8C61' },
                { name: '中等', value: 9, color: '#B08A2E' },
                { name: '偏重', value: 7, color: '#C05621' },
                { name: '严重', value: 3, color: '#B93A3A' },
              ]}
              height={218}
            />
            <Divider style={{ margin: '2px 0 10px' }} />
            <Row gutter={8}>
              <Col span={12}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: '#8B96A0' }}>检出总目标</div>
                  <div className="num" style={{ fontSize: 18, fontWeight: 600 }}>
                    {latest.reduce((a, b) => a + b.boxes.length, 0)} 处
                  </div>
                </div>
              </Col>
              <Col span={12}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: '#8B96A0' }}>模型置信均值</div>
                  <div className="num" style={{ fontSize: 18, fontWeight: 600 }}>91.4%</div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* 第四排：设备状态 */}
      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24}>
          <Card
            size="small"
            title="设备运行状态"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/devices')}>
                设备管理 <RightOutlined style={{ fontSize: 10 }} />
              </Button>
            }
          >
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={[
                { id: 'EDGE-01', name: '一号边缘节点 RK3588', metric: 'NPU 71% · CPU 63% · 58.4℃', health: 92, status: '运行中' },
                { id: 'EDGE-02', name: '二号边缘节点 RK3588', metric: 'NPU 52% · CPU 41% · 52.1℃', health: 95, status: '运行中' },
                { id: 'GW-01', name: '物联网关 USR-G806', metric: '4G 上联 · 信号 86%', health: 98, status: '运行中' },
                { id: 'CAM-P04', name: '东区 4 号田高清枪机', metric: '心跳丢失 6 小时', health: 0, status: '离线' },
                { id: 'SOIL-P05', name: '西区 1 号田土壤墒情仪', metric: '电池 28% · 电压偏低', health: 54, status: '故障' },
              ]}
              columns={[
                { title: '设备', dataIndex: 'name', ellipsis: true },
                { title: '运行指标', dataIndex: 'metric', ellipsis: true, width: 240 },
                {
                  title: '健康度',
                  dataIndex: 'health',
                  width: 130,
                  render: (v: number) => (
                    <Progress
                      percent={v}
                      size="small"
                      strokeColor={v > 80 ? '#3D8B5F' : v > 50 ? '#C08A2E' : '#B9452F'}
                      format={(p) => `${p}`}
                    />
                  ),
                },
                {
                  title: '状态',
                  dataIndex: 'status',
                  width: 90,
                  render: (v: string) => (
                    <span style={{ fontSize: 12, color: v === '运行中' ? '#3D8B5F' : v === '离线' ? '#98A2A9' : '#C05621' }}>
                      <span className={`status-dot ${v === '运行中' ? 'online' : v === '离线' ? 'offline' : 'fault'}`} />
                      {v}
                    </span>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

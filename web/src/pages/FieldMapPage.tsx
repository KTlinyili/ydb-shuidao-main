import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ApartmentOutlined, EnvironmentOutlined, RightOutlined } from '@ant-design/icons';
import { Button, Card, Col, Descriptions, List, Progress, Row, Space, Table, Tag } from 'antd';
import type { Device, Plot } from '@/types/domain';
import { listDevices, listPlots, listDetections } from '@/api/services';
import { FieldMap } from '@/components/FieldMap';
import { PageHeader, RiskTag } from '@/components/common';
import { RISK_LEVEL_META, FARM_INFO } from '@/utils/constants';
import { fromNow } from '@/utils/format';

/** 田间地图页：地块总平面 + 选中地块详情。 */
export default function FieldMapPage() {
  const navigate = useNavigate();
  const [plots, setPlots] = useState<Plot[]>([]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [selected, setSelected] = useState('P01');
  const [recentDets, setRecentDets] = useState<Awaited<ReturnType<typeof listDetections>>>([]);

  useEffect(() => {
    listPlots().then((p) => {
      setPlots(p);
    });
    listDevices().then(setDevices);
    listDetections(undefined, 2).then((d) => setRecentDets(d.slice(0, 12)));
  }, []);

  const plot = plots.find((p) => p.id === selected);
  const plotDevices = devices.filter((d) => d.plotId === selected);
  const plotDets = useMemo(
    () => recentDets.filter((d) => d.plotId === selected),
    [recentDets, selected],
  );

  return (
    <div>
      <PageHeader
        title="田间地图"
        subtitle={`${FARM_INFO.name} · ${FARM_INFO.region} · 总面积 ${FARM_INFO.totalAreaMu} 亩 · ${FARM_INFO.season}`}
        extra={
          <Space>
            <Tag icon={<EnvironmentOutlined />} color="green">
              8 个监测地块
            </Tag>
            <Button icon={<ApartmentOutlined />} onClick={() => navigate('/devices')}>
              设备台账
            </Button>
          </Space>
        }
      />

      <Row gutter={[12, 12]}>
        <Col xs={24} lg={16}>
          <Card size="small" title="基地总平面">
            <FieldMap
              plots={plots}
              devices={devices}
              selectedPlotId={selected}
              onSelect={setSelected}
              height={520}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          {plot && (
            <>
              <Card
                size="small"
                title={`${plot.name}（${plot.id}）`}
                extra={<RiskTag level={plot.riskLevel} score={plot.compositeRisk} />}
              >
                <Descriptions size="small" column={1} labelStyle={{ width: 88 }}>
                  <Descriptions.Item label="水稻品种">{plot.variety}</Descriptions.Item>
                  <Descriptions.Item label="生育期">{plot.stage}</Descriptions.Item>
                  <Descriptions.Item label="面积">{plot.areaMu} 亩</Descriptions.Item>
                  <Descriptions.Item label="管理员">{plot.manager}</Descriptions.Item>
                </Descriptions>
                <div style={{ display: 'flex', gap: 10, marginTop: 6 }}>
                  {[
                    { label: '视觉风险', v: plot.visualRisk },
                    { label: '环境风险', v: plot.envRisk },
                    { label: '趋势风险', v: plot.trendRisk },
                    { label: '综合风险', v: plot.compositeRisk },
                  ].map((x) => (
                    <div key={x.label} style={{ flex: 1 }}>
                      <div style={{ fontSize: 11, color: '#8B96A0' }}>{x.label}</div>
                      <Progress
                        type="circle"
                        size={54}
                        percent={x.v}
                        strokeColor={RISK_LEVEL_META[plot.riskLevel].color}
                        format={(p) => <span style={{ fontSize: 12 }}>{p}</span>}
                        style={{ marginTop: 4 }}
                      />
                    </div>
                  ))}
                </div>
                <Space style={{ marginTop: 12 }}>
                  <Button size="small" onClick={() => navigate(`/live`)}>
                    查看实时画面
                  </Button>
                  <Button size="small" type="primary" onClick={() => navigate(`/consult?plotId=${plot.id}`)}>
                    发起会诊
                  </Button>
                  <Button size="small" onClick={() => navigate(`/warnings`)}>
                    预警记录 <RightOutlined style={{ fontSize: 9 }} />
                  </Button>
                </Space>
              </Card>

              <Card size="small" title="地块设备" style={{ marginTop: 12 }}>
                <List
                  size="small"
                  dataSource={plotDevices}
                  rowKey="id"
                  renderItem={(d) => (
                    <List.Item style={{ padding: '7px 0' }}>
                      <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 12.5, fontWeight: 500 }}>{d.name}</span>
                        <span style={{ fontSize: 11, color: '#8B96A0' }}>{d.model}</span>
                        <span style={{ marginLeft: 'auto', fontSize: 11, color: d.status === 'online' ? '#3D8B5F' : d.status === 'fault' ? '#C05621' : '#98A2A9' }}>
                          ● {d.status === 'online' ? '在线' : d.status === 'fault' ? '故障' : '离线'} · {fromNow(d.lastHeartbeat)}
                        </span>
                      </div>
                    </List.Item>
                  )}
                />
              </Card>

              <Card size="small" title="近期检测" style={{ marginTop: 12 }}>
                <Table
                  size="small"
                  rowKey="id"
                  pagination={false}
                  dataSource={plotDets.slice(0, 6)}
                  columns={[
                    { title: '记录', dataIndex: 'id', width: 74 },
                    { title: '时间', dataIndex: 'time', width: 96, render: (t: string) => <span style={{ fontSize: 11 }} className="num">{fromNow(t)}</span> },
                    { title: '目标', dataIndex: 'boxes', render: (b: unknown[]) => `${b?.length ?? 0} 处` },
                    { title: '视觉风险', dataIndex: 'visualRisk', width: 82, render: (v: number) => <span className="num">{v}</span> },
                  ]}
                />
              </Card>
            </>
          )}
        </Col>
      </Row>
    </div>
  );
}

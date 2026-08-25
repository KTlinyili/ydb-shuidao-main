import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DownloadOutlined, ExperimentOutlined, HistoryOutlined } from '@ant-design/icons';
import { Button, Card, Col, Descriptions, Drawer, Row, Segmented, Space, Table, Tag } from 'antd';
import type { DetectionRecord, PestKey, Severity } from '@/types/domain';
import { listDetections } from '@/api/services';
import { FrameAnalysis } from '@/components/FrameAnalysis';
import { PageHeader, PestTag, SeverityTag } from '@/components/common';
import { PEST_META } from '@/utils/constants';
import { fmtFullTime, SOURCE_LABEL } from '@/utils/format';
import { plotById } from '@/mock/farm';

/** 历史记录页：检测记录归档查询。 */
export default function HistoryPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState(7);
  const [plotFilter, setPlotFilter] = useState<string>('all');
  const [records, setRecords] = useState<DetectionRecord[]>([]);
  const [active, setActive] = useState<DetectionRecord | null>(null);

  useEffect(() => {
    listDetections(undefined, days).then(setRecords);
  }, [days]);

  const filtered = useMemo(
    () => records.filter((r) => plotFilter === 'all' || r.plotId === plotFilter),
    [records, plotFilter],
  );

  const stats = useMemo(() => {
    const boxCount = filtered.reduce((a, b) => a + b.boxes.length, 0);
    const byPest = new Map<string, number>();
    for (const r of filtered) for (const b of r.boxes) byPest.set(b.pest, (byPest.get(b.pest) ?? 0) + 1);
    return { boxCount, byPest };
  }, [filtered]);

  return (
    <div>
      <PageHeader
        title="历史记录"
        subtitle="视觉检测全量归档 · 可追溯每一帧的检测框、置信度与病斑面积"
        extra={
          <Button icon={<DownloadOutlined />}>导出 CSV</Button>
        }
      />

      <Row gutter={[12, 12]}>
        <Col xs={24}>
          <Card
            size="small"
            title={
              <Space>
                <HistoryOutlined />
                检测记录
              </Space>
            }
            extra={
              <Space>
                <Segmented
                  size="small"
                  value={plotFilter}
                  onChange={(v) => setPlotFilter(v as string)}
                  options={[
                    { value: 'all', label: '全部地块' },
                    ...['P01', 'P02', 'P03', 'P04', 'P05', 'P06', 'P07', 'P08'].map((p) => ({
                      value: p,
                      label: p,
                    })),
                  ]}
                />
                <Segmented
                  size="small"
                  value={days}
                  onChange={(v) => setDays(v as number)}
                  options={[
                    { value: 1, label: '近 24 小时' },
                    { value: 7, label: '近 7 天' },
                  ]}
                />
              </Space>
            }
          >
            <div style={{ fontSize: 12, color: '#64707C', marginBottom: 10 }}>
              共 <b className="num">{filtered.length}</b> 条检测记录 · 检出目标合计 <b className="num">{stats.boxCount}</b> 处 ·
              主要对象：
              {Array.from(stats.byPest.entries())
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3)
                .map(([k, v]) => `${PEST_META[k as PestKey].name} ${v} 处`)
                .join('、')}
            </div>
            <Table
              size="small"
              rowKey="id"
              dataSource={filtered}
              pagination={{ pageSize: 12, size: 'small' }}
              onRow={(r) => ({
                onClick: () => setActive(r),
                style: { cursor: 'pointer', background: active?.id === r.id ? '#F3F9F5' : undefined },
              })}
              columns={[
                { title: '记录号', dataIndex: 'id', width: 84 },
                {
                  title: '时间',
                  dataIndex: 'time',
                  width: 140,
                  render: (t: string) => <span className="num" style={{ fontSize: 12 }}>{fmtFullTime(t).slice(5)}</span>,
                },
                {
                  title: '地块',
                  dataIndex: 'plotId',
                  width: 120,
                  render: (p: string) => plotById(p).name,
                },
                { title: '摄像头', dataIndex: 'cameraId', width: 96 },
                {
                  title: '来源',
                  dataIndex: 'source',
                  width: 90,
                  render: (s: DetectionRecord['source']) => <Tag style={{ fontSize: 11 }}>{SOURCE_LABEL[s]}</Tag>,
                },
                {
                  title: '检出',
                  dataIndex: 'boxes',
                  width: 170,
                  render: (b: DetectionRecord['boxes']) =>
                    b.length === 0 ? (
                      <span style={{ color: '#8B96A0', fontSize: 12 }}>无目标</span>
                    ) : (
                      <Space size={4} wrap>
                        {b.slice(0, 2).map((x) => (
                          <PestTag key={x.id} pest={x.pest} size="small" />
                        ))}
                        {b.length > 2 && <span style={{ fontSize: 11, color: '#8B96A0' }}>+{b.length - 2}</span>}
                      </Space>
                    ),
                },
                {
                  title: '视觉风险',
                  dataIndex: 'visualRisk',
                  width: 92,
                  render: (v: number) => (
                    <span
                      className="num"
                      style={{ fontWeight: 600, color: v >= 75 ? '#B93A3A' : v >= 55 ? '#C05621' : v >= 35 ? '#9A6D15' : '#2E7D5B' }}
                    >
                      {v}
                    </span>
                  ),
                },
                { title: '推理', dataIndex: 'inferenceMs', width: 76, render: (v: number) => <span className="num">{v}ms</span> },
                {
                  title: '状态',
                  dataIndex: 'handled',
                  width: 88,
                  render: (h: boolean) =>
                    h ? <Tag color="green" style={{ fontSize: 11 }}>已处置</Tag> : <Tag color="orange" style={{ fontSize: 11 }}>待跟进</Tag>,
                },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Drawer
        title={active ? `检测记录 ${active.id}` : ''}
        width={560}
        open={!!active}
        onClose={() => setActive(null)}
        extra={
          active && (
            <Button
              size="small"
              type="primary"
              icon={<ExperimentOutlined />}
              onClick={() => navigate(`/consult?plotId=${active.plotId}`)}
            >
              转入会诊
            </Button>
          )
        }
      >
        {active && (
          <div>
            <FrameAnalysis boxes={active.boxes} seed={active.imageSeed} height={300} label={active.cameraId} />
            <Descriptions size="small" column={1} bordered style={{ marginTop: 14 }} labelStyle={{ width: 90 }}>
              <Descriptions.Item label="拍摄时间">{fmtFullTime(active.time)}</Descriptions.Item>
              <Descriptions.Item label="地块">{plotById(active.plotId).name}（{active.plotId}）</Descriptions.Item>
              <Descriptions.Item label="摄像头">{active.cameraId}</Descriptions.Item>
              <Descriptions.Item label="来源">{SOURCE_LABEL[active.source]}</Descriptions.Item>
              <Descriptions.Item label="推理耗时">{active.inferenceMs} ms</Descriptions.Item>
              <Descriptions.Item label="视觉风险分">{active.visualRisk}</Descriptions.Item>
            </Descriptions>
            <Card size="small" title="检测框明细" style={{ marginTop: 12 }}>
              <Table
                size="small"
                rowKey="id"
                pagination={false}
                dataSource={active.boxes}
                columns={[
                  { title: '类别', dataIndex: 'pest', render: (p: string) => <PestTag pest={p as never} size="small" /> },
                  { title: '置信度', dataIndex: 'confidence', render: (v: number) => <span className="num">{(v * 100).toFixed(1)}%</span> },
                  { title: '病斑面积', dataIndex: 'lesionAreaPct', render: (v: number) => <span className="num">{v.toFixed(2)}%</span> },
                  { title: '程度', dataIndex: 'severity', render: (s: Severity) => <SeverityTag sev={s} /> },
                ]}
              />
            </Card>
          </div>
        )}
      </Drawer>
    </div>
  );
}

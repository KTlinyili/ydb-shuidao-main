import { useEffect, useMemo, useRef, useState } from 'react';
import {
  CaretRightOutlined,
  PauseOutlined,
  ReloadOutlined,
  DesktopOutlined,
} from '@ant-design/icons';
import { Badge, Button, Card, Col, Empty, List, Row, Space, Statistic, Table, Tag, Tooltip } from 'antd';
import type { DetectionRecord, Severity } from '@/types/domain';
import { getLatestDetections, listDetections } from '@/api/services';
import { FrameAnalysis } from '@/components/FrameAnalysis';
import { PageHeader, PestTag, RiskTag, SeverityTag } from '@/components/common';
import { PEST_META } from '@/utils/constants';
import { fmtFullTime, fromNow, SOURCE_LABEL } from '@/utils/format';
import { plotById } from '@/mock/farm';

/**
 * 实时监测页：摄像头通道状态 + 最新推理帧分析 + 实时检测流水。
 * 接入真实视频流后，在通道卡片中嵌入 <video> 播放器即可。
 */
export default function LiveMonitorPage() {
  const [latest, setLatest] = useState<DetectionRecord[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [running, setRunning] = useState(true);
  const [feed, setFeed] = useState<DetectionRecord[]>([]);
  const [tick, setTick] = useState(0);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    getLatestDetections().then((d) => {
      setLatest(d);
      setActiveId(d[0]?.id ?? null);
    });
    listDetections(undefined, 1).then((d) => setFeed(d.slice(0, 24)));
  }, []);

  const active = useMemo(
    () => latest.find((d) => d.id === activeId) ?? latest[0],
    [latest, activeId],
  );

  // 模拟实时推理心跳：检测框轻微抖动
  useEffect(() => {
    if (!running) return;
    timerRef.current = window.setInterval(() => setTick((t) => t + 1), 2200);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [running]);

  const jitterBoxes = useMemo(() => {
    if (!active) return [];
    return active.boxes.map((b, i) => {
      const j = ((Math.sin(tick * 1.7 + i * 2.3) + 1) / 2) * 0.008;
      return {
        ...b,
        bbox: [
          Math.max(0, b.bbox[0] + j),
          Math.max(0, b.bbox[1] + j / 2),
          b.bbox[2],
          b.bbox[3],
        ] as [number, number, number, number],
      };
    });
  }, [active, tick]);

  const summary = useMemo(() => {
    const targets = latest.reduce((a, b) => a + b.boxes.length, 0);
    const avgMs = latest.length
      ? Math.round(latest.reduce((a, b) => a + b.inferenceMs, 0) / latest.length)
      : 0;
    const highRisk = latest.filter((d) => d.visualRisk >= 55).length;
    return { targets, avgMs, highRisk, channels: latest.length };
  }, [latest]);

  if (!latest.length || !active) return null;

  const plot = plotById(active.plotId);

  return (
    <div>
      <PageHeader
        title="实时监测"
        subtitle="RK3588 边缘推理 · 8 路摄像头轮巡 · 每通道 5 秒抽帧检测"
        extra={
          <Space>
            <span style={{ fontSize: 12, color: '#64707C' }}>
              <Badge status="processing" /> 推理服务运行中
            </span>
            <Button
              icon={running ? <PauseOutlined /> : <CaretRightOutlined />}
              onClick={() => setRunning(!running)}
            >
              {running ? '暂停轮巡' : '开始轮巡'}
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => setTick((t) => t + 1)}>
              立即抓拍
            </Button>
          </Space>
        }
      />

      {/* 顶部运行指标 */}
      <Row gutter={[12, 12]}>
        {[
          { title: '在线通道', value: `${summary.channels}/8`, suffix: '路' },
          { title: '当前检出目标', value: summary.targets, suffix: '处' },
          { title: '高风险通道', value: summary.highRisk, suffix: '路' },
          { title: '平均推理耗时', value: summary.avgMs, suffix: 'ms/帧' },
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

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        {/* 通道网格 */}
        <Col xs={24} lg={14}>
          <Card size="small" title="摄像头通道">
            <Row gutter={[10, 10]}>
              {latest.map((d) => {
                const p = plotById(d.plotId);
                const selected = d.id === active.id;
                const level =
                  d.visualRisk >= 75 ? 'critical' : d.visualRisk >= 55 ? 'high' : d.visualRisk >= 35 ? 'medium' : 'low';
                return (
                  <Col key={d.id} span={12}>
                    <div
                      onClick={() => setActiveId(d.id)}
                      style={{
                        cursor: 'pointer',
                        borderRadius: 8,
                        padding: '10px 12px',
                        border: `1.5px solid ${selected ? '#2E8B62' : '#E7ECE9'}`,
                        background: selected ? '#F3F9F5' : '#FCFDFC',
                        boxShadow: selected ? '0 0 0 2px rgba(46,139,98,0.12)' : undefined,
                        transition: 'all .15s',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <Space size={6}>
                          <DesktopOutlined style={{ color: '#64707C', fontSize: 13 }} />
                          <span style={{ fontSize: 12.5, fontWeight: 600 }}>{d.cameraId}</span>
                        </Space>
                        <RiskTag level={level} score={d.visualRisk} />
                      </div>
                      <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 5 }}>
                        {p.name} · {p.stage}
                      </div>
                      <div style={{ display: 'flex', gap: 5, marginTop: 8, alignItems: 'center', flexWrap: 'wrap', minHeight: 20 }}>
                        {d.boxes.length > 0 ? (
                          <>
                            {d.boxes.slice(0, 2).map((b) => (
                              <PestTag key={b.id} pest={b.pest} size="small" />
                            ))}
                            {d.boxes.length > 2 && (
                              <span style={{ fontSize: 10.5, color: '#8B96A0' }}>+{d.boxes.length - 2}</span>
                            )}
                          </>
                        ) : (
                          <span style={{ fontSize: 11, color: '#A5AEB5' }}>本帧未检出病虫害</span>
                        )}
                        <span style={{ marginLeft: 'auto', fontSize: 10.5, color: '#A5AEB5' }} className="num">
                          {fmtFullTime(d.time).slice(11, 19)}
                        </span>
                      </div>
                    </div>
                  </Col>
                );
              })}
            </Row>
          </Card>

          {/* 实时检测流水 */}
          <Card
            size="small"
            title="实时检测流水"
            style={{ marginTop: 12 }}
            extra={<Badge count={feed.length} color="#2E8B62" overflowCount={99} />}
          >
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              <List
                size="small"
                dataSource={feed}
                rowKey="id"
                renderItem={(d) => (
                  <List.Item style={{ padding: '6px 2px' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <span className="num" style={{ fontSize: 11, color: '#8B96A0' }}>
                          {fmtFullTime(d.time).slice(5, 16)}
                        </span>
                        {d.boxes.slice(0, 2).map((b) => (
                          <PestTag key={b.id} pest={b.pest} size="small" />
                        ))}
                        {d.boxes.length > 2 && (
                          <span style={{ fontSize: 11, color: '#8B96A0' }}>+{d.boxes.length - 2}</span>
                        )}
                        <span style={{ marginLeft: 'auto' }}>
                          <RiskTag
                            level={d.visualRisk >= 75 ? 'critical' : d.visualRisk >= 55 ? 'high' : d.visualRisk >= 35 ? 'medium' : 'low'}
                            score={d.visualRisk}
                          />
                        </span>
                      </div>
                      <div style={{ fontSize: 11, color: '#A5AEB5', marginTop: 2 }}>
                        {plotById(d.plotId).name} · {d.cameraId} · {d.inferenceMs}ms
                      </div>
                    </div>
                  </List.Item>
                )}
              />
            </div>
          </Card>
        </Col>

        {/* 选中通道帧分析 */}
        <Col xs={24} lg={10}>
          <Card
            size="small"
            title={`${plot.name} · ${active.cameraId}`}
            extra={
              <Tooltip title="模型推理结果的可视化标注图，非视频画面">
                <Tag style={{ fontSize: 10 }}>最新推理帧</Tag>
              </Tooltip>
            }
          >
            <FrameAnalysis
              boxes={jitterBoxes}
              seed={active.imageSeed}
              height={300}
              label={active.cameraId}
              timeText={fmtFullTime(active.time).slice(11, 19)}
            />
            <div
              style={{
                display: 'flex',
                gap: 16,
                marginTop: 10,
                fontSize: 12,
                color: '#64707C',
                flexWrap: 'wrap',
              }}
            >
              <span>拍摄：{fmtFullTime(active.time)}</span>
              <span>耗时：{active.inferenceMs} ms</span>
              <span>来源：{SOURCE_LABEL[active.source]}</span>
              <span>视觉风险：{active.visualRisk}</span>
            </div>
          </Card>

          <Card size="small" title="检测结果明细" style={{ marginTop: 12 }}>
            {active.boxes.length === 0 ? (
              <Empty description="当前帧未检出病虫害目标" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Table
                size="small"
                rowKey="id"
                pagination={false}
                dataSource={active.boxes}
                columns={[
                  { title: '类别', dataIndex: 'pest', width: 110, render: (p: DetectionRecord['boxes'][number]['pest']) => <PestTag pest={p} /> },
                  {
                    title: '置信度',
                    dataIndex: 'confidence',
                    width: 86,
                    render: (v: number) => <span className="num">{(v * 100).toFixed(1)}%</span>,
                  },
                  {
                    title: '病斑面积',
                    dataIndex: 'lesionAreaPct',
                    width: 92,
                    render: (v: number) => <span className="num">{v.toFixed(2)}%</span>,
                  },
                  { title: '严重程度', dataIndex: 'severity', width: 84, render: (s: Severity) => <SeverityTag sev={s} /> },
                  {
                    title: '边界框',
                    dataIndex: 'bbox',
                    render: (b: number[]) => (
                      <span className="num" style={{ color: '#8B96A0', fontSize: 11 }}>
                        [{b.map((x) => x.toFixed(2)).join(', ')}]
                      </span>
                    ),
                  },
                ]}
              />
            )}
            <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 10, lineHeight: 1.7 }}>
              适发条件参考：{active.boxes.length > 0 ? PEST_META[active.boxes[0].pest].favorable : '—'}
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

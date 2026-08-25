import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  AudioOutlined,
  CheckSquareOutlined,
  DownloadOutlined,
  ExperimentOutlined,
  FileTextOutlined,
  PlusOutlined,
  ReadOutlined,
  SendOutlined,
  SolutionOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Avatar,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Input,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Steps,
  Tag,
  Timeline,
  Typography,
  Upload,
  message,
} from 'antd';
import type { AgentKey, ConsultSession } from '@/types/domain';
import { CONSULT_USE_REAL_API, listDetections, listPlots, runConsult } from '@/api/services';
import { AGENT_NAMES, AGENT_ROLES } from '@/mock/consult';
import { FrameAnalysis } from '@/components/FrameAnalysis';
import { PageHeader, PestTag, RiskTag } from '@/components/common';
import { PEST_META } from '@/utils/constants';
import { fmtFullTime } from '@/utils/format';
import { docById, caseById } from '@/mock/knowledge';
import { plotById } from '@/mock/farm';

const AGENT_COLORS: Record<AgentKey, string> = {
  pest_evidence_officer: '#2E8B62',
  differential_officer: '#5B7FA8',
  plant_protection_expert: '#C0764A',
  field_management_officer: '#8C7CC7',
};

const AGENT_AVATAR_BG: Record<AgentKey, string> = {
  pest_evidence_officer: '#E8F3ED',
  differential_officer: '#EAF0F6',
  plant_protection_expert: '#F7EEE6',
  field_management_officer: '#F0EDF8',
};

/** 多 Agent 会诊页：四专家两轮会诊 → 结论 → 报告。 */
export default function ConsultPage() {
  const [searchParams] = useSearchParams();
  const [plotId, setPlotId] = useState(searchParams.get('plotId') ?? 'P01');
  const [plots, setPlots] = useState<Awaited<ReturnType<typeof listPlots>>>([]);
  const [detections, setDetections] = useState<Awaited<ReturnType<typeof listDetections>>>([]);
  const [detectionId, setDetectionId] = useState<string | undefined>();
  const [complaint, setComplaint] = useState(
    '东区 1 号田拔节期稻株下位叶出现梭形褐斑，部分带灰绿色霉层，近一周连续阴雨，请会诊是否稻瘟病并给出防治方案。',
  );
  const [useKb, setUseKb] = useState(true);
  const [useCase, setUseCase] = useState(true);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState<string>();
  const [waitPct, setWaitPct] = useState(0);

  const [session, setSession] = useState<ConsultSession | null>(null);
  const [visibleTurns, setVisibleTurns] = useState(0);
  const [phase, setPhase] = useState<'idle' | 'running' | 'done'>('idle');
  const [reportOpen, setReportOpen] = useState(false);
  const timers = useRef<number[]>([]);

  useEffect(() => {
    listPlots().then(setPlots);
  }, []);
  useEffect(() => {
    listDetections(plotId, 3).then((d) => {
      setDetections(d);
      setDetectionId(d.find((x) => x.boxes.length > 0)?.id ?? d[0]?.id);
    });
  }, [plotId]);

  useEffect(
    () => () => {
      timers.current.forEach((t) => {
        window.clearTimeout(t);
        window.clearInterval(t);
      });
      if (imageUrl) URL.revokeObjectURL(imageUrl);
    },
    [imageUrl],
  );

  /** 仅本地暂存照片，不自动上传；由“启动会诊”统一提交到后端 */
  const onPickImage = (file: File) => {
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageFile(file);
    setImageUrl(URL.createObjectURL(file));
    return false;
  };

  const selectedDet = useMemo(
    () => detections.find((d) => d.id === detectionId),
    [detections, detectionId],
  );

  const startConsult = async () => {
    if (CONSULT_USE_REAL_API && !imageFile) {
      message.warning('请先上传一张待会诊的田间照片');
      return;
    }
    setPhase('running');
    setSession(null);
    setVisibleTurns(0);
    setWaitPct(0);
    // 真实后端推理约 20~60 秒，等待期间用缓慢爬升的进度条提示
    const waiter = window.setInterval(() => setWaitPct((p) => Math.min(92, p + 1)), 600);
    timers.current.push(waiter);
    try {
      const s = await runConsult({
        plotId,
        detectionId,
        complaint,
        useKnowledgeBase: useKb,
        useCaseLibrary: useCase,
        image: imageFile ?? undefined,
      });
      setSession(s);
      // 逐轮展示 8 个 Agent 发言
      for (let i = 1; i <= s.turns.length; i++) {
        timers.current.push(
          window.setTimeout(() => {
            setVisibleTurns(i);
            if (i === s.turns.length) setPhase('done');
          }, i * 420),
        );
      }
    } catch (e) {
      setPhase('idle');
      message.error(e instanceof Error ? e.message : '会诊失败，请稍后重试');
    } finally {
      window.clearInterval(waiter);
    }
  };

  const progressPct =
    phase === 'idle'
      ? 0
      : phase === 'done'
        ? 100
        : session
          ? Math.min(96, visibleTurns * 12)
          : waitPct;

  return (
    <div>
      <PageHeader
        title="智能会诊"
        subtitle="四专家多轮会诊：病虫害证据官 → 鉴别诊断官 → 植保专家 → 田间管理官（两轮）"
        extra={
          session && phase === 'done' ? (
            <Button icon={<FileTextOutlined />} onClick={() => setReportOpen(true)}>
              查看诊断报告
            </Button>
          ) : undefined
        }
      />

      <Row gutter={[12, 12]}>
        {/* 左侧：会诊发起 */}
        <Col xs={24} lg={7}>
          <Card size="small" title={<Space><SolutionOutlined /> 发起会诊</Space>}>
            <Descriptions size="small" column={1} labelStyle={{ width: 64 }}>
              <Descriptions.Item label="地块">
                <Select
                  size="small"
                  style={{ width: '100%' }}
                  value={plotId}
                  onChange={setPlotId}
                  options={plots.map((p) => ({ value: p.id, label: `${p.id} ${p.name}` }))}
                />
              </Descriptions.Item>
              <Descriptions.Item label="检测帧">
                <Select
                  size="small"
                  style={{ width: '100%' }}
                  value={detectionId}
                  onChange={setDetectionId}
                  options={detections.slice(0, 8).map((d) => ({
                    value: d.id,
                    label: `${d.id} · ${d.boxes.length} 目标 · 风险${d.visualRisk}`,
                  }))}
                />
              </Descriptions.Item>
            </Descriptions>
            <Divider style={{ margin: '10px 0' }} />
            <div style={{ fontSize: 12, color: '#64707C', marginBottom: 6 }}>
              田间照片{CONSULT_USE_REAL_API ? '（必传，真实 AI 会诊对象）' : '（选填）'}
            </div>
            <Upload accept="image/*" showUploadList={false} beforeUpload={onPickImage}>
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt="待会诊田间照片"
                  style={{ width: 88, height: 88, objectFit: 'cover', borderRadius: 8 }}
                />
              ) : (
                <div
                  style={{
                    width: 88,
                    height: 88,
                    border: '1px dashed #C6D2CB',
                    borderRadius: 8,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#8B96A0',
                    fontSize: 11,
                    background: '#FCFDFC',
                  }}
                >
                  <PlusOutlined style={{ fontSize: 18, marginBottom: 4 }} />
                  上传照片
                </div>
              )}
            </Upload>
            {imageFile && (
              <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 6 }}>{imageFile.name}</div>
            )}
            <div style={{ fontSize: 12, color: '#64707C', marginBottom: 6 }}>田间主诉与观察描述</div>
            <Input.TextArea
              rows={5}
              value={complaint}
              onChange={(e) => setComplaint(e.target.value)}
              maxLength={300}
              showCount
            />
            <Space style={{ marginTop: 10 }} direction="vertical" size={4}>
              <Checkbox checked={useKb} onChange={(e) => setUseKb(e.target.checked)}>
                <Space size={4}>
                  <ReadOutlined style={{ color: '#2E8B62' }} /> 检索植保知识库（RAG）
                </Space>
              </Checkbox>
              <Checkbox checked={useCase} onChange={(e) => setUseCase(e.target.checked)}>
                <Space size={4}>
                  <CheckSquareOutlined style={{ color: '#2E8B62' }} /> 匹配水稻病例库
                </Space>
              </Checkbox>
            </Space>
            <Button
              type="primary"
              block
              icon={<ExperimentOutlined />}
              style={{ marginTop: 14 }}
              loading={phase === 'running'}
              disabled={!detectionId || !complaint.trim() || (CONSULT_USE_REAL_API && !imageFile)}
              onClick={startConsult}
            >
              启动多 Agent 会诊
            </Button>
            {phase === 'running' && (
              <div style={{ marginTop: 10 }}>
                <Progress percent={progressPct} size="small" strokeColor="#2E8B62" />
                <div style={{ fontSize: 11.5, color: '#8B96A0', lineHeight: 1.8 }}>
                  {!session && CONSULT_USE_REAL_API ? (
                    '已提交真实多专家会诊：照片上传 → 图像分析 → 多 Agent 两轮推理 → 报告生成，约需 20~60 秒…'
                  ) : (
                    <>
                      {visibleTurns < 2 && '第一轮 · 假设构建层：证据官提取征象，鉴别官校验必要条件…'}
                      {visibleTurns >= 2 && visibleTurns < 4 && '第一轮 · 决策层：植保专家制定方案，田间管理官给出环境措施…'}
                      {visibleTurns >= 4 && visibleTurns < 8 && '第二轮 · 复核与收敛：补充证据、修正置信、完善处置路径…'}
                      {visibleTurns >= 8 && '生成会诊结论与结构化报告…'}
                    </>
                  )}
                </div>
              </div>
            )}
          </Card>

          {selectedDet && (
            <Card size="small" title={`关联检测 ${selectedDet.id}`} style={{ marginTop: 12 }}>
              <FrameAnalysis
                boxes={selectedDet.boxes}
                seed={selectedDet.imageSeed}
                height={190}
                label={`${selectedDet.cameraId}`}
              />
              <div style={{ fontSize: 11.5, color: '#8B96A0', marginTop: 8, lineHeight: 1.7 }}>
                拍摄：{fmtFullTime(selectedDet.time)}
                <br />
                检出：{selectedDet.boxes.length} 处 · 视觉风险 {selectedDet.visualRisk} · 推理 {selectedDet.inferenceMs}ms
              </div>
            </Card>
          )}

          {session && session.kbHits.length > 0 && (
            <Card size="small" title="知识库检索命中" style={{ marginTop: 12 }}>
              {session.kbHits.map((h) => (
                <div key={h.docId} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Tag color="green" style={{ fontSize: 10 }}>{(h.score * 100).toFixed(0)}%</Tag>
                    <span style={{ fontSize: 12.5, fontWeight: 500 }}>{h.title}</span>
                  </div>
                  <div style={{ fontSize: 11.5, color: '#8B96A0', marginTop: 2 }}>{h.snippet}</div>
                </div>
              ))}
            </Card>
          )}
        </Col>

        {/* 中间：会诊过程 */}
        <Col xs={24} lg={10}>
          <Card size="small" title="会诊过程" extra={session && <Tag>{session.id}</Tag>}>
            {!session && phase !== 'running' && (
              <Empty description="配置左侧参数后启动会诊" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 60 }} />
            )}
            {phase === 'running' && !session && (
              <div style={{ textAlign: 'center', padding: '80px 0' }}>
                <Spin size="large" />
                <div style={{ marginTop: 16, color: '#64707C', fontSize: 13 }}>
                  {CONSULT_USE_REAL_API ? '真实多专家推理中，约需 20~60 秒…' : '正在构建会诊上下文…'}
                </div>
              </div>
            )}
            {session && (
              <>
                <Steps
                  size="small"
                  current={Math.min(2, Math.floor(visibleTurns / 4))}
                  style={{ marginBottom: 14, display: visibleTurns >= 8 ? 'none' : 'flex' }}
                  items={[
                    { title: '第一轮会诊', description: '假设构建与初步决策' },
                    { title: '第二轮会诊', description: '复核证据与收敛' },
                    { title: '生成结论', description: '结构化报告' },
                  ]}
                />
                <Timeline
                  items={session.turns.slice(0, visibleTurns).map((t) => ({
                    dot: (
                      <Avatar
                        size={22}
                        style={{
                          background: AGENT_AVATAR_BG[t.agent],
                          color: AGENT_COLORS[t.agent],
                          fontSize: 11,
                          fontWeight: 600,
                        }}
                      >
                        {AGENT_NAMES[t.agent].slice(0, 1)}
                      </Avatar>
                    ),
                    children: (
                      <div
                        className="agent-fields"
                        style={{
                          border: '1px solid #EEF1EF',
                          borderRadius: 8,
                          padding: '10px 12px',
                          background: '#FCFDFC',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                          <span style={{ fontWeight: 600, fontSize: 13, color: AGENT_COLORS[t.agent] }}>
                            {AGENT_NAMES[t.agent]}
                          </span>
                          <Tag style={{ fontSize: 10 }}>第 {t.round} 轮</Tag>
                          <span style={{ fontSize: 11, color: '#A5AEB5', marginLeft: 'auto' }}>{t.latencyMs}ms</span>
                        </div>
                        <div style={{ fontSize: 11.5, color: '#8B96A0', marginBottom: 6 }}>{AGENT_ROLES[t.agent]}</div>
                        {t.fields.map((f) => (
                          <div key={f.label} style={{ marginBottom: 6 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#4A5560', marginBottom: 3 }}>
                              {f.label}
                            </div>
                            {f.items.map((item, i) => (
                              <div key={i} className="agent-field-item">
                                {item}
                              </div>
                            ))}
                          </div>
                        ))}
                        {t.citations.length > 0 && (
                          <div style={{ fontSize: 11, color: '#A5AEB5', marginTop: 4 }}>
                            引用：{t.citations.join('；')}
                          </div>
                        )}
                      </div>
                    ),
                  }))}
                />
                {phase === 'done' && (
                  <Alert
                    type="success"
                    showIcon
                    message="会诊完成：结论已生成"
                    description={
                      <span style={{ fontSize: 12 }}>
                        共 {session.turns.length} 轮专家发言，右侧查看结论，或
                        <Button type="link" size="small" onClick={() => setReportOpen(true)}>
                          查看完整报告
                        </Button>
                      </span>
                    }
                  />
                )}
              </>
            )}
          </Card>
        </Col>

        {/* 右侧：结论 */}
        <Col xs={24} lg={7}>
          <Card size="small" title="会诊结论">
            {session?.conclusion ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <PestTag pest={session.conclusion.diagnosis} />
                  <RiskTag level={session.conclusion.riskLevel} />
                  <span className="num" style={{ fontSize: 12, color: '#64707C' }}>
                    置信 {(session.conclusion.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <Typography.Paragraph style={{ fontSize: 12.5, color: '#3D474F' }}>
                  {session.conclusion.judgment}
                </Typography.Paragraph>
                <Divider style={{ margin: '8px 0' }} />
                {[
                  { title: '证据说明', items: session.conclusion.evidence },
                  { title: '防治措施', items: session.conclusion.measures },
                  { title: '田间管理建议', items: session.conclusion.fieldAdvice },
                  { title: '后续观察项', items: session.conclusion.observations },
                ].map((blk) => (
                  <div key={blk.title} style={{ marginBottom: 10 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: '#2E8B62', marginBottom: 4 }}>
                      {blk.title}
                    </div>
                    {blk.items.map((it, i) => (
                      <div key={i} className="agent-field-item">
                        {it}
                      </div>
                    ))}
                  </div>
                ))}
                {session.similarCases.length > 0 && (
                  <>
                    <Divider style={{ margin: '8px 0' }} />
                    <div style={{ fontSize: 12, color: '#64707C', marginBottom: 4 }}>相似历史病例</div>
                    {session.similarCases.map((c) => {
                      const rec = caseById(c.caseId);
                      return (
                        <div key={c.caseId} style={{ fontSize: 12, display: 'flex', gap: 6, marginBottom: 3 }}>
                          <span style={{ color: '#2E8B62' }}>{c.caseId}</span>
                          <span style={{ color: '#8B96A0' }}>
                            相似度 {(c.similarity * 100).toFixed(0)}% · {rec?.diagnosis ? PEST_META[rec.diagnosis].name : ''}
                          </span>
                        </div>
                      );
                    })}
                  </>
                )}
                <Button
                  block
                  icon={<DownloadOutlined />}
                  style={{ marginTop: 8 }}
                  onClick={() => message.success('报告已导出（模拟）')}
                >
                  导出诊断报告
                </Button>
              </>
            ) : (
              <Empty description="会诊完成后显示结论" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 40 }} />
            )}
          </Card>
        </Col>
      </Row>

      {/* 报告抽屉 */}
      <Drawer
        title={`多 Agent 会诊报告 · ${session?.id ?? ''}`}
        width={520}
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        extra={
          <Button size="small" icon={<DownloadOutlined />} onClick={() => message.success('已下载 Markdown（模拟）')}>
            下载
          </Button>
        }
      >
        {session?.report ? (
          <div className="doc-body">
            <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
              <Descriptions.Item label="地块">
                {plotById(session.plotId).name}（{plotById(session.plotId).variety}）
              </Descriptions.Item>
              <Descriptions.Item label="会诊时间">{fmtFullTime(session.createdAt)}</Descriptions.Item>
              <Descriptions.Item label="关联检测">{session.detectionId}</Descriptions.Item>
              <Descriptions.Item label="结论">
                <PestTag pest={session.conclusion?.diagnosis ?? 'multi'} />
                <RiskTag level={session.conclusion?.riskLevel ?? 'low'} />
              </Descriptions.Item>
            </Descriptions>
            {session.report.map((sec) => (
              <div key={sec.heading} style={{ marginBottom: 14 }}>
                <Typography.Title level={5} style={{ fontSize: 14 }}>
                  {sec.heading}
                </Typography.Title>
                <p style={{ whiteSpace: 'pre-wrap' }}>{sec.body}</p>
              </div>
            ))}
          </div>
        ) : (
          <Empty />
        )}
      </Drawer>
    </div>
  );
}

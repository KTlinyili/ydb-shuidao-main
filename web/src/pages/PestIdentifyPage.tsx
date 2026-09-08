import { useMemo, useRef, useState } from 'react';
import {
  ExperimentOutlined,
  FileTextOutlined,
  InboxOutlined,
  MedicineBoxOutlined,
  PictureOutlined,
  VideoCameraOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Flex,
  Input,
  Progress,
  Row,
  Select,
  Space,
  Table,
  Tabs,
  Tag,
  Upload,
  message,
} from 'antd';
import type { UploadFile } from 'antd';
import type { DetectionBox, PestKey, Severity } from '@/types/domain';
import { FrameAnalysis } from '@/components/FrameAnalysis';
import { PageHeader, PestTag, SeverityTag } from '@/components/common';
import { PEST_META, VISION_MODEL } from '@/utils/constants';
import { makeRng } from '@/mock/random';
import { severityToScore } from '@/utils/risk';
import { plots } from '@/mock/farm';
import { classifyImage, diagnoseByText } from '@/api/services';
import type { TextDiagnosisResult } from '@/api/services';
import { USE_MOCK } from '@/api/services';

const { TextArea } = Input;

interface SimResult {
  boxes: DetectionBox[];
  seed: number;
  inferenceMs: number;
}

function simulateInference(fileName: string, hint?: PestKey): SimResult {
  const seed = Array.from(fileName).reduce((a, c) => a + c.charCodeAt(0) * 7, 9000);
  const r = makeRng(seed);
  const n = r.int(1, 5);
  const pool: PestKey[] = hint
    ? [hint, hint, 'brown_spot', 'rice_planthopper']
    : ['rice_blast', 'sheath_blight', 'brown_spot', 'rice_planthopper', 'rice_leaf_roller'];
  const boxes: DetectionBox[] = [];
  for (let i = 0; i < n; i++) {
    const pest = r.pick(pool);
    const w = r.float(0.07, 0.3);
    const h = r.float(0.08, 0.26);
    const x = r.float(0.03, 0.94 - w);
    const y = r.float(0.1, 0.9 - h);
    const conf = r.float(0.64, 0.97, 3);
    const sev = conf > 0.9 ? '严重' : conf > 0.82 ? '偏重' : conf > 0.73 ? '中等' : '轻微';
    boxes.push({
      id: `U${i}`,
      pest,
      confidence: conf,
      lesionAreaPct: r.float(0.5, 12, 2),
      severity: sev as Severity,
      bbox: [x, y, w, h],
    });
  }
  return { boxes, seed, inferenceMs: r.int(33, 48) };
}

const SAMPLE_IMAGES: { name: string; desc: string; hint: PestKey; seed: number }[] = [
  { name: 'P01-叶片近景-稻瘟病疑似.jpg', desc: '东区 1 号田 · 叶部梭形病斑', hint: 'rice_blast', seed: 7101 },
  { name: 'P03-叶鞘特写-云纹状斑.jpg', desc: '东区 3 号田 · 叶鞘云纹斑', hint: 'sheath_blight', seed: 7303 },
  { name: 'P06-茎基部-虫体群集.jpg', desc: '西区 2 号田 · 茎基虫体', hint: 'rice_planthopper', seed: 7606 },
  { name: 'P07-功能叶-纵缀虫苞.jpg', desc: '西区 3 号田 · 叶片虫苞', hint: 'rice_leaf_roller', seed: 7707 },
];

const RISK_TAG_COLOR: Record<string, string> = {
  low: 'green',
  medium: 'gold',
  high: 'orange',
  critical: 'red',
};
const RISK_LABEL: Record<string, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重',
};

/** ===== 文字诊断标签页 ===== */
function TextDiagnosisTab() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TextDiagnosisResult | null>(null);

  const handleDiagnose = async () => {
    if (!text.trim()) {
      message.warning('请输入症状描述');
      return;
    }
    setLoading(true);
    try {
      const res = await diagnoseByText(text);
      setResult(res);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '诊断失败');
    } finally {
      setLoading(false);
    }
  };

  const sampleTexts = [
    '叶片出现褐色梭形病斑，中央灰白，边缘褐色',
    '叶鞘有云纹状灰白斑，基部腐烂',
    '茎基部有褐色虫体群集，叶片黄化',
  ];

  return (
    <div>
      <Card size="small" title="症状描述输入">
        <TextArea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          placeholder="请描述您观察到的水稻症状，例如：叶片出现褐色斑点，叶鞘有云纹状病斑…"
          maxLength={500}
          showCount
        />
        <Space style={{ marginTop: 12 }} wrap>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            loading={loading}
            onClick={handleDiagnose}
          >
            开始分析
          </Button>
        </Space>
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11.5, color: '#8B96A0', marginBottom: 6 }}>示例描述（点击填入）</div>
          {sampleTexts.map((s, i) => (
            <div
              key={i}
              onClick={() => setText(s)}
              style={{
                cursor: 'pointer',
                padding: '6px 10px',
                borderRadius: 6,
                border: '1px solid #E7ECE9',
                background: '#FCFDFC',
                fontSize: 12,
                color: '#4A5560',
                marginBottom: 4,
              }}
            >
              {s}
            </div>
          ))}
        </div>
      </Card>

      {result && (
        <>
          <Card size="small" title="诊断结论" style={{ marginTop: 12 }}>
            <Alert
              type={result.riskLevel === 'critical' || result.riskLevel === 'high' ? 'error' : 'warning'}
              showIcon
              message={result.summary}
              description={
                <Space direction="vertical" size={4}>
                  <div>
                    风险等级：
                    <Tag color={RISK_TAG_COLOR[result.riskLevel]}>
                      {RISK_LABEL[result.riskLevel]}（风险分 {result.riskScore}）
                    </Tag>
                  </div>
                </Space>
              }
            />
          </Card>

          {result.topMatch && (
            <Card size="small" title="主要匹配病害" style={{ marginTop: 12 }}>
              <div style={{ fontSize: 13, marginBottom: 8 }}>
                <span style={{ fontWeight: 600, fontSize: 15 }}>{result.topMatch.diseaseName}</span>
                <span style={{ marginLeft: 8, color: '#8B96A0', fontSize: 12 }}>
                  {result.topMatch.diseaseNameEn}
                </span>
                <Tag color="blue" style={{ marginLeft: 8 }}>
                  匹配度 {(result.topMatch.matchScore * 100).toFixed(0)}%
                </Tag>
              </div>
              <div style={{ fontSize: 12, color: '#64707C', marginBottom: 4 }}>
                命中关键词：
                {result.topMatch.matchedKeywords.map((kw) => (
                  <Tag key={kw} style={{ marginRight: 4 }}>{kw}</Tag>
                ))}
              </div>
              <Divider style={{ margin: '8px 0' }} />
              <div style={{ fontSize: 12, marginBottom: 6 }}>
                <strong>典型症状：</strong>
                <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                  {result.topMatch.symptoms.map((s, i) => (
                    <li key={i} style={{ color: '#4A5560' }}>{s}</li>
                  ))}
                </ul>
              </div>
              <div style={{ fontSize: 12, marginBottom: 6 }}>
                <strong>治疗建议：</strong>
                <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                  {result.topMatch.treatment.map((t, i) => (
                    <li key={i} style={{ color: '#4A5560' }}>{t}</li>
                  ))}
                </ul>
              </div>
              <div style={{ fontSize: 12, marginBottom: 6 }}>
                <strong>预防措施：</strong>
                <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                  {result.topMatch.prevention.map((p, i) => (
                    <li key={i} style={{ color: '#4A5560' }}>{p}</li>
                  ))}
                </ul>
              </div>
              <div style={{ fontSize: 12, color: '#8B96A0' }}>
                适发条件：{result.topMatch.favorable}
              </div>
            </Card>
          )}

          {result.matches.length > 1 && (
            <Card size="small" title="其他可能病害" style={{ marginTop: 12 }}>
              <Table
                size="small"
                rowKey="diseaseKey"
                pagination={false}
                dataSource={result.matches.slice(1)}
                columns={[
                  {
                    title: '病害',
                    dataIndex: 'diseaseName',
                    width: 120,
                    render: (v: string, r: TextDiagnosisResult['matches'][0]) => (
                      <span>{v} <span style={{ color: '#A5AEB5', fontSize: 11 }}>{r.diseaseNameEn}</span></span>
                    ),
                  },
                  {
                    title: '匹配度',
                    dataIndex: 'matchScore',
                    width: 100,
                    render: (v: number) => (
                      <Progress percent={Math.round(v * 100)} size="small" strokeColor="#2E8B62" />
                    ),
                  },
                  {
                    title: '命中关键词',
                    dataIndex: 'matchedKeywords',
                    render: (kws: string[]) => (
                      <Space size={[4, 4]} wrap>
                        {kws.map((k) => <Tag key={k}>{k}</Tag>)}
                      </Space>
                    ),
                  },
                ]}
              />
            </Card>
          )}
        </>
      )}
    </div>
  );
}

/** ===== 图片识别标签页（原有功能） ===== */
function ImageIdentifyTab() {
  const [file, setFile] = useState<UploadFile | null>(null);
  const [fileName, setFileName] = useState('');
  const [activeHint, setActiveHint] = useState<PestKey | undefined>(undefined);
  const [previewSeed, setPreviewSeed] = useState<number | null>(null);
  const [result, setResult] = useState<SimResult | null>(null);
  const [inferencing, setInferencing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [plotId, setPlotId] = useState(plots[0].id);
  const [history, setHistory] = useState<{ name: string; time: string; n: number; top: string }[]>([]);
  const timerRef = useRef<number | null>(null);

  const handleUpload = (f: UploadFile) => {
    setFile(f);
    setFileName(f.name ?? 'upload.jpg');
    setActiveHint(undefined);
    setResult(null);
    setPreviewSeed(Array.from(f.name ?? 'x').reduce((a, c) => a + c.charCodeAt(0) * 7, 9000));
  };

  const pickSample = (s: (typeof SAMPLE_IMAGES)[number]) => {
    setFile({ uid: String(s.seed), name: s.name } as UploadFile);
    setFileName(s.name);
    setActiveHint(s.hint);
    setResult(null);
    setPreviewSeed(s.seed);
  };

  const runInference = async () => {
    if (!file) return;
    setInferencing(true);
    setProgress(0);

    if (!USE_MOCK && file.originFileObj) {
      try {
        const res = await classifyImage(file.originFileObj as File);
        setProgress(100);
        const clsMap: Record<string, PestKey> = {
          brown_spot: 'brown_spot',
          healthy: 'brown_spot',
          leaf_blast: 'rice_blast',
          bacterial_leaf_streak: 'sheath_blight',
        };
        const pest = clsMap[res.top1Class] ?? 'brown_spot';
        const conf = res.top1Confidence;
        const sev = conf > 0.9 ? '严重' : conf > 0.8 ? '偏重' : conf > 0.65 ? '中等' : '轻微';
        const simResult: SimResult = {
          boxes: [{
            id: 'R0',
            pest,
            confidence: conf,
            lesionAreaPct: Math.round(conf * 10 * 100) / 100,
            severity: sev as Severity,
            bbox: [0.1, 0.1, 0.8, 0.8],
          }],
          seed: previewSeed ?? 0,
          inferenceMs: res.inferenceMs,
        };
        setResult(simResult);
        setHistory((h) => [
          {
            name: res.filename,
            time: new Date().toLocaleString('zh-CN', { hour12: false }).slice(5),
            n: 1,
            top: PEST_META[pest].name,
          },
          ...h,
        ].slice(0, 8));
        message.success(`识别完成：${res.top1Class}（${(conf * 100).toFixed(1)}%），耗时 ${res.inferenceMs} ms`);
      } catch (err) {
        message.error(err instanceof Error ? err.message : '识别失败');
      } finally {
        setInferencing(false);
      }
      return;
    }

    timerRef.current = window.setInterval(() => {
      setProgress((p) => {
        if (p >= 92) {
          window.clearInterval(timerRef.current!);
          return 92;
        }
        return p + Math.random() * 18;
      });
    }, 160);
    setTimeout(() => {
      const res = simulateInference(fileName, activeHint);
      window.clearInterval(timerRef.current!);
      setProgress(100);
      setResult(res);
      setInferencing(false);
      setHistory((h) => [
        {
          name: fileName,
          time: new Date().toLocaleString('zh-CN', { hour12: false }).slice(5),
          n: res.boxes.length,
          top: res.boxes.length ? PEST_META[res.boxes[0].pest].name : '无',
        },
        ...h,
      ].slice(0, 8));
      message.success(`推理完成：检出 ${res.boxes.length} 处目标，耗时 ${res.inferenceMs} ms`);
    }, 2200);
  };

  const stats = useMemo(() => {
    if (!result) return null;
    const top = result.boxes.slice().sort((a, b) => b.confidence - a.confidence)[0];
    const area = result.boxes.reduce((a, b) => a + b.lesionAreaPct, 0);
    return { top, area };
  }, [result]);

  return (
    <div>
      <Row gutter={[12, 12]}>
        <Col xs={24} lg={15}>
          <Card size="small" title="图像上传与推理">
            <Flex gap={16} wrap="wrap" align="flex-start">
              <div style={{ width: 300 }}>
                <Upload.Dragger
                  accept="image/*"
                  maxCount={1}
                  showUploadList={false}
                  customRequest={({ file: f }) => handleUpload(f as UploadFile)}
                >
                  <p className="ant-upload-drag-icon" style={{ marginBottom: 6 }}>
                    <InboxOutlined style={{ color: '#2E8B62', fontSize: 34 }} />
                  </p>
                  <p style={{ fontSize: 13, color: '#4A5560', marginBottom: 2 }}>点击或拖拽图片到此处</p>
                  <p style={{ fontSize: 11.5, color: '#8B96A0' }}>
                    支持 JPG / PNG，建议田间近景，单张 ≤ 10 MB
                  </p>
                </Upload.Dragger>
                <Space style={{ marginTop: 12 }} wrap>
                  <Select
                    size="small"
                    value={plotId}
                    onChange={setPlotId}
                    style={{ width: 170 }}
                    options={plots.map((p) => ({ value: p.id, label: `${p.id} ${p.name}` }))}
                  />
                  <Button
                    type="primary"
                    icon={<MedicineBoxOutlined />}
                    loading={inferencing}
                    disabled={!file}
                    onClick={runInference}
                  >
                    开始识别
                  </Button>
                </Space>
                <div style={{ marginTop: 12 }}>
                  <div style={{ fontSize: 11.5, color: '#8B96A0', marginBottom: 6 }}>
                    演示示例（一键载入田间样例帧）
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {SAMPLE_IMAGES.map((s) => (
                      <div
                        key={s.seed}
                        onClick={() => pickSample(s)}
                        style={{
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          gap: 8,
                          padding: '7px 10px',
                          borderRadius: 6,
                          border: `1px solid ${fileName === s.name ? '#2E8B62' : '#E7ECE9'}`,
                          background: fileName === s.name ? '#F3F9F5' : '#FCFDFC',
                          fontSize: 11.5,
                        }}
                      >
                        <span
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: 2,
                            background: PEST_META[s.hint].color,
                            flexShrink: 0,
                          }}
                        />
                        <span style={{ color: '#3D474F', fontWeight: 500 }}>{s.name}</span>
                        <span style={{ color: '#A5AEB5', marginLeft: 'auto' }}>{s.desc}</span>
                      </div>
                    ))}
                  </div>
                </div>
                {inferencing && (
                  <div style={{ marginTop: 12 }}>
                    <Progress percent={Math.round(progress)} size="small" strokeColor="#2E8B62" />
                    <div style={{ fontSize: 11.5, color: '#8B96A0' }}>
                      图像预处理 → NPU 推理中 → NMS 后处理…
                    </div>
                  </div>
                )}
              </div>
              <div style={{ flex: 1, minWidth: 280 }}>
                {previewSeed === null ? (
                  <div
                    style={{
                      height: 240,
                      borderRadius: 8,
                      border: '1px dashed #DCE5DF',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#FAFBFA',
                    }}
                  >
                    <Empty description="上传后显示预览与检测框" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  </div>
                ) : (
                  <FrameAnalysis
                    boxes={result?.boxes ?? []}
                    seed={previewSeed}
                    height={result ? 360 : 240}
                    label={file?.name?.slice(0, 24) ?? '预览'}
                  />
                )}
              </div>
            </Flex>
          </Card>

          {result && (
            <Card size="small" title="检测输出" style={{ marginTop: 12 }}>
              <Table
                size="small"
                rowKey="id"
                pagination={false}
                dataSource={result.boxes}
                columns={[
                  { title: '类别', dataIndex: 'pest', width: 120, render: (p: PestKey) => <PestTag pest={p} /> },
                  {
                    title: '置信度',
                    dataIndex: 'confidence',
                    width: 150,
                    render: (v: number) => (
                      <Progress
                        percent={Math.round(v * 100)}
                        size="small"
                        strokeColor={v > 0.85 ? '#B93A3A' : v > 0.75 ? '#C05621' : '#2E8B62'}
                      />
                    ),
                  },
                  { title: '病斑面积', dataIndex: 'lesionAreaPct', width: 110, render: (v: number) => <span className="num">{v.toFixed(2)}%</span> },
                  { title: '严重程度', dataIndex: 'severity', width: 100, render: (s: Severity) => <SeverityTag sev={s} /> },
                  {
                    title: '为害部位',
                    render: (_, b: DetectionBox) => (
                      <span style={{ fontSize: 12, color: '#64707C' }}>{PEST_META[b.pest].site}</span>
                    ),
                  },
                ]}
              />
            </Card>
          )}
        </Col>

        <Col xs={24} lg={9}>
          {stats && stats.top ? (
            <Card size="small" title="识别结论">
              <div style={{ fontSize: 13, marginBottom: 10 }}>
                主要识别对象：
                <PestTag pest={stats.top.pest} />
                <span style={{ marginLeft: 8, color: '#64707C', fontSize: 12 }}>
                  {PEST_META[stats.top.pest].latin}
                </span>
              </div>
              <Row gutter={12}>
                <Col span={6}>
                  <div style={{ fontSize: 11, color: '#8B96A0' }}>检出目标</div>
                  <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>{result!.boxes.length} 处</div>
                </Col>
                <Col span={6}>
                  <div style={{ fontSize: 11, color: '#8B96A0' }}>最高置信</div>
                  <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>
                    {(stats.top.confidence * 100).toFixed(0)}%
                  </div>
                </Col>
                <Col span={6}>
                  <div style={{ fontSize: 11, color: '#8B96A0' }}>病斑总面积</div>
                  <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>{stats.area.toFixed(1)}%</div>
                </Col>
                <Col span={6}>
                  <div style={{ fontSize: 11, color: '#8B96A0' }}>推理耗时</div>
                  <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>{result!.inferenceMs}ms</div>
                </Col>
              </Row>
              <Divider style={{ margin: '12px 0' }} />
              <Alert
                type={stats.top.severity === '严重' || stats.top.severity === '偏重' ? 'error' : 'warning'}
                showIcon
                message={`严重程度判定：${stats.top.severity}（量化分 ${severityToScore(stats.top.severity)}）`}
                description={
                  <>
                    <div style={{ fontSize: 12, color: '#4A5560', marginBottom: 4 }}>
                      适发条件：{PEST_META[stats.top.pest].favorable}
                    </div>
                    <Button
                      size="small"
                      type="primary"
                      style={{ marginTop: 6 }}
                      icon={<ExperimentOutlined />}
                      onClick={() => window.open(`/consult?plotId=${plotId}`, '_self')}
                    >
                      转入多 Agent 智能会诊
                    </Button>
                  </>
                }
              />
            </Card>
          ) : (
            <Card size="small" title="识别结论">
              <Empty description="完成推理后显示结论" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            </Card>
          )}

          <Card size="small" title="本机识别记录" style={{ marginTop: 12 }}>
            {history.length === 0 ? (
              <Empty description="暂无记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              <Table
                size="small"
                rowKey="time"
                pagination={false}
                dataSource={history}
                columns={[
                  { title: '文件', dataIndex: 'name', ellipsis: true },
                  { title: '时间', dataIndex: 'time', width: 90 },
                  { title: '目标', dataIndex: 'n', width: 60, render: (v: number) => `${v} 处` },
                  { title: '主要对象', dataIndex: 'top', width: 90 },
                ]}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

/** ===== 视频检测标签页 ===== */
function VideoDetectTab() {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<any>(null);
  const [uploading, setUploading] = useState(false);
  const pollRef = useRef<number | null>(null);

  const handleVideoUpload = async (file: File) => {
    setUploading(true);
    setProgress(0);
    setResult(null);
    setStatus('上传中…');

    if (USE_MOCK) {
      // Mock 模式模拟视频处理
      setTimeout(() => {
        const mockJobId = `MOCK${Date.now().toString().slice(-6)}`;
        setJobId(mockJobId);
        setStatus('处理中');
        const timer = setInterval(() => {
          setProgress((p) => {
            if (p >= 100) {
              clearInterval(timer);
              setStatus('完成');
              setResult({
                job_id: mockJobId,
                total_frames: 480,
                processed_frames: 480,
                avg_fps: 24,
                avg_inference_ms: 38,
                class_counts: {
                  rice_blast: 32,
                  sheath_blight: 12,
                  brown_spot: 8,
                },
                output_video_url: null,
              });
              setUploading(false);
              message.success('视频处理完成（Mock）');
              return 100;
            }
            return p + Math.random() * 15;
          });
        }, 400);
      }, 800);
      return;
    }

    try {
      const form = new FormData();
      form.append('file', file);
      form.append('model_id', 'best_cls');
      form.append('confidence_threshold', '0.5');
      const res = await fetch('/api/v1/video/video', { method: 'POST', body: form });
      if (!res.ok) throw new Error(`上传失败：HTTP ${res.status}`);
      const data = await res.json();
      setJobId(data.job_id);
      setStatus(data.status);
      setUploading(false);
      message.success('视频上传成功，开始处理…');
      pollStatus(data.job_id);
    } catch (err) {
      message.error(err instanceof Error ? err.message : '上传失败');
      setUploading(false);
      setStatus('');
    }
  };

  const pollStatus = (jid: string) => {
    pollRef.current = window.setInterval(async () => {
      try {
        const res = await fetch(`/api/v1/video/${jid}/status`);
        const data = await res.json();
        setStatus(data.status);
        setProgress(data.progress || 0);
        if (data.status === 'completed' || data.status === 'done') {
          if (pollRef.current) clearInterval(pollRef.current);
          setResult(data);
          message.success('视频处理完成');
        } else if (data.status === 'failed') {
          if (pollRef.current) clearInterval(pollRef.current);
          message.error(data.error || '处理失败');
        }
      } catch {
        // 忽略轮询错误
      }
    }, 2000);
  };

  const classLabels: Record<string, string> = {
    rice_blast: '稻瘟病',
    sheath_blight: '纹枯病',
    brown_spot: '褐斑病',
    bacterial_leaf_streak: '细菌性条斑病',
    rice_planthopper: '稻飞虱',
    rice_leaf_roller: '稻纵卷叶螟',
  };

  return (
    <div>
      <Card size="small" title="视频检测">
        <Upload.Dragger
          accept="video/*"
          maxCount={1}
          showUploadList={false}
          customRequest={({ file: f }) => handleVideoUpload(f as File)}
        >
          <p className="ant-upload-drag-icon" style={{ marginBottom: 6 }}>
            <VideoCameraOutlined style={{ color: '#2E8B62', fontSize: 34 }} />
          </p>
          <p style={{ fontSize: 13, color: '#4A5560', marginBottom: 2 }}>点击或拖拽视频到此处</p>
          <p style={{ fontSize: 11.5, color: '#8B96A0' }}>
            支持 MP4 / AVI / MOV，逐帧检测，输出标注视频
          </p>
        </Upload.Dragger>

        {(uploading || status) && (
          <div style={{ marginTop: 16 }}>
            <div style={{ fontSize: 12, color: '#4A5560', marginBottom: 6 }}>
              任务 ID：{jobId ?? '处理中…'} | 状态：{status}
            </div>
            <Progress percent={Math.round(progress)} size="small" strokeColor="#2E8B62" />
          </div>
        )}

        {result && (
          <div style={{ marginTop: 16 }}>
            <Row gutter={12}>
              <Col span={6}>
                <div style={{ fontSize: 11, color: '#8B96A0' }}>总帧数</div>
                <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>
                  {result.total_frames ?? result.processed_frames}
                </div>
              </Col>
              <Col span={6}>
                <div style={{ fontSize: 11, color: '#8B96A0' }}>平均 FPS</div>
                <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>
                  {result.avg_fps ?? '—'}
                </div>
              </Col>
              <Col span={6}>
                <div style={{ fontSize: 11, color: '#8B96A0' }}>推理耗时</div>
                <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>
                  {result.avg_inference_ms ?? '—'}ms
                </div>
              </Col>
              <Col span={6}>
                <div style={{ fontSize: 11, color: '#8B96A0' }}>检出类别</div>
                <div className="num" style={{ fontSize: 20, fontWeight: 600 }}>
                  {result.class_counts ? Object.keys(result.class_counts).length : 0}
                </div>
              </Col>
            </Row>
            <Divider style={{ margin: '12px 0' }} />
            {result.class_counts && (
              <Table
                size="small"
                rowKey="cls"
                pagination={false}
                dataSource={Object.entries(result.class_counts).map(([cls, count]) => ({
                  cls,
                  count,
                  name: classLabels[cls] ?? cls,
                }))}
                columns={[
                  { title: '病害类别', dataIndex: 'name', width: 150 },
                  { title: '检出帧数', dataIndex: 'count', width: 100 },
                  {
                    title: '占比',
                    render: (_, r: any) => (
                      <Progress
                        percent={Math.round((r.count / result.total_frames) * 100)}
                        size="small"
                        strokeColor="#2E8B62"
                      />
                    ),
                  },
                ]}
              />
            )}
            {result.output_video_url && (
              <Button
                type="primary"
                style={{ marginTop: 12 }}
                href={result.output_video_url}
              >
                下载标注视频
              </Button>
            )}
          </div>
        )}
      </Card>

      <Card size="small" title="视频检测说明" style={{ marginTop: 12 }}>
        <div style={{ fontSize: 12, color: '#4A5560', lineHeight: 1.9 }}>
          · 上传田间视频后，系统逐帧进行 YOLO 检测
          <br />
          · 输出带标注框、类别名、置信度的视频
          <br />
          · 统计各类病害检出帧数和占比
          <br />
          · 需要检测模型权重（.pt 或 .onnx）支持
        </div>
      </Card>
    </div>
  );
}

/** ===== 主页面 ===== */
export default function PestIdentifyPage() {
  return (
    <div>
      <PageHeader
        title="病虫害识别"
        subtitle={`${VISION_MODEL.name} ${VISION_MODEL.version} · ${VISION_MODEL.inputSize} · ${VISION_MODEL.classes} 类目标 · ${VISION_MODEL.device}`}
      />

      <Tabs
        defaultActiveKey="image"
        size="large"
        items={[
          {
            key: 'image',
            label: (
              <span><PictureOutlined /> 图片识别</span>
            ),
            children: <ImageIdentifyTab />,
          },
          {
            key: 'text',
            label: (
              <span><FileTextOutlined /> 文字诊断</span>
            ),
            children: <TextDiagnosisTab />,
          },
          {
            key: 'video',
            label: (
              <span><VideoCameraOutlined /> 视频检测</span>
            ),
            children: <VideoDetectTab />,
          },
        ]}
      />
    </div>
  );
}

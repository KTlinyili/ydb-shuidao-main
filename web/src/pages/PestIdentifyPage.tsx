import { useMemo, useRef, useState } from 'react';
import {
  ExperimentOutlined,
  InboxOutlined,
  MedicineBoxOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  Empty,
  Flex,
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

/**
 * 病虫害识别页：上传图片 → 模拟 RK3588 视觉推理 → 检测结果。
 * 接入后端后：POST /api/v1/vision/infer（multipart）返回同结构 JSON。
 */
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

/** 演示示例图库：一键载入样例并推理（真实部署时替换为实拍图） */
const SAMPLE_IMAGES: { name: string; desc: string; hint: PestKey; seed: number }[] = [
  { name: 'P01-叶片近景-稻瘟病疑似.jpg', desc: '东区 1 号田 · 叶部梭形病斑', hint: 'rice_blast', seed: 7101 },
  { name: 'P03-叶鞘特写-云纹状斑.jpg', desc: '东区 3 号田 · 叶鞘云纹斑', hint: 'sheath_blight', seed: 7303 },
  { name: 'P06-茎基部-虫体群集.jpg', desc: '西区 2 号田 · 茎基虫体', hint: 'rice_planthopper', seed: 7606 },
  { name: 'P07-功能叶-纵缀虫苞.jpg', desc: '西区 3 号田 · 叶片虫苞', hint: 'rice_leaf_roller', seed: 7707 },
];

export default function PestIdentifyPage() {
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

  const runInference = () => {
    if (!file) return;
    setInferencing(true);
    setProgress(0);
    timerRef.current = window.setInterval(() => {
      setProgress((p) => {
        if (p >= 92) {
          window.clearInterval(timerRef.current!);
          return 92;
        }
        return p + Math.random() * 18;
      });
    }, 160);
    // 模拟 NPU 推理 + 后处理
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
      <PageHeader
        title="病虫害识别"
        subtitle={`${VISION_MODEL.name} ${VISION_MODEL.version} · ${VISION_MODEL.inputSize} · ${VISION_MODEL.classes} 类目标 · ${VISION_MODEL.device}`}
      />

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
                    icon={<ScanOutlinedPrivate />}
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
                      onClick={() =>
                        window.open(
                          `/consult?plotId=${plotId}`,
                          '_self',
                        )
                      }
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

          <Card size="small" title="模型信息" style={{ marginTop: 12 }}>
            <Tabs
              size="small"
              items={[
                {
                  key: 'info',
                  label: '运行参数',
                  children: (
                    <div style={{ fontSize: 12, color: '#4A5560', lineHeight: 1.9 }}>
                      模型：{VISION_MODEL.name} {VISION_MODEL.version}
                      <br />
                      类别文件：{VISION_MODEL.classesFile}
                      <br />
                      输入尺寸：{VISION_MODEL.inputSize}，letterbox 填充
                      <br />
                      量化：INT8（PTQ，RKNN 2.3.0）
                      <br />
                      置信阈值：0.45，NMS IoU 阈值：0.5
                      <br />
                      平均推理：38 ms / 帧（RK3588 NPU 三核）
                    </div>
                  ),
                },
                {
                  key: 'classes',
                  label: '类别清单',
                  children: (
                    <Space size={[4, 4]} wrap>
                      {Object.values(PEST_META).map((m) => (
                        <PestTag key={m.key} pest={m.key} size="small" />
                      ))}
                    </Space>
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

function ScanOutlinedPrivate() {
  return <MedicineBoxOutlined />;
}

import { useState } from 'react';
import {
  BellOutlined,
  CloudUploadOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  RobotOutlined,
  SafetyOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Slider,
  Space,
  Switch,
  Tabs,
  Tag,
  Typography,
  message,
} from 'antd';
import { PageHeader } from '@/components/common';
import { ENDPOINTS, USE_MOCK } from '@/api/services';
import { RISK_WEIGHTS, VISION_MODEL, FARM_INFO } from '@/utils/constants';

/** 系统设置页：预警阈值 / 模型 / Agent / 数据与接口 / 通知。 */
export default function SettingsPage() {
  const [form] = Form.useForm();
  const [weights, setWeights] = useState({ ...RISK_WEIGHTS });
  const [mockMode, setMockMode] = useState(USE_MOCK);
  const [notify, setNotify] = useState({ wecom: true, sms: false, email: true, voice: false });
  const [autoConsult, setAutoConsult] = useState(true);

  const weightSum = Math.round((weights.visual + weights.env + weights.trend) * 100);

  return (
    <div>
      <PageHeader title="系统设置" subtitle="预警策略 · 视觉模型 · 多 Agent · 数据接口 · 消息通知" />

      <Tabs
        items={[
          {
            key: 'risk',
            label: (
              <Space size={6}>
                <DashboardOutlined />
                预警策略
              </Space>
            ),
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={14}>
                  <Card size="small" title="风险融合权重">
                    <div style={{ fontSize: 12, color: '#64707C', marginBottom: 14 }}>
                      综合风险 = 视觉 ×{weights.visual} + 环境 ×{weights.env} + 趋势 ×{weights.trend}
                      <Tag
                        color={weightSum === 100 ? 'green' : 'red'}
                        style={{ marginLeft: 8, fontSize: 11 }}
                      >
                        权重和 {weightSum}%
                      </Tag>
                    </div>
                    {(
                      [
                        { key: 'visual', label: '视觉风险权重（检测框数量、置信度、病斑面积）', max: 0.8 },
                        { key: 'env', label: '环境风险权重（温湿度、土壤含水率适发度）', max: 0.8 },
                        { key: 'trend', label: '趋势风险权重（近 7 日风险斜率）', max: 0.6 },
                      ] as const
                    ).map((w) => (
                      <div key={w.key} style={{ marginBottom: 16 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                          <span style={{ fontSize: 12.5, color: '#4A5560' }}>{w.label}</span>
                          <span className="num" style={{ fontSize: 12 }}>
                            {(weights[w.key] * 100).toFixed(0)}%
                          </span>
                        </div>
                        <Slider
                          min={0}
                          max={w.max}
                          step={0.05}
                          value={weights[w.key]}
                          onChange={(v) => setWeights((s) => ({ ...s, [w.key]: v }))}
                        />
                      </div>
                    ))}
                    <Space>
                      <Button
                        type="primary"
                        size="small"
                        disabled={weightSum !== 100}
                        onClick={() => message.success('风险权重已保存（模拟）')}
                      >
                        保存权重
                      </Button>
                      <Button size="small" onClick={() => setWeights({ ...RISK_WEIGHTS })}>
                        恢复默认
                      </Button>
                    </Space>
                  </Card>
                </Col>
                <Col xs={24} lg={10}>
                  <Card size="small" title="分级预警阈值">
                    <Form
                      form={form}
                      layout="vertical"
                      size="small"
                      initialValues={{ medium: 35, high: 55, critical: 75, cooldown: 4 }}
                    >
                      <Row gutter={12}>
                        {[
                          { name: 'medium', label: '中风险阈值' },
                          { name: 'high', label: '高风险阈值' },
                          { name: 'critical', label: '严重风险阈值' },
                          { name: 'cooldown', label: '同地块冷却（小时）' },
                        ].map((f) => (
                          <Col key={f.name as string} span={12}>
                            <Form.Item name={f.name} label={f.label} style={{ marginBottom: 8 }}>
                              <InputNumber style={{ width: '100%' }} min={0} max={100} />
                            </Form.Item>
                          </Col>
                        ))}
                      </Row>
                      <Button type="primary" onClick={() => message.success('阈值已保存（模拟）')}>
                        保存阈值
                      </Button>
                    </Form>
                    <Divider style={{ margin: '12px 0' }} />
                    <Space direction="vertical" size={6}>
                      <Space size={8}>
                        <Switch size="small" checked={autoConsult} onChange={setAutoConsult} />
                        <span style={{ fontSize: 12.5 }}>高风险预警自动触发多 Agent 会诊</span>
                      </Space>
                      <Typography.Text type="secondary" style={{ fontSize: 11.5 }}>
                        开启后，综合风险 ≥ 高风险阈值时自动创建会诊任务并推送植保专家复核
                      </Typography.Text>
                    </Space>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'model',
            label: (
              <Space size={6}>
                <RobotOutlined />
                视觉模型
              </Space>
            ),
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={12}>
                  <Card size="small" title="边缘推理配置">
                    <Descriptions size="small" column={1} bordered>
                      <Descriptions.Item label="模型">{VISION_MODEL.name} {VISION_MODEL.version}</Descriptions.Item>
                      <Descriptions.Item label="运行设备">{VISION_MODEL.device}</Descriptions.Item>
                      <Descriptions.Item label="输入尺寸">{VISION_MODEL.inputSize}</Descriptions.Item>
                      <Descriptions.Item label="类别数">{VISION_MODEL.classes} 类（与 classes.txt 对齐）</Descriptions.Item>
                      <Descriptions.Item label="RKNN 运行时">2.3.0 · NPU 三核 · INT8</Descriptions.Item>
                    </Descriptions>
                    <Divider style={{ margin: '12px 0' }} />
                    <Form layout="vertical" size="small" initialValues={{ conf: 0.45, iou: 0.5, fps: 2 }}>
                      <Row gutter={12}>
                        <Col span={8}>
                          <Form.Item name="conf" label="置信度阈值">
                            <InputNumber style={{ width: '100%' }} min={0.1} max={0.9} step={0.05} />
                          </Form.Item>
                        </Col>
                        <Col span={8}>
                          <Form.Item name="iou" label="NMS IoU 阈值">
                            <InputNumber style={{ width: '100%' }} min={0.1} max={0.9} step={0.05} />
                          </Form.Item>
                        </Col>
                        <Col span={8}>
                          <Form.Item name="fps" label="巡检帧率（fps）">
                            <InputNumber style={{ width: '100%' }} min={1} max={10} />
                          </Form.Item>
                        </Col>
                      </Row>
                      <Space>
                        <Button type="primary" onClick={() => message.success('已下发到边缘节点（模拟）')}>
                          下发配置
                        </Button>
                        <Button onClick={() => message.info('OTA 升级通道预留')}>
                          模型 OTA 升级
                        </Button>
                      </Space>
                    </Form>
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card size="small" title="模型类别映射（classes.txt）">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
                      {[
                        ['0', 'rice_blast', '稻瘟病'],
                        ['1', 'sheath_blight', '纹枯病'],
                        ['2', 'bacterial_blight', '白叶枯病'],
                        ['3', 'brown_spot', '褐斑病'],
                        ['4', 'bacterial_streak', '细菌性条斑病'],
                        ['5', 'rice_planthopper', '稻飞虱'],
                        ['6', 'rice_leaf_roller', '稻纵卷叶螟'],
                        ['7', 'striped_stem_borer', '二化螟'],
                      ].map(([idx, key, name]) => (
                        <div
                          key={key}
                          style={{
                            display: 'flex',
                            gap: 8,
                            alignItems: 'center',
                            border: '1px solid #EEF1EF',
                            borderRadius: 6,
                            padding: '6px 10px',
                            fontSize: 12,
                          }}
                        >
                          <span className="num" style={{ color: '#8B96A0', width: 14 }}>{idx}</span>
                          <code style={{ color: '#2E8B62', fontSize: 11 }}>{key}</code>
                          <span style={{ marginLeft: 'auto', color: '#4A5560' }}>{name}</span>
                        </div>
                      ))}
                    </div>
                    <Typography.Text type="secondary" style={{ fontSize: 11.5, display: 'block', marginTop: 10 }}>
                      注意：更换检测模型时须保证输出类别顺序与本映射一致，否则前端展示与风险计算将失真。
                    </Typography.Text>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'agent',
            label: (
              <Space size={6}>
                <ExperimentOutlined />
                多 Agent 会诊
              </Space>
            ),
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={14}>
                  <Card size="small" title="专家角色配置">
                    <Form
                      layout="vertical"
                      size="small"
                      initialValues={{
                        rounds: 2,
                        llm: 'ollama',
                        model: 'deepseek-r1:8b',
                        kb: true,
                        cases: true,
                        timeout: 60,
                      }}
                    >
                      <Row gutter={12}>
                        <Col span={6}>
                          <Form.Item name="rounds" label="会诊轮数">
                            <Select options={[1, 2, 3].map((n) => ({ value: n, label: `${n} 轮` }))} />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item name="llm" label="LLM 提供方">
                            <Select
                              options={[
                                { value: 'ollama', label: 'Ollama（本地）' },
                                { value: 'openai', label: 'OpenAI 兼容' },
                                { value: 'dnxapi', label: 'DNXAPI' },
                              ]}
                            />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item name="model" label="模型名称">
                            <Input />
                          </Form.Item>
                        </Col>
                        <Col span={6}>
                          <Form.Item name="timeout" label="单次超时（秒）">
                            <InputNumber style={{ width: '100%' }} min={10} max={300} />
                          </Form.Item>
                        </Col>
                      </Row>
                      <Space direction="vertical">
                        <Form.Item name="kb" valuePropName="checked" style={{ marginBottom: 4 }}>
                          <Switch size="small" checkedChildren="开" unCheckedChildren="关" />
                        </Form.Item>
                        <span style={{ fontSize: 11.5, color: '#8B96A0', marginLeft: -52 }}>
                          启用植保知识库 RAG 检索（knowledge_bases）
                        </span>
                      </Space>
                      <Button type="primary" style={{ marginTop: 8 }} onClick={() => message.success('Agent 配置已保存（模拟）')}>
                        保存配置
                      </Button>
                    </Form>
                  </Card>
                </Col>
                <Col xs={24} lg={10}>
                  <Card size="small" title="专家阵容">
                    {[
                      { name: '病虫害证据官', duty: '图像征象 → 病理语言，构建候选假设', color: '#2E8B62' },
                      { name: '鉴别诊断官', duty: '魔鬼代言人：校验必要条件、挖掘矛盾', color: '#5B7FA8' },
                      { name: '植保专家', duty: '药剂选择、施药时机、防治方案', color: '#C0764A' },
                      { name: '田间管理官', duty: '水肥调控、农事安排、复查节点', color: '#8C7CC7' },
                    ].map((a) => (
                      <div key={a.name} style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #F0F2F1' }}>
                        <span style={{ width: 8, height: 8, borderRadius: 2, background: a.color, flexShrink: 0 }} />
                        <span style={{ fontSize: 13, fontWeight: 500, width: 96 }}>{a.name}</span>
                        <span style={{ fontSize: 12, color: '#64707C' }}>{a.duty}</span>
                      </div>
                    ))}
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'data',
            label: (
              <Space size={6}>
                <DatabaseOutlined />
                数据与接口
              </Space>
            ),
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={12}>
                  <Card size="small" title="数据源模式">
                    <Space direction="vertical" size={10}>
                      <Space size={10}>
                        <Switch checked={mockMode} onChange={setMockMode} />
                        <span style={{ fontSize: 13 }}>Mock 演示模式</span>
                        <Tag color={mockMode ? 'orange' : 'green'}>{mockMode ? '使用本地模拟数据' : '请求后端 API'}</Tag>
                      </Space>
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        当前前端通过 src/api/services.ts 统一取数。接入 FastAPI 后端时：
                        将 USE_MOCK 置为 false 并按 ENDPOINTS 注释实现 fetch 封装，页面无需改动。
                        Vite 开发代理已将 /api 转发到 127.0.0.1:8000。
                      </Typography.Text>
                      <Divider style={{ margin: '2px 0' }} />
                      <Button icon={<CloudUploadOutlined />} onClick={() => message.info('数据备份通道预留')}>
                        立即备份
                      </Button>
                    </Space>
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card size="small" title="后端接口契约（预留）">
                    <div style={{ fontSize: 11.5, lineHeight: 2 }}>
                      {Object.entries(ENDPOINTS).map(([k, v]) => (
                        <div key={k} style={{ display: 'flex', gap: 8 }}>
                          <code style={{ color: '#5B7FA8', width: 96 }}>{k}</code>
                          <code style={{ color: '#64707C' }}>{v}</code>
                        </div>
                      ))}
                      <div style={{ display: 'flex', gap: 8 }}>
                        <code style={{ color: '#5B7FA8', width: 96 }}>detectionStream</code>
                        <code style={{ color: '#64707C' }}>ws://…/api/v1/stream/detection</code>
                      </div>
                    </div>
                  </Card>
                </Col>
              </Row>
            ),
          },
          {
            key: 'notify',
            label: (
              <Space size={6}>
                <BellOutlined />
                消息通知
              </Space>
            ),
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={14}>
                  <Card size="small" title="通知渠道">
                    {(
                      [
                        { key: 'wecom', name: '企业微信应用消息', desc: '推送给地块管理员与植保服务队群' },
                        { key: 'sms', name: '短信', desc: '仅严重风险预警，每日限额 50 条' },
                        { key: 'email', name: '邮件日报', desc: '每日 08:00 汇总 24 小时预警与风险变化' },
                        { key: 'voice', name: '电话语音', desc: '严重风险且 15 分钟未接单时升级呼叫' },
                      ] as const
                    ).map((c) => (
                      <div key={c.key} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 0', borderBottom: '1px solid #F0F2F1' }}>
                        <Switch
                          size="small"
                          checked={notify[c.key]}
                          onChange={(v) => setNotify((s) => ({ ...s, [c.key]: v }))}
                        />
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 500 }}>{c.name}</div>
                          <div style={{ fontSize: 11.5, color: '#8B96A0' }}>{c.desc}</div>
                        </div>
                      </div>
                    ))}
                    <Button type="primary" size="small" style={{ marginTop: 12 }} onClick={() => message.success('通知配置已保存（模拟）')}>
                      保存配置
                    </Button>
                  </Card>
                </Col>
                <Col xs={24} lg={10}>
                  <Card size="small" title="预警推送模板（企业微信）">
                    <div
                      style={{
                        border: '1px solid #E4E9E6',
                        borderRadius: 8,
                        padding: 12,
                        background: '#FAFBFA',
                        fontSize: 12.5,
                        lineHeight: 1.9,
                        color: '#3D474F',
                      }}
                    >
                      【稻影知微 · {FARM_INFO.name}】
                      <br />
                      严重风险预警 W0031
                      <br />
                      地块：东区 1 号田（P01）
                      <br />
                      对象：稻瘟病 · 综合风险 78 分
                      <br />
                      触发：视觉风险 78（稻瘟检出 4 处）；环境风险 70
                      <br />
                      处置：请于 24 小时内组织防治，方案见预警详情。
                      <br />
                      <span style={{ color: '#8B96A0' }}>—— 点击卡片跳转预警详情页</span>
                    </div>
                  </Card>
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </div>
  );
}

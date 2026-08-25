import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { BookOutlined, FileSearchOutlined, SearchOutlined, TagsOutlined } from '@ant-design/icons';
import {
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Input,
  List,
  Progress,
  Row,
  Segmented,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import type { CaseRecord, KnowledgeDoc, PestKey, Severity } from '@/types/domain';
import { listCases, searchKnowledge } from '@/api/services';
import { PageHeader, PestTag, SeverityTag } from '@/components/common';
import { PEST_META, PEST_ORDER } from '@/utils/constants';
import { fmtTime } from '@/utils/format';
import { plotById } from '@/mock/farm';

/**
 * 知识库页：植保知识库（RAG 检索） + 水稻病例库。
 * 接入后端：GET /api/v1/knowledge/docs?q= 与 GET /api/v1/cases。
 */
export default function KnowledgePage() {
  const [searchParams] = useSearchParams();
  const [tab, setTab] = useState<'kb' | 'cases'>('kb');
  const [query, setQuery] = useState(searchParams.get('q') ?? '');
  const [input, setInput] = useState(query);
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [activeDoc, setActiveDoc] = useState<KnowledgeDoc | null>(null);
  const [activeCase, setActiveCase] = useState<CaseRecord | null>(null);
  const [category, setCategory] = useState<string>('all');

  useEffect(() => {
    searchKnowledge(query).then((d) => {
      setDocs(d);
      setActiveDoc(d[0] ?? null);
    });
    listCases().then(setCases);
  }, [query]);

  const filteredCases = useMemo(
    () => (category === 'all' ? cases : cases.filter((c) => c.diagnosis === category)),
    [cases, category],
  );

  return (
    <div>
      <PageHeader
        title="知识库"
        subtitle="植保知识库 8 个条目 · 水稻病例库 6 例 · 支持语义检索（RAG，接入后端后生效）"
      />

      <Tabs
        activeKey={tab}
        onChange={(k) => setTab(k as typeof tab)}
        items={[
          {
            key: 'kb',
            label: (
              <Space size={6}>
                <BookOutlined />
                植保知识库
              </Space>
            ),
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={8}>
                  <Card size="small">
                    <Input.Search
                      placeholder="检索病虫害知识，如：稻瘟病 防治 / 三环唑 / 晒田"
                      prefix={<SearchOutlined style={{ color: '#9AA6AF' }} />}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onSearch={setQuery}
                      enterButton
                      allowClear
                    />
                    {query && (
                      <div style={{ fontSize: 11.5, color: '#8B96A0', margin: '8px 2px 4px' }}>
                        「{query}」命中 {docs.length} 条
                        <Button type="link" size="small" style={{ paddingInline: 6 }} onClick={() => { setQuery(''); setInput(''); }}>
                          清空
                        </Button>
                      </div>
                    )}
                    <Divider style={{ margin: '10px 0' }} />
                    <div style={{ fontSize: 12, color: '#64707C', marginBottom: 6 }}>
                      <TagsOutlined /> 按病虫害筛选
                    </div>
                    <Space size={[4, 6]} wrap>
                      <Tag.CheckableTag checked={!query} onChange={() => { setQuery(''); setInput(''); }}>
                        全部
                      </Tag.CheckableTag>
                      {PEST_ORDER.map((k) => (
                        <Tag.CheckableTag
                          key={k}
                          checked={query === PEST_META[k].name}
                          onChange={(checked) => {
                            const q = checked ? PEST_META[k].name : '';
                            setQuery(q);
                            setInput(q);
                          }}
                        >
                          {PEST_META[k].name}
                        </Tag.CheckableTag>
                      ))}
                    </Space>
                    <Divider style={{ margin: '10px 0' }} />
                    <List
                      dataSource={docs}
                      rowKey="id"
                      renderItem={(d) => (
                        <List.Item
                          style={{
                            padding: '9px 10px',
                            cursor: 'pointer',
                            borderRadius: 6,
                            border:
                              activeDoc?.id === d.id
                                ? '1px solid #CBE5D6'
                                : '1px solid transparent',
                            background: activeDoc?.id === d.id ? '#F0F7F2' : undefined,
                          }}
                          onClick={() => setActiveDoc(d)}
                        >
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                              {d.score !== undefined && (
                                <Progress
                                  type="circle"
                                  size={26}
                                  percent={Math.round(d.score * 100)}
                                  strokeColor="#2E8B62"
                                  format={(p) => <span style={{ fontSize: 8 }}>{p}</span>}
                                  style={{ marginRight: 2 }}
                                />
                              )}
                              <span style={{ fontSize: 13, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {d.title}
                              </span>
                            </div>
                            <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 3 }}>
                              {d.source} · 更新 {fmtTime(d.updatedAt, 'YYYY-MM-DD')}
                            </div>
                          </div>
                        </List.Item>
                      )}
                    />
                  </Card>
                </Col>
                <Col xs={24} lg={16}>
                  {activeDoc ? (
                    <Card
                      size="small"
                      title={
                        <Space>
                          <FileSearchOutlined style={{ color: '#2E8B62' }} />
                          {activeDoc.title}
                        </Space>
                      }
                      extra={
                        <Space size={6} wrap>
                          {activeDoc.tags.map((t) => (
                            <Tag key={t} style={{ fontSize: 11 }}>
                              {t}
                            </Tag>
                          ))}
                        </Space>
                      }
                    >
                      <Descriptions size="small" column={3} style={{ marginBottom: 12 }}>
                        <Descriptions.Item label="类别">
                          {activeDoc.category === 'general' ? (
                            <Tag>综合</Tag>
                          ) : (
                            <PestTag pest={activeDoc.category} size="small" />
                          )}
                        </Descriptions.Item>
                        <Descriptions.Item label="来源">{activeDoc.source}</Descriptions.Item>
                        <Descriptions.Item label="更新时间">
                          {fmtTime(activeDoc.updatedAt, 'YYYY-MM-DD')}
                        </Descriptions.Item>
                      </Descriptions>
                      <div className="doc-body">
                        {activeDoc.sections.map((s) => (
                          <div key={s.heading} style={{ marginBottom: 14 }}>
                            <Typography.Title level={5} style={{ fontSize: 14, marginBottom: 6 }}>
                              {s.heading}
                            </Typography.Title>
                            <p>{s.body}</p>
                          </div>
                        ))}
                      </div>
                    </Card>
                  ) : (
                    <Card size="small">
                      <Empty description="未检索到相关条目" style={{ marginTop: 60 }} />
                    </Card>
                  )}
                </Col>
              </Row>
            ),
          },
          {
            key: 'cases',
            label: (
              <Space size={6}>
                <BookOutlined />
                水稻病例库
              </Space>
            ),
            children: (
              <Row gutter={[12, 12]}>
                <Col xs={24} lg={15}>
                  <Card
                    size="small"
                    title="历史病例"
                    extra={
                      <Segmented
                        size="small"
                        value={category}
                        onChange={(v) => setCategory(v as string)}
                        options={[
                          { value: 'all', label: '全部' },
                          { value: 'verified', label: '已核实' },
                          { value: 'unverified', label: '待核实' },
                        ]}
                      />
                    }
                  >
                    <Table
                      size="small"
                      rowKey="id"
                      pagination={false}
                      dataSource={filteredCases.filter((c) =>
                        category === 'verified' ? c.status === 'verified' : category === 'unverified' ? c.status === 'unverified' : true,
                      )}
                      onRow={(r) => ({
                        onClick: () => setActiveCase(r),
                        style: { cursor: 'pointer', background: activeCase?.id === r.id ? '#F3F9F5' : undefined },
                      })}
                      columns={[
                        { title: '病例号', dataIndex: 'id', width: 120 },
                        { title: '时间', dataIndex: 'time', width: 96, render: (t: string) => <span className="num" style={{ fontSize: 11 }}>{fmtTime(t, 'MM-DD')}</span> },
                        { title: '地块', dataIndex: 'plotId', width: 110, render: (p: string) => plotById(p).name },
                        { title: '诊断', dataIndex: 'diagnosis', width: 100, render: (p: PestKey) => <PestTag pest={p} size="small" /> },
                        { title: '置信', dataIndex: 'confidence', width: 70, render: (v: number) => <span className="num">{(v * 100).toFixed(0)}%</span> },
                        { title: '程度', dataIndex: 'severity', width: 76, render: (s: Severity) => <SeverityTag sev={s} /> },
                        {
                          title: '状态',
                          dataIndex: 'status',
                          width: 84,
                          render: (s: string) => (
                            <Tag color={s === 'verified' ? 'green' : 'orange'} style={{ fontSize: 11 }}>
                              {s === 'verified' ? '已核实' : '待核实'}
                            </Tag>
                          ),
                        },
                        { title: '结局', dataIndex: 'outcome', width: 84 },
                      ]}
                    />
                  </Card>
                </Col>
                <Col xs={24} lg={9}>
                  {activeCase ? (
                    <Card size="small" title={`病例详情 · ${activeCase.id}`}>
                      <Descriptions size="small" column={1} labelStyle={{ width: 70 }}>
                        <Descriptions.Item label="地块">
                          {plotById(activeCase.plotId).name}
                        </Descriptions.Item>
                        <Descriptions.Item label="时间">{fmtTime(activeCase.time, 'YYYY-MM-DD HH:mm')}</Descriptions.Item>
                        <Descriptions.Item label="诊断">
                          <PestTag pest={activeCase.diagnosis} />
                          <SeverityTag sev={activeCase.severity} />
                        </Descriptions.Item>
                        <Descriptions.Item label="转归">
                          <Tag color={activeCase.outcome === '已恢复' ? 'green' : activeCase.outcome === '防治中' ? 'orange' : 'default'}>
                            {activeCase.outcome}
                          </Tag>
                        </Descriptions.Item>
                      </Descriptions>
                      <Divider style={{ margin: '8px 0' }} />
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: '#2E8B62', marginBottom: 4 }}>病例摘要</div>
                      <p style={{ fontSize: 12.5, color: '#3D474F', lineHeight: 1.8 }}>{activeCase.summary}</p>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: '#2E8B62', marginBottom: 4 }}>处置与治疗</div>
                      <p style={{ fontSize: 12.5, color: '#3D474F', lineHeight: 1.8 }}>{activeCase.treatment}</p>
                      <Divider style={{ margin: '8px 0' }} />
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: '#2E8B62', marginBottom: 6 }}>
                        多 Agent 会诊要点
                      </div>
                      {activeCase.agentHighlights.map((h, i) => (
                        <div key={i} style={{ marginBottom: 6, paddingLeft: 12, borderLeft: '2px solid #E4E9E6' }}>
                          <div style={{ fontSize: 11.5, color: '#8B96A0' }}>{h.agent}</div>
                          <div style={{ fontSize: 12, color: '#3D474F', lineHeight: 1.6 }}>{h.point}</div>
                        </div>
                      ))}
                    </Card>
                  ) : (
                    <Card size="small">
                      <Empty description="点击病例查看详情" image={Empty.PRESENTED_IMAGE_SIMPLE} style={{ marginTop: 40 }} />
                    </Card>
                  )}
                </Col>
              </Row>
            ),
          },
        ]}
      />
    </div>
  );
}

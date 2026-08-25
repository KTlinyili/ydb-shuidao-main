import { useEffect, useMemo, useState } from 'react';
import { CloudOutlined, DashboardOutlined, ExperimentOutlined, SunOutlined } from '@ant-design/icons';
import { Card, Col, Progress, Row, Segmented, Table, Tag } from 'antd';
import type { EnvSnapshot, TimeRange } from '@/types/domain';
import { getEnvSeries, listPlots } from '@/api/services';
import { MetricStatistic, PageHeader } from '@/components/common';
import { EnvTrendChart } from '@/components/charts';
import { plotById } from '@/mock/farm';

/**
 * 环境监测页：温度 / 空气湿度 / 光照 / 土壤含水率。
 * 数据契约对应后端 GET /api/v1/env/series。
 */

const METRIC_DEFS = [
  { key: 'temperature', name: '温度', unit: '℃', color: '#C0764A', icon: <SunOutlined />, desc: '适发区间 22~33℃' },
  { key: 'humidity', name: '空气湿度', unit: '%RH', color: '#5B8AA8', icon: <CloudOutlined />, desc: '病害预警阈值 85%' },
  { key: 'light', name: '光照强度', unit: 'klx', color: '#B8982E', icon: <SunOutlined />, desc: '光合有效辐射参考' },
  { key: 'soilMoisture', name: '土壤含水率', unit: '%VWC', color: '#5F8FA8', icon: <ExperimentOutlined />, desc: '晒田阈值 55%' },
] as const;

export default function EnvMonitorPage() {
  const [range, setRange] = useState<TimeRange>('24h');
  const [plotId, setPlotId] = useState<string | 'all'>('all');
  const [series, setSeries] = useState<EnvSnapshot[]>([]);
  const [activeMetric, setActiveMetric] = useState<(typeof METRIC_DEFS)[number]['key']>('humidity');

  useEffect(() => {
    getEnvSeries(range, plotId === 'all' ? undefined : plotId).then(setSeries);
  }, [range, plotId]);

  const current = series.at(-1);
  const dayStats = useMemo(() => {
    if (!series.length) return null;
    const temp = series.map((s) => s.temperature);
    const hum = series.map((s) => s.humidity);
    const light = series.map((s) => s.light);
    const soil = series.map((s) => s.soilMoisture);
    const avg = (a: number[]) => Math.round((a.reduce((x, y) => x + y, 0) / a.length) * 10) / 10;
    const max = (a: number[]) => Math.max(...a);
    const min = (a: number[]) => Math.min(...a);
    return {
      temperature: { avg: avg(temp), max: max(temp), min: min(temp) },
      humidity: { avg: avg(hum), max: max(hum), min: min(hum) },
      light: { avg: avg(light), max: max(light), min: min(light) },
      soilMoisture: { avg: avg(soil), max: max(soil), min: min(soil) },
    };
  }, [series]);

  // 各地块最新环境横向对比
  const plotRows = useMemo(() => {
    const c = series.at(-1);
    if (!c) return [];
    return ['P01', 'P03', 'P05', 'P07'].map((pid) => {
      // 用种子偏移模拟地块差异
      const off = pid.charCodeAt(1) * 2 + pid.charCodeAt(2);
      return {
        key: pid,
        plot: `${pid} ${plotById(pid).name}`,
        temperature: Math.round((c.temperature + ((off % 5) - 2) * 0.7) * 10) / 10,
        humidity: Math.min(98, Math.round((c.humidity + ((off % 7) - 3) * 1.4) * 10) / 10),
        light: Math.round((c.light + ((off % 4) - 1.5) * 3) * 10) / 10,
        soilMoisture: Math.round((c.soilMoisture + ((off % 6) - 2.5) * 1.8) * 10) / 10,
      };
    });
  }, [series]);

  if (!current || !dayStats) return null;

  return (
    <div>
      <PageHeader
        title="环境监测"
        subtitle="传感器网络：8 台气象站 + 4 台土壤墒情仪 · 5 分钟上报周期"
        extra={
          <Segmented
            value={plotId}
            onChange={(v) => setPlotId(v as string)}
            options={[
              { value: 'all', label: '全基地' },
              ...['P01', 'P03', 'P05', 'P07'].map((p) => ({ value: p, label: p })),
            ]}
          />
        }
      />

      {/* 四个环境指标卡 */}
      <Row gutter={[12, 12]}>
        {METRIC_DEFS.map((m) => {
          const v = current[m.key];
          const st = dayStats[m.key];
          const pctForBar =
            m.key === 'temperature'
              ? ((v - 15) / 20) * 100
              : m.key === 'light'
                ? (v / 100) * 100
                : v;
          const warn =
            (m.key === 'humidity' && v > 85) ||
            (m.key === 'soilMoisture' && v > 55) ||
            (m.key === 'temperature' && v > 32);
          return (
            <Col key={m.key} xs={12} lg={6}>
              <Card
                size="small"
                styles={{ body: { padding: 14 } }}
                style={{ border: warn ? '1px solid #EEDFB2' : undefined }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 12, color: '#64707C' }}>{m.name}</span>
                  <span style={{ color: m.color, fontSize: 14 }}>{m.icon}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 3, marginTop: 6 }}>
                  <span className="num" style={{ fontSize: 24, fontWeight: 600, color: warn ? '#C05621' : '#2B333A' }}>
                    {v}
                  </span>
                  <span style={{ fontSize: 12, color: '#8B96A0' }}>{m.unit}</span>
                  {warn && <Tag color="warning" style={{ marginLeft: 'auto', fontSize: 10 }}>预警</Tag>}
                </div>
                <Progress
                  percent={Math.max(2, Math.min(100, pctForBar))}
                  showInfo={false}
                  size="small"
                  strokeColor={warn ? '#C08A2E' : m.color}
                  style={{ margin: '6px 0 4px' }}
                />
                <div style={{ fontSize: 11, color: '#8B96A0' }}>
                  {range === '24h' ? '今日' : '区间'} {st.min} ~ {st.max} / 均值 {st.avg}
                </div>
              </Card>
            </Col>
          );
        })}
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={16}>
          <Card
            size="small"
            title="环境变化趋势"
            extra={
              <Segmented
                size="small"
                value={range}
                onChange={(v) => setRange(v as TimeRange)}
                options={[
                  { value: '24h', label: '近 24 小时' },
                  { value: '7d', label: '近 7 天' },
                  { value: '30d', label: '近 30 天' },
                ]}
              />
            }
          >
            <EnvTrendChart data={series} range={range} height={326} metrics={METRIC_DEFS.map((m) => ({ key: m.key, name: m.name, unit: m.unit, color: m.color }))} />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card size="small" title="单指标详查">
            <Segmented
              size="small"
              value={activeMetric}
              onChange={(v) => setActiveMetric(v as typeof activeMetric)}
              options={METRIC_DEFS.map((m) => ({ value: m.key, label: m.name === '土壤含水率' ? '墒情' : m.name === '空气湿度' ? '湿度' : m.name === '光照强度' ? '光照' : m.name }))}
              style={{ marginBottom: 8 }}
            />
            <EnvTrendChart
              data={series}
              range={range}
              height={240}
              metrics={[
                METRIC_DEFS.find((m) => m.key === activeMetric)!.key === 'temperature'
                  ? { key: 'temperature', name: '温度', unit: '℃', color: '#C0764A' }
                  : METRIC_DEFS.find((m) => m.key === activeMetric)!.key === 'humidity'
                    ? { key: 'humidity', name: '湿度', unit: '%', color: '#5B8AA8' }
                    : METRIC_DEFS.find((m) => m.key === activeMetric)!.key === 'light'
                      ? { key: 'light', name: '光照', unit: 'klx', color: '#B8982E' }
                      : { key: 'soilMoisture', name: '土壤含水率', unit: '%', color: '#5F8FA8' },
              ]}
            />
            <div style={{ fontSize: 11.5, color: '#8B96A0', marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
              <DashboardOutlined />
              {METRIC_DEFS.find((m) => m.key === activeMetric)!.desc}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
        <Col xs={24} lg={14}>
          <Card size="small" title="各地块环境对比（最新上报）">
            <Table
              size="small"
              pagination={false}
              dataSource={plotRows}
              columns={[
                { title: '地块', dataIndex: 'plot' },
                { title: '温度 ℃', dataIndex: 'temperature', render: (v: number) => <span className="num">{v}</span> },
                {
                  title: '湿度 %',
                  dataIndex: 'humidity',
                  render: (v: number) => (
                    <span className="num" style={{ color: v > 85 ? '#C05621' : undefined }}>
                      {v}
                    </span>
                  ),
                },
                { title: '光照 klx', dataIndex: 'light', render: (v: number) => <span className="num">{v}</span> },
                {
                  title: '土壤含水率 %',
                  dataIndex: 'soilMoisture',
                  render: (v: number) => (
                    <span className="num" style={{ color: v > 55 ? '#C05621' : undefined }}>
                      {v}
                    </span>
                  ),
                },
                {
                  title: '环境态势',
                  render: (_, r) => (
                    <Tag color={r.humidity > 88 ? 'warning' : r.humidity > 80 ? 'default' : 'success'} style={{ fontSize: 11 }}>
                      {r.humidity > 88 ? '高湿适发' : r.humidity > 80 ? '接近阈值' : '常态'}
                    </Tag>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card size="small" title="环境与病害适发关系（当前）">
            <div style={{ fontSize: 12, color: '#4A5560', lineHeight: 2 }}>
              当前空气湿度 <b className="num">{current.humidity}%</b>
              {current.humidity > 85 ? ' 已超过 85% 预警线，' : ' 低于 85% 预警线，'}
              {current.humidity > 85
                ? '纹枯病、稻瘟病侵染风险处于高位，建议通风降湿、适时晒田。'
                : '真菌性病害侵染压力中等。'}
              <br />
              土壤含水率 <b className="num">{current.soilMoisture}%</b>
              {current.soilMoisture > 55 ? ' 偏高，' : ' 处于适宜区间，'}
              {current.soilMoisture > 55
                ? '长期淹水状态会加重纹枯病与稻飞虱发生，建议排水晾田。'
                : '维持浅水勤灌即可。'}
              <br />
              气温 <b className="num">{current.temperature}℃</b> 处于 8 月中旬常值区间，对稻飞虱繁殖与纹枯病扩展均较有利，需结合虫口密度关注。
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

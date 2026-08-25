import type { ReactNode } from 'react';
import { Card, Col, Row, Statistic } from 'antd';
import { ArrowDownOutlined, ArrowUpOutlined } from '@ant-design/icons';
import type { DeviceStatus, PestKey, RiskLevel, Severity } from '@/types/domain';
import { PEST_META, RISK_LEVEL_META, SEVERITY_META } from '@/utils/constants';

/** 风险等级标签 */
export function RiskTag({ level, score }: { level: RiskLevel; score?: number }) {
  const m = RISK_LEVEL_META[level];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        fontSize: 12,
        lineHeight: '20px',
        padding: '0 8px',
        borderRadius: 4,
        color: m.color,
        background: m.bg,
        border: `1px solid ${m.border}`,
      }}
    >
      {m.label}
      {score !== undefined && <span className="num">{score}</span>}
    </span>
  );
}

/** 严重程度标签 */
export function SeverityTag({ sev }: { sev: Severity }) {
  const m = SEVERITY_META[sev];
  return (
    <span
      style={{
        fontSize: 12,
        lineHeight: '20px',
        padding: '0 8px',
        borderRadius: 4,
        color: m.color,
        background: '#F5F7F6',
        border: '1px solid #E4E9E6',
      }}
    >
      {sev}
    </span>
  );
}

/** 病虫害标签 */
export function PestTag({ pest, size = 'normal' }: { pest: PestKey | 'multi'; size?: 'small' | 'normal' }) {
  if (pest === 'multi') {
    return (
      <span
        style={{
          fontSize: size === 'small' ? 11 : 12,
          lineHeight: size === 'small' ? '18px' : '20px',
          padding: '0 7px',
          borderRadius: 4,
          color: '#5A6570',
          background: '#F0F2F1',
          border: '1px solid #E0E5E2',
        }}
      >
        混合发生
      </span>
    );
  }
  const m = PEST_META[pest];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        fontSize: size === 'small' ? 11 : 12,
        lineHeight: size === 'small' ? '18px' : '20px',
        padding: '0 7px',
        borderRadius: 4,
        color: m.color,
        background: `${m.color}12`,
        border: `1px solid ${m.color}30`,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: 2, background: m.color }} />
      {m.name}
    </span>
  );
}

/** 设备状态渲染 */
export function DeviceStatusBadge({ status }: { status: DeviceStatus }) {
  const map: Record<DeviceStatus, { label: string; color: string }> = {
    online: { label: '在线', color: '#3D8B5F' },
    offline: { label: '离线', color: '#98A2A9' },
    fault: { label: '故障', color: '#C05621' },
  };
  const m = map[status];
  return (
    <span style={{ fontSize: 12, color: m.color }}>
      <span className={`status-dot ${status === 'online' ? 'online' : status}`} />
      {m.label}
    </span>
  );
}

/** 页面头部 */
export function PageHeader({
  title,
  subtitle,
  extra,
}: {
  title: string;
  subtitle?: string;
  extra?: ReactNode;
}) {
  return (
    <div className="page-header">
      <div>
        <h2 className="page-title">{title}</h2>
        {subtitle && <div className="page-subtitle">{subtitle}</div>}
      </div>
      {extra}
    </div>
  );
}

/** 指标统计卡组 */
export interface StatItem {
  title: string;
  value: string | number;
  suffix?: string;
  icon?: ReactNode;
  iconBg?: string;
  delta?: number;
  deltaLabel?: string;
  footer?: ReactNode;
}

export function StatCards({ items, span = 4 }: { items: StatItem[]; span?: number }) {
  return (
    <Row gutter={[12, 12]}>
      {items.map((it) => (
        <Col key={it.title} xs={12} sm={12} lg={span}>
          <Card
            size="small"
            styles={{ body: { padding: '15px 16px' } }}
            hoverable
            style={{ height: '100%' }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, color: '#64707C', marginBottom: 8 }}>{it.title}</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                  <span
                    className="num"
                    style={{ fontSize: 26, fontWeight: 600, color: '#1F262B', letterSpacing: -0.5 }}
                  >
                    {it.value}
                  </span>
                  {it.suffix && (
                    <span style={{ fontSize: 12, color: '#8B96A0' }}>{it.suffix}</span>
                  )}
                </div>
                {(it.delta !== undefined || it.footer) && (
                  <div
                    style={{
                      marginTop: 8,
                      fontSize: 11.5,
                      minHeight: 17,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {it.delta !== undefined && (
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 2,
                          color: it.delta > 0 ? '#B9452F' : it.delta < 0 ? '#3D8B5F' : '#8B96A0',
                          background: it.delta > 0 ? '#FBECEC' : it.delta < 0 ? '#EAF4EE' : '#F0F2F1',
                          borderRadius: 4,
                          padding: '0 6px',
                          lineHeight: '17px',
                          flexShrink: 0,
                        }}
                      >
                        {it.delta > 0 ? (
                          <ArrowUpOutlined style={{ fontSize: 9 }} />
                        ) : it.delta < 0 ? (
                          <ArrowDownOutlined style={{ fontSize: 9 }} />
                        ) : null}
                        {it.delta > 0 ? '+' : ''}
                        {it.delta} {it.deltaLabel ?? 'vs 昨日'}
                      </span>
                    )}
                    {it.footer}
                  </div>
                )}
              </div>
              {it.icon && (
                <div
                  style={{
                    width: 38,
                    height: 38,
                    borderRadius: 9,
                    background: it.iconBg ?? '#E8F3ED',
                    color: '#2E8B62',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 18,
                    flexShrink: 0,
                    marginLeft: 12,
                  }}
                >
                  {it.icon}
                </div>
              )}
            </div>
          </Card>
        </Col>
      ))}
    </Row>
  );
}

/** 数值+单位的安全 Statistic 封装（保持企业风格） */
export function MetricStatistic(props: {
  title: string;
  value: number | string;
  suffix?: string;
  precision?: number;
}) {
  return (
    <Statistic
      title={<span style={{ fontSize: 12, color: '#64707C' }}>{props.title}</span>}
      value={props.value}
      suffix={
        props.suffix ? <span style={{ fontSize: 12, color: '#8B96A0' }}>{props.suffix}</span> : undefined
      }
      precision={props.precision}
      valueStyle={{ fontSize: 20, fontWeight: 600 }}
    />
  );
}

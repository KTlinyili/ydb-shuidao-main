import { useMemo, useState } from 'react';
import type { Device, Plot } from '@/types/domain';
import { RISK_LEVEL_META } from '@/utils/constants';

/**
 * 田间地图：4×2 地块栅格俯视图。
 * - 地块左侧色条标识风险等级，点击选中
 * - 设备以文字徽标标注（CAM/ENV/SOL）
 * 接入 GIS 后可替换为瓦片地图组件，交互契约不变。
 */
export function FieldMap({
  plots,
  devices,
  selectedPlotId,
  onSelect,
  height = 380,
  showDevices = true,
}: {
  plots: Plot[];
  devices?: Device[];
  selectedPlotId?: string;
  onSelect?: (plotId: string) => void;
  height?: number;
  showDevices?: boolean;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const gridRows = useMemo(() => {
    const maxRow = Math.max(...plots.map((p) => p.grid.row));
    const maxCol = Math.max(...plots.map((p) => p.grid.col));
    const grid: (Plot | undefined)[][] = Array.from({ length: maxRow + 1 }, () =>
      Array.from({ length: maxCol + 1 }, () => undefined),
    );
    for (const p of plots) grid[p.grid.row][p.grid.col] = p;
    return grid;
  }, [plots]);

  const devicesByPlot = useMemo(() => {
    const m = new Map<string, Device[]>();
    for (const d of devices ?? []) {
      if (!d.plotId) continue;
      m.set(d.plotId, [...(m.get(d.plotId) ?? []), d]);
    }
    return m;
  }, [devices]);

  const KIND_BADGE: Record<Device['kind'], string> = {
    camera: 'CAM',
    env_sensor: 'ENV',
    soil_sensor: 'SOL',
    edge: 'EDGE',
    gateway: 'GW',
  };

  return (
    <div
      style={{
        position: 'relative',
        height,
        background: '#F2F5F3',
        border: '1px solid #E7ECE9',
        borderRadius: 10,
        padding: 16,
        overflow: 'auto',
      }}
    >
      {/* 地图顶部标注行 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: '#8B96A0' }}>北 ↑ · 农场总平面（示意）</span>
        <span style={{ display: 'flex', gap: 10, fontSize: 10.5, color: '#8B96A0' }}>
          {(Object.keys(RISK_LEVEL_META) as (keyof typeof RISK_LEVEL_META)[]).map((k) => (
            <span key={k} style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
              <span style={{ width: 8, height: 8, borderRadius: 2, background: RISK_LEVEL_META[k].color }} />
              {RISK_LEVEL_META[k].label}
            </span>
          ))}
        </span>
      </div>

      {/* 灌溉主渠（横向贯穿） */}
      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          top: '50%',
          height: 7,
          background: 'repeating-linear-gradient(90deg,#D9E4DC 0 16px,#CBDCCF 16px 32px)',
          borderRadius: 3,
        }}
      />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 14,
          marginTop: 24,
          marginBottom: 14,
          position: 'relative',
        }}
      >
        {gridRows.flat().map((p, i) =>
          p ? (
            <div
              key={p.id}
              onMouseEnter={() => setHover(p.id)}
              onMouseLeave={() => setHover(null)}
              onClick={() => onSelect?.(p.id)}
              style={{
                cursor: 'pointer',
                borderRadius: 8,
                border: `1px solid ${selectedPlotId === p.id ? '#2E8B62' : '#E4E9E6'}`,
                borderLeft: `4px solid ${RISK_LEVEL_META[p.riskLevel].color}`,
                background: '#FFFFFF',
                boxShadow:
                  selectedPlotId === p.id
                    ? '0 0 0 2px rgba(46,139,98,0.14)'
                    : hover === p.id
                      ? '0 2px 8px rgba(24,35,30,0.06)'
                      : undefined,
                padding: '11px 12px',
                minHeight: 138,
                transition: 'box-shadow .15s, border-color .15s',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12.5, fontWeight: 600, color: '#1F262B' }}>{p.name}</span>
                <span
                  style={{
                    fontSize: 10.5,
                    color: RISK_LEVEL_META[p.riskLevel].color,
                    background: RISK_LEVEL_META[p.riskLevel].bg,
                    border: `1px solid ${RISK_LEVEL_META[p.riskLevel].border}`,
                    borderRadius: 3,
                    padding: '0 5px',
                    lineHeight: '17px',
                  }}
                >
                  {RISK_LEVEL_META[p.riskLevel].label}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#8B96A0', marginTop: 3 }}>
                {p.id} · {p.variety} · {p.stage}
              </div>
              {/* 稻行纹理 + 风险分 */}
              <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10, marginTop: 'auto' }}>
                <div
                  style={{
                    flex: 1,
                    height: 30,
                    borderRadius: 4,
                    background:
                      'repeating-linear-gradient(180deg, rgba(85,134,107,0.14) 0 3px, transparent 3px 8px), #F8FAF8',
                    border: '1px solid #EEF1EF',
                  }}
                />
                <div style={{ textAlign: 'right' }}>
                  <div
                    className="num"
                    style={{ fontSize: 17, fontWeight: 600, color: RISK_LEVEL_META[p.riskLevel].color }}
                  >
                    {p.compositeRisk}
                  </div>
                  <div style={{ fontSize: 9.5, color: '#A5AEB5' }}>综合风险</div>
                </div>
              </div>
              {/* 设备徽标 */}
              {showDevices && (
                <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
                  {(devicesByPlot.get(p.id) ?? []).map((d) => (
                    <span
                      key={d.id}
                      title={`${d.name} · ${d.status === 'online' ? '在线' : d.status === 'fault' ? '故障' : '离线'}`}
                      style={{
                        fontSize: 9.5,
                        lineHeight: '15px',
                        padding: '0 5px',
                        borderRadius: 3,
                        background: d.status === 'online' ? '#F0F6F2' : '#F7F0EC',
                        color: d.status === 'online' ? '#5F8570' : '#C05621',
                        border: `1px solid ${d.status === 'online' ? '#E1EDE5' : '#F0DBCE'}`,
                      }}
                    >
                      {KIND_BADGE[d.kind]}
                    </span>
                  ))}
                </div>
              )}
              {(hover === p.id || selectedPlotId === p.id) && (
                <div
                  style={{
                    marginTop: 8,
                    fontSize: 10.5,
                    color: '#64707C',
                    background: '#F8FAF8',
                    borderRadius: 4,
                    padding: '5px 8px',
                    border: '1px solid #EEF1EF',
                    lineHeight: 1.7,
                  }}
                >
                  {p.areaMu} 亩 · 管理员 {p.manager}
                  <br />
                  视觉 {p.visualRisk} / 环境 {p.envRisk} / 趋势 {p.trendRisk}
                </div>
              )}
            </div>
          ) : (
            <div key={`empty-${i}`} style={{ minHeight: 138 }} />
          ),
        )}
      </div>
    </div>
  );
}

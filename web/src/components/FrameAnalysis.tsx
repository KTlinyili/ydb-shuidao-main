import { useMemo } from 'react';
import type { DetectionBox } from '@/types/domain';
import { PEST_META } from '@/utils/constants';
import { makeRng } from '@/mock/random';

/**
 * 帧分析视图：目标检测结果的可视化标注图。
 *
 * 定位为"模型推理结果的分析视图"（类似标注工具），不是视频画面：
 * 白底网格 + 示意稻叶纹理 + 检测框叠加。接入真实视频后，
 * 背景层替换为 <video>/截图，检测框逻辑不变。
 */
export function FrameAnalysis({
  boxes,
  seed,
  height = 320,
  showBoxes = true,
  label,
  timeText,
}: {
  boxes: DetectionBox[];
  seed: number;
  height?: number;
  showBoxes?: boolean;
  label?: string;
  timeText?: string;
}) {
  const scene = useMemo(() => {
    const r = makeRng(seed);
    // 示意稻叶：斜向半透明绿色圆角长条，风格化而非仿照片
    const leaves = Array.from({ length: 34 }, () => ({
      x: r.float(-8, 108),
      y: r.float(6, 106),
      len: r.float(14, 30),
      angle: r.float(-26, 26),
      w: r.float(2.6, 4.6),
      shade: r.int(0, 3),
    }));
    return { leaves };
  }, [seed]);

  const leafColors = ['#D9E8DC', '#CBDFD0', '#BCD6C4', '#ADCDB7'];

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height,
        borderRadius: 8,
        overflow: 'hidden',
        background: '#FBFCFB',
        border: '1px solid #E7ECE9',
      }}
    >
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: '100%', height: '100%', display: 'block' }}>
        <defs>
          <pattern id={`grid-${seed}`} width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M10 0 H0 V10" fill="none" stroke="#EDF1EE" strokeWidth="0.25" />
          </pattern>
        </defs>
        <rect x="0" y="0" width="100" height="100" fill={`url(#grid-${seed})`} />
        {scene.leaves.map((l, i) => (
          <rect
            key={i}
            x={l.x}
            y={l.y}
            width={l.len}
            height={l.w}
            rx={l.w / 2}
            fill={leafColors[l.shade]}
            opacity="0.75"
            transform={`rotate(${l.angle} ${l.x} ${l.y})`}
          />
        ))}
      </svg>

      {/* 检测框（标注工具风格：角部加粗 + 顶置标签） */}
      {showBoxes &&
        boxes.map((b) => {
          const meta = PEST_META[b.pest];
          const style: React.CSSProperties = {
            position: 'absolute',
            left: `${b.bbox[0] * 100}%`,
            top: `${b.bbox[1] * 100}%`,
            width: `${b.bbox[2] * 100}%`,
            height: `${b.bbox[3] * 100}%`,
            border: `1.5px solid ${meta.color}`,
            background: `${meta.color}14`,
            borderRadius: 3,
            pointerEvents: 'none',
          };
          return (
            <div key={b.id} style={style}>
              <span
                style={{
                  position: 'absolute',
                  top: -20,
                  left: -1.5,
                  fontSize: 10.5,
                  lineHeight: '18px',
                  padding: '0 6px',
                  borderRadius: 3,
                  color: '#fff',
                  background: meta.color,
                  whiteSpace: 'nowrap',
                  fontWeight: 500,
                }}
              >
                {meta.name} {(b.confidence * 100).toFixed(0)}% · {b.severity}
              </span>
              {/* 四角加粗 */}
              {[
                { left: -2.5, top: -2.5, borderLeft: `3px solid ${meta.color}`, borderTop: `3px solid ${meta.color}` },
                { right: -2.5, top: -2.5, borderRight: `3px solid ${meta.color}`, borderTop: `3px solid ${meta.color}` },
                { left: -2.5, bottom: -2.5, borderLeft: `3px solid ${meta.color}`, borderBottom: `3px solid ${meta.color}` },
                { right: -2.5, bottom: -2.5, borderRight: `3px solid ${meta.color}`, borderBottom: `3px solid ${meta.color}` },
              ].map((corner, ci) => (
                <span key={ci} style={{ position: 'absolute', width: 8, height: 8, ...corner }} />
              ))}
            </div>
          );
        })}

      {/* 顶部信息条 */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 10px',
          background: 'rgba(255,255,255,0.88)',
          borderBottom: '1px solid #EEF1EF',
          fontSize: 11,
          color: '#64707C',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: 2,
              background: '#2E8B62',
              display: 'inline-block',
            }}
          />
          帧分析视图{label ? ` · ${label}` : ''}
        </span>
        <span className="num">{timeText ?? ''}</span>
      </div>

      {/* 底部统计条 */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          display: 'flex',
          gap: 12,
          padding: '6px 10px',
          background: 'rgba(255,255,255,0.88)',
          borderTop: '1px solid #EEF1EF',
          fontSize: 10.5,
          color: '#8B96A0',
        }}
      >
        <span>检出 {boxes.length} 处目标</span>
        {Array.from(new Set(boxes.map((b) => b.pest))).map((p) => (
          <span key={p} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 6, height: 6, borderRadius: 1.5, background: PEST_META[p].color }} />
            {PEST_META[p].name}
          </span>
        ))}
      </div>
    </div>
  );
}

import type { WarningRecord } from '@/types/domain';
import { List, Tooltip } from 'antd';
import { RiskTag, PestTag } from '@/components/common';
import { fmtTime } from '@/utils/format';
import { plotById } from '@/mock/farm';
import { useNavigate } from 'react-router-dom';

const STATUS_LABEL: Record<WarningRecord['status'], { text: string; color: string }> = {
  pending: { text: '待处理', color: '#B9452F' },
  processing: { text: '处置中', color: '#C08A2E' },
  resolved: { text: '已解除', color: '#3D8B5F' },
};

/** 预警列表（Dashboard、预警页共用） */
export function WarningList({
  records,
  showStatus = true,
  maxHeight = 360,
}: {
  records: WarningRecord[];
  showStatus?: boolean;
  maxHeight?: number;
}) {
  const navigate = useNavigate();
  return (
    <div style={{ maxHeight, overflowY: 'auto' }}>
      <List
        dataSource={records}
        rowKey={(w) => w.id}
        renderItem={(w) => {
          const plot = plotById(w.plotId);
          const st = STATUS_LABEL[w.status];
          return (
            <List.Item
              style={{ padding: '10px 4px', cursor: 'pointer' }}
              onClick={() => navigate(`/warnings?id=${w.id}`)}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span className="num" style={{ fontSize: 11.5, color: '#8B96A0' }}>
                    {fmtTime(w.time, 'MM-DD HH:mm')}
                  </span>
                  <PestTag pest={w.pest} size="small" />
                  <RiskTag level={w.level} score={w.compositeRisk} />
                  <span style={{ fontSize: 12.5, color: '#2B333A', fontWeight: 500 }}>
                    {plot.name}
                  </span>
                  {showStatus && (
                    <span style={{ fontSize: 11.5, color: st.color, marginLeft: 'auto' }}>● {st.text}</span>
                  )}
                </div>
                <Tooltip title={w.trigger} placement="topLeft">
                  <div
                    style={{
                      fontSize: 12,
                      color: '#64707C',
                      marginTop: 4,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    触发：{w.trigger}
                  </div>
                </Tooltip>
              </div>
            </List.Item>
          );
        }}
      />
    </div>
  );
}

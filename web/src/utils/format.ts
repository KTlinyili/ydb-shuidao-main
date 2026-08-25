import dayjs from 'dayjs';
import type { DetectSource, PestKey } from '@/types/domain';
import { PEST_META } from '@/utils/constants';

export function fmtTime(iso: string, pattern = 'MM-DD HH:mm'): string {
  return dayjs(iso).format(pattern);
}

export function fmtFullTime(iso: string): string {
  return dayjs(iso).format('YYYY-MM-DD HH:mm:ss');
}

export function fromNow(iso: string): string {
  const diffMin = Math.round((Date.now() - dayjs(iso).valueOf()) / 60000);
  if (diffMin < 1) return '刚刚';
  if (diffMin < 60) return `${diffMin} 分钟前`;
  const h = Math.floor(diffMin / 60);
  if (h < 24) return `${h} 小时前`;
  return `${Math.floor(h / 24)} 天前`;
}

export function pct(v: number, digits = 1): string {
  return `${v.toFixed(digits)}%`;
}

export function pestName(key: PestKey | 'multi'): string {
  if (key === 'multi') return '多种病虫害';
  return PEST_META[key].name;
}

export const SOURCE_LABEL: Record<DetectSource, string> = {
  auto_patrol: '自动巡检',
  scheduled_capture: '定时抓拍',
  manual_upload: '手动上传',
};

export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

export function fixed(v: number, digits = 1): string {
  return v.toFixed(digits);
}

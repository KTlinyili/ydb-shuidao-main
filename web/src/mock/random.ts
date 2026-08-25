/**
 * 种子随机数工具：保证 Mock 数据在同一会话内稳定可复现，
 * 演示时刷新页面数据形态一致。
 */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface Rng {
  next: () => number;
  int: (lo: number, hi: number) => number;
  float: (lo: number, hi: number, digits?: number) => number;
  pick: <T>(arr: readonly T[]) => T;
  bool: (p?: number) => boolean;
}

export function makeRng(seed: number): Rng {
  const next = mulberry32(seed);
  return {
    next,
    int: (lo, hi) => Math.floor(next() * (hi - lo + 1)) + lo,
    float: (lo, hi, digits = 1) => {
      const v = next() * (hi - lo) + lo;
      const f = Math.pow(10, digits);
      return Math.round(v * f) / f;
    },
    pick: (arr) => arr[Math.floor(next() * arr.length)],
    bool: (p = 0.5) => next() < p,
  };
}

/** 全局演示种子：按当日日期生成，保证同一天内刷新数据稳定，次日自动更新 */
export const DEMO_SEED = (() => {
  const d = new Date();
  return d.getFullYear() * 10000 + (d.getMonth() + 1) * 100 + d.getDate();
})();

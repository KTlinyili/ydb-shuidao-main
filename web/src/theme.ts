import type { ThemeConfig } from 'antd';
import { BRAND } from '@/utils/constants';

/**
 * 企业级后台主题：低饱和农业绿品牌色、克制的圆角与阴影。
 * 参考飞书/华为云控制台的克制风格。
 */
export const themeConfig: ThemeConfig = {
  token: {
    colorPrimary: BRAND.primary,
    colorInfo: BRAND.primary,
    colorSuccess: '#3D8B5F',
    colorWarning: '#C08A2E',
    colorError: '#B9452F',
    colorTextBase: '#2B333A',
    colorBgLayout: BRAND.bgLayout,
    colorBgContainer: '#FFFFFF',
    colorBorder: BRAND.border,
    colorBorderSecondary: BRAND.borderLight,
    borderRadius: 8,
    borderRadiusLG: 10,
    fontSize: 13,
    controlHeight: 32,
    boxShadow: '0 1px 2px rgba(24, 35, 30, 0.03), 0 2px 10px rgba(24, 35, 30, 0.04)',
    boxShadowSecondary: '0 4px 14px rgba(24, 35, 30, 0.08)',
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif",
  },
  components: {
    Layout: {
      headerBg: '#FFFFFF',
      headerHeight: 56,
      siderBg: '#FFFFFF',
      bodyBg: BRAND.bgLayout,
    },
    Card: {
      paddingLG: 18,
      headerFontSize: 14,
      headerHeight: 46,
    },
    Table: {
      headerBg: '#F8FAF9',
      headerColor: '#64707C',
      headerSplitColor: 'transparent',
      cellPaddingBlock: 10,
      cellPaddingInline: 12,
      rowHoverBg: '#F7FAF8',
    },
    Menu: {
      itemHeight: 38,
      itemMarginInline: 10,
      itemMarginBlock: 3,
      itemBorderRadius: 8,
      itemSelectedBg: BRAND.primarySoft,
      itemSelectedColor: BRAND.primaryDeep,
      subMenuItemBg: 'transparent',
      itemColor: '#4A5560',
      itemHoverBg: '#F4F7F5',
      groupTitleFontSize: 11,
    },
    Statistic: {
      contentFontSize: 22,
    },
    Tag: {
      borderRadiusSM: 4,
    },
    Tabs: {
      itemColor: '#64707C',
    },
  },
};

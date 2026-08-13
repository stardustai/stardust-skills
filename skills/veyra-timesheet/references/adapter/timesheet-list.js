import { cli, Strategy } from '@jackwener/opencli/registry';

// Veyra 睿策工时系统 — 列出已填工时
// base_url 可用 env VEYRA_BASE_URL 覆盖；默认公司地址
const BASE = process.env.VEYRA_BASE_URL || 'https://guance.corpintra.rosettalab.top';

// 服务端约束（2026-08-07 实测）：
// - pageSize 硬上限 100，传更大值仍只回 100 条；
// - 不支持任何日期过滤参数（startDate / start / workDateStart 均被忽略，total 不变）。
// 因此必须按 workDate desc 翻页拉取后在本地过滤。旧实现用 asc 拉单页再过滤，
// 记录总数一旦超过 100，最新的数据就落在页外，任何日期范围查询都查不到——
// 曾因此把「已填 24h」误判成「已填 14h」。
const PAGE_SIZE = 100;

cli({
  site: 'veyra',
  name: 'timesheet-list',
  description: '列出 Veyra 已填工时（可按日期范围过滤）',
  access: 'read',
  example: 'opencli veyra timesheet-list --start 2026-06-15 --end 2026-06-21',
  domain: 'guance.corpintra.rosettalab.top',
  strategy: Strategy.COOKIE,
  browser: true,
  args: [
    { name: 'start', help: '起始日期 YYYY-MM-DD（含）' },
    { name: 'end', help: '结束日期 YYYY-MM-DD（含）' },
    { name: 'limit', type: 'int', default: 1000, help: '最大拉取条数（翻页累计上限）' },
  ],
  columns: ['workDate', 'hours', 'project', 'content', 'id'],
  func: async (page, kwargs) => {
    await page.goto(`${BASE}/timesheets`);
    await page.wait(2);
    const { start, end } = kwargs;
    const limit = kwargs.limit || 1000;
    const rows = await page.evaluate(`(async()=>{
      const start = ${JSON.stringify(start || null)};
      const acc = [];
      for (let p = 1; ; p++) {
        const url = '${BASE}/api/timesheets?page=' + p + '&pageSize=${PAGE_SIZE}&sortBy=workDate&sortOrder=desc';
        const r = await fetch(url, {credentials:'include'});
        const j = await r.json();
        const items = (j.data && j.data.items) || [];
        if (!items.length) break;
        for (const x of items) {
          acc.push({workDate:x.workDate, hours:x.hours, project:x.opportunityProjectId, content:x.content, id:x.id});
        }
        const total = (j.data && j.data.total) || 0;
        if (acc.length >= total || acc.length >= ${limit}) break;
        // desc 排序：本页最后一条已早于 start，后续页只会更早，无需继续翻
        if (start && items[items.length - 1].workDate < start) break;
      }
      return acc;
    })()`);
    return rows
      .filter(x => (!start || x.workDate >= start) && (!end || x.workDate <= end))
      .sort((a, b) => a.workDate.localeCompare(b.workDate));
  },
});

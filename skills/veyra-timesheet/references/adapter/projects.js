import { cli, Strategy } from '@jackwener/opencli/registry';

// Veyra 睿策 — 列出/搜索项目池（投入事项要挂的「项目」）
const BASE = process.env.VEYRA_BASE_URL || 'https://guance.corpintra.rosettalab.top';

cli({
  site: 'veyra',
  name: 'projects',
  description: '列出/搜索 Veyra 项目池（type+id 用于 timesheet-add）',
  access: 'read',
  example: 'opencli veyra projects --search StarBench',
  domain: 'guance.corpintra.rosettalab.top',
  strategy: Strategy.COOKIE,
  browser: true,
  args: [
    { name: 'search', help: '按 label 关键词过滤（项目编号/名称/客户）' },
  ],
  columns: ['type', 'id', 'projectId', 'label'],
  func: async (page, kwargs) => {
    await page.goto(`${BASE}/timesheets`);
    await page.wait(2);
    const all = await page.evaluate(`(async()=>{
      const j = await (await fetch('${BASE}/api/opportunities/select-options',{credentials:'include'})).json();
      return (j.data||[]).map(o=>({type:o.type,id:o.id,projectId:o.projectId,label:o.label}));
    })()`);
    const s = kwargs.search;
    return s ? all.filter(o => (o.label || '').toLowerCase().includes(String(s).toLowerCase())) : all;
  },
});

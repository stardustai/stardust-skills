import { cli, Strategy } from '@jackwener/opencli/registry';
import { readFileSync } from 'node:fs';

// Veyra 睿策 — 列出/搜索项目池（投入事项要挂的「项目」）
// Veyra 地址不硬编码：env VEYRA_BASE_URL 优先，否则读本目录 config.json（init 流程写入）。
// 未配置时不在 import 阶段抛错（会让整组命令无法注册、被误诊为未安装），改为占位 domain + 调用时报错。
const CFG = new URL('./config.json', import.meta.url);
const BASE = (() => {
  if (process.env.VEYRA_BASE_URL) return process.env.VEYRA_BASE_URL.replace(/\/+$/, '');
  try {
    const u = JSON.parse(readFileSync(CFG, 'utf8')).veyra_base_url;
    if (u && !u.includes('<')) return u.replace(/\/+$/, '');
  } catch {}
  return null;
})();
const DOMAIN = BASE ? new URL(BASE).host : 'veyra-unconfigured.invalid';
const requireBase = () => { if (!BASE) throw new Error(`Veyra 地址未配置：把公司工时系统地址写入 ${CFG.pathname}（格式见 config.example.json）或设置环境变量 VEYRA_BASE_URL`); return BASE; };

cli({
  site: 'veyra',
  name: 'projects',
  description: '列出/搜索 Veyra 项目池（type+id 用于 timesheet-add）',
  access: 'read',
  example: 'opencli veyra projects --search StarBench',
  domain: DOMAIN,
  strategy: Strategy.COOKIE,
  browser: true,
  args: [
    { name: 'search', help: '按 label 关键词过滤（项目编号/名称/客户）' },
  ],
  columns: ['type', 'id', 'projectId', 'label'],
  func: async (page, kwargs) => {
    requireBase();
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

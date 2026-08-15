import { cli, Strategy } from '@jackwener/opencli/registry';
import { readFileSync } from 'node:fs';

// Veyra 睿策 — 新建一条工时记录（POST /api/timesheets）
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
  name: 'timesheet-add',
  description: '新建一条 Veyra 工时记录（投入事项只写本人实际做的事，加班如实填）',
  access: 'write',
  example: "opencli veyra timesheet-add --date 2026-06-15 --project cmq7uru49004apv0jzcnr8re6 --content '搭建评标demo' --hours 5",
  domain: DOMAIN,
  strategy: Strategy.COOKIE,
  browser: true,
  args: [
    { name: 'date', required: true, help: '工时日期 YYYY-MM-DD' },
    { name: 'project', required: true, help: '项目 opportunityId（来自 veyra projects 的 id）' },
    { name: 'content', required: true, help: '投入事项（一句话本人实际动作）' },
    { name: 'hours', type: 'int', required: true, help: '小时（数字，8h上限已放开）' },
    { name: 'type', default: 'project', help: 'opportunityType: lead|deal|project' },
  ],
  columns: ['status', 'ok', 'id', 'err'],
  func: async (page, kwargs) => {
    requireBase();
    await page.goto(`${BASE}/timesheets`);
    await page.wait(2);
    const payload = JSON.stringify({
      workDate: kwargs.date,
      opportunityType: kwargs.type || 'project',
      opportunityId: kwargs.project,
      content: kwargs.content,
      hours: Number(kwargs.hours),
    });
    const res = await page.evaluate(`(async()=>{
      const r = await fetch('${BASE}/api/timesheets',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:${JSON.stringify(payload)}});
      let j={}; try{ j=await r.json() }catch(e){}
      return {status:r.status, ok:j.success===true, id:(j.data&&j.data.id)||null, err:(j.error&&j.error.message)||null};
    })()`);
    return [res];
  },
});

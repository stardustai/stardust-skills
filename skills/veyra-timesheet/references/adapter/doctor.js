import { cli, Strategy } from '@jackwener/opencli/registry';
import { readFileSync } from 'node:fs';

// Veyra adapter 健康检查 — 结构/登录态变化时先跑这个定位问题
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
  name: 'doctor',
  description: 'Veyra adapter 健康检查：登录态 + 各 API 端点是否仍可用（失效时先跑这个，再按 adapter 自愈 playbook 修）',
  access: 'read',
  example: 'opencli veyra doctor',
  domain: DOMAIN,
  strategy: Strategy.COOKIE,
  browser: true,
  columns: ['check', 'ok', 'detail'],
  func: async (page, kwargs) => {
    requireBase();
    await page.goto(`${BASE}/timesheets`);
    await page.wait(2);
    return await page.evaluate(`(async()=>{
      const out=[];
      const probe=async(name,path,ok)=>{
        try{
          const res=await fetch('${BASE}'+path,{credentials:'include'});
          const ct=res.headers.get('content-type')||'';
          let j=null; if(ct.includes('json')){try{j=await res.json()}catch(e){}}
          out.push({check:name, ok:ok(res,j), detail:'HTTP '+res.status+' '+(ct.split(';')[0]||'?')});
        }catch(e){out.push({check:name, ok:false, detail:String(e)})}
      };
      await probe('登录态 /api/auth/me','/api/auth/me',(r)=>r.status===200);
      await probe('读 /api/timesheets','/api/timesheets?page=1&pageSize=1',(r,j)=>r.status===200&&!!(j&&j.data&&Array.isArray(j.data.items)));
      await probe('项目 /api/opportunities/select-options','/api/opportunities/select-options',(r,j)=>r.status===200&&!!(j&&Array.isArray(j.data)));
      const bad=out.filter(o=>!o.ok);
      if(bad.length) out.push({check:'>> 诊断', ok:false, detail: bad.some(b=>b.check.includes('auth'))?'登录态失效 → 在该 Chrome 重新登录 Veyra':'端点/结构疑似变化 → 按工时填写 skill 的 references/repair.md 重新探测并改 ~/.opencli/clis/veyra/*.js'});
      return out;
    })()`);
  },
});

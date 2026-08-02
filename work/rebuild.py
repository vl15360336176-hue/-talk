# -*- coding: utf-8 -*-
"""按新设计重构 brand-roundtable.html：新布局 + 复用现有 JS 逻辑"""
old = open("/Users/job/Documents/Codex/2026-07-31/ni/outputs/brand-roundtable.html", encoding="utf-8").read()

import re
js = re.search(r"<script>([\s\S]*?)</script>", old).group(1)

# ---------- 拆分数据层与逻辑层 ----------
logic_marker = "/* ============================================================\n * 逻辑层：设置、状态、LLM 编排、渲染、历史\n * ============================================================ */"
assert logic_marker in js, "logic marker missing"
data_layer = js[js.index("const BRAND_VOICES"):js.index(logic_marker)]
logic = js[js.index(logic_marker):]

# ---------- 移除将被替换的代码块 ----------
def cut(text, start_marker, end_marker):
    s = text.index(start_marker)
    e = text.index(end_marker)
    return text[:s] + text[e:]

logic = cut(logic, "/* ---------- 品牌名录与「与品牌对话」搜索 ---------- */", "/* ---------- 状态栏与轻提示 ---------- */")
logic = cut(logic, "/* ---------- 左侧对话历史栏 ---------- */", "/* 回看历史：瞬时渲染（不做打字机动画） */")
logic = cut(logic, "/* 回到新对话空状态 */", "/* ---------- 初始化 ---------- */")
s = logic.index("/* ---------- 初始化 ---------- */")
e = logic.index('document.addEventListener("DOMContentLoaded", init);')
e = logic.index("\n", e)  # 吃掉行尾
logic = logic[:s] + logic[e+1:]

# ---------- 注入 showStage 调用 ----------
logic = logic.replace(
    "  clearStatus();\n  const useDemo = forceDemo || settings.forceDemo || !settings.apiKey;",
    "  clearStatus();\n  showStage();\n  const useDemo = forceDemo || settings.forceDemo || !settings.apiKey;")
logic = logic.replace(
    "  clearStatus();\n  const lineup = currentLineup;",
    "  clearStatus();\n  showStage();\n  const lineup = currentLineup;")
logic = logic.replace(
    "  resetStage();\n  renderHistorySidebar(idx);",
    "  resetStage();\n  showStage();\n  renderHistorySidebar(idx);")
assert "showStage();" in logic, "showStage injection failed"

# ---------- 新增逻辑 ----------
extra_js = r'''
/* ---------- 页面视图切换（首页 / 对话） ---------- */
function showStage(){ $("homeView").classList.add("hidden"); $("stageView").classList.remove("hidden"); }
function showHome(){ $("stageView").classList.add("hidden"); $("homeView").classList.remove("hidden"); resetStage(); }

/* ---------- 暗色模式 ---------- */
const THEME_KEY = "brandRoundtableTheme";
function applyTheme(theme){
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_KEY, theme);
  $("darkToggle").textContent = theme === "dark" ? "☀️" : "🌙";
}
function initTheme(){ applyTheme(localStorage.getItem(THEME_KEY) || "light"); }

/* ---------- 更多菜单 / 使用说明 ---------- */
function openUsage(){
  const overlay = el("div","overlay");
  overlay.innerHTML = `<div class="modal"><h3>📖 使用说明</h3>
    <p>1. 在「自动圆桌」输入产品话题，点击「开始 →」，4 个品牌 + 1 位主持人会围绕它展开讨论。<br>
    2. 没有 API Key 时自动使用内置演示数据；点击左下角「⚙️ 设置」填入 Key 与模型名后可调用真实模型。<br>
    3. 在「与品牌对话」搜索或点击品牌，可把它加入阵容；输入任意名字后回车可创建自定义角色。<br>
    4. 「推荐圆桌」点击任意卡片可直接开始一场讨论。<br>
    5. 点击左侧对话历史可回看之前的结果。</p>
    <div class="row"><button id="uClose" class="btn">知道了</button></div></div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", e=>{ if(e.target===overlay) overlay.remove(); });
  overlay.querySelector("#uClose").onclick = ()=>overlay.remove();
}

/* ---------- 左侧导航：对话历史（emoji + 日期标签） ---------- */
const HISTORY_EMOJI = ["🎯","💡","🚀","🧩","🎲","🌶️","🍵","📦","✨","⚡"];
function dateLabel(ts){
  const t = new Date(ts), now = new Date();
  const d0 = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const d1 = new Date(t.getFullYear(), t.getMonth(), t.getDate());
  const diff = Math.round((d0 - d1) / 86400000);
  if(diff === 0) return "今天";
  if(diff === 1) return "昨天";
  return `${t.getMonth()+1}/${t.getDate()}`;
}
function renderHistorySidebar(activeIdx){
  const list = loadHistory();
  const q = ($("navSearch").value || "").trim().toLowerCase();
  const box = $("historyList");
  box.innerHTML = "";
  if(!list.length){ box.appendChild(el("div","h-empty","暂无对话历史\n完成一场圆桌或灵感卡后会出现在这里")); return; }
  let shown = 0;
  list.forEach((h,i)=>{
    if(q && !String(h.case||"").toLowerCase().includes(q)) return;
    shown++;
    const emoji = (h.mode||"").includes("灵感") ? "💡" : HISTORY_EMOJI[i % HISTORY_EMOJI.length];
    const item = el("div","h-item"+(i===activeIdx?" active":""),
      `<div class="h-emoji">${emoji}</div><div class="h-title">${escapeHtml(h.case)}</div><div class="h-date">${dateLabel(h.ts||Date.now())}</div>`);
    item.onclick = ()=>viewHistory(i);
    box.appendChild(item);
  });
  if(!shown) box.appendChild(el("div","h-empty","没有匹配的对话"));
}

/* ---------- 与品牌对话：标签筛选 + 角色卡片网格 ---------- */
const BRAND_TAG = { Fintech:"金融科技", AI:"AI", "Dev Tools":"开发工具", Gaming:"游戏", SaaS:"SaaS", Consumer:"消费品", B2B:"B2B" };
const BRAND_TAGS = ["全部","消费品","SaaS","开发工具","金融科技","游戏","AI","B2B"];
const FAV_KEY = "brandRoundtableFavs";
const CUSTOM_KEY = "brandRoundtableCustoms";
let brandQ = "", brandTag = "全部";

function loadFavs(){ try{ return JSON.parse(localStorage.getItem(FAV_KEY)||"[]"); }catch(e){ return []; } }
function saveFavs(f){ localStorage.setItem(FAV_KEY, JSON.stringify(f)); }
function loadCustoms(){ try{ return JSON.parse(localStorage.getItem(CUSTOM_KEY)||"[]"); }catch(e){ return []; } }
function saveCustoms(c){ localStorage.setItem(CUSTOM_KEY, JSON.stringify(c)); }
function customColor(name){
  let h = 0;
  for(const ch of name) h = (h*31 + ch.codePointAt(0)) % 360;
  return `hsl(${h},55%,50%)`;
}

function renderBrandTags(){
  const box = $("brandTags"); box.innerHTML = "";
  BRAND_TAGS.forEach(t=>{
    const tag = el("button","tag"+(t===brandTag?" active":""), t);
    tag.onclick = ()=>{ brandTag = t; renderBrandTags(); renderBrandGrid(); };
    box.appendChild(tag);
  });
}

function renderBrandGrid(){
  const grid = $("brandGrid"); grid.innerHTML = "";
  const q = brandQ.trim().toLowerCase();
  const favs = loadFavs();
  const items = [];
  BRAND_VOICES.forEach(v=>{
    const tag = BRAND_TAG[v.category] || "其他";
    if(brandTag !== "全部" && tag !== brandTag) return;
    if(q && !v.brand.toLowerCase().includes(q)) return;
    items.push({ name:v.brand, tag, color:BRAND_COLORS[v.brand]||"#6b7280" });
  });
  loadCustoms().forEach(c=>{
    if(brandTag !== "全部" && brandTag !== "自定义") return;
    if(q && !c.name.toLowerCase().includes(q)) return;
    items.push({ name:c.name, tag:"自定义", color:customColor(c.name) });
  });
  items.sort((a,b)=> (favs.includes(b.name)?1:0) - (favs.includes(a.name)?1:0));
  if(!items.length) grid.appendChild(el("div","h-empty","没有匹配的品牌，回车可创建自定义角色"));
  items.forEach(it=>{
    const isFav = favs.includes(it.name);
    const card = el("div","brand-card");
    card.innerHTML = `<div class="bc-top"><div class="bc-logo" style="background:${it.color}">${escapeHtml(it.name.charAt(0))}</div>
      <button class="bc-star${isFav?" fav":""}" title="收藏">${isFav?"★":"☆"}</button></div>
      <div class="bc-name">${escapeHtml(it.name)}</div>
      <span class="bc-cat">${escapeHtml(it.tag)}</span>
      <button class="bc-btn">开始对话</button>`;
    card.querySelector(".bc-star").onclick = ()=>toggleFav(it.name);
    card.querySelector(".bc-btn").onclick = ()=>addBrandToLineup(it.name);
    grid.appendChild(card);
  });
}

function toggleFav(name){
  const favs = loadFavs();
  const i = favs.indexOf(name);
  if(i >= 0) favs.splice(i,1); else favs.push(name);
  saveFavs(favs);
  renderBrandGrid();
  showToast(i >= 0 ? `已取消收藏 ${name}` : `已收藏 ${name}`);
}

function createRole(){
  const name = (typeof prompt === "function" ? prompt("输入自定义角色名（例如：蜜雪冰城）") : "") || "";
  const n = name.trim();
  if(!n) return;
  const customs = loadCustoms();
  if(customs.some(c=>c.name===n)){ showToast("该角色已存在"); return; }
  customs.push({name:n});
  saveCustoms(customs);
  renderBrandGrid();
  showToast(`已创建角色「${n}」`);
}

/* 把品牌放入当前阵容（替换第 4 位）；未知名字作为自定义品牌 */
function addBrandToLineup(name){
  if(!currentLineup) refreshPreview();
  const n = name.trim();
  if(!n) return;
  if(currentLineup.brands.includes(n) || currentLineup.host===n){ showToast(`「${n}」已在阵容中`); return; }
  currentLineup.brands[currentLineup.brands.length-1] = n;
  renderPreview();
  showToast(`已把「${n}」放入阵容`);
  $("inputPanel") && $("inputPanel").scrollIntoView({behavior:"smooth"});
}

/* ---------- 推荐圆桌（6 个预设 case） ---------- */
const RECOMMENDED = [
  { emoji:"🍹", title:"便携榨汁杯", desc:"3 秒出汁的通勤健康神器，怎么让年轻人天天带着它出门？", case:"便携榨汁杯：3 秒出汁、可拆卸清洗、USB 充电、随身携带，主打通勤与轻健康生活", industry:"Consumer" },
  { emoji:"⌚", title:"智能手环", desc:"把健康数据变成看得见的日常习惯，而不是另一个吃灰设备。", case:"智能手环：心率/睡眠/运动追踪，续航 14 天，主打健康习惯养成", industry:"Consumer" },
  { emoji:"🧰", title:"团队协作工具", desc:"把碎片化沟通收进一个工作台，让跨部门协作不再刷屏。", case:"团队协作工具：任务看板 + 文档 + 会议一体化，主打减少工具切换", industry:"SaaS" },
  { emoji:"🧪", title:"开发者测试平台", desc:"让每次版本上线前都更稳，开发者愿意主动写测试。", case:"开发者测试平台：自动生成测试用例、CI 集成、覆盖率看板，面向开发团队", industry:"DevTools" },
  { emoji:"💳", title:"数字钱包", desc:"年轻人的第一张全球卡：实时汇率、无手续费、费率透明。", case:"数字钱包：多币种账户、实时汇率、无隐藏手续费，主打全球自由消费", industry:"Fintech" },
  { emoji:"🤖", title:"AI 写作助手", desc:"写得快，也写得像你：一键调风格、查事实、改语气。", case:"AI 写作助手：长文写作、风格模仿、事实核查，面向内容创作者", industry:"AI" }
];
function renderRecommended(){
  const grid = $("recGrid"); grid.innerHTML = "";
  RECOMMENDED.forEach(r=>{
    const card = el("div","rec-card");
    card.innerHTML = `<div class="rec-emoji">${r.emoji}</div><div class="rec-title">${escapeHtml(r.title)}</div><div class="rec-desc">${escapeHtml(r.desc)}</div>`;
    card.onclick = ()=>{
      $("industrySelect").value = r.industry;
      refreshPreview();
      $("productInput").value = r.case;
      runRoundtable(false);
    };
    grid.appendChild(card);
  });
}

/* ---------- 初始化 ---------- */
function init(){
  initTheme();
  $("darkToggle").onclick = ()=>{ const cur = document.documentElement.getAttribute("data-theme")==="dark" ? "light" : "dark"; applyTheme(cur); };
  $("moreBtn").onclick = e=>{ e.stopPropagation(); $("moreMenu").classList.toggle("hidden"); };
  document.addEventListener("click", e=>{
    if(typeof e.target.closest === "function" && e.target.closest("#moreWrap")) return;
    $("moreMenu").classList.add("hidden");
  });
  $("moreMenu").querySelectorAll(".menu-item").forEach(n=>n.onclick = ()=>{
    if(n.dataset.act === "clear"){ saveHistoryList([]); renderHistorySidebar(); showToast("历史已清空"); }
    if(n.dataset.act === "usage") openUsage();
  });
  $("supportBtn").onclick = openUsage;
  $("langSelect").value = "中文";

  $("btnNewChat").onclick = showHome;
  $("navSearch").addEventListener("input", ()=>renderHistorySidebar());
  $("btnSettings").onclick = openSettings;

  const sel = $("industrySelect");
  sel.innerHTML = Object.keys(INDUSTRY_LINEUP).map(k=>`<option value="${k}">${escapeHtml(INDUSTRY_LINEUP[k].label)}</option>`).join("");
  sel.value = "Consumer";
  sel.onchange = refreshPreview;
  $("btnShuffle").onclick = shuffleLineup;
  $("btnRoundtable").onclick = ()=>runRoundtable(false);
  $("btnCards").onclick = runCards;
  $("btnStop").onclick = ()=>{ if(abortCtrl) abortCtrl.abort(); skipAnim = true; };
  $("btnBackHome").onclick = showHome;
  $("fileInput").addEventListener("change", e=>{ handleFiles(e.target.files); e.target.value = ""; });

  $("brandSearch").addEventListener("input", e=>{ brandQ = e.target.value; renderBrandGrid(); });
  $("brandSearch").addEventListener("keydown", e=>{
    if(e.key !== "Enter") return;
    const val = e.target.value.trim();
    if(!val) return;
    const known = BRAND_VOICES.find(b=>b.brand.toLowerCase()===val.toLowerCase());
    if(known){ addBrandToLineup(known.brand); }
    else {
      const customs = loadCustoms();
      if(!customs.some(c=>c.name===val)){ customs.push({name:val}); saveCustoms(customs); showToast(`已创建角色「${val}」`); }
      addBrandToLineup(val);
    }
    e.target.value = "";
    brandQ = "";
    renderBrandGrid();
  });
  $("createRoleBtn").onclick = createRole;
  $("stage").addEventListener("click", ()=>{ skipAnim = true; });

  refreshPreview();
  renderRecommended();
  renderBrandTags();
  renderBrandGrid();
  renderHistorySidebar();
  $("keyHint").classList.toggle("hidden", !!(settings.apiKey||settings.forceDemo));
}
document.addEventListener("DOMContentLoaded", init);
'''

new_script = data_layer + "\n" + logic.rstrip() + "\n\n" + extra_js

# ---------- 新 HTML 骨架 + CSS ----------
css = r'''
/* ===== 设计变量（浅色 / 暗色） ===== */
:root{
  --bg:#fafafa; --card:#ffffff; --border:#ececf0; --text:#1f2329; --muted:#8a8f98;
  --primary:#e5484d; --primary-2:#d64045; --primary-bg:#fdecec;
  --radius-card:8px; --radius-btn:6px;
  --shadow:0 1px 2px rgba(0,0,0,.04);
  --shadow-hover:0 8px 24px rgba(0,0,0,.10);
  --hover:#f4f4f6;
}
html[data-theme="dark"]{
  --bg:#151619; --card:#1e2025; --border:#2c2f36; --text:#e8eaed; --muted:#989da6;
  --hover:#262932; --primary-bg:#3a2325;
  --shadow-hover:0 8px 24px rgba(0,0,0,.45);
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);font-size:13px;line-height:1.6;-webkit-font-smoothing:antialiased}
.app{min-width:1024px}
button{font-family:inherit}
.hidden{display:none!important}

/* ===== 顶部栏 56px ===== */
.topbar{height:56px;display:flex;align-items:center;justify-content:space-between;padding:0 18px;background:var(--card);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:20}
.logo{font-size:16px;font-weight:800;display:flex;align-items:center;gap:8px}
.logo .brand{color:var(--primary)}
.top-right{display:flex;align-items:center;gap:6px}
.hbtn{background:transparent;border:1px solid transparent;color:var(--text);font-size:13px;cursor:pointer;padding:6px 10px;border-radius:var(--radius-btn);display:flex;align-items:center;gap:5px}
.hbtn:hover{background:var(--hover)}
.lang-sel{border:1px solid var(--border);border-radius:var(--radius-btn);padding:5px 8px;font-size:13px;background:var(--card);color:var(--text);outline:none;cursor:pointer}
.dropdown{position:relative}
.menu{position:absolute;right:0;top:36px;background:var(--card);border:1px solid var(--border);border-radius:8px;box-shadow:var(--shadow-hover);min-width:140px;padding:4px;z-index:30}
.menu-item{padding:7px 10px;border-radius:6px;cursor:pointer;font-size:13px;color:var(--text)}
.menu-item:hover{background:var(--hover)}

/* ===== 两栏布局：240px 导航 + 弹性主区 ===== */
.layout{display:flex;min-height:calc(100vh - 56px)}
.nav{width:240px;flex:none;background:var(--card);border-right:1px solid var(--border);display:flex;flex-direction:column;position:sticky;top:56px;height:calc(100vh - 56px)}
.nav-pad{padding:12px 12px 4px}
.btn-new{width:100%;background:var(--primary);color:#fff;border:none;border-radius:var(--radius-btn);padding:9px 0;font-size:13.5px;font-weight:600;cursor:pointer;margin-bottom:10px}
.btn-new:hover{background:var(--primary-2)}
.nav-search{position:relative;margin-bottom:10px}
.nav-search .icon{position:absolute;left:9px;top:50%;transform:translateY(-50%);font-size:12px;opacity:.7;pointer-events:none}
.nav-search input{width:100%;border:1px solid var(--border);border-radius:var(--radius-btn);padding:7px 8px 7px 28px;font-size:13px;background:var(--bg);color:var(--text);outline:none}
.nav-search input:focus{border-color:var(--primary)}
.nav-label{font-size:12px;font-weight:700;color:var(--muted);padding:4px 6px}
.history{flex:1;overflow:auto;padding:2px 8px 8px}
.h-item{display:flex;align-items:center;gap:8px;padding:7px 8px;border-radius:8px;cursor:pointer}
.h-item:hover{background:var(--hover)}
.h-item.active{background:var(--primary-bg)}
.h-emoji{width:28px;height:28px;border-radius:6px;background:var(--hover);display:flex;align-items:center;justify-content:center;font-size:15px;flex:none}
.h-title{flex:1;font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.h-date{font-size:11px;color:var(--muted);flex:none}
.h-empty{font-size:12.5px;color:var(--muted);padding:8px;line-height:1.5}
.nav-foot{margin-top:auto;border-top:1px solid var(--border);padding:8px 12px}
.btn-settings{width:100%;display:flex;align-items:center;gap:8px;background:transparent;border:none;color:var(--text);font-size:13px;cursor:pointer;padding:8px;border-radius:var(--radius-btn)}
.btn-settings:hover{background:var(--hover)}

/* ===== 主内容 ===== */
.main{flex:1;min-width:0;padding:20px 26px}
.block{margin-bottom:30px}
.block-title{font-size:15px;font-weight:800;margin-bottom:12px}

/* 区块 1：自动圆桌 */
.big-input-wrap{position:relative}
.big-input{width:100%;min-height:76px;border:1px solid var(--border);border-radius:var(--radius-card);padding:12px 14px;font-size:14px;resize:vertical;background:var(--card);color:var(--text);outline:none;transition:border-color .15s, box-shadow .15s}
.big-input:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(229,72,77,.08)}
.start-btn{position:absolute;right:10px;bottom:10px;background:var(--primary);color:#fff;border:none;border-radius:var(--radius-btn);padding:8px 16px;font-size:13px;font-weight:600;cursor:pointer}
.start-btn:hover{background:var(--primary-2)}
.toolbar{display:flex;align-items:center;gap:10px;margin-top:10px;flex-wrap:wrap}
.toolbar label{font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px}
.toolbar select{font-size:12.5px;border:1px solid var(--border);border-radius:var(--radius-btn);padding:5px 8px;background:var(--card);color:var(--text);outline:none}
.toolbar-sep{width:1px;height:18px;background:var(--border)}
.preview-label{font-size:12px;color:var(--muted);font-weight:600}
.btn{border:1px solid var(--border);background:var(--card);color:var(--text);padding:6px 12px;border-radius:var(--radius-btn);font-size:12.5px;cursor:pointer;transition:.15s}
.btn:hover{border-color:var(--primary);color:var(--primary)}
.btn.small{padding:5px 10px;font-size:12px}
.btn.danger{color:var(--primary);border-color:#f3c2c4}
.btn.danger:hover{background:var(--primary-bg)}
.chips{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.chip{display:inline-flex;align-items:center;gap:6px;background:var(--hover);border:1px solid var(--border);padding:3px 10px;border-radius:999px;font-size:12px;font-weight:500}
.chip .dot{width:8px;height:8px;border-radius:50%;flex:none}
.chip.host{background:var(--primary-bg);border-color:#f3c2c4;color:var(--primary)}
.chip .host-tag{font-size:10.5px;font-weight:700}
.hint-bar{margin-top:12px;font-size:12px;color:#92400e;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:8px 12px}

/* 区块 2：推荐圆桌 */
.rec-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.rec-card{border:1px solid var(--border);border-radius:var(--radius-card);padding:14px;background:var(--card);cursor:pointer;transition:box-shadow .15s, border-color .15s}
.rec-card:hover{box-shadow:var(--shadow-hover);border-color:#e8d7d8}
.rec-emoji{font-size:24px;margin-bottom:10px}
.rec-title{font-size:14px;font-weight:700}
.rec-desc{font-size:12px;color:var(--muted);margin-top:5px;line-height:1.55}

/* 区块 3：与品牌对话 */
.brand-search-row{display:flex;gap:10px;align-items:center;margin-bottom:12px}
.brand-search-row .nav-search{flex:1;margin:0}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.tag{padding:4px 13px;border-radius:999px;font-size:12.5px;border:1px solid var(--border);color:var(--muted);cursor:pointer;background:transparent;transition:.15s}
.tag:hover{border-color:var(--primary);color:var(--primary)}
.tag.active{background:var(--primary);color:#fff;border-color:var(--primary)}
.brand-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.brand-card{border:1px solid var(--border);border-radius:var(--radius-card);background:var(--card);display:flex;flex-direction:column;transition:box-shadow .15s, border-color .15s;padding:12px}
.brand-card:hover{box-shadow:var(--shadow-hover)}
.bc-top{display:flex;align-items:flex-start;gap:10px;margin-bottom:8px}
.bc-logo{width:36px;height:36px;border-radius:8px;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:16px;flex:none}
.bc-star{margin-left:auto;border:none;background:none;font-size:17px;cursor:pointer;color:#c9cdd4;line-height:1;padding:2px}
.bc-star.fav{color:#f5b301}
.bc-name{font-size:14px;font-weight:700}
.bc-cat{display:inline-block;margin-top:3px;padding:2px 10px;border-radius:999px;background:var(--hover);color:var(--muted);font-size:11px}
.bc-btn{margin-top:12px;width:100%;padding:7px 0;border:1px solid var(--border);border-radius:var(--radius-btn);background:transparent;color:var(--text);font-size:12.5px;cursor:pointer;transition:.15s}
.bc-btn:hover{border-color:var(--primary);color:var(--primary);background:var(--primary-bg)}

/* ===== 对话视图 ===== */
.stage-head{display:flex;align-items:center;gap:12px;margin-bottom:14px;flex-wrap:wrap}
.stage-head .status{margin-top:0}
.status{padding:8px 14px;border-radius:8px;background:var(--primary-bg);color:var(--primary);font-size:12.5px;display:flex;align-items:center;gap:8px}
.status.err{background:#fdecec;color:#b91c1c}
.status.ok{background:#ecfdf5;color:#047857}
.spinner{width:14px;height:14px;border:2px solid #f3c2c4;border-top-color:var(--primary);border-radius:50%;animation:spin .8s linear infinite;flex:none}
@keyframes spin{to{transform:rotate(360deg)}}
.stage{min-height:200px}

/* ===== 聊天气泡 ===== */
.section-title{display:flex;align-items:center;gap:10px;margin:22px 0 12px;font-size:14.5px;font-weight:700}
.section-title .bar{width:4px;height:16px;border-radius:2px;background:var(--primary)}
.case-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-card);padding:14px 16px;box-shadow:var(--shadow);margin-bottom:4px}
.case-card .case-title{font-weight:700;font-size:14.5px;margin-bottom:3px}
.case-card .case-meta{font-size:12px;color:var(--muted)}
.bubble-row{display:flex;gap:10px;margin:10px 0;align-items:flex-start;opacity:0;transform:translateY(8px);animation:rise .3s forwards}
@keyframes rise{to{opacity:1;transform:none}}
.avatar{width:36px;height:36px;border-radius:8px;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:15px;flex:none;box-shadow:0 1px 4px rgba(0,0,0,.15)}
.bubble-body{max-width:78%}
.bubble-head{display:flex;align-items:baseline;gap:8px;margin-bottom:3px;flex-wrap:wrap}
.bubble-name{font-size:13.5px;font-weight:700}
.bubble-cat{font-size:11px;color:var(--muted)}
.bubble{background:var(--card);border:1px solid var(--border);border-radius:4px 12px 12px 12px;padding:11px 14px;font-size:13.5px;box-shadow:var(--shadow)}
.bubble .tagline{display:block;margin-top:7px;padding-top:7px;border-top:1px dashed var(--border);color:var(--primary);font-weight:600;font-style:italic}
.angle-chip{display:inline-block;font-size:11px;font-weight:600;color:var(--primary);background:var(--primary-bg);border-radius:999px;padding:2px 9px;margin-bottom:5px}
.host-row{justify-content:center}
.host-card{max-width:86%;background:var(--primary-bg);border:1px solid #f3c2c4;border-radius:12px;padding:13px 16px;font-size:14px;text-align:center;box-shadow:var(--shadow)}
.host-card .host-label{font-size:11px;font-weight:700;color:var(--primary);letter-spacing:2px;margin-bottom:4px}
.target-chip{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:600;background:var(--hover);border:1px solid var(--border);border-radius:999px;padding:2px 9px;margin:4px 8px 5px 0}
.stance{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:700;border-radius:999px;padding:2px 9px;margin:4px 0 5px}
.stance.agree{color:#047857;background:#ecfdf5;border:1px solid #a7f3d0}
.stance.disagree{color:#b91c1c;background:#fdecec;border:1px solid #fecaca}
.stance.build-on{color:var(--primary);background:var(--primary-bg);border:1px solid #f3c2c4}

/* ===== 灵感卡 ===== */
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}
.inspire-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-card);padding:16px;box-shadow:var(--shadow);border-top:4px solid var(--bc,var(--primary))}
.inspire-card .card-brand{display:flex;align-items:center;gap:8px;font-weight:700;font-size:14.5px}
.inspire-card .card-cat{font-size:11px;color:var(--muted);font-weight:500;margin-left:auto}
.inspire-card ul.headline{margin:12px 0 10px;list-style:none}
.inspire-card ul.headline li{font-size:13.5px;font-weight:600;color:var(--primary-2);margin:6px 0;border-left:3px solid var(--bc,var(--primary));padding-left:8px}
.inspire-card .why{font-size:12px;color:var(--muted);line-height:1.7}

/* ===== 主持人总结 ===== */
.summary-card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius-card);padding:18px;box-shadow:var(--shadow);margin-top:14px}
.summary-intro{font-size:14.5px;text-align:center;margin-bottom:6px}
.sum-block{margin-top:16px}
.sum-title{font-size:12.5px;font-weight:700;color:var(--muted);letter-spacing:1px;margin-bottom:9px}
table.mini{width:100%;border-collapse:collapse;font-size:13px}
table.mini th,table.mini td{border:1px solid var(--border);padding:7px 10px;text-align:left}
table.mini th{background:var(--hover);font-weight:600}
ul.sum{list-style:none;display:flex;flex-direction:column;gap:8px}
ul.sum li{padding-left:20px;position:relative;font-size:13.5px}
ul.sum li::before{content:"✓";position:absolute;left:0;color:#10b981;font-weight:700}
ul.sum.diff li::before{content:"⚡";color:#f59e0b}
.action-item{display:flex;gap:10px;align-items:flex-start;background:var(--hover);border:1px solid var(--border);border-radius:8px;padding:9px 13px;font-size:13.5px;margin-bottom:8px}
.action-item .num{flex:none;width:20px;height:20px;border-radius:50%;background:var(--primary);color:#fff;font-size:11px;font-weight:700;display:flex;align-items:center;justify-content:center}

/* ===== 附件 ===== */
.attach-list{display:flex;flex-direction:column;gap:5px;margin-top:8px}
.attach-item{display:flex;align-items:center;gap:8px;background:var(--hover);border:1px solid var(--border);border-radius:8px;padding:5px 11px;font-size:12.5px}
.attach-item .a-name{font-weight:600;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.attach-item .a-meta{color:var(--muted);font-size:11px;flex:none}
.attach-item .a-del{margin-left:auto;border:none;background:none;color:var(--muted);cursor:pointer;font-size:13px;padding:2px 6px;border-radius:5px}
.attach-item .a-del:hover{color:var(--primary);background:var(--primary-bg)}

/* ===== 弹窗 / 提示 ===== */
.overlay{position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;align-items:center;justify-content:center;z-index:50;padding:20px}
.modal{background:var(--card);border-radius:10px;width:100%;max-width:460px;padding:20px;box-shadow:0 20px 60px rgba(0,0,0,.2);max-height:85vh;overflow:auto}
.modal h3{margin-bottom:12px;font-size:16px}
.modal label{display:block;font-size:12.5px;color:var(--muted);font-weight:600;margin:12px 0 5px}
.modal .inp{width:100%;font-family:inherit;font-size:13.5px;border:1px solid var(--border);border-radius:var(--radius-btn);padding:8px 10px;background:var(--bg);color:var(--text);outline:none}
.modal .inp:focus{border-color:var(--primary)}
.modal .row{display:flex;gap:10px;margin-top:16px;justify-content:flex-end}
.modal p{font-size:13px;line-height:1.7}
.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1f2937;color:#fff;padding:9px 16px;border-radius:8px;font-size:12.5px;z-index:99;box-shadow:0 8px 30px rgba(0,0,0,.3);opacity:0;transition:.25s;pointer-events:none;max-width:86vw}
.toast.show{opacity:1}
.foot{border-top:1px solid var(--border);margin-top:8px;padding:14px 0;text-align:center;color:var(--muted);font-size:11.5px}
'''

html_body = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>品牌 Talk</title>
<style>
__CSS__
</style>
</head>
<body>
<div class="app">

  <!-- 顶部栏 56px -->
  <header class="topbar">
    <div class="logo">🪑 <span class="brand">品牌 Talk</span></div>
    <div class="top-right">
      <select id="langSelect" class="lang-sel" title="输出语言">
        <option value="中文">中文</option>
        <option value="English">English</option>
        <option value="双语">双语</option>
      </select>
      <button id="darkToggle" class="hbtn" title="切换暗色模式">🌙</button>
      <div class="dropdown" id="moreWrap">
        <button id="moreBtn" class="hbtn">更多 ▾</button>
        <div id="moreMenu" class="menu hidden">
          <div class="menu-item" data-act="usage">使用说明</div>
          <div class="menu-item" data-act="clear">清空历史</div>
        </div>
      </div>
      <button id="supportBtn" class="hbtn">支持</button>
    </div>
  </header>

  <div class="layout">

    <!-- 左侧导航 240px -->
    <aside class="nav">
      <div class="nav-pad">
        <button id="btnNewChat" class="btn-new">＋ 新对话</button>
        <div class="nav-search">
          <span class="icon">🔍</span>
          <input id="navSearch" type="text" placeholder="搜索对话">
        </div>
        <div class="nav-label">对话历史</div>
      </div>
      <div id="historyList" class="history"></div>
      <div class="nav-foot">
        <button id="btnSettings" class="btn-settings">⚙️ 设置</button>
      </div>
    </aside>

    <!-- 右侧主内容 -->
    <main class="main">

      <!-- 首页：三个区块 -->
      <div id="homeView">

        <!-- 区块 1：自动圆桌 -->
        <section id="inputPanel" class="block">
          <div class="block-title">自动圆桌</div>
          <div class="big-input-wrap">
            <textarea id="productInput" class="big-input" rows="3" placeholder="输入话题，AI 自动匹配嘉宾..."></textarea>
            <button id="btnRoundtable" class="start-btn">开始 →</button>
          </div>
          <div class="toolbar">
            <label>行业
              <select id="industrySelect"></select>
            </label>
            <label>市场
              <select id="marketSelect">
                <option value="全球">全球</option>
                <option value="中国">中国</option>
                <option value="欧美">欧美</option>
                <option value="日韩">日韩</option>
              </select>
            </label>
            <span class="toolbar-sep"></span>
            <span class="preview-label">阵容</span>
            <div id="brandPreview" class="chips"></div>
            <button id="btnShuffle" class="btn small" title="随机换一组品牌">🔄 换一换</button>
            <button id="btnCards" class="btn small">💡 只要灵感卡</button>
            <label class="btn small" for="fileInput">📎 资料</label>
            <input id="fileInput" type="file" multiple accept=".txt,.md,.markdown,.csv,.tsv,.json,.log,.text" class="hidden">
          </div>
          <div id="attachList" class="attach-list"></div>
          <div id="keyHint" class="hint-bar hidden">🔑 未检测到 API Key：将自动使用内置演示数据。点击左下角「⚙️ 设置」填入 Key 即可调用真实模型。</div>
        </section>

        <!-- 区块 2：推荐圆桌 -->
        <section class="block">
          <div class="block-title">推荐圆桌</div>
          <div id="recGrid" class="rec-grid"></div>
        </section>

        <!-- 区块 3：与品牌对话 -->
        <section class="block">
          <div class="block-title">与品牌对话</div>
          <div class="brand-search-row">
            <div class="nav-search">
              <span class="icon">🔍</span>
              <input id="brandSearch" type="text" placeholder="搜索或输入任意品牌...">
            </div>
            <button id="createRoleBtn" class="btn">＋ 创建角色</button>
          </div>
          <div id="brandTags" class="tags"></div>
          <div id="brandGrid" class="brand-grid"></div>
        </section>

      </div>

      <!-- 对话视图 -->
      <div id="stageView" class="hidden">
        <div class="stage-head">
          <button id="btnBackHome" class="btn small">← 返回</button>
          <div id="statusBar" class="status hidden"></div>
          <button id="btnStop" class="btn danger small hidden">停止</button>
        </div>
        <div id="stage" class="stage"></div>
      </div>

    </main>
  </div>

  <footer class="foot">仅供创意灵感与学习，与各品牌无关；不生成冒充品牌官方传播的内容。数据来源：HuggingFace manifesta/brandvoice-marketing-briefs (CC0)。</footer>
</div>

<div id="toast" class="toast"></div>

<script>
__SCRIPT__
</script>
</body>
</html>
'''

new_html = html_body.replace("__CSS__", css).replace("__SCRIPT__", new_script)
open("/Users/job/Documents/Codex/2026-07-31/ni/outputs/brand-roundtable.html", "w", encoding="utf-8").write(new_html)
print("rebuilt:", len(new_html.splitlines()), "lines,", len(new_html)//1024, "KB")

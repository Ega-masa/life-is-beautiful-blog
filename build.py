#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Life is beautiful 学びの場 — 静的サイト生成スクリプト

data/themes.json（学習スペース getlibrary の出力が正本）から、
index.html / unread.html / t/<theme_id>.html / glossary.html /
deliveries.html / issues.html / genres.html / genre/<slug>.html /
later.html / memo.html を生成する。

構成の方針:
- 全ページ共通で上部に固定（sticky）ヘッダーを持ち、左のハンバーガーから
  各一覧ページへ移動でき、右の「トップに戻る」が常時使える。
- トップは「続きはここから＋未読リスト＋各一覧への導線」に絞り、
  一覧の詳細は専用ページ（配信ごと=deliveries、号ごと=issues、
  未読=unread、ジャンル=genres/genre/*）へ分離する（段階的開示）。
- テーマにはジャンル（genre、Notion「ビジネス」DBの大カテゴリ体系が土台）と
  AI評価（evaluation: 新規性・面白さ・話題性・関連度の4軸×25点=100点）を付け、
  一覧に合計点バッジ、テーマページに評価パネルを表示する。
  話題性は題材の世間的な注目度をもとにした目安（個別のSNS調査はしていない）。
- 「後で読む」「いらない」の選択とテーマごとの自由記載メモは端末側 localStorage
  で管理する（既読 lib_read_v1 とは別キー: 選択 lib_pref_v1、メモ lib_memo_v1）。
  メモはテーマページのメモ欄で書き、memo.html（メモ一覧）でも編集・削除でき、
  入力のたびに自動保存される。要点チェック機能は 2026-11-24 の主君の決定で
  廃止した（旧キー lib_checks_v1 のデータは端末側に残るが、UI からは参照しない）。
  「いらない」はトップの続き計算と未読リストから除外される。
- テーマページの用語解説は、用語集へ誘導せず定義文をその場に全文表示する
  （定義が無い項目は、他テーマで定義済みの用語から補完する）。
- テーマページの末尾には、その号の配信状況を「配信済みユニット数／全ユニット数」
  の分数で表示する。全体数（分母）は themes.json の issues[].unit_total に保持し、
  分子は themes の delivered 件数から自動計算する。unit_total が無い号では表示しない。
- 今後の配信ジョブは、themes.json を更新してから `python3 build.py` を
  再実行すればサイト全体が再生成される。

スライド画像は Base64 データURIとしてテーマページの HTML に埋め込む
（GitHub コネクタが UTF-8 テキストしか push できないため、生成物は
テキストファイルのみで構成する。PNG 本体は hidden_files 側が正本）。
"""
import base64
import json
import re
import html
from pathlib import Path

BASE = Path(__file__).resolve().parent
DATA = BASE / "data" / "themes.json"
HIDDEN = BASE.parent / "hidden_files"
OUT_T = BASE / "t"
OUT_G = BASE / "genre"
ASSETS = BASE / "assets"

# ジャンル体系（主君の Notion「ビジネス」DB の大カテゴリが土台）
GENRES = [
    ("起業・新規事業", "startup"),
    ("企業ケース", "cases"),
    ("経営・事業戦略", "strategy"),
    ("投資・金融", "finance"),
    ("思考法・キャリア", "thinking"),
    ("マーケティング・営業", "marketing"),
    ("テクノロジー・AI", "tech"),
    ("社会・時事", "society"),
]
GENRE_SLUG = dict(GENRES)

# テーマID -> スライド画像（hidden_files からの相対パス）
# 対応は生成スクリプトとファイル名から特定したものだけを載せる。
#  - 6/2号 SDS版（1テーマ1枚）: visuals_2026-11-21-sds/slide_0602_t{1,2,3}.png
#  - 6/2号 記事コーナー: visuals_0602/slide3.png（囲碁・金融・SaaS＝記事コーナー中心）
#    ※ slide4.png は「小さなAIとメモリ革命＋質問コーナー」の合体スライドのため id5 には付けない
#  - 6/9号 夕の回: visuals_2026-06-09-pm/slide{1,2,3,4}.png（生成スクリプトのタイトルで特定）
#  - 11/17号 テーマ2・3: visuals_2026-11-21-pm/slide_theme{2,3}.png（make_slides_v3.py のタイトルで特定）
#  - 11/17号 テーマ1（Starship）: visuals_2026-11-21-pm/slide_theme1.png
#    ※ 当時単独スライドが無かったため、2026-11-24 の監査訂正で配信データから
#      同体裁で新規作成したもの（make_slide_theme1.py）。候補だった
#      slide_1117_pm.png はテーマ2・3の合体スライドなので id6 には付けない
#  - 11/17号 テーマ4・5: visuals_2026-11-22-am/slide_1117_am_t{4,5}.png
#  - 11/17号 テーマ6・記事グループA: visuals_2026-11-23-am/slide_1117_am_t6.png / _t7a.png
#  - 11/17号 記事グループB・C: visuals_2026-11-24-am/slide_1117_am_t7b.png / _t7c.png
SLIDES = {
    1: "visuals_2026-11-21-sds/slide_0602_t1.png",
    2: "visuals_2026-11-21-sds/slide_0602_t2.png",
    3: "visuals_2026-11-21-sds/slide_0602_t3.png",
    4: "visuals_0602/slide3.png",
    15: "visuals_2026-06-09-pm/slide1.png",
    16: "visuals_2026-06-09-pm/slide2.png",
    18: "visuals_2026-06-09-pm/slide3.png",
    19: "visuals_2026-06-09-pm/slide4.png",
    22: "visuals_2026-06-09-pm/slide5.png",
    23: "visuals_2026-06-09-pm/slide6.png",
    6: "visuals_2026-11-21-pm/slide_theme1.png",
    7: "visuals_2026-11-21-pm/slide_theme2.png",
    8: "visuals_2026-11-21-pm/slide_theme3.png",
    9: "visuals_2026-11-22-am/slide_1117_am_t4.png",
    10: "visuals_2026-11-22-am/slide_1117_am_t5.png",
    11: "visuals_2026-11-23-am/slide_1117_am_t6.png",
    17: "visuals_2026-11-23-am/slide_1117_am_t7a.png",
    20: "visuals_2026-11-24-am/slide_1117_am_t7b.png",
    21: "visuals_2026-11-24-am/slide_1117_am_t7c.png",
}

CSS = """
:root{--ink:#1c2733;--sub:#5a6a7a;--line:#dde4ea;--bg:#f6f8fa;--card:#fff;--accent:#1a5fb4;--badge:#e8f0fa;--read:#8a97a5;--newbg:#e7f6ec;--newink:#137333;--newline:#bfe6cc}
@media (prefers-color-scheme:dark){:root{--ink:#e8edf2;--sub:#9fb0c0;--line:#33404d;--bg:#141a20;--card:#1e262f;--accent:#6aa6e8;--badge:#26374a;--read:#66727e;--newbg:#1d3a28;--newink:#7fd79a;--newline:#2c5a3c}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Hiragino Kaku Gothic ProN","Noto Sans JP","Yu Gothic",sans-serif;line-height:1.75;font-size:16px}
.wrap{max-width:760px;margin:0 auto;padding:16px 14px 48px}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header.site{padding:10px 0 4px}
header.site .home{font-size:13px;color:var(--sub)}
h1{font-size:22px;line-height:1.45;margin:6px 0 10px}
h2{font-size:18px;margin:28px 0 10px;padding-bottom:4px;border-bottom:2px solid var(--line)}
h3{font-size:16px;margin:20px 0 6px}
.meta{color:var(--sub);font-size:13px}
.badge{display:inline-block;background:var(--badge);color:var(--accent);border-radius:999px;padding:1px 10px;font-size:12px;margin:2px 4px 2px 0}
.badge.read{background:transparent;border:1px solid var(--line);color:var(--read)}
.badge.score{background:var(--accent);color:#fff;font-weight:700}
.badge.newb{background:var(--newbg);color:var(--newink);border:1px solid var(--newline);font-weight:700}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0}
.card.big{border:2px solid var(--accent);padding:18px}
.card .ttl{font-weight:700;font-size:17px;line-height:1.5}
.card.big .ttl{font-size:19px}
ul.list{list-style:none;margin:0;padding:0}
ul.list li{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:8px 0}
ul.list li.is-read{opacity:.62}
ul.list .ttl{font-weight:600}
ul.points{margin:6px 0 6px 1.2em;padding:0}
ul.points li{margin:5px 0}
img.slide{width:100%;height:auto;border-radius:10px;border:1px solid var(--line);margin:10px 0}
details.fulltext{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;margin:14px 0}
details.fulltext summary{cursor:pointer;font-weight:700;color:var(--accent)}
details.fulltext .ft{margin-top:8px;font-size:15px}
details.fulltext .ft h4{font-size:15px;margin:14px 0 4px}
details.fulltext .ft p{margin:6px 0}
.note{background:var(--badge);border-radius:10px;padding:10px 14px;font-size:14px;margin:12px 0}
.gloss dt{font-weight:700;margin-top:10px}
.gloss dd{margin:2px 0 0 1em;color:var(--ink)}
button.next{width:100%;background:var(--accent);color:#fff;border:0;border-radius:12px;padding:16px;font-size:17px;font-weight:700;cursor:pointer;margin:22px 0 8px}
button.next:active{opacity:.85}
.navrow{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.navrow a{flex:1;min-width:140px;text-align:center;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px;font-size:14px}
footer{color:var(--sub);font-size:12px;margin-top:36px;text-align:center}
.stickyhead{position:sticky;top:0;z-index:60;background:var(--card);border-bottom:1px solid var(--line)}
.topbar-in{max-width:760px;margin:0 auto;display:flex;align-items:center;gap:10px;padding:8px 14px}
.burger{background:var(--badge);border:1px solid var(--line);border-radius:8px;font-size:17px;line-height:1;padding:7px 11px;cursor:pointer;color:var(--ink)}
.topbar-title{font-weight:700;font-size:14px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.topbar-home{font-size:13px;font-weight:700;white-space:nowrap}
.menu-in{max-width:760px;margin:0 auto;padding:4px 14px 10px;display:flex;flex-wrap:wrap;gap:6px}
.menu-in a{flex:1 1 40%;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:14px;text-align:center;color:var(--ink)}
.rowbtns{display:inline-flex;gap:6px;margin:4px 0 0 0;vertical-align:middle}
button.mini{background:var(--card);border:1.5px solid var(--accent);color:var(--accent);border-radius:999px;padding:4px 13px;font-size:12.5px;font-weight:700;cursor:pointer}
button.mini.on{background:var(--accent);color:#fff}
button.mini.skipb{border-color:var(--sub);color:var(--sub)}
button.mini.skipb.on{background:var(--sub);color:#fff}
.rowbtns.big{display:flex;margin:12px 0 4px}
.rowbtns.big button.mini{font-size:14.5px;padding:9px 20px}
.eval{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:14px 0}
.eval-head{display:flex;justify-content:space-between;align-items:baseline;font-weight:700;font-size:15px}
.eval-total{font-size:23px;color:var(--accent)}
.eval-total small{font-size:13px;color:var(--sub)}
.eval-grid{display:grid;grid-template-columns:1fr 1fr;gap:4px 16px;margin:8px 0;font-size:14px}
.eval-grid b{color:var(--accent)}
.eval-comment{font-size:14px;margin:6px 0 0}
.memo-sec{margin:22px 0 4px}
.memo-sec textarea{width:100%;min-height:110px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:15px;line-height:1.7;font-family:inherit;resize:vertical}
.memo-item textarea{width:100%;min-height:90px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:15px;line-height:1.7;font-family:inherit;resize:vertical;margin-top:8px}
.memo-status{font-size:12.5px;color:var(--sub);margin-top:4px;min-height:1.4em}
.memo-del{margin-top:2px}
"""

JS = """
const KEY='lib_read_v1';
function getRead(){try{return JSON.parse(localStorage.getItem(KEY))||[]}catch(e){return[]}}
function setRead(a){localStorage.setItem(KEY,JSON.stringify(a))}
function markRead(id){const r=getRead();if(!r.includes(id)){r.push(id);setRead(r)}}
function unmarkRead(id){setRead(getRead().filter(x=>x!==id))}
const PREF_KEY='lib_pref_v1';
function getPref(){try{const p=JSON.parse(localStorage.getItem(PREF_KEY));if(p&&Array.isArray(p.later)&&Array.isArray(p.skip))return p;}catch(e){}return{later:[],skip:[]}}
function setPref(p){localStorage.setItem(PREF_KEY,JSON.stringify(p))}
function getLater(){return getPref().later}
function getSkip(){return getPref().skip}
function toggleIn(a,id){return a.includes(id)?a.filter(function(x){return x!==id}):a.concat([id])}
function toggleLater(id){const p=getPref();p.later=toggleIn(p.later,id);setPref(p);refreshPrefUI()}
function toggleSkip(id){const p=getPref();p.skip=toggleIn(p.skip,id);setPref(p);refreshPrefUI()}
const MEMO_KEY='lib_memo_v1';
function getMemos(){try{const m=JSON.parse(localStorage.getItem(MEMO_KEY));if(m&&typeof m==='object'&&!Array.isArray(m))return m;}catch(e){}return{}}
function setMemos(m){localStorage.setItem(MEMO_KEY,JSON.stringify(m))}
function saveMemo(id,text){const m=getMemos();if(text){m[id]={text:text,updated_at:new Date().toISOString()}}else{delete m[id]}setMemos(m)}
function fmtDate(iso){try{const d=new Date(iso);return d.getFullYear()+'年'+(d.getMonth()+1)+'月'+d.getDate()+'日 '+String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0')}catch(e){return''}}
function refreshButtons(){
  const later=getLater(),skip=getSkip();
  document.querySelectorAll('[data-later-btn]').forEach(function(b){const on=later.includes(+b.dataset.laterBtn);b.classList.toggle('on',on);b.textContent=on?'後で読む ✓':'後で読む';});
  document.querySelectorAll('[data-skip-btn]').forEach(function(b){const on=skip.includes(+b.dataset.skipBtn);b.classList.toggle('on',on);b.textContent=on?'いらない ✓':'いらない';});
}
function refreshPrefUI(){refreshButtons();if(window.onPrefChange)window.onPrefChange();}
function applyReadState(){
  const read=getRead();
  document.querySelectorAll('[data-tid]').forEach(function(el){
    if(read.includes(+el.dataset.tid)){el.classList.add('is-read');const b=el.querySelector('[data-read-badge]');if(b)b.style.display='inline-block';}
  });
}
document.addEventListener('click',function(e){
  const lb=e.target.closest('[data-later-btn]');if(lb){toggleLater(+lb.dataset.laterBtn);return;}
  const sb=e.target.closest('[data-skip-btn]');if(sb){toggleSkip(+sb.dataset.skipBtn);}
});
document.addEventListener('DOMContentLoaded',function(){
  const mb=document.getElementById('menuBtn'),mp=document.getElementById('menuPanel');
  if(mb&&mp){mb.addEventListener('click',function(){mp.hidden=!mp.hidden;});mp.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){mp.hidden=true;});});}
  document.querySelectorAll('[data-memo]').forEach(function(ta){
    const id=ta.dataset.memo;const m=getMemos();
    if(m[id]&&m[id].text)ta.value=m[id].text;
    const sec=ta.closest('.memo-sec,.memo-item');const st=sec?sec.querySelector('.memo-status'):null;
    ta.addEventListener('input',function(){
      saveMemo(id,ta.value);
      if(st)st.textContent=ta.value?'保存しました':'';
      if(window.onMemoChange)window.onMemoChange();
    });
  });
  applyReadState();
  refreshPrefUI();
});
"""

MENU_ITEMS = [
    ("index.html", "トップ"),
    ("unread.html", "未読リスト"),
    ("deliveries.html", "配信ごと"),
    ("issues.html", "号ごと"),
    ("genres.html", "ジャンル"),
    ("glossary.html", "用語集"),
    ("later.html", "後で読む"),
    ("memo.html", "メモ"),
]

def esc(s):
    return html.escape(s or "", quote=True)

def issue_label(issue_date):
    y, m, d = issue_date.split("-")
    return f"{int(y)}年{int(m)}月{int(d)}日号"

def json_for_script(obj):
    """<script> 内に埋めるJSON（</script> 等の事故防止に < をエスケープ）"""
    return json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")

def topbar(prefix):
    links = "".join(f'<a href="{prefix}{h}">{n}</a>' for h, n in MENU_ITEMS)
    return f"""<div class="stickyhead"><div class="topbar-in"><button class="burger" id="menuBtn" aria-label="メニュー">☰</button><span class="topbar-title">Life is beautiful 学びの場</span><a class="topbar-home" href="{prefix}index.html">トップに戻る</a></div><nav class="menu" id="menuPanel" hidden><div class="menu-in">{links}</div></nav></div>"""

def head(title, prefix):
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="{prefix}assets/style.css"></head><body>
{topbar(prefix)}<div class="wrap">"""

def md_lite(text):
    """full_text 用の軽量Markdown変換（見出し・リンク・段落のみ）"""
    out = []
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        b = block.strip()
        if not b:
            continue
        b = esc(b)
        b = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', b)
        if b.startswith("### "):
            out.append(f"<h4>{b[4:]}</h4>")
        elif b.startswith("## "):
            out.append(f"<h4>{b[3:]}</h4>")
        elif b.startswith("# "):
            out.append(f"<h4>{b[2:]}</h4>")
        else:
            out.append(f"<p>{b.replace(chr(10), '<br>')}</p>")
    return "\n".join(out)

def badges(t, extra=""):
    b = ""
    if t.get("delivery_label"):
        b += f'<span class="badge">{esc(t["delivery_label"])}</span>'
    if not t.get("delivered"):
        b += '<span class="badge">未配信</span>'
    ev = t.get("evaluation")
    if ev:
        b += f'<span class="badge score">AI評価 {ev["total"]}点</span>'
    if t.get("has_new"):
        b += '<span class="badge newb">新しい学び</span>'
    return b + extra

def toggle_btns(t, big=False):
    if not t.get("delivered"):
        return ""
    cls = "rowbtns big" if big else "rowbtns"
    return (f'<span class="{cls}"><button class="mini" data-later-btn="{t["id"]}">後で読む</button>'
            f'<button class="mini skipb" data-skip-btn="{t["id"]}">いらない</button></span>')

def theme_li(t, href):
    """一覧ページ共通のテーマ行（既読バッジ・評価・選択ボタン付き）"""
    return (f'<li data-tid="{t["id"]}"><a class="ttl" href="{href}">{esc(t["title"] or "")}</a><br>'
            f'{badges(t)}<span class="badge read" data-read-badge style="display:none">既読</span>'
            f'{toggle_btns(t)}</li>')

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    themes = data["themes"]
    by_id = {t["id"]: t for t in themes}

    # 号ごとの全ユニット数（分母）。issues[].unit_total に保持する。
    issue_totals = {i["issue_date"]: i["unit_total"]
                    for i in data.get("issues", []) if i.get("unit_total")}

    # 配信順（古い順）: delivered_at → id
    delivered = [t for t in themes if t.get("delivered")]
    delivered.sort(key=lambda t: (t.get("delivered_at") or "9999", t["id"]))
    reading_order = [t["id"] for t in delivered]

    # 号ごとのテーマ（号内は created_at → id 順）
    issues = {}
    for t in themes:
        issues.setdefault(t["issue_date"], []).append(t)
    for v in issues.values():
        v.sort(key=lambda t: (t.get("created_at") or "", t["id"]))

    # ジャンルごとのテーマ（号日付 → id 順）
    genre_themes = {}
    for t in themes:
        if t.get("genre"):
            genre_themes.setdefault(t["genre"], []).append(t)
    for v in genre_themes.values():
        v.sort(key=lambda t: (t["issue_date"], t["id"]))

    # テキストアセット（CSS/JS）を assets へ出力
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    (ASSETS / "app.js").write_text(JS.strip() + "\n", encoding="utf-8")
    # スライドは Base64 データURI化して HTML に埋め込む（外部画像参照を持たない）
    slide_of = {}
    for tid, rel in SLIDES.items():
        src = HIDDEN / rel
        if src.exists():
            slide_of[tid] = "data:image/png;base64," + base64.b64encode(src.read_bytes()).decode("ascii")
        else:
            print(f"WARN: slide source missing for theme {tid}: {src}")

    # 用語の定義を全テーマから集めた対応表（テーマページで定義が欠けた項目の補完用）
    global_defs = {}
    for t in themes:
        for g in (t.get("glossary") or []):
            if g.get("term") and g.get("definition"):
                global_defs.setdefault(g["term"], g["definition"])

    OUT_T.mkdir(parents=True, exist_ok=True)
    for t in themes:
        (OUT_T / f"{t['id']}.html").write_text(theme_page(t, by_id, issues, reading_order, slide_of, global_defs, issue_totals), encoding="utf-8")
    (BASE / "index.html").write_text(index_page(delivered, reading_order), encoding="utf-8")
    (BASE / "unread.html").write_text(unread_page(delivered, reading_order), encoding="utf-8")
    (BASE / "deliveries.html").write_text(deliveries_page(delivered), encoding="utf-8")
    (BASE / "issues.html").write_text(issues_page(issues), encoding="utf-8")
    (BASE / "glossary.html").write_text(glossary_page(themes), encoding="utf-8")
    (BASE / "genres.html").write_text(genres_page(genre_themes), encoding="utf-8")
    OUT_G.mkdir(parents=True, exist_ok=True)
    for name, slug in GENRES:
        (OUT_G / f"{slug}.html").write_text(genre_page(name, genre_themes.get(name, [])), encoding="utf-8")
    (BASE / "later.html").write_text(later_page(delivered, reading_order), encoding="utf-8")
    (BASE / "memo.html").write_text(memo_page(delivered), encoding="utf-8")
    print(f"built: index + unread + {len(themes)} theme pages + glossary + deliveries + issues + genres + {len(GENRES)} genre pages + later + memo; slides mapped: {sorted(slide_of)}")

def theme_page(t, by_id, issues, reading_order, slide_of, global_defs, issue_totals):
    tid = t["id"]
    title = t["title"] or ""
    parts = []
    parts.append(head(f"{title} | Life is beautiful 学びの場", "../"))
    parts.append(f"""<header class="site">
<div class="meta">{esc(issue_label(t['issue_date']))}｜{esc(t.get('major_theme') or '')} / {esc(t.get('middle_theme') or '')}｜ジャンル: {esc(t.get('genre') or '')}</div>
<h1>{esc(title)}</h1>
<div>{badges(t)}<span class="badge read" data-read-badge style="display:none">既読</span></div>
{toggle_btns(t, big=True)}</header>""")
    if tid in slide_of:
        parts.append(f'<img class="slide" src="{slide_of[tid]}" alt="まとめスライド">')
    if t.get("summary"):
        parts.append(f'<h2>概要</h2><p>{esc(t["summary"])}</p>')
    ev = t.get("evaluation")
    if ev:
        parts.append(f"""<div class="eval"><div class="eval-head"><span>AI評価</span><span class="eval-total">{ev['total']}<small> / 100点</small></span></div>
<div class="eval-grid"><div>新規性 <b>{ev['novelty']}</b> / 25</div><div>面白さ <b>{ev['interest']}</b> / 25</div><div>話題性 <b>{ev['buzz']}</b> / 25</div><div>関連度 <b>{ev['relevance']}</b> / 25</div></div>
<p class="eval-comment">{esc(ev.get('comment') or '')}</p>
<p class="meta">話題性は、題材がSNSや世の中のニュースでどれだけ注目されるかを目安にした推定です（個別のSNS調査はしていません）。関連度は、主君のNotion「ビジネス」欄のまとめ傾向（企業ケース・事業アイデア・投資・思考法）との合致度です。</p></div>""")
    elif not t.get("delivered"):
        parts.append('<p class="meta">AI評価は配信時に付けます。</p>')
    if t.get("key_points"):
        items = "".join(f'<li>{esc(k)}</li>' for k in t["key_points"])
        parts.append(f'<h2>要点</h2><ul class="points">{items}</ul>')
    gloss = [g for g in (t.get("glossary") or []) if g.get("term")]
    if gloss:
        # 用語解説は定義文をその場に全文表示する（用語集ページへの参照で済ませない）。
        # そのテーマに定義が無い項目は、他テーマで定義済みの用語から補完する。
        items = "".join(
            f'<dt>{esc(g["term"])}</dt><dd>{esc(g.get("definition") or global_defs.get(g["term"], ""))}</dd>'
            for g in gloss)
        parts.append(f'<h2>用語解説</h2><dl class="gloss">{items}</dl>')
    if t.get("re_summary"):
        parts.append(f'<h2>まとめ直し</h2><p>{esc(t["re_summary"])}</p>')
    if t.get("note"):
        parts.append(f'<div class="note"><strong>補足：</strong>{esc(t["note"])}</div>')
    if t.get("full_text"):
        parts.append(f'<details class="fulltext"><summary>全文はこちら（{len(t["full_text"])}字）</summary><div class="ft">{md_lite(t["full_text"])}</div></details>')
    # 関連テーマ: 同じ中テーマ + 同じ号の前後
    rel = []
    seen = set()
    for o in by_id.values():
        if o["id"] != tid and o.get("middle_theme") and o.get("middle_theme") == t.get("middle_theme"):
            rel.append(o); seen.add(o["id"])
    sibs = issues.get(t["issue_date"], [])
    idx = [s["id"] for s in sibs].index(tid) if tid in [s["id"] for s in sibs] else -1
    for j in (idx - 1, idx + 1):
        if 0 <= j < len(sibs) and sibs[j]["id"] not in seen:
            rel.append(sibs[j]); seen.add(sibs[j]["id"])
    if rel:
        lis = "".join(f'<li><a href="{o["id"]}.html">{esc(o["title"] or "")}</a> <span class="meta">（{esc(issue_label(o["issue_date"]))}）</span></li>' for o in rel)
        parts.append(f'<h2>関連テーマ</h2><ul class="points">{lis}</ul>')
    if t.get("notion_url"):
        parts.append(f'<p><a href="{esc(t["notion_url"])}" target="_blank" rel="noopener">Notionで原文の記録を読む</a></p>')
    # 記事の最後に、その号の配信状況を分数で表示する（分子は delivered 件数から自動計算）
    total_units = issue_totals.get(t["issue_date"])
    if total_units:
        done_units = sum(1 for s in issues.get(t["issue_date"], []) if s.get("delivered"))
        parts.append(f'<p class="note" style="text-align:center">{esc(issue_label(t["issue_date"]))}の配信状況： {done_units}/{total_units}</p>')
    parts.append(f"""<div class="memo-sec"><h2>メモ</h2>
<textarea data-memo="{tid}" placeholder="気になったことや保存したいことを自由に書けます"></textarea>
<div class="memo-status"></div></div>""")
    parts.append(f"""<button class="next" id="nextBtn">読んだ ✓ 次の未読へ</button>
<p class="meta" style="text-align:center"><a href="#" id="unreadLink">未読に戻す</a></p>
<footer>週刊 Life is beautiful 学びの場</footer>
<script src="../assets/app.js"></script>
<script>
const ORDER={json.dumps(reading_order)};
const CUR={tid};
if(getRead().includes(CUR)){{document.querySelector('[data-read-badge]').style.display='inline-block';}}
document.getElementById('nextBtn').addEventListener('click',()=>{{
  markRead(CUR);
  const read=getRead();const skip=getSkip();
  const next=ORDER.find(id=>!read.includes(id)&&!skip.includes(id));
  location.href = next ? next+'.html' : '../index.html';
}});
document.getElementById('unreadLink').addEventListener('click',e=>{{e.preventDefault();unmarkRead(CUR);document.querySelector('[data-read-badge]').style.display='none';}});
</script></div></body></html>""")
    return "\n".join(parts)

def info_map(delivered):
    return {t["id"]: {"title": t["title"] or "", "issue": issue_label(t["issue_date"]), "label": t.get("delivery_label") or ""} for t in delivered}

def index_page(delivered, reading_order):
    # トップは「続きを読む」に集中させる。配信ごと・号ごとの全一覧は
    # deliveries.html / issues.html へ分離し、ここには導線だけを置く。
    info = info_map(delivered)
    parts = [head("Life is beautiful 学びの場", "")]
    parts.append("""<header class="site"><h1>Life is beautiful 学びの場</h1>
<p class="meta">週刊 Life is beautiful のテーマ別まとめ。未読は古い順に並んでいます。</p></header>
<h2>続きはここから</h2>
<div id="continueBox"><p class="meta">読み込み中…</p></div>
<h2>未読リスト（古い順）</h2>
<ul class="list" id="unreadList">""")
    for t in delivered:
        parts.append(theme_li(t, f't/{t["id"]}.html'))
    parts.append('</ul>')
    parts.append("""<div class="navrow">
<a href="unread.html">未読リスト</a>
<a href="deliveries.html">配信ごとに見る</a>
<a href="issues.html">号ごとに見る</a>
<a href="genres.html">ジャンルで見る</a>
<a href="later.html">後で読む</a>
<a href="memo.html">メモ</a>
<a href="glossary.html">用語集</a>
</div>""")
    script = """<footer>週刊 Life is beautiful 学びの場</footer>
<script src="assets/app.js"></script>
<script>
const ORDER=__ORDER__;
const INFO=__INFO__;
function render(){
  const read=getRead(),skip=getSkip();
  document.querySelectorAll('[data-tid]').forEach(function(el){
    el.style.display=skip.includes(+el.dataset.tid)?'none':'';
  });
  const rest=ORDER.filter(function(id){return !read.includes(id)&&!skip.includes(id)});
  const next=rest[0];
  const box=document.getElementById('continueBox');
  if(next){
    const m=INFO[next];
    box.innerHTML='<div class="card big"><div class="meta">'+m.issue+(m.label?'｜'+m.label:'')+'</div><a class="ttl" href="t/'+next+'.html">'+m.title+'</a><p class="meta">未読 '+rest.length+' 件のうち最古のものです</p></div>';
  }else{
    box.innerHTML='<div class="card big"><div class="ttl">全部読み終わっています ✓</div><p class="meta">次の配信をお待ちください</p></div>';
  }
}
window.onPrefChange=render;
render();
</script></div></body></html>"""
    parts.append(script.replace("__ORDER__", json.dumps(reading_order)).replace("__INFO__", json_for_script(info)))
    return "\n".join(parts)

def unread_page(delivered, reading_order):
    parts = [head("未読リスト | Life is beautiful 学びの場", "")]
    parts.append("""<header class="site"><h1>未読リスト</h1>
<p class="meta">配信済みテーマを古い順に並べています。既読はグレー表示、「いらない」にしたテーマはここから外れます。</p>
<p class="meta" id="unreadCount"></p></header>
<ul class="list" id="unreadList">""")
    for t in delivered:
        parts.append(theme_li(t, f't/{t["id"]}.html'))
    parts.append('</ul>')
    script = """<footer>週刊 Life is beautiful 学びの場</footer>
<script src="assets/app.js"></script>
<script>
const ORDER=__ORDER__;
function render(){
  const read=getRead(),skip=getSkip();
  let unread=0;
  document.querySelectorAll('[data-tid]').forEach(function(el){
    const id=+el.dataset.tid;
    el.style.display=skip.includes(id)?'none':'';
    if(!read.includes(id)&&!skip.includes(id))unread++;
  });
  document.getElementById('unreadCount').textContent='未読 '+unread+' 件 / 配信済み '+ORDER.length+' 件';
}
window.onPrefChange=render;
render();
</script></div></body></html>"""
    parts.append(script.replace("__ORDER__", json.dumps(reading_order)))
    return "\n".join(parts)

def deliveries_page(delivered):
    # 配信ごとの一覧（配信ラベル単位、古い順）。delivered は配信順に整列済み。
    groups = {}
    for t in delivered:
        groups.setdefault(t.get("delivery_label") or "配信日時は未記録", []).append(t)
    parts = [head("配信ごとに見る | Life is beautiful 学びの場", "")]
    parts.append("""<header class="site"><h1>配信ごとに見る</h1>
<p class="meta">配信1回分ずつ、その回に届いたテーマを古い順に並べています。</p></header>""")
    for label, ts in groups.items():
        lis = "".join(theme_li(t, f't/{t["id"]}.html') for t in ts)
        parts.append(f'<div class="card"><div class="ttl">{esc(label)}</div><ul class="list">{lis}</ul></div>')
    parts.append('<footer>週刊 Life is beautiful 学びの場</footer><script src="assets/app.js"></script></div></body></html>')
    return "\n".join(parts)

def issues_page(issues):
    # 号ごとの一覧（号の日付順、号内はテーマ順）。
    parts = [head("号ごとに見る | Life is beautiful 学びの場", "")]
    parts.append("""<header class="site"><h1>号ごとに見る</h1>
<p class="meta">号ごとに、その号のテーマを並べています。</p></header>""")
    for date in sorted(issues):
        ts = issues[date]
        lis = "".join(theme_li(t, f't/{t["id"]}.html') for t in ts)
        parts.append(f'<div class="card"><div class="ttl">{esc(issue_label(date))}</div><ul class="list">{lis}</ul></div>')
    parts.append('<footer>週刊 Life is beautiful 学びの場</footer><script src="assets/app.js"></script></div></body></html>')
    return "\n".join(parts)

def genres_page(genre_themes):
    parts = [head("ジャンル | Life is beautiful 学びの場", "")]
    parts.append("""<header class="site"><h1>ジャンル</h1>
<p class="meta">主君のNotion「ビジネス」欄の大カテゴリ体系でテーマを分類しています。ジャンルを選ぶと、そのジャンルのテーマ一覧が開きます。</p></header>""")
    for name, slug in GENRES:
        ts = genre_themes.get(name, [])
        if ts:
            sample = "、".join(esc(t["title"] or "") for t in ts[:3])
            parts.append(f'<div class="card"><a class="ttl" href="genre/{slug}.html">{esc(name)}</a><p class="meta">{len(ts)}件：{sample}</p></div>')
        else:
            parts.append(f'<div class="card"><div class="ttl">{esc(name)}</div><p class="meta">まだテーマがありません</p></div>')
    parts.append('<footer>週刊 Life is beautiful 学びの場</footer><script src="assets/app.js"></script></div></body></html>')
    return "\n".join(parts)

def genre_page(name, ts):
    parts = [head(f"{name} | Life is beautiful 学びの場", "../")]
    parts.append(f"""<header class="site"><h1>ジャンル：{esc(name)}</h1>
<p class="meta">このジャンルのテーマ一覧です（{len(ts)}件）。</p></header>""")
    if ts:
        lis = "".join(theme_li(t, f'../t/{t["id"]}.html') for t in ts)
        parts.append(f'<ul class="list">{lis}</ul>')
    else:
        parts.append('<p class="meta">まだテーマがありません。</p>')
    parts.append('<footer>週刊 Life is beautiful 学びの場</footer><script src="../assets/app.js"></script></div></body></html>')
    return "\n".join(parts)

def later_page(delivered, reading_order):
    info = info_map(delivered)
    parts = [head("後で読む | Life is beautiful 学びの場", "")]
    parts.append("""<header class="site"><h1>後で読む・いらない</h1>
<p class="meta">「後で読む」にしたテーマと、「いらない」にしたテーマの一覧です。各テーマのボタンでもう一度押せば元に戻せます。この状態はこの端末の中にだけ保存されます。</p></header>
<h2>後で読む</h2>
<ul class="list" id="laterList"></ul>
<h2>いらない</h2>
<ul class="list" id="skipList"></ul>""")
    script = """<footer>週刊 Life is beautiful 学びの場</footer>
<script src="assets/app.js"></script>
<script>
const ORDER=__ORDER__;
const INFO=__INFO__;
function rowHtml(id){
  const m=INFO[id];if(!m)return '';
  return '<li data-tid="'+id+'"><a class="ttl" href="t/'+id+'.html">'+m.title+'</a><br><span class="meta">'+m.issue+(m.label?'｜'+m.label:'')+'</span> <span class="rowbtns"><button class="mini" data-later-btn="'+id+'">後で読む</button><button class="mini skipb" data-skip-btn="'+id+'">いらない</button></span></li>';
}
function render(){
  const later=getLater(),skip=getSkip();
  const lo=ORDER.filter(function(id){return later.includes(id)});
  const so=ORDER.filter(function(id){return skip.includes(id)});
  document.getElementById('laterList').innerHTML=lo.length?lo.map(rowHtml).join(''):'<li class="meta">まだありません。テーマページや一覧の「後で読む」ボタンで追加できます。</li>';
  document.getElementById('skipList').innerHTML=so.length?so.map(rowHtml).join(''):'<li class="meta">まだありません。</li>';
  refreshButtons();
}
window.onPrefChange=render;
render();
</script></div></body></html>"""
    parts.append(script.replace("__ORDER__", json.dumps(reading_order)).replace("__INFO__", json_for_script(info)))
    return "\n".join(parts)

def memo_page(delivered):
    info = {t["id"]: {"title": t["title"] or "", "issue": issue_label(t["issue_date"]), "label": t.get("delivery_label") or ""} for t in delivered}
    parts = [head("メモ | Life is beautiful 学びの場", "")]
    parts.append("""<header class="site"><h1>メモ</h1>
<p class="meta">各テーマページのメモ欄に書いた自由記載メモの一覧です。更新日時の新しい順に並んでいます。ここでも編集でき、入力すると自動で保存されます。この状態はこの端末の中にだけ保存されます。</p></header>
<div id="memoBox"><p class="meta">読み込み中…</p></div>""")
    script = """<footer>週刊 Life is beautiful 学びの場</footer>
<script src="assets/app.js"></script>
<script>
const INFO=__INFO__;
function escHtml(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function render(){
  const m=getMemos();
  const ids=Object.keys(m).map(Number).filter(function(id){return INFO[id]&&m[id]&&m[id].text}).sort(function(a,b){return String(m[b].updated_at||'').localeCompare(String(m[a].updated_at||''))});
  const box=document.getElementById('memoBox');
  if(!ids.length){box.innerHTML='<p class="meta">まだメモがありません。各記事ページのメモ欄から書けます。</p>';return;}
  box.innerHTML=ids.map(function(id){
    const t=INFO[id];
    return '<div class="card memo-item"><a class="ttl" href="t/'+id+'.html">'+escHtml(t.title)+'</a><div class="meta">'+escHtml(t.issue)+(t.label?'｜'+escHtml(t.label):'')+'</div><textarea data-memo="'+id+'"></textarea><div class="memo-status"></div><div class="meta">更新：'+escHtml(fmtDate(m[id].updated_at))+'</div><button class="mini skipb memo-del" data-memo-del="'+id+'">メモを消す</button></div>';
  }).join('');
  box.querySelectorAll('[data-memo]').forEach(function(ta){
    const id=ta.dataset.memo;const mm=getMemos();
    if(mm[id]&&mm[id].text)ta.value=mm[id].text;
    const sec=ta.closest('.memo-item');const st=sec?sec.querySelector('.memo-status'):null;
    ta.addEventListener('input',function(){saveMemo(id,ta.value);if(st)st.textContent=ta.value?'保存しました':'';});
  });
  box.querySelectorAll('[data-memo-del]').forEach(function(b){
    b.addEventListener('click',function(){saveMemo(b.dataset.memoDel,'');render();});
  });
}
render();
</script></div></body></html>"""
    parts.append(script.replace("__INFO__", json_for_script(info)))
    return "\n".join(parts)

def glossary_page(themes):
    defined, plain = {}, {}
    for t in themes:
        for g in (t.get("glossary") or []):
            term = g.get("term")
            if not term:
                continue
            if g.get("definition"):
                defined.setdefault(term, g["definition"])
            else:
                plain.setdefault(term, True)
    parts = [head("用語集 | Life is beautiful 学びの場", "")]
    parts.append('<header class="site"><h1>用語集</h1></header>\n<dl class="gloss">')
    for term in sorted(defined):
        parts.append(f'<dt>{esc(term)}</dt><dd>{esc(defined[term])}</dd>')
    parts.append('</dl>')
    rest = [t for t in sorted(plain) if t not in defined]
    if rest:
        chips = "".join(f'<span class="badge">{esc(t)}</span>' for t in rest)
        parts.append(f'<h2>その他の用語（定義はテーマページ内にあります）</h2><p>{chips}</p>')
    parts.append('<footer>週刊 Life is beautiful 学びの場</footer><script src="assets/app.js"></script></div></body></html>')
    return "\n".join(parts)

if __name__ == "__main__":
    main()

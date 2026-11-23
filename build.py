#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Life is beautiful 学びの場 — 静的サイト生成スクリプト

data/themes.json（学習スペース getlibrary の出力が正本）から、
index.html / t/<theme_id>.html / glossary.html を生成する。
今後の配信ジョブは、themes.json を更新してから `python3 build.py` を
再実行すればサイト全体が再生成される。

既読状態は各ページの JavaScript が localStorage（キー lib_read_v1）で管理する。

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
ASSETS = BASE / "assets"

# テーマID -> スライド画像（hidden_files からの相対パス）
# 対応は生成スクリプトとファイル名から特定したものだけを載せる。
#  - 6/2号 SDS版（1テーマ1枚）: visuals_2026-11-21-sds/slide_0602_t{1,2,3}.png
#  - 6/2号 記事コーナー: visuals_0602/slide3.png（囲碁・金融・SaaS＝記事コーナー中心）
#    ※ slide4.png は「小さなAIとメモリ革命＋質問コーナー」の合体スライドのため id5 には付けない
#  - 6/9号 夕の回: visuals_2026-06-09-pm/slide{1,2,3,4}.png（生成スクリプトのタイトルで特定）
#  - 11/17号 テーマ2・3: visuals_2026-11-21-pm/slide_theme{2,3}.png（make_slides_v3.py のタイトルで特定）
#    ※ テーマ1（Starship）の単独スライドは存在しない
#  - 11/17号 テーマ4・5: visuals_2026-11-22-am/slide_1117_am_t{4,5}.png
#  - 11/17号 テーマ6・記事グループA: visuals_2026-11-23-am/slide_1117_am_t6.png / _t7a.png
SLIDES = {
    1: "visuals_2026-11-21-sds/slide_0602_t1.png",
    2: "visuals_2026-11-21-sds/slide_0602_t2.png",
    3: "visuals_2026-11-21-sds/slide_0602_t3.png",
    4: "visuals_0602/slide3.png",
    15: "visuals_2026-06-09-pm/slide1.png",
    16: "visuals_2026-06-09-pm/slide2.png",
    18: "visuals_2026-06-09-pm/slide3.png",
    19: "visuals_2026-06-09-pm/slide4.png",
    7: "visuals_2026-11-21-pm/slide_theme2.png",
    8: "visuals_2026-11-21-pm/slide_theme3.png",
    9: "visuals_2026-11-22-am/slide_1117_am_t4.png",
    10: "visuals_2026-11-22-am/slide_1117_am_t5.png",
    11: "visuals_2026-11-23-am/slide_1117_am_t6.png",
    17: "visuals_2026-11-23-am/slide_1117_am_t7a.png",
}

CSS = """
:root{--ink:#1c2733;--sub:#5a6a7a;--line:#dde4ea;--bg:#f6f8fa;--card:#fff;--accent:#1a5fb4;--badge:#e8f0fa;--read:#8a97a5}
@media (prefers-color-scheme:dark){:root{--ink:#e8edf2;--sub:#9fb0c0;--line:#33404d;--bg:#141a20;--card:#1e262f;--accent:#6aa6e8;--badge:#26374a;--read:#66727e}}
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
"""

JS = """
const KEY='lib_read_v1';
function getRead(){try{return JSON.parse(localStorage.getItem(KEY))||[]}catch(e){return[]}}
function setRead(a){localStorage.setItem(KEY,JSON.stringify(a))}
function markRead(id){const r=getRead();if(!r.includes(id)){r.push(id);setRead(r)}}
function unmarkRead(id){setRead(getRead().filter(x=>x!==id))}
"""

def esc(s):
    return html.escape(s or "", quote=True)

def issue_label(issue_date):
    y, m, d = issue_date.split("-")
    return f"{int(y)}年{int(m)}月{int(d)}日号"

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

def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    themes = data["themes"]
    by_id = {t["id"]: t for t in themes}

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

    OUT_T.mkdir(parents=True, exist_ok=True)
    for t in themes:
        (OUT_T / f"{t['id']}.html").write_text(theme_page(t, by_id, issues, reading_order, slide_of), encoding="utf-8")
    (BASE / "index.html").write_text(index_page(delivered, issues, reading_order, by_id), encoding="utf-8")
    (BASE / "glossary.html").write_text(glossary_page(themes), encoding="utf-8")
    print(f"built: index + {len(themes)} theme pages + glossary; slides mapped: {sorted(slide_of)}")

def theme_link(t, prefix="t/"):
    return f'{prefix}{t["id"]}.html'

def badges(t, extra=""):
    b = ""
    if t.get("delivery_label"):
        b += f'<span class="badge">{esc(t["delivery_label"])}</span>'
    if not t.get("delivered"):
        b += '<span class="badge">未配信</span>'
    return b + extra

def theme_page(t, by_id, issues, reading_order, slide_of):
    tid = t["id"]
    title = t["title"] or ""
    parts = []
    parts.append(f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | Life is beautiful 学びの場</title>
<link rel="stylesheet" href="../assets/style.css"></head><body><div class="wrap">
<header class="site"><a class="home" href="../index.html">← トップへ</a>
<div class="meta">{esc(issue_label(t['issue_date']))}｜{esc(t.get('major_theme') or '')} / {esc(t.get('middle_theme') or '')}</div>
<h1>{esc(title)}</h1>
<div>{badges(t)}<span class="badge read" data-read-badge style="display:none">既読</span></div></header>""")
    if tid in slide_of:
        parts.append(f'<img class="slide" src="{slide_of[tid]}" alt="まとめスライド">')
    if t.get("summary"):
        parts.append(f'<h2>概要</h2><p>{esc(t["summary"])}</p>')
    if t.get("key_points"):
        lis = "".join(f"<li>{esc(k)}</li>" for k in t["key_points"])
        parts.append(f'<h2>要点</h2><ul class="points">{lis}</ul>')
    gloss = [g for g in (t.get("glossary") or []) if g.get("term")]
    if gloss:
        items = "".join(
            f'<dt>{esc(g["term"])}</dt><dd>{esc(g["definition"])}</dd>' if g.get("definition") else f'<dt>{esc(g["term"])}</dt><dd>（定義は用語集ページ参照）</dd>'
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
  const read=getRead();
  const next=ORDER.find(id=>!read.includes(id));
  location.href = next ? next+'.html' : '../index.html';
}});
document.getElementById('unreadLink').addEventListener('click',e=>{{e.preventDefault();unmarkRead(CUR);document.querySelector('[data-read-badge]').style.display='none';}});
</script></div></body></html>""")
    return "\n".join(parts)

def index_page(delivered, issues, reading_order, by_id):
    info = {t["id"]: {"title": t["title"] or "", "issue": issue_label(t["issue_date"]), "label": t.get("delivery_label") or ""} for t in delivered}
    parts = ["""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Life is beautiful 学びの場</title>
<link rel="stylesheet" href="assets/style.css"></head><body><div class="wrap">
<header class="site"><h1>Life is beautiful 学びの場</h1>
<p class="meta">週刊 Life is beautiful のテーマ別まとめ。未読は古い順に並んでいます。</p></header>
<h2>続きはここから</h2>
<div id="continueBox"><p class="meta">読み込み中…</p></div>
<h2>未読リスト（古い順）</h2>
<ul class="list" id="unreadList">"""]
    for t in delivered:
        parts.append(f'<li data-tid="{t["id"]}"><a class="ttl" href="{theme_link(t)}">{esc(t["title"] or "")}</a><br>{badges(t)}<span class="meta">{esc(issue_label(t["issue_date"]))}</span> <span class="badge read" data-read-badge style="display:none">既読</span></li>')
    parts.append('</ul>')
    # 配信ごと（ラベル単位、古い順）
    groups = {}
    for t in delivered:
        groups.setdefault(t.get("delivery_label") or "配信日時は未記録", []).append(t)
    parts.append('<h2>配信ごと</h2>')
    for label, ts in groups.items():
        lis = "".join(f'<li data-tid="{t["id"]}"><a class="ttl" href="{theme_link(t)}">{esc(t["title"] or "")}</a> <span class="meta">（{esc(issue_label(t["issue_date"]))}）</span></li>' for t in ts)
        parts.append(f'<div class="card"><div class="ttl">{esc(label)}</div><ul class="points">{lis}</ul></div>')
    # 号ごと
    parts.append('<h2>号ごと</h2>')
    for date in sorted(issues):
        ts = issues[date]
        lis = "".join(f'<li data-tid="{t["id"]}"><a class="ttl" href="{theme_link(t)}">{esc(t["title"] or "")}</a>{"" if t.get("delivered") else " <span class=\"badge\">未配信</span>"}</li>' for t in ts)
        parts.append(f'<div class="card"><div class="ttl">{esc(issue_label(date))}</div><ul class="points">{lis}</ul></div>')
    parts.append(f"""<p style="margin-top:24px"><a href="glossary.html">用語集を見る →</a></p>
<footer>週刊 Life is beautiful 学びの場</footer>
<script src="assets/app.js"></script>
<script>
const ORDER={json.dumps(reading_order)};
const INFO={json.dumps(info, ensure_ascii=False)};
const read=getRead();
document.querySelectorAll('[data-tid]').forEach(el=>{{
  const id=+el.dataset.tid;
  if(read.includes(id)){{el.classList.add('is-read');const b=el.querySelector('[data-read-badge]');if(b)b.style.display='inline-block';}}
}});
const next=ORDER.find(id=>!read.includes(id));
const box=document.getElementById('continueBox');
if(next){{
  const m=INFO[next];
  box.innerHTML='<div class="card big"><div class="meta">'+m.issue+(m.label?'｜'+m.label:'')+'</div><a class="ttl" href="t/'+next+'.html">'+m.title+'</a><p class="meta">未読 '+ORDER.filter(id=>!read.includes(id)).length+' 件のうち最古のものです</p></div>';
}}else{{
  box.innerHTML='<div class="card big"><div class="ttl">全部読み終わっています ✓</div><p class="meta">次の配信をお待ちください</p></div>';
}}
</script></div></body></html>""")
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
    parts = ["""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>用語集 | Life is beautiful 学びの場</title>
<link rel="stylesheet" href="assets/style.css"></head><body><div class="wrap">
<header class="site"><a class="home" href="index.html">← トップへ</a><h1>用語集</h1></header>
<dl class="gloss">"""]
    for term in sorted(defined):
        parts.append(f'<dt>{esc(term)}</dt><dd>{esc(defined[term])}</dd>')
    parts.append('</dl>')
    rest = [t for t in sorted(plain) if t not in defined]
    if rest:
        chips = "".join(f'<span class="badge">{esc(t)}</span>' for t in rest)
        parts.append(f'<h2>その他の用語（定義はテーマページ内にあります）</h2><p>{chips}</p>')
    parts.append('<footer>週刊 Life is beautiful 学びの場</footer></div></body></html>')
    return "\n".join(parts)

if __name__ == "__main__":
    main()

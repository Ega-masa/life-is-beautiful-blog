#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Life is beautiful 学びの場 — 静的サイト生成スクリプト

data/themes.json（学習スペース getlibrary の出力が正本）から、
index.html / unread.html / all.html / t/<theme_id>.html / glossary.html /
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
  メモは 2026-11-24 夜の主君の決定で、テーマページ常時表示の「メモ」ボタンから
  開くパネルで書く形に改修した。保存形式は {テーマid: [{text, at}]} で複数件を
  保持し、追加時は入力を改行で分割して1行を1件のメモとして記録する。旧形式
  {テーマid: {text, updated_at}} のデータは読み込み時に1件のメモへ自動移行する。
  memo.html（メモ一覧）でもテーマごとに全メモを編集・削除できる。
  要点チェック機能は 2026-11-24 の主君の決定で廃止した（旧キー lib_checks_v1
  のデータは端末側に残るが、UI からは参照しない）。
  「いらない」はトップの続き計算と未読リストから除外される。
- テーマページの用語解説は、用語集へ誘導せず定義文をその場に全文表示する
  （定義が無い項目は、他テーマで定義済みの用語から補完する）。
- テーマページの末尾には、その号の配信状況を「配信済みユニット数／全ユニット数」
  の分数で表示する。全体数（分母）は themes.json の issues[].unit_total に保持し、
  分子は themes の delivered 件数から自動計算する。unit_total が無い号では表示しない。
- 質問コーナーは専用レイアウト（2026-11-24 の主君の決定）: kind="qa" かつ
  questions 配列を持つテーマは、号の全質問を1ページにまとめる。構成は
  FAQアコーディオン型＋TL;DR型の組み合わせで、質問の目次（アンカーリンク）→
  質問ごとに「Q. 質問の要約／A. 回答の要約／ポイント／質問と回答の全文
  （details、初期状態は閉）」を並べる。旧来の個別質問テーマの URL は
  REDIRECTS で Q&A ページの該当アンカーへ転送する（リンク切れ防止）。
- 固定ヘッダーのサイトタイトルはトップ（index.html）へのリンク
  （2026-11-24 夜の主君の決定）。サブフォルダのページでは prefix で
  相対パスを解決する。
- 一覧ページ（トップの未読リスト・未読・配信ごと・号ごと・ジャンル別・
  すべての記事）には並べ替えバーを置く（同じく 2026-11-24 夜の主君の決定）。
  キー＝既定／総合点／新規性／面白さ／話題性／関連度／ジャンル、各キーに
  昇順・降順。実装はクライアント側 JS（assets/app.js、選択は localStorage の
  lib_sort_v1 に保存し全一覧ページで共通）。各テーマ行は data 属性に
  評価の各軸とジャンル順序（GENRES の定義順）を持ち、未評価・ジャンル
  無しは点数系・ジャンル順のどちらでも常に最後に置く。配信ごと・号ごとは
  グループ構造を保ち、各グループの中で並べ替える。
- all.html（すべての記事、2026-11-24 夜の主君の決定で新設）は登録テーマ
  全部（配信済み・未配信とも、リダイレクト専用の旧 id は除く）を1つの
  一覧に並べ、並べ替えに加えてフィルター（状態＝すべて／未読／既読／
  後で読む／いらない、ジャンル、号、題名キーワードの AND 条件）を付ける。
  状態は静的 HTML には持たせず、端末の localStorage（既読 lib_read_v1、
  選択 lib_pref_v1）から読み取り時に判定する。フィルターの選択は
  lib_filter_v1 に保存し次回も維持する。表示件数は「全X件中 Y件を表示」。
- 状態のクラウド同期（2026-11-24 夜の主君の決定）: 上記5キー
  （lib_read_v1 / lib_pref_v1 / lib_memo_v1 / lib_sort_v1 /
  lib_filter_v1）は、端末の localStorage に加えて小さなクラウド保存先
  （Cloudflare Workers + KV）にもスナップショットを置き、スマホと PC で
  常に同じ表示に揃える。主君しか見ないため、メモ本文を含めそのまま
  完全保存する。同期メタ情報は lib_sync_v1 に持ち、同期対象には含めない。
  競合ルールは updated_at の新しい方を正とする last-write-wins。
  実装は assets/app.js 末尾の同期モジュール。定数 SYNC_URL は本番
  エンドポイント確定後に実値へ差し替える（プレースホルダの間は
  SYNC_ENABLED=false で同期は無効、現行どおり localStorage のみで動作）。
  Worker のコードと Cloudflare 側の手順は hidden_files/sync/
  （worker.js / SETUP.md）に置く。
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
# ジャンル名 -> 定義順の番号（一覧のジャンル順ソートで使う）
GENRE_INDEX = {name: i for i, (name, slug) in enumerate(GENRES)}

# 過去号アーカイブ（2026-11-25 一括取り込み、1,782件）の配信ラベル。
# 件数が多いため、トップと未読リストには載せず（続きを読む導線は ORDER で
# 保持される）、号ごと・すべての記事・ジャンルから辿る形にする。
# 配信ごとのページでは行を並べず、号ごとページへのリンクカードにする。
# 一覧ページは年別に分割する（1ページに全件を並べるとファイルサイズが
# GitHub コネクタの push 上限を超えるため）。
ARCHIVE_LABEL = "過去号アーカイブ（2026年11月25日取り込み）"

def is_archive(t):
    return t.get("delivery_label") == ARCHIVE_LABEL

def year_nav(kind, years, current):
    """年別一覧ページ間のナビ。kind は 'all' または 'issues'。
    最新年は <kind>.html、それ以外は <kind>-<年>.html。"""
    latest = years[-1]
    links = []
    for y in years:
        href = f"{kind}.html" if y == latest else f"{kind}-{y}.html"
        label = f"{y}年"
        if y == current:
            links.append(f"<strong>{label}</strong>")
        else:
            links.append(f'<a href="{href}">{label}</a>')
    return '<p class="meta">年別: ' + " ｜ ".join(links) + "</p>"

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
    # 6/9号 質問コーナー専用ページ（9問）: visuals_2026-06-09-pm/slide_qa.png
    # （make_visuals_0609_qa.py）。旧 id22・23 の slide5/6.png は統合に伴い未使用。
    24: "visuals_2026-06-09-pm/slide_qa.png",
    6: "visuals_2026-11-21-pm/slide_theme1.png",
    7: "visuals_2026-11-21-pm/slide_theme2.png",
    8: "visuals_2026-11-21-pm/slide_theme3.png",
    9: "visuals_2026-11-22-am/slide_1117_am_t4.png",
    10: "visuals_2026-11-22-am/slide_1117_am_t5.png",
    11: "visuals_2026-11-23-am/slide_1117_am_t6.png",
    17: "visuals_2026-11-23-am/slide_1117_am_t7a.png",
    20: "visuals_2026-11-24-am/slide_1117_am_t7b.png",
    21: "visuals_2026-11-24-am/slide_1117_am_t7c.png",
    25: "visuals_2026-11-25-am/slide_1117_am_t10.png",
    26: "visuals_2026-11-25-am/slide_1117_am_t11.png",
    1809: "visuals_2026-06-16-pm/slide_0616_pm_t1.png",
    1810: "visuals_2026-06-16-pm/slide_0616_pm_t2.png",
    1811: "visuals_2026-11-26-am/slide_1117_am_t12.png",
    1812: "visuals_2026-11-26-am/slide_1117_am_t13.png",
    1815: "visuals_2026-11-27-am/slide_1117_am_t14.png",
    1816: "visuals_2026-11-27-am/slide_1117_am_t15.png",
    1813: "visuals_2026-06-16-pm/slide_0616_pm_t3.png",
    1814: "visuals_2026-06-16-pm/slide_0616_pm_t4.png",
}

# 旧URL -> Q&Aページのアンカーへの転送（統合で消えたテーマのリンク切れ防止）
# 2026-11-24: 6/9号の個別質問テーマ id22・23 を Q&A テーマ id24 へ統合した。
REDIRECTS = {
    22: "24.html#q1",
    23: "24.html#q2",
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
.topbar-title{font-weight:700;font-size:14px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--ink)}
.sortbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0 2px}
.sortbar label{font-size:13.5px;color:var(--sub);display:inline-flex;align-items:center;gap:6px}
.sortbar select{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:14px;font-family:inherit}
.sortbar button.mini:disabled{cursor:default}
.filterbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:10px 0 2px}
.filterbar label{font-size:13.5px;color:var(--sub);display:inline-flex;align-items:center;gap:6px}
.filterbar select,.filterbar input[type="search"]{background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:8px;padding:6px 8px;font-size:14px;font-family:inherit}
.filterbar input[type="search"]{flex:1;min-width:140px}
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
.memo-item textarea{width:100%;min-height:90px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:15px;line-height:1.7;font-family:inherit;resize:vertical;margin-top:8px}
.memo-status{font-size:12.5px;color:var(--sub);margin-top:4px;min-height:1.4em}
.memo-entry{border-top:1px solid var(--line);margin-top:10px;padding-top:4px}
.memo-fab{position:fixed;right:14px;bottom:14px;z-index:95;background:var(--accent);color:#fff;border:0;border-radius:999px;padding:12px 18px;font-size:15px;font-weight:700;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.28)}
.memo-fab:active{opacity:.85}
.memo-panel{position:fixed;inset:0;z-index:96;background:rgba(10,16,22,.45);display:flex;align-items:flex-end;justify-content:center}
.memo-panel[hidden]{display:none}
.memo-panel-box{background:var(--card);color:var(--ink);width:100%;max-width:760px;max-height:82vh;overflow-y:auto;border-radius:16px 16px 0 0;padding:14px 16px calc(14px + env(safe-area-inset-bottom))}
.memo-panel-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.memo-row{border:1px solid var(--line);border-radius:10px;padding:8px 12px;margin:8px 0}
.memo-row-text{white-space:pre-wrap;word-break:break-word}
.memo-row-meta{display:flex;justify-content:space-between;align-items:center;margin-top:4px}
.memo-panel-box textarea{width:100%;min-height:90px;background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:10px 12px;font-size:15px;line-height:1.7;font-family:inherit;resize:vertical}
.memo-add{width:100%;background:var(--accent);color:#fff;border:0;border-radius:10px;padding:12px;font-size:15px;font-weight:700;cursor:pointer;margin-top:8px}
.memo-add:active{opacity:.85}
.qa-toc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px 12px 36px;margin:12px 0}
.qa-toc li{margin:7px 0}
.qa-block{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:6px 16px 12px;margin:14px 0}
.qa-block h3{font-size:17px;margin:14px 0 8px;line-height:1.55}
.qa-a{background:var(--badge);border-radius:10px;padding:10px 14px;margin:8px 0;font-size:15.5px}
.qa-block h4{font-size:14.5px;margin:14px 0 4px;color:var(--accent)}
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
function normalizeMemos(raw){
  const out={};
  if(!raw||typeof raw!=='object'||Array.isArray(raw))return out;
  Object.keys(raw).forEach(function(id){
    const v=raw[id];
    if(Array.isArray(v)){
      const arr=v.filter(function(e){return e&&typeof e.text==='string'&&e.text}).map(function(e){return{text:e.text,at:e.at||''}});
      if(arr.length)out[id]=arr;
    }else if(v&&typeof v.text==='string'&&v.text){
      out[id]=[{text:v.text,at:v.updated_at||''}];
    }
  });
  return out;
}
function getMemos(){
  try{
    const raw=JSON.parse(localStorage.getItem(MEMO_KEY));
    const norm=normalizeMemos(raw);
    if(JSON.stringify(raw||{})!==JSON.stringify(norm))setMemos(norm);
    return norm;
  }catch(e){return{}}
}
function setMemos(m){localStorage.setItem(MEMO_KEY,JSON.stringify(m))}
function splitMemoLines(text){
  const LF=String.fromCharCode(10),CR=String.fromCharCode(13);
  return String(text||'').split(CR).join(LF).split(LF).map(function(s){return s.trim()}).filter(function(s){return s.length>0});
}
function addMemos(id,text){
  const lines=splitMemoLines(text);
  if(!lines.length)return 0;
  const m=getMemos();const arr=(m[id]||[]).slice();const now=new Date().toISOString();
  lines.forEach(function(s){arr.push({text:s,at:now})});
  m[id]=arr;setMemos(m);return lines.length;
}
function updateMemoText(id,idx,text){
  const m=getMemos();const arr=(m[id]||[]).slice();
  if(idx<0||idx>=arr.length)return;
  if(String(text||'').trim()){arr[idx]={text:String(text),at:new Date().toISOString()};m[id]=arr;}
  else{arr.splice(idx,1);if(arr.length)m[id]=arr;else delete m[id];}
  setMemos(m);
}
function deleteMemoAt(id,idx){
  const m=getMemos();const arr=(m[id]||[]).slice();
  if(idx<0||idx>=arr.length)return;
  arr.splice(idx,1);if(arr.length)m[id]=arr;else delete m[id];setMemos(m);
}
function refreshMemoCounts(){
  const memos=getMemos();
  document.querySelectorAll('[data-memo-count]').forEach(function(el){
    const n=(memos[el.getAttribute('data-memo-count')]||[]).length;
    el.textContent=n?('（'+n+'）'):'';
  });
}
function renderMemoPanel(panel){
  const id=panel.getAttribute('data-memo-panel');
  const list=panel.querySelector('[data-memo-list]');
  const arr=getMemos()[id]||[];
  list.innerHTML='';
  if(!arr.length){list.innerHTML='<p class="meta">まだメモがありません。</p>';return;}
  arr.forEach(function(mm,i){
    const row=document.createElement('div');row.className='memo-row';
    const tx=document.createElement('div');tx.className='memo-row-text';tx.textContent=mm.text;
    const meta=document.createElement('div');meta.className='memo-row-meta';
    const dt=document.createElement('span');dt.className='meta';dt.textContent=fmtDate(mm.at);
    const del=document.createElement('button');del.type='button';del.className='mini skipb';del.textContent='削除';
    del.addEventListener('click',function(){deleteMemoAt(id,i);renderMemoPanel(panel);refreshMemoCounts();});
    meta.appendChild(dt);meta.appendChild(del);
    row.appendChild(tx);row.appendChild(meta);list.appendChild(row);
  });
}
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
const SORT_KEY='lib_sort_v1';
const SORT_KEYS=['default','total','novelty','interest','buzz','relevance','genre'];
function getSortPref(){
  try{const s=JSON.parse(localStorage.getItem(SORT_KEY));if(s&&SORT_KEYS.indexOf(s.key)>=0&&(s.dir==='asc'||s.dir==='desc'))return{key:s.key,dir:s.dir};}catch(e){}
  return{key:'default',dir:'desc'};
}
function setSortPref(p){localStorage.setItem(SORT_KEY,JSON.stringify(p))}
function sortItemsBy(items,pref){
  const key=pref.key,dir=(pref.dir==='asc')?1:-1;
  return items.slice().sort(function(a,b){
    if(key==='default')return a.i-b.i;
    const va=a[key],vb=b[key];
    if(va===null&&vb===null)return a.i-b.i;
    if(va===null)return 1;
    if(vb===null)return -1;
    const c=(va-vb)*dir;
    return (c!==0)?c:(a.i-b.i);
  });
}
function readSortVals(el){
  function num(name){const v=el.getAttribute(name);return (v===null||v==='')?null:parseFloat(v);}
  return {total:num('data-total'),novelty:num('data-novelty'),interest:num('data-interest'),buzz:num('data-buzz'),relevance:num('data-relevance'),genre:num('data-genre-idx')};
}
function applySort(){
  const pref=getSortPref();
  document.querySelectorAll('ul.sortable').forEach(function(ul){
    const els=Array.prototype.slice.call(ul.children).filter(function(el){return el.hasAttribute&&el.hasAttribute('data-tid');});
    const items=els.map(function(el,i){const o=readSortVals(el);o.i=i;o.el=el;return o;});
    sortItemsBy(items,pref).forEach(function(o){ul.appendChild(o.el);});
  });
  document.querySelectorAll('[data-sort-key]').forEach(function(sel){sel.value=pref.key;});
  document.querySelectorAll('[data-sort-dir]').forEach(function(btn){
    btn.textContent=(pref.dir==='asc')?'昇順 ▲':'降順 ▼';
    btn.disabled=(pref.key==='default');
    btn.style.opacity=(pref.key==='default')?'0.5':'';
  });
}
function initSortUI(){
  document.querySelectorAll('[data-sort-key]').forEach(function(sel){
    sel.value=getSortPref().key;
    sel.addEventListener('change',function(){
      const p=getSortPref();p.key=sel.value;setSortPref(p);applySort();
    });
  });
  document.querySelectorAll('[data-sort-dir]').forEach(function(btn){
    btn.addEventListener('click',function(){
      const p=getSortPref();p.dir=(p.dir==='asc')?'desc':'asc';setSortPref(p);applySort();
    });
  });
  if(document.querySelector('ul.sortable'))applySort();
}
const FILTER_KEY='lib_filter_v1';
const FILTER_STATUSES=['all','unread','read','later','skip'];
function getFilterPref(){
  try{const f=JSON.parse(localStorage.getItem(FILTER_KEY));if(f&&typeof f==='object'&&!Array.isArray(f)){
    return {status:(FILTER_STATUSES.indexOf(f.status)>=0)?f.status:'all',
            genre:(typeof f.genre==='string'&&f.genre)?f.genre:'all',
            issue:(typeof f.issue==='string'&&f.issue)?f.issue:'all',
            keyword:(typeof f.keyword==='string')?f.keyword:''};
  }}catch(e){}
  return {status:'all',genre:'all',issue:'all',keyword:''};
}
function setFilterPref(f){localStorage.setItem(FILTER_KEY,JSON.stringify(f))}
function themeMatchesStatus(id,status,read,later,skip){
  if(status==='unread')return !read.includes(id);
  if(status==='read')return read.includes(id);
  if(status==='later')return later.includes(id);
  if(status==='skip')return skip.includes(id);
  return true;
}
function rowMatchesFilter(v,f,ctx){
  if(!themeMatchesStatus(v.tid,f.status,ctx.read,ctx.later,ctx.skip))return false;
  if(f.genre!=='all'&&v.genre!==f.genre)return false;
  if(f.issue!=='all'&&v.issue!==f.issue)return false;
  if(f.keyword&&String(v.title||'').indexOf(f.keyword)<0)return false;
  return true;
}
document.addEventListener('DOMContentLoaded',function(){
  initSortUI();
  const mb=document.getElementById('menuBtn'),mp=document.getElementById('menuPanel');
  if(mb&&mp){mb.addEventListener('click',function(){mp.hidden=!mp.hidden;});mp.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){mp.hidden=true;});});}
  document.querySelectorAll('[data-memo-open]').forEach(function(btn){
    btn.addEventListener('click',function(){
      const panel=document.querySelector('[data-memo-panel="'+btn.getAttribute('data-memo-open')+'"]');
      if(panel){renderMemoPanel(panel);panel.hidden=false;}
    });
  });
  document.querySelectorAll('[data-memo-panel]').forEach(function(panel){
    const id=panel.getAttribute('data-memo-panel');
    panel.querySelector('[data-memo-close]').addEventListener('click',function(){panel.hidden=true;});
    panel.addEventListener('click',function(e){if(e.target===panel)panel.hidden=true;});
    panel.querySelector('[data-memo-add]').addEventListener('click',function(){
      const ta=panel.querySelector('[data-memo-input]');
      if(addMemos(id,ta.value)>0){ta.value='';renderMemoPanel(panel);refreshMemoCounts();}
    });
  });
  refreshMemoCounts();
  applyReadState();
  refreshPrefUI();
});
const SYNC_URL='https://lib-state-sync.mr-maksgh.workers.dev/state?k=a2bb07bbc1e0dd23bcf9a2589245773ff5eba301c675a986';
const SYNC_ENABLED=SYNC_URL.indexOf('REPLACE-ME')<0;
const SYNC_KEYS=['lib_read_v1','lib_pref_v1','lib_memo_v1','lib_sort_v1','lib_filter_v1'];
const SYNC_META_KEY='lib_sync_v1';
const SYNC_RELOAD_FLAG='lib_sync_reloaded_v1';
const SYNC_DEBOUNCE_MS=800;
const SYNC_TIMEOUT_MS=3000;
function syncGetMeta(){
  try{const m=JSON.parse(localStorage.getItem(SYNC_META_KEY));if(m&&typeof m.updated_at==='number')return{updated_at:m.updated_at,last_synced_at:(typeof m.last_synced_at==='number')?m.last_synced_at:0};}catch(e){}
  return{updated_at:0,last_synced_at:0};
}
function syncSetMeta(m){
  try{localStorage.setItem(SYNC_META_KEY,JSON.stringify({updated_at:m.updated_at||0,last_synced_at:m.last_synced_at||0}));}catch(e){}
}
function syncHasLocalState(store){
  for(let i=0;i<SYNC_KEYS.length;i++){const v=store.getItem(SYNC_KEYS[i]);if(v!==null&&v!=='')return true;}
  return false;
}
function syncBuildSnapshot(store,updatedAt){
  const data={};
  SYNC_KEYS.forEach(function(k){data[k]=store.getItem(k);});
  return{updated_at:updatedAt,data:data};
}
function syncDecide(localUpdatedAt,cloudUpdatedAt,hasLocal){
  if(cloudUpdatedAt>localUpdatedAt)return 'pull';
  if(localUpdatedAt>cloudUpdatedAt)return hasLocal?'push':'pull';
  if(cloudUpdatedAt===0)return hasLocal?'push':'none';
  return 'none';
}
let syncApplying=false;
let syncPushTimer=null;
function syncSchedulePush(){
  if(!SYNC_ENABLED)return;
  if(syncPushTimer)clearTimeout(syncPushTimer);
  syncPushTimer=setTimeout(function(){syncPushTimer=null;syncPushNow();},SYNC_DEBOUNCE_MS);
}
function syncOnLocalWrite(){
  const m=syncGetMeta();m.updated_at=Date.now();syncSetMeta(m);
  syncSchedulePush();
}
function syncPushNow(){
  if(!SYNC_ENABLED)return;
  if(syncPushTimer){clearTimeout(syncPushTimer);syncPushTimer=null;}
  const meta=syncGetMeta();
  const snap=syncBuildSnapshot(localStorage,meta.updated_at||Date.now());
  fetch(SYNC_URL,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(snap)}).then(function(r){
    if(!r.ok)return;
    const m2=syncGetMeta();m2.last_synced_at=Date.now();syncSetMeta(m2);
    if(m2.updated_at!==snap.updated_at)syncSchedulePush();
  }).catch(function(){});
}
const syncOrigSetItem=Storage.prototype.setItem;
Storage.prototype.setItem=function(k,v){
  syncOrigSetItem.call(this,k,v);
  if(this===localStorage&&!syncApplying&&SYNC_KEYS.indexOf(k)>=0)syncOnLocalWrite();
};
function syncApplyCloud(cloud){
  syncApplying=true;
  try{
    const data=(cloud&&cloud.data)||{};
    SYNC_KEYS.forEach(function(k){
      if(Object.prototype.hasOwnProperty.call(data,k)){
        if(data[k]===null||data[k]===undefined)localStorage.removeItem(k);
        else localStorage.setItem(k,String(data[k]));
      }
    });
    syncSetMeta({updated_at:(cloud&&typeof cloud.updated_at==='number')?cloud.updated_at:0,last_synced_at:Date.now()});
  }catch(e){}
  syncApplying=false;
}
function syncFetchCloud(){
  const ctrl=('AbortController' in window)?new AbortController():null;
  const timer=ctrl?setTimeout(function(){ctrl.abort();},SYNC_TIMEOUT_MS):null;
  const opt={method:'GET'};
  if(ctrl)opt.signal=ctrl.signal;
  return fetch(SYNC_URL,opt).then(function(r){
    if(timer)clearTimeout(timer);
    if(!r.ok)throw new Error('sync get failed');
    return r.json();
  });
}
function syncStartup(){
  if(!SYNC_ENABLED)return;
  syncFetchCloud().then(function(cloud){
    const cloudUpdated=(cloud&&typeof cloud.updated_at==='number')?cloud.updated_at:0;
    const meta=syncGetMeta();
    const action=syncDecide(meta.updated_at,cloudUpdated,syncHasLocalState(localStorage));
    if(action==='pull'){
      syncApplyCloud(cloud);
      let reloaded=false;
      try{reloaded=!!sessionStorage.getItem(SYNC_RELOAD_FLAG);}catch(e){}
      if(!reloaded){
        try{sessionStorage.setItem(SYNC_RELOAD_FLAG,'1');}catch(e){}
        location.reload();
      }
    }else if(action==='push'){
      try{sessionStorage.removeItem(SYNC_RELOAD_FLAG);}catch(e){}
      syncPushNow();
    }else{
      try{sessionStorage.removeItem(SYNC_RELOAD_FLAG);}catch(e){}
      if(cloudUpdated>0){const m2=syncGetMeta();m2.last_synced_at=Date.now();syncSetMeta(m2);}
    }
  }).catch(function(){});
}
document.addEventListener('DOMContentLoaded',function(){syncStartup();});
"""

MENU_ITEMS = [
    ("index.html", "トップ"),
    ("unread.html", "未読リスト"),
    ("all.html", "すべての記事"),
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
    return f"""<div class="stickyhead"><div class="topbar-in"><button class="burger" id="menuBtn" aria-label="メニュー">☰</button><a class="topbar-title" href="{prefix}index.html">Life is beautiful 学びの場</a><a class="topbar-home" href="{prefix}index.html">トップに戻る</a></div><nav class="menu" id="menuPanel" hidden><div class="menu-in">{links}</div></nav></div>"""

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

def memo_ui(tid):
    """テーマページ常時表示の「メモ」ボタンと、開閉する入力パネルのマークアップ。
    既存メモの一覧・日時・削除と、改行で複数件に分かれる追加フォームを持つ。
    実際の保存・描画は assets/app.js 側（lib_memo_v1）が担う。"""
    return f"""<button type="button" class="memo-fab" data-memo-open="{tid}">メモ<span class="memo-fab-count" data-memo-count="{tid}"></span></button>
<div class="memo-panel" data-memo-panel="{tid}" hidden>
<div class="memo-panel-box">
<div class="memo-panel-head"><strong>メモ</strong><button type="button" class="mini" data-memo-close>閉じる</button></div>
<div data-memo-list></div>
<textarea data-memo-input placeholder="メモを書く（改行すると別のメモとして記録されます）"></textarea>
<button type="button" class="memo-add" data-memo-add>追加</button>
</div>
</div>"""

def sort_bar(note=""):
    """一覧ページ共通の並べ替えバー。操作と保存は assets/app.js（lib_sort_v1）が担う。
    配信ごと・号ごとのページでは各グループの中で並べ替えるため、その旨を note で添える。"""
    n = f'<span class="meta">{esc(note)}</span>' if note else ""
    return f"""<div class="sortbar"><label>並べ替え <select data-sort-key>
<option value="default">既定（表示順）</option>
<option value="total">総合点</option>
<option value="novelty">新規性</option>
<option value="interest">面白さ</option>
<option value="buzz">話題性</option>
<option value="relevance">関連度</option>
<option value="genre">ジャンル</option>
</select></label><button type="button" class="mini" data-sort-dir>降順 ▼</button>{n}</div>"""

def sort_attrs(t):
    """並べ替え用 data 属性（評価の各軸とジャンル順序）。
    未評価・ジャンル無しのテーマには付けない（JS 側で常に最後に置かれる）。"""
    attrs = ""
    ev = t.get("evaluation")
    if ev:
        attrs += (f' data-total="{ev["total"]}" data-novelty="{ev["novelty"]}"'
                  f' data-interest="{ev["interest"]}" data-buzz="{ev["buzz"]}"'
                  f' data-relevance="{ev["relevance"]}"')
    gidx = GENRE_INDEX.get(t.get("genre") or "")
    if gidx is not None:
        attrs += f' data-genre-idx="{gidx}"'
    return attrs

def theme_li(t, href):
    """一覧ページ共通のテーマ行（既読バッジ・評価・選択ボタン付き）。
    並べ替え用に、評価の各軸（総合点・新規性・面白さ・話題性・関連度）と
    ジャンル順序（GENRES の定義順の番号）を data 属性として持つ。
    未評価・ジャンル無しのテーマには付けない（JS 側で常に最後に置かれる）。"""
    return (f'<li data-tid="{t["id"]}"{sort_attrs(t)}><a class="ttl" href="{href}">{esc(t["title"] or "")}</a><br>'
            f'{badges(t)}<span class="badge read" data-read-badge style="display:none">既読</span>'
            f'{toggle_btns(t)}</li>')

def all_theme_li(t, href):
    """すべての記事ページ専用のテーマ行。theme_li と同じ体裁に、号とジャンルを
    メタ行で明示し、フィルター用に data-issue / data-genre-name を持つ。
    配信ラベル・配信状況（未配信）・総合点は badges() がバッジで出す。"""
    return (f'<li data-tid="{t["id"]}"{sort_attrs(t)} data-issue="{esc(t["issue_date"])}"'
            f' data-genre-name="{esc(t.get("genre") or "")}">'
            f'<a class="ttl" href="{href}">{esc(t["title"] or "")}</a><br>'
            f'<span class="meta">{esc(issue_label(t["issue_date"]))}｜ジャンル: {esc(t.get("genre") or "未分類")}</span><br>'
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
        if t.get("kind") == "qa" and t.get("questions"):
            page = qa_theme_page(t, issues, reading_order, slide_of, global_defs, issue_totals)
        else:
            page = theme_page(t, by_id, issues, reading_order, slide_of, global_defs, issue_totals)
        (OUT_T / f"{t['id']}.html").write_text(page, encoding="utf-8")
    for old_id, target in REDIRECTS.items():
        (OUT_T / f"{old_id}.html").write_text(redirect_page(old_id, target), encoding="utf-8")
    (BASE / "index.html").write_text(index_page(delivered, reading_order), encoding="utf-8")
    (BASE / "unread.html").write_text(unread_page(delivered, reading_order), encoding="utf-8")
    for fname, text in all_page(themes, issues).items():
        (BASE / fname).write_text(text, encoding="utf-8")
    (BASE / "deliveries.html").write_text(deliveries_page(delivered), encoding="utf-8")
    for fname, text in issues_page(issues).items():
        (BASE / fname).write_text(text, encoding="utf-8")
    (BASE / "glossary.html").write_text(glossary_page(themes), encoding="utf-8")
    (BASE / "genres.html").write_text(genres_page(genre_themes), encoding="utf-8")
    OUT_G.mkdir(parents=True, exist_ok=True)
    for name, slug in GENRES:
        (OUT_G / f"{slug}.html").write_text(genre_page(name, genre_themes.get(name, [])), encoding="utf-8")
    (BASE / "later.html").write_text(later_page(delivered, reading_order), encoding="utf-8")
    (BASE / "memo.html").write_text(memo_page(delivered), encoding="utf-8")
    print(f"built: index + unread + all + {len(themes)} theme pages + glossary + deliveries + issues + genres + {len(GENRES)} genre pages + later + memo; slides mapped: {sorted(slide_of)}")

def eval_html(t):
    """AI評価パネル（通常テーマと Q&A テーマで共用）"""
    ev = t.get("evaluation")
    if ev:
        return f"""<div class="eval"><div class="eval-head"><span>AI評価</span><span class="eval-total">{ev['total']}<small> / 100点</small></span></div>
<div class="eval-grid"><div>新規性 <b>{ev['novelty']}</b> / 25</div><div>面白さ <b>{ev['interest']}</b> / 25</div><div>話題性 <b>{ev['buzz']}</b> / 25</div><div>関連度 <b>{ev['relevance']}</b> / 25</div></div>
<p class="eval-comment">{esc(ev.get('comment') or '')}</p>
<p class="meta">話題性は、題材がSNSや世の中のニュースでどれだけ注目されるかを目安にした推定です（個別のSNS調査はしていません）。関連度は、主君のNotion「ビジネス」欄のまとめ傾向（企業ケース・事業アイデア・投資・思考法）との合致度です。</p></div>"""
    if not t.get("delivered"):
        return '<p class="meta">AI評価は配信時に付けます。</p>'
    return ""

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
    parts.append(eval_html(t))
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
    parts.append(memo_ui(tid))
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

def qa_theme_page(t, issues, reading_order, slide_of, global_defs, issue_totals):
    """質問コーナー専用レイアウト: 号の全質問を1ページにまとめる。
    FAQアコーディオン型（目次＋タップで全文展開）と TL;DR＋キーポイント型
    （答えの要約を先に、要点は箇条書き）の組み合わせ。"""
    tid = t["id"]
    title = t["title"] or ""
    questions = t.get("questions") or []
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
    toc = "".join(f'<li><a href="#q{i}">{esc(q.get("q_summary") or "")}</a></li>'
                  for i, q in enumerate(questions, 1))
    parts.append(f'<h2>質問の目次（全{len(questions)}問）</h2><ol class="qa-toc">{toc}</ol>')
    for i, q in enumerate(questions, 1):
        pts = "".join(f'<li>{esc(p)}</li>' for p in (q.get("points") or []))
        parts.append(f"""<section class="qa-block" id="q{i}">
<h3>Q{i}. {esc(q.get('q_summary') or '')}</h3>
<p class="qa-a"><strong>A.</strong> {esc(q.get('a_summary') or '')}</p>
<h4>ポイント</h4>
<ul class="points">{pts}</ul>
<details class="fulltext"><summary>質問と回答の全文</summary><div class="ft"><h4>【質問】</h4>{md_lite(q.get('full_q') or '')}<h4>《回答》</h4>{md_lite(q.get('full_a') or '')}</div></details>
</section>""")
    gloss = [g for g in (t.get("glossary") or []) if g.get("term")]
    if gloss:
        items = "".join(
            f'<dt>{esc(g["term"])}</dt><dd>{esc(g.get("definition") or global_defs.get(g["term"], ""))}</dd>'
            for g in gloss)
        parts.append(f'<h2>用語解説</h2><dl class="gloss">{items}</dl>')
    if t.get("re_summary"):
        parts.append(f'<h2>まとめ直し</h2><p>{esc(t["re_summary"])}</p>')
    if t.get("note"):
        parts.append(f'<div class="note"><strong>補足：</strong>{esc(t["note"])}</div>')
    if t.get("notion_url"):
        parts.append(f'<p><a href="{esc(t["notion_url"])}" target="_blank" rel="noopener">Notionで原文の記録を読む</a></p>')
    total_units = issue_totals.get(t["issue_date"])
    if total_units:
        done_units = sum(1 for s in issues.get(t["issue_date"], []) if s.get("delivered"))
        parts.append(f'<p class="note" style="text-align:center">{esc(issue_label(t["issue_date"]))}の配信状況： {done_units}/{total_units}</p>')
    parts.append(memo_ui(tid))
    parts.append(f"""<button class="next" id="nextBtn">読んだ ✓ 次の未読へ</button>
<p class="meta" style="text-align:center"><a href="#" id="unreadLink">未読に戻す</a></p>
{eval_html(t)}
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

def redirect_page(old_id, target):
    """統合で消えた旧テーマURLを、Q&Aページの該当アンカーへ転送するページ"""
    url = target
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="0; url={esc(url)}">
<link rel="canonical" href="{esc(url)}">
<title>移動しました | Life is beautiful 学びの場</title>
<link rel="stylesheet" href="../assets/style.css"></head><body>
<div class="wrap">
<p>このページは質問コーナー専用ページに統合されました。自動で移動しない場合は、<a href="{esc(url)}">こちら</a>を開いてください。</p>
</div></body></html>"""

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
<h2>未読リスト</h2>
""" + sort_bar() + """
<ul class="list sortable" id="unreadList">""")
    for t in delivered:
        if is_archive(t):
            continue
        parts.append(theme_li(t, f't/{t["id"]}.html'))
    parts.append('</ul>')
    n_arch = sum(1 for t in delivered if is_archive(t))
    if n_arch:
        parts.append(f'<p class="meta">過去号アーカイブ（{n_arch}件）はこのリストには載せていません。<a href="issues.html">号ごとに見る</a>・<a href="all.html">すべての記事</a>から読めます。</p>')
    parts.append("""<div class="navrow">
<a href="unread.html">未読リスト</a>
<a href="all.html">すべての記事</a>
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
""" + sort_bar() + """
<ul class="list sortable" id="unreadList">""")
    listed = [t for t in delivered if not is_archive(t)]
    for t in listed:
        parts.append(theme_li(t, f't/{t["id"]}.html'))
    parts.append('</ul>')
    n_arch = len(delivered) - len(listed)
    if n_arch:
        parts.append(f'<p class="meta">過去号アーカイブ（{n_arch}件）はこのリストには載せていません。<a href="issues.html">号ごとに見る</a>・<a href="all.html">すべての記事</a>から読めます。</p>')
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
  document.getElementById('unreadCount').textContent='未読 '+unread+' 件 / 配信済み '+__LISTED__+' 件（過去号アーカイブを除く）';
}
window.onPrefChange=render;
render();
</script></div></body></html>"""
    parts.append(script.replace("__ORDER__", json.dumps(reading_order)).replace("__LISTED__", str(len(listed))))
    return "\n".join(parts)

def all_page(themes, issues):
    """すべての記事: 登録テーマ全部（配信済み・未配信とも）を号の日付順・号内順に
    並べた一覧。年別に分割し {ファイル名: HTML} を返す（最新年が all.html、
    他の年は all-<年>.html）。並べ替えバー（既存の共通仕組み）に加えて、
    状態・ジャンル・号・題名キーワードのフィルター（AND 条件）を付ける。
    フィルターは年ページの中で効く。状態は端末の localStorage から
    読み取り時に判定し、選択は lib_filter_v1 に保存する。"""
    present_genres = [(name, slug) for name, slug in GENRES
                      if any(t.get("genre") == name for t in themes)]
    genre_opts = "".join(f'<option value="{esc(name)}">{esc(name)}</option>' for name, _ in present_genres)
    years = sorted({d[:4] for d in issues})
    latest = years[-1]
    pages = {}
    for y in years:
        dates = sorted(d for d in issues if d[:4] == y)
        issue_opts = "".join(f'<option value="{esc(d)}">{esc(issue_label(d))}</option>' for d in dates)
        parts = [head(f"すべての記事（{y}年） | Life is beautiful 学びの場", "")]
        parts.append(f"""<header class="site"><h1>すべての記事（{y}年）</h1>
<p class="meta">登録されているテーマをすべて並べています（号の日付順）。フィルターと並べ替えは組み合わせて使えます。状態（既読・後で読む・いらない）はこの端末に保存された状態で判定します。</p></header>
""" + year_nav("all", years, y) + """
<div class="filterbar">
<label>状態 <select data-filter-status>
<option value="all">すべて</option>
<option value="unread">未読</option>
<option value="read">既読</option>
<option value="later">後で読む</option>
<option value="skip">いらない</option>
</select></label>
<label>ジャンル <select data-filter-genre>
<option value="all">すべて</option>
""" + genre_opts + """
</select></label>
<label>号 <select data-filter-issue>
<option value="all">すべて</option>
""" + issue_opts + """
</select></label>
<input type="search" data-filter-keyword placeholder="題名で絞り込む" aria-label="題名で絞り込む">
<button type="button" class="mini" data-filter-reset>リセット</button>
</div>
<p class="meta" id="filterCount"></p>
""" + sort_bar() + """
<ul class="list sortable" id="allList">""")
        for date in dates:
            for t in issues[date]:
                parts.append(all_theme_li(t, f't/{t["id"]}.html'))
        parts.append('</ul>')
        parts.append("""<footer>週刊 Life is beautiful 学びの場</footer>
    <script src="assets/app.js"></script>
    <script>
    function readRowVals(el){
      const ttl=el.querySelector('.ttl');
      return {tid:+el.dataset.tid,title:ttl?ttl.textContent:'',genre:el.getAttribute('data-genre-name')||'',issue:el.getAttribute('data-issue')||''};
    }
    function applyFilter(){
      const f=getFilterPref();
      const ctx={read:getRead(),later:getLater(),skip:getSkip()};
      let shown=0,total=0;
      document.querySelectorAll('#allList [data-tid]').forEach(function(el){
        total++;
        const ok=rowMatchesFilter(readRowVals(el),f,ctx);
        el.style.display=ok?'':'none';
        if(ok)shown++;
      });
      document.getElementById('filterCount').textContent='全'+total+'件中 '+shown+'件を表示';
      const st=document.querySelector('[data-filter-status]');if(st)st.value=f.status;
      const ge=document.querySelector('[data-filter-genre]');if(ge){ge.value=f.genre;if(ge.value!==f.genre){ge.value='all';}}
      const is=document.querySelector('[data-filter-issue]');if(is){is.value=f.issue;if(is.value!==f.issue){is.value='all';}}
      const kw=document.querySelector('[data-filter-keyword]');if(kw&&kw.value!==f.keyword)kw.value=f.keyword;
    }
    function bindFilter(sel,field){
      const el=document.querySelector(sel);if(!el)return;
      el.addEventListener('input',function(){const f=getFilterPref();f[field]=el.value;setFilterPref(f);applyFilter();});
      el.addEventListener('change',function(){const f=getFilterPref();f[field]=el.value;setFilterPref(f);applyFilter();});
    }
    bindFilter('[data-filter-status]','status');
    bindFilter('[data-filter-genre]','genre');
    bindFilter('[data-filter-issue]','issue');
    bindFilter('[data-filter-keyword]','keyword');
    const rst=document.querySelector('[data-filter-reset]');
    if(rst)rst.addEventListener('click',function(){setFilterPref({status:'all',genre:'all',issue:'all',keyword:''});applyFilter();});
    window.onPrefChange=applyFilter;
    applyFilter();
    </script></div></body></html>""")
        fname = "all.html" if y == latest else f"all-{y}.html"
        pages[fname] = "\n".join(parts)
    return pages


def deliveries_page(delivered):
    # 配信ごとの一覧（配信ラベル単位、古い順）。delivered は配信順に整列済み。
    # 過去号アーカイブのグループは件数が多いため、行を並べず、号ごとページへの
    # リンクカードにする。
    groups = {}
    for t in delivered:
        groups.setdefault(t.get("delivery_label") or "配信日時は未記録", []).append(t)
    years = sorted({t["issue_date"][:4] for t in delivered})
    latest = years[-1] if years else None
    parts = [head("配信ごとに見る | Life is beautiful 学びの場", "")]
    parts.append("""<header class="site"><h1>配信ごとに見る</h1>
<p class="meta">配信1回分ずつ、その回に届いたテーマを古い順に並べています。</p></header>""")
    parts.append(sort_bar("並べ替えは各配信グループの中で効きます"))
    for label, ts in groups.items():
        if label == ARCHIVE_LABEL:
            links = []
            for y in sorted({t["issue_date"][:4] for t in ts}):
                href = "issues.html" if y == latest else f"issues-{y}.html"
                links.append(f'<a href="{href}">{esc(y)}年の号</a>')
            parts.append(f'<div class="card"><div class="ttl">{esc(label)}</div><p class="meta">過去号 {len(ts)} 件を一括で取り込みました。号ごとの一覧から読めます: ' + " ｜ ".join(links) + '</p></div>')
            continue
        lis = "".join(theme_li(t, f't/{t["id"]}.html') for t in ts)
        parts.append(f'<div class="card"><div class="ttl">{esc(label)}</div><ul class="list sortable">{lis}</ul></div>')
    parts.append('<footer>週刊 Life is beautiful 学びの場</footer><script src="assets/app.js"></script></div></body></html>')
    return "\n".join(parts)


def issues_page(issues):
    # 号ごとの一覧（号の日付順、号内はテーマ順）。年別に分割し
    # {ファイル名: HTML} を返す（最新年が issues.html、他の年は issues-<年>.html）。
    years = sorted({d[:4] for d in issues})
    latest = years[-1]
    pages = {}
    for y in years:
        parts = [head(f"号ごとに見る（{y}年） | Life is beautiful 学びの場", "")]
        parts.append(f"""<header class="site"><h1>号ごとに見る（{y}年）</h1>
<p class="meta">号ごとに、その号のテーマを並べています。</p></header>""")
        parts.append(year_nav("issues", years, y))
        parts.append(sort_bar("並べ替えは各号の中で効きます"))
        for date in sorted(d for d in issues if d[:4] == y):
            ts = issues[date]
            lis = "".join(theme_li(t, f't/{t["id"]}.html') for t in ts)
            parts.append(f'<div class="card"><div class="ttl">{esc(issue_label(date))}</div><ul class="list sortable">{lis}</ul></div>')
        parts.append('<footer>週刊 Life is beautiful 学びの場</footer><script src="assets/app.js"></script></div></body></html>')
        fname = "issues.html" if y == latest else f"issues-{y}.html"
        pages[fname] = "\n".join(parts)
    return pages


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
        parts.append(sort_bar())
        lis = "".join(theme_li(t, f'../t/{t["id"]}.html') for t in ts)
        parts.append(f'<ul class="list sortable">{lis}</ul>')
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
<p class="meta">各テーマに書いたメモの一覧です。テーマごとに、そのテーマのメモをすべて表示しています（新しいメモがあるテーマ順）。ここでも各メモを編集でき、入力すると自動で保存されます。空にするとそのメモは削除されます。この状態はこの端末の中にだけ保存されます。</p></header>
<div id="memoBox"><p class="meta">読み込み中…</p></div>""")
    script = """<footer>週刊 Life is beautiful 学びの場</footer>
<script src="assets/app.js"></script>
<script>
const INFO=__INFO__;
function escHtml(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
function render(){
  const m=getMemos();
  const ids=Object.keys(m).map(Number).filter(function(id){return INFO[id]&&(m[id]||[]).length});
  ids.sort(function(a,b){
    const la=m[a][m[a].length-1],lb=m[b][m[b].length-1];
    return String((lb&&lb.at)||'').localeCompare(String((la&&la.at)||''));
  });
  const box=document.getElementById('memoBox');
  if(!ids.length){box.innerHTML='<p class="meta">まだメモがありません。各記事ページのメモボタンから書けます。改行すると別のメモとして記録されます。</p>';return;}
  box.innerHTML=ids.map(function(id){
    const t=INFO[id];
    const entries=m[id].map(function(mm,i){
      return '<div class="memo-entry"><textarea data-memo-edit="'+id+'_'+i+'"></textarea><div class="memo-status"></div><div class="memo-row-meta"><span class="meta">'+escHtml(fmtDate(mm.at))+'</span><button class="mini skipb" data-memo-del="'+id+'_'+i+'">削除</button></div></div>';
    }).join('');
    return '<div class="card memo-item"><a class="ttl" href="t/'+id+'.html">'+escHtml(t.title)+'</a><div class="meta">'+escHtml(t.issue)+(t.label?'｜'+escHtml(t.label):'')+'</div>'+entries+'</div>';
  }).join('');
  box.querySelectorAll('[data-memo-edit]').forEach(function(ta){
    const kv=ta.getAttribute('data-memo-edit').split('_');const id=kv[0],idx=+kv[1];
    const cur=getMemos()[id]||[];if(cur[idx])ta.value=cur[idx].text;
    const st=ta.parentElement.querySelector('.memo-status');
    ta.addEventListener('input',function(){
      if(ta.value.trim()){updateMemoText(id,idx,ta.value);if(st)st.textContent='保存しました';}
      else if(st)st.textContent='空にすると削除されます';
    });
    ta.addEventListener('change',function(){if(!ta.value.trim()){deleteMemoAt(id,idx);render();}});
  });
  box.querySelectorAll('[data-memo-del]').forEach(function(b){
    b.addEventListener('click',function(){const kv=b.getAttribute('data-memo-del').split('_');deleteMemoAt(kv[0],+kv[1]);render();});
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

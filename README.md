# insurance-hearing

保険の営業・相談まわりを手伝う小さなツール集です。サーバー不要の静的ページなので、GitHub Pages でそのまま動きます。

| ページ / ツール | 内容 |
|---|---|
| [`index.html`](./index.html) | 保険ヒアリング AIアシスト。その場の聞き取りから社内共有メモと確認リストを作る |
| [`yakkan.html`](./yakkan.html) | 約款チャット。約款PDFを読み込み、質問に関係する条文を探して、条文を根拠に回答する |
| [`watcher/`](./watcher) | 保険ルール改定の情報収集。金融庁・厚労省・業界団体の新着を集める |

## 約款チャット（yakkan.html）

1. 保険会社のサイトから「ご契約のしおり・約款」のPDFをダウンロードする
   - 例：[かんぽ生命 Web約款](https://www.jp-life.japanpost.jp/products/clause/index.html)、各社の「約款」ページ
2. ページにPDFをドロップする。条文（第◯条）ごとに分けて、ブラウザ内（IndexedDB）に保存される
3. 質問する
   - **APIキーなし**：質問に関係しそうな条文を検索して表示する（文字bigramのBM25検索と、日常語→約款用語の言い換え辞書）
   - **APIキーあり**：見つかった条文をClaudeに渡して、条番号とページを示した回答を作る

注意点

- 約款は**契約した時期の版**が適用されます。名前欄に「商品名・版（年月）」を入れて、版ごとに分けて読み込んでください。
- 約款PDFは各社の著作物なので、リポジトリには入れません（`.gitignore` で `*.pdf` を除外）。
- APIキーはその端末のブラウザ（localStorage）にだけ保存され、ブラウザから Anthropic API へ直接送られます。個人利用の試作向けの方式です。複数人で使う場合は、キーをサーバー側に置く構成にしてください。
- 回答は下書きです。支払可否の最終判断は保険会社が行います。

## 情報収集（watcher/）

標準ライブラリだけで動く Python スクリプトです。

```bash
python3 watcher/check_updates.py            # 新着を表示し、既読（watcher/seen.json）を更新
python3 watcher/check_updates.py --dry-run  # 既読を更新しない
python3 watcher/check_updates.py --json     # 自動化向けに JSON で出力
```

- 見に行く先とキーワードは [`watcher/sources.json`](./watcher/sources.json) で変えられます
  - RSS：金融庁、厚生労働省（キーワードに合う記事だけ）
  - お知らせ一覧ページ：損害保険料率算出機構、生命保険協会、日本損害保険協会（全件）
- `seen.json` に既読のURLを記録しているので、2回目以降は新しく出た記事だけが出ます

### 定期実行の例（Claude Code のルーティン）

毎朝このスクリプトを動かし、新着をAIで要約して Notion などに記録できます。ルーティンに渡す指示の例：

> insurance-hearing リポジトリで `python3 watcher/check_updates.py --json` を実行してください。
> 新着があれば、保険の契約者・募集人に影響しそうなものを選び、各記事について
> 「何が変わるか・いつから・誰に影響するか」を3行で要約して Notion の「保険ルール改定ウォッチ」に追記してください。
> 最後に `watcher/seen.json` の変更をコミットしてプッシュしてください。新着がなければ何もしないでください。

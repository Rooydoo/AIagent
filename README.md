# Paper Agent

医学研究者向け論文管理・文書作成AIエージェントシステム

## 機能

### 論文管理
- **PubMed/PMC検索**: キーワード検索、論文タイプフィルタ（レビュー、RCT等）、年代指定
- **PDFダウンロード**: PMC Open Accessから自動ダウンロード（30ページ以内）
- **Abstract要約**: Claude Haikuによる自動要約生成
- **タグ・お気に入り**: 論文の整理・分類

### 文書作成
- **レビュー論文自動生成**: 複数論文を引用した学術文書作成
- **セクション別生成**: Introduction, Methods, Results, Discussion, Conclusion
- **引用管理**: 自動番号付け、引用整合性チェック
- **出力フォーマット**: Word (docx), PDF
- **引用スタイル**: Vancouver, APA, Harvard

### プロジェクト管理
- **最大5プロジェクト**: 各プロジェクト300会話履歴（FIFO）
- **自動アーカイブ**: 6個目作成時に最古プロジェクトを自動保存
- **プロジェクト別引用リスト**: 論文はグローバル共有、引用はプロジェクト別

### その他
- **ファイル操作**: PDF移動・コピー・削除・リネーム、フォルダ管理
- **Telegram連携**: 論文検索、通知（オプション）

## 技術スタック

- **フロントエンド**: Electron（日本語UI）
- **バックエンド**: FastAPI
- **AI**: Claude API
  - Sonnet 4.5: 文書生成、構成提案
  - Haiku 4.5: 要約生成、意図分類
- **LLM統合**: Langchain（キャッシング、会話履歴管理）
- **データベース**: SQLite
- **文書生成**: python-docx, reportlab
- **論文取得**: NCBI E-utilities API

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイル

`config.json`を編集してAPIキーを設定:

```json
{
  "anthropic_api_key": "YOUR_ANTHROPIC_API_KEY",
  "telegram_bot_token": "YOUR_TELEGRAM_BOT_TOKEN (optional)",
  "database_path": "data/paper_agent.db",
  "papers_directory": "papers",
  "outputs_directory": "outputs",
  "default_citation_style": "Vancouver",
  "max_projects": 5,
  "max_conversation_history": 300,
  "max_paper_pages": 30
}
```

または環境変数で設定:

```bash
export ANTHROPIC_API_KEY="your_api_key_here"
export TELEGRAM_BOT_TOKEN="your_bot_token_here"  # オプション
```

### 3. バックエンド起動

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 4. Electron UI起動（オプション）

```bash
npm install
npm start
```

### 5. APIドキュメント

ブラウザで http://localhost:8000/docs にアクセス

## API エンドポイント

### プロジェクト管理
- `POST /api/projects` - 新規プロジェクト作成（自動アーカイブ対応）
- `GET /api/projects` - プロジェクト一覧
- `GET /api/projects/{id}` - プロジェクト詳細
- `PUT /api/projects/{id}` - プロジェクト更新
- `DELETE /api/projects/{id}` - プロジェクト削除

### チャット
- `POST /api/chat` - メッセージ送信（意図分類、タスク分解）
- `GET /api/chat/{project_id}/history` - 会話履歴取得

### 論文管理
- `POST /api/papers/search` - 論文検索
  - クエリ最適化
  - 論文タイプフィルタ（review, systematic_review, rct等）
  - 除外フィルタ（case_report, editorial等）
  - 年代フィルタ、フリーアクセス限定
- `POST /api/papers/download` - PDFダウンロード
- `GET /api/papers` - 論文一覧
- `GET /api/papers/{pmid}` - 論文詳細
- `PUT /api/papers/{pmid}` - 論文更新（タグ、お気に入り）
- `DELETE /api/papers/{pmid}` - 論文削除

### 文書作成
- `POST /api/documents/structure` - 文書構成提案
- `POST /api/documents/generate-section` - セクション生成
- `POST /api/documents` - 完全文書生成
- `GET /api/documents/project/{project_id}` - プロジェクトの文書一覧
- `GET /api/documents/{id}/download` - 文書ダウンロード
- `GET /api/documents/{id}/citations` - 引用一覧
- `PUT /api/documents/{id}` - セクション更新

### ファイル操作
- `POST /api/files/move` - ファイル移動
- `POST /api/files/copy` - ファイルコピー
- `POST /api/files/delete` - ファイル削除
- `POST /api/files/rename` - ファイルリネーム
- `POST /api/files/folders/create` - フォルダ作成
- `DELETE /api/files/folders/{path}` - フォルダ削除

### 統計
- `GET /api/stats/tokens` - トークン使用量

## 使用例

### 論文検索

```bash
curl -X POST "http://localhost:8000/api/papers/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "脳卒中リハビリ",
    "include_types": ["systematic_review", "meta_analysis"],
    "exclude_types": ["case_report"],
    "year_from": 2020,
    "max_results": 20
  }'
```

### 文書作成

```bash
curl -X POST "http://localhost:8000/api/documents" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "project-uuid",
    "topic": "脳卒中リハビリテーションにおけるtDCSの効果",
    "paper_pmids": ["12345678", "23456789"],
    "file_type": "docx",
    "citation_style": "Vancouver",
    "language": "ja"
  }'
```

## Telegram Bot

### セットアップ

1. BotFatherでbotを作成しトークンを取得
2. `config.json`または環境変数に設定
3. バックエンド起動時に自動起動

### 利用可能なコマンド

- `/start` - Bot起動
- `/search <キーワード>` - 論文検索
- `/help` - ヘルプ表示
- `/status` - システムステータス

## ディレクトリ構造

```
paper-agent/
├── backend/                 # FastAPI Backend
│   ├── api/                # APIエンドポイント
│   ├── llm/                # LLM処理（意図分類、要約、文書生成等）
│   ├── services/           # ビジネスロジック
│   ├── integrations/       # 外部API（PubMed）
│   └── utils/              # ユーティリティ
├── frontend/               # Electron UI
├── data/                   # データベース・ログ
├── papers/                 # 論文PDF保存
├── outputs/                # 生成文書
└── archived_projects/      # アーカイブプロジェクト
```

## 開発状況

### Phase 1 - コア機能 ✅
- データベース構築
- FastAPI基本構造
- Claude API連携
- Langchain統合
- Electron UI

### Phase 2 - 論文検索 ✅
- PubMed/PMC API連携
- クエリ最適化
- Abstract要約生成
- PDFダウンロード
- 論文タイプフィルタ

### Phase 3 - 文書作成 ✅
- 文書構成提案
- セクション生成
- 引用管理
- Word/PDF出力
- 引用整合性チェック

### Phase 4 - 追加機能 ✅
- プロジェクト自動アーカイブ
- Telegram Bot統合

## ライセンス

MIT

## 今後の拡張予定

- Ollama対応（ローカルLLM）
- 医中誌対応（日本語論文）
- 図表の自動生成
- Excel出力
- モバイルアプリ

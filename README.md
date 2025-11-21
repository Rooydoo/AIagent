# Paper Agent

医学研究者向け論文管理・文書作成AIエージェントシステム

## 機能

- PubMed/PMC論文の検索・ダウンロード・要約
- 複数論文を引用した学術文書の自動生成（Word/PDF/Excel）
- ファイル・フォルダ管理
- プロジェクト管理（最大5プロジェクト、各300会話履歴）

## 技術スタック

- **フロントエンド**: Electron（日本語UI）
- **バックエンド**: FastAPI
- **AI**: Claude API (Sonnet 4.5 / Haiku 4.5)
- **LLM統合**: Langchain
- **データベース**: SQLite

## セットアップ

### 1. Python依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. 設定ファイルの編集

`config.json`を編集してAPIキーを設定:

```json
{
  "anthropic_api_key": "YOUR_API_KEY_HERE"
}
```

### 3. バックエンドの起動

```bash
cd /home/user/AIagent
python -m uvicorn backend.main:app --reload --port 8000
```

### 4. フロントエンドの起動（Electronを使用する場合）

```bash
npm install
npm start
```

## API エンドポイント

- `POST /api/projects` - 新規プロジェクト作成
- `GET /api/projects` - プロジェクト一覧取得
- `POST /api/chat` - メッセージ送信
- `GET /api/chat/{project_id}/history` - 会話履歴取得
- `POST /api/papers/search` - 論文検索
- `GET /api/papers` - 論文一覧取得
- `POST /api/documents` - 文書生成開始
- `POST /api/files/move` - ファイル移動

## 開発状況

### Phase 1 (完了)
- [x] データベース構築
- [x] 基本的なElectron UI
- [x] FastAPI基本構造
- [x] Claude API連携
- [x] Langchain統合

### Phase 2 (予定)
- [ ] PubMed/PMC検索
- [ ] PDFダウンロード
- [ ] 要約生成

### Phase 3 (予定)
- [ ] 文書構成提案
- [ ] セクション生成
- [ ] 引用管理

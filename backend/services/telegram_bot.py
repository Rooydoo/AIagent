"""Telegram bot integration for paper search and notifications."""
import asyncio
from typing import Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from ..config import settings
from ..integrations.pubmed_client import PubMedClient
from ..llm.query_optimizer import optimize_query
from ..llm.summarizer import summarize_abstract


class PaperAgentBot:
    """Telegram bot for paper agent."""

    def __init__(self, token: str):
        self.token = token
        self.application = None

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = """
📚 Paper Agent Bot へようこそ！

利用可能なコマンド:
/search <検索キーワード> - 論文を検索
/help - ヘルプを表示

例: /search 脳卒中 tDCS
        """
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = """
📖 ヘルプ

/search <キーワード> - PubMedで論文を検索します
  例: /search stroke rehabilitation tDCS

/status - システムステータスを確認

今後の機能:
- 論文ダウンロード指示
- 文書作成完了通知
        """
        await update.message.reply_text(help_text)

    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        if not context.args:
            await update.message.reply_text("検索キーワードを入力してください。\n例: /search stroke tDCS")
            return

        query = " ".join(context.args)
        await update.message.reply_text(f"🔍 検索中: {query}")

        try:
            # Optimize query
            optimized = await optimize_query(query)

            # Search PubMed
            client = PubMedClient()
            search_result = await client.search(optimized, max_results=10)

            if search_result.get("pmids"):
                details = await client.fetch_details(search_result["pmids"][:5])
                await client.close()

                message = f"✅ 検索完了（{search_result['total_count']}件見つかりました）\n"
                message += f"最適化されたクエリ: {optimized}\n\n"
                message += "上位5件:\n\n"

                for i, paper in enumerate(details, 1):
                    if "error" in paper:
                        continue

                    title = paper.get("title", "Unknown")
                    authors = ", ".join(paper.get("authors", [])[:2])
                    year = paper.get("year", "N/A")
                    pmid = paper.get("pmid", "")
                    has_pmc = "✓" if paper.get("pmc_id") else "✗"

                    message += f"{i}. {title}\n"
                    message += f"   著者: {authors} et al.\n"
                    message += f"   年: {year} | PMID: {pmid} | フリー: {has_pmc}\n\n"

                await update.message.reply_text(message)
            else:
                await update.message.reply_text("❌ 検索結果が見つかりませんでした。")

        except Exception as e:
            await update.message.reply_text(f"❌ エラーが発生しました: {str(e)}")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        await update.message.reply_text("✅ システムは正常に稼働しています。")

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle general messages."""
        await update.message.reply_text(
            "コマンドを使用してください。ヘルプは /help で確認できます。"
        )

    def setup_handlers(self):
        """Setup bot handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler)
        )

    async def start(self):
        """Start the bot."""
        if not self.token:
            raise ValueError("Telegram bot token not configured")

        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()

        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        print("✅ Telegram bot started")

    async def stop(self):
        """Stop the bot."""
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()
            print("❌ Telegram bot stopped")


# Global bot instance
_bot_instance: Optional[PaperAgentBot] = None


async def start_telegram_bot():
    """Start the Telegram bot."""
    global _bot_instance

    if not settings.telegram_bot_token:
        print("⚠️  Telegram bot token not configured, skipping bot startup")
        return None

    _bot_instance = PaperAgentBot(settings.telegram_bot_token)
    await _bot_instance.start()
    return _bot_instance


async def stop_telegram_bot():
    """Stop the Telegram bot."""
    global _bot_instance
    if _bot_instance:
        await _bot_instance.stop()
        _bot_instance = None


def get_bot_instance() -> Optional[PaperAgentBot]:
    """Get the current bot instance."""
    return _bot_instance

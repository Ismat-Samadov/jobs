"""
Telegram notification module for scraper results
"""
import asyncio
import aiohttp
import os
import sys
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

# Load .env from parent directory (scraper/)
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class TelegramNotifier:
    """Send scraping reports to Telegram channel(s)"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None, db_pool=None):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram Bot API token
            chat_id: Telegram chat/channel ID(s) - can be comma-separated for multiple recipients
            db_pool: Database connection pool for querying actual stats
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id_str = chat_id or os.getenv('TELEGRAM_CHAT_ID')

        # Support multiple chat IDs (comma-separated)
        if chat_id_str:
            self.chat_ids = [cid.strip() for cid in chat_id_str.split(',') if cid.strip()]
        else:
            self.chat_ids = []

        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        self.db_pool = db_pool

    def is_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.bot_token and self.chat_ids)

    def get_database_stats(self) -> Dict[str, int]:
        """
        Query database for actual lead statistics

        Returns:
            Dict with total_leads, today_leads, yesterday_leads
        """
        if not self.db_pool:
            return {'total_leads': 0, 'today_leads': 0, 'yesterday_leads': 0}

        conn = None
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor()

            # Get total leads count
            cursor.execute("SELECT COUNT(*) FROM leads.leads")
            total_leads = cursor.fetchone()[0]

            # Get today's leads count
            cursor.execute("""
                SELECT COUNT(*) FROM leads.leads
                WHERE DATE(created_at) = CURRENT_DATE
            """)
            today_leads = cursor.fetchone()[0]

            # Get yesterday's leads count (for comparison)
            cursor.execute("""
                SELECT COUNT(*) FROM leads.leads
                WHERE DATE(created_at) = CURRENT_DATE - INTERVAL '1 day'
            """)
            yesterday_leads = cursor.fetchone()[0]

            cursor.close()
            self.db_pool.putconn(conn)

            return {
                'total_leads': total_leads,
                'today_leads': today_leads,
                'yesterday_leads': yesterday_leads
            }

        except Exception as e:
            print(f"Error querying database stats: {e}")
            if conn:
                self.db_pool.putconn(conn)
            return {'total_leads': 0, 'today_leads': 0, 'yesterday_leads': 0}

    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send message to Telegram (to all configured chat IDs)

        Args:
            message: Message text to send
            parse_mode: Message formatting (HTML or Markdown)

        Returns:
            True if sent successfully to at least one chat, False otherwise
        """
        if not self.is_configured():
            print("Telegram not configured - skipping notification")
            return False

        success_count = 0
        total_chats = len(self.chat_ids)

        try:
            async with aiohttp.ClientSession() as session:
                for chat_id in self.chat_ids:
                    try:
                        payload = {
                            'chat_id': chat_id,
                            'text': message,
                            'parse_mode': parse_mode
                        }

                        async with session.post(self.api_url, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                            if response.status == 200:
                                success_count += 1
                                print(f"✓ Sent to chat {chat_id}")
                            else:
                                error_text = await response.text()
                                print(f"✗ Failed to send to chat {chat_id} (HTTP {response.status}): {error_text}")

                    except asyncio.TimeoutError:
                        print(f"✗ Error sending to chat {chat_id}: Timeout after 30 seconds")
                    except Exception as e:
                        error_msg = str(e) if str(e) else type(e).__name__
                        print(f"✗ Error sending to chat {chat_id}: {error_msg}")

        except Exception as e:
            print(f"Failed to send Telegram notifications: {e}")
            return False

        print(f"Telegram: {success_count}/{total_chats} messages sent successfully")
        return success_count > 0

    async def send_scraper_report(self, source: str, stats: Dict[str, int], duration: float, start_time: datetime) -> bool:
        """
        Send formatted scraper report to Telegram

        Args:
            source: Source name (e.g., "EVV.AZ", "Villa.AZ")
            stats: Dictionary with scraping statistics
            duration: Scraping duration in seconds
            start_time: When scraping started

        Returns:
            True if sent successfully, False otherwise
        """
        # Calculate metrics
        total = stats.get('total', 0)
        saved = stats.get('saved', 0)
        failed = stats.get('failed', 0)
        extracted = total - failed

        extraction_rate = (extracted / total * 100) if total > 0 else 0
        save_rate = (saved / extracted * 100) if extracted > 0 else 0

        # Determine status emoji
        if extraction_rate >= 80:
            status_emoji = "✅"
        elif extraction_rate >= 50:
            status_emoji = "⚠️"
        else:
            status_emoji = "❌"

        # Format message
        message = f"""
{status_emoji} <b>{source} Scraping Report</b>

📊 <b>Statistics</b>
━━━━━━━━━━━━━━━━━━
📋 Total Listings: <code>{total}</code>
📱 Phones Extracted: <code>{extracted}</code> ({extraction_rate:.1f}%)
💾 New Saved: <code>{saved}</code> ({save_rate:.1f}% of extracted)
🔄 Duplicates/Invalid: <code>{extracted - saved}</code>
❌ Failed: <code>{failed}</code>

⏱ <b>Performance</b>
━━━━━━━━━━━━━━━━━━
🕐 Started: <code>{start_time.strftime('%Y-%m-%d %H:%M:%S')}</code>
⏳ Duration: <code>{duration:.2f}s</code>
⚡ Speed: <code>{total / duration:.1f}</code> listings/sec

🎯 <b>Status</b>: {'Success' if extraction_rate >= 70 else 'Partial Success' if extraction_rate >= 50 else 'Check Logs'}
"""

        return await self.send_message(message.strip())

    async def send_multi_source_report(self, reports: list, total_duration: float) -> bool:
        """
        Send combined report for multiple sources

        Args:
            reports: List of dicts with 'source', 'stats', 'duration', 'start_time'
            total_duration: Total duration for all sources

        Returns:
            True if sent successfully, False otherwise
        """
        total_listings = 0
        total_extracted = 0
        total_saved = 0
        total_failed = 0

        # Build individual source summaries
        source_summaries = []
        for report in reports:
            source = report['source']
            stats = report['stats']

            # Handle different stat formats
            # Format 1: 'total', 'saved', 'failed' (EVV, Villa, Bul, BiTurbo, AutoNet)
            # Format 2: 'new_leads', 'duplicates', 'errors' (XiDMETLER, BIRJA, QARABAZAR)
            if 'total' in stats:
                total = stats.get('total', 0)
                saved = stats.get('saved', 0)
                failed = stats.get('failed', 0)
                extracted = total - failed
            else:
                # Format 2: calculate from new_leads + duplicates
                saved = stats.get('new_leads', 0)
                duplicates = stats.get('duplicates', 0)
                failed = stats.get('errors', 0)
                invalid = stats.get('invalid_phones', 0)
                extracted = saved + duplicates
                total = extracted + failed + invalid

            total_listings += total
            total_extracted += extracted
            total_saved += saved
            total_failed += failed

            extraction_rate = (extracted / total * 100) if total > 0 else 0
            emoji = "✅" if extraction_rate >= 80 else "⚠️" if extraction_rate >= 50 else "❌"

            source_summaries.append(
                f"{emoji} <b>{source}</b>: {extracted}/{total} ({extraction_rate:.1f}%) | Saved: {saved}"
            )

        # Get actual database statistics
        db_stats = self.get_database_stats()
        actual_today_saved = db_stats['today_leads']
        actual_total_leads = db_stats['total_leads']

        # Calculate duplicates from scraped data vs actual saves in this run
        actual_duplicates = total_extracted - total_saved if total_extracted >= total_saved else 0

        # Overall metrics
        overall_extraction_rate = (total_extracted / total_listings * 100) if total_listings > 0 else 0
        overall_save_rate = (total_saved / total_extracted * 100) if total_extracted > 0 else 0

        # Determine overall status
        if overall_extraction_rate >= 80:
            status_emoji = "✅"
            status_text = "Excellent"
        elif overall_extraction_rate >= 50:
            status_emoji = "⚠️"
            status_text = "Good"
        else:
            status_emoji = "❌"
            status_text = "Check Required"

        # Format message
        message = f"""
{status_emoji} <b>Multi-Source Scraping Report</b>

📊 <b>Overall Statistics</b>
━━━━━━━━━━━━━━━━━━
📋 Total Listings Scraped: <code>{total_listings}</code>
📱 Phones Extracted: <code>{total_extracted}</code> ({overall_extraction_rate:.1f}%)
💾 New Saved (This Run): <code>{total_saved}</code> ({overall_save_rate:.1f}%)
🔄 Duplicates/Invalid: <code>{actual_duplicates}</code>
❌ Failed Extractions: <code>{total_failed}</code>

📍 <b>By Source</b>
━━━━━━━━━━━━━━━━━━
{chr(10).join(source_summaries)}

⏱ <b>Performance</b>
━━━━━━━━━━━━━━━━━━
⏳ Total Duration: <code>{total_duration / 60:.1f} min</code> ({total_duration:.0f}s)
⚡ Overall Speed: <code>{total_listings / total_duration:.1f}</code> listings/sec

💼 <b>Database Totals</b>
━━━━━━━━━━━━━━━━━━
📊 Total Leads in DB: <code>{actual_total_leads:,}</code>
📅 Added Today: <code>{actual_today_saved}</code>
📆 Added Yesterday: <code>{db_stats['yesterday_leads']}</code>

🎯 <b>Status</b>: {status_text}
"""

        return await self.send_message(message.strip())


# Example usage
async def test_notification():
    """Test Telegram notification"""
    notifier = TelegramNotifier()

    if not notifier.is_configured():
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        return

    # Test single source report
    test_stats = {
        'total': 100,
        'saved': 45,
        'failed': 10
    }

    success = await notifier.send_scraper_report(
        source="EVV.AZ",
        stats=test_stats,
        duration=25.5,
        start_time=datetime.now()
    )

    if success:
        print("✓ Test notification sent successfully!")
    else:
        print("✗ Failed to send test notification")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_notification())

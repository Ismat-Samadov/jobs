"""
Telegram notification module for scraper results
"""
import aiohttp
import os
from typing import Dict, Optional
from datetime import datetime


class TelegramNotifier:
    """Send scraping reports to Telegram channel"""

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram notifier

        Args:
            bot_token: Telegram Bot API token
            chat_id: Telegram chat/channel ID
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

    def is_configured(self) -> bool:
        """Check if Telegram is properly configured"""
        return bool(self.bot_token and self.chat_id)

    async def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send message to Telegram

        Args:
            message: Message text to send
            parse_mode: Message formatting (HTML or Markdown)

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured():
            print("Telegram not configured - skipping notification")
            return False

        try:
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return True
                    else:
                        error_text = await response.text()
                        print(f"Telegram API error (HTTP {response.status}): {error_text}")
                        return False

        except Exception as e:
            print(f"Failed to send Telegram notification: {e}")
            return False

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

            total = stats.get('total', 0)
            saved = stats.get('saved', 0)
            failed = stats.get('failed', 0)
            extracted = total - failed

            total_listings += total
            total_extracted += extracted
            total_saved += saved
            total_failed += failed

            extraction_rate = (extracted / total * 100) if total > 0 else 0
            emoji = "✅" if extraction_rate >= 80 else "⚠️" if extraction_rate >= 50 else "❌"

            source_summaries.append(
                f"{emoji} <b>{source}</b>: {extracted}/{total} ({extraction_rate:.1f}%) | Saved: {saved}"
            )

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
📋 Total Listings: <code>{total_listings}</code>
📱 Phones Extracted: <code>{total_extracted}</code> ({overall_extraction_rate:.1f}%)
💾 New Saved: <code>{total_saved}</code> ({overall_save_rate:.1f}%)
🔄 Duplicates/Invalid: <code>{total_extracted - total_saved}</code>
❌ Failed: <code>{total_failed}</code>

📍 <b>By Source</b>
━━━━━━━━━━━━━━━━━━
{chr(10).join(source_summaries)}

⏱ <b>Performance</b>
━━━━━━━━━━━━━━━━━━
⏳ Total Duration: <code>{total_duration:.2f}s</code>
⚡ Overall Speed: <code>{total_listings / total_duration:.1f}</code> listings/sec

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

# Fix: Timeout Error Handling in BiTurbo.AZ Scraper

## Problem
The BiTurbo.AZ scraper was experiencing timeout errors when fetching listings. While these errors were being caught in the exception handler, they were being logged with full stack traces using `traceback.print_exc()`, which created very verbose and cluttered output.

### Original Error Output
```
Error processing listing: https://www.biturbo.az/az/avtomobil-elanlari/hyundai-sonata-489883/ -
Traceback (most recent call last):
  File "/Users/ismatsamadov/lead_generator/scraper/sources/biturbo_az_scraper.py", line 254, in process_listing
    async with session.get(listing['url'], headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as response:
  File "/Users/ismatsamadov/lead_generator/scraper/venv/lib/python3.10/site-packages/aiohttp/client.py", line 1187, in __aenter__
    self._resp = await self._coro
  ... (many more lines of stack trace)
asyncio.exceptions.TimeoutError
```

## Root Causes
1. **Short timeout**: 15 seconds was too short for biturbo.az to respond
2. **Verbose error logging**: Using `traceback.print_exc()` printed full stack traces
3. **No specific timeout handling**: All exceptions were handled the same way

## Solution Implemented

### File: `scraper/sources/biturbo_az_scraper.py`

**Changes made (lines 252-288):**

1. **Increased timeout** from 15s to 30s:
```python
# Before
timeout=aiohttp.ClientTimeout(total=15)

# After
timeout=aiohttp.ClientTimeout(total=30)
```

2. **Added specific exception handlers**:
```python
except asyncio.TimeoutError:
    # Handle timeout errors gracefully without full stack trace
    print(f"  ⏱️ Timeout fetching listing (30s): {listing['url']}")
except aiohttp.ClientError as e:
    # Handle network-related errors
    print(f"  ❌ Network error for {listing['url']}: {type(e).__name__}")
except Exception as e:
    # Handle other unexpected errors
    print(f"  ❌ Error processing listing {listing['url']}: {type(e).__name__} - {str(e)[:100]}")
```

3. **Removed verbose logging**:
   - Removed `import traceback`
   - Removed `traceback.print_exc()`

4. **Improved output formatting**:
   - Added emoji indicators (⏱️, ❌, ⚠️) for better visual scanning
   - Truncated error messages to 100 characters
   - Only show exception type, not full stack trace

## Results

### Before Fix
```
Error processing listing: https://www.biturbo.az/az/avtomobil-elanlari/hyundai-sonata-489883/ -
Traceback (most recent call last):
  File ".../biturbo_az_scraper.py", line 254, in process_listing
    async with session.get(listing['url']...
  [30+ lines of stack trace]
asyncio.exceptions.TimeoutError
```

### After Fix
```
⏱️ Timeout fetching listing (30s): https://www.biturbo.az/az/avtomobil-elanlari/hyundai-sonata-489883/
```

## Benefits
1. **Cleaner output**: One-line error messages instead of 30+ line stack traces
2. **Better debugging**: Emoji indicators make it easy to scan for error types
3. **Fewer timeouts**: 30s timeout gives biturbo.az more time to respond
4. **Proper error categorization**: Different handling for timeouts vs network errors vs other exceptions
5. **Production-ready**: Error output is suitable for logs and monitoring

## Error Types Handled

### 1. Timeout Errors (asyncio.TimeoutError)
- **Cause**: Website takes > 30s to respond
- **Output**: `⏱️ Timeout fetching listing (30s): [URL]`
- **Action**: Scraper continues to next listing

### 2. Network Errors (aiohttp.ClientError)
- **Cause**: Connection issues, DNS failures, SSL errors
- **Output**: `❌ Network error for [URL]: ClientConnectorError`
- **Action**: Scraper continues to next listing

### 3. Other Exceptions (catch-all)
- **Cause**: Parsing errors, database issues, unexpected errors
- **Output**: `❌ Error processing listing [URL]: ValueError - invalid literal...`
- **Action**: Scraper continues to next listing

## Configuration

Current timeout settings for all scrapers:

| Scraper | Timeout | Notes |
|---------|---------|-------|
| BiTurbo.AZ | 30s | Increased from 15s (fixed) |
| EVV.AZ | 30s | Working well |
| Villa.AZ | 30s | Working well |
| Bul.AZ | 30s | Working well |
| Turbo.AZ | Sync | No async timeout |
| Lalafo.AZ | 30s | New scraper |
| Others | 30s | Standard |

## Testing

To test the fix:

```bash
cd scraper
python sources/biturbo_az_scraper.py
```

Expected output (with timeouts):
```
Started at 2025-11-05 17:30:00
⏱️ Timeout fetching listing (30s): https://www.biturbo.az/az/avtomobil-elanlari/...
⏱️ Timeout fetching listing (30s): https://www.biturbo.az/az/avtomobil-elanlari/...
✓ Saved: 775062013 - BMW 530
✓ Saved: 507654321 - Mercedes E200
...
Completed in 125.45s | Found: 50 | Saved: 35 | Failed: 15
```

## Prevention

To prevent similar issues in future scrapers:

1. **Always use specific exception handlers** for common error types:
   - `asyncio.TimeoutError` for timeouts
   - `aiohttp.ClientError` for network errors
   - `Exception` as catch-all

2. **Never use `traceback.print_exc()`** in production code unless debugging

3. **Use descriptive, single-line error messages** with error type name

4. **Set appropriate timeouts** (30s is good for most Azerbaijan sites)

5. **Add visual indicators** (emojis) for different error types

## Related Files
- `/Users/ismatsamadov/lead_generator/scraper/sources/biturbo_az_scraper.py` (lines 252-288)
- All other scrapers in `/Users/ismatsamadov/lead_generator/scraper/sources/` follow similar patterns

## Status
✅ **Fixed** - BiTurbo.AZ scraper now handles timeout errors gracefully with clean, concise error messages.

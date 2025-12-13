# TODO - Codebase Issues

## Critical

### 2. Blocking sleep calls in file monitor (file_monitor.py:123, 169)
`time.sleep(1)` and `time.sleep(0.5)` block the watchdog observer thread, which can cause missed events during high file activity. Should use a separate worker thread or queue-based processing.

### 3. Memory leak in file_monitor.py
The `last_moved` dictionary (line 58) grows indefinitely as files are processed. Old entries are never cleaned up.

## High Priority

### 4. Inconsistent error output
Mixed use of `print(..., file=sys.stderr)` and `logging.error()`:
- parse_project.py:43, 67 - uses print to stderr
- match_metadata.py:35, 46, 150 - uses print to stderr
- Other modules use logging

Should standardize on logging throughout.

### 5. Unused custom exceptions
`MetadataNotFoundError` and `PdfProcessingError` in logger.py are never used anywhere in the codebase. Either use them or remove them.

### 6. Thread safety issues in controller.py
- The `critique_thread` and `critique_worker` attributes are accessed from multiple threads without synchronization
- If user rapidly clicks "Get AI Critique" before first request completes, behavior is undefined
- The button is disabled but `is_critique_running` flag is set after thread setup, not before

## Medium Priority

### 8. Hardcoded magic numbers
- Similarity thresholds: 0.9 and 0.6 (match_metadata.py:227, 242, 259, 271)
- Character limits: 3000, 8 (match_metadata.py:32, 225)
- Sleep durations: 1s, 0.5s, 2s (file_monitor.py)
- Debounce time: 2s (file_monitor.py:96, 164)

Should be constants or configurable.

### 9. Hardcoded Gemini model name (prep_ai_critique.py:52)
`gemini-3-pro-preview` is hardcoded. Should be configurable or at least a constant.

### 10. UI doing file operations (ui_view.py:249-265)
The `QCWindow.on_right_list_item_clicked` method directly renames files with `os.rename()`. File operations should be delegated to the controller.

### 11. No API key validation before API call
`on_ai_critique_clicked` in controller.py retrieves the API key but the validation only happens inside `get_ai_critique` after the thread is already started.

## Low Priority

### 12. Test files are ad-hoc scripts
- `test_implementation.py` is not a proper test (just prints output)
- `test_parse_project.py` has proper unittest structure but isn't integrated into any test runner
- No tests for controller, file_monitor, match_metadata, prep_ai_critique, or UI

### 13. Global config not thread-safe (config.py:104)
The `config` dict is loaded at module import and accessed/modified from multiple threads (main thread, worker threads, watchdog thread) without synchronization.

### 14. sys.path manipulation in test files
Both test files add the current directory to sys.path which is unnecessary when running from the project root.

### 15. No type hints in several modules
- file_monitor.py
- controller.py
- ui_view.py
- logger.py

parse_project.py and match_metadata.py have partial type hints.

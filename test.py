#!/usr/bin/env python3
"""
SANITIZED VERSION FOR DEVELOPER TESTING (UPDATED FOR STRONG ONLINE PRESENCE)

Цей файл є очищеною копією `keep_online_tdlib.py` з модифікаціями:
- більш агресивні інтервали пінгів/активності для стабільного online;
- рандомізація інтервалів, щоб виглядати природніше;
- виправлені блокуючі time.sleep всередині async-коду (тепер await asyncio.sleep);
- stagger старту акаунтів;
- більш часті підтвердження online.

Розробнику потрібно підставити свої значення перед тестом:

    --root              -> шлях до директорії з TDLib сесіями
    --libtdjson         -> шлях до власної бібліотеки libtdjson.so / .dylib
    --api-id, --api-hash -> власні API ключі Telegram
    --sheet-id          -> власний Google Sheet ID, якщо використовується

Скрипт не логінить акаунти, лише підтримує їх у стані "онлайн".

Основні дефолти ТЕПЕР:
    --ping-interval        30s   (раніше 70)
    --action-interval      15s   (раніше 45)
    --chat-presence-interval 60s (раніше 180)

Ідея: не давати Телеграму встигнути скинути статус із "online".
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import glob
import io
import logging
import contextvars
import os
import random
import hashlib
import sys
import time
from contextlib import suppress
from pathlib import Path
from typing import Optional, Tuple, Dict, Deque, List, Any, Set
from collections import deque
import subprocess
import re
import resource
from urllib import request as urllib_request, parse as urllib_parse

# Reuse helpers and TDLib wrapper from convert_sessions
try:
    import convert_sessions as cs
except Exception as e:
    print(f"Failed to import convert_sessions.py: {e}", file=sys.stderr)
    sys.exit(2)


# --- Logging: reuse the same file for continuity, include phone in each line ---
LOG_FILE = getattr(cs, 'LOG_FILE', 'convert_sessions.log')

class _EnsurePhoneFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Guarantee 'phone' is present to avoid KeyError in formatter
        if not hasattr(record, 'phone'):
            # Try to use context var if available, else '-'
            try:
                record.phone = CURRENT_PHONE.get()
            except Exception:
                record.phone = '-'
        return True

# formatter + handlers
_formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(phone)s]: %(message)s")
_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(_formatter)
_file_handler.addFilter(_EnsurePhoneFilter())
_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_formatter)
_stream_handler.addFilter(_EnsurePhoneFilter())

# replace any existing handlers so we always inject 'phone'
root_logger = logging.getLogger()
for h in list(root_logger.handlers):
    try:
        root_logger.removeHandler(h)
    except Exception:
        pass
root_logger.setLevel(logging.INFO)
_file_handler.setLevel(logging.DEBUG)
_stream_handler.setLevel(logging.DEBUG)
root_logger.addHandler(_file_handler)
root_logger.addHandler(_stream_handler)

# Context variable to propagate current phone into logs emitted by lower layers (e.g., TDLib wrapper)
CURRENT_PHONE: contextvars.ContextVar[str] = contextvars.ContextVar('CURRENT_PHONE', default='-')


# --- Defaults (align with convert_sessions) ---
DEFAULT_ROOT = getattr(cs, 'DEFAULT_ROOT', 'YOUR_SESSION_ROOT_PATH')
DEFAULT_API_ID = 29874443
DEFAULT_API_HASH = "f738a91e86ed53f0f0328a9b4760569c"
CONTROL_REFRESH_INTERVAL_SEC = 1800
DEFAULT_CONTROL_SHEET_ID = "1ohZE2AT6m0YkuP_6TxBc5pvnzht0tTdUeFro7RugLJk"

REACTION_EMOJIS: Tuple[str, ...] = ("👍", "❤️", "🙏", "😁", "💪", "🎉", "🧐", "💰")


_ANDROID_MODELS = [
    "Samsung Galaxy S24",
    "Google Pixel 8",
    "OnePlus 12",
    "Xiaomi 14 Pro",
    "Samsung Galaxy A54",
    "Sony Xperia 1 V",
    "Motorola Edge 50",
    "OPPO Find X7",
    "Vivo X100 Pro",
    "Realme GT 6",
    "Samsung Galaxy S23",
    "Xiaomi 13T Pro",
]

_ANDROID_VERSIONS = ["Android 14", "Android 13", "Android 12"]

_ANDROID_APP_VERSIONS = ["10.13.1", "10.14.0", "11.0.2", "10.12.5"]

_IOS_MODELS = [
    "iPhone 15 Pro",
    "iPhone 15 Pro Max",
    "iPhone 14 Pro",
    "iPhone 14 Pro Max",
    "iPhone 13 Pro",
    "iPhone 13 mini",
    "iPhone SE (3rd generation)",
    "iPad Pro 12.9 (M4)",
    "iPad Pro 11 (M4)",
    "iPad Air (5th generation)",
    "iPad mini (6th generation)",
]

_IOS_VERSIONS = ["iOS 17.5.1", "iOS 17.4.1", "iOS 16.7.8", "iPadOS 17.5"]

_IOS_APP_VERSIONS = ["10.13.1", "10.13.2", "10.12.4", "9.8.3"]

_PLATFORM_CONFIGS: Dict[str, Dict[str, List[str]]] = {
    'android': {
        'models': _ANDROID_MODELS,
        'systems': _ANDROID_VERSIONS,
        'apps': _ANDROID_APP_VERSIONS,
    },
    'ios': {
        'models': _IOS_MODELS,
        'systems': _IOS_VERSIONS,
        'apps': _IOS_APP_VERSIONS,
    },
}

_PLATFORM_NAMES: Tuple[str, ...] = tuple(_PLATFORM_CONFIGS.keys())


def _deterministic_choice(seed_str: str, options: List[str]) -> str:
    h = hashlib.sha256(seed_str.encode()).digest()
    idx = int.from_bytes(h[:4], "big") % len(options)
    return options[idx]


def _infer_platform_from_string(value: Optional[str]) -> Optional[str]:
    text = (value or '').strip().lower()
    if not text:
        return None
    if any(keyword in text for keyword in ('iphone', 'ipad', 'ios', 'ipados', 'apple')):
        return 'ios'
    if any(keyword in text for keyword in ('android', 'pixel', 'galaxy', 'oneplus', 'xiaomi', 'oppo', 'vivo', 'realme', 'sony', 'motorola')):
        return 'android'
    return None


def get_mobile_signature(account_id: Optional[str] = None, preferred_platform: Optional[str] = None) -> Tuple[str, str, str]:
    seed = str(account_id) if account_id is not None else str(random.random())
    platform = (preferred_platform or '').strip().lower() if preferred_platform else None
    if platform not in _PLATFORM_CONFIGS:
        platform = _deterministic_choice(seed + 'platform', list(_PLATFORM_NAMES))
    cfg = _PLATFORM_CONFIGS[platform]
    device_model = _deterministic_choice(seed + platform + 'model', cfg['models'])
    system_version = _deterministic_choice(seed + platform + 'sys', cfg['systems'])
    app_version = _deterministic_choice(seed + platform + 'app', cfg['apps'])
    return device_model, system_version, app_version


def canonicalize_chat_identifier(raw: str) -> Optional[str]:
    text = (raw or '').strip()
    if not text:
        return None
    text = text.strip("'\"")
    text = re.sub(r"[\u00A0\s]+", " ", text)

    # t.me links
    link_match = re.search(r"(?:https?://)?t\.me/(?P<path>[^\s]+)", text, re.IGNORECASE)
    if link_match:
        path = link_match.group('path')
        path = re.split(r"[?#]", path, maxsplit=1)[0]
        if path.startswith('+') or path.lower().startswith('joinchat/'):
            return None
        username = path.split('/', 1)[0]
        username = username.strip('@')
        if re.fullmatch(r'[A-Za-z0-9_]{3,}', username):
            return username
        return None

    # @username
    at_match = re.search(r'@([A-Za-z0-9_]{3,})', text)
    if at_match:
        return at_match.group(1)

    # numeric id или просто username
    if re.fullmatch(r'-?\d{5,}', text):
        return text
    if re.fullmatch(r'[A-Za-z0-9_]{3,}', text):
        return text

    return None


def process_control_entries(values: List[str], label: str) -> List[str]:
    cleaned: List[str] = []
    skipped: List[str] = []
    for raw in values:
        ident = canonicalize_chat_identifier(raw)
        if ident:
            cleaned.append(ident)
        else:
            skipped.append(raw)
    if skipped:
        sample = '; '.join(skipped[:3])
        logging.getLogger().warning(
            f"{label}: пропущено {len(skipped)} запис(ів) — невідомий формат (приклад: {sample})",
            extra={'phone': '-'}
        )
    return _dedupe_preserve_order(cleaned)


class ControlState:
    def __init__(
        self,
        *,
        chat_presence_interval: int,
        scroll_bounds: Tuple[int, int],
        writer_bounds: Tuple[int, int],
    ) -> None:
        self._lock = asyncio.Lock()
        self._chat_presence: List[str] = []
        self._scroll_targets: List[str] = []
        self._writer_targets: List[str] = []
        self._chat_presence_interval = chat_presence_interval
        self._scroll_bounds = scroll_bounds
        self._writer_bounds = writer_bounds
        self._version = 0

    @property
    def version(self) -> int:
        return self._version

    async def snapshot(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                'version': self._version,
                'chat_presence': list(self._chat_presence),
                'scroll_targets': list(self._scroll_targets),
                'writer_targets': list(self._writer_targets),
                'chat_presence_interval': self._chat_presence_interval,
                'scroll_bounds': self._scroll_bounds,
                'writer_bounds': self._writer_bounds,
            }

    async def update(
        self,
        *,
        chat_presence: Optional[List[str]] = None,
        scroll_targets: Optional[List[str]] = None,
        writer_targets: Optional[List[str]] = None,
        chat_presence_interval: Optional[int] = None,
        scroll_bounds: Optional[Tuple[int, int]] = None,
        writer_bounds: Optional[Tuple[int, int]] = None,
    ) -> Tuple[bool, int]:
        changed = False
        async with self._lock:
            if chat_presence is not None and chat_presence != self._chat_presence:
                self._chat_presence = list(chat_presence)
                changed = True
            if scroll_targets is not None and scroll_targets != self._scroll_targets:
                self._scroll_targets = list(scroll_targets)
                changed = True
            if writer_targets is not None and writer_targets != self._writer_targets:
                self._writer_targets = list(writer_targets)
                changed = True
            if (
                chat_presence_interval is not None
                and chat_presence_interval != self._chat_presence_interval
            ):
                self._chat_presence_interval = chat_presence_interval
                changed = True
            if scroll_bounds is not None and scroll_bounds != self._scroll_bounds:
                self._scroll_bounds = scroll_bounds
                changed = True
            if writer_bounds is not None and writer_bounds != self._writer_bounds:
                self._writer_bounds = writer_bounds
                changed = True
            if changed:
                self._version += 1
            version = self._version
        return changed, version


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        norm = item.strip()
        if not norm:
            continue
        key = norm.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return out


def fetch_sheet_column(sheet_id: str, sheet_name: str, column_index: int = 0) -> List[str]:
    if not sheet_id or not sheet_name:
        return []
    try:
        sheet_param = urllib_parse.quote(sheet_name)
        url = (
            f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq"
            f"?tqx=out:csv&sheet={sheet_param}"
        )
        with urllib_request.urlopen(url, timeout=20) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
        reader = csv.reader(io.StringIO(raw))
        values: List[str] = []
        for idx, row in enumerate(reader):
            if not row or column_index >= len(row):
                continue
            cell = (row[column_index] or '').strip()
            if not cell:
                continue
            if idx == 0 and cell.lower() in {'чат', 'channel', 'chat', 'назва', 'name'}:
                continue
            values.append(cell)
        logging.getLogger().debug(
            f"Fetched {len(values)} entries from sheet '{sheet_name}' column {column_index}",
            extra={'phone': '-'}
        )
        return values
    except Exception as exc:
        logging.getLogger().warning(
            f"Не вдалося отримати дані Google Sheet '{sheet_name}': {exc}", extra={'phone': '-'}
        )
        return []


async def refresh_control_lists(
    control_state: ControlState,
    *,
    manual_touch_identifiers: List[str],
    sheet_id: Optional[str],
    sheet_scroll_tab: str,
    sheet_write_tab: str,
    refresh_interval_sec: int = 1800,
) -> None:
    log = logging.getLogger()
    manual_touch_clean = process_control_entries(manual_touch_identifiers, 'Ручні touch-чати')
    while True:
        try:
            if sheet_id:
                sheet_scroll_raw = fetch_sheet_column(sheet_id, sheet_scroll_tab)
                sheet_writer_raw = fetch_sheet_column(sheet_id, sheet_write_tab)
            else:
                sheet_scroll_raw = []
                sheet_writer_raw = []

            scroll_list = process_control_entries(
                sheet_scroll_raw,
                f"Google Sheet '{sheet_scroll_tab}'"
            )
            writer_list = process_control_entries(
                sheet_writer_raw,
                f"Google Sheet '{sheet_write_tab}'"
            )
            presence_list = _dedupe_preserve_order(manual_touch_clean + writer_list)

            changed, version = await control_state.update(
                chat_presence=presence_list,
                scroll_targets=scroll_list,
                writer_targets=writer_list,
            )
            if changed:
                log.info(
                    f"Контрольні списки оновлено (версія {version}): присутність={len(presence_list)}, скрол={len(scroll_list)}, написання={len(writer_list)}",
                    extra={'phone': '-'}
                )
        except Exception as exc:
            log.warning(f'Помилка під час оновлення контрольних списків: {exc}', extra={'phone': '-'})
        await asyncio.sleep(max(60, int(refresh_interval_sec)))


def _parse_version(v: Optional[str]) -> Tuple[int, int, int]:
    try:
        parts = (v or '').split('.')
        return (int(parts[0]), int(parts[1]), int(parts[2] if len(parts) > 2 else 0))
    except Exception:
        return (0, 0, 0)


async def keep_one_account_online(
    root: str,
    phone: str,
    libtdjson: str,
    api_id_override: Optional[int] = None,
    api_hash_override: Optional[str] = None,
    app_version: Optional[str] = None,
    device_model: Optional[str] = None,
    system_version: Optional[str] = None,
    req_jitter_min_ms: int = 120,
    req_jitter_max_ms: int = 300,
    status_interval_sec: int = 300,
    online_ping_sec: int = 30,
    action_interval_sec: int = 15,
    log_pings: bool = False,
    chat_presence_targets: Optional[List[str]] = None,
    chat_presence_interval_sec: int = 60,
    scroll_targets: Optional[List[str]] = None,
    writer_targets: Optional[List[str]] = None,
    scroll_interval_range: Tuple[int, int] = (900, 1800),
    writer_interval_range: Tuple[int, int] = (120, 300),
    control_state: Optional[ControlState] = None,
    auto_open_status_privacy: bool = True,
) -> None:
    """
    Opens existing TDLib database for the account and keeps it online.
    Restarts TDLib on closure. Doesn't attempt re-login.

    Модификации:
    - online_ping_sec по умолчанию ~30 сек
    - action_interval_sec по умолчанию ~15 сек
    - chat_presence_interval_sec по умолчанию ~60 сек
    - sleep внутри активностей теперь async-friendly
    - интервалы пульса рандомизированы
    """
    # Tag logs with current phone for the duration of this coroutine
    token = CURRENT_PHONE.set(phone)
    log = cs.PhoneAdapter(logging.getLogger(), {'phone': phone})
    acc_dir = os.path.join(root, phone)
    td_state_dir = os.path.join(acc_dir, 'tdlib_state')
    if not os.path.isdir(td_state_dir):
        log.error('No tdlib_state found; skip')
        return

    data = cs.read_account_json(acc_dir) or {}
    account_api_id = data.get('api_id') or data.get('app_id')
    account_api_hash = data.get('api_hash') or data.get('app_hash')
    api_id = api_id_override or account_api_id
    api_hash = api_hash_override or account_api_hash
    if not api_id or not api_hash:
        log.error('api_id/api_hash missing; cannot open TDLib DB')
        return
    try:
        src = 'override(embedded/env/cli)' if api_id_override else 'account_json'
        log.info(f'Using api_id={int(api_id)} (source: {src})')
    except Exception:
        pass

    # App/device/system defaults similar to convert_sessions but with per-account signatures
    env_app_ver = os.getenv('APP_VERSION')
    app_ver = app_version or env_app_ver or None
    env_device_model = os.getenv('APP_DEVICE_MODEL')
    env_system_version = os.getenv('APP_SYSTEM_VERSION')
    env_platform = os.getenv('APP_PLATFORM')
    dev_model = device_model or env_device_model or None
    sys_ver = system_version or env_system_version or None

    platform_override = None
    if env_platform:
        env_platform_norm = env_platform.strip().lower()
        if env_platform_norm in _PLATFORM_CONFIGS:
            platform_override = env_platform_norm
        else:
            log.warning(
                f"APP_PLATFORM='{env_platform}' не підтримується; використовую детермінований вибір",
            )
    if not platform_override:
        platform_override = _infer_platform_from_string(dev_model) or _infer_platform_from_string(sys_ver)

    seed_id = phone or data.get('id')
    if not app_ver or not dev_model or not sys_ver:
        gen_dev, gen_sys, gen_app = get_mobile_signature(seed_id, platform_override)
        dev_model = dev_model or gen_dev
        sys_ver = sys_ver or gen_sys
        app_ver = app_ver or gen_app

    # Optional TDLib proxy
    proxy = None
    with suppress(Exception):
        proxy = cs.parse_proxy_field(data.get('proxy'))

    backoff = 2
    last_status_log = 0.0
    last_online_ping = 0.0
    next_online_ping_at = 0.0

    # >>> tuned ping bounds <<<
    # Telegram гасит online быстро, поэтому делаем пульс чаще.
    target_ping = max(20.0, float(online_ping_sec or 0))
    ping_lower = max(10.0, target_ping * 0.5)
    ping_upper = max(ping_lower + 5.0, target_ping * 1.5)
    online_ping_bounds = (ping_lower, ping_upper)

    pending_updates: Deque[Dict] = deque()

    chat_presence_interval = max(30, int(chat_presence_interval_sec or 0))

    def _sanitize_bounds(bounds: Tuple[int, int], minimum: int) -> Tuple[int, int]:
        lo, hi = bounds
        lo = max(minimum, int(lo))
        hi = max(minimum, int(hi))
        if lo > hi:
            lo, hi = hi, lo
        return lo, hi

    scroll_interval_bounds = _sanitize_bounds(scroll_interval_range, 120)
    writer_interval_bounds = _sanitize_bounds(writer_interval_range, 60)

    chat_presence_states: List[Dict[str, Any]] = []
    chat_scroll_states: List[Dict[str, Any]] = []
    chat_writer_states: List[Dict[str, Any]] = []

    supergroup_watch_ids: Set[int] = set()
    supergroup_monitor_task: Optional[asyncio.Task] = None
    active_ping_task: Optional[asyncio.Task] = None
    supergroup_monitor_interval = 60.0
    supergroup_labels: Dict[int, str] = {}

    current_presence_targets: List[str] = list(chat_presence_targets or [])
    current_scroll_targets: List[str] = list(scroll_targets or [])
    current_writer_targets: List[str] = list(writer_targets or [])

    pending_presence_targets: Optional[List[str]] = None
    pending_scroll_targets: Optional[List[str]] = None
    pending_writer_targets: Optional[List[str]] = None

    control_version_seen = -1
    self_user_id: Optional[int] = None
    self_chat_id: Optional[int] = None

    while True:
        td = None
        try:
            # Start TDLib client
            td = cs.TDJsonClient(libtdjson, jitter_min_ms=req_jitter_min_ms, jitter_max_ms=req_jitter_max_ms)

            # Detect TDLib version
            td_version = None
            with suppress(Exception):
                ver = td.execute({'@type': 'getOption', 'name': 'version'})
                if isinstance(ver, dict) and ver.get('@type') == 'optionValueString':
                    td_version = ver.get('value')
                    log.info(f'TDLib runtime version: {td_version}')
            major, minor, _ = _parse_version(td_version)
            use_flat = (major, minor) >= (1, 8)

            files_dir = os.path.join(td_state_dir, 'files')
            os.makedirs(files_dir, exist_ok=True)

            if use_flat:
                params = {
                    '@type': 'setTdlibParameters',
                    'use_test_dc': False,
                    'database_directory': td_state_dir,
                    'files_directory': files_dir,
                    'database_encryption_key': '',
                    'use_file_database': False,
                    'use_chat_info_database': False,
                    'use_message_database': True,
                    'use_secret_chats': False,
                    'api_id': int(api_id),
                    'api_hash': str(api_hash),
                    'system_language_code': 'en',
                    'device_model': dev_model,
                    'system_version': sys_ver,
                    'application_version': app_ver,
                    'enable_storage_optimizer': True,
                }
            else:
                params = {
                    '@type': 'setTdlibParameters',
                    'parameters': {
                        '@type': 'tdlibParameters',
                        'use_test_dc': False,
                        'database_directory': td_state_dir,
                        'files_directory': files_dir,
                        'use_file_database': False,
                        'use_chat_info_database': False,
                        'use_message_database': True,
                        'use_secret_chats': False,
                        'api_id': int(api_id),
                        'api_hash': str(api_hash),
                        'system_language_code': 'en',
                        'device_model': dev_model,
                        'system_version': sys_ver,
                        'application_version': app_ver,
                        'enable_storage_optimizer': True,
                    }
                }

            # Configure proxy if any
            if proxy:
                try:
                    ptype, phost, pport, _rdns, puser, ppass = proxy
                    ptype = (ptype or 'socks5').lower()
                    if ptype.startswith('socks'):
                        proxy_type_obj = {
                            '@type': 'proxyTypeSocks5',
                            'username': puser or '',
                            'password': ppass or '',
                        }
                    elif ptype.startswith('http'):
                        proxy_type_obj = {
                            '@type': 'proxyTypeHttp',
                            'username': puser or '',
                            'password': ppass or '',
                            'http_only': False,
                        }
                    else:
                        proxy_type_obj = None
                    if proxy_type_obj:
                        td.send({
                            '@type': 'addProxy',
                            'server': phost,
                            'port': int(pport),
                            'enable': True,
                            'type': proxy_type_obj,
                        })
                        log.info(f'Configured TDLib proxy {ptype}://{phost}:{pport} (enable=True)')
                except Exception as e:
                    log.warning(f'Failed to configure TDLib proxy: {e}')

            # Start auth state machine
            td.send(params)
            if not use_flat:
                td.send({'@type': 'checkDatabaseEncryptionKey'})
            with suppress(Exception):
                td.send({'@type': 'getAuthorizationState'})

            sent_params = True
            is_ready = False
            last_status_log = 0.0
            last_online_ping = 0.0
            next_online_ping_at = 0.0

            def _next_update(timeout_s: float) -> Optional[Dict]:
                if pending_updates:
                    return pending_updates.popleft()
                return td.receive(timeout_s)

            def _td_call(tag: str, query: Dict, expected: Tuple[str, ...], timeout: float, log_level: int) -> Optional[Dict]:
                req = dict(query)
                extra = f"{phone}:{tag}:{time.time_ns()}"
                req['@extra'] = extra
                td.send(req)
                deadline = time.time() + max(0.1, timeout)
                while time.time() < deadline:
                    # check already queued
                    for _ in range(len(pending_updates)):
                        candidate = pending_updates.popleft()
                        if isinstance(candidate, dict) and candidate.get('@extra') == extra:
                            candidate.pop('@extra', None)
                            return candidate
                        pending_updates.append(candidate)

                    remaining = max(0.05, deadline - time.time())
                    resp = td.receive(min(0.5, remaining))
                    if not resp:
                        continue
                    if isinstance(resp, dict) and resp.get('@extra') == extra:
                        resp.pop('@extra', None)
                        return resp
                    pending_updates.append(resp)

                log.log(log_level, f'{tag}: не дочекався відповіді TDLib протягом {timeout:.1f}s')
                return None

            def _set_online(tag: str) -> bool:
                resp = _td_call(
                    f'{tag}-setOption',
                    {
                        '@type': 'setOption',
                        'name': 'online',
                        'value': {'@type': 'optionValueBoolean', 'value': True},
                    },
                    expected=('ok',),
                    timeout=5.0,
                    log_level=logging.WARNING,
                )
                if not resp:
                    log.warning(f'{tag}: не отримав підтвердження від TDLib для online=true')
                    return False
                rtype = resp.get('@type')
                if rtype == 'ok':
                    log.debug(f'{tag}: setOption online підтверджено TDLib')
                    return True
                if rtype == 'error':
                    log.warning(
                        f"{tag}: setOption online повернув помилку {resp.get('code')} {resp.get('message')}"
                    )
                    return False
                log.warning(f'{tag}: неочікувана відповідь на setOption online -> {resp}')
                return False

            def _ensure_status_privacy_open(tag: str) -> None:
                if not auto_open_status_privacy:
                    log.debug('PRIVACY: автоматичне налаштування вимкнено через --skip-privacy-adjust')
                    return
                resp = _td_call(
                    f'{tag}-privacy-get',
                    {
                        '@type': 'getUserPrivacySettingRules',
                        'setting': {'@type': 'userPrivacySettingStatusTimestamp'},
                    },
                    expected=('userPrivacySettingRules',),
                    timeout=6.0,
                    log_level=logging.INFO,
                )
                need_change = True
                if resp and resp.get('@type') == 'userPrivacySettingRules':
                    rules = resp.get('rules') or []
                    for rule in rules:
                        if isinstance(rule, dict) and rule.get('@type') == 'userPrivacySettingRuleAllowAll':
                            need_change = False
                            break
                    log.info(
                        f"PRIVACY: поточні правила Last seen -> {rules}",
                    )
                if not need_change:
                    return
                log.warning('PRIVACY: відкриваю статус "Останній раз в мережі" для всіх')
                set_resp = _td_call(
                    f'{tag}-privacy-set',
                    {
                        '@type': 'setUserPrivacySettingRules',
                        'setting': {'@type': 'userPrivacySettingStatusTimestamp'},
                        'rules': {
                            '@type': 'userPrivacySettingRules',
                            'rules': [
                                {'@type': 'userPrivacySettingRuleAllowAll'},
                            ],
                        },
                    },
                    expected=('ok',),
                    timeout=8.0,
                    log_level=logging.WARNING,
                )
                if set_resp and set_resp.get('@type') == 'ok':
                    log.info('PRIVACY: статус "Останній раз в мережі" відкрито для всіх користувачів')
                else:
                    log.warning(f'PRIVACY: не вдалося застосувати глобальне правило (відповідь={set_resp})')

            def _log_self_status(tag: str, level: int = logging.INFO) -> Optional[dict]:
                resp = _td_call(
                    f'{tag}-getMe',
                    {'@type': 'getMe'},
                    expected=('user',),
                    timeout=5.0,
                    log_level=level,
                )
                if not resp:
                    return None
                if resp.get('@type') == 'error':
                    log.log(level, f"{tag}: getMe повернув помилку {resp.get('code')} {resp.get('message')}")
                    return None
                status_obj = resp.get('status') or {}
                uid = resp.get('id')
                uname = ' '.join(filter(None, [resp.get('first_name'), resp.get('last_name')]))
                log.log(level, f'{tag}: getMe id={uid} name="{uname.strip()}" status={status_obj}')
                if isinstance(status_obj, dict) and status_obj.get('@type') != 'userStatusOnline':
                    log.warning(
                        f"{tag}: статус не userStatusOnline -> {status_obj}. Telegram може не сприймати присутність."
                    )
                return status_obj if isinstance(status_obj, dict) else None

            def _resolve_chat_identifier(tag: str, identifier: str) -> Optional[int]:
                ident = (identifier or '').strip()
                if not ident:
                    return None
                if ident.lower().startswith('id:'):
                    ident = ident[3:]
                if re.fullmatch(r'-?\d+', ident or ''):
                    try:
                        return int(ident)
                    except Exception:
                        return None
                username = ident[1:] if ident.startswith('@') else ident
                resp = _td_call(
                    f'{tag}-resolve',
                    {'@type': 'searchPublicChat', 'username': username},
                    expected=('chat',),
                    timeout=15.0,
                    log_level=logging.WARNING,
                )
                if resp and isinstance(resp, dict) and resp.get('@type') == 'chat':
                    chat_id = resp.get('id')
                    if chat_id is not None:
                        log.info(f'{tag}: розпізнано чат @{username} -> chat_id={chat_id}')
                        return chat_id
                log.warning(f'{tag}: не вдалося розпізнати чат "{identifier}"')
                return None

            def _fetch_chat_info(tag: str, chat_id: int) -> Optional[Dict[str, Any]]:
                resp = _td_call(
                    f'{tag}-getChat',
                    {'@type': 'getChat', 'chat_id': chat_id},
                    expected=('chat',),
                    timeout=6.0,
                    log_level=logging.DEBUG,
                )
                if resp and resp.get('@type') == 'chat':
                    return resp
                log.warning(f'{tag}: не вдалося отримати інформацію про chat_id={chat_id}')
                return None

            def _random_interval(bounds: Tuple[int, int]) -> float:
                lo, hi = bounds
                return float(random.randint(lo, hi))

            def _ensure_chat_open(tag: str, state: Dict[str, Any]) -> bool:
                """
                Открывает чат, при необходимости joinChat.
                НЕ await'ит, остаётся sync, потому что общается с TDLib синхронно.
                """
                if state.get('failed'):
                    return False
                if state.get('opened'):
                    return True
                chat_id = state.get('chat_id')
                if chat_id is None:
                    state['failed'] = True
                    return False
                if state.get('needs_join') and not state.get('join_failed'):
                    join_resp = _td_call(
                        f'{tag}-join',
                        {'@type': 'joinChat', 'chat_id': chat_id},
                        expected=('ok',),
                        timeout=8.0,
                        log_level=logging.WARNING,
                    )
                    if not join_resp:
                        log.warning(f'{tag}: joinChat не отримав відповідь')
                        state['join_failed'] = True
                        state['failed'] = True
                        return False
                    rtype = join_resp.get('@type')
                    message = (join_resp.get('message') or '') if isinstance(join_resp, dict) else ''
                    if rtype == 'ok' or 'USER_ALREADY_PARTICIPANT' in message:
                        if rtype == 'ok':
                            log.info(f'{tag}: успішно приєднався до chat_id={chat_id}')
                        elif message:
                            log.debug(f'{tag}: вже був учасником chat_id={chat_id} ({message.strip()})')
                        state['needs_join'] = False
                        state.pop('join_failed', None)
                        state['join_succeeded'] = True
                        state['last_join_time'] = time.time()
                        state['just_joined'] = True
                    else:
                        log.warning(
                            f"{tag}: joinChat повернув помилку {join_resp.get('code')} {message.strip()}"
                        )
                        state['join_failed'] = True
                        state['failed'] = True
                        return False
                resp_open = _td_call(
                    f'{tag}-open',
                    {'@type': 'openChat', 'chat_id': chat_id},
                    expected=('ok',),
                    timeout=5.0,
                    log_level=logging.DEBUG,
                )
                if resp_open and resp_open.get('@type') == 'ok':
                    state['opened'] = True
                    return True
                state['failed'] = True
                log.warning(f'{tag}: не вдалося відкрити chat_id={chat_id}')
                return False

            async def _perform_scroll_action(state: Dict[str, Any]) -> bool:
                """
                скрол/просмотр истории/реакции.
                async теперь, чтобы мы могли await asyncio.sleep и не блокировать event loop.
                """
                chat_id = state.get('chat_id')
                if chat_id is None:
                    return False
                tag = f'SCROLL-{chat_id}'
                if not _ensure_chat_open(tag, state):
                    return False
                if state.pop('just_joined', False):
                    # раньше был time.sleep(1.0)
                    await asyncio.sleep(1.0)

                limit = random.randint(2, 20)
                history = _td_call(
                    f'{tag}-history',
                    {
                        '@type': 'getChatHistory',
                        'chat_id': chat_id,
                        'from_message_id': 0,
                        'offset': 0,
                        'limit': limit,
                        'only_local': False,
                    },
                    expected=('messages',),
                    timeout=12.0,
                    log_level=logging.DEBUG,
                )
                messages = []
                if history and history.get('@type') == 'messages':
                    messages = [m for m in (history.get('messages') or []) if isinstance(m, dict)]
                if not messages:
                    log.debug(f'{tag}: немає повідомлень для скролу')
                    return True

                message_ids = [m.get('id') for m in messages if m.get('id')]
                if message_ids:
                    _td_call(
                        f'{tag}-view',
                        {
                            '@type': 'viewMessages',
                            'chat_id': chat_id,
                            'message_ids': message_ids,
                            'force_read': False,
                            'source': {'@type': 'messageSourceChatHistory'},
                        },
                        expected=('ok',),
                        timeout=8.0,
                        log_level=logging.DEBUG,
                    )

                # Реакции — но не на ВСЕ подряд, чтобы не палиться:
                # случайно возьмём до 2 сообщений из первых 20 и попробуем поставить реакцию.
                if state.get('is_channel'):
                    react_candidates = messages[:20]
                    random.shuffle(react_candidates)
                    react_candidates = react_candidates[:2]
                    for msg in react_candidates:
                        mid = msg.get('id')
                        if not mid:
                            continue
                        emoji = random.choice(REACTION_EMOJIS)
                        resp_react = _td_call(
                            f'{tag}-react-{mid}',
                            {
                                '@type': 'addMessageReaction',
                                'chat_id': chat_id,
                                'message_id': mid,
                                'reaction': {'@type': 'reactionTypeEmoji', 'emoji': emoji},
                                'is_big': False,
                            },
                            expected=('ok',),
                            timeout=6.0,
                            log_level=logging.DEBUG,
                        )
                        if not resp_react or resp_react.get('@type') != 'ok':
                            if isinstance(resp_react, dict) and resp_react.get('@type') == 'error':
                                log.warning(
                                    f"{tag}: реакція {emoji} відхилена ({resp_react.get('code')} {resp_react.get('message')})"
                                )
                            else:
                                log.debug(
                                    f'{tag}: не вдалося поставити реакцію {emoji} на повідомлення {mid}'
                                )

                suffix = ' і реакції додано (рандомно)' if state.get('is_channel') else ''
                log.info(f'{tag}: проглянуто {len(messages)} повідомлень{suffix}')
                return True

            async def _perform_writer_action(state: Dict[str, Any]) -> bool:
                """
                Имитируем "печатает", "записывает войс", "загружает фото" и т.д.
                async теперь, опять же чтобы не блочить event loop.
                """
                chat_id = state.get('chat_id')
                if chat_id is None or state.get('is_channel'):
                    return False
                tag = f'WRITE-{chat_id}'
                if state.get('write_restricted'):
                    return False
                if not _ensure_chat_open(tag, state):
                    return False
                if state.pop('just_joined', False):
                    await asyncio.sleep(1.0)

                action_type = random.choice(
                    [
                        'chatActionTyping',
                        'chatActionRecordingVideo',
                        'chatActionRecordingVoiceNote',
                        'chatActionUploadingPhoto',
                        'chatActionUploadingDocument',
                        'chatActionChoosingSticker',
                    ]
                )
                resp_act = _td_call(
                    f'{tag}-action',
                    {
                        '@type': 'sendChatAction',
                        'chat_id': chat_id,
                        'action': {'@type': action_type},
                    },
                    expected=('ok',),
                    timeout=6.0,
                    log_level=logging.DEBUG,
                )
                if not resp_act or resp_act.get('@type') != 'ok':
                    code = resp_act.get('code') if isinstance(resp_act, dict) else None
                    message = ''
                    if isinstance(resp_act, dict):
                        message = (resp_act.get('message') or '').strip()
                    if code == 403 or (message and 'FORBIDDEN' in message.upper()):
                        state['write_restricted'] = True
                        state['failed'] = True
                        log.warning(
                            f'{tag}: немає прав для {action_type} (code={code}, message="{message}"); вимикаю сценарій написання'
                        )
                    else:
                        log.debug(f'{tag}: не вдалось надіслати {action_type} ({message or code})')
                    return False

                # Иногда подглядываем историю чата, чтобы выглядеть "живым"
                if random.random() < 0.4:
                    limit = random.randint(1, 5)
                    _td_call(
                        f'{tag}-peek',
                        {
                            '@type': 'getChatHistory',
                            'chat_id': chat_id,
                            'from_message_id': 0,
                            'offset': 0,
                            'limit': limit,
                            'only_local': False,
                        },
                        expected=('messages',),
                        timeout=8.0,
                        log_level=logging.DEBUG,
                    )
                log.info(f'{tag}: імітовано активність {action_type}')
                return True

            async def _supergroup_monitor() -> None:
                while True:
                    try:
                        await asyncio.sleep(supergroup_monitor_interval)
                        if not is_ready:
                            continue
                        ids_snapshot = [sg for sg in list(supergroup_watch_ids) if sg is not None]
                        if not ids_snapshot:
                            continue
                        for supergroup_id in ids_snapshot:
                            resp = _td_call(
                                f'SUP-info-{supergroup_id}',
                                {
                                    '@type': 'getSupergroupFullInfo',
                                    'supergroup_id': supergroup_id,
                                },
                                expected=('supergroupFullInfo',),
                                timeout=8.0,
                                log_level=logging.DEBUG,
                            )
                            if not resp or resp.get('@type') != 'supergroupFullInfo':
                                continue
                            try:
                                online_count = resp.get('online_member_count')
                            except Exception:
                                online_count = None
                            member_count = resp.get('member_count') if isinstance(resp, dict) else None
                            can_get_members = resp.get('can_get_members') if isinstance(resp, dict) else None
                            can_get_statistics = resp.get('can_get_statistics') if isinstance(resp, dict) else None
                            is_slow_mode = resp.get('is_slow_mode_enabled') if isinstance(resp, dict) else None
                            label = supergroup_labels.get(supergroup_id) or str(supergroup_id)
                            log.info(
                                f'SUPMON: supergroup_id={supergroup_id} ({label}) online_member_count={online_count} member_count={member_count} can_get_members={can_get_members} can_get_statistics={can_get_statistics} slow_mode={is_slow_mode}'
                            )
                    except asyncio.CancelledError:
                        break
                    except Exception as monitor_exc:
                        log.debug(f'SUPMON: помилка моніторингу суперґруп: {monitor_exc!r}')

            def _apply_activity_targets(
                targets_presence: List[str],
                targets_scroll: List[str],
                targets_writer: List[str],
                reason: str,
            ) -> None:
                nonlocal chat_presence_states, chat_scroll_states, chat_writer_states, current_presence_targets, current_scroll_targets, current_writer_targets, supergroup_watch_ids, supergroup_labels, supergroup_monitor_task, self_chat_id, chat_presence_interval

                resolve_cache: Dict[str, Optional[int]] = {}
                chat_info_cache: Dict[int, Optional[Dict[str, Any]]] = {}
                member_statuses = {
                    'chatMemberStatusCreator',
                    'chatMemberStatusAdministrator',
                    'chatMemberStatusMember',
                    'chatMemberStatusRestricted',
                }

                supergroup_ids_local: Set[int] = set()
                labels_local: Dict[int, str] = {}

                def _resolve(tag: str, identifier: str) -> Optional[int]:
                    if identifier in resolve_cache:
                        return resolve_cache[identifier]
                    chat_id_local = _resolve_chat_identifier(tag, identifier)
                    resolve_cache[identifier] = chat_id_local
                    return chat_id_local

                def _get_chat_info(tag: str, chat_id_local: int) -> Optional[Dict[str, Any]]:
                    if chat_id_local in chat_info_cache:
                        return chat_info_cache[chat_id_local]
                    info = _fetch_chat_info(tag, chat_id_local)
                    chat_info_cache[chat_id_local] = info
                    return info

                chat_presence_states.clear()
                chat_scroll_states.clear()
                chat_writer_states.clear()

                current_presence_targets = list(targets_presence)
                current_scroll_targets = list(targets_scroll)
                current_writer_targets = list(targets_writer)

                now_ready = time.time()

                # Presence targets
                for ident in current_presence_targets:
                    chat_id_local = _resolve('CHAT', ident)
                    info = _get_chat_info('CHAT', chat_id_local) if chat_id_local is not None else None
                    chat_type_obj = info.get('type') if isinstance(info, dict) else None
                    chat_type = chat_type_obj.get('@type') if isinstance(chat_type_obj, dict) else None
                    is_channel = bool(chat_type_obj.get('is_channel')) if isinstance(chat_type_obj, dict) and chat_type == 'chatTypeSupergroup' else False
                    supergroup_id = None
                    if isinstance(chat_type_obj, dict) and chat_type == 'chatTypeSupergroup':
                        supergroup_id = chat_type_obj.get('supergroup_id')
                    status_obj = info.get('status') if isinstance(info, dict) else None
                    status_type = status_obj.get('@type') if isinstance(status_obj, dict) else None
                    needs_join = False
                    if chat_type in {'chatTypeSupergroup', 'chatTypeBasicGroup'} and status_type not in member_statuses:
                        needs_join = True
                    state = {
                        'identifier': ident,
                        'chat_id': chat_id_local,
                        'last_touch': now_ready,
                        'opened': False,
                        'failed': chat_id_local is None,
                        'is_channel': is_channel,
                        'needs_join': needs_join,
                        'chat_type': chat_type,
                        'status_type': status_type,
                        'just_joined': False,
                        'supergroup_id': supergroup_id,
                    }
                    chat_presence_states.append(state)
                    if supergroup_id:
                        supergroup_ids_local.add(int(supergroup_id))
                        labels_local[int(supergroup_id)] = ident
                    if is_channel:
                        log.warning(
                            f'CHAT: "{ident}" є каналом (broadcast). Telegram не показує онлайн-лічильник для каналів.'
                        )
                    elif chat_type == 'chatTypeSupergroup' and not needs_join and state.get('chat_id') is not None:
                        log.debug(
                            f'CHAT: "{ident}" тип={chat_type} supergroup_id={supergroup_id} is_channel={is_channel}'
                        )

                # Scroll targets
                for ident in current_scroll_targets:
                    chat_id_local = _resolve('SCROLL', ident)
                    info = None
                    is_channel = False
                    chat_type = None
                    status_type = None
                    needs_join = False
                    supergroup_id = None
                    if chat_id_local is not None:
                        info = _get_chat_info('SCROLL', chat_id_local)
                        chat_type_obj = info.get('type') if isinstance(info, dict) else None
                        if isinstance(chat_type_obj, dict):
                            chat_type = chat_type_obj.get('@type')
                            if chat_type == 'chatTypeSupergroup':
                                is_channel = bool(chat_type_obj.get('is_channel'))
                                supergroup_id = chat_type_obj.get('supergroup_id')
                        status_obj = info.get('status') if isinstance(info, dict) else None
                        if isinstance(status_obj, dict):
                            status_type = status_obj.get('@type')
                        if chat_type in {'chatTypeSupergroup', 'chatTypeBasicGroup'} and status_type not in member_statuses:
                            needs_join = True
                    state = {
                        'identifier': ident,
                        'chat_id': chat_id_local,
                        'last_action': now_ready,
                        'opened': False,
                        'failed': chat_id_local is None,
                        'is_channel': is_channel,
                        'next_interval': _random_interval(scroll_interval_bounds),
                        'needs_join': needs_join,
                        'chat_type': chat_type,
                        'status_type': status_type,
                        'just_joined': False,
                        'supergroup_id': supergroup_id,
                    }
                    chat_scroll_states.append(state)
                    if supergroup_id:
                        supergroup_ids_local.add(int(supergroup_id))
                        labels_local[int(supergroup_id)] = ident

                # Writer targets
                for ident in current_writer_targets:
                    chat_id_local = _resolve('WRITE', ident)
                    info = None
                    is_channel = False
                    chat_type = None
                    status_type = None
                    needs_join = False
                    supergroup_id = None
                    if chat_id_local is not None:
                        info = _get_chat_info('WRITE', chat_id_local)
                        chat_type_obj = info.get('type') if isinstance(info, dict) else None
                        if isinstance(chat_type_obj, dict):
                            chat_type = chat_type_obj.get('@type')
                            if chat_type == 'chatTypeSupergroup':
                                is_channel = bool(chat_type_obj.get('is_channel'))
                                supergroup_id = chat_type_obj.get('supergroup_id')
                        status_obj = info.get('status') if isinstance(info, dict) else None
                        if isinstance(status_obj, dict):
                            status_type = status_obj.get('@type')
                        if chat_type in {'chatTypeSupergroup', 'chatTypeBasicGroup'} and status_type not in member_statuses:
                            needs_join = True
                    state = {
                        'identifier': ident,
                        'chat_id': chat_id_local,
                        'last_action': now_ready,
                        'opened': False,
                        'failed': chat_id_local is None,
                        'is_channel': is_channel,
                        'next_interval': _random_interval(writer_interval_bounds),
                        'needs_join': needs_join,
                        'chat_type': chat_type,
                        'status_type': status_type,
                        'write_restricted': False,
                        'just_joined': False,
                        'supergroup_id': supergroup_id,
                    }
                    chat_writer_states.append(state)
                    if supergroup_id:
                        supergroup_ids_local.add(int(supergroup_id))
                        labels_local[int(supergroup_id)] = ident

                supergroup_watch_ids = {int(sg) for sg in supergroup_ids_local if sg is not None}
                if labels_local:
                    supergroup_labels = {sg: labels_local.get(sg, supergroup_labels.get(sg, str(sg))) for sg in supergroup_watch_ids}
                else:
                    supergroup_labels = {sg: supergroup_labels.get(sg, str(sg)) for sg in supergroup_watch_ids}
                log.info(
                    f"{reason}: оновлено активності (присутність={len(chat_presence_states)}, скрол={len(chat_scroll_states)}, написання={len(chat_writer_states)})"
                )
                if self_chat_id is not None and not any(
                    state.get('chat_id') == self_chat_id for state in chat_presence_states
                ):
                    chat_presence_states.append(
                        {
                            'identifier': 'SavedMessages',
                            'chat_id': self_chat_id,
                            'last_touch': now_ready - max(5.0, float(chat_presence_interval)),
                            'opened': False,
                            'failed': False,
                            'is_channel': False,
                            'needs_join': False,
                            'chat_type': 'chatTypePrivate',
                            'status_type': 'chatMemberStatusMember',
                            'just_joined': False,
                            'supergroup_id': None,
                        }
                    )
                    log.info(
                        'AUTO: додано Saved Messages як fallback для імітації активності',
                    )
                if supergroup_watch_ids and (
                    supergroup_monitor_task is None or supergroup_monitor_task.done()
                ):
                    supergroup_monitor_task = asyncio.create_task(_supergroup_monitor())

            while True:
                upd = _next_update(2.0)
                now = time.time()

                # обновление control_state (Google Sheet и т.д.)
                if control_state and control_state.version != control_version_seen:
                    snapshot = await control_state.snapshot()
                    control_version_seen = snapshot.get('version', control_version_seen)
                    pending_presence_targets = snapshot.get('chat_presence', [])
                    pending_scroll_targets = snapshot.get('scroll_targets', [])
                    pending_writer_targets = snapshot.get('writer_targets', [])
                    chat_presence_interval = max(
                        30,
                        int(snapshot.get('chat_presence_interval', chat_presence_interval) or 0),
                    )
                    scroll_bounds_snapshot = snapshot.get('scroll_bounds') or scroll_interval_bounds
                    writer_bounds_snapshot = snapshot.get('writer_bounds') or writer_interval_bounds
                    scroll_interval_bounds = _sanitize_bounds(tuple(scroll_bounds_snapshot), 120)
                    writer_interval_bounds = _sanitize_bounds(tuple(writer_bounds_snapshot), 60)
                    log.info(f'CONTROL: отримано нову версію списків ({control_version_seen})')
                    if is_ready:
                        _apply_activity_targets(
                            pending_presence_targets,
                            pending_scroll_targets,
                            pending_writer_targets,
                            reason=f'CONTROL v{control_version_seen}',
                        )
                        pending_presence_targets = None
                        pending_scroll_targets = None
                        pending_writer_targets = None

                if upd:
                    t = upd.get('@type') if isinstance(upd, dict) else None
                    if t == 'updateAuthorizationState':
                        st = (upd.get('authorization_state') or {}).get('@type')
                        logging.getLogger().debug(f"[keep] Auth state: {st}", extra={'phone': phone})
                        if st == 'authorizationStateWaitTdlibParameters':
                            if not locals().get('sent_params'):
                                td.send(params)
                                if not use_flat:
                                    with suppress(Exception):
                                        td.send({'@type': 'checkDatabaseEncryptionKey'})
                            continue
                        if st == 'authorizationStateWaitEncryptionKey':
                            with suppress(Exception):
                                td.send({'@type': 'checkDatabaseEncryptionKey'})
                            continue
                        if st == 'authorizationStateWaitPhoneNumber':
                            log.warning('Requires phone re-login; skipping (keep-online doesn\'t login)')
                            await asyncio.sleep(10)
                            break
                        if st == 'authorizationStateWaitCode':
                            log.warning('Requires code; skipping (keep-online doesn\'t submit codes)')
                            await asyncio.sleep(10)
                            break
                        if st == 'authorizationStateWaitPassword':
                            log.warning('Requires 2FA password; skipping (keep-online cannot unlock)')
                            await asyncio.sleep(10)
                            break
                        if st == 'authorizationStateReady':
                            if not is_ready:
                                is_ready = True
                                # Пытаемся выставить online сразу
                                if not _set_online('READY'):
                                    log.warning('READY: не вдалося встановити online=true; повторю спроби у пінгах')
                                _ensure_status_privacy_open('READY')
                                me_info = _td_call(
                                    'READY-me',
                                    {'@type': 'getMe'},
                                    expected=('user',),
                                    timeout=5.0,
                                    log_level=logging.INFO,
                                )
                                if isinstance(me_info, dict) and me_info.get('@type') == 'user':
                                    try:
                                        self_user_id = int(me_info.get('id'))
                                    except Exception:
                                        self_user_id = me_info.get('id')
                                if self_user_id is not None:
                                    saved_resp = _td_call(
                                        'READY-selfChat',
                                        {
                                            '@type': 'createPrivateChat',
                                            'user_id': int(self_user_id),
                                            'force': True,
                                        },
                                        expected=('chat',),
                                        timeout=6.0,
                                        log_level=logging.INFO,
                                    )
                                    if isinstance(saved_resp, dict) and saved_resp.get('@type') == 'chat':
                                        new_chat_id = saved_resp.get('id')
                                        if new_chat_id is not None:
                                            if self_chat_id != new_chat_id:
                                                log.info(f'Визначено Saved Messages chat_id={new_chat_id}')
                                            self_chat_id = new_chat_id
                                _log_self_status('READY')
                                # active ping loop (presence heartbeat)
                                if active_ping_task is None or active_ping_task.done():
                                    async def _active_ping_loop():
                                        while True:
                                            try:
                                                # рандомный дрейф вокруг action_interval_sec
                                                base = max(5, int(action_interval_sec))
                                                drift_low = base * 0.7
                                                drift_high = base * 1.3
                                                await asyncio.sleep(random.uniform(drift_low, drift_high))
                                                if not is_ready:
                                                    continue
                                                # reaffirm online
                                                if not _set_online('ACTIVE'):
                                                    log.warning('ACTIVE: setOption online failed')
                                                # send a lightweight chat action to Saved Messages as presence pulse
                                                if self_chat_id is not None:
                                                    act = _td_call(
                                                        'ACTIVE-action',
                                                        {
                                                            '@type': 'sendChatAction',
                                                            'chat_id': int(self_chat_id),
                                                            'action': {'@type': 'chatActionTyping'},
                                                        },
                                                        expected=('ok',),
                                                        timeout=6.0,
                                                        log_level=logging.DEBUG,
                                                    )
                                                    if act and act.get('@type') == 'ok':
                                                        log.debug('ACTIVE: sendChatAction to Saved Messages OK')
                                                    else:
                                                        log.debug(f'ACTIVE: sendChatAction response={act}')
                                            except asyncio.CancelledError:
                                                break
                                            except Exception as e:
                                                log.debug(f'ACTIVE: exception in ping loop: {e!r}')
                                    active_ping_task = asyncio.create_task(_active_ping_loop())

                                targets_presence = (
                                    pending_presence_targets
                                    if pending_presence_targets is not None
                                    else current_presence_targets
                                )
                                targets_scroll = (
                                    pending_scroll_targets
                                    if pending_scroll_targets is not None
                                    else current_scroll_targets
                                )
                                targets_writer = (
                                    pending_writer_targets
                                    if pending_writer_targets is not None
                                    else current_writer_targets
                                )
                                _apply_activity_targets(
                                    targets_presence,
                                    targets_scroll,
                                    targets_writer,
                                    reason='READY',
                                )
                                pending_presence_targets = None
                                pending_scroll_targets = None
                                pending_writer_targets = None
                                next_online_ping_at = now + random.uniform(*online_ping_bounds)
                    elif t == 'connectionState':
                        # optional connection state updates
                        pass
                    elif t == 'error':
                        msg = upd.get('message')
                        log.warning(f'TDLib error: {msg}')
                    elif t == 'user':
                        # getMe response; ignore
                        pass
                    # else: ignore other updates

                # Periodic status log
                if now - last_status_log > max(60, status_interval_sec):
                    last_status_log = now
                    if is_ready:
                        log.info('Heartbeat: READY and online')
                    else:
                        log.info('Heartbeat: not READY yet')

                # Periodic presence ping (online reaffirm)
                if is_ready and (next_online_ping_at <= 0.0 or now >= next_online_ping_at):
                    last_online_ping = now
                    if not _set_online('PING'):
                        log.warning('PING: не вдалося підтвердити online=true цього разу')
                    ping_level = logging.INFO if log_pings else logging.DEBUG
                    _log_self_status('PING', level=ping_level)
                    with suppress(Exception):
                        td.send({'@type': 'getChats', 'limit': 1})
                    next_online_ping_at = now + random.uniform(*online_ping_bounds)

                # Presence targets activity (typing+peek)
                if is_ready and chat_presence_states:
                    for state in chat_presence_states:
                        if state.get('failed'):
                            continue
                        chat_id_local = state.get('chat_id')
                        if chat_id_local is None:
                            state['failed'] = True
                            continue
                        if now - state.get('last_touch', 0.0) < chat_presence_interval:
                            continue
                        if not _ensure_chat_open(f'CHAT-{chat_id_local}', state):
                            continue
                        if state.pop('just_joined', False):
                            # раньше было time.sleep(1.0)
                            await asyncio.sleep(1.0)
                        resp_act = _td_call(
                            f'CHAT-action-{chat_id_local}',
                            {
                                '@type': 'sendChatAction',
                                'chat_id': chat_id_local,
                                'action': {'@type': 'chatActionTyping'},
                            },
                            expected=('ok',),
                            timeout=5.0,
                            log_level=logging.DEBUG,
                        )
                        if not resp_act or resp_act.get('@type') != 'ok':
                            state['failed'] = True
                            log.warning(
                                f'CHAT: chat_id={chat_id_local} не прийняв chatActionTyping; зупиняю активність для цього чату'
                            )
                            continue
                        history_limit = random.randint(1, 4)
                        history = _td_call(
                            f'CHAT-peek-{chat_id_local}',
                            {
                                '@type': 'getChatHistory',
                                'chat_id': chat_id_local,
                                'from_message_id': 0,
                                'offset': 0,
                                'limit': history_limit,
                                'only_local': False,
                            },
                            expected=('messages',),
                            timeout=8.0,
                            log_level=logging.DEBUG,
                        )
                        messages = []
                        if history and history.get('@type') == 'messages':
                            messages = [m for m in (history.get('messages') or []) if isinstance(m, dict)]
                        message_ids = [m.get('id') for m in messages if m and m.get('id')]
                        if message_ids:
                            _td_call(
                                f'CHAT-view-{chat_id_local}',
                                {
                                    '@type': 'viewMessages',
                                    'chat_id': chat_id_local,
                                    'message_ids': message_ids,
                                    'force_read': False,
                                    'source': {'@type': 'messageSourceChatHistory'},
                                },
                                expected=('ok',),
                                timeout=6.0,
                                log_level=logging.DEBUG,
                            )
                        state['last_touch'] = now
                        log.debug(f'CHAT: chat_id={chat_id_local} позначено активністю (typing)')
                    # end for

                # Scheduled scroll/reaction activity
                if is_ready and chat_scroll_states:
                    for state in chat_scroll_states:
                        if state.get('failed'):
                            continue
                        next_interval = state.get('next_interval')
                        if next_interval is None:
                            next_interval = _random_interval(scroll_interval_bounds)
                            state['next_interval'] = next_interval
                        if now - state.get('last_action', 0.0) < next_interval:
                            continue
                        success = await _perform_scroll_action(state)
                        state['last_action'] = now
                        state['next_interval'] = _random_interval(scroll_interval_bounds)
                        if not success:
                            state['failed'] = True
                        break  # обрабатываем только один чат за тик, чтобы не спамить

                # Scheduled writer/typing activity
                if is_ready and chat_writer_states:
                    for state in chat_writer_states:
                        if state.get('failed'):
                            continue
                        next_interval = state.get('next_interval')
                        if next_interval is None:
                            next_interval = _random_interval(writer_interval_bounds)
                            state['next_interval'] = next_interval
                        if now - state.get('last_action', 0.0) < next_interval:
                            continue
                        success = await _perform_writer_action(state)
                        state['last_action'] = now
                        state['next_interval'] = _random_interval(writer_interval_bounds)
                        if not success:
                            state['failed'] = True
                        break  # тоже не спамим

                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            log.info('Shutting down keep-online task')
            break
        except Exception as e:
            log.error(f'Keep-online loop crashed: {e}')
        finally:
            if supergroup_monitor_task:
                try:
                    if not supergroup_monitor_task.done():
                        supergroup_monitor_task.cancel()
                        with suppress(Exception):
                            await supergroup_monitor_task
                finally:
                    supergroup_monitor_task = None
            if active_ping_task:
                try:
                    if not active_ping_task.done():
                        active_ping_task.cancel()
                        with suppress(Exception):
                            await active_ping_task
                finally:
                    active_ping_task = None
            supergroup_watch_ids.clear()
            supergroup_labels.clear()
            next_online_ping_at = 0.0
            with suppress(Exception):
                CURRENT_PHONE.reset(token)
            pass

        # If we reached here, TDLib likely closed or we decided to skip; backoff and retry
        with suppress(Exception):
            await asyncio.sleep(min(60, max(2, backoff)))
        backoff = min(60, max(2, backoff * 2))
        log.info(f'Restarting keep-online (backoff={backoff}s)')


def _get_total_memory_bytes() -> Optional[int]:
    """Повертає обсяг оперативної пам'яті системи в байтах."""
    try:
        if sys.platform == 'darwin':
            return int(subprocess.check_output(['sysctl', '-n', 'hw.memsize']).strip())
        if sys.platform.startswith('linux'):
            with open('/proc/meminfo', 'r') as f:
                info = f.read()
            m_total = re.search(r'^MemTotal:\s+(\d+)', info, re.M)
            if m_total:
                return int(m_total.group(1)) * 1024
        if sys.platform.startswith('win'):
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                return int(stat.ullTotalPhys)
    except Exception:
        return None
    return None


def get_process_memory_usage() -> Optional[Tuple[float, Optional[float]]]:
    """Повертає (RSS у МБ, відсоток від загальної пам'яті) для процесу."""
    rss_bytes: Optional[int] = None
    percent: Optional[float] = None

    try:
        import psutil  # type: ignore[import]
        proc = psutil.Process(os.getpid())
        info = proc.memory_info()
        rss_bytes = int(info.rss)
        percent = round(proc.memory_percent(), 2)
    except Exception:
        rss_bytes = None
        percent = None

    if rss_bytes is None:
        try:
            out = subprocess.check_output(['ps', '-o', 'rss=', '-p', str(os.getpid())])
            rss_kb = int(out.strip())
            rss_bytes = rss_kb * 1024
        except Exception:
            pass

    if rss_bytes is None:
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            rss_val = int(getattr(usage, 'ru_maxrss', 0))
            if sys.platform == 'darwin':
                rss_bytes = rss_val
            else:
                rss_bytes = rss_val * 1024
        except Exception:
            pass

    if rss_bytes is None:
        return None

    if percent is None:
        total = _get_total_memory_bytes()
        if total and total > 0:
            percent = round((rss_bytes / total) * 100.0, 2)

    rss_mb = rss_bytes / (1024 * 1024)
    return rss_mb, percent


async def memory_monitor(interval_sec: int = 300):
    """Фонове логування використання пам'яті самим скриптом."""
    log = logging.getLogger()
    while True:
        try:
            usage = get_process_memory_usage()
            if usage is None:
                log.info('Використання пам\'яті процесом: невідомо', extra={'phone': '-'})
            else:
                rss_mb, percent = usage
                if percent is None:
                    log.info(f'Використання пам\'яті процесом: {rss_mb:.1f} МБ', extra={'phone': '-'})
                else:
                    log.info(
                        f"Використання пам'яті процесом: {rss_mb:.1f} МБ ({percent:.2f}%)",
                        extra={'phone': '-'}
                    )
        except Exception as e:
            log.warning(f'Не вдалося отримати дані про пам\'ять: {e}', extra={'phone': '-'})
        await asyncio.sleep(interval_sec)


def find_libtdjson() -> Optional[str]:
    candidates = []
    # Homebrew on Apple Silicon
    candidates += glob.glob('/opt/homebrew/Cellar/tdlib/*/lib/libtdjson*.dylib')
    # Homebrew on Intel
    candidates += glob.glob('/usr/local/Cellar/tdlib/*/lib/libtdjson*.dylib')
    # Common lib locations
    candidates += glob.glob('/opt/homebrew/lib/libtdjson*.dylib')
    candidates += glob.glob('/usr/local/lib/libtdjson*.dylib')
    candidates += glob.glob('/usr/lib/libtdjson*.so')
    candidates += glob.glob('/usr/local/lib/libtdjson*.so')
    seen = set()
    out = []
    for p in candidates:
        if p and p not in seen and os.path.exists(p):
            seen.add(p)
            out.append(p)
    return out[0] if out else None


async def main_cli():
    parser = argparse.ArgumentParser(description='Keep TDLib accounts online (presence daemon, strong online mode)')
    parser.add_argument('--root', default=DEFAULT_ROOT)
    parser.add_argument('--libtdjson', required=False)
    parser.add_argument('--single')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--concurrency', type=int, default=100)

    # NEW: stagger real usage
    parser.add_argument('--stagger-max', type=int, default=3,
                        help='Макс рандом пауза (сек) перед стартом кожного акаунта, щоб не було шквалу запросів')

    parser.add_argument('--status-interval', type=int, default=300)

    # tightened defaults
    parser.add_argument('--ping-interval', type=int, default=30,
                        help='Seconds between periodic online pings (setOption online + status check)')
    parser.add_argument('--action-interval', type=int, default=15,
                        help='Базовий інтервал (сек) між активними presence-імпульсами в Saved Messages. Буде рандомізовано ±30%.')

    # API overrides (used only to open the DB, not for login)
    parser.add_argument('--api-id', type=int)
    parser.add_argument('--api-hash', type=str)
    parser.add_argument('--app-version', type=str)
    parser.add_argument('--device-model', type=str)
    parser.add_argument('--system-version', type=str)

    # Per-request jitter to avoid burstiness
    parser.add_argument('--req-jitter-min-ms', type=int, default=120)
    parser.add_argument('--req-jitter-max-ms', type=int, default=300)
    parser.add_argument('--verbose', action='store_true', default=True)
    parser.add_argument('--log-pings', action='store_true', help='Log each presence ping on INFO')

    # Presence tuning defaults are more aggressive now
    parser.add_argument('--touch-chat', dest='touch_chats', action='append', default=[], help='Chat identifier to keep active (can be repeated)')
    parser.add_argument('--touch-chats-file', type=str, help='File with chat identifiers (one per line) to keep active')
    parser.add_argument('--chat-presence-interval', type=int, default=60,
                        help='Seconds between activity pulses in target chats (typing/peek). (Раніше було 180)')

    # Google Sheet control
    parser.add_argument('--sheet-id', type=str, default=os.getenv('KEEPONLINE_SHEET_ID', DEFAULT_CONTROL_SHEET_ID), help='Google Sheet ID with control lists')
    parser.add_argument('--sheet-scroll-tab', type=str, default='Вступити-Скролити', help='Sheet tab containing channels for scrolling/reactions')
    parser.add_argument('--sheet-write-tab', type=str, default='Писати', help='Sheet tab containing chats for typing simulation')
    parser.add_argument('--sheet-disable', action='store_true', help='Disable Google Sheet integration even if sheet ID is set')

    parser.add_argument('--scroll-interval-min', type=int, default=900, help='Minimum seconds between scroll batches per chat')
    parser.add_argument('--scroll-interval-max', type=int, default=1800, help='Maximum seconds between scroll batches per chat')
    parser.add_argument('--writer-interval-min', type=int, default=120, help='Minimum seconds between writing simulations per chat')
    parser.add_argument('--writer-interval-max', type=int, default=300, help='Maximum seconds between writing simulations per chat')

    parser.add_argument('--skip-privacy-adjust', action='store_true', help='Не змінювати налаштування "Last seen" автоматично (інакше ми відкриваємо last seen для всіх)')

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load chat targets from CLI and file
    touch_chat_identifiers_raw: List[str] = []
    for ident in args.touch_chats or []:
        if ident:
            touch_chat_identifiers_raw.append(ident.strip())
    if args.touch_chats_file:
        try:
            with open(args.touch_chats_file, 'r', encoding='utf-8') as fh:
                for line in fh:
                    ident = line.strip()
                    if ident and not ident.startswith('#'):
                        touch_chat_identifiers_raw.append(ident)
        except Exception as e:
            logging.getLogger().warning(
                f'Не вдалося прочитати touch-чати з файлу {args.touch_chats_file}: {e}', extra={'phone': '-'}
            )
    touch_chat_identifiers = _dedupe_preserve_order(
        process_control_entries(touch_chat_identifiers_raw, 'CLI touch-чати')
    )

    # From google sheet (optional)
    sheet_scroll_identifiers: List[str] = []
    sheet_writer_identifiers: List[str] = []
    sheet_id = (args.sheet_id or '').strip()
    if not args.sheet_disable and sheet_id:
        sheet_scroll_identifiers = fetch_sheet_column(sheet_id, args.sheet_scroll_tab)
        sheet_writer_identifiers = fetch_sheet_column(sheet_id, args.sheet_write_tab)
        if sheet_scroll_identifiers:
            logging.getLogger().info(
                f"З аркуша '{args.sheet_scroll_tab}' завантажено {len(sheet_scroll_identifiers)} чатів для скролу",
                extra={'phone': '-'}
            )
        if sheet_writer_identifiers:
            logging.getLogger().info(
                f"З аркуша '{args.sheet_write_tab}' завантажено {len(sheet_writer_identifiers)} чатів для написання",
                extra={'phone': '-'}
            )
    elif args.sheet_disable:
        logging.getLogger().info('Інтеграцію з Google Sheet вимкнено', extra={'phone': '-'})

    scroll_chat_identifiers = _dedupe_preserve_order(sheet_scroll_identifiers)
    writer_chat_identifiers = _dedupe_preserve_order(sheet_writer_identifiers)
    chat_presence_identifiers = _dedupe_preserve_order(touch_chat_identifiers + writer_chat_identifiers)

    logging.getLogger().info(
        f'Чатів для присутності: {len(chat_presence_identifiers)}, для скролу: {len(scroll_chat_identifiers)}, для написання: {len(writer_chat_identifiers)}',
        extra={'phone': '-'}
    )

    def _normalize_interval(min_v: int, max_v: int, floor: int) -> Tuple[int, int]:
        a = max(floor, int(min_v))
        b = max(floor, int(max_v))
        if a > b:
            a, b = b, a
        return a, b

    presence_interval_value = max(30, int(args.chat_presence_interval))
    scroll_interval_bounds = _normalize_interval(args.scroll_interval_min, args.scroll_interval_max, 120)
    writer_interval_bounds = _normalize_interval(args.writer_interval_min, args.writer_interval_max, 60)

    control_state = ControlState(
        chat_presence_interval=presence_interval_value,
        scroll_bounds=scroll_interval_bounds,
        writer_bounds=writer_interval_bounds,
    )
    await control_state.update(
        chat_presence=chat_presence_identifiers,
        scroll_targets=scroll_chat_identifiers,
        writer_targets=writer_chat_identifiers,
        chat_presence_interval=presence_interval_value,
        scroll_bounds=scroll_interval_bounds,
        writer_bounds=writer_interval_bounds,
    )

    sheet_refresh_task: Optional[asyncio.Task] = None
    if not args.sheet_disable and sheet_id:
        sheet_refresh_task = asyncio.create_task(
            refresh_control_lists(
                control_state,
                manual_touch_identifiers=touch_chat_identifiers,
                sheet_id=sheet_id,
                sheet_scroll_tab=args.sheet_scroll_tab,
                sheet_write_tab=args.sheet_write_tab,
                refresh_interval_sec=CONTROL_REFRESH_INTERVAL_SEC,
            )
        )

    # Resolve libtdjson path
    libtdjson_path = args.libtdjson
    if libtdjson_path:
        if not os.path.exists(libtdjson_path):
            fb = find_libtdjson()
            if fb:
                logging.getLogger().warning(
                    f"Provided --libtdjson not found: {libtdjson_path}; falling back to {fb}", extra={'phone': '-'}
                )
                libtdjson_path = fb
            else:
                logging.getLogger().error(
                    f"--libtdjson not found and auto-discovery failed", extra={'phone': '-'}
                )
                sys.exit(2)
    else:
        libtdjson_path = find_libtdjson()
        if libtdjson_path:
            logging.getLogger().info(f'Auto-discovered libtdjson at {libtdjson_path}', extra={'phone': '-'})
        else:
            logging.getLogger().error('libtdjson not provided and auto-discovery failed', extra={'phone': '-'})
            sys.exit(2)

    # Discover accounts: require tdlib_state folder present
    accounts = []
    root = args.root
    for name in sorted(os.listdir(root) if os.path.exists(root) else []):
        p = os.path.join(root, name)
        if os.path.isdir(p) and os.path.isdir(os.path.join(p, 'tdlib_state')):
            accounts.append(name)

    if args.single:
        accounts = [args.single]
    elif not args.all:
        # default: all discovered
        args.all = True

    if not accounts:
        logging.getLogger().warning(
            f"No accounts with tdlib_state under '{root}'.", extra={'phone': '-'}
        )
        return

    sem = asyncio.Semaphore(max(1, int(args.concurrency)))

    async def worker(phone: str):
        # stagger start for realism / load shedding
        stagger_max = max(0, int(getattr(args, 'stagger_max', 0) or 0))
        if stagger_max > 0:
            delay = random.uniform(0, float(stagger_max))
            logging.getLogger().info(
                f"[{phone}] stagger delay {delay:.2f}s before start",
                extra={'phone': phone}
            )
            await asyncio.sleep(delay)

        async with sem:
            await keep_one_account_online(
                root,
                phone,
                libtdjson_path,
                api_id_override=(
                    args.api_id or (
                        int(os.getenv('API_ID')) if os.getenv('API_ID') else DEFAULT_API_ID
                    )
                ),
                api_hash_override=(
                    args.api_hash or os.getenv('API_HASH') or DEFAULT_API_HASH
                ),
                app_version=args.app_version or os.getenv('APP_VERSION') or None,
                device_model=args.device_model or os.getenv('APP_DEVICE_MODEL') or None,
                system_version=args.system_version or os.getenv('APP_SYSTEM_VERSION') or None,
                req_jitter_min_ms=(getattr(args, 'req_jitter_min_ms', 0) or 0),
                req_jitter_max_ms=(getattr(args, 'req_jitter_max_ms', 0) or 0),
                status_interval_sec=max(60, int(args.status_interval)),
                online_ping_sec=max(20, int(args.ping_interval)),
                action_interval_sec=max(5, int(getattr(args, 'action_interval', 15))),
                log_pings=bool(getattr(args, 'log_pings', False)),
                chat_presence_targets=chat_presence_identifiers,
                chat_presence_interval_sec=presence_interval_value,
                scroll_targets=scroll_chat_identifiers,
                writer_targets=writer_chat_identifiers,
                scroll_interval_range=scroll_interval_bounds,
                writer_interval_range=writer_interval_bounds,
                control_state=control_state,
                auto_open_status_privacy=not getattr(args, 'skip_privacy_adjust', False),
            )

    # Start background memory monitor (logs memory usage every status_interval seconds, min 60s)
    monitor_task = asyncio.create_task(memory_monitor(interval_sec=max(60, int(args.status_interval))))

    background_tasks: List[asyncio.Task] = [monitor_task]
    if sheet_refresh_task:
        background_tasks.append(sheet_refresh_task)

    tasks = [asyncio.create_task(worker(phone)) for phone in accounts]
    try:
        await asyncio.gather(*background_tasks, *tasks)
    except KeyboardInterrupt:
        # Graceful shutdown: cancel monitor, sheet refresher and all workers
        for bg in background_tasks:
            bg.cancel()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*background_tasks, *tasks, return_exceptions=True)
    except asyncio.CancelledError:
        for bg in background_tasks:
            bg.cancel()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*background_tasks, *tasks, return_exceptions=True)


if __name__ == '__main__':
    try:
        asyncio.run(main_cli())
    except KeyboardInterrupt:
        print('Interrupted')

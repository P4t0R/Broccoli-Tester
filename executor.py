import asyncio
import json
import re
import os
from datetime import datetime
from typing import Any, Dict, List, Tuple

# Try to import aiohttp; if missing, we'll simulate requests
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except Exception:
    AIOHTTP_AVAILABLE = False

PLACEHOLDER_RE = re.compile(r"\{+([A-Za-z0-9_]+)\}+")


def _extract_keys_from_obj(obj: Any) -> List[str]:
    s = json.dumps(obj) if not isinstance(obj, str) else obj
    return list(set(PLACEHOLDER_RE.findall(s)))


def _replace_placeholders_in_str(s: str, mapping: Dict[str, str]) -> str:
    def repl(m):
        k = m.group(1)
        return mapping.get(k, m.group(0))
    return PLACEHOLDER_RE.sub(repl, s)


def _replace_in_obj(obj: Any, mapping: Dict[str, str]):
    if isinstance(obj, str):
        return _replace_placeholders_in_str(obj, mapping)
    if isinstance(obj, dict):
        return {k: _replace_in_obj(v, mapping) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_replace_in_obj(v, mapping) for v in obj]
    return obj


def _compact(obj, max_len: int):
    try:
        if isinstance(obj, (dict, list)):
            s = json.dumps(obj, ensure_ascii=False)
        else:
            s = str(obj)
    except Exception:
        s = str(obj)
    s = s.replace('\n', '\\n').replace('\r', '\\r')
    if len(s) > max_len:
        return s[:max_len] + '...'
    return s


async def _fetch(session, api_conf: Dict, mapping: Dict[str, str], seq: int | None = None):
    method = api_conf.get('method', 'GET').upper()
    url = _replace_placeholders_in_str(api_conf.get('url', ''), mapping)
    api_name = api_conf.get('name', '<unnamed>')
    # token may be None; coerce to empty string and replace placeholders safely
    token_raw = api_conf.get('token', '')
    if token_raw is None:
        token_raw = ''
    try:
        token = _replace_placeholders_in_str(str(token_raw), mapping)
    except Exception:
        token = ''
    headers = {}
    try:
        headers = _replace_in_obj(api_conf.get('headers', {}) or {}, mapping)
    except Exception:
        headers = api_conf.get('headers', {}) or {}
    # add token if present — prefer Authorization header and ensure Bearer prefix
    if token:
        try:
            tval = str(token).strip()
            # ensure token uses Bearer scheme
            if not tval.lower().startswith('bearer '):
                tval = f'Bearer {tval}'
            # find existing Authorization header case-insensitively
            existing_key = None
            for k in list(headers.keys()):
                if k.lower() == 'authorization':
                    existing_key = k
                    break
            if existing_key:
                # only set if empty
                if not headers.get(existing_key):
                    headers[existing_key] = tval
            else:
                headers['Authorization'] = tval
        except Exception:
            pass

    body_raw = api_conf.get('body_raw')
    body = api_conf.get('body')
    body_to_send = None
    if body_raw:
        body_to_send = _replace_placeholders_in_str(body_raw, mapping)
    elif body:
        body_to_send = _replace_in_obj(body, mapping)

    # compact representations for logging
    try:
        bstr = body_to_send if body_to_send is not None else ''
        bshow_trunc = _compact(bstr, 600)
        headers_trunc = _compact(headers, 400)
        mapping_trunc = _compact(mapping, 300)
    except Exception:
        bshow_trunc = ''
        headers_trunc = ''
        mapping_trunc = ''

    try:
        if AIOHTTP_AVAILABLE:
            async with session.request(method, url, headers=headers, data=body_to_send) as resp:
                text = await resp.text()
                status = resp.status
                # print single-line request+response log with enumeration if provided
                try:
                    prefix = f"[{seq}] " if seq is not None else ''
                    print(f"[executor] {prefix}-> {method} {api_name} {url} | status={status} | headers={headers_trunc} | body={bshow_trunc} | mapping={mapping_trunc}")
                except Exception:
                    pass
                return {'status': status, 'text': text, 'api_name': api_name, 'mapping': mapping, 'seq': seq, 'url_expanded': url, 'headers_sent': headers, 'body_sent': body_to_send, 'method': method}
        else:
            # simulate
            await asyncio.sleep(0.02)
            status = 200
            text = f"SIMULATED: {method} {url} headers={headers} body={body_to_send}"
            try:
                prefix = f"[{seq}] " if seq is not None else ''
                print(f"[executor] {prefix}-> {method} {api_name} {url} | status={status} | headers={headers_trunc} | body={bshow_trunc} | mapping={mapping_trunc}")
            except Exception:
                pass
            return {
                'status': status,
                'text': text,
                'api_name': api_name,
                'mapping': mapping,
                'seq': seq,
                'url_expanded': url,
                'headers_sent': headers,
                'body_sent': body_to_send,
                'method': method,
            }
    except Exception as e:
        return {'status': None, 'text': '', 'error': str(e), 'api_name': api_name, 'mapping': mapping}


async def _run_all(apis: List[Dict], mappings: List[Dict[str, str]]):
    results = []
    if AIOHTTP_AVAILABLE:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, mapping in enumerate(mappings):
                for j, api in enumerate(apis):
                    seq = i * len(apis) + j + 1
                    tasks.append(_fetch(session, api, mapping, seq))
            results = await asyncio.gather(*tasks)
    else:
        tasks = []
        for i, mapping in enumerate(mappings):
            for j, api in enumerate(apis):
                seq = i * len(apis) + j + 1
                tasks.append(_fetch(None, api, mapping, seq))
        results = await asyncio.gather(*tasks)
    return results


def run_apis(apis: List[Dict], dynamic_lists: Dict[str, List[str]]) -> Tuple[List[Dict], str]:
    """
    apis: list of api dicts
    dynamic_lists: dict key -> list of values

    Expands apis for each mapping of dynamic variables and executes them.
    Returns list of results.
    """
    # Build mappings list: a mapping per combination? We want per-api per-value where placeholder used.
    # Simpler: produce one mapping per value for each dynamic key used in any api.
    used_keys = set()
    for api in apis:
        used_keys.update(_extract_keys_from_obj(api))
    print(f"[executor] used dynamic keys in apis: {used_keys}")

    # Build mappings as the Cartesian product of all used keys' value lists.
    # This ensures that when an API uses multiple placeholders (e.g. {DNI} and {Ciudad})
    # each generated mapping contains values for all placeholders and URLs are expanded.
    from itertools import product
    mappings = []
    # preserve key order (appear in APIs) for deterministic mappings
    used_keys_list = []
    for api in apis:
        for k in _extract_keys_from_obj(api):
            if k not in used_keys_list:
                used_keys_list.append(k)
    # gather value lists for each key
    vals_lists = [dynamic_lists.get(k, []) for k in used_keys_list]
    # if any key has no values, keep a single empty mapping so caller can handle validation
    if any((not lst) for lst in vals_lists):
        mappings = [{}]
    else:
        for combo in product(*vals_lists):
            mappings.append(dict(zip(used_keys_list, combo)))

    print(f"[executor] total mapping slots: {len(mappings)}")

    # Execute
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(_run_all(apis, mappings))
    # Persist responses to disk under resultados/<timestamp>_
    try:
        base = os.path.abspath(os.getcwd())
        root_results = os.path.join(base, 'resultados')
        os.makedirs(root_results, exist_ok=True)
        ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        run_dir_name = f"run_{ts}"
        run_dir = os.path.join(root_results, run_dir_name)
        # avoid collision
        idx = 1
        orig = run_dir
        while os.path.exists(run_dir):
            run_dir = f"{orig}_{idx}"
            idx += 1
        os.makedirs(run_dir, exist_ok=True)
        # write each result as numbered json
        summary = []
        for i, r in enumerate(res):
            seq = r.get('seq') or (i+1)
            api_name = r.get('api_name', 'unnamed')
            safe_name = ''.join([c if c.isalnum() or c in ('-', '_') else '_' for c in api_name])[:60]
            filename = f"{seq:04d}_{safe_name}.json"
            filepath = os.path.join(run_dir, filename)
            # assemble stored object
            stored = {
                'seq': seq,
                'api_name': api_name,
                'url_expanded': r.get('url_expanded', ''),
                'method': r.get('method', ''),
                'headers_sent': r.get('headers_sent', {}),
                'body_sent': r.get('body_sent', None),
                'mapping': r.get('mapping', {}),
                'status': r.get('status'),
                'text': r.get('text'),
            }
            try:
                with open(filepath, 'w', encoding='utf-8') as fh:
                    json.dump(stored, fh, ensure_ascii=False, indent=2)
            except Exception:
                pass
            summary.append({'file': filename, 'api': api_name, 'status': r.get('status')})
        # write summary
        try:
            with open(os.path.join(run_dir, 'summary.json'), 'w', encoding='utf-8') as fh:
                json.dump({'created': ts, 'count': len(res), 'items': summary}, fh, ensure_ascii=False, indent=2)
        except Exception:
            pass
    except Exception:
        run_dir = ''
    # attach mapping and api name info to sample result printout
    # for i, r in enumerate(res[:20]):
    #     api_name = r.get('api_name', '<unnamed>')
    #     try:
    #         mapping_json = json.dumps(r.get('mapping', {}), ensure_ascii=False)
    #     except Exception:
    #         mapping_json = str(r.get('mapping', {}))
    #     text_snip = (r.get('text') or '')[:120]
    #     print(f"[executor] sample result {i}: api={api_name} status={r.get('status')} mapping={mapping_json} text={text_snip}")
    return res, run_dir

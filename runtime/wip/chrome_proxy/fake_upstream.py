"""Stand-in for the real Chrome MCP server, used ONLY to test bro_chrome_proxy.py. It drives no browser.

Every request it receives is appended to --log: that file is the independent evidence of what reached "Chrome".
  --mode ok      answers every call
  --mode dead    exits at once
  --mode mute    reads but never answers
  --mode image   answers get_page_text with an image block (a form the gate does not know)
"""
import argparse
import json
import sys
import time

TOOLS = ['list_connected_browsers', 'select_browser', 'tabs_context_mcp', 'tabs_create_mcp', 'tabs_close_mcp', 'navigate',
         'get_page_text', 'read_page', 'find', 'computer', 'javascript_tool', 'form_input']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--log', required=True)
    parser.add_argument('--mode', default='ok')
    parser.add_argument('--device', default='11111111-2222-3333-4444-555555555555')
    args = parser.parse_args()
    if args.mode == 'dead':
        return 3
    tabs = {}
    for raw in sys.stdin.buffer:
        message = json.loads(raw.decode('utf-8'))
        with open(args.log, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'method': message.get('method'), 'params': message.get('params')}) + '\n')
        if 'id' not in message:
            continue
        if args.mode == 'mute' and message['method'] != 'initialize':
            time.sleep(600)
        method, params = message['method'], message.get('params') or {}
        if method == 'initialize':
            result = {'protocolVersion': '2024-11-05', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'fake chrome', 'version': '0'}}
        elif method == 'tools/list':
            result = {'tools': [{'name': t, 'description': t, 'inputSchema': {'type': 'object'}} for t in TOOLS]}
        else:
            name, data = params.get('name'), params.get('arguments') or {}
            if name == 'list_connected_browsers':
                text = json.dumps([{'deviceId': args.device, 'name': 'Browser 1', 'osPlatform': 'Windows', 'connectedAt': 1, 'isLocal': True, 'inUse': True}])
            elif name == 'tabs_context_mcp':
                text = json.dumps({'availableTabs': [{'tabId': t, 'title': 'x', 'url': u} for t, u in tabs.items()], 'tabGroupId': 7})
            elif name == 'tabs_create_mcp':
                tabs[5001] = 'chrome://newtab/'
                text = 'Created new tab. Tab ID: 5001'
            elif name == 'navigate':
                tabs[data.get('tabId')] = data.get('url')
                text = 'Navigated'
            else:
                text = 'PAGE TEXT FROM FAKE CHROME'
            content = [{'type': 'image', 'data': 'AAAA', 'mimeType': 'image/png'}] if (args.mode == 'image' and name == 'get_page_text') else [{'type': 'text', 'text': text}]
            result = {'content': content}
        sys.stdout.write(json.dumps({'jsonrpc': '2.0', 'id': message['id'], 'result': result}) + '\n')
        sys.stdout.flush()
    return 0


if __name__ == '__main__':
    sys.exit(main())

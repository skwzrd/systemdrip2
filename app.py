import subprocess
import requests
import time
from flask import Flask

app = Flask(__name__)

services = {
    'redis': {'url': '', 'alias': ''},
    'sshd': {'url': '', 'alias': 'ssh'},
    'wg-quick@wg0': {'url': '', 'alias': 'wg'},
}

cached_results = None
last_checked_time = 0
cache_duration = 300

def collect_statuses_api():
    def get_systemd_status(service):
        result = subprocess.run(
            ['systemctl', 'show', service, '--property=ActiveState,UnitFileState,LoadState', '--value'],
            capture_output=True, text=True, check=True
        )
        return ' '.join(result.stdout.strip().split('\n'))

    def get_web_ping_status(url):
        try:
            response = requests.get(url, timeout=1)
            return f'http {response.status_code}'
        except requests.RequestException:
            return '(no resp)'

    results = []
    for service, d in services.items():
        systemd_status = get_systemd_status(service)
        web_status = 'na'
        if url := d.get('url'):
            web_status = get_web_ping_status(url)
        alias = d.get('alias')
        results.append({
            "service": service,
            "systemd_status": systemd_status,
            "web_status": web_status,
            "alias": alias,
        })
    return results

def generate_html(services, last_updated):
    html = """
    <!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Systemdrip2</title><style>html{font-family:system-ui}table{border-collapse:collapse}td,th{padding:8px;text-align:left;border:1px solid #ddd}th{background-color:#f2f2f2}</style></head><body>"""
    html += f"""
        <p>Last updated: {last_updated}</p>
        <table><thead><tr><th>Name</th><th>Web</th><th>Systemd</th></tr></thead><tbody>
    """
    for service in services:
        html += f"""
        <tr>
            <td>{service['service'] if not service['alias'] else service['alias']}</td>
            <td>{service['web_status']}</td>
            <td>{service['systemd_status']}</td>
        </tr>
        """
    html += f"""</tbody></table><script>
    setInterval(function () {{
        location.reload();
    }}, 1000 * 60 * 5); // page will reload every 1 minute(s)
    </script></body></html>
    """
    return html

@app.route('/', methods=['GET'])
def service_status():
    global cached_results, last_checked_time
    current_time = time.time()
    if cached_results is not None and (current_time - last_checked_time) < cache_duration:
        return cached_results
    last_checked_time = current_time
    last_updated = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last_checked_time))
    cached_results = generate_html(collect_statuses_api(), last_updated)
    return cached_results

if __name__ == '__main__':
    app.run(debug=True)

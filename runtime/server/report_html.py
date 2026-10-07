"""Offline aggregate report; no customer identities and no sending."""
import argparse, html, json
from datetime import datetime, timezone
from pathlib import Path
from runtime import Runtime
from contact_metrics import daily_summary

def render(report,include_tests=False):
 orders=[x for x in report['orders'] if x['data'].get('test') is not True]
 calls=[x for x in report['call_jobs'] if x['data'].get('test') is not True]
 ids={x['id'] for x in orders}
 metrics=[('Сохранено форм с сайта',len(orders)),('Сообщений сопоставлено оператором',sum(x['order_id'] in ids for x in report['whatsapp_matches'])),('Записано телефонных обращений',len(calls)),('Выполнено по записи оператора',sum(x['data']['outcome']=='COMPLETED' for x in calls))]
 days=daily_summary(report.get('contact_interactions',[]),include_tests=include_tests)
 contact_section='<h2>Нажатия кнопок — по дням Москвы</h2><p>Нажатие не является звонком или полученным сообщением. TEST исключён.</p>'
 if not days:contact_section+='<p>Записанных нажатий нет; полнота наблюдения не установлена.</p>'
 for day in days:contact_section+='<p>'+html.escape(day['date'])+' / Позвонить: '+str(day['call'])+' / WhatsApp: '+str(day['wa'])+' / Telegram: '+str(day['tg'])+'</p>'
 if include_tests:contact_section='<h2>ТЕСТОВЫЙ ОТЧЁТ — нажатия включают TEST; не статистика бизнеса</h2>'+contact_section.replace('TEST исключён.','TEST включён только в нажатия.')
 contact_section+='<p>Метрика: сравнение не подключено.</p>'
 cards=''.join('<article><strong>'+str(value)+'</strong><p>'+html.escape(label)+'</p></article>' for label,value in metrics)
 return '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>КРЮК24 — отчёт</title><style>body{font:18px system-ui;background:#f3f5f7;color:#152231;max-width:800px;margin:auto;padding:24px}section{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}article{background:white;padding:20px;border-radius:16px}strong{font-size:36px}p{line-height:1.5}</style><h1>КРЮК24 — состояние учёта</h1><p>Срез всего сохранённого журнала. Сформирован: '''+html.escape(datetime.now(timezone.utc).isoformat())+'''</p><section>'''+cards+'''</section>'''+contact_section+'''<p>Тестовые записи исключены. Форма не означает, что сообщение получено или заказ выполнен. Телефонные результаты внесены оператором; источник рекламы для них неизвестен.</p><p>Это не полная статистика бизнеса: незаписанные звонки и заказы сюда не входят. Выручка, прибыль и эффективность рекламы пока не установлены.</p><p>Отчёт не содержит телефонов, адресов или имён клиентов.</p></html>'''

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--output',required=True);p.add_argument('--include-test-clicks',action='store_true');a=p.parse_args()
 if not Path(a.db).is_file(): p.error('existing database required')
 with Path(a.output).open('x',encoding='utf-8') as f:f.write(render(Runtime(a.db).report(),include_tests=a.include_test_clicks))
 print(json.dumps({'report':a.output,'sent':False},ensure_ascii=False))

"""Bounded contact-intent metadata and Moscow daily aggregates. No request headers stored."""
import ipaddress, re
from datetime import datetime, timedelta, timezone
PAGES={'/','/index.html','/evakuator-balashikha/','/evakuator-domodedovo/','/evakuator-khimki/','/evakuator-lyubertsy/','/evakuator-podolsk/','/manipulyator/','/perevozka-spetstekhniki/','/operator/staging'}
FIELDS={'channel','page','position','button','referrer_domain','utm','yclid','device'}
def validate_metadata(data):
 if not isinstance(data,dict) or set(data)-FIELDS:raise ValueError('invalid contact metadata fields')
 if data.get('channel') not in ('call','wa','tg'):raise ValueError('invalid contact channel')
 if data.get('page') not in PAGES:raise ValueError('unknown page; no query strings allowed')
 if data.get('position') not in ('header','hero','sticky','form','footer','content'):raise ValueError('invalid button position')
 if data.get('device') not in ('mobile','desktop'):raise ValueError('invalid device category')
 button=data.get('button','')
 if not isinstance(button,str) or not re.fullmatch(r'(header|hero|sticky|form|footer|content)-(call|wa|tg)-[0-9]{1,3}',button):raise ValueError('invalid button code')
 if not button.startswith(data['position']+'-'+data['channel']+'-'):raise ValueError('button/channel mismatch')
 domain=data.get('referrer_domain','')
 if not isinstance(domain,str) or len(domain)>253 or (domain and not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',domain)):raise ValueError('domain only required')
 if re.search(r'[0-9]{7,}',domain):raise ValueError('phone-like referrer not stored')
 if domain:
  try:ipaddress.ip_address(domain)
  except ValueError:pass
  else:raise ValueError('IP referrers not stored')
 utm=data.get('utm',{})
 if not isinstance(utm,dict) or set(utm)-{'utm_source','utm_medium','utm_campaign','utm_content','utm_term'}:raise ValueError('invalid UTM keys')
 for value in utm.values():
  if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',value) or re.search(r'[0-9]{7,}',value):raise ValueError('campaign codes only; no free text or phone numbers')
 yclid=data.get('yclid','')
 if not isinstance(yclid,str) or (yclid and not re.fullmatch(r'[0-9]{1,32}',yclid)):raise ValueError('invalid yclid')
 return {**data,'referrer_domain':domain,'utm':utm,'yclid':yclid}
MOSCOW=timezone(timedelta(hours=3))
def daily_summary(interactions,include_tests=False):
 days={}
 for row in interactions:
  if row['data'].get('test') is True and not include_tests:continue
  day=datetime.fromisoformat(row['created']).astimezone(MOSCOW).date().isoformat()
  counts=days.setdefault(day,{'call':0,'wa':0,'tg':0})
  counts[row['data']['channel']]+=1
 return [{'date':day,**days[day]} for day in sorted(days,reverse=True)]

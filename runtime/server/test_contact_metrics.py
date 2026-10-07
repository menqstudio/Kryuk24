import json, tempfile, unittest
from pathlib import Path
from runtime import Runtime
from contact_metrics import daily_summary
from report_html import render

def metadata(channel='call'):
 return dict(channel=channel,page='/',position='hero',button='hero-'+channel+'-0',referrer_domain='yandex.ru',utm={'utm_source':'yandex','utm_campaign':'tow_moscow'},yclid='123456789',device='mobile')
class ContactTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.r=Runtime(str(Path(self.tmp.name)/'db'))
 def tearDown(self):self.tmp.cleanup()
 def test_each_channel_does_not_create_order(self):
  for i,ch in enumerate(('call','wa','tg')):self.r.contact_click('CLICK-'+str(i)*32,metadata(ch))
  report=self.r.report();self.assertEqual(report['orders'],[]);self.assertEqual(len(report['contact_interactions']),3)
  self.assertEqual(report['contact_daily_test'][0]['call'],1);self.assertEqual(report['contact_daily_test'][0]['wa'],1);self.assertEqual(report['contact_daily_test'][0]['tg'],1)
  self.assertEqual(report['contact_daily'],[])
 def test_idempotency_and_conflicting_payload(self):
  key='CLICK-'+'a'*32
  self.assertTrue(self.r.contact_click(key,metadata())['new']);self.assertFalse(self.r.contact_click(key,metadata())['new'])
  with self.assertRaises(ValueError):self.r.contact_click(key,metadata('wa'))
  self.assertEqual(len(self.r.report()['contact_interactions']),1)
 def test_reject_personal_fields_and_raw_urls(self):
  variants=[{**metadata(),'phone':'+79858930606'},{**metadata(),'ip':'1.2.3.4'},{**metadata(),'user_agent':'Browser'}, {**metadata(),'page':'/?phone=79858930606'},{**metadata(),'referrer_domain':'https://example.com/private'},{**metadata(),'referrer_domain':'1.2.3.4'},{**metadata(),'utm':{'utm_campaign':'79858930606'}},{**metadata(),'utm':{'utm_term':'a@example.com'}}]
  for i,m in enumerate(variants):
   with self.assertRaises(ValueError):self.r.contact_click('CLICK-'+format(i,'032x'),m)
  self.assertEqual(self.r.report()['contact_interactions'],[])
 def test_stored_contact_row_has_only_bounded_metadata(self):
  self.r.contact_click('CLICK-'+'a'*32,metadata())
  with self.r.db() as db:row=dict(db.execute('SELECT * FROM contact_interactions').fetchone())
  clean=json.loads(row['data']);self.assertEqual(set(clean),set(metadata())|{'test'})
  for key in ('phone','contact','name','ip','user_agent','href','referrer'):self.assertNotIn(key,clean)
 def test_form_link_is_one_atomic_interaction_on_retry(self):
  m=metadata('wa');m.update(position='form',button='form-wa-0')
  payload=dict(contact='NOT_PROVIDED',pickup='A',destination='B',vehicle='car',channel='wa',request_id='K24-'+'a'*32,interaction=m,flow='VISITOR_SENDS_WHATSAPP',test=True)
  self.r.intake(payload,payload['request_id']);self.r.intake(payload,payload['request_id'])
  report=self.r.report();self.assertEqual(len(report['orders']),1);self.assertEqual(len(report['contact_interactions']),1);self.assertEqual(report['contact_interactions'][0]['order_id'],payload['request_id'])
 def test_invalid_form_metadata_leaves_no_order(self):
  m=metadata('wa');m.update(position='form',button='form-wa-0',phone='PRIVATE')
  with self.assertRaises(ValueError):self.r.intake(dict(contact='X',pickup='A',destination='B',vehicle='car',channel='wa',interaction=m),'bad')
  self.assertEqual(self.r.report()['orders'],[])
 def test_moscow_midnight_and_test_exclusion_in_report(self):
  rows=[{'created':'2026-10-06T21:05:00+00:00','data':{'channel':'call','test':False}},{'created':'2026-10-06T20:59:00+00:00','data':{'channel':'wa','test':False}},{'created':'2026-10-06T21:10:00+00:00','data':{'channel':'tg','test':True}}]
  days=daily_summary(rows);self.assertEqual(days[0],{'date':'2026-10-07','call':1,'wa':0,'tg':0})
  content=render({'orders':[],'call_jobs':[],'whatsapp_matches':[],'contact_interactions':rows})
  self.assertIn('2026-10-07 / Позвонить: 1 / WhatsApp: 0 / Telegram: 0',content)

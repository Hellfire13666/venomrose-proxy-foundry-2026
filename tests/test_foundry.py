import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from venomrose import core as c

class ProxyParserTests(unittest.TestCase):
    def test_valid_http(self):
        p=c.parse_line('8.8.8.8:8080');self.assertEqual(p.address,'http://8.8.8.8:8080')
    def test_socks5(self):
        self.assertEqual(c.parse_line('socks5://1.1.1.1:1080').protocol,'socks5')
    def test_ipv6(self):
        self.assertEqual(c.parse_line('socks4://[2606:4700:4700::1111]:1080').port,1080)
    def test_invalid_hostname(self):
        self.assertIsNone(c.parse_line('example.com:8080'))
    def test_invalid_credentials(self):
        self.assertIsNone(c.parse_line('http://user:pass@1.1.1.1:80'))
    def test_invalid_reserved(self):
        self.assertIsNone(c.parse_line('10.0.0.1:3128'))
        self.assertIsNone(c.parse_line('192.0.2.1:3128'))
    def test_invalid_port(self):
        self.assertIsNone(c.parse_line('1.1.1.1:99999'))
        self.assertIsNone(c.parse_line('1.1.1.1:0'))
    def test_invalid_path(self):
        self.assertIsNone(c.parse_line('http://1.1.1.1:80/admin'))
    def test_blank_comment(self):
        self.assertIsNone(c.parse_line('# testing'))
    def test_txt_mixed(self):
        result,bad=c.parse_feed('1.1.1.1:80\nsocks5://8.8.8.8:1080\n8.8.4.4:443\ninvalid\n','txt','http')
        self.assertEqual(len(result),3); self.assertEqual(bad,1)
    def test_json_array(self):
        result,bad=c.parse_feed('[{"protocol":"http","ip":"8.8.8.8","port":8080,"country_code":"US","latency_ms":55}]','json')
        self.assertEqual((result[0].country,result[0].provider_latency_ms,bad),('US',55,0))
    def test_json_envelope(self):
        result,bad=c.parse_feed('{"snapshot":"x","proxies":[{"ip":"1.1.1.1","port":1080,"protocol":"socks5","uptime_24h":93}]}','json')
        self.assertEqual((result[0].protocol,result[0].uptime_pct,bad),('socks5',93,0))
    def test_monosans_metadata(self):
        row={"protocol":"socks5","host":"8.8.4.4","port":1080,"timeout":0.25,"asn":{"autonomous_system_number":15169},"geolocation":{"country":{"iso_code":"US"}}}
        p=c.parse_json_record(row)
        self.assertEqual((p.country,p.provider_latency_ms,p.asn),('US',250,'15169'))
    def test_metadata_credentials_rejected(self):
        self.assertIsNone(c.parse_json_record({"ip":"8.8.8.8","port":3128,"username":"user","password":"secret"}))
    def test_metadata_bad_values(self):
        row={"ip":"8.8.8.8","port":8080,"uptime_percent":120,"latency_ms":"garbage"}
        p=c.parse_json_record(row)
        self.assertIsNone(p.uptime_pct);self.assertIsNone(p.provider_latency_ms)
    def test_json_bad_rows(self):
        result,bad=c.parse_feed('[{},null,{"protocol":"http","ip":"8.8.8.8","port":80}]','json')
        self.assertEqual((len(result),bad),(1,2))

class FoundryTests(unittest.TestCase):
    def test_merge_dedupe_sources(self):
        store={}
        for source,grp in [('monosans','monosans'),('monosans-meta','monosans'),('proxyscrape','proxyscrape')]:
            c.merge_proxy(store,c.parse_line('1.1.1.1:3128'),source,grp)
        p=list(store.values())[0]
        self.assertEqual((len(store),len(p.groups),len(p.sources)),(1,2,3))
    def test_rank_metadata(self):
        p=c.parse_line('1.1.1.1:80'); p.groups={'monosans'}; r0=c.ranking(p)
        p.last_checked='2026-10-21';p.uptime_pct=92;p.provider_latency_ms=20
        self.assertGreater(c.ranking(p),r0)
    def test_rank_tcp(self):
        p=c.parse_line('1.1.1.1:80');p.groups={'monosans'}
        r0=c.ranking(p);p.tcp_status='reachable';self.assertGreater(c.ranking(p),r0)
    def test_sort_by_latency(self):
        a=c.parse_line('1.1.1.1:80');b=c.parse_line('8.8.8.8:80')
        a.provider_latency_ms=500;b.provider_latency_ms=20
        self.assertEqual(c.sort_items([a,b],'latency')[0].host,b.host)
    def test_sort_ip(self):
        a=c.parse_line('8.8.8.8:80');b=c.parse_line('1.1.1.1:80')
        self.assertEqual(c.sort_items([a,b],'ip')[0].host,'1.1.1.1')
    def test_demo_synthetic(self):
        d,states,total,bad=c.demo_data()
        self.assertEqual((len(d),total,bad),(4,6,0))
        self.assertEqual(sum(len(x.groups)>1 for x in d.values()),2)
        self.assertEqual(states['demo']['state'],'synthetic')
    def test_dashboard_escape(self):
        report=c.build_report([],{'<script>':{'state':'received','rows':0}},'TEST',0,0,0)
        s=c.render_html(report)
        self.assertIn('&lt;script&gt;',s)
        self.assertNotIn('<script>',s)
    def test_dashboard_offline(self):
        r=c.build_report([],{"sample":{"state":"received"}},'TEST',0,0,0)
        h=c.render_html(r)
        self.assertIn("default-src 'none'",h)
        self.assertNotIn('src="http',h)
    def test_save_four_reports(self):
        with tempfile.TemporaryDirectory() as d:
            r=c.build_report([],{"synthetic":{"state":"synthetic"}},'SYNTHETIC',0,0,0)
            paths=c.save_report(r,Path(d)/'r')
            self.assertEqual(set(paths),{'json','csv','txt','html'})
            for path in paths.values():self.assertTrue(Path(path).is_file())
            self.assertEqual(json.loads(Path(paths['json']).read_text())['version'],c.VERSION)
    def test_private_report_modes(self):
        if os.name=='nt':self.skipTest('Unix only')
        with tempfile.TemporaryDirectory() as d:
            r=c.build_report([],{},'TEST',0,0,0);paths=c.save_report(r,Path(d)/'r')
            self.assertEqual(os.stat(paths['json']).st_mode & 0o777,0o600)
    def test_demo_cli(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main(['--demo','--out',d,'--color','never']),0)
            self.assertTrue(list(Path(d).glob('*.html')))
    def test_file_cli(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            f=Path(d)/'input.txt';f.write_text('1.1.1.1:80\n192.0.2.1:90\n')
            self.assertEqual(c.main(['--from-file',str(f),'--out',str(Path(d)/'out')]),0)
            result=json.loads(next((Path(d)/'out').glob('*.json')).read_text())
            self.assertEqual(result['summary']['unique'],1)
    def test_country_filter(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            c.main(['--demo','--country','US','--out',d])
            r=json.loads(next(Path(d).glob('*.json')).read_text())
            self.assertEqual(r['summary']['unique'],1)
    def test_demo_no_probe(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):c.main(['--demo','--probe','1'])
    def test_out_of_bounds_probe(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):c.main(['--live','--probe','50'])
    def test_unknown_feed(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):c.main(['--live','--feeds','nope'])
    def test_feed_404(self):
        with patch.object(c.urllib.request,'urlopen',side_effect=HTTPError('example',404,'missing',{},None)):
            rows,status=c.fetch_feed('monosans',3)
        self.assertEqual((rows,status['state']),([], 'no_data'))
    def test_feed_rate_limit(self):
        with patch.object(c.urllib.request,'urlopen',side_effect=HTTPError('example',429,'rate',{},None)):
            rows,status=c.fetch_feed('monosans',3)
        self.assertEqual(status['state'],'rate_limited')
    def test_feed_unavailable(self):
        with patch.object(c.urllib.request,'urlopen',side_effect=URLError('offline')):
            rows,status=c.fetch_feed('monosans',3)
        self.assertEqual(status['state'],'unavailable')
    def test_feed_mock_parsing(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def read(self,n):return b'1.1.1.1:3128\n'
        with patch.object(c.urllib.request,'urlopen',return_value=Response()):
            rows,status=c.fetch_feed('speedx-http',3)
        self.assertEqual((rows[0].address,status['state']),('http://1.1.1.1:3128','received'))
    def test_live_mock_no_network(self):
        def fake(name,timeout):
            return ([c.parse_line('1.1.1.1:80')], {'state':'received','rows':1,'discarded':0,'elapsed_ms':0})
        with tempfile.TemporaryDirectory() as d,patch.object(c,'fetch_feed',side_effect=fake),patch.object(c.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main(['--live','--feeds','monosans,proxyscrape','--min-sources','2','--out',d]),0)
            report=json.loads(next(Path(d).glob('*.json')).read_text())
            self.assertEqual((report['summary']['multi_source'],report['summary']['unique']),(1,1))
    def test_demo_never_probes(self):
        with tempfile.TemporaryDirectory() as d,patch.object(c,'probe_tcp',side_effect=AssertionError('not called')),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(c.main(['--demo','--out',d]),0)
    def test_probe_function_mock_socket(self):
        class FakeSocket:
            def __enter__(self):return self
            def __exit__(self,*_):pass
        with patch.object(c.socket,'create_connection',return_value=FakeSocket()) as f:
            state,ms=c.probe_tcp(c.parse_line('1.1.1.1:3128'),2)
        self.assertEqual(state,'reachable');self.assertGreaterEqual(ms,0)
        f.assert_called_once_with(('1.1.1.1',3128),timeout=2)

if __name__=='__main__':unittest.main()

class ForwardingTests(unittest.TestCase):
    def test_socks_skipped(self):
        status,ms=c.verify_http_forward(c.parse_line('socks5://1.1.1.1:1080'),3)
        self.assertEqual(status,'unsupported_protocol');self.assertIsNone(ms)
    def test_fixed_destination_and_proxy(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def getcode(self):return 200
            def read(self,n):return b'Example Domain'
        class Opener:
            def open(self,request,timeout=0):
                self.request=request
                return Response()
        op=Opener()
        with patch.object(c.urllib.request,'build_opener',return_value=op) as mock:
            status,ms=c.verify_http_forward(c.parse_line('http://1.1.1.1:3128'),3)
        self.assertEqual(status,'verified');self.assertIn('example.com',op.request.full_url)
        self.assertIn('https',mock.call_args.args[0].proxies)
    def test_http_failure(self):
        with patch.object(c.urllib.request,'build_opener') as mock:
            mock.return_value.open.side_effect=URLError('timeout')
            status,ms=c.verify_http_forward(c.parse_line('1.1.1.1:80'),2)
        self.assertEqual(status,'failed')
    def test_http_scores(self):
        p=c.parse_line('1.1.1.1:80');p.groups.add('test');a=c.ranking(p)
        p.forwarding_status='verified';self.assertGreater(c.ranking(p),a)
    def test_demo_no_forward(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):c.main(['--demo','--verify-http','1'])

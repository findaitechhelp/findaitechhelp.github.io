"""Build orchestration contracts; mock child processes to avoid recursive discovery."""
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import build_cloudflare as cloudflare

class CloudflareBuildTests(unittest.TestCase):
    def test_cloudflare_requires_valid_explicit_origin_before_any_subprocess(self):
        for origin in [None,'','http://example.com','https://example.com/path']:
            env={'CF_PAGES':'1'}
            if origin is not None:env['PUBLIC_SITE_ORIGIN']=origin
            with self.subTest(origin=origin),patch.dict(os.environ,env,clear=True),patch.object(cloudflare.subprocess,'run') as run:
                self.assertEqual(cloudflare.main(),1)
                run.assert_not_called()

    def test_order_and_final_build_keep_production_environment(self):
        env={'CF_PAGES':'1','PUBLIC_SITE_ORIGIN':'https://example.pages.dev'}
        seen=[]
        def child(command,**kwargs):
            seen.append((command,os.environ.get('PUBLIC_SITE_ORIGIN')))
            self.assertTrue(kwargs['check'])
            self.assertEqual(kwargs['cwd'],cloudflare.ROOT)
        with patch.dict(os.environ,env,clear=True),patch.object(cloudflare.subprocess,'run',side_effect=child):
            self.assertEqual(cloudflare.main(),0)
        self.assertEqual([command[1:] for command,_ in seen],[['tools/validate.py'],['-m','unittest','discover','tests','-v'],['tools/check_public_review.py']])
        self.assertEqual([origin for _,origin in seen],['https://example.pages.dev']*3)

    def test_any_failed_check_prevents_final_build(self):
        for failed_at in range(2):
            calls=[]
            def child(command,**kwargs):
                calls.append(command)
                if len(calls)==failed_at+1:raise subprocess.CalledProcessError(1,command)
            with self.subTest(failed_at=failed_at),patch.dict(os.environ,{},clear=True),patch.object(cloudflare.subprocess,'run',side_effect=child):
                self.assertEqual(cloudflare.main(),1)
                self.assertEqual(len(calls),failed_at+1)

if __name__=='__main__':unittest.main()

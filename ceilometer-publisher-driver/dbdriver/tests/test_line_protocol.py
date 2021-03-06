# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime
import unittest
from pytz import UTC, timezone

from influxdb import line_protocol


class TestLineProtocol(unittest.TestCase):

    def test_make_lines(self):
        data = {
            "tags": {
                "empty_tag": "",
                "none_tag": None,
                "integer_tag": 2,
                "string_tag": "hello"
            },
            "points": [
                {
                    "measurement": "test",
                    "fields": {
                        "string_val": "hello!",
                        "int_val": 1,
                        "float_val": 1.1,
                        "none_field": None,
                        "bool_val": True,
                    }
                }
            ]
        }

        self.assertEqual(
            line_protocol.make_lines(data),
            'test,integer_tag=2,string_tag=hello '
            'bool_val=True,float_val=1.1,int_val=1i,string_val="hello!"\n'
        )

    def test_timezone(self):
        dt = datetime(2009, 11, 10, 23, 0, 0, 123456)
        utc = UTC.localize(dt)
        berlin = timezone('Europe/Berlin').localize(dt)
        eastern = berlin.astimezone(timezone('US/Eastern'))
        data = {
            "points": [
                {"measurement": "A", "fields": {"val": 1},
                 "time": 0},
                {"measurement": "A", "fields": {"val": 1},
                 "time": "2009-11-10T23:00:00.123456Z"},
                {"measurement": "A", "fields": {"val": 1}, "time": dt},
                {"measurement": "A", "fields": {"val": 1}, "time": utc},
                {"measurement": "A", "fields": {"val": 1}, "time": berlin},
                {"measurement": "A", "fields": {"val": 1}, "time": eastern},
            ]
        }
        self.assertEqual(
            line_protocol.make_lines(data),
            '\n'.join([
                'A val=1i 0',
                'A val=1i 1257894000123456000',
                'A val=1i 1257894000123456000',
                'A val=1i 1257894000123456000',
                'A val=1i 1257890400123456000',
                'A val=1i 1257890400123456000',
            ]) + '\n'
        )

    def test_string_val_newline(self):
        data = {
            "points": [
                {
                    "measurement": "m1",
                    "fields": {
                        "multi_line": "line1\nline1\nline3"
                    }
                }
            ]
        }

        self.assertEqual(
            line_protocol.make_lines(data),
            'm1 multi_line="line1\\nline1\\nline3"\n'
        )

    def test_make_lines_unicode(self):
        data = {
            "tags": {
                "unicode_tag": "\'Привет!\'"  # Hello! in Russian
            },
            "points": [
                {
                    "measurement": "test",
                    "fields": {
                        "unicode_val": "Привет!",  # Hello! in Russian
                    }
                }
            ]
        }

        self.assertEqual(
            line_protocol.make_lines(data),
            'test,unicode_tag=\'Привет!\' unicode_val="Привет!"\n'
        )

    def test_quote_ident(self):
        self.assertEqual(
            line_protocol.quote_ident(r"""\foo ' bar " Örf"""),
            r'''"\\foo ' bar \" Örf"'''
        )

    def test_quote_literal(self):
        self.assertEqual(
            line_protocol.quote_literal(r"""\foo ' bar " Örf"""),
            r"""'\\foo \' bar " Örf'"""
        )

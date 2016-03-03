#    Copyright krozin.com
#   __author__  krozin@gmail.com

import unittest

from ipmi_driver import DevopsDriver, DevopsDriverException



class TestDevopsDriver(unittest.TestCase):

    def setUp(self):
        self.user = 'test'
        self.password = 'test1'
        self.level = 3
        self.host = 'test.com'

    def test_check_system_ready(self):
        try:
            dd = DevopsDriver(self.user, self.password, self.host, self.level)
            self.assertEqual(dd._check_system_ready(), True)
        except Exception as e:
            print e

    def test_check_remote_host(self):
        try:
            dd = DevopsDriver(self.user, self.password, self.host, self.level)
            self.assertEqual(dd._check_remote_host(), True)
        except Exception as e:
            print e

    def test_check_false_remote_host(self):
        try:
            dd = DevopsDriver('fail', self.password, self.host, self.level)
            self.assertEqual(dd._check_remote_host() == False, True)
        except Exception as e:
            print e

    def test_controller_management(self):
        try:
            dd = DevopsDriver(self.user, self.password, self.host, self.level)
            self.assertEqual(dd.node_controller_info() != {}, True)
        except Exception as e:
            print e

    def test_user_management(self):
        try:
            dd = DevopsDriver(self.user, self.password, self.host, self.level)
            self.assertEqual(dd.node_user_list() != [], True)
        except Exception as e:
            print e

    def test_power_management(self):
        try:
            dd = DevopsDriver(self.user, self.password, self.host, self.level)
            self.assertEqual(dd.node_power_status() != None, True)
            self.assertEqual(dd.node_power_off(), True)
            self.assertEqual(dd.node_power_on(), True)
            self.assertEqual(dd.node_power_reset(), True)
            self.assertEqual(dd.node_power_on(), True)
        except Exception as e:
            print e

    def test_chassis_management(self):
        try:
            dd = DevopsDriver(self.user, self.password, self.host, self.level)
            self.assertEqual(dd.node_chassis_status() != {}, True)
        except Exception as e:
            print e

    def test_lan_management(self):
        try:
            dd = DevopsDriver(self.user, self.password, self.host, self.level)
            self.assertEqual(dd.node_lan_status() != {}, True)
            self.assertEqual(dd.node_lan_stats() != {}, True)
        except Exception as e:
            print e

if __name__ == '__main__':
    unittest.main()
#    Copyright krozin.com
#    __author__  krozin@gmail.com


from contextlib import contextmanager
import exceptions
import os
import shutil
import subprocess
from StringIO import StringIO
import time

class DevopsDriverException(Exception):
    pass


class DevopsDriver(object):
    """ IPMI DevopsDriver

        The DevopsDriver shall provide ability to manage remote
        baremetal node through impi interface by using
        ipmitool: http://sourceforge.net/projects/ipmitool/
        Take into account that it is suitable tool
        according to licence criteria.

        More info can be found here:
        http://ipmiutil.sourceforge.net/docs/ipmisw-compare.htm

        Note:
            Power management - on/off/reset
            User management - user list
            Chassis management - chassis info
            Virtual Storage management - ISO attache
            Sensors management - get sensors info
            Node management - start/stop/reset

        Args:
`           ipmi_user(str)
            ipmi_password(str)
            ipmi_prev_level(Optional(int))
            ipmi_remote_host(str)
            ipmi_remote_lan_interface(Optional(str))

        Attributes:
            ipmi_user(str)       -- the user login for IPMI board. mandatory.
            ipmi_password(str)   -- the user password. mandatory.
            ipmi_prev_level(int) -- the user privileges level. (default 3)
                    values: 1 - CALLBACK, 2 - USER, 3 - OPERATOR
                            4 - ADMINISTRATOR, 5 - OEM, 15 - NO ACCESS
            ipmi_remote_host(str) -- remote host name. mandatory
            ipmi_remote_lan_interface(str) -- the lan interface. (default 'lanplus')
                    values: lan, lanplus

    """

    def __init__(self,
                 ipmi_user, ipmi_password, ipmi_remote_host,
                 ipmi_prev_level = 3,
                 ipmi_remote_lan_interface='lanplus',
                 ipmi_remote_port=None):

        super(DevopsDriver, self).__init__()

        if not (ipmi_user and ipmi_password and ipmi_prev_level\
           and ipmi_remote_host):
            raise DevopsDriverException('Error while init.')

        self.ipmi_user = ipmi_user
        self.ipmi_password = ipmi_password
        self.features = self._get_capabilities()
        self.ipmi_prev_level = self._get_ipmi_prev_level(ipmi_prev_level)
        self.ipmi_remote_host = ipmi_remote_host
        self.ipmi_remote_lan_interface = ipmi_remote_lan_interface
        self.ipmi_remote_port = ipmi_remote_port
        self.ipmi_cmd = ['ipmitool',
                         '-I', self.ipmi_remote_lan_interface,
                         '-H', self.ipmi_remote_host,
                         '-U', self.ipmi_user, '-P', self.ipmi_password,
                         '-L', self.ipmi_prev_level]
        if ipmi_remote_port:
            self.ipmi_cmd.extend(['-p', ipmi_remote_port])
        self._check_system_ready()
        self._check_remote_host()
        self.ipmi_user_id = self._get_user_id()

    def _check_system_ready(self):
        """ Double check that ipmitool is presented
        Args: None
        Returns:
            True if successful, False otherwise.
        """
        for command in ['/usr/bin/ipmitool']:
            if not os.path.exists(command):
                return False
        return True

    def _get_ipmi_prev_level(self, level):
        return self._get_capabilities().get('UserManagementPrivilegesLevel',
                                            {}).get(str(int(level)), 'USER')

    def _get_capabilities(self):
        """Get capabilities

        Note: self.capabilities shall be set if it is None
        Args: None
        Returns: capabilities dictionary.
        """
        features = {'PowerManagement': ['status', 'on', 'off',
                                        'cycle', 'reset', 'diag', 'soft'],
                    'PowerManagementStatus': ['Chassis Power is on',
                                              'Chassis Power is off'],
                    'PowerManagementOn': 'Chassis Power Control: Up/On',
                    'PowerManagementOff': 'Chassis Power Control: Down/Off',
                    'PowerManagementReset': 'Chassis Power Control: Reset',
                    'PowerManagementCycle': 'Chassis Power Control: Cycle',
                    'UserManagement': ['list'],
                    'UserManagementPrivilegesLevel': {
                        '1': 'CALLBACK',
                        '2': 'USER',
                        '3': 'OPERATOR',
                        '4': 'ADMINISTRATOR',
                        '5': 'OEM',
                        '15': 'NO ACCESS'},
                    'UserManagementListReply': 'ID  Name',
                    'ChassisManagement': ['status', 'power', 'identify',
                                          'bootdev', 'bootparam', 'selftest'],
                    'LanManagement': ['print', 'stats get'],
                    'ControllerManagement': ['info', 'getsysinfo', 'getenables'],
                    'VirtualStorageManagement': [],
                    'SensorsManagement': []}
        return features

    def _run_ipmi(self, args):
        """ Run command through ipmitool

        Args: args(str) -- ipmitool command string
        Returns: True if successful, None otherwise.
        """
        out = None
        err = None
        rcode = None

        if not args:
            return None
        try:
            # workaround for commands like "stats get. Need to investigate why
            args = " ".join(args).split(" ")
            #print " ".join(args)
            pipe = subprocess.Popen(args, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            out, err = pipe.communicate()
            rcode = pipe.returncode
        except Exception as e:
            #logger.debug('{}'.format(e))
            print e
            return None
        if out is None:
            print "rcode ={} or out ={}".format(rcode, out)
            return None
        return out

    def _check_remote_host(self):
        """ Check baremetal node through ipmi

        Args: None
        Returns: True if successful, False otherwise.
        """
        return (self.node_controller_info() != {})

    def _get_user_id(self):
        userlist = self.node_user_list()
        for i in userlist:
            if self.ipmi_user == i.get('name'):
                return i.get('id')
        return None

    def _convert2dict(self, data):
        res = {}
        if data:
            for i in data.split('\n'):
                if i:
                    key,value = map(str.strip, i.split(':'))
                    res.update({key: value})
        return res

    def _convert2dict2(self, data):
        res = {}
        if data:
            for i in data.split('\n'):
                if i:
                    index = i.find(':')
                    if index > 0:
                        key = i[:index].strip()
                        value = i[index+1:].strip()
                        index2 = value.find(':')
                    else:
                        value = i.strip()
                        key = keepkey
                        index = 0
                    #print "index={}, key={}, value={}".format(index, key, value)

                    if key and index > 0:
                        res.update({key: value})
                        keepkey = key
                    else:
                        newvalue = res.get(keepkey, [])
                        if not isinstance(newvalue, list):
                            newvalue = []
                        newvalue.append(value)
                        res.update({keepkey: newvalue})
        #print res
        return res

    def node_controller_management(self, command):
        """ Try to do user controller
            applicable: list

        Args: command(str) -- ipmitool command string acceptable for 'power'
        Returns: output if successful, empty string otherwise.
        """
        if command in self.features.get('ControllerManagement'):
            cmd = self.ipmi_cmd + ['mc', command]
            return self._run_ipmi(cmd)
        return ''

    def node_controller_info(self):
        """  Try to controller status

        Args: None
        Returns: dict if successful, {} otherwise.
        """
        out = self.node_controller_management('info')
        return self._convert2dict2(out)

    def node_user_management(self, command):
        """ Try to do user management
            applicable: list

        Args: command(str) -- ipmitool command string acceptable for 'power'
        Returns: output if successful, empty string otherwise.
        """
        if command in self.features.get('UserManagement'):
            cmd = self.ipmi_cmd + ['user', command]
            return self._run_ipmi(cmd)
        return ''

    def node_user_list(self):
        """  Try to user list

        Args: None
        Returns: True if successful, False otherwise.
        """
        res = []
        out = self.node_user_management('list')
        if out.find(self.features.get('UserManagementListReply')) is not None:
            # let's get user ID and Privileges. UserID is a first column
            userlist = out.strip().split('\n')
            for i in userlist[1:]:
                ss= i.split(' ')
                id, priv, name = ss[0], ss[-1], " ".join([value for value in ss[1:4] if value])
                res.append({'id':id, 'name':name, 'priv': priv})
        return res

    def node_power_management(self, command):
        """ Try to do power management
            applicable: status/on/off/reset

        Args: command(str) -- ipmitool command string acceptable for 'power'
        Returns: output if successful, empty string otherwise.
        """
        if command in self.features.get('PowerManagement'):
            cmd = self.ipmi_cmd + ['power', command]
            return self._run_ipmi(cmd)
        return ''

    def node_power_status(self):
        """  Try to get power status

        Args: None
        Returns: 1 - power on, 0 - power off, None otherwise.
        """
        out = self.node_power_management('status').strip()
        if out.find(self.features.get('PowerManagementStatus',[])[0]):
            return 1
        elif out.find(self.features.get('PowerManagementStatus',[])[1]):
            return 0
        return None

    def node_power_on(self):
        """  Try to power on

        Args: None
        Returns: True if successful, False otherwise.
        """
        out = self.node_power_management('on').strip()
        if out.find(self.features.get('PowerManagementOn')) is not None:
            return True
        return False

    def node_power_off(self):
        """  Try to power off

        Args: None
        Returns: True if successful, False otherwise.
        """
        out = self.node_power_management('off').strip()
        if out.find(self.features.get('PowerManagementOff')) is not None:
            return True
        return False

    def node_power_reset(self):
        """  Try to power reset

        Args: None
        Returns: True if successful, False otherwise.
        """
        out = self.node_power_management('reset').strip()
        if out.find(self.features.get('PowerManagementReset')) is not None:
            return True
        return False

    def node_power_reboot(self):
        """  Try to power reboot

        Args: None
        Returns: True if successful, False otherwise.
        """
        out = self.node_power_management('cycle')
        if out.find(self.features.get('PowerManagementCycle')) is not None:
            return True
        return False

    def node_chassis_management(self, command):
        """ Try to do chassis management
            applicable: status, power, identify, policy,
                        restart_cause, poh, bootdev,
                        bootparam, selftest

        Args: command(str) -- ipmitool command string acceptable for 'chassis'
        Returns: output if successful, empty string otherwise.
        """
        if command in self.features.get('ChassisManagement'):
            cmd = self.ipmi_cmd + ['chassis', command]
            return self._run_ipmi(cmd)
        return ''

    def node_chassis_status(self):
        """  Try to get chassis status

        Args: None
        Returns: dict if OK, empty dict - {} otherwise.
        """
        out = self.node_chassis_management('status')
        return self._convert2dict(out)

    def node_lan_management(self, command):
        """ Try to do lan management
            applicable: print
                        stats get
                        stats clear
        Args: command(str) -- ipmitool command string acceptable for 'lan'
        Returns: output if successful, empty string otherwise.
        """
        if command in self.features.get('LanManagement'):
            cmd = self.ipmi_cmd + ['lan', command]
            return self._run_ipmi(cmd)
        return ''

    def node_lan_status(self):
        """  Try to get lan status

        Args: None
        Returns: dict if OK, empty dict - {} otherwise.
        """
        out = self.node_lan_management('print')
        return self._convert2dict2(out)

    def node_lan_stats(self):
        """  Try to get lan stats info

        Args: None
        Returns: dict if OK, empty dict - {} otherwise.
        """
        out = self.node_lan_management("stats get")
        return self._convert2dict(out)

    def node_shutdown(self):
        """  Shutdown Node

        Note: Actually we can do power off only
              but we have take into account
              safe shutdown if OS is already installed
        Args: None
        Returns: True if successful, False otherwise.
        """
        return self.node_power_off()

    def node_active(self):
        """  Check if node is active

        Note: we have to check power on and
              we have take into account that OS is working on remote host
        Args: None
        Returns: True if successful, False otherwise.
        """
        return (self.node_power_status() > 0)

    def node_exists(self, node):
        """  Check if node exists

        Args: None
        Returns: True if successful, False otherwise.
        """
        return self._check_remote_host()

    def set_node_boot(self, device):
        """Set boot device """
        cmd = self.ipmi_cmd + ['chassis', 'bootdev', device]
        output = subprocess.check_output(cmd)
        #logger.debug('Set boot server output: {0}'.format(output))
        return True


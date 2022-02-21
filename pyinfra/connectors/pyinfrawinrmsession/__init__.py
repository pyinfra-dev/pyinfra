import base64

import winrm


class PyinfraWinrmSession(winrm.Session):
    ''' This is our subclassed Session that allows for env setting '''

    def run_cmd(self, command, args=(), env=None):
        shell_id = self.protocol.open_shell(env_vars=env)
        command_id = self.protocol.run_command(shell_id, command, args)
        rs = winrm.Response(self.protocol.get_command_output(shell_id, command_id))
        self.protocol.cleanup_command(shell_id, command_id)
        self.protocol.close_shell(shell_id)
        return rs

    def run_ps(self, script, env=None):
        '''base64 encodes a Powershell script and executes the powershell
        encoded script command
        '''
        # must use utf16 little endian on windows
        encoded_ps = base64.b64encode(script.encode('utf_16_le')).decode('ascii')
        rs = self.run_cmd('powershell -encodedcommand {0}'.format(encoded_ps), env=env)
        if len(rs.std_err):
            # if there was an error message, clean it it up and make it human
            # readable
            rs.std_err = self._clean_error_msg(rs.std_err)
        return rs

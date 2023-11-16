import os
import os.path
import sys

import sys
if sys.platform == 'posix':
    os.system('echo Hello')
else:
    os.system(os.path.dirname(os.getcwd()))

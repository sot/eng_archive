"""
Derived Parameters
------------------

The engineering archive has pseudo-MSIDs that are derived via computation from
telemetry MSIDs.  All derived parameter names begin with the characters "DP_"
(not case sensitive as usual).  Otherwise there is no difference from standard
MSIDs.  
"""

from .base import *

from .thermal import *
from .test import *
from .acispow import *

import logging
import builtins

# カスタムログレベルVERBOSEを作成
VERBOSE = 15
logging.addLevelName(VERBOSE, "VERBOSE")

def verbose(self, message, *args, **kws):
    if self.isEnabledFor(VERBOSE):
        self._log(VERBOSE, message, args, **kws) 

logging.Logger.verbose = verbose

# カスタムログレベルDETAILEDを作成
DETAILED = 18
logging.addLevelName(DETAILED, "DETAILED")

def detailed(self, message, *args, **kws):
    if self.isEnabledFor(DETAILED):
        self._log(DETAILED, message, args, **kws) 

logging.Logger.detailed = detailed

# print関数をオーバーライド
old_print = builtins.print

def new_print(*args, **kwargs):
    old_print(*args, **kwargs)
    logging.getLogger().detailed(" ".join(map(str, args)))

builtins.print = new_print
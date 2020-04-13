#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

from jinja2 import TemplateError
from functools import partial

from .Test import SIPpTest
import sipplauncher.utils.Utils

class GlobalTest(SIPpTest):
    """
    This is a special subclass which contains a limited funcionality of a SIPpTest.

    This test is used to:
    1. run the `before.sh` script before all the other SIPpTests have been launched
    2. run the `after.sh` script after all the other SIPpTests have been finished

    The purpose of this class is to either perform a global initialization/cleanup,
    or to perform a global check for the consistent state of a DUT,
    which might be not feasible to do in each SIPpTest's `after.sh` for timing considerations.

    Due to subclassing, we get the useful functionality of a SIPpTest, like:
    - template engine
    - keyword substitution
    - temporary folder creation and logging to it
    """
    def _get_uas(self):
        # We don't need to support UA scenarios
        return set()

    def pre_run(self, run_id_prefix, args):
        """
        We overwrite `SIPpTest.pre_run()` with a shorter pre-run procedure.
        Also there are other small differences, like raising an exception.
        Unlike `SIPpTest`, `GlobalTest` should terminate immediately if any exception occurs.
        """
        start = time.time()
        self.run_id = sipplauncher.utils.Utils.generate_id(n=6, just_letters=True)
        self._set_state(SIPpTest.State.PREPARING)
        self._print_run_state(run_id_prefix)
        self._create_temp_folder()
        self._init_logger()
        try:
            self._replace_keywords(args)
            self._run_script("before.sh", args)
        except BaseException as e:
            self._set_state(SIPpTest.State.NOT_READY)
            end = time.time()
            elapsed = end - start
            elapsed_str=' - took %.0fs' % (elapsed)
            self._print_run_state(run_id_prefix, extra=elapsed_str)
            if isinstance(e, (TemplateError, SIPpTest.ScriptRunException)):
                # Logging is activated. Safe to print to temp folder.
                self._get_logger().debug(e, exc_info = True)
            raise
        else:
            # No exceptions during initialization.
            self._set_state(SIPpTest.State.READY)
            self._successful = True

    def _get_cleanup_handlers(self, args):
        cleanup_handlers = []
        cleanup_handlers.append(partial(SIPpTest._run_script, self, "after.sh", args))
        cleanup_handlers.append(partial(SIPpTest._remove_temp_folder, self, args))
        return cleanup_handlers

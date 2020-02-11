#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""

.. moduleauthor:: Zaleos <admin@zaleos.net>

"""

import sys
import logging
import logging.config
import io
import configparser
import textwrap
import os
from . import Exceptions
from . import Utils

logger = logging.getLogger(__name__)

class DynamicFileHandler(logging.FileHandler):
    """
    Destination file has to be created dynamically according to application's logic.
    And the destination log path isn't known beforehand.
    The module, which wishes to implement support for this handler:
    1. Should check if this handler is specified.
    2. Should configure the desired path of a log file on-the-fly.
    Please see SIPpTest class for example.

    If user by mistake has specified this handler for a module which doesn't support dynamic file path configuration,
    self.stream is not set, and log message is ignored in emit().
    """
    def __init__(self, filename):
        super().__init__(filename, delay=1) # delay real opening file stream

    def set_folder(self, folder):
        assert(not self.stream)
        self.baseFilename = os.path.abspath(os.path.join(folder, os.path.basename(self.baseFilename)))
        self.stream = self._open()

    def emit(self, record):
        if self.stream:
            super().emit(record)

class LoggingCallAdapter(logging.LoggerAdapter):
    """
    This example adapter expects the passed in dict-like object to have a
    'prefix' key, whose value in brackets is prepended to the log message.
    """
    def process(self, msg, kwargs):
        return '[%s] %s' % (self.extra['prefix'], msg), kwargs


class RainbowLoggingHandler(logging.StreamHandler):

    """
    From: https://pypi.python.org/pypi/rainbow_logging_handler
    A colorful logging handler optimized for terminal debugging aesthetics.

    - Designed for diagnosis and debug mode output - not for disk logs
    - Highlight the content of logging message in more readable manner
    - Show function and line, so you can trace where your logging messages
      are coming from
    - Keep timestamp compact
    - Extra module/function output for traceability

    The class provide few options as member variables you
    would might want to customize after instiating the handler.
    """

    color_map = {
        'black': 0,
        'red': 1,
        'green': 2,
        'yellow': 3,
        'blue': 4,
        'magenta': 5,
        'cyan': 6,
        'white': 8,
    }
    (csi, reset) = ('\x1b[', '\x1b[0m')

    #: Show logger name
    show_name = True

    #: Color of each column
    _column_color = {
        # '%(asctime)s' : ("black", None, True),
        # ...
        '%(message)s': {
            # logging.DEBUG   : ('cyan'  , None , False),
            # ...
        },
    }

    # Enable ANSI color code on Windows
    if os.name == 'nt':
        import colorama
        colorama.init()

    def __init__(
        self, stream,
        color_name=('white', None, True),
        color_levelno=('white', None, False),
        color_levelname=('white', None, True),
        color_pathname=('blue', None, True),
        color_filename=('blue', None, True),
        color_module=('yellow', None, True),
        color_lineno=('cyan', None, False),
        color_funcName=('green', None, False),
        color_created=('white', None, False),
        color_asctime=('black', None, True),
        color_msecs=('white', None, False),
        color_relativeCreated=('white', None, False),
        color_thread=('white', None, False),
        color_threadName=('white', None, False),
        color_process=('white', None, False),
        color_message_debug=('cyan', None, False),
        color_message_info=('white', None, False),
        color_message_warning=('yellow', None, True),
        color_message_error=('red', None, True),
        color_message_critical=('white', 'red', True),
    ):
        """Construct colorful stream handler

        :param stream:  a stream to emit log
                        (e.g. sys.stderr, sys.stdout, writable `file`
                        object, ...)
        :type color_*:  str compatible to `time.strftime()` argument
        :param datefmt: format of %(asctime)s, passed to
                        `logging.Formatter.__init__()`.
                        If `None` is passed, `logging`'s default format of
                        '%H:%M:%S,<milliseconds>' is used.
        :type color_*:  `(<symbolic name of foreground color>,
                          <symbolic name of background color>,
                          <brightness flag>)`
        :param color_*: Each column's color. See `logging.Formatter` for
                        supported column (`*`)
        """
        logging.StreamHandler.__init__(self, stream)

        # set custom color
        self._column_color['%(name)s'] = color_name
        self._column_color['%(levelno)s'] = color_levelno
        self._column_color['%(levelname)s'] = color_levelname
        self._column_color['%(pathname)s'] = color_pathname
        self._column_color['%(filename)s'] = color_filename
        self._column_color['%(module)s'] = color_module
        self._column_color['%(lineno)d'] = color_lineno
        self._column_color['%(funcName)s'] = color_funcName
        self._column_color['%(created)f'] = color_created
        self._column_color['%(asctime)s'] = color_asctime
        self._column_color['%(msecs)d'] = color_msecs
        self._column_color['%(relativeCreated)d'] = color_relativeCreated
        self._column_color['%(thread)d'] = color_thread
        self._column_color['%(threadName)s'] = color_threadName
        self._column_color['%(process)d'] = color_process
        self._column_color['%(message)s'][logging.DEBUG] = color_message_debug
        self._column_color['%(message)s'][logging.INFO] = color_message_info
        self._column_color['%(message)s'][
            logging.WARNING] = color_message_warning
        self._column_color['%(message)s'][logging.ERROR] = color_message_error
        self._column_color['%(message)s'][
            logging.CRITICAL] = color_message_critical

    @property
    def is_tty(self):
        """Returns true if the handler's stream is a terminal."""
        return getattr(self.stream, 'isatty', lambda: False)()

    def get_color(self, fg=None, bg=None, bold=False):
        """
        Construct a terminal color code

        :param fg: Symbolic name of foreground color

        :param bg: Symbolic name of background color

        :param bold: Brightness bit
        """
        params = []
        if bg in self.color_map:
            params.append(str(self.color_map[bg] + 40))
        if fg in self.color_map:
            params.append(str(self.color_map[fg] + 30))
        if bold:
            params.append('1')

        color_code = ''.join((self.csi, ';'.join(params), 'm'))

        return color_code

    def colorize(self, record):
        """
        Get a special format string with ASCII color codes.
        """
        color_fmt = self._colorize_fmt(self.formatter._fmt,
                                       record.levelno)
        formatter = logging.Formatter(color_fmt,
                                      self.formatter.datefmt)
        self.colorize_traceback(formatter, record)
        output = formatter.format(record)
        # Clean cache so the color codes of traceback don't leak to other
        # formatters
        record.ext_text = None
        return output

    def colorize_traceback(self, formatter, record):
        """
        Turn traceback text to red.
        """
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            record.exc_text = "".join([
                self.get_color("red"),
                formatter.formatException(record.exc_info),
                self.reset,
            ])

    def format(self, record):
        """
        Formats a record for output.

        Takes a custom formatting path on a terminal.
        """
        if self.is_tty:
            message = self.colorize(record)
        else:
            message = logging.StreamHandler.format(self, record)

        return message

    def emit(self, record):
        """Emit colorized `record` when called from `logging` module's printing
        functions"""
        try:
            msg = self.format(record)
            msg = self._encode(msg)
            self.stream.write(msg + getattr(self, 'terminator', '\n'))
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

    def _encode(self, msg):
        """Encode `msg` if it is `unicode` object"""
        import sys
        if ((2, 6, 0) <= sys.version_info < (3, 0, 0) and unicode and
                isinstance(msg, unicode)):
            enc = getattr(self.stream, 'encoding', 'utf-8')
            if enc is None:
                # An encoding property was found, but it was None
                enc = 'utf-8'
            return msg.encode(enc, 'replace')
        return msg

    def _colorize_fmt(self, fmt, levelno):
        """Adds ANSI color codes on plain `fmt`"""
        for column in self._column_color.keys():
            pos = fmt.find(column)
            if pos == -1:
                continue
            (pre_col, post_col) = (fmt[:pos], fmt[pos + len(column):])
            if column != '%(message)s':
                color_tup = self._column_color[column]
            else:
                color_tup = self._column_color[column][levelno]
            fmt = ''.join([pre_col,
                           self.reset, self.get_color(*color_tup),
                           column,
                           self.reset,
                           post_col])
        return fmt


class WrappedRainbowLoggingHandler(RainbowLoggingHandler):
    """ Wrapping the message of the record.
    Very expensive handler. Don't use it in production!
    """

    def __init__(self, *args, **kwargs):

        RainbowLoggingHandler.__init__(self, *args, **kwargs)
        self.width = Utils.get_terminal_size()[0]

    def format(self, record):

        raw_rainbow = RainbowLoggingHandler.format(self, record)

        # Some maths to properly wrap the msg
        raw_tmp = logging.Formatter(
            fmt=self.formatter._fmt,
            datefmt=self.formatter.datefmt).format(record)
        gap = ' ' * raw_tmp.find(record.getMessage())
        del raw_tmp

        # Wrapping the message
        message = textwrap.fill(raw_rainbow,
                                width=self.width,
                                subsequent_indent=gap)
        # message = message + '\n'

        return message

def init_log(log_config_paths, stamped_id, quiet=False):
    """ Initializes, validates and tweaks log formats to always attach the
    stamped_id param.

    :param log_config_path: path of the logging configuration file.
    :type name: str.

    :param stamped_id: id to stamp in all log formatters.
    :type state: str.

    :param quiet: don't report anything to user during initialization.
    :type: bool.

    :returns:  None.
    :raises: sipplauncher.utils.Exceptions.ErrorInitLog

    """

    # At least one file from log_config_paths need to exists.
    log_config_path = None
    for log_config_tmp in log_config_paths:
        try:
            with open(log_config_tmp):
                log_config_path = log_config_tmp
                break
        except IOError:
            pass
        except:
            raise

    # We need to have a logging configuration file.
    if not log_config_path:
        msg = 'Please make sure a valid log configuration'
        msg += ' file exists %s' % (log_config_path or '')
        raise Exceptions.ErrorInitLog(msg)

    # Init the loggers. As a good practice, a stamped_id needs to always be
    # attached in the log formater. This function reads the actual log config
    # file and modifies it in memory attaching the stamped_id to the
    # formatters. After that it sends it to fileConfig.
    try:
        with open(log_config_path, mode='r') as f:
            cp = configparser.ConfigParser()
            cp.readfp(f)
    except:
        raise

    try:
        formatters = cp.get("formatters", "keys").split(',')
    except Exception:
        msg = 'Formatters section and its keys option are mandatory'
        raise Exceptions.ErrorInitLog(msg)

    # Lets tweak all the formatters found
    for formatter in formatters:
        section = "formatter_%s" % formatter

        try:
            oldargs = cp.get(section, "format", raw=True)
        except Exception:
            msg = 'Formatter section not found "%s"' % section
            raise Exceptions.ErrorInitLog(msg)

        try:
            cp.set(section, "format", str(stamped_id) + ' ' + oldargs)
        except Exception as err:
            msg = 'Error while attaching version to the formatter. %s' % err
            raise Exceptions.ErrorInitLog(msg)

    # We'll pass the tweaked config to the fileConfig method
    try:
        log_config_labelled = io.StringIO()
        cp.write(log_config_labelled)
        log_config_labelled.seek(0)
        logging.config.fileConfig(log_config_labelled,
                                  disable_existing_loggers=False)

    except:
        raise

    class StreamToLogger(object):
       """
       Fake file-like stream object that redirects writes to a logger instance.
       https://www.electricmonk.nl/log/2011/08/14/redirect-stdout-and-stderr-to-a-logger-in-python/
       """
       def __init__(self, logger, log_level=logging.INFO):
          self.logger = logger
          self.log_level = log_level
          self.linebuf = ''

       def write(self, buf):
          for line in buf.rstrip().splitlines():
             self.logger.log(self.log_level, line.rstrip())

       # Spawning new multiprocessing.Process doesn't work
       # when below method is not implemented:
       # AttributeError: 'StreamToLogger' object has no attribute 'flush'
       def flush(self):
           pass

    # Let's hide stderr into DEBUG
    stderr_logger = logging.getLogger('STDERR')
    sl = StreamToLogger(stderr_logger, logging.DEBUG)
    sys.stderr = sl

    if not quiet:
        # Lets give some feedback
        logger_config = logging.getLogger("config")
        msg = 'Using log configuration file "%s"' % log_config_path
        logger_config.info(msg)

    return
    

if __name__ == '__main__':
    pass

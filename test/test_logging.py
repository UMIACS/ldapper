# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging

from ldapper.logging import ProxyLogger


class TestProxyLogger:

    def test_logging_init(self):
        logger = ProxyLogger(logger=logging.getLogger('test'))
        assert not logger.has_errors()
        assert not logger.has_warnings()
        assert logger.get_messages() == []

    def test_logging_warning(self):
        logger = ProxyLogger(logger=logging.getLogger('test'))
        logger.warning('this is a test')
        assert logger.has_warnings()
        assert not logger.has_errors()

        assert logger.get_messages() == [("WARNING", 'this is a test')]
        # does not flush until we ask it to
        assert logger.get_messages() == [("WARNING", 'this is a test')]

        # we flush and get our messages
        assert logger.flush() == [("WARNING", 'this is a test')]
        # but now it should be empty
        assert logger.flush() == []
        assert logger.get_messages() == []

    def test_logging_info(self):
        logger = ProxyLogger(logger=logging.getLogger('test'))
        logger.info('this is an info msg')
        assert logger.get_messages() == [("INFO", 'this is an info msg')]
        assert not logger.has_warnings()
        assert not logger.has_errors()

    def test_logging_debug(self):
        logger = ProxyLogger(logger=logging.getLogger('test'))
        logger.debug('this is a debug msg')
        assert logger.get_messages() == [("DEBUG", 'this is a debug msg')]

    def test_logging_error(self):
        logger = ProxyLogger(logger=logging.getLogger('test'))
        logger.error('this is an error msg')
        assert logger.get_messages() == [("ERROR", 'this is an error msg')]
        assert logger.has_errors()
        assert not logger.has_warnings()

# -*- coding: utf-8 -*-

import pygments.styles
import pygments.lexers
import pygments.formatters
from pygments import token

from .escapeseq import EscapeSequence
from .colormap import reshade

import logging
logger = logging.getLogger('consolemd.styler')

# based on solarized dark
solarized = {
    'text':         '',
    'heading':      '#cb4b16 bold', # orange
    'emph':         'italic',
    'strong':       'bold',
    'block_quote':  'italic',
    'code':         '#af8700', # yellow
    'link':         '#0087ff',
    'image':        '#0087ff',
    'bullet':       '#268bd2 bold', # blue
    }

class Style(object):

    def __init__(self, style_name):
        self.pyg_style = pygments.styles.get_style_by_name(style_name)

        f = self.eseq_from_pygments # shortcut

        # each style has an entering value and an exiting value, None means reset
        self.styles = {
            'document':     (None, None),
            'paragraph':    (None, None),
            'text':         (None, None),
            'softbreak':    (None, None),
            'linebreak':    (None, None),
            'heading':      (f(token.Generic.Heading, solarized['heading']), None),
            'emph':         (f(token.Generic.Emph, solarized['emph']), None),
            'strong':       (f(token.Generic.Strong, solarized['strong']), None),
            'link':         (f(token.Name.Entity, solarized['link']), None),
            'image':        (f(token.Name.Entity, solarized['image']), None),
            'code':         (f(token.String.Backtick, solarized['code']), None),
            'block_quote':  (f(token.Generic.Emph, solarized['block_quote']), None),
            'bullet':  (f(token.Literal, solarized['bullet']), None),
                }

        #print self.styles

    def eseq_from_pygments(self, token, default=''):
        value = self.pyg_style.styles.get(token, '') or default
        values = value.split()

        def fg(values):
            try:
                return filter(lambda val: val.startswith('#'), values)[0]
            except IndexError:
                return ''

        def bg(values):
            try:
                bg = filter(lambda val: val.startswith('bg:'), values)[0]
                return bg.split('bg:')[1]
            except IndexError:
                return ''

        return EscapeSequence(
                fg        = fg(values),
                bg        = bg(values),
                bold      = 'bold' in values,
                underline = 'underline' in values,
                italic    = 'italic' in values,
                )

    def entering(self, key):
        try:
            eseq = self.styles[key][0]
        except KeyError:
            return ''

        if eseq is not None:
            return eseq.color_string()

        return ''

    def exiting(self, key):
        try:
            eseq = self.styles[key][1] or self.styles[key][0]
        except KeyError:
            return ''

        if eseq is not None:
            return eseq.reset_string()

        return ''


class Styler(object):

    def __init__(self, style_name):
        self.stack = []
        self.style_name = style_name
        self.style = Style(style_name)

    def __getattr__(self, name):
        from functools import partial
        return partial(self._default, name)

    def push(self, eseq):
        self.stack.append(eseq)
        return eseq

    def pop(self):
        return self.stack.pop()

    @staticmethod
    def stylize( eseq, text ):
        return "{}{}{}".format(eseq.color_string(), text, eseq.reset_string())

    def dispatch(self, obj, entering):
        try:
            handler = getattr(self, obj.t)
            return handler(obj, entering)
        except KeyError:
            logger.error( "unhandled ast type: {}".format(obj.t) )

        return ''

    def _default(self, name, obj, entering):
        if entering:
            return self.style.entering(name)
        else:
            return self.style.exiting(name)

    def heading(self, obj, entering):
        # make each heading level a bit darker
        eseq = self.style.styles['heading'][0]
        color = eseq.fg
        if entering:
            level = 1 if obj.level is None else obj.level
            per = 1.0 - .05 * (level-1)
            eseq.fg = reshade(color, per)
            return self.push(eseq).color_string()
        else:
            return self.pop().reset_string()

    def code(self, obj, entering):
        if entering:
            eseq = self.style.styles['code'][0]
            return self.push(eseq).color_string()
        else:
            assert False, "this shouldn't be called, ConsoleMD() is resetting this token"

    def bullet(self, bullet):
        """
        this is not an official markdown type, but it's how we colorize
        just the bullet/number of a list item
        """
        eseq = self.style.styles['bullet'][0]
        return Styler.stylize(eseq, bullet)

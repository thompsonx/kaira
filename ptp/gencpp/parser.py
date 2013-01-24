#
#    Copyright (C) 2013 Stanislav Bohm
#
#    This file is part of Kaira.
#
#    Kaira is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License, or
#    (at your option) any later version.
#
#    Kaira is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Kaira.  If not, see <http://www.gnu.org/licenses/>.


import pyparsing as pp
import base.utils as utils
import base.net

digits = "0123456789"
operator_chars = "+-*/%=!<>&|"

lpar, rpar, dot, delim, sem, lbracket, rbracket \
    = map(pp.Suppress, "().,;[]")

ident = pp.Word(pp.alphas+"_:", pp.alphanums+"_:")
expression = pp.Forward()
number = (pp.Optional("-", "+") + pp.Word(digits) +
          pp.Optional(dot + pp.Word(digits)))
string = pp.dblQuotedString
operator = pp.Word(operator_chars)
parens = lpar + pp.Optional(expression + pp.ZeroOrMore(delim + expression)) + rpar
var_or_call = ident + pp.Optional(parens)
term = number | string | var_or_call
expression << term

mark = pp.Empty().setParseAction(lambda loc, t: loc)
full_expression = (mark + expression.suppress() + mark) \
    .setParseAction(lambda s, loc, t: s[t[0]:t[1]])

expressions = pp.delimitedList(full_expression, ";")

"""
expression_marks = pp.Group(mark + expression.suppress() + mark)
expressions_marks = pp.delimitedList(expression_marks, ";")
"""

typename = ident

edge_config_param = lpar + mark + expression.suppress() + mark + rpar
edge_config_item = ident + pp.Optional(edge_config_param, None)
edge_config = lbracket + pp.delimitedList(edge_config_item, ";") + rbracket

edge_expr = pp.Optional(edge_config, None) + pp.Group(expressions)

def check_expression(expr):
    if len(expr) == 0:
        return "Expression is empty"
    try:
        expression.parseString(expr, parseAll=True)
        return None
    except pp.ParseException, e:
        return e.lineno, e.col, e.msg

def check_typename(tname, source):
    if len(tname) == 0:
        raise utils.PtpException("Type is empty", source)
    try:
        typename.parseString(tname, parseAll=True)
    except pp.ParseException, e:
        raise utils.PtpException(e.msg, source)

def is_variable(expr):
    try:
        ident.parseString(expr, parseAll=True)
        return True
    except pp.ParseException:
        return False

def take_substrings(string, pairs):
    return [ string[start:end] for start, end in pairs ]

def split_expressions(string, source):
    if string.strip() == "":
        return []
    try:
        return expressions.parseString(string, parseAll=True)
    except pp.ParseException, e:
        raise utils.PtpException(e.msg, source)

def parse_edge_expression(string, source):
    configs, expressions = edge_expr.parseString(string, parseAll=True)
    return (edge_config,
            [ base.net.EdgeInscription(expr)
                for expr in expressions ])

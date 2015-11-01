import subprocess
import string
import os
import datetime
import socket

from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses, utils
import ycmd.utils


TokenTypeMap = {
    'skConst':           'const',
    'skEnumField':       'enum',
    'skForVar':          'var',
    'skIterator':        'iterator',
    'skClosureIterator': 'iterator',
    'skLabel':           'label',
    'skLet':             'let',
    'skMacro':           'macro',
    'skParam':           'param',
    'skMethod':          'method',
    'skProc':            'proc',
    'skResult':          'result',
    'skTemplate':        'template',
    'skType':            'type',
    'skVar':             'var',
    'skAlias':           'alias',
}


def _GetCompletions(cfile, memfile, crow, ccol, ctype):
    query = ctype + ' ' + cfile + ';' + memfile + ':' + str(crow) + ':' + str(ccol) + '\n'
    completions = []
    # raise ValueError(query)

    try:
        s = socket.socket()
        s.setblocking(True)
        s.connect(('localhost', 6002))
        s.sendall(query)
        f = s.makefile('r')

        for line in f:
            line = line.strip()
            if len(line) is not 0:
                completions.append(line)
                print line
    except:
        raise RuntimeError("nimsuggest server is not running")
    finally:
        s.close()

    return completions


def _WrapString(string):
    return string.strip().replace('\\x0A', '\n').replace('x0A', '\n')


def FormatDocStr(docstr):
    nstr = docstr.replace('\\x0A\\x0A', '\n--------------------------------------------------------------------------------\n')
    nstr = nstr.replace('\\x0A', '\n')
    nstr = nstr.strip()[1:][0:-1]
    return nstr


def _CreateTmpFile(request_data):
    cfile = request_data['filepath']
    contents = request_data['file_data'][cfile][u'contents']
    memfilepath = '/tmp/ycmnimcomp.%s.nim' % os.getpid()
    memfile = open(memfilepath, 'w')
    memfile.write(contents)
    memfile.close()
    return memfilepath, cfile, contents


class NimCompleter(Completer):
    def __init__(self, user_options):
        super(NimCompleter, self).__init__(user_options)


    def SupportedFiletypes(self):
        return ['nim', 'nimrod']


    def ComputeCandidatesInner(self, request_data):
        memfilepath, cfile = _CreateTmpFile(request_data)

        suggestions = []
        ycm_completions = []

        try:
            suggestions = _GetCompletions(
                cfile,
                memfilepath,
                request_data['line_num'],
                request_data['column_num'],
                'sug')

        except RuntimeError as err:
            raise RuntimeError(err)
        finally:
            os.remove(memfilepath)

        def addOne(ftype, name, description, doc):
            ycm_completions.append(
                responses.BuildCompletionData(
                    ToUtf8IfNeeded(name),
                    ToUtf8IfNeeded(ftype + ': ' + description),
                    ToUtf8IfNeeded(FormatDocStr(doc))))

        for line in suggestions:
            splitted = line.split('\t')
            if len(splitted) >= 8:
                _, ftype, name, signature, ffile, x, y, docstr = splitted
                addOne(TokenTypeMap.get(ftype, 'Unknown'),
                       name.split('.')[-1],
                       signature,
                       signature + '\n\n' + FormatDocStr(docstr))

        return ycm_completions


    def DefinedSubcommands(self):
        return ['GoTo',
                'GetType']


    def OnUserCommand(self, arguments, request_data):
        memfilepath, cfile, _ = _CreateTmpFile(request_data)

        completion = _GetCompletions(
            cfile,
            memfilepath,
            request_data['line_num'],
            request_data['column_num'],
            'def')

        if not completion:
            raise ValueError("No idea")

        completion = completion[0].split('\t')

        if len(completion) < 6:
            raise ValueError("No such symbol")

        _, ctype, fullname, rtype, ffile, row, col, docstr = completion

        if not arguments:
            raise ValueError(self.UserCommandsHelpMessage())
        elif arguments[0] == 'GetType':
            reply = '[' + TokenTypeMap.get(ctype, '') + '] (' + fullname + ')'
            if len(rtype) != 0:
                reply += ': ' + rtype + '\n--------------------------------------------------------------------------------\n' + FormatDocStr(docstr)
            return responses.BuildDisplayMessageResponse(ToUtf8IfNeeded(reply))
        elif arguments[0] == 'GoTo':
            return responses.BuildGoToResponse(
                    ToUtf8IfNeeded(ffile),
                    int(row),
                    int(col) + 1,
                    ToUtf8IfNeeded(FormatDocStr(docstr)))
        else:
            raise RuntimeError(arguments)

import subprocess
import os

from ycmd.utils import ToUtf8IfNeeded
from ycmd.completers.completer import Completer
from ycmd import responses, utils

NIM_COMPILER = '/usr/bin/nim'

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


def _ExecBinary(*args, **kwargs):
    proc = utils.SafePopen([NIM_COMPILER] + list(args),
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE)
    stdoutdata, stderrdata = proc.communicate(None)
    return stdoutdata


def _GetCompletions(cfile, crow, ccol, ctype):
    ctypestr = ''
    if ctype == 'definition':
        ctypestr = '--def'
    elif ctype == 'context':
        ctypestr = '--context'
    elif ctype == 'usage':
        ctypestr = '--usages'
    else:
        ctypestr = '--suggest'
    return _ExecBinary('--verbosity:0',
                       'idetools',
                       '--track:' +
                       cfile +
                       ',' + str(crow) +
                       ',' + str(ccol - 1),
                       ctypestr,
                       cfile).split('\n')


class NimCompleter(Completer):
    def __init__(self, user_options):
        super(NimCompleter, self).__init__(user_options)

    def SupportedFiletypes(self):
        return ['nim', 'nimrod']

    def ComputeCandidatesInner(self, request_data):
        cfile = request_data['filepath']
        contents = request_data['file_data'][cfile][u'contents']
        memfilepath = '/tmp/ycmnimcomp.%s.nim' % os.getpid()
        memfile = open(memfilepath, 'w')

        suggestions = []
        ycm_completions = []

        def addOne(ftype, name, description, doc):
            ycm_completions.append(
                responses.BuildCompletionData(
                    ToUtf8IfNeeded(name),
                    ToUtf8IfNeeded(ftype + ': ' + description),
                    ToUtf8IfNeeded(doc)))

        try:
            memfile.write(contents)
            memfile.close()
            suggestions = _GetCompletions(
                memfilepath,
                request_data['line_num'],
                request_data['column_num'],
                'suggestion')
        except RuntimeError as err:
            raise RuntimeError(err)
        finally:
            os.remove(memfilepath)

        for line in suggestions:
            splitted = line.split('\t')
            if len(splitted) >= 8:
                _, ftype, name, signature, ffile, x, y, docstr = splitted
                addOne(TokenTypeMap.get(ftype, 'Unknown'),
                       name.split('.')[-1],
                       signature,
                       signature + '\n\n' + docstr)

        return ycm_completions

    def DefinedSubcommands(self):
        return ['GoTo',
                'GetType']

    def OnUserCommand(self, arguments, request_data):
        completion = _GetCompletions(
            request_data['filepath'],
            request_data['line_num'],
            request_data['column_num'],
            'definition')[0].split('\t')

        if len(completion) < 6:
            raise ValueError("No such symbol")

        _, ctype, fullname, rtype, ffile, row, col, docstr = completion

        if not arguments:
            raise ValueError(self.UserCommandsHelpMessage())
        elif arguments[0] == 'GetType':
            reply = '[' + TokenTypeMap.get(ctype, '') + '] (' + fullname + ')'
            if len(rtype) != 0:
                reply += ': ' + rtype
            return responses.BuildDisplayMessageResponse(reply)
        elif arguments[0] == 'GoTo':
            return responses.BuildGoToResponse(
                    ToUtf8IfNeeded(ffile),
                    int(row),
                    int(col) + 1,
                    ToUtf8IfNeeded(docstr))
        else:
            raise RuntimeError(arguments)

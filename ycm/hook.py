from ycmd.completers.nim.nim_completer import NimCompleter

def GetCompleter( user_options ):
  return NimCompleter( user_options )

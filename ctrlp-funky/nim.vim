" Language: Nim (nim)
" Author: baabelfish
" License: The MIT License

function! ctrlp#funky#ft#nim#filters()
  let filters = [
        \ { 'pattern': '\v\s*macro\s+\w.+\s*\(',
        \   'formatter': [] },
        \ { 'pattern': '\v\s*template\s+\w.+\s*\(',
        \   'formatter': [] },
        \ { 'pattern': '\v\s*func\s+\w.+\s*\(',
        \   'formatter': [] },
        \ { 'pattern': '\v\s*method\s+\w.+\s*\(',
        \   'formatter': [] },
        \ { 'pattern': '\v\s*proc\s+\w.+\s*\(',
        \   'formatter': [] }
  \ ]
  return filters
endfunction

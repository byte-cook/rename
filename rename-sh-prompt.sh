# Shell Auto Completion
#
# To enable: 
#
# 1) Copy this file to somewhere (e.g. /opt/rename/rename-sh-prompt).
# 2) Add the following line to your .bashrc/.zshrc:
#   source /opt/rename/rename-sh-prompt
#
# https://www.baeldung.com/linux/compgen-command-usage
# https://www.baeldung.com/linux/shell-auto-completion
# 

function _rename() {
    compWithoutLatest="${COMP_WORDS[@]:0:$COMP_CWORD}"
    latest="${COMP_WORDS[$COMP_CWORD]}"
    
    local options
    options="-h --help --debug -v --verbose -n --dry-run -r --recursive --dir-only --exclude --include"
    options="$options -b -e -E"
    options="$options --index --index-from --index-to --indexr-from --indexr-to"
    options="$options --text --text-from --text-to --textx-from --textx-to"
    options="$options --char-num --char-non-num --char-alpha --char-non-alpha --char-alnum --char-non-alnum --char-upper --char-lower"
    options="$options --pattern"
    options="$options test add remove replace lower upper camel sentence fill keep swap number cut dir"
    # set program options as default
    local words="$options"

    # overwrite $words for command options
    local commandFound=false
    for e in $compWithoutLatest
    do
        case "${e}" in 
            "test")
                words="-h --help -a --all -p"
                commandFound=true
                ;;
            add)
                words="-h --help -e"
                commandFound=true
                ;;
            remove | replace)
                words="-h --help"
                commandFound=true
                ;;
            lower | upper | camel | sentence)
                words="-h --help"
                commandFound=true
                ;;
            fill)
                words="-h --help -w -e"
                commandFound=true
                ;;
            keep)
                words="-h --help -e"
                commandFound=true
                ;;
            swap)
                words="-h --help -l --left -r --right"
                commandFound=true
                ;;
            "cut")
                words="-h --help -e"
                commandFound=true
                ;;
            dir)
                words="-h --help"
                commandFound=true
                ;;
            number)
                words="-h --help -e -b -a -w -s --start -i --increment --replace --no-reset"
                commandFound=true
                ;;
        esac
    done

    if $commandFound ; then
        COMPREPLY=($(compgen -fd -W "$words" -- $latest))
    else
        COMPREPLY=($(compgen -W "$words" -- $latest))
    fi
    return 0
}

complete -F _rename rename.py

_osed_completion() {
    local cur prev opts subcmds
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    subcmds="validate lint generate diff visualize check-versions completion"
    opts="--file --schema-version --schema-file --output-format --driver --expected-schema-version --target --out --help"

    # Complete subcommands
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "${subcmds}" -- ${cur}) )
        return 0
    fi

    # Complete options for subcommands
    case "${COMP_WORDS[1]}" in
        validate|lint|generate|diff|visualize)
            if [[ ${cur} == --* ]]; then
                COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
                return 0
            fi
            ;;
    esac

    # Complete file paths for --file and --schema-file
    if [[ ${prev} == "--file" || ${prev} == "--schema-file" ]]; then
        COMPREPLY=( $(compgen -f -- ${cur}) )
        return 0
    fi
}
complete -F _osed_completion osed
